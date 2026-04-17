"""Tests for grader weights — weighted mean scoring and pass/fail logic."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.providers.base import LLMResponse
from src.services.eval_runner import run_evaluation


def _make_config(graders: list | None = None) -> MagicMock:
    """Create a fake EvalConfig with graders."""
    config = MagicMock()
    config.system_prompt = "You are a test assistant."
    config.model = "gpt-4.1"
    config.temperature = 0.7
    config.max_tokens = None
    config.tools = []
    config.tool_options = {}
    config.graders = graders or []
    config.concurrency = 5
    config.reasoning_config = None
    config.response_format = None
    return config


def _make_run() -> MagicMock:
    run = MagicMock()
    run.id = "run1"
    run.eval_config_id = "cfg1"
    run.dataset_id = "ds1"
    return run


def _make_dataset() -> MagicMock:
    ds = MagicMock()
    ds.file_path = "/fake/data.csv"
    return ds


def _make_llm_response(text: str) -> LLMResponse:
    return LLMResponse(
        text=text,
        latency_ms=100,
        token_usage={"input_tokens": 10, "output_tokens": 20},
        raw_response={"id": "resp_1", "model": "gpt-4.1"},
    )


@pytest.fixture
def mock_repos():
    """Patch all repository classes and session context."""
    with (
        patch("src.services.eval_runner.get_session_context") as mock_session_ctx,
        patch("src.services.eval_runner.RunRepository") as mock_run_repo_cls,
        patch("src.services.eval_runner.ConfigRepository") as mock_config_repo_cls,
        patch("src.services.eval_runner.DatasetRepository") as mock_dataset_repo_cls,
        patch("src.services.eval_runner.ResultRepository") as mock_result_repo_cls,
        patch("src.services.eval_runner.read_csv_rows") as mock_read_csv,
        patch("src.services.eval_runner.call_llm") as mock_call_llm,
    ):
        session_mock = AsyncMock()
        ctx = AsyncMock()
        ctx.__aenter__.return_value = session_mock
        mock_session_ctx.return_value = ctx

        run_repo = mock_run_repo_cls.return_value
        config_repo = mock_config_repo_cls.return_value
        dataset_repo = mock_dataset_repo_cls.return_value
        result_repo = mock_result_repo_cls.return_value

        run_repo.update_status = AsyncMock()
        run_repo.update_progress = AsyncMock()
        run_repo.set_summary = AsyncMock()
        result_repo.create_batch = AsyncMock()

        yield {
            "run_repo": run_repo,
            "config_repo": config_repo,
            "dataset_repo": dataset_repo,
            "result_repo": result_repo,
            "read_csv": mock_read_csv,
            "call_llm": mock_call_llm,
        }


class TestGraderWeights:
    """Weighted mean scoring and pass/fail with grader weights."""

    async def test_no_weights_is_simple_average(self, mock_repos):
        """Without explicit weights, all graders default to weight 1.0 → simple average."""
        config = _make_config(graders=[
            {"type": "string_check", "name": "check1", "input_value": "{{ sample.output_text }}", "operation": "equals", "reference_value": "hello"},
            {"type": "string_check", "name": "check2", "input_value": "{{ sample.output_text }}", "operation": "equals", "reference_value": "hello"},
        ])
        mock_repos["run_repo"].get_by_id = AsyncMock(return_value=_make_run())
        mock_repos["config_repo"].get_by_id = AsyncMock(return_value=config)
        mock_repos["dataset_repo"].get_by_id = AsyncMock(return_value=_make_dataset())
        mock_repos["read_csv"].return_value = [
            {"input": "hello", "expected_output": "hello"},
        ]
        mock_repos["call_llm"].return_value = _make_llm_response("hello")

        mock_compare1 = AsyncMock(return_value=(1.0, True, {}))
        mock_compare2 = AsyncMock(return_value=(0.6, True, {}))

        with (
            patch("src.comparers.string_check_grader.StringCheckGraderComparer") as MockGrader1,
        ):
            # We need to mock both graders created from the same class
            call_count = {"n": 0}
            def make_grader(cfg):
                call_count["n"] += 1
                m = MagicMock()
                m.grader_name = cfg.get("name", "")
                if call_count["n"] == 1:
                    m.compare = mock_compare1
                else:
                    m.compare = mock_compare2
                return m
            MockGrader1.side_effect = make_grader
            await run_evaluation("run1")

        results = mock_repos["result_repo"].create_batch.call_args[0][0]
        assert len(results) == 1
        r = results[0]
        # check1 returns 1.0, check2 returns 0.6
        # Both have default weight 1.0 → simple average = 0.8
        assert r.comparer_score == pytest.approx(0.8)
        assert r.passed is True
        for detail in r.comparer_details.values():
            assert detail.get("weight") == 1.0

    async def test_weighted_mean_calculation(self, mock_repos):
        """Weights alter the score average: w*s / sum(w)."""
        config = _make_config(graders=[
            {"type": "string_check", "name": "check1", "weight": 0.5, "input_value": "{{ sample.output_text }}", "operation": "equals", "reference_value": "hello"},
            {"type": "string_check", "name": "check2", "weight": 1.0, "input_value": "{{ sample.output_text }}", "operation": "equals", "reference_value": "hello"},
        ])
        mock_repos["run_repo"].get_by_id = AsyncMock(return_value=_make_run())
        mock_repos["config_repo"].get_by_id = AsyncMock(return_value=config)
        mock_repos["dataset_repo"].get_by_id = AsyncMock(return_value=_make_dataset())
        mock_repos["read_csv"].return_value = [
            {"input": "hello", "expected_output": "hello"},
        ]
        mock_repos["call_llm"].return_value = _make_llm_response("hello")

        mock_compare1 = AsyncMock(return_value=(1.0, True, {}))
        mock_compare2 = AsyncMock(return_value=(0.8, True, {}))

        with (
            patch("src.comparers.string_check_grader.StringCheckGraderComparer") as MockGrader,
        ):
            call_count = {"n": 0}
            def make_grader(cfg):
                call_count["n"] += 1
                m = MagicMock()
                m.grader_name = cfg.get("name", "")
                if call_count["n"] == 1:
                    m.compare = mock_compare1
                else:
                    m.compare = mock_compare2
                return m
            MockGrader.side_effect = make_grader
            await run_evaluation("run1")

        results = mock_repos["result_repo"].create_batch.call_args[0][0]
        r = results[0]
        # Weighted mean: (0.5*1.0 + 1.0*0.8) / (0.5 + 1.0) = 1.3/1.5 ≈ 0.8667
        expected_score = (0.5 * 1.0 + 1.0 * 0.8) / (0.5 + 1.0)
        assert r.comparer_score == pytest.approx(expected_score, abs=1e-4)
        assert r.passed is True

    async def test_weight_zero_excluded_from_pass_fail(self, mock_repos):
        """A grader with weight=0 is informational — its failure doesn't fail the result."""
        config = _make_config(graders=[
            {"type": "string_check", "name": "check1", "weight": 0, "input_value": "{{ sample.output_text }}", "operation": "equals", "reference_value": "hello"},
            {"type": "string_check", "name": "check2", "weight": 1.0, "input_value": "{{ sample.output_text }}", "operation": "equals", "reference_value": "hello"},
        ])
        mock_repos["run_repo"].get_by_id = AsyncMock(return_value=_make_run())
        mock_repos["config_repo"].get_by_id = AsyncMock(return_value=config)
        mock_repos["dataset_repo"].get_by_id = AsyncMock(return_value=_make_dataset())
        mock_repos["read_csv"].return_value = [
            {"input": "hello", "expected_output": "world"},
        ]
        mock_repos["call_llm"].return_value = _make_llm_response("different")

        # check1 fails (score 0), check2 passes (score 0.9)
        mock_compare1 = AsyncMock(return_value=(0.0, False, {}))
        mock_compare2 = AsyncMock(return_value=(0.9, True, {}))

        with (
            patch("src.comparers.string_check_grader.StringCheckGraderComparer") as MockGrader,
        ):
            call_count = {"n": 0}
            def make_grader(cfg):
                call_count["n"] += 1
                m = MagicMock()
                m.grader_name = cfg.get("name", "")
                if call_count["n"] == 1:
                    m.compare = mock_compare1
                else:
                    m.compare = mock_compare2
                return m
            MockGrader.side_effect = make_grader
            await run_evaluation("run1")

        results = mock_repos["result_repo"].create_batch.call_args[0][0]
        r = results[0]
        # check1 weight=0 → excluded from score and pass/fail
        assert r.comparer_score == pytest.approx(0.9, abs=1e-4)
        assert r.passed is True  # Only check2 matters
        # Weight is recorded in details
        assert r.comparer_details["check1"]["weight"] == 0
        assert r.comparer_details["check2"]["weight"] == 1.0

    async def test_all_weights_zero_gives_zero_score_and_fail(self, mock_repos):
        """If all graders have weight=0, score=0 and passed=False."""
        config = _make_config(graders=[
            {"type": "string_check", "name": "check1", "weight": 0, "input_value": "{{ sample.output_text }}", "operation": "equals", "reference_value": "hello"},
        ])
        mock_repos["run_repo"].get_by_id = AsyncMock(return_value=_make_run())
        mock_repos["config_repo"].get_by_id = AsyncMock(return_value=config)
        mock_repos["dataset_repo"].get_by_id = AsyncMock(return_value=_make_dataset())
        mock_repos["read_csv"].return_value = [
            {"input": "hello", "expected_output": "hello"},
        ]
        mock_repos["call_llm"].return_value = _make_llm_response("hello")

        await run_evaluation("run1")

        results = mock_repos["result_repo"].create_batch.call_args[0][0]
        r = results[0]
        assert r.comparer_score == 0.0
        assert r.passed is False
