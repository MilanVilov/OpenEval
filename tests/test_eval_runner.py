"""Tests for eval_runner — latency, durability, and completion behavior."""

import asyncio
from datetime import datetime
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
    config.graders = [{
        "type": "string_check",
        "name": "exact",
        "input_value": "{{ sample.output_text }}",
        "operation": "equals",
        "reference_value": "{{ item.expected_output }}",
    }]
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
    dataset = MagicMock()
    dataset.file_path = "/fake/data.csv"
    return dataset


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
    """Patch all repository classes and the session context."""
    with (
        patch("src.services.eval_runner.get_session_context") as mock_session_ctx,
        patch("src.services.eval_runner.RunRepository") as mock_run_repo_cls,
        patch("src.services.eval_runner.ConfigRepository") as mock_config_repo_cls,
        patch("src.services.eval_runner.DatasetRepository") as mock_dataset_repo_cls,
        patch("src.services.eval_runner.ResultRepository") as mock_result_repo_cls,
        patch("src.services.eval_runner.read_dataset_rows") as mock_read_csv,
        patch("src.services.eval_runner.call_llm") as mock_call_llm,
    ):
        session_mock = AsyncMock()
        session_context = AsyncMock()
        session_context.__aenter__.return_value = session_mock
        mock_session_ctx.return_value = session_context

        run_repo = mock_run_repo_cls.return_value
        config_repo = mock_config_repo_cls.return_value
        dataset_repo = mock_dataset_repo_cls.return_value
        result_repo = mock_result_repo_cls.return_value

        run_repo.update_status = AsyncMock()
        run_repo.update_progress = AsyncMock()
        run_repo.update_heartbeat = AsyncMock()
        run_repo.set_summary = AsyncMock()
        result_repo.create_batch = AsyncMock()
        result_repo.upsert_batch = AsyncMock()

        yield {
            "run_repo": run_repo,
            "config_repo": config_repo,
            "dataset_repo": dataset_repo,
            "result_repo": result_repo,
            "read_csv": mock_read_csv,
            "call_llm": mock_call_llm,
        }


class TestLatencyPerRow:
    """Each row should carry provider latency through persistence and summary."""

    async def test_latency_recorded_per_row(self, mock_repos):
        """Each persisted result should keep its provider latency."""
        config = _make_config(concurrency=5)
        mock_repos["run_repo"].get_by_id = AsyncMock(return_value=_make_run())
        mock_repos["config_repo"].get_by_id = AsyncMock(return_value=config)
        mock_repos["dataset_repo"].get_by_id_with_content = AsyncMock(return_value=_make_dataset())
        mock_repos["read_csv"].return_value = [
            {"input": "q1", "expected_output": "a1"},
            {"input": "q2", "expected_output": "a2"},
            {"input": "q3", "expected_output": "a3"},
        ]
        mock_repos["call_llm"].side_effect = [
            _make_llm_response("a1", latency_ms=100),
            _make_llm_response("a2", latency_ms=250),
            _make_llm_response("a3", latency_ms=50),
        ]

        await run_evaluation("run1")

        persisted_results = [
            call.args[0][0]
            for call in mock_repos["result_repo"].upsert_batch.await_args_list
        ]
        latencies = sorted(result.latency_ms for result in persisted_results)
        assert latencies == [50, 100, 250]

    async def test_avg_latency_in_summary(self, mock_repos):
        """Summary latency should be the mean across all processed rows."""
        config = _make_config(concurrency=5)
        mock_repos["run_repo"].get_by_id = AsyncMock(return_value=_make_run())
        mock_repos["config_repo"].get_by_id = AsyncMock(return_value=config)
        mock_repos["dataset_repo"].get_by_id_with_content = AsyncMock(return_value=_make_dataset())
        mock_repos["read_csv"].return_value = [
            {"input": "q1", "expected_output": "a1"},
            {"input": "q2", "expected_output": "a2"},
        ]
        mock_repos["call_llm"].side_effect = [
            _make_llm_response("a1", latency_ms=100),
            _make_llm_response("a2", latency_ms=300),
        ]

        await run_evaluation("run1")

        summary = mock_repos["run_repo"].set_summary.call_args.kwargs["summary"]
        assert summary["avg_latency_ms"] == 200

    async def test_error_row_no_latency(self, mock_repos):
        """Errored rows should keep a null latency and lower the average accordingly."""
        config = _make_config(concurrency=5)
        mock_repos["run_repo"].get_by_id = AsyncMock(return_value=_make_run())
        mock_repos["config_repo"].get_by_id = AsyncMock(return_value=config)
        mock_repos["dataset_repo"].get_by_id_with_content = AsyncMock(return_value=_make_dataset())
        mock_repos["read_csv"].return_value = [
            {"input": "q1", "expected_output": "a1"},
            {"input": "q2", "expected_output": "a2"},
        ]
        mock_repos["call_llm"].side_effect = [
            _make_llm_response("a1", latency_ms=200),
            Exception("API error"),
        ]

        await run_evaluation("run1")

        persisted_results = [
            call.args[0][0]
            for call in mock_repos["result_repo"].upsert_batch.await_args_list
        ]
        successful = [result for result in persisted_results if result.error is None]
        errored = [result for result in persisted_results if result.error is not None]

        assert len(successful) == 1
        assert successful[0].latency_ms == 200
        assert len(errored) == 1
        assert errored[0].latency_ms is None

        summary = mock_repos["run_repo"].set_summary.call_args.kwargs["summary"]
        assert summary["avg_latency_ms"] == 100


