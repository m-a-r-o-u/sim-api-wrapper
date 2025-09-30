"""Output formatters for the SIM API CLI."""

from __future__ import annotations

import csv
import io
import json
from functools import lru_cache
from typing import Any, Iterable, Sequence


def _split_expression(spec: str, delimiter: str) -> list[str]:
    parts: list[str] = []
    current: list[str] = []
    bracket_depth = 0
    paren_depth = 0
    brace_depth = 0
    in_single_quote = False
    in_double_quote = False
    escape_next = False

    for char in spec:
        if escape_next:
            current.append(char)
            escape_next = False
            continue

        if char == "\\" and (in_single_quote or in_double_quote):
            current.append(char)
            escape_next = True
            continue

        if char == "'" and not in_double_quote:
            in_single_quote = not in_single_quote
            current.append(char)
            continue

        if char == '"' and not in_single_quote:
            in_double_quote = not in_double_quote
            current.append(char)
            continue

        if not in_single_quote and not in_double_quote:
            if char == "[":
                bracket_depth += 1
            elif char == "]" and bracket_depth:
                bracket_depth -= 1
            elif char == "(":
                paren_depth += 1
            elif char == ")" and paren_depth:
                paren_depth -= 1
            elif char == "{":
                brace_depth += 1
            elif char == "}" and brace_depth:
                brace_depth -= 1

            if (
                char == delimiter
                and bracket_depth == 0
                and paren_depth == 0
                and brace_depth == 0
            ):
                parts.append("".join(current))
                current = []
                continue

        current.append(char)

    parts.append("".join(current))
    return parts


def _split_logical(spec: str, operator: str) -> list[str]:
    parts: list[str] = []
    current: list[str] = []
    bracket_depth = 0
    paren_depth = 0
    brace_depth = 0
    in_single_quote = False
    in_double_quote = False
    escape_next = False
    index = 0
    length = len(spec)

    while index < length:
        char = spec[index]
        if escape_next:
            current.append(char)
            escape_next = False
            index += 1
            continue

        if char == "\\" and (in_single_quote or in_double_quote):
            current.append(char)
            escape_next = True
            index += 1
            continue

        if char == "'" and not in_double_quote:
            in_single_quote = not in_single_quote
            current.append(char)
            index += 1
            continue

        if char == '"' and not in_single_quote:
            in_double_quote = not in_double_quote
            current.append(char)
            index += 1
            continue

        if not in_single_quote and not in_double_quote:
            if char == "[":
                bracket_depth += 1
            elif char == "]" and bracket_depth:
                bracket_depth -= 1
            elif char == "(":
                paren_depth += 1
            elif char == ")" and paren_depth:
                paren_depth -= 1
            elif char == "{":
                brace_depth += 1
            elif char == "}" and brace_depth:
                brace_depth -= 1

            if (
                bracket_depth == 0
                and paren_depth == 0
                and brace_depth == 0
                and spec.startswith(operator, index)
            ):
                parts.append("".join(current))
                current = []
                index += len(operator)
                continue

        current.append(char)
        index += 1

    parts.append("".join(current))
    return parts


def parse_fields(spec: str | None) -> list[str] | None:
    """Parse a comma separated list of field expressions.

    The parser keeps commas that are enclosed within brackets, braces, parentheses
    or string literals so complex JMESPath-like expressions remain intact.
    """

    if spec is None:
        return None

    parts = _split_expression(spec, ",")
    cleaned = [part.strip() for part in parts if part.strip()]
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
    stages = _split_expression(expression, "|")
    current = item
    for stage in stages:
        stage = stage.strip()
        if not stage:
            continue
        tokens = _compile_stage(stage)
        current = _evaluate_tokens(current, tokens)
    return current


