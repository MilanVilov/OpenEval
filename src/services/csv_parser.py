"""CSV parsing service for dataset uploads."""

import csv
from collections.abc import Iterator
from io import StringIO
from pathlib import Path

CSV_FIELD_SIZE_LIMIT = 64 * 1024 * 1024


def _create_dict_reader(csv_content: str) -> csv.DictReader:
    csv.field_size_limit(CSV_FIELD_SIZE_LIMIT)
    return csv.DictReader(StringIO(csv_content))


async def parse_csv(file_path: str) -> dict:
    """Parse a CSV file and return metadata.

    Returns dict with keys: row_count, columns, preview (first 5 rows as list of dicts).
    """
    return parse_csv_content(Path(file_path).read_text(encoding="utf-8"))


def parse_csv_content(csv_content: str) -> dict:
    """Parse CSV text and return metadata."""
    reader = _create_dict_reader(csv_content)
    columns = reader.fieldnames or []
    rows = list(reader)
    return {
        "row_count": len(rows),
        "columns": list(columns),
        "preview": rows[:5],
    }


async def read_csv_rows(file_path: str) -> list[dict]:
    """Read all rows from a CSV file as a list of dicts."""
    return read_csv_rows_content(Path(file_path).read_text(encoding="utf-8"))


async def read_csv_rows_text(csv_content: str) -> list[dict]:
    """Read all rows from CSV text as a list of dicts."""
    return read_csv_rows_content(csv_content)


def iter_csv_rows(file_path: str) -> Iterator[dict]:
    """Yield rows from a CSV file without materializing the whole dataset."""
    with Path(file_path).open(encoding="utf-8", newline="") as csv_file:
        yield from csv.DictReader(csv_file)


def iter_csv_rows_text(csv_content: str) -> Iterator[dict]:
    """Yield rows from CSV text without materializing parsed rows."""
    return _create_dict_reader(csv_content)


def read_csv_rows_content(csv_content: str) -> list[dict]:
    """Read all rows from CSV text as a list of dicts."""
    reader = _create_dict_reader(csv_content)
    return list(reader)


def serialize_csv_rows(columns: list[str], rows: list[dict]) -> str:
    """Serialize rows into CSV text with the given column order."""
    buffer = StringIO()
    writer = csv.DictWriter(buffer, fieldnames=columns)
    writer.writeheader()
    for row in rows:
        writer.writerow({col: row.get(col, "") for col in columns})
    return buffer.getvalue()


async def write_csv_rows(
    file_path: str, columns: list[str], rows: list[dict]
) -> None:
    """Overwrite a CSV file with the given columns and rows."""
    path = Path(file_path)
    path.write_text(serialize_csv_rows(columns, rows), encoding="utf-8")


async def append_csv_rows(file_path: str, columns: list[str], rows: list[dict]) -> None:
    """Append rows to an existing CSV file using the provided column order."""
    path = Path(file_path)
    with path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        for row in rows:
            writer.writerow({col: row.get(col, "") for col in columns})
