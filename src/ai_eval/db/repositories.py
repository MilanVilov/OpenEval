"""Repository (data-access) layer for ai-eval.

Each repository class owns reads and writes for a single entity.
All write operations commit and refresh within the method.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ai_eval.db.models import Container, Dataset, EvalConfig, EvalResult, EvalRun, VectorStore

# ---------------------------------------------------------------------------
# EvalConfig
# ---------------------------------------------------------------------------


class ConfigRepository:
    """Data-access helpers for :class:`EvalConfig`."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        name: str,
        system_prompt: str,
        model: str,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        tools: list | None = None,
        tool_options: dict | None = None,
        comparer_type: str,
        comparer_config: dict | None = None,
        concurrency: int = 5,
        reasoning_config: dict | None = None,
        response_format: dict | None = None,
    ) -> EvalConfig:
        """Insert a new evaluation configuration."""
        config = EvalConfig(
            name=name,
            system_prompt=system_prompt,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            tools=tools if tools is not None else [],
            tool_options=tool_options if tool_options is not None else {},
            comparer_type=comparer_type,
            comparer_config=comparer_config if comparer_config is not None else {},
            concurrency=concurrency,
            reasoning_config=reasoning_config,
            response_format=response_format,
        )
        self._session.add(config)
        await self._session.commit()
        await self._session.refresh(config)
        return config

    async def get_by_id(self, config_id: str) -> EvalConfig | None:
        """Return a config by primary key, or ``None``."""
        return await self._session.get(EvalConfig, config_id)

    async def list_all(self) -> list[EvalConfig]:
        """Return every config ordered by newest first."""
        stmt = select(EvalConfig).order_by(EvalConfig.created_at.desc())
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def update(self, config_id: str, **fields: object) -> EvalConfig | None:
        """Update arbitrary fields on a config. Returns ``None`` if not found."""
        config = await self.get_by_id(config_id)
        if config is None:
            return None
        for key, value in fields.items():
            setattr(config, key, value)
        await self._session.commit()
        await self._session.refresh(config)
        return config

    async def delete(self, config_id: str) -> bool:
        """Delete a config. Returns ``True`` if it existed."""
        config = await self.get_by_id(config_id)
        if config is None:
            return False
        await self._session.delete(config)
        await self._session.commit()
        return True


# ---------------------------------------------------------------------------
# Dataset
# ---------------------------------------------------------------------------


class DatasetRepository:
    """Data-access helpers for :class:`Dataset`."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        name: str,
        file_path: str,
        row_count: int,
        columns: list,
    ) -> Dataset:
        """Insert a new dataset record."""
        dataset = Dataset(
            name=name,
            file_path=file_path,
            row_count=row_count,
            columns=columns,
        )
        self._session.add(dataset)
        await self._session.commit()
        await self._session.refresh(dataset)
        return dataset

    async def get_by_id(self, dataset_id: str) -> Dataset | None:
        """Return a dataset by primary key, or ``None``."""
        return await self._session.get(Dataset, dataset_id)

    async def list_all(self) -> list[Dataset]:
        """Return every dataset ordered by newest first."""
        stmt = select(Dataset).order_by(Dataset.created_at.desc())
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def delete(self, dataset_id: str) -> bool:
        """Delete a dataset. Returns ``True`` if it existed."""
        dataset = await self.get_by_id(dataset_id)
        if dataset is None:
            return False
        await self._session.delete(dataset)
        await self._session.commit()
        return True


# ---------------------------------------------------------------------------
# VectorStore
# ---------------------------------------------------------------------------


class VectorStoreRepository:
    """Data-access helpers for :class:`VectorStore`."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        openai_vector_store_id: str,
        name: str,
        status: str = "creating",
    ) -> VectorStore:
        """Insert a new vector-store reference."""
        store = VectorStore(
            openai_vector_store_id=openai_vector_store_id,
            name=name,
            status=status,
        )
        self._session.add(store)
        await self._session.commit()
        await self._session.refresh(store)
        return store

    async def get_by_id(self, store_id: str) -> VectorStore | None:
        """Return a vector store by primary key, or ``None``."""
        return await self._session.get(VectorStore, store_id)

    async def list_all(self) -> list[VectorStore]:
        """Return every vector store ordered by newest first."""
        stmt = select(VectorStore).order_by(VectorStore.created_at.desc())
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def update(self, store_id: str, **fields: object) -> VectorStore | None:
        """Update arbitrary fields on a vector store. Returns ``None`` if not found."""
        store = await self.get_by_id(store_id)
        if store is None:
            return None
        for key, value in fields.items():
            setattr(store, key, value)
        await self._session.commit()
        await self._session.refresh(store)
        return store

    async def delete(self, store_id: str) -> bool:
        """Delete a vector store. Returns ``True`` if it existed."""
        store = await self.get_by_id(store_id)
        if store is None:
            return False
        await self._session.delete(store)
        await self._session.commit()
        return True


# ---------------------------------------------------------------------------
# Container
# ---------------------------------------------------------------------------


