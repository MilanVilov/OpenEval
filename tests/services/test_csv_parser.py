"""Tests for CSV dataset parsing."""

from src.services.csv_parser import CSV_FIELD_SIZE_LIMIT, parse_csv_content


def test_csv_field_size_limit_is_64_mib() -> None:
    """Set the CSV parser field limit to 64 MiB."""
    assert CSV_FIELD_SIZE_LIMIT == 64 * 1024 * 1024


def test_parse_csv_content_accepts_field_larger_than_python_default() -> None:
    """Parse a field larger than Python's default 128 KiB limit."""
    large_value = "A" * (128 * 1024 + 1)
    csv_content = f"input,expected_output,file_base64\nhello,world,{large_value}\n"

    metadata = parse_csv_content(csv_content)

    assert metadata["preview"][0]["file_base64"] == large_value
