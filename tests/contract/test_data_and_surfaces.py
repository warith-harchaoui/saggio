"""Contracts the package must keep with its own data and between its surfaces."""

from __future__ import annotations

import re
from datetime import date
from importlib import resources
from pathlib import Path

import pytest
import yaml

from saggio.catalog.registry import (
    BUNDLED_CATALOGS,
    INTERNAL_DEFAULT_SOURCE,
    SECTION_OF_KIND,
    Catalog,
    carries_numbers,
)
from saggio.estimate.energy import (
    carbon_from_energy,
    facility_energy,
    it_energy_from_runtime,
    money_from_energy,
)
from saggio.model import SCHEMA_VERSION, CostModel, Quantity, overall_status, validate
from saggio.report import render_html, render_markdown
from saggio.templates import template_mapping, template_names

ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def catalog_rows() -> list[tuple[str, str, dict]]:
    rows: list[tuple[str, str, dict]] = []
    for kind, (name, section) in SECTION_OF_KIND.items():
        for key, row in (
            Catalog.load(name, overlay=Path("/nonexistent-overlay")).rows(section).items()
        ):
            rows.append((kind, key, row))
    return rows


ROWS = catalog_rows()


# --- The catalogues ----------------------------------------------------------


@pytest.mark.parametrize("name", BUNDLED_CATALOGS)
def test_every_bundled_catalogue_is_in_the_wheel(name: str) -> None:
    text = resources.files("saggio.data").joinpath(f"{name}.yaml").read_text("utf-8")
    assert yaml.safe_load(text)


@pytest.mark.parametrize("name", BUNDLED_CATALOGS)
def test_every_bundled_catalogue_declares_the_current_schema(name: str) -> None:
    text = resources.files("saggio.data").joinpath(f"{name}.yaml").read_text("utf-8")
    assert yaml.safe_load(text)["schema_version"] == SCHEMA_VERSION


@pytest.mark.parametrize(("kind", "key", "row"), ROWS, ids=[f"{k}:{key}" for k, key, _ in ROWS])
def test_every_row_that_asserts_a_number_says_where_it_came_from(
    kind: str, key: str, row: dict
) -> None:
    if not carries_numbers(row):
        return
    assert row.get("source_url"), f"{kind} {key} asserts a number with no source"
    assert ISO_DATE.match(str(row.get("retrieved_date", ""))), f"{kind} {key} has no ISO date"


@pytest.mark.parametrize(("kind", "key", "row"), ROWS, ids=[f"{k}:{key}" for k, key, _ in ROWS])
def test_no_provenance_date_is_in_the_future(kind: str, key: str, row: dict) -> None:
    retrieved = row.get("retrieved_date")
    if isinstance(retrieved, str) and ISO_DATE.match(retrieved):
        assert date.fromisoformat(retrieved) <= date.today(), f"{kind} {key} was read in the future"


@pytest.mark.parametrize(("kind", "key", "row"), ROWS, ids=[f"{k}:{key}" for k, key, _ in ROWS])
def test_a_source_url_is_a_link_or_an_admitted_default(kind: str, key: str, row: dict) -> None:
    source = row.get("source_url")
    if source is None:
        return
    assert str(source).startswith("http") or source == INTERNAL_DEFAULT_SOURCE


@pytest.mark.parametrize("kind", sorted(SECTION_OF_KIND))
def test_keys_are_unique_within_a_catalogue(kind: str) -> None:
    name, section = SECTION_OF_KIND[kind]
    text = resources.files("saggio.data").joinpath(f"{name}.yaml").read_text("utf-8")
    keys = [row["key"] for row in yaml.safe_load(text)[section]]
    assert len(keys) == len(set(keys))


@pytest.mark.parametrize("kind", sorted(SECTION_OF_KIND))
def test_every_key_is_a_string(kind: str) -> None:
    # Unquoted, YAML reads NO as the boolean false, and Norway vanishes from the
    # catalogue with no error anywhere.
    name, section = SECTION_OF_KIND[kind]
    text = resources.files("saggio.data").joinpath(f"{name}.yaml").read_text("utf-8")
    assert all(isinstance(row["key"], str) for row in yaml.safe_load(text)[section])


