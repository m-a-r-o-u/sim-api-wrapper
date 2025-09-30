"""Tests for CLI utilities."""

from __future__ import annotations

import pytest

from sim_api_wrapper.cli import _decode_separator


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
