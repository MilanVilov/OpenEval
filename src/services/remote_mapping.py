"""Helpers for remote payload inspection and mapping into dataset rows."""

from __future__ import annotations

import json
import re


_INDEX_OR_WILDCARD_PATTERN = re.compile(r"\[(\d*)\]")
_TEMPLATE_PATTERN = re.compile(r"\{([^{}]+)\}")
_NUMBER_PATTERN = re.compile(r"-?\d+(?:\.\d+)?")
_COMPARISON_OPERATORS = ("==", "!=", ">=", "<=", ">", "<", "=")
_WILDCARD = object()
_MISSING = object()


def find_array_paths(payload: object) -> list[str]:
    """Return all paths within ``payload`` whose value is a list."""
    paths: set[str] = set()
    _collect_array_paths(payload, "$", paths)
    return sorted(paths)


def extract_records(payload: object, records_path: str | None) -> list[object]:
    """Return the list of records at ``records_path``."""
    if not records_path:
        return []

    records = resolve_path(payload, records_path)
    if records is None:
        return []
    if not isinstance(records, list):
        raise ValueError("records_path must resolve to a list")
    return list(records)


def list_field_candidates(records: list[object], *, sample_size: int = 5) -> list[str]:
    """Return flattened candidate field paths for a sample of records."""
    candidates: set[str] = set()
    for record in records[:sample_size]:
        _collect_field_paths(record, "", candidates)
    return sorted(candidates)


def map_records(
    records: list[object],
    field_mapping: dict[str, str],
    *,
    columns: list[str] | None = None,
) -> list[dict[str, str]]:
    """Map remote records into dataset rows using the provided field mapping."""
    target_columns = columns if columns is not None else list(field_mapping.keys())
    rows: list[dict[str, str]] = []

    for record in records:
        row = {
            column: _render_mapping_expression(record, field_mapping.get(column, ""))
            for column in target_columns
        }
        rows.append(row)

    return rows


def resolve_path(payload: object, path: str | None) -> object | None:
    """Resolve a simple dot/bracket path against ``payload``."""
    if path in (None, "", "$"):
        return payload

    return _resolve_tokens(payload, _tokenize_path(path))


def _collect_array_paths(payload: object, path: str, paths: set[str]) -> None:
    """Recursively collect array paths."""
    if isinstance(payload, list):
        paths.add(path)
        wildcard_path = f"{path}[]" if path != "$" else "$[]"
        for item in payload[:5]:
            _collect_array_paths(item, wildcard_path, paths)
        return

    if not isinstance(payload, dict):
        return

    for key, value in payload.items():
        child_path = f"{path}.{key}" if path != "$" else f"$.{key}"
        _collect_array_paths(value, child_path, paths)


def _collect_field_paths(payload: object, prefix: str, candidates: set[str]) -> None:
    """Recursively flatten field paths for a record."""
    if isinstance(payload, dict):
        if not payload and prefix:
            candidates.add(prefix)
            return
        for key, value in payload.items():
            child = key if not prefix else f"{prefix}.{key}"
            _collect_field_paths(value, child, candidates)
        return

    if isinstance(payload, list):
        candidates.add(prefix or "$")
        if not payload:
            return
        for value in payload[:5]:
            child = f"{prefix}[]" if prefix else "$[]"
            _collect_field_paths(value, child, candidates)
        return

    candidates.add(prefix or "$")


def _stringify_value(value: object | None) -> str:
    """Convert a mapped value into the stored dataset string form."""
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, separators=(",", ":"), ensure_ascii=False)
    return str(value)


def _render_mapping_expression(record: object, expression: str) -> str:
    """Render a mapping expression using either a single path or template placeholders."""
    if not expression:
        return ""

    matches = list(_TEMPLATE_PATTERN.finditer(expression))
    if not matches:
        return _stringify_value(_evaluate_expression(record, expression))

    def replace(match: re.Match[str]) -> str:
        inner_expression = match.group(1).strip()
        return _stringify_value(_evaluate_expression(record, inner_expression))

    return _TEMPLATE_PATTERN.sub(replace, expression)