def test_every_instance_names_an_accelerator_the_catalogue_knows() -> None:
    gpus = Catalog.load("hardware").keys("gpus")
    for key, row in Catalog.load("instances").rows("instances").items():
        gpu = row.get("gpu_key")
        assert gpu is None or gpu in gpus, f"instance {key} names unknown accelerator {gpu}"


def test_every_country_row_is_complete() -> None:
    for key, row in Catalog.load("grid").rows("countries").items():
        assert row.get("name"), f"{key} has no name"
        assert row.get("carbon_gco2e_per_kwh") is not None, f"{key} has no carbon intensity"
        assert row.get("timezones"), f"{key} lists no timezone"


def test_no_timezone_belongs_to_two_countries() -> None:
    # A timezone in two countries resolves to neither, which is correct but makes
    # the inference useless; a duplicate here is a data mistake, not a policy.
    seen: dict[str, str] = {}
    for key, row in Catalog.load("grid").rows("countries").items():
        for zone in row.get("timezones") or []:
            assert zone not in seen, f"{zone} is claimed by {seen.get(zone)} and {key}"
            seen[zone] = key


def test_every_service_says_where_to_price_it_and_how_to_spot_it() -> None:
    for key, row in Catalog.load("services").rows("services").items():
        assert row.get("pricing_source_url", "").startswith("http"), f"{key} has no pricing page"
        assert row.get("detect"), f"{key} has no detection hints"


def test_no_detection_hint_is_a_bare_word() -> None:
    # A bare package name matches any sentence that mentions it, including this
    # one, and used to report services that a repository only wrote about.
    for key, row in Catalog.load("services").rows("services").items():
        for hint in row["detect"]:
            shaped_like_code = hint.startswith(("import ", "from ")) or hint.endswith(("(", ")"))
            assert shaped_like_code or "." in hint, f"{key}: {hint!r} is too loose"


def test_no_service_row_ships_a_price() -> None:
    # A price copied today is wrong by next quarter, and a stale one shipped as
    # authoritative is exactly the dishonesty this package exists to prevent.
    for key, row in Catalog.load("services").rows("services").items():
        assert not carries_numbers(row), f"{key} ships a number"


# --- The templates -----------------------------------------------------------


@pytest.mark.parametrize("name", template_names())
def test_every_template_passes_its_own_validation(name: str) -> None:
    report = validate(template_mapping(name))
    assert report.ok, report.to_text()


def test_the_annotated_templates_arithmetic_is_exact() -> None:
    model = CostModel.from_mapping(template_mapping("annotated"))
    runtime = Quantity.from_mapping(model.get("scenarios[0].runtime"))
    power = Quantity.from_mapping(model.get("assumptions.power_draw"))
    pue = Quantity.from_mapping(model.get("assumptions.pue"))
    price = Quantity.from_mapping(model.get("assumptions.electricity_price"))
    grid = Quantity.from_mapping(model.get("assumptions.grid_carbon_intensity"))

    machine = it_energy_from_runtime(runtime, power)
    facility = facility_energy(machine, pue)

    stated_machine = Quantity.from_mapping(model.get("assumptions.machine_energy"))
    stated_energy = Quantity.from_mapping(model.get("scenarios[0].costs.energy"))
    stated_money = Quantity.from_mapping(model.get("scenarios[0].costs.money"))
    stated_carbon = Quantity.from_mapping(model.get("scenarios[0].costs.carbon"))

    assert stated_machine.value == pytest.approx(machine.value, rel=1e-4)
    assert stated_energy.value == pytest.approx(facility.value, rel=1e-4)
    assert stated_money.value == pytest.approx(money_from_energy(facility, price).value, rel=1e-4)
    assert stated_carbon.value == pytest.approx(carbon_from_energy(facility, grid).value, rel=1e-4)