class TestConcurrency:
    """Verify that the semaphore enforces concurrency limits."""

    async def test_concurrency_limit_respected(self, mock_repos):
        """At most ``concurrency`` provider calls should run simultaneously."""
        config = _make_config(concurrency=2)
        mock_repos["run_repo"].get_by_id = AsyncMock(return_value=_make_run())
        mock_repos["config_repo"].get_by_id = AsyncMock(return_value=config)
        mock_repos["dataset_repo"].get_by_id_with_content = AsyncMock(return_value=_make_dataset())
        mock_repos["read_csv"].return_value = [
            {"input": f"q{i}", "expected_output": f"a{i}"} for i in range(6)
        ]

        current_concurrent = 0
        max_concurrent = 0
        lock = asyncio.Lock()

        async def tracked_llm(**kwargs):
            nonlocal current_concurrent, max_concurrent
            async with lock:
                current_concurrent += 1
                max_concurrent = max(max_concurrent, current_concurrent)
            try:
                await asyncio.sleep(0.05)
                return _make_llm_response(kwargs["user_input"], latency_ms=50)
            finally:
                async with lock:
                    current_concurrent -= 1

        mock_repos["call_llm"].side_effect = tracked_llm

        await run_evaluation("run1")

        assert max_concurrent <= 2
        assert mock_repos["call_llm"].call_count == 6

    async def test_all_rows_processed_despite_concurrency(self, mock_repos):
        """Every dataset row should eventually be persisted."""
        config = _make_config(concurrency=1)
        mock_repos["run_repo"].get_by_id = AsyncMock(return_value=_make_run())
        mock_repos["config_repo"].get_by_id = AsyncMock(return_value=config)
        mock_repos["dataset_repo"].get_by_id_with_content = AsyncMock(return_value=_make_dataset())
        mock_repos["read_csv"].return_value = [
            {"input": f"q{i}", "expected_output": f"a{i}"} for i in range(5)
        ]
        mock_repos["call_llm"].side_effect = lambda **kwargs: _make_llm_response("answer", 10)

        await run_evaluation("run1")

        assert mock_repos["result_repo"].upsert_batch.await_count == 5