def _evaluate_expression(record: object, expression: str) -> object | None:
    """Evaluate a mapping expression against one record."""
    stripped = expression.strip()
    if not stripped:
        return None

    ternary = _split_ternary_expression(stripped)
    if ternary is not None:
        condition, when_true, when_false = ternary
        branch = when_true if _evaluate_condition(record, condition) else when_false
        return _evaluate_expression(record, branch)

    literal = _parse_literal(stripped)
    if literal is not _MISSING:
        return literal

    return resolve_path(record, stripped)


def _evaluate_condition(record: object, expression: str) -> bool:
    """Evaluate a simple comparison condition."""
    stripped = expression.strip()
    comparison = _split_comparison_expression(stripped)
    if comparison is None:
        value = _evaluate_expression(record, stripped)
        return _coerce_truthy(value)

    left_expression, operator, right_expression = comparison
    left_value = _evaluate_expression(record, left_expression)
    right_value = _evaluate_expression(record, right_expression)
    return _compare_values(left_value, right_value, operator)


def _split_ternary_expression(expression: str) -> tuple[str, str, str] | None:
    """Split a top-level ternary expression into condition, true branch, false branch."""
    question_index = _find_top_level_token(expression, "?")
    if question_index is None:
        return None

    colon_index = _find_top_level_token(expression, ":", start=question_index + 1)
    if colon_index is None:
        raise ValueError("Conditional mapping expressions must include ':'")

    return (
        expression[:question_index].strip(),
        expression[question_index + 1 : colon_index].strip(),
        expression[colon_index + 1 :].strip(),
    )


def _split_comparison_expression(expression: str) -> tuple[str, str, str] | None:
    """Split a top-level comparison expression."""
    for operator in _COMPARISON_OPERATORS:
        index = _find_top_level_token(expression, operator)
        if index is not None:
            return (
                expression[:index].strip(),
                operator,
                expression[index + len(operator) :].strip(),
            )
    return None


def _find_top_level_token(
    expression: str,
    token: str,
    *,
    start: int = 0,
) -> int | None:
    """Find a token outside quotes and bracket nesting."""
    quote: str | None = None
    escaped = False
    bracket_depth = 0
    paren_depth = 0

    index = start
    while index < len(expression):
        char = expression[index]
        if quote is not None:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
            index += 1
            continue

        if char in ('"', "'"):
            quote = char
            index += 1
            continue

        if char == "[":
            bracket_depth += 1
            index += 1
            continue
        if char == "]":
            bracket_depth = max(0, bracket_depth - 1)
            index += 1
            continue
        if char == "(":
            paren_depth += 1
            index += 1
            continue
        if char == ")":
            paren_depth = max(0, paren_depth - 1)
            index += 1
            continue

        if bracket_depth == 0 and paren_depth == 0 and expression.startswith(token, index):
            return index

        index += 1

    return None


def _parse_literal(expression: str) -> object:
    """Parse a supported literal value, or return ``_MISSING`` when not a literal."""
    if len(expression) >= 2 and expression[0] == expression[-1] and expression[0] in ('"', "'"):
        return expression[1:-1]
    if expression == "true":
        return True
    if expression == "false":
        return False
    if expression == "null":
        return None
    if _NUMBER_PATTERN.fullmatch(expression):
        return float(expression) if "." in expression else int(expression)
    return _MISSING


def _coerce_truthy(value: object | None) -> bool:
    """Convert an evaluated value to boolean for conditional expressions."""
    if isinstance(value, list):
        return len(value) > 0
    return bool(value)


