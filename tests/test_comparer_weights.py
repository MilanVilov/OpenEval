"""Tests for comparer_weights — weighted mean scoring and pass/fail logic."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.providers.base import LLMResponse
from src.services.eval_runner import run_evaluation


def _make_config(
    comparer_type: str = "exact_match",
    comparer_weights: dict | None = None,
    custom_graders: list | None = None,
) -> MagicMock:
    """Create a fake EvalConfig with optional weights."""
    config = MagicMock()
    config.system_prompt = "You are a test assistant."
    config.model = "gpt-4.1"
    config.temperature = 0.7
    config.max_tokens = None
    config.tools = []
    config.tool_options = {}
    config.comparer_type = comparer_type
    config.comparer_config = {}
    config.custom_graders = custom_graders or []
    config.comparer_weights = comparer_weights or {}
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


class TestComparerWeights:
    """Weighted mean scoring and pass/fail with comparer_weights."""

    async def test_no_weights_is_simple_average(self, mock_repos):
        """Without comparer_weights, behaviour equals simple average (backward compat)."""
        config = _make_config(comparer_type="exact_match,semantic_similarity")
        mock_repos["run_repo"].get_by_id = AsyncMock(return_value=_make_run())
        mock_repos["config_repo"].get_by_id = AsyncMock(return_value=config)
        mock_repos["dataset_repo"].get_by_id = AsyncMock(return_value=_make_dataset())
        mock_repos["read_csv"].return_value = [
            {"input": "hello", "expected_output": "hello"},
        ]
        mock_repos["call_llm"].return_value = _make_llm_response("hello")

        await run_evaluation("run1")

        results = mock_repos["result_repo"].create_batch.call_args[0][0]
        assert len(results) == 1
        r = results[0]
        # exact_match returns 1.0, semantic_similarity returns some score
        # Both have default weight 1.0 → simple average
        assert r.comparer_score is not None
        assert r.passed is not None
        # Weight stored in details
        for detail in r.comparer_details.values():
            assert detail.get("weight") == 1.0

    async def test_weighted_mean_calculation(self, mock_repos):
        """Weights alter the score average: w*s / sum(w)."""
        # Use two comparers; we'll mock them to return known scores.
        config = _make_config(
            comparer_type="exact_match,semantic_similarity",
            comparer_weights={"exact_match": 0.5, "semantic_similarity": 1.0},
        )
        mock_repos["run_repo"].get_by_id = AsyncMock(return_value=_make_run())
        mock_repos["config_repo"].get_by_id = AsyncMock(return_value=config)
        mock_repos["dataset_repo"].get_by_id = AsyncMock(return_value=_make_dataset())
        mock_repos["read_csv"].return_value = [
            {"input": "hello", "expected_output": "hello"},
        ]
        mock_repos["call_llm"].return_value = _make_llm_response("hello")

        # Mock comparers to return fixed scores
        mock_exact = AsyncMock(return_value=(1.0, True, {}))
        mock_semantic = AsyncMock(return_value=(0.8, True, {}))
        with patch("src.comparers.registry.get_comparer") as mock_get:
            def side_effect(name, cfg):
                m = MagicMock()
                if name == "exact_match":
                    m.compare = mock_exact
                else:
                    m.compare = mock_semantic
                return m
            mock_get.side_effect = side_effect
            await run_evaluation("run1")

        results = mock_repos["result_repo"].create_batch.call_args[0][0]
        r = results[0]
        # Weighted mean: (0.5*1.0 + 1.0*0.8) / (0.5 + 1.0) = 1.3/1.5 ≈ 0.8667
        expected_score = (0.5 * 1.0 + 1.0 * 0.8) / (0.5 + 1.0)
        assert r.comparer_score == pytest.approx(expected_score, abs=1e-4)
        assert r.passed is True

    async def test_weight_zero_excluded_from_pass_fail(self, mock_repos):
        """A grader with weight=0 is informational — its failure doesn't fail the result."""
        config = _make_config(
            comparer_type="exact_match,semantic_similarity",
            comparer_weights={"exact_match": 0, "semantic_similarity": 1.0},
        )
        mock_repos["run_repo"].get_by_id = AsyncMock(return_value=_make_run())
        mock_repos["config_repo"].get_by_id = AsyncMock(return_value=config)
        mock_repos["dataset_repo"].get_by_id = AsyncMock(return_value=_make_dataset())
        mock_repos["read_csv"].return_value = [
            {"input": "hello", "expected_output": "world"},
        ]
        mock_repos["call_llm"].return_value = _make_llm_response("different")

        # exact_match fails (score 0), semantic_similarity passes (score 0.9)
        mock_exact = AsyncMock(return_value=(0.0, False, {}))
        mock_semantic = AsyncMock(return_value=(0.9, True, {}))
        with patch("src.comparers.registry.get_comparer") as mock_get:
            def side_effect(name, cfg):
                m = MagicMock()
                if name == "exact_match":
                    m.compare = mock_exact
                else:
                    m.compare = mock_semantic
                return m
            mock_get.side_effect = side_effect
            await run_evaluation("run1")

        results = mock_repos["result_repo"].create_batch.call_args[0][0]
        r = results[0]
        # exact_match weight=0 → excluded from score and pass/fail
        assert r.comparer_score == pytest.approx(0.9, abs=1e-4)
        assert r.passed is True  # Only semantic_similarity matters
        # Weight is recorded in details
        assert r.comparer_details["exact_match"]["weight"] == 0
        assert r.comparer_details["semantic_similarity"]["weight"] == 1.0

    async def test_all_weights_zero_gives_zero_score_and_fail(self, mock_repos):
        """If all graders have weight=0, score=0 and passed=False."""
        config = _make_config(
            comparer_type="exact_match",
            comparer_weights={"exact_match": 0},
        )
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
