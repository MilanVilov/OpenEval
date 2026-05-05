"""SQLAlchemy ORM models for OpenEval."""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import JSON, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _new_id() -> str:
    """Generate a hex UUID string for use as a primary key."""
    return uuid4().hex


ID_LENGTH = 32
NAME_LENGTH = 255
STATUS_LENGTH = 50
PATH_LENGTH = 1024
URL_LENGTH = 2048
CRON_LENGTH = 100


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


class EvalConfig(Base):
    """Configuration for an evaluation run."""

    __tablename__ = "eval_configs"

    id: Mapped[str] = mapped_column(String(ID_LENGTH), primary_key=True, default=_new_id)
    name: Mapped[str] = mapped_column(String(NAME_LENGTH))
    system_prompt: Mapped[str] = mapped_column(Text)
    model: Mapped[str] = mapped_column(String(NAME_LENGTH))
    temperature: Mapped[float] = mapped_column(default=0.7)
    max_tokens: Mapped[int | None] = mapped_column(default=None)
    tools: Mapped[list] = mapped_column(JSON, default=list)
    tool_options: Mapped[dict] = mapped_column(JSON, default=dict)
    graders: Mapped[list] = mapped_column(JSON, default=list)
    tags: Mapped[list | None] = mapped_column(JSON, default=list)
    reasoning_config: Mapped[dict | None] = mapped_column(JSON, default=None)
    response_format: Mapped[dict | None] = mapped_column(JSON, default=None)
    concurrency: Mapped[int] = mapped_column(default=5)
    readonly: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    runs: Mapped[list["EvalRun"]] = relationship(
        back_populates="config",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        return f"<EvalConfig id={self.id!r} name={self.name!r}>"


class Dataset(Base):
    """An uploaded evaluation dataset."""

    __tablename__ = "datasets"

    id: Mapped[str] = mapped_column(String(ID_LENGTH), primary_key=True, default=_new_id)
    name: Mapped[str] = mapped_column(String(NAME_LENGTH))
    file_path: Mapped[str] = mapped_column(String(PATH_LENGTH))
    row_count: Mapped[int]
    columns: Mapped[list] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    runs: Mapped[list["EvalRun"]] = relationship(
        back_populates="dataset",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        return f"<Dataset id={self.id!r} name={self.name!r}>"


class VectorStore(Base):
    """Reference to an OpenAI vector store."""

    __tablename__ = "vector_stores"

    id: Mapped[str] = mapped_column(String(ID_LENGTH), primary_key=True, default=_new_id)
    openai_vector_store_id: Mapped[str] = mapped_column(String(NAME_LENGTH))
    name: Mapped[str] = mapped_column(String(NAME_LENGTH))
    file_count: Mapped[int] = mapped_column(default=0)
    status: Mapped[str] = mapped_column(String(STATUS_LENGTH), default="creating")
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    def __repr__(self) -> str:
        return f"<VectorStore id={self.id!r} name={self.name!r}>"


class Container(Base):
    """Reference to an OpenAI container for the shell tool."""

    __tablename__ = "containers"

    id: Mapped[str] = mapped_column(String(ID_LENGTH), primary_key=True, default=_new_id)
    openai_container_id: Mapped[str] = mapped_column(String(NAME_LENGTH))
    name: Mapped[str] = mapped_column(String(NAME_LENGTH))
    file_count: Mapped[int] = mapped_column(default=0)
    status: Mapped[str] = mapped_column(String(STATUS_LENGTH), default="active")
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    def __repr__(self) -> str:
        return f"<Container id={self.id!r} name={self.name!r}>"


class EvalRun(Base):
    """A single execution of an evaluation configuration against a dataset."""

    __tablename__ = "eval_runs"

    id: Mapped[str] = mapped_column(String(ID_LENGTH), primary_key=True, default=_new_id)
    eval_config_id: Mapped[str] = mapped_column(
        String(ID_LENGTH),
        ForeignKey("eval_configs.id", ondelete="CASCADE"),
    )
    dataset_id: Mapped[str] = mapped_column(
        String(ID_LENGTH),
        ForeignKey("datasets.id", ondelete="CASCADE"),
    )
    status: Mapped[str] = mapped_column(String(STATUS_LENGTH), default="pending")
    progress: Mapped[int] = mapped_column(default=0)
    total_rows: Mapped[int] = mapped_column(default=0)
    summary: Mapped[dict | None] = mapped_column(JSON, default=None)
    started_at: Mapped[datetime | None] = mapped_column(default=None)
    completed_at: Mapped[datetime | None] = mapped_column(default=None)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    scheduled_by_id: Mapped[str | None] = mapped_column(
        String(ID_LENGTH),
        ForeignKey("schedules.id", ondelete="SET NULL"),
        default=None,
    )

    config: Mapped["EvalConfig"] = relationship(back_populates="runs")
    dataset: Mapped["Dataset"] = relationship(back_populates="runs")
    results: Mapped[list["EvalResult"]] = relationship(
        back_populates="run",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    schedule: Mapped["Schedule | None"] = relationship(back_populates="runs")

    __table_args__ = (
        Index("ix_eval_runs_eval_config_id", "eval_config_id"),
        Index("ix_eval_runs_dataset_id", "dataset_id"),
        Index("ix_eval_runs_scheduled_by_id", "scheduled_by_id"),
    )

    def __repr__(self) -> str:
        return f"<EvalRun id={self.id!r} status={self.status!r}>"


class EvalResult(Base):
    """Individual row result within an evaluation run."""

    __tablename__ = "eval_results"

    id: Mapped[str] = mapped_column(String(ID_LENGTH), primary_key=True, default=_new_id)
    eval_run_id: Mapped[str] = mapped_column(
        String(ID_LENGTH),
        ForeignKey("eval_runs.id", ondelete="CASCADE"),
    )
    row_index: Mapped[int]
    input_data: Mapped[str] = mapped_column(Text)
    expected_output: Mapped[str] = mapped_column(Text)
    actual_output: Mapped[str | None] = mapped_column(Text, default=None)
    comparer_score: Mapped[float | None] = mapped_column(default=None)
    comparer_details: Mapped[dict | None] = mapped_column(JSON, default=None)
    passed: Mapped[bool | None] = mapped_column(default=None)
    latency_ms: Mapped[int | None] = mapped_column(default=None)
    token_usage: Mapped[dict | None] = mapped_column(JSON, default=None)
    error: Mapped[str | None] = mapped_column(Text, default=None)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    run: Mapped["EvalRun"] = relationship(back_populates="results")

    __table_args__ = (Index("ix_eval_results_eval_run_id", "eval_run_id"),)

    def __repr__(self) -> str:
        return f"<EvalResult id={self.id!r} row_index={self.row_index}>"


class Schedule(Base):
    """A recurring trigger that creates eval runs on a cron schedule."""

    __tablename__ = "schedules"

    id: Mapped[str] = mapped_column(String(ID_LENGTH), primary_key=True, default=_new_id)
    name: Mapped[str] = mapped_column(String(NAME_LENGTH))
    eval_config_id: Mapped[str] = mapped_column(
        String(ID_LENGTH),
        ForeignKey("eval_configs.id", ondelete="CASCADE"),
    )
    dataset_id: Mapped[str] = mapped_column(
        String(ID_LENGTH),
        ForeignKey("datasets.id", ondelete="CASCADE"),
    )
    cron_expression: Mapped[str] = mapped_column(String(CRON_LENGTH))
    enabled: Mapped[bool] = mapped_column(default=True)
    slack_webhook_url: Mapped[str | None] = mapped_column(String(URL_LENGTH), default=None)
    min_accuracy: Mapped[float | None] = mapped_column(default=None)
    last_triggered_at: Mapped[datetime | None] = mapped_column(default=None)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        onupdate=func.now(),
    )

    config: Mapped["EvalConfig"] = relationship()
    dataset: Mapped["Dataset"] = relationship()
    runs: Mapped[list["EvalRun"]] = relationship(back_populates="schedule")

    def __repr__(self) -> str:
        return f"<Schedule id={self.id!r} name={self.name!r} enabled={self.enabled}>"
