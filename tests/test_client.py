from __future__ import annotations

import json
from typing import Callable, Dict, Tuple

import pytest

from sim_api_wrapper.auth import build_basic_auth_header
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


def test_get_environment(register_response, client: SimApiClient) -> None:
    url = f"{DEFAULT_BASE_URL}/umgebung"
    register_response(url, json_data={"umgebung": "production", "plafoList_count": 2})

    environment = client.get_environment()

    assert environment["umgebung"] == "production"
    assert environment["plafoList_count"] == 2


def test_get_current_user(register_response, client: SimApiClient) -> None:
    url = f"{DEFAULT_BASE_URL}/whoami"
    register_response(url, json_data={"kennung": "di38qex"})

    info = client.get_current_user()

    assert info["kennung"] == "di38qex"


def test_get_service_characteristics(register_response, client: SimApiClient) -> None:
    url = f"{DEFAULT_BASE_URL}/service/AI/egh"
    register_response(url, json_data={"dn": "cn=AI,ou=services"})

    data = client.get_service_characteristics("AI")

    assert data["dn"] == "cn=AI,ou=services"


def test_get_group_rights(register_response, client: SimApiClient) -> None:
    url = f"{DEFAULT_BASE_URL}/service/AI/group/pn69ju-ai-c/user/di38qex/grprights"
    register_response(url, json_data={"rights": {"Verwalter": ["group-admin"]}})

    rights = client.get_group_rights("AI", "pn69ju-ai-c", "di38qex")

    assert rights["rights"]["Verwalter"] == ["group-admin"]


def test_get_permissions_metadata(register_response, client: SimApiClient) -> None:
    url = f"{DEFAULT_BASE_URL}/permissions"
    register_response(
        url,
        json_data={
            "code": 0,
            "message": "OK",
            "data": {
                "storeMetadata": {"type": "file"},
                "allPermissions": {"&free": ["read"]},
            },
        },
    )

    metadata = client.get_permissions_metadata()

    assert metadata["storeMetadata"]["type"] == "file"


def test_get_user_permissions(register_response, client: SimApiClient) -> None:
    url = f"{DEFAULT_BASE_URL}/permissions/di38qex"
    register_response(
        url,
        json_data={
            "code": 0,
            "message": "OK",
            "data": {
                "di38qex": {"&all": {"&free": {"read": ""}}},
                "@all-authenticated-users": {"&free": {"login": ""}},
            },
        },
    )

    permissions = client.get_user_permissions("di38qex")

    assert "di38qex" in permissions
    assert permissions["di38qex"]["&all"]["&free"]["read"] == ""