class ContainerRepository:
    """Data-access helpers for :class:`Container`."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        openai_container_id: str,
        name: str,
        status: str = "active",
    ) -> Container:
        """Insert a new container reference."""
        container = Container(
            openai_container_id=openai_container_id,
            name=name,
            status=status,
        )
        self._session.add(container)
        await self._session.commit()
        await self._session.refresh(container)
        return container

    async def get_by_id(self, container_id: str) -> Container | None:
        """Return a container by primary key, or ``None``."""
        return await self._session.get(Container, container_id)

    async def list_all(self) -> list[Container]:
        """Return every container ordered by newest first."""
        stmt = select(Container).order_by(Container.created_at.desc())
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def update(self, container_id: str, **fields: object) -> Container | None:
        """Update arbitrary fields on a container. Returns ``None`` if not found."""
        container = await self.get_by_id(container_id)
        if container is None:
            return None
        for key, value in fields.items():
            setattr(container, key, value)
        await self._session.commit()
        await self._session.refresh(container)
        return container

    async def delete(self, container_id: str) -> bool:
        """Delete a container. Returns ``True`` if it existed."""
        container = await self.get_by_id(container_id)
        if container is None:
            return False
        await self._session.delete(container)
        await self._session.commit()
        return True


# ---------------------------------------------------------------------------
# EvalRun
# ---------------------------------------------------------------------------


class RunRepository:
    """Data-access helpers for :class:`EvalRun`."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        eval_config_id: str,
        dataset_id: str,
        total_rows: int,
    ) -> EvalRun:
        """Insert a new evaluation run."""
        run = EvalRun(
            eval_config_id=eval_config_id,
            dataset_id=dataset_id,
            total_rows=total_rows,
        )
        self._session.add(run)
        await self._session.commit()
        await self._session.refresh(run)
        return run

    async def get_by_id(self, run_id: str) -> EvalRun | None:
        """Return a run by primary key with config and dataset eagerly loaded."""
        stmt = (
            select(EvalRun)
            .options(selectinload(EvalRun.config), selectinload(EvalRun.dataset))
            .where(EvalRun.id == run_id)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_all(self) -> list[EvalRun]:
        """Return every run ordered by newest first, with config and dataset loaded."""
        stmt = (
            select(EvalRun)
            .options(selectinload(EvalRun.config), selectinload(EvalRun.dataset))
            .order_by(EvalRun.created_at.desc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def list_recent(self, limit: int = 10) -> list[EvalRun]:
        """Return the most recent runs for the dashboard."""
        stmt = (
            select(EvalRun)
            .options(selectinload(EvalRun.config), selectinload(EvalRun.dataset))
            .order_by(EvalRun.created_at.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def update_status(self, run_id: str, *, status: str, **fields: object) -> EvalRun | None:
        """Set the run status and any extra fields. Returns ``None`` if not found."""
        run = await self._session.get(EvalRun, run_id)
        if run is None:
            return None
        run.status = status
        for key, value in fields.items():
            setattr(run, key, value)
        await self._session.commit()
        await self._session.refresh(run)
        return run

    async def update_progress(self, run_id: str, *, progress: int) -> None:
        """Bump the progress counter on a run."""
        run = await self._session.get(EvalRun, run_id)
        if run is None:
            return
        run.progress = progress
        await self._session.commit()

    async def set_summary(self, run_id: str, *, summary: dict) -> None:
        """Store the final summary JSON on a run."""
        run = await self._session.get(EvalRun, run_id)
        if run is None:
            return
        run.summary = summary
        await self._session.commit()

    async def delete(self, run_id: str) -> bool:
        """Delete a run. Returns ``True`` if it existed."""
        run = await self._session.get(EvalRun, run_id)
        if run is None:
            return False
        await self._session.delete(run)
        await self._session.commit()
        return True


# ---------------------------------------------------------------------------
# EvalResult
# ---------------------------------------------------------------------------


class ResultRepository:
    """Data-access helpers for :class:`EvalResult`."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        eval_run_id: str,
        row_index: int,
        input_data: str,
        expected_output: str,
        actual_output: str | None = None,
        comparer_score: float | None = None,
        comparer_details: dict | None = None,
        passed: bool | None = None,
        latency_ms: int | None = None,
        token_usage: dict | None = None,
        error: str | None = None,
    ) -> EvalResult:
        """Insert a single evaluation result row."""
        result = EvalResult(
            eval_run_id=eval_run_id,
            row_index=row_index,
            input_data=input_data,
            expected_output=expected_output,
            actual_output=actual_output,
            comparer_score=comparer_score,
            comparer_details=comparer_details,
            passed=passed,
            latency_ms=latency_ms,
            token_usage=token_usage,
            error=error,
        )
        self._session.add(result)
        await self._session.commit()
        await self._session.refresh(result)
        return result

    async def create_batch(self, results: list[EvalResult]) -> None:
        """Bulk-insert a list of pre-built :class:`EvalResult` instances."""
        self._session.add_all(results)
        await self._session.commit()

    async def list_by_run(self, run_id: str, *, failed_only: bool = False) -> list[EvalResult]:
        """Return results for a run, ordered by row index."""
        stmt = (
            select(EvalResult)
            .where(EvalResult.eval_run_id == run_id)
            .order_by(EvalResult.row_index)
        )
        if failed_only:
            stmt = stmt.where(EvalResult.passed == False)  # noqa: E712
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_id(self, result_id: str) -> EvalResult | None:
        """Return a single result by primary key, or ``None``."""
        return await self._session.get(EvalResult, result_id)