class TestLatencyMeasuresOnlyApiCall:
    """Latency should measure just the provider call, not queue wait time."""

    async def test_latency_excludes_queue_wait(self, mock_repos):
        """Queued rows should preserve provider latency, not cumulative wait."""
        config = _make_config(concurrency=1)
        mock_repos["run_repo"].get_by_id = AsyncMock(return_value=_make_run())
        mock_repos["config_repo"].get_by_id = AsyncMock(return_value=config)
        mock_repos["dataset_repo"].get_by_id_with_content = AsyncMock(return_value=_make_dataset())
        mock_repos["read_csv"].return_value = [
            {"input": "q1", "expected_output": "a1"},
            {"input": "q2", "expected_output": "a2"},
        ]
        mock_repos["call_llm"].side_effect = [
            _make_llm_response("a1", latency_ms=100),
            _make_llm_response("a2", latency_ms=100),
        ]

        await run_evaluation("run1")

        persisted_results = [
            call.args[0][0]
            for call in mock_repos["result_repo"].upsert_batch.await_args_list
        ]
        assert all(result.latency_ms == 100 for result in persisted_results)


class TestFileSearchToolPassed:
    """Verify that tools and tool_options are forwarded to the LLM call."""

    async def test_file_search_forwarded(self, mock_repos):
        """Configured tools should be forwarded to the provider call."""
        config = _make_config(concurrency=5)
        config.tools = ["file_search"]
        config.tool_options = {"vector_store_id": "vs_abc123"}
        mock_repos["run_repo"].get_by_id = AsyncMock(return_value=_make_run())
        mock_repos["config_repo"].get_by_id = AsyncMock(return_value=config)
        mock_repos["dataset_repo"].get_by_id_with_content = AsyncMock(return_value=_make_dataset())
        mock_repos["read_csv"].return_value = [{"input": "What is X?", "expected_output": "X is Y"}]
        mock_repos["call_llm"].return_value = _make_llm_response("X is Y", latency_ms=150)

        await run_evaluation("run1")

        call_kwargs = mock_repos["call_llm"].call_args.kwargs
        assert call_kwargs["tools"] == ["file_search"]
        assert call_kwargs["tool_options"] == {"vector_store_id": "vs_abc123"}

    async def test_no_tools_forwarded(self, mock_repos):
        """Runs without tools should still pass the default empty values."""
        config = _make_config(concurrency=5)
        mock_repos["run_repo"].get_by_id = AsyncMock(return_value=_make_run())
        mock_repos["config_repo"].get_by_id = AsyncMock(return_value=config)
        mock_repos["dataset_repo"].get_by_id_with_content = AsyncMock(return_value=_make_dataset())
        mock_repos["read_csv"].return_value = [{"input": "Hello", "expected_output": "Hi"}]
        mock_repos["call_llm"].return_value = _make_llm_response("Hi", latency_ms=50)

        await run_evaluation("run1")

        call_kwargs = mock_repos["call_llm"].call_args.kwargs
        assert call_kwargs["tools"] == []
        assert call_kwargs["tool_options"] == {}


