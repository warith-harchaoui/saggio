"""Re-reading a catalogue from the source it cites, and refusing the shortcut."""

from __future__ import annotations

import argparse
import json
import pathlib

import pytest

from saggio.catalog.refresh import (
    EMBER_KEY_VARIABLE,
    ISO3_OF_ISO2,
    GridRefresh,
    apply_grid,
    fetch_grid,
    missing_key_message,
)
from saggio.cli.commands import catalog_refresh

# --- What it refuses to do ---------------------------------------------------


def test_no_key_is_a_refusal_not_a_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(EMBER_KEY_VARIABLE, raising=False)
    with pytest.raises(RuntimeError) as caught:
        fetch_grid(["FR"])
    assert "API key" in str(caught.value)


def test_the_message_names_the_shortcut_and_why_it_is_wrong() -> None:
    # The one dataset that is reachable without a key measures a different
    # quantity. Somebody will find it; they should find the reason first.
    message = missing_key_message()
    assert "lifecycle" in message
    assert "operating emissions" in message


def test_the_command_refuses_a_catalogue_that_cites_no_machine_readable_source() -> None:
    from saggio.cli.exit_codes import USAGE

    args = argparse.Namespace(catalog="hardware", api_key=None, year=None, write=None, json=False)
    assert catalog_refresh(args) == USAGE


