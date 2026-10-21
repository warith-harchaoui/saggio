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


def offenders(check) -> list[str]:
    """Return what every catalogue row has to say against one rule.

    One claim, checked over every row, reporting all of them. These were
    parametrised per row, which turned three rules into 333 cases that each
    said the same sentence about a different key. Collapsing them loses
    nothing and gains the thing that matters when one actually fails: every
    offending row named at once, rather than whichever pytest stopped at.
    """
    found: list[str] = []
    for kind, key, row in ROWS:
        complaint = check(kind, key, row)
        if complaint:
            found.append(complaint)
    return found


def test_every_row_that_asserts_a_number_says_where_it_came_from() -> None:
    """A row-level `source_url` used to be the whole claim.

    That is how a grid row ended up citing an emissions dataset for its
    electricity tariff: one URL stood for every field, including the ones
    nobody had checked. A row may state its provenance per column instead, and
    either shape has to say where the numbers came from and when they were read.
    """

    def check(kind: str, key: str, row: dict) -> str | None:
        if not carries_numbers(row):
            return None
        sources = [n for n in row if n == "source_url" or n.endswith("_source_url")]
        dates = [n for n in row if n == "retrieved_date" or n.endswith("_retrieved_date")]
        if not sources:
            return f"{kind} {key} asserts a number with no source"
        empty = [n for n in sources if not row[n]]
        if empty:
            return f"{kind} {key} has an empty {', '.join(empty)}"
        if not dates:
            return f"{kind} {key} asserts a number with no date"
        unparsed = [n for n in dates if not ISO_DATE.match(str(row[n]))]
        if unparsed:
            return f"{kind} {key} has no ISO date in {', '.join(unparsed)}"
        return None

    found = offenders(check)
    assert not found, "\n".join(found)


def test_no_provenance_date_is_in_the_future() -> None:
    """A date later than today is a typo, and must not buy unearned freshness."""

    def check(kind: str, key: str, row: dict) -> str | None:
        ahead = [
            name
            for name, value in row.items()
            if (name == "retrieved_date" or name.endswith("_retrieved_date"))
            and isinstance(value, str)
            and ISO_DATE.match(value)
            and date.fromisoformat(value) > date.today()
        ]
        return f"{kind} {key} was read in the future, per {', '.join(ahead)}" if ahead else None

    found = offenders(check)
    assert not found, "\n".join(found)


def test_a_source_url_is_a_link_or_an_admitted_default() -> None:
    """Either a reader can follow it, or it says plainly that nobody read one."""

    def check(kind: str, key: str, row: dict) -> str | None:
        bad = [
            name
            for name, source in row.items()
            if (name == "source_url" or name.endswith("_source_url"))
            and not (str(source).startswith("http") or source == INTERNAL_DEFAULT_SOURCE)
        ]
        return (
            f"{kind} {key}: {', '.join(bad)} is neither a link nor an admitted default"
            if bad
            else None
        )

    found = offenders(check)
    assert not found, "\n".join(found)


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


