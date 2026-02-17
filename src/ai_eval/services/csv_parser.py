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