def test_the_command_reports_a_missing_key_as_an_unavailable_dependency(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from saggio.cli.exit_codes import UNAVAILABLE

    monkeypatch.delenv(EMBER_KEY_VARIABLE, raising=False)
    args = argparse.Namespace(catalog="grid", api_key=None, year=None, write=None, json=False)
    assert catalog_refresh(args) == UNAVAILABLE


def test_asking_about_nothing_reaches_no_network() -> None:
    # Guards the loop that would otherwise build a query of zero countries and
    # ask anyway.
    assert fetch_grid([], api_key="irrelevant").rows == {}


# --- What it reports ---------------------------------------------------------


def test_only_the_values_that_moved_are_called_changes() -> None:
    refresh = GridRefresh(2025, {"FR": 41.4, "DE": 329.0}, {}, "ember")
    current = {
        "FR": {"carbon_gco2e_per_kwh": 56},
        "DE": {"carbon_gco2e_per_kwh": 329.2},
    }
    assert refresh.changed(current) == {"FR": (56, 41.4)}


def test_a_row_the_catalogue_has_no_number_for_counts_as_moved() -> None:
    refresh = GridRefresh(2025, {"FR": 41.4}, {}, "ember")
    assert refresh.changed({"FR": {}}) == {"FR": (None, 41.4)}


def test_a_country_with_no_alpha3_on_file_is_named_rather_than_guessed() -> None:
    refresh = fetch_grid(["ZZ"], api_key="irrelevant")
    assert "ZZ" in refresh.skipped
    assert "alpha-3" in refresh.skipped["ZZ"]


def test_every_bundled_country_can_be_asked_about() -> None:
    # A key the mapping does not know is silently un-refreshable, which would
    # make a refresh look complete while leaving rows behind.
    from saggio.catalog.registry import Catalog

    for key in Catalog.bundled("grid").rows("countries"):
        assert key in ISO3_OF_ISO2, f"{key} has no ISO 3166-1 alpha-3 code on file"


# --- What it writes ----------------------------------------------------------


GRID = """# A header that explains the columns and must survive.
countries:
  # Quoted on purpose: unquoted, NO is the boolean false.
  - key: "FR"
    name: "France"
    carbon_gco2e_per_kwh: 56
    price_usd_per_kwh: 0.24
    timezones: ["Europe/Paris"]
    source_url: "https://ember-energy.org/data/electricity-data-explorer/"
    retrieved_date: "2026-09-12"

  - key: "NO"
    name: "Norway"
    carbon_gco2e_per_kwh: 30
    retrieved_date: "2026-09-12"
"""


def written_grid(tmp_path: pathlib.Path, refresh: GridRefresh) -> str:
    target = tmp_path / "grid.yaml"
    target.write_text(GRID, encoding="utf-8")
    apply_grid(target, refresh)
    return target.read_text(encoding="utf-8")


def test_the_intensity_is_replaced(tmp_path: pathlib.Path) -> None:
    body = written_grid(tmp_path, GridRefresh(2025, {"FR": 41.44}, {}, "ember"))
    assert "carbon_gco2e_per_kwh: 41.4" in body
    assert "carbon_gco2e_per_kwh: 56" not in body


def test_the_carbon_figure_gets_its_own_provenance(tmp_path: pathlib.Path) -> None:
    # The row's price came from somewhere else and keeps the row's own dates.
    body = written_grid(tmp_path, GridRefresh(2025, {"FR": 41.44}, {}, "ember"))
    assert 'carbon_source_url: "ember"' in body
    assert "carbon_data_year: 2025" in body
    assert 'retrieved_date: "2026-09-12"' in body, "the row's own date must survive"


def test_a_country_the_source_did_not_answer_for_is_left_alone(
    tmp_path: pathlib.Path,
) -> None:
    body = written_grid(tmp_path, GridRefresh(2025, {"FR": 41.44}, {}, "ember"))
    assert "carbon_gco2e_per_kwh: 30" in body, "Norway was not refreshed and must not move"


def test_the_header_and_the_comments_survive(tmp_path: pathlib.Path) -> None:
    # A round trip through a YAML dumper would lose both, and the comment about
    # NO being the boolean false is load-bearing.
    body = written_grid(tmp_path, GridRefresh(2025, {"FR": 41.44}, {}, "ember"))
    assert "A header that explains the columns" in body
    assert "NO is the boolean false" in body


def test_refreshing_twice_does_not_stack_the_fields(tmp_path: pathlib.Path) -> None:
    target = tmp_path / "grid.yaml"
    target.write_text(GRID, encoding="utf-8")
    apply_grid(target, GridRefresh(2025, {"FR": 41.44}, {}, "ember"))
    apply_grid(target, GridRefresh(2026, {"FR": 39.0}, {}, "ember"))
    body = target.read_text(encoding="utf-8")
    assert body.count("carbon_source_url:") == 1
    assert "carbon_data_year: 2026" in body


def test_the_result_still_parses_as_yaml(tmp_path: pathlib.Path) -> None:
    import yaml

    body = written_grid(tmp_path, GridRefresh(2025, {"FR": 41.44, "NO": 28.1}, {}, "ember"))
    rows = {row["key"]: row for row in yaml.safe_load(body)["countries"]}
    assert rows["FR"]["carbon_gco2e_per_kwh"] == pytest.approx(41.4)
    assert rows["NO"]["carbon_data_year"] == 2025


def test_it_edits_a_catalogue_and_never_creates_one(tmp_path: pathlib.Path) -> None:
    with pytest.raises(FileNotFoundError):
        apply_grid(tmp_path / "absent.yaml", GridRefresh(2025, {"FR": 1.0}, {}, "ember"))


def test_the_json_report_says_what_changed_and_what_did_not(
    tmp_path: pathlib.Path, capsys, monkeypatch: pytest.MonkeyPatch
) -> None:
    import saggio.cli.commands as commands

    # Deliberately far from anything the catalogue could hold, so that FR lands
    # in `changed` whatever this week's refresh put there. Picking a plausible
    # number here made the test pass only until the catalogue caught up with it.
    invented = 999.5
    monkeypatch.setattr(
        commands,
        "fetch_grid",
        lambda *a, **k: GridRefresh(2025, {"FR": invented}, {"ZZ": "no code"}, "ember"),
    )
    args = argparse.Namespace(catalog="grid", api_key=None, year=None, write=None, json=True)
    catalog_refresh(args)
    payload = json.loads(capsys.readouterr().out)
    assert payload["data_year"] == 2025
    assert payload["changed"]["FR"]["now"] == pytest.approx(invented)
    assert payload["skipped"] == {"ZZ": "no code"}


# --- The tariff and timezone readers, without a network --------------------------
#
# Everything below feeds the readers a document and checks what they make of it.
# What is deliberately *not* covered is the two functions that fetch one:
# `_rendered`, which shells out to a headless browser, and `_iana_zones`, which
# opens a socket. Testing those would be testing `subprocess` and `urllib`, and
# would make the suite depend on a network it has no business needing. The
# fallible half of each reader is the parsing, and the parsing is here.


#: What the tariff page looks like once its script has run: a table of country
#: name, residential price, business price, headed by the quarter it covers.
#: Trimmed to the shape that matters, with the real spellings kept, because the
#: spellings are half of what can go wrong.
TARIFF_DOCUMENT = """
<html><body>
<p>Q3 2026 update : The average electricity price in the world is
USD 0.179 kWh for residential users and USD 0.172 USD per kWh for businesses.</p>
<table>
  <tr><th>Country</th><th>Households</th><th>Business</th></tr>
  <tr><td><a href="/France/">France</a></td><td>0.276</td><td>0.212</td></tr>
  <tr><td><a href="/Germany/">Germany</a></td><td>0.409</td><td>0.284</td></tr>
  <tr><td><a href="/USA/">USA</a></td><td>0.190</td><td>0.172</td></tr>
  <tr><td><a href="/UK/">UK</a></td><td>0.405</td><td>0.331</td></tr>
  <tr><td>Continent</td><td>Households(change)</td><td>Business(change)</td></tr>
  <tr><td>Africa</td><td>1.05%</td><td>5.94%</td></tr>
</table>
</body></html>
"""


def test_the_tariff_table_is_read_by_the_name_each_country_is_listed_under(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import saggio.catalog.refresh as module

    monkeypatch.setattr(module, "_rendered", lambda url, timeout: TARIFF_DOCUMENT)
    refresh = module.fetch_prices(
        ["FR", "DE", "US", "GB"],
        names={"FR": "France", "DE": "Germany", "US": "United States", "GB": "United Kingdom"},
    )
    # US and GB are listed as USA and UK, which is what PRICE_NAME_OF_KEY is for.
    # Without it they would be skipped and the catalogue would quietly keep two
    # stale tariffs while reporting a successful refresh.
    assert refresh.rows == {"FR": 0.276, "DE": 0.409, "US": 0.190, "GB": 0.405}
    assert refresh.skipped == {}


def test_the_quarter_the_prices_describe_is_not_the_day_they_were_read(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import saggio.catalog.refresh as module

    monkeypatch.setattr(module, "_rendered", lambda url, timeout: TARIFF_DOCUMENT)
    refresh = module.fetch_prices(["FR"], names={"FR": "France"})
    assert refresh.collected == "Q3 2026"
    assert refresh.retrieved != refresh.collected


def test_a_country_the_page_does_not_list_is_named_rather_than_guessed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import saggio.catalog.refresh as module

    monkeypatch.setattr(module, "_rendered", lambda url, timeout: TARIFF_DOCUMENT)
    refresh = module.fetch_prices(["FR", "ZZ"], names={"FR": "France", "ZZ": "Atlantis"})
    assert refresh.rows == {"FR": 0.276}
    assert "ZZ" in refresh.skipped


def test_the_percentage_rows_are_not_mistaken_for_tariffs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # The same table carries a continent summary whose cells are percentages.
    # Reading "1.05%" as a price would put Africa in the catalogue at a dollar
    # a kilowatt-hour, and nothing downstream would question it.
    import saggio.catalog.refresh as module

    monkeypatch.setattr(module, "_rendered", lambda url, timeout: TARIFF_DOCUMENT)
    refresh = module.fetch_prices(["ZA"], names={"ZA": "Africa"})
    assert refresh.rows == {}
    assert "ZA" in refresh.skipped


def test_no_browser_means_no_tariff_rather_than_a_guess(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import saggio.catalog.refresh as module

    monkeypatch.setattr(module, "_rendered", lambda url, timeout: "")
    with pytest.raises(RuntimeError, match="headless browser"):
        module.fetch_prices(["FR"], names={"FR": "France"})


#: The two files the timezone database publishes, in their real formats: a
#: tab-separated table of canonical zones and a list of compatibility links.
ZONE_TAB = (
    "# tzdb timezone descriptions\n"
    "#country-\n"
    "#codes\tcoordinates\tTZ\tcomments\n"
    "FR\t+4852+00220\tEurope/Paris\n"
    "UA\t+5026+03031\tEurope/Kyiv\n"
    "IN\t+2232+08822\tAsia/Kolkata\n"
    "NO,SJ\t+5955+01045\tEurope/Berlin\tNorway shares a zone\n"
)
BACKWARD = (
    "# This file provides links between current names and older names.\n"
    "Link\tEurope/Kyiv\tEurope/Kiev\n"
    "Link\tAsia/Kolkata\tAsia/Calcutta\n"
)


def test_a_compatibility_name_is_as_real_as_a_canonical_one(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # The catalogue carries Europe/Kiev and Asia/Calcutta on purpose: those are
    # what a real machine reports, and a country this package cannot recognise
    # from its own machine's timezone is a country the user has to type by hand.
    # Checking against the canonical table alone would condemn both.
    import saggio.catalog.refresh as module

    monkeypatch.setattr(module, "_iana_zones", lambda timeout: (_names(), "2026e"))
    check = module.check_timezones(
        {
            "FR": {"timezones": ["Europe/Paris"]},
            "UA": {"timezones": ["Europe/Kiev"]},
            "IN": {"timezones": ["Asia/Calcutta", "Asia/Kolkata"]},
        }
    )
    assert check.ok
    assert check.version == "2026e"
    assert check.known == 4


def _names() -> set[str]:
    """Return the zone names the two fixture files define, parsed as the module does."""
    names: set[str] = set()
    for line in ZONE_TAB.splitlines():
        if line and not line.startswith("#"):
            columns = line.split("\t")
            if len(columns) >= 3:
                names.add(columns[2])
    for line in BACKWARD.splitlines():
        columns = line.split()
        if len(columns) >= 3 and columns[0] == "Link":
            names.add(columns[2])
    return names


def test_a_zone_the_database_does_not_publish_is_reported_not_corrected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import saggio.catalog.refresh as module

    monkeypatch.setattr(module, "_iana_zones", lambda timeout: (_names(), "2026e"))
    check = module.check_timezones({"ZZ": {"timezones": ["Mars/Olympus", "Europe/Paris"]}})
    assert not check.ok
    assert check.unknown == {"ZZ": ["Mars/Olympus"]}
    # The good one still counted; this reports rather than discards.
    assert check.known == 1


def test_a_failed_check_stamps_nothing(tmp_path: pathlib.Path) -> None:
    # Marking a list as verified when it did not verify would be this package's
    # own mistake, in miniature.
    from saggio.catalog.refresh import TimezoneCheck, apply_timezone_check

    target = tmp_path / "grid.yaml"
    body = 'countries:\n  - key: "FR"\n    timezones: ["Europe/Paris"]\n'
    target.write_text(body, encoding="utf-8")
    with pytest.raises(ValueError, match="not zones the database publishes"):
        apply_timezone_check(target, TimezoneCheck("2026e", 0, {"FR": ["Mars/Olympus"]}))
    assert target.read_text(encoding="utf-8") == body


def test_stamping_twice_replaces_rather_than_stacks(tmp_path: pathlib.Path) -> None:
    from saggio.catalog.refresh import TimezoneCheck, apply_timezone_check

    target = tmp_path / "grid.yaml"
    target.write_text(
        'countries:\n  - key: "FR"\n    timezones: ["Europe/Paris"]\n', encoding="utf-8"
    )
    apply_timezone_check(target, TimezoneCheck("2026d", 1, {}))
    apply_timezone_check(target, TimezoneCheck("2026e", 1, {}))
    body = target.read_text(encoding="utf-8")
    assert body.count("timezones_tzdb_version:") == 1
    assert "2026e" in body
    assert "2026d" not in body


# --- The Ember response, parsed without a network --------------------------------


class FakeResponse:
    """The little of a urlopen response that the reader uses."""

    def __init__(self, payload: str) -> None:
        self._payload = payload.encode("utf-8")

    def read(self) -> bytes:
        """Return the body, as urlopen would."""
        return self._payload

    def __enter__(self) -> FakeResponse:
        """Enter the `with` the reader wraps its call in."""
        return self

    def __exit__(self, *_exception: object) -> bool:
        """Leave it, without swallowing anything."""
        return False


def answer_with(monkeypatch: pytest.MonkeyPatch, payload: str) -> None:
    """Make the next Ember call return this body instead of opening a socket."""
    import saggio.catalog.refresh as module

    monkeypatch.setattr(
        module.urllib.request, "urlopen", lambda request, timeout=0: FakeResponse(payload)
    )


def test_the_most_recent_year_wins_per_country(monkeypatch: pytest.MonkeyPatch) -> None:
    # The real call returns every year since 2000 for every country at once, in
    # no guaranteed order. Taking the last record seen, or the first, would pin
    # the catalogue to whichever year the API happened to list last.
    answer_with(
        monkeypatch,
        json.dumps(
            {
                "data": [
                    {"entity_code": "FRA", "date": "2023", "emissions_intensity_gco2_per_kwh": 56},
                    {
                        "entity_code": "FRA",
                        "date": "2025",
                        "emissions_intensity_gco2_per_kwh": 41.2,
                    },
                    {"entity_code": "FRA", "date": "2024", "emissions_intensity_gco2_per_kwh": 44},
                    {"entity_code": "DEU", "date": "2025", "emissions_intensity_gco2_per_kwh": 334},
                ]
            }
        ),
    )
    refresh = fetch_grid(["FR", "DE"], api_key="irrelevant")
    assert refresh.rows == {"FR": 41.2, "DE": 334.0}
    assert refresh.year == 2025


def test_a_country_the_answer_omits_is_left_alone_and_named(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Never interpolated, never carried over. A row this refresh cannot speak
    # for keeps the figure it had, and the report says which rows those were.
    answer_with(
        monkeypatch,
        json.dumps(
            {
                "data": [
                    {"entity_code": "FRA", "date": "2025", "emissions_intensity_gco2_per_kwh": 41.2}
                ]
            }
        ),
    )
    refresh = fetch_grid(["FR", "DE"], api_key="irrelevant")
    assert refresh.rows == {"FR": 41.2}
    assert "DE" in refresh.skipped


def test_a_record_with_no_figure_is_not_a_figure(monkeypatch: pytest.MonkeyPatch) -> None:
    # The API returns null for a country-year it has no number for. Reading null
    # as zero would put a carbon-free grid in the catalogue.
    answer_with(
        monkeypatch,
        json.dumps(
            {
                "data": [
                    {
                        "entity_code": "FRA",
                        "date": "2025",
                        "emissions_intensity_gco2_per_kwh": None,
                    },
                    {
                        "entity_code": "FRA",
                        "date": "2024",
                        "emissions_intensity_gco2_per_kwh": 44.0,
                    },
                ]
            }
        ),
    )
    refresh = fetch_grid(["FR"], api_key="irrelevant")
    assert refresh.rows == {"FR": 44.0}
    assert refresh.year == 2024


def test_an_answer_in_a_shape_it_does_not_recognise_touches_nothing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    answer_with(monkeypatch, json.dumps({"error": "rate limited"}))
    with pytest.raises(RuntimeError, match="shape this does not recognise"):
        fetch_grid(["FR"], api_key="irrelevant")


def test_a_source_that_does_not_answer_raises_rather_than_returns_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # An empty refresh and a failed refresh look identical to a caller that only
    # checks `rows`, and one of them should not write anything.
    import saggio.catalog.refresh as module

    def refuse(request: object, timeout: int = 0) -> None:
        raise module.urllib.error.URLError("no route to host")

    monkeypatch.setattr(module.urllib.request, "urlopen", refuse)
    with pytest.raises(RuntimeError, match="did not answer"):
        fetch_grid(["FR"], api_key="irrelevant")


def test_the_query_names_the_parameter_the_api_actually_has(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # It once sent `is_aggregate_series`, which this API has no such parameter
    # for. Unknown query parameters are ignored rather than refused, so the
    # filter the code believed it was setting was never set, and nothing failed.
    import saggio.catalog.refresh as module

    seen: dict[str, str] = {}

    def capture(request: object, timeout: int = 0) -> FakeResponse:
        seen["url"] = request.full_url  # type: ignore[attr-defined]
        return FakeResponse(json.dumps({"data": []}))

    monkeypatch.setattr(module.urllib.request, "urlopen", capture)
    fetch_grid(["FR"], api_key="irrelevant")
    assert "is_aggregate_entity=false" in seen["url"]
    assert "is_aggregate_series" not in seen["url"]
