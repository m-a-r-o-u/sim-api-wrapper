"""Tests for CLI utilities."""

from __future__ import annotations

import pytest

from sim_api_wrapper.cli import _decode_separator, _select_formatter
from sim_api_wrapper.formatters import emit_delimited, emit_json


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (",", ","),
        ("\\t", "\t"),
        ("\\n", "\n"),
        ("\\x09", "\t"),
    ],
)
def test_decode_separator_handles_escape_sequences(value: str, expected: str) -> None:
    assert _decode_separator(value) == expected


def test_select_formatter_falls_back_to_json_for_dict_payload() -> None:
    formatter = _select_formatter("delimited", {"key": "value"})
    assert formatter is emit_json


def test_select_formatter_keeps_delimited_for_list_payload() -> None:
    formatter = _select_formatter("delimited", [{"key": "value"}])
    assert formatter is emit_delimited
