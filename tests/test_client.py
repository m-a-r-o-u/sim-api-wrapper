from __future__ import annotations

import json
from typing import Callable, Dict, Tuple

import pytest

from sim_api_wrapper.client import DEFAULT_BASE_URL, SimApiClient
from sim_api_wrapper.exceptions import SimApiError

ResponseTuple = Tuple[int, Dict[str, str], bytes]


@pytest.fixture()
def register_response(monkeypatch: pytest.MonkeyPatch) -> Callable[[str, ResponseTuple], None]:
    responses: Dict[str, ResponseTuple] = {}

    def fake_open(self: SimApiClient, request) -> ResponseTuple:
        try:
            return responses[request.full_url]
        except KeyError as exc:  # pragma: no cover - defensive guard
            raise AssertionError(f"Unexpected URL requested: {request.full_url}") from exc

    monkeypatch.setattr(SimApiClient, "_open", fake_open)

    def registrar(url: str, response: ResponseTuple | None = None, *, status: int = 200, json_data=None, headers=None) -> None:
        if response is not None:
            responses[url] = response
            return
        body = b""
        header_map = headers.copy() if headers else {}
        if json_data is not None:
            body = json.dumps(json_data).encode("utf-8")
            header_map.setdefault("Content-Type", "application/json")
        responses[url] = (status, header_map, body)

    return registrar


@pytest.fixture()
def client() -> SimApiClient:
    with SimApiClient(use_netrc=False) as api_client:
        yield api_client


def test_list_groups(register_response, client: SimApiClient) -> None:
    url = f"{DEFAULT_BASE_URL}/service/AI/groups"
    register_response(url, json_data=["a1101", "a1101-ai-c"])

    groups = client.list_groups()

    assert groups == ["a1101", "a1101-ai-c"]


def test_get_group_members(register_response, client: SimApiClient) -> None:
    url = f"{DEFAULT_BASE_URL}/service/AI/groups/pn69ju-ai-c/members?solve=false"
    register_response(url, json_data=["di25koy", "di29xub"])

    members = client.get_group_members("pn69ju-ai-c")

    assert members == ["di25koy", "di29xub"]


def test_get_project_institution_links(register_response, client: SimApiClient) -> None:
    url = f"{DEFAULT_BASE_URL}/einrichtung?projektname=pn69ju"
    register_response(
        url,
        json_data={
            "code": 0,
            "message": "OK",
            "data": [
                {
                    "projektname": "pn69ju",
                    "einrichtungsId": "0000000000E4EE4B",
                    "link": "https://simapi.sim.lrz.de/einrichtung/0000000000E4EE4B",
                }
            ],
        },
    )

    links = client.get_project_institution_links("pn69ju")

    assert len(links) == 1
    assert links[0].projektname == "pn69ju"
    assert links[0].einrichtungs_id == "0000000000E4EE4B"


def test_get_institution(register_response, client: SimApiClient) -> None:
    url = f"{DEFAULT_BASE_URL}/einrichtung/0000000000E4EE4B"
    register_response(
        url,
        json_data={
            "code": 0,
            "message": "OK",
            "data": {
                "LRZid": "0000000000E4EE4B",
                "name": "Test Institution",
                "parent_lrzId": ["0000000000000000"],
                "parent_link": ["https://simapi.sim.lrz.de/einrichtung/0000000000000000"],
                "anschriften": [
                    {
                        "typ": "Generell",
                        "strasse": "Teststraße 1",
                        "plz": "85748",
                        "ort": "Garching",
                        "land": "Deutschland",
                        "adressat1": "Bayerische Akademie der Wissenschaften",
                        "adressat2": "Leibniz-Rechenzentrum",
                        "geerbt": True,
                    }
                ],
                "chef_lrzId": "00000000001F17E0",
                "chef_link": ["https://simapi.sim.lrz.de/person/00000000001F17E0"],
            },
        },
    )

    institution = client.get_institution("0000000000E4EE4B")

    assert institution.lrz_id == "0000000000E4EE4B"
    assert institution.chef_lrz_id == "00000000001F17E0"
    assert institution.chef_links == ["https://simapi.sim.lrz.de/person/00000000001F17E0"]
    assert institution.anschriften[0].ort == "Garching"


def test_get_person(register_response, client: SimApiClient) -> None:
    url = f"{DEFAULT_BASE_URL}/person/00000000001F17E0"
    register_response(
        url,
        json_data={
            "code": 0,
            "message": "OK",
            "data": {
                "LRZid": "00000000001F17E0",
                "benutzername": "barekzai",
                "anrede": "Herr Prof. Dr.",
                "rufname": "Mares",
                "nachname": "Barekzai",
                "titelPre": "Prof. Dr.",
                "titelPost": "",
                "kennungen": ["di38qex"],
                "status": "aktiv",
            },
        },
    )

    person = client.get_person("00000000001F17E0")

    assert person.lrz_id == "00000000001F17E0"
    assert person.benutzername == "barekzai"
    assert person.kennungen == ["di38qex"]


def test_get_user(register_response, client: SimApiClient) -> None:
    url = f"{DEFAULT_BASE_URL}/user/di38qex"
    register_response(
        url,
        json_data={
            "kennung": "di38qex",
            "mwnlrzid": "0000000001579799",
            "status": "aktiv",
            "status_num": 1,
            "uid": "4355134",
            "gid": "3888589",
            "projekt": "pn69ju",
            "kennungstyp": "pers",
            "daten": {
                "vorname": "Mares",
                "nachname": "Barekzai",
            },
        },
    )

    user = client.get_user("di38qex")

    assert user.kennung == "di38qex"
    assert user.projekt == "pn69ju"
    assert user.daten["vorname"] == "Mares"


def test_error_handling(register_response, client: SimApiClient) -> None:
    url = f"{DEFAULT_BASE_URL}/service/AI/groups"
    register_response(
        url,
        status=500,
        json_data={"message": "Internal error"},
    )

    with pytest.raises(SimApiError):
        client.list_groups()