def test_token_authentication(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    token_file = tmp_path / ".simapi.env"
    token_file.write_text("SIMAPI_TOKEN=test-token\n", encoding="utf-8")

    def fail_netrc(*args, **kwargs):  # pragma: no cover - should not be used
        raise AssertionError("netrc should not be accessed when token authentication is available")

    monkeypatch.setattr("sim_api_wrapper.client.load_netrc_credentials", fail_netrc)

    client = SimApiClient(token_path=token_file)
    try:
        assert client._auth_header == "Basic test-token"
    finally:
        client.close()


def test_invalid_token_falls_back_to_netrc(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    token_file = tmp_path / ".simapi.env"
    token_file.write_text("SIMAPI_TOKEN=\n", encoding="utf-8")

    expected_header = build_basic_auth_header("user", "pass")

    def fake_netrc(base_url, netrc_path):
        return "user", "pass"

    monkeypatch.setattr("sim_api_wrapper.client.load_netrc_credentials", fake_netrc)

    client = SimApiClient(token_path=token_file)
    try:
        assert client._auth_header == expected_header
    finally:
        client.close()


def test_list_groups(register_response, client: SimApiClient) -> None:
    url = f"{DEFAULT_BASE_URL}/service/AI/groups"
    register_response(url, json_data=["a1101", "a1101-ai-c"])

    groups = client.list_groups("AI")

    assert groups == ["a1101", "a1101-ai-c"]


def test_get_group_members(register_response, client: SimApiClient) -> None:
    url = f"{DEFAULT_BASE_URL}/service/AI/groups/pn69ju-ai-c/members?solve=false"
    register_response(url, json_data=["di25koy", "di29xub"])

    members = client.get_group_members("AI", "pn69ju-ai-c")

    assert members == ["di25koy", "di29xub"]


def test_get_group_admins(register_response, client: SimApiClient) -> None:
    url = f"{DEFAULT_BASE_URL}/service/AI/groups/pn69ju-ai-c/grpadmins"
    register_response(url, json_data=["di25koy", "di29xub"])

    admins = client.get_group_admins("AI", "pn69ju-ai-c")

    assert admins == ["di25koy", "di29xub"]


def test_get_group_details(register_response, client: SimApiClient) -> None:
    url = f"{DEFAULT_BASE_URL}/service/AI/group/pn69ju-ai-c"
    register_response(url, json_data={"name": "pn69ju-ai-c", "gid": "12345"})

    details = client.get_group_details("AI", "pn69ju-ai-c")

    assert details["gid"] == "12345"


def test_is_group_member(register_response, client: SimApiClient) -> None:
    url = f"{DEFAULT_BASE_URL}/service/AI/group/pn69ju-ai-c/members/di38qex"
    register_response(url, json_data=True)

    assert client.is_group_member("AI", "pn69ju-ai-c", "di38qex") is True


def test_is_group_master_user(register_response, client: SimApiClient) -> None:
    url = f"{DEFAULT_BASE_URL}/service/AI/group/pn69ju-ai-c/masteruser/di38qex"
    register_response(url, json_data=False)

    assert client.is_group_master_user("AI", "pn69ju-ai-c", "di38qex") is False


def test_is_group_admin(register_response, client: SimApiClient) -> None:
    url = f"{DEFAULT_BASE_URL}/service/AI/group/pn69ju-ai-c/grpadmin/di38qex"
    register_response(url, json_data=True)

    assert client.is_group_admin("AI", "pn69ju-ai-c", "di38qex") is True


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


def test_list_org_projects(register_response, client: SimApiClient) -> None:
    url = f"{DEFAULT_BASE_URL}/org/TUM/projects"
    register_response(
        url,
        json_data={"code": 0, "message": "OK", "data": ["pn69ju", "pn70ka"]},
    )

    projects = client.list_org_projects("TUM")

    assert projects == ["pn69ju", "pn70ka"]


def test_get_org_project_details(register_response, client: SimApiClient) -> None:
    url = f"{DEFAULT_BASE_URL}/org/TUM/project/uk431"
    register_response(
        url,
        json_data={
            "code": 0,
            "message": "OK",
            "data": {"name": "Test", "status": "active"},
        },
    )

    details = client.get_org_project_details("TUM", "uk431")

    assert details["status"] == "active"


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


def test_get_project_master_users(register_response, client: SimApiClient) -> None:
    url = f"{DEFAULT_BASE_URL}/project/pn69ju/mudusers"
    register_response(url, json_data=["di38qex", "ga75ded"])

    mud_users = client.get_project_master_users("pn69ju")

    assert mud_users == ["di38qex", "ga75ded"]


def test_list_service_projects(register_response, client: SimApiClient) -> None:
    url = f"{DEFAULT_BASE_URL}/project/service/AI"
    register_response(
        url,
        json_data=[
            {"name": "pn69ju", "status": "active"},
            {"name": "pn70ka", "status": "archived"},
        ],
    )

    projects = client.list_service_projects("AI")

    assert projects[0]["name"] == "pn69ju"
    assert projects[1]["status"] == "archived"


def test_list_org_types(register_response, client: SimApiClient) -> None:
    url = f"{DEFAULT_BASE_URL}/auswahlliste/orgtypes"
    register_response(
        url,
        json_data={"code": 0, "message": "OK", "data": ["Fakultät", "Lehrstuhl"]},
    )

    org_types = client.list_org_types()

    assert org_types == ["Fakultät", "Lehrstuhl"]


def test_get_vweb_user(register_response, client: SimApiClient) -> None:
    url = f"{DEFAULT_BASE_URL}/service/vweb/user/di38qex/vwebserver"
    register_response(
        url,
        json_data={
            "code": 0,
            "message": "OK",
            "data": {"name": "di38qex", "vwebserver": []},
        },
    )

    data = client.get_vweb_user("di38qex")

    assert data["name"] == "di38qex"


def test_list_personal_homepages(register_response, client: SimApiClient) -> None:
    url = f"{DEFAULT_BASE_URL}/persHomepage"
    register_response(
        url,
        json_data={
            "di38qex": [
                {"fqdn": "example.lrz.de", "path": "~di38qex", "https": True},
            ]
        },
    )

    pages = client.list_personal_homepages()

    assert pages["di38qex"][0]["fqdn"] == "example.lrz.de"


def test_is_service_admin(register_response, client: SimApiClient) -> None:
    url = f"{DEFAULT_BASE_URL}/service/AI/serviceadmin/di38qex"
    register_response(url, json_data=False)

    assert client.is_service_admin("AI", "di38qex") is False


def test_list_managed_groups(register_response, client: SimApiClient) -> None:
    url = f"{DEFAULT_BASE_URL}/service/AI/user/di38qex/managedgroups"
    register_response(url, json_data=["pn69ju-ai-c", "pn69ju-ai-w"])

    groups = client.list_managed_groups("AI", "di38qex")

    assert groups == ["pn69ju-ai-c", "pn69ju-ai-w"]


def test_list_group_memberships(register_response, client: SimApiClient) -> None:
    url = f"{DEFAULT_BASE_URL}/service/AI/user/di38qex/groupmembership"
    register_response(url, json_data=["pn69ju-ai-c"])

    memberships = client.list_group_memberships("AI", "di38qex")

    assert memberships == ["pn69ju-ai-c"]


def test_list_user_services(register_response, client: SimApiClient) -> None:
    url = f"{DEFAULT_BASE_URL}/user/di38qex/services"
    register_response(
        url,
        json_data=[{"dienstname": "AI", "status": "active"}],
    )

    services = client.list_user_services("di38qex")

    assert services[0]["dienstname"] == "AI"


def test_get_password_metadata(register_response, client: SimApiClient) -> None:
    url = f"{DEFAULT_BASE_URL}/pwd"
    register_response(url, json_data={"policytext": {"en": "Password policy"}})

    metadata = client.get_password_metadata()

    assert metadata["policytext"]["en"] == "Password policy"


def test_get_user_password_metadata(register_response, client: SimApiClient) -> None:
    url = f"{DEFAULT_BASE_URL}/user/di38qex/pwd"
    register_response(
        url,
        json_data={
            "code": 0,
            "message": "OK",
            "data": {"changeable": True, "status": 1},
        },
    )

    data = client.get_user_password_metadata("di38qex")

    assert data["changeable"] is True


def test_is_password_pwned(register_response, client: SimApiClient) -> None:
    url = f"{DEFAULT_BASE_URL}/user/di38qex/pwned"
    register_response(
        url,
        json_data={
            "code": 0,
            "message": "OK",
            "data": {"pwned": False, "user": "di38qex"},
        },
    )

    assert client.is_password_pwned("di38qex") is False


def test_list_exchange_distributions(register_response, client: SimApiClient) -> None:
    url = f"{DEFAULT_BASE_URL}/v2/verteiler"
    register_response(url, json_data=["LMZVD06GI-Intern", "AnotherList"])

    lists = client.list_exchange_distributions()

    assert lists == ["LMZVD06GI-Intern", "AnotherList"]


def test_get_exchange_distribution(register_response, client: SimApiClient) -> None:
    url = f"{DEFAULT_BASE_URL}/v2/verteiler/LMZVD06GI-Intern"
    register_response(
        url,
        json_data={"name": "LMZVD06GI-Intern", "displayname": "Internal"},
    )

    details = client.get_exchange_distribution("LMZVD06GI-Intern")

    assert details["displayname"] == "Internal"


def test_get_exchange_distribution_admins(register_response, client: SimApiClient) -> None:
    url = f"{DEFAULT_BASE_URL}/v2/verteiler/LMZVD06GI-Intern/exchangeadmin"
    register_response(url, json_data=["di38qex"])

    admins = client.get_exchange_distribution_admins("LMZVD06GI-Intern")

    assert admins == ["di38qex"]


def test_error_handling(register_response, client: SimApiClient) -> None:
    url = f"{DEFAULT_BASE_URL}/service/AI/groups"
    register_response(
        url,
        status=500,
        json_data={"message": "Internal error"},
    )

    with pytest.raises(SimApiError):
        client.list_groups("AI")