def test_ci_runs_only_on_platforms_the_package_supports() -> None:
    """Every runner in the workflow is one `import saggio` would survive.

    The first time these drifted, the package had just stopped importing on
    Windows and the workflow still ran two Windows jobs that could only fail.

    What this asserts changed when the workflow shrank to a single job. It used
    to require the runners to *equal* the supported platforms, which quietly
    also asserted that CI covered all of them. It does not: the workflow runs
    Linux only, and says so in its own header. The invariant worth keeping is the
    one that caught the real bug — no job may run somewhere the package refuses
    to import.
    """
    import re

    from saggio.analyze.capability import SUPPORTED_PLATFORMS

    workflow = (
        _repository_root().joinpath(".github", "workflows", "ci.yml").read_text(encoding="utf-8")
    )
    runner_of_platform = {"linux": "ubuntu-latest", "darwin": "macos-latest"}
    allowed = set(runner_of_platform.values())
    assert set(SUPPORTED_PLATFORMS) == set(runner_of_platform), (
        "a platform was added or removed; teach this test which runner it maps to"
    )

    # The leading "- " of a matrix `include:` entry is stripped before matching,
    # and a bare `os: macos-latest` is read as well as the bracketed list form.
    # Without both, this saw `runs-on: ${{ matrix.os }}` and nothing else: the
    # runners were declared one line lower, as `- os: macos-latest`, and the
    # check that exists to stop a runner coming back could not see a runner.
    runners: set[str] = set()
    for line in workflow.splitlines():
        stripped = line.strip().removeprefix("- ")
        if stripped.startswith("runs-on:"):
            runners.add(stripped.split(":", 1)[1].strip())
        elif stripped.startswith("os:"):
            value = stripped.split(":", 1)[1].strip()
            inside = re.search(r"\[([^\]]+)\]", value)
            if inside:
                runners.update(name.strip() for name in inside.group(1).split(","))
            elif value:
                runners.add(value)
    assert runners, "the workflow declares no runner at all"
    assert allowed <= runners, (
        f"the workflow declares {sorted(runners)}, which does not include every "
        f"runner this test knows how to read -- the shapes it parses have drifted "
        f"away from the shapes the file uses"
    )

    stray = {name for name in runners if not name.startswith("${{") and name not in allowed}
    assert not stray, (
        f"the workflow runs on {sorted(stray)}, which the package does not support "
        f"({sorted(SUPPORTED_PLATFORMS)})"
    )


def test_no_job_runs_on_a_platform_that_was_excluded() -> None:
    # Prose is allowed to mention Windows — the comment explains why it is not
    # here, which is worth keeping. What must not come back is a *runner*.
    workflow = (
        _repository_root().joinpath(".github", "workflows", "ci.yml").read_text(encoding="utf-8")
    )
    # Same leading "- " as above: a matrix `include:` entry is where a runner is
    # actually named, so a filter that cannot see one is a filter against nothing.
    runner_lines = [
        line
        for line in workflow.splitlines()
        if line.strip().removeprefix("- ").startswith(("os:", "runs-on:"))
    ]
    assert runner_lines, "the workflow declares no runners in a shape this can read"
    assert not any("windows" in line.lower() for line in runner_lines)


def _repository_root() -> Path:
    """Return the checkout this test file lives in."""
    return Path(__file__).resolve().parents[2]


# --- Every figure cites the source that actually contains it -----------------


def test_each_grid_column_carries_its_own_source() -> None:
    """The check that would have caught the catalogue's longest-standing untruth.

    Every row of `grid.yaml` cited one URL for the whole row. The carbon
    intensity came from Ember; the tariff beside it did not, and could not —
    that page publishes generation, emissions, capacity and demand, and no
    price at all. Thirty-eight rows carried a `source_url` that did not contain
    the number next to it, which is the precise failure this package exists to
    object to, and nothing in the suite looked.
    """
    import yaml

    root = Path(__file__).resolve().parents[2]
    rows = yaml.safe_load((root / "saggio" / "data" / "grid.yaml").read_text(encoding="utf-8"))[
        "countries"
    ]
    assert rows, "the grid catalogue is empty"
    for row in rows:
        key = row["key"]
        figure_of = {"carbon": "carbon_gco2e_per_kwh", "price": "price_usd_per_kwh"}
        for column, field in figure_of.items():
            if row.get(field) is None:
                continue
            url = row.get(f"{column}_source_url")
            read = row.get(f"{column}_retrieved_date")
            assert url and url.startswith("https://"), (
                f"{key}: the {column} figure has no source of its own. Inheriting "
                "the row's means citing a page that may not contain it"
            )
            assert read, f"{key}: the {column} figure does not say when it was read"


