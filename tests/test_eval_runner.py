"""Tests for eval_runner — latency tracking and parallelization correctness."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.providers.base import LLMResponse
from src.services.eval_runner import run_evaluation


def _make_config(concurrency: int = 3) -> MagicMock:
    """Create a fake EvalConfig."""
    config = MagicMock()
    config.system_prompt = "You are a test assistant."
    config.model = "gpt-4.1"
    config.temperature = 0.7
    config.max_tokens = None
    config.tools = []
    config.tool_options = {}
    config.comparer_type = "exact_match"
    config.comparer_config = {}
    config.custom_graders = []
    config.comparer_weights = {}
    config.concurrency = concurrency
    config.reasoning_config = None
    config.response_format = None
    return config


def _make_run(run_id: str = "run1", config_id: str = "cfg1", dataset_id: str = "ds1") -> MagicMock:
    """Create a fake EvalRun."""
    run = MagicMock()
    run.id = run_id
    run.eval_config_id = config_id
    run.dataset_id = dataset_id
    return run


def _make_dataset() -> MagicMock:
    """Create a fake Dataset."""
    ds = MagicMock()
    ds.file_path = "/fake/data.csv"
    return ds


def _make_llm_response(text: str, latency_ms: int) -> LLMResponse:
    """Create a fake LLMResponse with a specific latency value."""
    return LLMResponse(
        text=text,
        latency_ms=latency_ms,
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
        # Set up the async session context manager
        session_mock = AsyncMock()
        ctx = AsyncMock()
        ctx.__aenter__.return_value = session_mock
        mock_session_ctx.return_value = ctx

        # Set up repo instances
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


class TestLatencyPerRow:
    """Each row should get its own latency_ms from the LLM call."""

    async def test_latency_recorded_per_row(self, mock_repos):
        """Each result should carry the latency value returned by the provider."""
        config = _make_config(concurrency=5)
        mock_repos["run_repo"].get_by_id = AsyncMock(return_value=_make_run())
        mock_repos["config_repo"].get_by_id = AsyncMock(return_value=config)
        mock_repos["dataset_repo"].get_by_id = AsyncMock(return_value=_make_dataset())
        mock_repos["read_csv"].return_value = [
            {"input": "q1", "expected_output": "a1"},
            {"input": "q2", "expected_output": "a2"},
            {"input": "q3", "expected_output": "a3"},
        ]

        # Return different latencies per call
        mock_repos["call_llm"].side_effect = [
            _make_llm_response("a1", latency_ms=100),
            _make_llm_response("a2", latency_ms=250),
            _make_llm_response("a3", latency_ms=50),
        ]

        await run_evaluation("run1")

        # Grab the results that were passed to create_batch
        create_batch_call = mock_repos["result_repo"].create_batch
        assert create_batch_call.called
        results = create_batch_call.call_args[0][0]

        latencies = sorted([r.latency_ms for r in results], key=lambda x: x or 0)
        assert latencies == [50, 100, 250]

    async def test_avg_latency_in_summary(self, mock_repos):
        """The summary's avg_latency_ms should be the mean of individual latencies."""
        config = _make_config(concurrency=5)
        mock_repos["run_repo"].get_by_id = AsyncMock(return_value=_make_run())
        mock_repos["config_repo"].get_by_id = AsyncMock(return_value=config)
        mock_repos["dataset_repo"].get_by_id = AsyncMock(return_value=_make_dataset())
        mock_repos["read_csv"].return_value = [
            {"input": "q1", "expected_output": "a1"},
            {"input": "q2", "expected_output": "a2"},
        ]

        mock_repos["call_llm"].side_effect = [
            _make_llm_response("a1", latency_ms=100),
            _make_llm_response("a2", latency_ms=300),
        ]

        await run_evaluation("run1")

        summary_call = mock_repos["run_repo"].set_summary
        assert summary_call.called
        summary = summary_call.call_args[1]["summary"]
        assert summary["avg_latency_ms"] == 200  # (100 + 300) / 2

    async def test_error_row_no_latency(self, mock_repos):
        """Rows that error out should have None latency and not inflate the average."""
        config = _make_config(concurrency=5)
        mock_repos["run_repo"].get_by_id = AsyncMock(return_value=_make_run())
        mock_repos["config_repo"].get_by_id = AsyncMock(return_value=config)
        mock_repos["dataset_repo"].get_by_id = AsyncMock(return_value=_make_dataset())
        mock_repos["read_csv"].return_value = [
            {"input": "q1", "expected_output": "a1"},
            {"input": "q2", "expected_output": "a2"},
        ]

        mock_repos["call_llm"].side_effect = [
            _make_llm_response("a1", latency_ms=200),
            Exception("API error"),
        ]

        await run_evaluation("run1")

        results = mock_repos["result_repo"].create_batch.call_args[0][0]
        successful = [r for r in results if r.error is None]
        errored = [r for r in results if r.error is not None]

        assert len(successful) == 1
        assert successful[0].latency_ms == 200
        assert len(errored) == 1
        assert errored[0].latency_ms is None

        summary = mock_repos["run_repo"].set_summary.call_args[1]["summary"]
        # avg_latency_ms = sum of latencies of all valid results / total results
        # 200 / 2 = 100 (both count toward total)
        assert summary["avg_latency_ms"] == 100


