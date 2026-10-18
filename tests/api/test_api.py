"""The HTTP and agent surfaces, checked against the library they adapt.

Two things are being pinned here. The first is that every route answers what the
library answers, in the shape the command line prints, because a reader
comparing the two must never find a difference. The second is the pair of
refusals the surface is built around: it executes nobody's code, and it clones
nothing unless the operator said so.
"""

from __future__ import annotations

import inspect

import pytest
import yaml
from fastapi.testclient import TestClient

from saggio import __version__, placed_model
from saggio.api.app import CLONE_SWITCH, create_app

A_MODEL = {
    "unit_of_work": {"name": "one request"},
    "deployment": {"provider": "on-prem"},
    "scenarios": [
        {
            "name": "cold",
            "costs": {
                "carbon": {"value": 1.4, "unit": "gCO2e", "status": "estimated"},
                "water": {"value": None, "unit": "L", "status": "TODO"},
            },
        }
    ],
}


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app(allow_clone=False))


# --- What the deployment says about itself ------------------------------------


def test_health_reports_the_version_and_what_this_deployment_will_not_do(
    client: TestClient,
) -> None:
    body = client.get("/health").json()
    assert body["version"] == __version__
    assert body["runs_repository_code"] is False
    assert body["clones_repositories"] is False


# --- The surface agrees with the library it adapts ----------------------------


def test_the_placement_route_returns_exactly_what_the_library_returns(
    client: TestClient,
) -> None:
    # The whole reason the assembly moved out of the command line. A field that
    # differed between these two would be the package disagreeing with itself
    # about which line of an inventory a figure goes on.
    assert client.post("/scopes", json={"cost_model": A_MODEL}).json() == placed_model(A_MODEL)


def test_the_questions_route_ranks_by_what_answering_would_close(client: TestClient) -> None:
    # The route reports; it never computes or writes. A reader holding an open
    # model over HTTP needs the same ordering a reader at a terminal gets.
    open_model = {
        "assumptions": {"power_draw": {"value": 50.0, "unit": "W", "status": "estimated"}},
        "scenarios": [
            {
                "name": "one",
                "runtime": {"value": None, "unit": "s", "status": "TODO"},
                "costs": {
                    "energy": {
                        "value": None,
                        "unit": "kWh",
                        "status": "TODO",
                        "derived_from": ["scenarios[0].runtime", "assumptions.power_draw"],
                    }
                },
            }
        ],
    }
    body = client.post("/next", json={"cost_model": open_model}).json()
    assert body["open_total"] == 2
    assert body["questions"][0]["path"] == "scenarios[0].runtime"
    assert body["questions"][0]["closes"] == ["scenarios[0].costs.energy"]


def test_a_vendor_machine_is_placed_in_category_one(client: TestClient) -> None:
    rented = {**A_MODEL, "deployment": {"provider": "aws"}}
    placed = client.post("/scopes", json={"cost_model": rented}).json()["placements"][0]
    assert placed["scope"] == "3"
    assert placed["category"] == 1


def test_a_scenario_nobody_has_is_refused_rather_than_substituted(client: TestClient) -> None:
    answer = client.post("/scopes?scenario=hot", json={"cost_model": A_MODEL})
    assert answer.status_code == 422
    assert "cold" in answer.json()["detail"]


def test_the_yaml_a_person_pastes_and_the_json_a_program_sends_agree(
    client: TestClient,
) -> None:
    # The same document arriving two ways has to produce one answer, or the
    # surface has quietly made the format part of the result.
    text = yaml.safe_dump(A_MODEL, sort_keys=False)
    as_text = client.post("/scopes", json={"yaml_text": text}).json()
    as_document = client.post("/scopes", json={"cost_model": A_MODEL}).json()
    assert as_text == as_document


def test_a_request_carrying_both_forms_or_neither_is_refused(client: TestClient) -> None:
    assert client.post("/scopes", json={}).status_code == 422
    both = {"cost_model": A_MODEL, "yaml_text": "project: {name: x}"}
    assert client.post("/scopes", json=both).status_code == 422


def test_text_that_is_not_a_cost_model_is_refused_with_the_parser_s_complaint(
    client: TestClient,
) -> None:
    answer = client.post("/scopes", json={"yaml_text": "just a sentence"})
    assert answer.status_code == 422
    assert "mapping" in answer.json()["detail"]


def test_validation_carries_the_weakest_status_the_way_the_command_line_does(
    client: TestClient,
) -> None:
    body = client.post("/validate", json={"cost_model": A_MODEL}).json()
    assert set(body) >= {"ok", "errors", "warnings", "overall_status"}
    assert body["overall_status"] == "TODO"