def test_the_two_grid_columns_do_not_share_a_source() -> None:
    """Carbon and tariff come from different places, and the file has to show it.

    Not a style rule. If both columns ever point at one URL again, one of them
    is being vouched for by a page that does not publish it, which is how the
    original defect looked from the outside: entirely tidy.
    """
    import yaml

    root = Path(__file__).resolve().parents[2]
    rows = yaml.safe_load((root / "saggio" / "data" / "grid.yaml").read_text(encoding="utf-8"))[
        "countries"
    ]
    for row in rows:
        carbon, price = row.get("carbon_source_url"), row.get("price_source_url")
        if carbon and price:
            assert carbon != price, (
                f"{row['key']}: the carbon figure and the tariff cite the same page. "
                "One of them is not published there"
            )


def test_the_tariff_sources_are_the_ones_the_module_names() -> None:
    """The catalogue's URLs are the ones the refresh would write, not strays."""
    import yaml

    from saggio.catalog.refresh import EMBER_CITATION, PRICE_SOURCE

    root = Path(__file__).resolve().parents[2]
    rows = yaml.safe_load((root / "saggio" / "data" / "grid.yaml").read_text(encoding="utf-8"))[
        "countries"
    ]
    for row in rows:
        if row.get("carbon_source_url"):
            # The page Ember publishes the series on, not the API that serves it
            # to a machine. The refresh writes the first and names the second.
            assert row["carbon_source_url"] == EMBER_CITATION
        if row.get("price_source_url"):
            assert row["price_source_url"] == PRICE_SOURCE


def test_the_timezone_names_are_the_ones_iana_publishes() -> None:
    """Every zone on file carries the release it was checked against.

    The third time the same defect turned up. Carbon cited Ember, which was
    right; the tariff cited Ember, which publishes no tariff; and the timezone
    list cited Ember too, which publishes no timezones either. The row-level
    `source_url` covered whatever nobody had looked at.
    """
    import yaml

    root = Path(__file__).resolve().parents[2]
    rows = yaml.safe_load((root / "saggio" / "data" / "grid.yaml").read_text(encoding="utf-8"))[
        "countries"
    ]
    for row in rows:
        if not row.get("timezones"):
            continue
        url = row.get("timezones_source_url") or ""
        assert "iana.org" in url, (
            f"{row['key']}: the timezone list cites {url!r}, which is not the "
            "database that defines those names"
        )
        assert row.get("timezones_tzdb_version"), (
            f"{row['key']}: the timezone list does not say which tzdb release it "
            "was checked against, so nobody can tell whether it still holds"
        )


def test_no_row_level_source_vouches_for_whatever_is_left() -> None:
    """A row-level source_url now covers nothing, and covering nothing is how it lied.

    Each column states its own. A bare `source_url` reappearing on a grid row
    would mean some field has been added without being asked where it came
    from, which is exactly how the tariff went eight months uncited.
    """
    import yaml

    root = Path(__file__).resolve().parents[2]
    rows = yaml.safe_load((root / "saggio" / "data" / "grid.yaml").read_text(encoding="utf-8"))[
        "countries"
    ]
    for row in rows:
        assert "source_url" not in row, (
            f"{row['key']}: a row-level source_url is back. Which of this row's "
            "fields does it claim to be the source of?"
        )


def test_a_column_that_does_not_move_monthly_is_not_asked_to() -> None:
    """The reason STALE_AFTER_DAYS is a table, applied one level down.

    A grid row carries three columns from three sources. A tariff moves
    monthly; the list of timezone names a country uses is published a handful
    of times a year. Under one clock the row would go stale every month on
    account of a column nobody needed to re-read, which teaches a maintainer to
    re-date rather than re-read.
    """
    from datetime import date as _date

    from saggio.catalog.registry import is_stale

    row = {"carbon_gco2e_per_kwh": 41.2}
    today = _date(2026, 10, 2)
    half_a_year = "2026-04-01"
    assert not is_stale({**row, "timezones_retrieved_date": half_a_year}, "country", today=today)
    assert is_stale({**row, "price_retrieved_date": half_a_year}, "country", today=today)
    # But a column with a longer clock still has one.
    assert is_stale({**row, "timezones_retrieved_date": "2024-04-01"}, "country", today=today)
    # And one fresh column does not excuse a stale one.
    both = {**row, "price_retrieved_date": "2026-10-01", "timezones_retrieved_date": "2024-01-01"}
    assert is_stale(both, "country", today=today)