class TestConcurrency:
    """Verify that the semaphore enforces concurrency limits."""

    async def test_concurrency_limit_respected(self, mock_repos):
        """At most `concurrency` LLM calls should run simultaneously."""
        concurrency_limit = 2
        config = _make_config(concurrency=concurrency_limit)
        mock_repos["run_repo"].get_by_id = AsyncMock(return_value=_make_run())
        mock_repos["config_repo"].get_by_id = AsyncMock(return_value=config)
        mock_repos["dataset_repo"].get_by_id = AsyncMock(return_value=_make_dataset())
        mock_repos["read_csv"].return_value = [
            {"input": f"q{i}", "expected_output": f"a{i}"} for i in range(6)
        ]

        max_concurrent = 0
        current_concurrent = 0
        lock = asyncio.Lock()

        original_side_effects = []

        async def tracked_llm(**kwargs):
            nonlocal max_concurrent, current_concurrent
            async with lock:
                current_concurrent += 1
                if current_concurrent > max_concurrent:
                    max_concurrent = current_concurrent
            try:
                await asyncio.sleep(0.05)  # Simulate API latency
                return _make_llm_response(kwargs.get("user_input", ""), latency_ms=50)
            finally:
                async with lock:
                    current_concurrent -= 1

        mock_repos["call_llm"].side_effect = tracked_llm

        await run_evaluation("run1")

        assert max_concurrent <= concurrency_limit, (
            f"Max concurrent was {max_concurrent}, expected <= {concurrency_limit}"
        )
        assert mock_repos["call_llm"].call_count == 6

    async def test_all_rows_processed_despite_concurrency(self, mock_repos):
        """All rows should be processed even with limited concurrency."""
        config = _make_config(concurrency=1)  # Serial execution
        mock_repos["run_repo"].get_by_id = AsyncMock(return_value=_make_run())
        mock_repos["config_repo"].get_by_id = AsyncMock(return_value=config)
        mock_repos["dataset_repo"].get_by_id = AsyncMock(return_value=_make_dataset())

        num_rows = 5
        mock_repos["read_csv"].return_value = [
            {"input": f"q{i}", "expected_output": f"a{i}"} for i in range(num_rows)
        ]

        async def quick_llm(**kwargs):
            return _make_llm_response("answer", latency_ms=10)

        mock_repos["call_llm"].side_effect = quick_llm

        await run_evaluation("run1")

        results = mock_repos["result_repo"].create_batch.call_args[0][0]
        assert len(results) == num_rows


class TestLatencyMeasuresOnlyApiCall:
    """Latency should measure just the LLM API call, not semaphore wait time."""

    async def test_latency_excludes_queue_wait(self, mock_repos):
        """With concurrency=1, rows queued behind others should not include
        queue wait time in their latency — only the actual API call duration."""
        config = _make_config(concurrency=1)
        mock_repos["run_repo"].get_by_id = AsyncMock(return_value=_make_run())
        mock_repos["config_repo"].get_by_id = AsyncMock(return_value=config)
        mock_repos["dataset_repo"].get_by_id = AsyncMock(return_value=_make_dataset())
        mock_repos["read_csv"].return_value = [
            {"input": "q1", "expected_output": "a1"},
            {"input": "q2", "expected_output": "a2"},
        ]

        # Each call returns a fixed latency from the provider
        # (provider measures its own time, not queue time)
        mock_repos["call_llm"].side_effect = [
            _make_llm_response("a1", latency_ms=100),
            _make_llm_response("a2", latency_ms=100),
        ]

        await run_evaluation("run1")

        results = mock_repos["result_repo"].create_batch.call_args[0][0]
        for r in results:
            # Each result should have exactly the latency from the provider,
            # not the cumulative time including queue wait
            assert r.latency_ms == 100


class TestFileSearchToolPassed:
    """Verify that tools and tool_options are forwarded to the LLM call."""

    async def test_file_search_forwarded(self, mock_repos):
        """When config has file_search tool, it should be passed to call_llm."""
        config = _make_config(concurrency=5)
        config.tools = ["file_search"]
        config.tool_options = {"vector_store_id": "vs_abc123"}

        mock_repos["run_repo"].get_by_id = AsyncMock(return_value=_make_run())
        mock_repos["config_repo"].get_by_id = AsyncMock(return_value=config)
        mock_repos["dataset_repo"].get_by_id = AsyncMock(return_value=_make_dataset())
        mock_repos["read_csv"].return_value = [
            {"input": "What is X?", "expected_output": "X is Y"},
        ]

        mock_repos["call_llm"].return_value = _make_llm_response("X is Y", latency_ms=150)

        await run_evaluation("run1")

        call_kwargs = mock_repos["call_llm"].call_args[1]
        assert call_kwargs["tools"] == ["file_search"]
        assert call_kwargs["tool_options"] == {"vector_store_id": "vs_abc123"}

    async def test_no_tools_forwarded(self, mock_repos):
        """When config has no tools, empty list should be passed."""
        config = _make_config(concurrency=5)
        config.tools = []
        config.tool_options = {}

        mock_repos["run_repo"].get_by_id = AsyncMock(return_value=_make_run())
        mock_repos["config_repo"].get_by_id = AsyncMock(return_value=config)
        mock_repos["dataset_repo"].get_by_id = AsyncMock(return_value=_make_dataset())
        mock_repos["read_csv"].return_value = [
            {"input": "Hello", "expected_output": "Hi"},
        ]

        mock_repos["call_llm"].return_value = _make_llm_response("Hi", latency_ms=50)

        await run_evaluation("run1")

        call_kwargs = mock_repos["call_llm"].call_args[1]
        assert call_kwargs["tools"] == []
        assert call_kwargs["tool_options"] == {}


