"""CSV parsing service for dataset uploads."""

import csv
from pathlib import Path


async def parse_csv(file_path: str) -> dict:
    """Parse a CSV file and return metadata.

    Returns dict with keys: row_count, columns, preview (first 5 rows as list of dicts).
    """
    path = Path(file_path)
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        columns = reader.fieldnames or []
        rows = list(reader)

    return {
        "row_count": len(rows),
        "columns": list(columns),
        "preview": rows[:5],
    }


async def read_csv_rows(file_path: str) -> list[dict]:
    """Read all rows from a CSV file as a list of dicts."""
    path = Path(file_path)
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)


async def write_csv_rows(
    file_path: str, columns: list[str], rows: list[dict]
) -> None:
    """Overwrite a CSV file with the given columns and rows."""
    path = Path(file_path)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({col: row.get(col, "") for col in columns})


async def append_csv_rows(file_path: str, columns: list[str], rows: list[dict]) -> None:
    """Append rows to an existing CSV file using the provided column order."""
    path = Path(file_path)
    with path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        for row in rows:
            writer.writerow({col: row.get(col, "") for col in columns})