def test_the_minimal_template_states_no_number_at_all() -> None:
    # A scaffold full of plausible defaults would tell a lie that survives into a
    # report; one full of TODOs tells the truth.
    model = CostModel.from_mapping(template_mapping("minimal"))
    assert all(not quantity.is_known() for _, quantity in model.typed_quantities())


def test_the_annotated_template_exercises_a_custom_dimension() -> None:
    model = CostModel.from_mapping(template_mapping("annotated"))
    assert "egress" in model.registry


def test_every_template_declares_the_current_schema() -> None:
    for name in template_names():
        assert template_mapping(name)["schema_version"] == SCHEMA_VERSION


# --- Between the surfaces ----------------------------------------------------


@pytest.mark.parametrize("name", template_names())
def test_both_reports_render_every_template(name: str) -> None:
    model = template_mapping(name)
    assert render_markdown(model).startswith("# Cost of running")
    assert render_html(model).startswith("<!doctype html>")


@pytest.mark.parametrize("name", template_names())
def test_both_reports_show_the_same_verdict(name: str) -> None:
    # The two reports are two renderings of one model, so they have to agree on
    # the one sentence a reader takes away from either: how far it can be trusted.
    model = template_mapping(name)
    weakest = overall_status(model)
    assert weakest is not None
    markdown, html = render_markdown(model), render_html(model)
    assert f"which is `{weakest}`" in markdown
    assert f"which is <code>{weakest}</code>" in html


def test_every_report_asset_is_in_the_wheel() -> None:
    for asset in ("report.html", "report.css", "report.js", "i18n.yaml", "logo.png"):
        assert resources.files("saggio.data.report").joinpath(asset).is_file()


def test_the_public_api_is_importable_and_complete() -> None:
    import saggio

    for name in saggio.__all__:
        assert hasattr(saggio, name), f"__all__ names {name}, which does not exist"


def test_the_command_line_reaches_only_the_library() -> None:
    # The command line is one way of reaching the library. Anything it could do
    # that the library cannot would be something a library caller was locked out
    # of, so every verb has to route through a public function.
    import inspect

    from saggio.cli import commands

    source = inspect.getsource(commands)
    assert "subprocess" not in source
    assert "yaml.safe_load" not in source


# --- The platforms, said once and checked everywhere they are repeated --------


def test_the_ci_matrix_matches_the_platforms_the_package_supports() -> None:
    # The first time these drifted, the package had just stopped importing on
    # Windows and the workflow still ran two Windows jobs that could only fail.
    # A list of supported platforms that lives in two files needs a test.
    import re

    from saggio.analyze.capability import SUPPORTED_PLATFORMS

    workflow = (
        _repository_root().joinpath(".github", "workflows", "ci.yml").read_text(encoding="utf-8")
    )
    match = re.search(r"^\s*os:\s*\[([^\]]+)\]", workflow, re.MULTILINE)
    assert match, "the workflow no longer declares an os matrix in a shape this can read"
    runners = {name.strip() for name in match.group(1).split(",")}

    expected = {"linux": "ubuntu-latest", "darwin": "macos-latest"}
    assert set(SUPPORTED_PLATFORMS) == set(expected), (
        "a platform was added or removed; teach this test which runner it maps to"
    )
    assert runners == set(expected.values()), (
        f"the CI matrix runs on {sorted(runners)} but the package supports "
        f"{sorted(SUPPORTED_PLATFORMS)}"
    )


def test_no_job_runs_on_a_platform_that_was_excluded() -> None:
    # Prose is allowed to mention Windows — the comment explains why it is not
    # here, which is worth keeping. What must not come back is a *runner*.
    workflow = (
        _repository_root().joinpath(".github", "workflows", "ci.yml").read_text(encoding="utf-8")
    )
    runner_lines = [
        line for line in workflow.splitlines() if line.strip().startswith(("os:", "runs-on:"))
    ]
    assert runner_lines, "the workflow declares no runners in a shape this can read"
    assert not any("windows" in line.lower() for line in runner_lines)


def _repository_root() -> Path:
    """Return the checkout this test file lives in."""
    return Path(__file__).resolve().parents[2]