class TestRunCompletion:
    """Verify run status transitions and summary generation."""

    async def test_run_marked_completed(self, mock_repos):
        """After processing, run should be marked as completed."""
        config = _make_config(concurrency=5)
        mock_repos["run_repo"].get_by_id = AsyncMock(return_value=_make_run())
        mock_repos["config_repo"].get_by_id = AsyncMock(return_value=config)
        mock_repos["dataset_repo"].get_by_id = AsyncMock(return_value=_make_dataset())
        mock_repos["read_csv"].return_value = [
            {"input": "q1", "expected_output": "a1"},
        ]

        mock_repos["call_llm"].return_value = _make_llm_response("a1", latency_ms=50)

        await run_evaluation("run1")

        # Should have been called with status="completed"
        status_calls = mock_repos["run_repo"].update_status.call_args_list
        final_call = status_calls[-1]
        assert final_call[1]["status"] == "completed"

    async def test_missing_run_exits_early(self, mock_repos):
        """If the run doesn't exist, the function should exit without error."""
        mock_repos["run_repo"].get_by_id = AsyncMock(return_value=None)

        await run_evaluation("nonexistent")

        # Should not have called any further repo methods
        mock_repos["config_repo"].get_by_id.assert_not_called()


class TestGraderStats:
    """Verify per-grader statistics are computed in the run summary."""

    async def test_grader_stats_with_multiple_comparers(self, mock_repos):
        """Summary should include per-grader pass counts and avg_score."""
        config = _make_config(concurrency=5)
        config.comparer_type = "exact_match,pattern_match"

        mock_repos["run_repo"].get_by_id = AsyncMock(return_value=_make_run())
        mock_repos["config_repo"].get_by_id = AsyncMock(return_value=config)
        mock_repos["dataset_repo"].get_by_id = AsyncMock(return_value=_make_dataset())
        mock_repos["read_csv"].return_value = [
            {"input": "q1", "expected_output": "a1"},
            {"input": "q2", "expected_output": "a2"},
            {"input": "q3", "expected_output": "a3"},
        ]

        mock_repos["call_llm"].side_effect = [
            _make_llm_response("a1", latency_ms=50),
            _make_llm_response("wrong", latency_ms=50),
            _make_llm_response("a3", latency_ms=50),
        ]

        await run_evaluation("run1")

        summary = mock_repos["run_repo"].set_summary.call_args[1]["summary"]
        assert "grader_stats" in summary

        grader_stats = summary["grader_stats"]
        # Both comparers should be present
        assert "exact_match" in grader_stats
        assert "pattern_match" in grader_stats

        # Each grader stat should have the expected fields
        for name, stats in grader_stats.items():
            assert "total" in stats
            assert "passed" in stats
            assert "failed" in stats
            assert "accuracy" in stats
            assert "avg_score" in stats
            assert stats["total"] == 3
            assert stats["passed"] + stats["failed"] == stats["total"]

    async def test_grader_stats_single_comparer(self, mock_repos):
        """With a single comparer, grader_stats should still be populated."""
        config = _make_config(concurrency=5)
        config.comparer_type = "exact_match"

        mock_repos["run_repo"].get_by_id = AsyncMock(return_value=_make_run())
        mock_repos["config_repo"].get_by_id = AsyncMock(return_value=config)
        mock_repos["dataset_repo"].get_by_id = AsyncMock(return_value=_make_dataset())
        mock_repos["read_csv"].return_value = [
            {"input": "q1", "expected_output": "a1"},
            {"input": "q2", "expected_output": "a2"},
        ]

        mock_repos["call_llm"].side_effect = [
            _make_llm_response("a1", latency_ms=50),
            _make_llm_response("wrong", latency_ms=50),
        ]

        await run_evaluation("run1")

        summary = mock_repos["run_repo"].set_summary.call_args[1]["summary"]
        grader_stats = summary["grader_stats"]
        assert "exact_match" in grader_stats
        assert grader_stats["exact_match"]["total"] == 2
        assert grader_stats["exact_match"]["passed"] == 1
        assert grader_stats["exact_match"]["failed"] == 1
        assert grader_stats["exact_match"]["accuracy"] == 0.5