def test_both_reports_render(client: TestClient) -> None:
    markdown = client.post("/render", json={"cost_model": A_MODEL}).json()
    assert markdown["report"].startswith("# Cost of running")
    page = client.post("/render", json={"cost_model": A_MODEL, "format": "html"}).json()
    assert page["report"].lstrip().startswith("<!")


def test_the_gate_passes_an_unchanged_model_and_fails_a_moved_one(client: TestClient) -> None:
    moved = {
        **A_MODEL,
        "scenarios": [
            {
                "name": "cold",
                "costs": {"carbon": {"value": 9.9, "unit": "gCO2e", "status": "estimated"}},
            }
        ],
    }
    assert client.post("/diff", json={"before": A_MODEL, "after": A_MODEL}).json()["passes"]
    assert not client.post("/diff", json={"before": A_MODEL, "after": moved}).json()["passes"]


def test_a_catalogue_nobody_has_is_a_404_that_names_the_ones_there(client: TestClient) -> None:
    answer = client.get("/catalog/unicorns")
    assert answer.status_code == 404
    assert "grid" in answer.json()["detail"]


def test_a_catalogue_row_still_carries_where_it_came_from(client: TestClient) -> None:
    # The provenance is the product. A surface that dropped it while serialising
    # would hand a reader a number with nothing behind it.
    countries = client.get("/catalog/grid").json()["sections"]["countries"]
    france = countries["FR"]
    assert france["carbon_source_url"].startswith("http")
    assert france["carbon_retrieved_date"]


# --- The refusals the surface is built around ---------------------------------


def test_the_surface_offers_no_way_to_run_anybody_s_code(client: TestClient) -> None:
    # Measuring executes a slice of a repository with the permissions of whoever
    # started the process. Over HTTP those are the server's, and there is nobody
    # at a terminal to ask, so the capability has no route rather than a guard.
    paths = {route.path for route in create_app(allow_clone=False).routes}
    assert not {path for path in paths if "measure" in path or "run" in path}

    source = inspect.getsource(__import__("saggio.api.app", fromlist=["app"]))
    assert "run_slice" not in source
    assert "subprocess" not in source
    assert "run=True" not in source


def test_cloning_is_refused_by_default_and_the_refusal_says_what_to_do(
    client: TestClient,
) -> None:
    answer = client.post("/audit", json={"git_url": "https://example.invalid/x.git"})
    assert answer.status_code == 403
    detail = answer.json()["detail"]
    assert CLONE_SWITCH in detail
    assert "saggio audit ." in detail


def test_the_environment_can_turn_cloning_on_and_nothing_else_can(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(CLONE_SWITCH, "1")
    assert TestClient(create_app()).get("/health").json()["clones_repositories"] is True
    monkeypatch.setenv(CLONE_SWITCH, "no")
    assert TestClient(create_app()).get("/health").json()["clones_repositories"] is False


# --- The agent surface is the HTTP one, read by a machine ---------------------


def test_every_route_becomes_a_tool_under_the_name_the_route_declared() -> None:
    from saggio.api.mcp import attach_mcp

    application = create_app(allow_clone=False)
    tools = {tool.name for tool in attach_mcp(application).tools}
    assert {"place_in_inventory", "validate_cost_model", "render_report"} <= tools
    assert not {name for name in tools if "measure" in name}


def test_the_protocol_endpoint_is_mounted_beside_the_routes() -> None:
    from saggio.api.mcp import MOUNT_PATH, create_mcp_app

    paths = {route.path for route in create_mcp_app(allow_clone=False).routes}
    assert MOUNT_PATH in paths
    assert "/scopes" in paths


def test_the_protocol_server_reports_a_version_and_not_a_paragraph() -> None:
    # fastapi-mcp builds the protocol server as `Server(name, description)`, and
    # that constructor's second parameter is the version. Left alone, a client
    # listing its servers shows this package's whole description where a version
    # belongs, and an agent asked which version answered it reports a paragraph.
    from saggio.api.mcp import attach_mcp

    server = attach_mcp(create_app(allow_clone=False))
    assert server.server.version == __version__


def test_a_tool_tells_an_agent_what_the_route_tells_a_reader() -> None:
    # The descriptions are generated from the route docstrings, which is the
    # reason there is no second copy of them to drift. This is the test that
    # notices if that ever stops being true.
    from saggio.api.mcp import attach_mcp

    tools = {tool.name: tool for tool in attach_mcp(create_app(allow_clone=False)).tools}
    description = tools["place_in_inventory"].description or ""
    assert "scope" in description.lower()
    assert "market-based" in description.lower()