class TestRunCompletion:
    """Verify run status transitions and failure reporting."""

    async def test_run_marked_completed(self, mock_repos):
        """Successful runs should end in ``completed``."""
        config = _make_config(concurrency=5)
        mock_repos["run_repo"].get_by_id = AsyncMock(return_value=_make_run())
        mock_repos["config_repo"].get_by_id = AsyncMock(return_value=config)
        mock_repos["dataset_repo"].get_by_id_with_content = AsyncMock(return_value=_make_dataset())
        mock_repos["read_csv"].return_value = [{"input": "q1", "expected_output": "a1"}]
        mock_repos["call_llm"].return_value = _make_llm_response("a1", latency_ms=50)

        await run_evaluation("run1")

        final_call = mock_repos["run_repo"].update_status.call_args_list[-1]
        assert final_call.kwargs["status"] == "completed"

    async def test_missing_run_exits_early(self, mock_repos):
        """A missing run should exit without further work."""
        mock_repos["run_repo"].get_by_id = AsyncMock(return_value=None)

        await run_evaluation("missing")

        mock_repos["config_repo"].get_by_id.assert_not_called()

    async def test_missing_config_or_dataset_marks_failed(self, mock_repos):
        """Missing dependencies should produce a terminal failed run."""
        mock_repos["run_repo"].get_by_id = AsyncMock(return_value=_make_run())
        mock_repos["config_repo"].get_by_id = AsyncMock(return_value=None)
        mock_repos["dataset_repo"].get_by_id_with_content = AsyncMock(return_value=_make_dataset())

        await run_evaluation("run1")

        final_call = mock_repos["run_repo"].update_status.call_args_list[-1]
        assert final_call.kwargs["status"] == "failed"
        assert isinstance(final_call.kwargs["completed_at"], datetime)

    async def test_dataset_read_error_marks_failed(self, mock_repos):
        """Dataset read failures should surface a run-level error message."""
        config = _make_config(concurrency=5)
        mock_repos["run_repo"].get_by_id = AsyncMock(return_value=_make_run())
        mock_repos["config_repo"].get_by_id = AsyncMock(return_value=config)
        mock_repos["dataset_repo"].get_by_id_with_content = AsyncMock(return_value=_make_dataset())
        mock_repos["read_csv"].side_effect = RuntimeError("bad csv")

        await run_evaluation("run1")

        final_call = mock_repos["run_repo"].update_status.call_args_list[-1]
        assert final_call.kwargs["status"] == "failed"
        assert final_call.kwargs["error_message"] == "Failed to read dataset: RuntimeError: bad csv"
        assert isinstance(final_call.kwargs["completed_at"], datetime)

    async def test_unexpected_finalization_error_marks_run_failed(self, mock_repos):
        """Unhandled persistence errors should not leave the run active."""
        config = _make_config(concurrency=5)
        mock_repos["run_repo"].get_by_id = AsyncMock(return_value=_make_run())
        mock_repos["config_repo"].get_by_id = AsyncMock(return_value=config)
        mock_repos["dataset_repo"].get_by_id_with_content = AsyncMock(return_value=_make_dataset())
        mock_repos["read_csv"].return_value = [{"input": "q1", "expected_output": "a1"}]
        mock_repos["call_llm"].return_value = _make_llm_response("a1", latency_ms=50)
        mock_repos["result_repo"].upsert_batch.side_effect = RuntimeError("DB write failed")

        await run_evaluation("run1")

        final_call = mock_repos["run_repo"].update_status.call_args_list[-1]
        assert final_call.kwargs["status"] == "failed"
        assert final_call.kwargs["error_message"] == (
            "Run failed during evaluation: RuntimeError: DB write failed"
        )


