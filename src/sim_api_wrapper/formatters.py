"""Output formatters for the SIM API CLI."""

from __future__ import annotations

import csv
import io
import json
from typing import Any, Iterable, Sequence


def parse_fields(spec: str | None) -> list[str] | None:
    """Parse a comma separated list of field expressions."""

    if spec is None:
        return None
    fields = [field.strip() for field in spec.split(",")]
    cleaned = [field for field in fields if field]
    return cleaned or None


def emit_json(
    data: Any,
    *,
    fields: Sequence[str] | None = None,
    separator: str = ",",
    include_header: bool = True,
) -> str:
    """Render the payload as pretty printed JSON."""

    _ = separator, include_header  # Unused but kept for signature compatibility
    if fields is None:
        selected = data
    else:
        selected = _select_for_json(data, fields)
    return json.dumps(selected, indent=2, ensure_ascii=False)


def emit_kv(
    data: Any,
    *,
    fields: Sequence[str] | None = None,
    separator: str = ",",
    include_header: bool = True,
) -> str:
    """Render the payload as key=value pairs."""

    _ = separator, include_header
    records, field_names = _prepare_records(data, fields)
    lines: list[str] = []
    for index, record in enumerate(records):
        if index and field_names:
            lines.append("")
        for field in field_names:
            value = _stringify(record.get(field))
            lines.append(f"{field}={value}")
    return "\n".join(lines)


def emit_lines(
    data: Any,
    *,
    fields: Sequence[str] | None = None,
    separator: str = ",",
    include_header: bool = True,
) -> str:
    """Render the payload with one value per line."""

    _ = separator, include_header
    values: list[Any]
    if fields is None:
        if isinstance(data, list):
            values = list(data)
        else:
            values = [data]
    else:
        values = []
        for item in _as_items(data):
            for field in fields:
                resolved = _evaluate_field(item, field)
                if isinstance(resolved, list):
                    values.extend(_flatten(resolved))
                elif resolved is not None:
                    values.append(resolved)
    stringified = [_stringify_line(value) for value in values]
    return "\n".join(stringified)


def emit_delimited(
    data: Any,
    *,
    fields: Sequence[str] | None = None,
    separator: str = ",",
    include_header: bool = True,
) -> str:
    """Render the payload as delimited values using the csv module."""

    records, field_names = _prepare_records(data, fields)
    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=separator)
    if include_header and field_names:
        writer.writerow(field_names)
    for record in records:
        writer.writerow([_stringify(record.get(field)) for field in field_names])
    return buffer.getvalue().rstrip("\r\n")


def emit_table(
    data: Any,
    *,
    fields: Sequence[str] | None = None,
    separator: str = ",",
    include_header: bool = True,
) -> str:
    """Render the payload as an aligned table."""

    records, field_names = _prepare_records(data, fields)
    rows: list[list[str]] = [
        [_stringify(record.get(field)) for field in field_names]
        for record in records
    ]
    if include_header and field_names:
        rows.insert(0, list(field_names))

    if not rows:
        return ""

    widths = [max(len(row[idx]) for row in rows) for idx in range(len(field_names))]
    lines = []
    for row in rows:
        padded = [cell.ljust(widths[idx]) for idx, cell in enumerate(row)]
        lines.append(separator.join(padded))
    return "\n".join(lines)


def _select_for_json(data: Any, fields: Sequence[str]) -> Any:
    items = _as_items(data)
    if isinstance(data, list):
        return [_build_object(item, fields) for item in items]
    if len(fields) == 1 and fields[0] == ".":
        return _evaluate_field(data, ".")
    return _build_object(data, fields)


def _build_object(item: Any, fields: Sequence[str]) -> Any:
    if len(fields) == 1 and fields[0] == ".":
        return _evaluate_field(item, ".")
    return {field: _evaluate_field(item, field) for field in fields}


def _prepare_records(
    data: Any, fields: Sequence[str] | None
) -> tuple[list[dict[str, Any]], list[str]]:
    field_names = list(fields) if fields is not None else _default_fields(data)
    records: list[dict[str, Any]] = []
    for item in _as_items(data):
        record: dict[str, Any] = {}
        for field in field_names:
            record[field] = _evaluate_field(item, field)
        records.append(record)
    return records, field_names


def _default_fields(data: Any) -> list[str]:
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                return list(item.keys())
        return ["."] if data else ["."]
    if isinstance(data, dict):
        return list(data.keys())
    return ["."]


def _as_items(data: Any) -> Iterable[Any]:
    if isinstance(data, list):
        return data
    return [data]


def _evaluate_field(item: Any, expression: str) -> Any:
    if expression == ".":
        return item
    tokens = _tokenize(expression)
    current = item
    for token in tokens:
        if current is None:
            return None
        if isinstance(token, str):
            if isinstance(current, dict):
                current = current.get(token)
            else:
                return None
        else:
            if isinstance(current, list) and -len(current) <= token < len(current):
                current = current[token]
            else:
                return None
    return current


def _tokenize(expression: str) -> list[Any]:
    if not expression:
        raise ValueError("Field expression cannot be empty")

    tokens: list[Any] = []
    remainder = expression
    while remainder:
        if remainder[0] == "[":
            close = remainder.find("]")
            if close == -1:
                raise ValueError(f"Missing closing bracket in expression '{expression}'")
            index_str = remainder[1:close]
            if not index_str:
                raise ValueError(f"Empty index in expression '{expression}'")
            try:
                index = int(index_str)
            except ValueError as exc:  # pragma: no cover - defensive
                raise ValueError(f"Invalid list index '{index_str}' in expression '{expression}'") from exc
            tokens.append(index)
            remainder = remainder[close + 1 :]
            if remainder.startswith("."):
                remainder = remainder[1:]
        else:
            next_dot = remainder.find(".")
            next_bracket = remainder.find("[")
            end_index: int
            if next_dot == -1 and next_bracket == -1:
                end_index = len(remainder)
            elif next_bracket == -1 or (next_dot != -1 and next_dot < next_bracket):
                end_index = next_dot
            else:
                end_index = next_bracket
            token = remainder[:end_index]
            if not token:
                raise ValueError(f"Empty token in expression '{expression}'")
            tokens.append(token)
            remainder = remainder[end_index:]
            if remainder.startswith("."):
                remainder = remainder[1:]
    return tokens


def _flatten(values: Iterable[Any]) -> Iterable[Any]:
    for value in values:
        if isinstance(value, list):
            yield from _flatten(value)
        else:
            yield value


def _stringify(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return ",".join(_stringify(element) for element in value)
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def _stringify_line(value: Any) -> str:
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    if value is None:
        return ""
    return str(value)


__all__ = [
    "emit_delimited",
    "emit_json",
    "emit_kv",
    "emit_lines",
    "emit_table",
    "parse_fields",
]