def test_the_scheduled_job_gives_notice_before_a_row_expires() -> None:
    """The freshness job has to warn in advance, not report after the fact.

    Without `--within`, that step prints "every catalogue row is within its
    refresh window" every Monday until the week the rows expire, and only then
    fails. That is notice after the deadline, which is no notice at all for a
    figure somebody is about to quote.

    It still must not *fail* on a merely-expiring row. A gate that turns red
    overnight gets the date bumped in a hurry rather than the source re-read,
    which is the one outcome the whole mechanism exists to prevent -- so this
    checks for the flag, not for a non-zero exit.
    """
    import re

    workflow = (
        _repository_root().joinpath(".github", "workflows", "ci.yml").read_text(encoding="utf-8")
    )
    call = re.search(r"saggio catalog freshness([^\n]*)", workflow)
    assert call, "the scheduled job no longer runs the freshness command"
    within = re.search(r"--within\s+(\d+)", call.group(1))
    assert within, (
        "the freshness job runs without --within, so it says nothing about what "
        "is about to expire until the week it already has"
    )
    # The job runs weekly, and a country row lasts a month. Anything under two
    # weeks is a single Monday's warning, which one person being away defeats.
    assert int(within.group(1)) >= 14, (
        f"--within {within.group(1)} is less than two weekly runs of warning"
    )


def test_an_expiring_row_warns_without_failing_and_a_stale_one_fails() -> None:
    """Both halves of that policy, held in place.

    The distinction is the whole design: expiring is a reminder, stale is a
    defect. Collapsing either into the other breaks it in a different direction.
    """
    from datetime import date, timedelta

    from saggio.catalog import Catalog
    from saggio.catalog.registry import expiring_report, stale_after_days, stale_report

    rows = Catalog.bundled("grid").rows("countries")
    read = min(
        date.fromisoformat(value)
        for row in rows.values()
        for name, value in row.items()
        if name.endswith("_retrieved_date")
    )
    expires = read + timedelta(days=stale_after_days("country"))

    # A week before: a warning, and nothing is stale.
    before = expires - timedelta(days=7)
    assert "country" in expiring_report(today=before, within=21)
    assert "country" not in stale_report(today=before)

    # A week after: stale, which is what fails the job.
    after = expires + timedelta(days=7)
    assert "country" in stale_report(today=after)


def test_the_catalogue_keeps_the_generic_rows_the_detection_falls_back_to() -> None:
    """A machine with an uncatalogued processor leans on these two rows.

    Without them the detection reports no key at all, and every power figure
    downstream becomes a `TODO` — correct, and useless. They are easy to delete
    by accident while tidying the catalogue, because nothing names them except
    the fallback that needs them.
    """
    import yaml

    from saggio.estimate.machine import _FALLBACK_DESKTOP_CPU, _FALLBACK_SERVER_CPU

    rows = yaml.safe_load(
        (_repository_root() / "saggio" / "data" / "hardware.yaml").read_text(encoding="utf-8")
    )["cpus"]
    keys = {row["key"] for row in rows}
    for fallback in (_FALLBACK_DESKTOP_CPU, _FALLBACK_SERVER_CPU):
        assert fallback in keys, (
            f"{fallback} is gone from the catalogue, so a machine whose processor "
            "is not catalogued now gets no per-core power at all"
        )


