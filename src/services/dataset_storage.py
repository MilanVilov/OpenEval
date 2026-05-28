"""Dataset CSV storage helpers."""

import logging
from pathlib import Path
from uuid import uuid4

from src import config
from src.db.models import Dataset
from src.services.csv_parser import read_csv_rows, read_csv_rows_text, serialize_csv_rows

logger = logging.getLogger(__name__)


def build_dataset_file_path() -> Path:
    """Return a new CSV file path under the configured upload directory."""
    settings = config.get_settings()
    return Path(settings.upload_dir) / f"{uuid4().hex}.csv"


def decode_csv_upload(content: bytes) -> str:
    """Decode uploaded CSV bytes as UTF-8 text."""
    return content.decode("utf-8")


async def read_dataset_rows(dataset: Dataset) -> list[dict]:
    """Read rows from the stored dataset CSV snapshot."""
    if dataset.csv_content is not None:
        return await read_csv_rows_text(dataset.csv_content)
    return await read_csv_rows(dataset.file_path)


def serialize_dataset_rows(columns: list[str], rows: list[dict]) -> str:
    """Serialize dataset rows using the dataset column order."""
    return serialize_csv_rows(columns, rows)


def write_dataset_file_copy(file_path: str, csv_content: str) -> None:
    """Best-effort write of the dataset CSV to local disk."""
    path = Path(file_path)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(csv_content, encoding="utf-8")
    except OSError as exc:
        logger.warning("Could not write dataset file copy %s: %s", file_path, exc)