def _values_equal(left: object | None, right: object | None) -> bool:
    """Compare mapping values with simple list-aware semantics."""
    if isinstance(left, list) and isinstance(right, list):
        if len(left) != len(right):
            return False
        return all(_values_equal(left_item, right_item) for left_item, right_item in zip(left, right))
    if isinstance(left, list):
        return any(_values_equal(item, right) for item in left)
    if isinstance(right, list):
        return any(_values_equal(left, item) for item in right)
    return _normalize_scalar(left) == _normalize_scalar(right)


def _compare_values(left: object | None, right: object | None, operator: str) -> bool:
    """Compare mapping values using list-aware scalar semantics."""
    if operator in ("==", "="):
        return _values_equal(left, right)
    if operator == "!=":
        return not _values_equal(left, right)
    return _compare_ordered_values(left, right, operator)


def _compare_ordered_values(left: object | None, right: object | None, operator: str) -> bool:
    """Compare ordered values, applying wildcard comparisons to any matching scalar."""
    if isinstance(left, list) and isinstance(right, list):
        return any(_compare_ordered_values(left_item, right_item, operator) for left_item in left for right_item in right)
    if isinstance(left, list):
        return any(_compare_ordered_values(item, right, operator) for item in left)
    if isinstance(right, list):
        return any(_compare_ordered_values(left, item, operator) for item in right)

    normalized_left = _normalize_scalar(left)
    normalized_right = _normalize_scalar(right)
    if not _are_comparable_scalars(normalized_left, normalized_right):
        return False

    if operator == ">":
        return normalized_left > normalized_right
    if operator == ">=":
        return normalized_left >= normalized_right
    if operator == "<":
        return normalized_left < normalized_right
    if operator == "<=":
        return normalized_left <= normalized_right
    raise ValueError(f"Unsupported comparison operator: {operator}")


def _normalize_scalar(value: object | None) -> object | None:
    """Normalize scalar values for mapping comparisons."""
    if not isinstance(value, str):
        return value

    literal = _parse_literal(value)
    if literal is not _MISSING:
        return literal
    return value


def _are_comparable_scalars(left: object | None, right: object | None) -> bool:
    """Return whether two normalized scalars can be ordered."""
    if isinstance(left, bool) or isinstance(right, bool):
        return isinstance(left, bool) and isinstance(right, bool)
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        return True
    if isinstance(left, str) and isinstance(right, str):
        return True
    return False


def _tokenize_path(path: str) -> list[str | int | object]:
    """Split a simple dot/bracket path into tokens."""
    normalized = path.strip()
    if normalized.startswith("$."):
        normalized = normalized[2:]
    elif normalized.startswith("$"):
        normalized = normalized[1:]

    tokens: list[str | int | object] = []
    for segment in normalized.split("."):
        if not segment:
            continue

        cursor = 0
        for match in _INDEX_OR_WILDCARD_PATTERN.finditer(segment):
            if match.start() > cursor:
                tokens.append(segment[cursor:match.start()])
            index = match.group(1)
            tokens.append(int(index) if index.isdigit() else _WILDCARD)
            cursor = match.end()

        if cursor < len(segment):
            tokens.append(segment[cursor:])

    return tokens


def _resolve_tokens(
    payload: object,
    tokens: list[str | int | object],
) -> object | None:
    """Resolve a tokenized path, supporting wildcard list traversal."""
    if not tokens:
        return payload

    token = tokens[0]
    remainder = tokens[1:]

    if token is _WILDCARD:
        if not isinstance(payload, list):
            return None
        results: list[object] = []
        for item in payload:
            resolved = _resolve_tokens(item, remainder)
            if resolved is None:
                continue
            if isinstance(resolved, list):
                results.extend(resolved)
            else:
                results.append(resolved)
        return results

    if isinstance(token, int):
        if not isinstance(payload, list) or token >= len(payload):
            return None
        return _resolve_tokens(payload[token], remainder)

    if not isinstance(payload, dict) or token not in payload:
        return None
    return _resolve_tokens(payload[token], remainder)