def test_no_committed_example_cites_an_endpoint_a_reader_cannot_follow() -> None:
    """The same rule, on the surface where a reader actually meets a citation.

    A cost model copies the catalogue's provenance into itself at audit time, so
    every example here inherited the catalogue's citations -- and inherited the
    unfollowable one along with them, in eleven models and the eleven reports
    rendered from them. The rule had been enforced on the catalogue and nowhere
    downstream of it, which is how a fixed defect reappears in twenty-two files
    nobody thought of as data.
    """
    from saggio.catalog.refresh import ENDPOINTS_A_READER_CANNOT_FOLLOW

    root = _repository_root()
    examples = sorted(
        path for pattern in ("*.yaml", "*.md") for path in (root / "examples").rglob(pattern)
    )
    assert examples, "the examples are gone, so this checks nothing"
    for path in examples:
        body = path.read_text(encoding="utf-8")
        for endpoint in ENDPOINTS_A_READER_CANNOT_FOLLOW:
            assert endpoint not in body, (
                f"{path.relative_to(root)} cites {endpoint}, which answers a reader "
                "who follows it with an error rather than with the figure beside it"
            )


def test_no_row_cites_an_endpoint_that_would_show_a_reader_a_wrong_number() -> None:
    """A citation exists so a reader can check the figure beside it.

    One source here answers a bare request with a default: asked about nothing
    in particular, Boavizta's CPU endpoint returns 19.0 kgCO2e, the figure for
    an unnamed chip. Four rows cited it, so anybody following the link saw a
    number that had nothing to do with the processor on that row -- and it was
    the very default this package refuses when importing.

    Ember's endpoint then sat in thirty-eight carbon rows for three more
    iterations, passing this very test. Asked without a key it answers HTTP 403
    and `{"detail": "No API key set"}`: not the wrong number, no number -- which
    this test was not looking for, because it had been handed one URL and told
    about that one. The list is now what the refresh modules declare, so a
    module that gains an endpoint gains the check with it rather than waiting
    for somebody to remember.

    The rule is narrow on purpose: a row may name an endpoint in its *scope*,
    where it is provenance of method, but not in the field a reader is invited
    to follow.
    """
    import yaml

    from saggio.catalog.refresh import ENDPOINTS_A_READER_CANNOT_FOLLOW

    #: Endpoints that answer a bare GET with something other than the row's
    #: figure -- or with nothing. Declared by the modules that hold them rather
    #: than listed here, because a list here is a list that goes out of date in
    #: exactly the direction that hides a fault. An API that *does* answer with
    #: the figure is a perfectly good citation and is not in it.
    shows_the_wrong_thing = tuple(
        url.split("://", 1)[-1] for url in ENDPOINTS_A_READER_CANNOT_FOLLOW
    )
    assert len(shows_the_wrong_thing) >= 2, (
        "the modules declare fewer unfollowable endpoints than are known to exist"
    )

    root = _repository_root()
    for name in ("hardware.yaml", "grid.yaml"):
        rows = yaml.safe_load((root / "saggio" / "data" / name).read_text(encoding="utf-8"))
        for section in rows.values():
            if not isinstance(section, list):
                continue
            for row in section:
                for field, value in row.items():
                    if not field.endswith("source_url") or not isinstance(value, str):
                        continue
                    for endpoint in shows_the_wrong_thing:
                        assert endpoint not in value, (
                            f"{name}:{row.get('key')} cites {value} in {field}; that "
                            "endpoint shows a reader a default figure, not this row's"
                        )


def test_the_link_checker_finds_the_links_the_repository_asks_you_to_follow() -> None:
    # The checker itself reaches the network and is therefore a maintenance
    # script, not a test. What *is* testable without the network is that its
    # collector still sees the two places a citation lives — the pages and the
    # catalogue rows — because a collector that silently stopped finding them
    # would report "nothing broken" forever.
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "check_links", Path(__file__).resolve().parents[2] / "docs" / "check_links.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    cited = module.sources()
    assert len(cited) > 100, "the collector stopped seeing most of the links"
    assert any(place.startswith("catalogue:") for places in cited.values() for place in places), (
        "no catalogue row's source URL is being checked, which is the half that matters"
    )
    assert any(place.endswith(".md") for places in cited.values() for place in places)
    # An illustrative link is skipped by rule rather than by a list: a made-up
    # source on a real vendor's domain is indistinguishable from a stale one.
    assert not any("example.invalid" in url for url in cited)