@lru_cache(maxsize=256)
def _compile_stage(stage: str) -> list[tuple[str, Any]]:
    tokens: list[tuple[str, Any]] = []
    remainder = stage
    while remainder:
        if remainder[0] == "[":
            close = _find_closing(remainder, "[", "]")
            if close == -1:
                raise ValueError(f"Missing closing bracket in expression '{stage}'")
            content = remainder[1:close].strip()
            if not content:
                tokens.append(("all", None))
            elif content.startswith("?"):
                tokens.append(("filter", content[1:].strip()))
            else:
                try:
                    tokens.append(("index", int(content)))
                except ValueError as exc:
                    raise ValueError(
                        f"Invalid list index '{content}' in expression '{stage}'"
                    ) from exc
            remainder = remainder[close + 1 :]
            if remainder.startswith("."):
                remainder = remainder[1:]
            continue

        next_dot = remainder.find(".")
        next_bracket = remainder.find("[")
        if next_dot == -1 and next_bracket == -1:
            token = remainder.strip()
            remainder = ""
        elif next_bracket == -1 or (next_dot != -1 and next_dot < next_bracket):
            token = remainder[:next_dot]
            remainder = remainder[next_dot + 1 :]
        else:
            token = remainder[:next_bracket]
            remainder = remainder[next_bracket:]
        token = token.strip()
        if token:
            tokens.append(("field", token))
    return tokens


def _evaluate_tokens(value: Any, tokens: Sequence[tuple[str, Any]]) -> Any:
    current = value
    for kind, payload in tokens:
        if current is None:
            return None
        if kind == "field":
            current = _apply_field(current, payload)
        elif kind == "index":
            current = _apply_index(current, payload)
        elif kind == "all":
            current = _apply_all(current)
        elif kind == "filter":
            current = _apply_filter(current, payload)
        else:  # pragma: no cover - defensive programming
            raise ValueError(f"Unsupported token '{kind}' in expression")
    return current


def _apply_field(value: Any, name: str) -> Any:
    if isinstance(value, list):
        results = []
        for element in value:
            resolved = _apply_field(element, name)
            if isinstance(resolved, list):
                results.extend(resolved)
            elif resolved is not None:
                results.append(resolved)
        return results
    if isinstance(value, dict):
        return value.get(name)
    return None


def _apply_index(value: Any, index: int) -> Any:
    if isinstance(value, list) and -len(value) <= index < len(value):
        return value[index]
    return None


def _apply_all(value: Any) -> Any:
    if isinstance(value, list):
        flattened: list[Any] = []
        for element in value:
            if isinstance(element, list):
                flattened.extend(element)
            else:
                flattened.append(element)
        return flattened
    return value


def _apply_filter(value: Any, expression: str) -> Any:
    if not isinstance(value, list):
        return None
    return [item for item in value if _matches_filter(item, expression)]


def _matches_filter(item: Any, expression: str) -> bool:
    expression = expression.strip()
    while (
        expression.startswith("(")
        and expression.endswith(")")
        and _find_closing(expression, "(", ")") == len(expression) - 1
    ):
        expression = expression[1:-1].strip()

    for operator, combiner in (("||", any), ("&&", all)):
        parts = [part.strip() for part in _split_logical(expression, operator)]
        if len(parts) > 1:
            evaluations = (_matches_filter(item, part) for part in parts if part)
            return combiner(evaluations)

    if expression.startswith("contains(") and expression.endswith(")"):
        inner = expression[len("contains(") : -1]
        arguments = _split_expression(inner, ",")
        if len(arguments) != 2:
            raise ValueError(f"Invalid contains() call: '{expression}'")
        target_expr = arguments[0].strip()
        needle = _strip_quotes(arguments[1].strip())
        haystack = _evaluate_tokens(item, _compile_stage(target_expr))
        if isinstance(haystack, list):
            return any(_needle_in_value(needle, value) for value in haystack)
        return _needle_in_value(needle, haystack)
    raise ValueError(f"Unsupported filter expression '{expression}'")


def _needle_in_value(needle: str, value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, list):
        return any(_needle_in_value(needle, element) for element in value)
    return needle in str(value)


def _find_closing(text: str, opening: str, closing: str) -> int:
    depth = 0
    in_single_quote = False
    in_double_quote = False
    escape_next = False
    for index, char in enumerate(text):
        if escape_next:
            escape_next = False
            continue
        if char == "\\" and (in_single_quote or in_double_quote):
            escape_next = True
            continue
        if char == "'" and not in_double_quote:
            in_single_quote = not in_single_quote
            continue
        if char == '"' and not in_single_quote:
            in_double_quote = not in_double_quote
            continue
        if in_single_quote or in_double_quote:
            continue
        if char == opening:
            depth += 1
        elif char == closing:
            depth -= 1
            if depth == 0:
                return index
    return -1


def _strip_quotes(value: str) -> str:
    if (value.startswith("'") and value.endswith("'")) or (
        value.startswith('"') and value.endswith('"')
    ):
        return value[1:-1]
    return value


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

