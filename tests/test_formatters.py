"""Tests for CLI output formatters."""

from __future__ import annotations

import csv
import io
import json

import pytest

from sim_api_wrapper.formatters import emit_delimited, emit_json, emit_plain, emit_yaml, parse_fields


@pytest.fixture
def sample_dict() -> dict[str, object]:
    return {
        "name": "Example",
        "status": "active",
        "numbers": [1, 2, 3],
        "nested": {"value": 42},
    }


@pytest.fixture
def sample_list(sample_dict: dict[str, object]) -> list[dict[str, object]]:
    other = {"name": "Second", "status": None, "numbers": [4], "nested": {"value": 7}}
    return [sample_dict, other]


def test_parse_fields_splits_and_trims() -> None:
    assert parse_fields(" a , b , ") == ["a", "b"]
    assert parse_fields(None) is None
    assert parse_fields(" ") is None


def test_parse_fields_respects_nested_commas() -> None:
    spec = "foo, daten.emailadressen[?contains(typ,'haupt,email')].adresse | [0]"
    assert parse_fields(spec) == [
        "foo",
        "daten.emailadressen[?contains(typ,'haupt,email')].adresse | [0]",
    ]


def test_emit_json_preserves_structure(sample_dict: dict[str, object]) -> None:
    rendered = emit_json(sample_dict)
    assert json.loads(rendered) == sample_dict


def test_emit_json_with_fields(sample_dict: dict[str, object]) -> None:
    rendered = emit_json(sample_dict, fields=["name", "nested.value"])
    assert json.loads(rendered) == {"name": "Example", "nested.value": 42}


def test_emit_yaml_produces_expected_structure(sample_dict: dict[str, object]) -> None:
    rendered = emit_yaml(sample_dict)
    expected = "\n".join(
        [
            'name: "Example"',
            'status: "active"',
            "numbers:",
            "  - 1",
            "  - 2",
            "  - 3",
            "nested:",
            "  value: 42",
        ]
    )
    assert rendered == expected


def test_emit_yaml_with_fields(sample_dict: dict[str, object]) -> None:
    rendered = emit_yaml(sample_dict, fields=["name", "nested.value"])
    expected = "\n".join([
        'name: "Example"',
        "nested.value: 42",
    ])
    assert rendered == expected


def test_emit_plain_from_list() -> None:
    values = ["alpha", "beta"]
    rendered = emit_plain(values)
    assert rendered.splitlines() == values


def test_emit_plain_from_dict_falls_back_to_yaml(sample_dict: dict[str, object]) -> None:
    rendered = emit_plain(sample_dict)
    assert rendered == emit_yaml(sample_dict)


def test_emit_plain_with_field_flattening(sample_dict: dict[str, object]) -> None:
    rendered = emit_plain(sample_dict, fields=["numbers"])
    assert rendered.splitlines() == ["1", "2", "3"]


def test_emit_plain_supports_jmespath_filters() -> None:
    payload = {
        "daten": {
            "emailadressen": [
                {"typ": "hauptemail", "adresse": "main@example.org"},
                {"typ": "zweitemail", "adresse": "alt@example.org"},
            ]
        }
    }
    expression = "daten.emailadressen[?contains(typ,'hauptemail')].adresse | [0]"
    rendered = emit_plain(payload, fields=[expression])
    assert rendered.splitlines() == ["main@example.org"]


def test_emit_delimited_with_header(sample_list: list[dict[str, object]]) -> None:
    rendered = emit_delimited(sample_list, fields=["name", "numbers", "nested.value"])
    reader = csv.reader(io.StringIO(rendered))
    rows = list(reader)
    assert rows[0] == ["name", "numbers", "nested.value"]
    assert rows[1] == ["Example", "1,2,3", "42"]
    assert rows[2] == ["Second", "4", "7"]


def test_emit_delimited_without_header(sample_dict: dict[str, object]) -> None:
    rendered = emit_delimited(sample_dict, fields=["name", "missing"], separator="\t", include_header=False)
    assert rendered == "Example\t"