def test_the_eu_row_carries_what_the_report_says_about_itself() -> None:
    # A catalogue row is read instead of the document it came from, so the
    # limits the document states about its own figures have to travel with it.
    # This one's are unusually load-bearing: a third of the population reported,
    # and the water average excludes the rooms that use none.
    row = Catalog.load("providers", overlay=Path("/nonexistent")).rows("providers")["on-prem-eu"]
    assert row["pue"] == 1.36
    assert row["wue_l_per_kwh"] == 0.58
    assert row["operated_by"] == "self", "a room you run is your own scope 2"
    notes = str(row["notes"])
    for stated in ("681", "458", "36%", "70.1%", "Article 5(5)"):
        assert stated in notes, f"the row does not carry {stated!r}, which the report states"


def test_a_european_room_can_close_its_water() -> None:
    # The point of the row. Water was a TODO on every self-run model because
    # "On-premises publishes no water usage effectiveness" — true until the
    # Commission published one.
    providers = Catalog.load("providers", overlay=Path("/nonexistent")).rows("providers")
    assert providers["on-prem"]["wue_l_per_kwh"] is None, "the global row still publishes none"
    assert providers["on-prem-eu"]["wue_l_per_kwh"] is not None


def test_every_footprint_says_what_one_of_it_is() -> None:
    """A manufacturing footprint is meaningless without the thing it is of.

    NVIDIA's PCF summaries state a figure for a *baseboard* — 1,312 kgCO2e for
    an HGX H100, 2,274 for an HGX B200 — while this catalogue's unit is one
    accelerator. The divisor is on a different page of the document, in a spec
    table reading "Form Factor: 8x NVIDIA H100 SXM". A row carrying 1312 under
    the key `H100` would be wrong by a factor of eight and would look perfect:
    real source, real date, a number genuinely in the document.

    So the scope is not decoration. It is the field that says which of the two
    numbers in the document this one is, and it is required of every row that
    states a footprint at all.
    """
    offenders: list[str] = []
    for kind, key, row in catalog_rows():
        if row.get("embodied_kgco2e") is None:
            continue
        scope = str(row.get("embodied_scope") or "")
        if not scope:
            offenders.append(f"{kind}:{key} states a footprint and no scope")
            continue
        # "One X", "One of the eight Y": the scope has to open by naming a unit,
        # because a scope that only names a method still leaves the reader
        # dividing by a number nobody wrote down.
        if not scope.lower().startswith("one"):
            offenders.append(
                f"{kind}:{key} scope does not begin by naming one unit: {scope[:60]!r}"
            )
        if row.get("embodied_source_url") is None:
            offenders.append(f"{kind}:{key} states a footprint and no source")
        if row.get("embodied_retrieved_date") is None:
            offenders.append(f"{kind}:{key} states a footprint and no date")
    assert not offenders, "\n".join(offenders)


def test_a_footprint_divided_from_a_board_says_so_and_by_how_much() -> None:
    # Checked against the two documents on 2026-10-19: the HGX H100 summary
    # states 1,312 kgCO2e for the baseboard and the H100 row carries 164.0,
    # which is 1312/8; the HGX B200 summary states 2,274 and the B200 row
    # carries 284.25, which is 2274/8. Both rows say so in their own scope.
    rows = {key: row for _, key, row in catalog_rows() if row.get("embodied_kgco2e")}
    for key, board, count in (("H100", 1312.0, 8), ("B200", 2274.0, 8)):
        row = rows[key]
        scope = str(row["embodied_scope"])
        assert str(int(board)) in scope, f"{key}: the scope does not quote the board figure"
        assert row["embodied_kgco2e"] == pytest.approx(board / count), (
            f"{key} carries {row['embodied_kgco2e']} and {board}/{count} is {board / count}"
        )