class TestProgressTracking:
    """Verify progress only advances after durable row completion."""

    async def test_progress_waits_for_grading_completion(self, mock_repos):
        """Rows should not count as complete until grading has finished."""
        config = _make_config(concurrency=2)
        config.graders = [{"type": "prompt", "name": "judge", "prompt": "grade this"}]
        mock_repos["run_repo"].get_by_id = AsyncMock(return_value=_make_run())
        mock_repos["config_repo"].get_by_id = AsyncMock(return_value=config)
        mock_repos["dataset_repo"].get_by_id_with_content = AsyncMock(return_value=_make_dataset())
        mock_repos["read_csv"].return_value = [
            {"input": "q1", "expected_output": "a1"},
            {"input": "q2", "expected_output": "a2"},
        ]
        mock_repos["call_llm"].side_effect = [
            _make_llm_response("a1", latency_ms=50),
            _make_llm_response("a2", latency_ms=50),
        ]
        grader_gate = asyncio.Event()

        async def blocked_compare(self, *, expected, actual, row_data=None):
            await grader_gate.wait()
            return 1.0, True, {"reasoning": "ok"}

        with patch(
            "src.comparers.custom_grader.CustomGraderComparer.compare",
            new=blocked_compare,
        ):
            task = asyncio.create_task(run_evaluation("run1"))
            await asyncio.sleep(0.05)
            assert mock_repos["run_repo"].update_progress.await_count == 0

            grader_gate.set()
            await task

        progress_calls = mock_repos["run_repo"].update_progress.call_args_list
        assert [call.kwargs["progress"] for call in progress_calls] == [1, 2]

    async def test_progress_waits_for_result_persistence(self, mock_repos):
        """Progress should not advance before the result upsert finishes."""
        config = _make_config(concurrency=1)
        mock_repos["run_repo"].get_by_id = AsyncMock(return_value=_make_run())
        mock_repos["config_repo"].get_by_id = AsyncMock(return_value=config)
        mock_repos["dataset_repo"].get_by_id_with_content = AsyncMock(return_value=_make_dataset())
        mock_repos["read_csv"].return_value = [{"input": "q1", "expected_output": "a1"}]
        mock_repos["call_llm"].return_value = _make_llm_response("a1", latency_ms=50)
        persist_gate = asyncio.Event()

        async def blocked_upsert(results):
            await persist_gate.wait()

        mock_repos["result_repo"].upsert_batch.side_effect = blocked_upsert

        task = asyncio.create_task(run_evaluation("run1"))
        await asyncio.sleep(0.05)
        assert mock_repos["run_repo"].update_progress.await_count == 0

        persist_gate.set()
        await task

        assert mock_repos["run_repo"].update_progress.await_count == 1


class TestGraderStats:
    """Verify per-grader statistics in the final summary."""

    async def test_grader_stats_with_multiple_comparers(self, mock_repos):
        """Summary should include pass counts and average score per grader."""
        config = _make_config(concurrency=5)
        config.graders = [
            {
                "type": "string_check",
                "name": "check1",
                "input_value": "{{ sample.output_text }}",
                "operation": "equals",
                "reference_value": "{{ item.expected_output }}",
            },
            {
                "type": "string_check",
                "name": "check2",
                "input_value": "{{ sample.output_text }}",
                "operation": "contains",
                "reference_value": "{{ item.expected_output }}",
            },
        ]
        mock_repos["run_repo"].get_by_id = AsyncMock(return_value=_make_run())
        mock_repos["config_repo"].get_by_id = AsyncMock(return_value=config)
        mock_repos["dataset_repo"].get_by_id_with_content = AsyncMock(return_value=_make_dataset())
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

        summary = mock_repos["run_repo"].set_summary.call_args.kwargs["summary"]
        grader_stats = summary["grader_stats"]

        assert "check1" in grader_stats
        assert "check2" in grader_stats
        for _name, stats in grader_stats.items():
            assert stats["total"] == 3
            assert stats["passed"] + stats["failed"] == stats["total"]
            assert "accuracy" in stats
            assert "avg_score" in stats

    async def test_grader_stats_single_comparer(self, mock_repos):
        """Single-grader runs should still emit grader_stats."""
        config = _make_config(concurrency=5)
        mock_repos["run_repo"].get_by_id = AsyncMock(return_value=_make_run())
        mock_repos["config_repo"].get_by_id = AsyncMock(return_value=config)
        mock_repos["dataset_repo"].get_by_id_with_content = AsyncMock(return_value=_make_dataset())
        mock_repos["read_csv"].return_value = [
            {"input": "q1", "expected_output": "a1"},
            {"input": "q2", "expected_output": "a2"},
        ]
        mock_repos["call_llm"].side_effect = [
            _make_llm_response("a1", latency_ms=50),
            _make_llm_response("wrong", latency_ms=50),
        ]

        await run_evaluation("run1")

        summary = mock_repos["run_repo"].set_summary.call_args.kwargs["summary"]
        grader_stats = summary["grader_stats"]
        assert grader_stats["exact"]["total"] == 2
        assert grader_stats["exact"]["passed"] == 1
        assert grader_stats["exact"]["failed"] == 1
        assert grader_stats["exact"]["accuracy"] == 0.5
