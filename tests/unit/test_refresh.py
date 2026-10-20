"""Re-reading a catalogue from the source it cites, and refusing the shortcut."""

from __future__ import annotations

import argparse
import io
import json
import pathlib

import pytest
import yaml

from saggio.catalog.refresh import (
    EMBER_API,
    EMBER_CITATION,
    EMBER_INTENSITY_COLUMN,
    EMBER_KEY_VARIABLE,
    EMBER_TOTAL_ROW,
    ISO3_OF_ISO2,
    GridRefresh,
    apply_grid,
    fetch_grid,
    fetch_grid_public,
    missing_key_message,
)
from saggio.cli.commands import catalog_refresh
from saggio.i18n import language

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


def test_no_key_reads_the_dataset_ember_publishes_rather_than_refusing(
    monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    """A key opens a faster door, not the only one.

    This used to exit 4 without a key, and that was the wrong shape of refusal.
    What has to be refused is a *different measure* wearing the same units --
    lifecycle where the column says operating -- and that refusal is intact and
    tested above. Ember's own published yearly dataset is not that: same
    publisher, same series, no key, and it is the file behind the page every
    refreshed row cites. Making it unreachable without a credential is how a
    column stops being re-read, and a column that stops being re-read gets
    re-dated instead, which is the one outcome this whole mechanism exists to
    prevent.
    """
    import saggio.cli.commands as commands

    monkeypatch.delenv(EMBER_KEY_VARIABLE, raising=False)

    def not_the_keyed_path(*_a: object, **_k: object) -> None:
        raise AssertionError("the keyed API was called with no key in sight")

    monkeypatch.setattr(commands, "fetch_grid", not_the_keyed_path)
    monkeypatch.setattr(
        commands, "fetch_grid_public", lambda *a, **k: GridRefresh(2025, {"FR": 41.2}, {}, "public")
    )
    assert catalog_refresh(grid_args()) == 0
    assert EMBER_CITATION in capsys.readouterr().out


def test_a_key_in_the_environment_is_used_and_said_so(
    monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    # Which of the two answered is printed rather than inferred from whether it
    # worked. They agree, but "they agree" is a thing somebody checked once, not
    # a thing a reader of the output should have to assume.
    import saggio.cli.commands as commands

    monkeypatch.setenv(EMBER_KEY_VARIABLE, "a-key")

    def not_the_keyless_path(*_a: object, **_k: object) -> None:
        raise AssertionError("the published dataset was read although a key was offered")

    monkeypatch.setattr(commands, "fetch_grid_public", not_the_keyless_path)
    monkeypatch.setattr(
        commands,
        "fetch_grid",
        lambda *a, **k: GridRefresh(2025, {"FR": 41.2}, {}, source=EMBER_API),
    )
    assert catalog_refresh(grid_args()) == 0
    assert EMBER_API in capsys.readouterr().out


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
    assert f'carbon_source_url: "{EMBER_CITATION}"' in body
    assert "carbon_data_year: 2025" in body
    assert 'retrieved_date: "2026-09-12"' in body, "the row's own date must survive"


def test_the_row_cites_what_a_reader_can_open_not_what_answered(
    tmp_path: pathlib.Path,
) -> None:
    """The URL that answers a machine and the one that shows a reader differ here.

    Thirty-eight rows cited `api.ember-energy.org`, which answers anybody
    without a key with HTTP 403 and `{"detail": "No API key set"}`. Every one of
    those citations was unfollowable, in a package whose whole claim is that a
    number says where it came from, and the suite already had a test for this
    exact fault -- written for Boavizta's endpoint and told about that one only.
    """
    body = written_grid(tmp_path, GridRefresh(2025, {"FR": 41.44}, {}, source=EMBER_API))
    assert EMBER_API not in body, "a row is citing the endpoint again"
    assert f'carbon_source_url: "{EMBER_CITATION}"' in body


def test_a_country_the_source_has_not_caught_up_on_keeps_its_own_year(
    tmp_path: pathlib.Path,
) -> None:
    """One data year for the refresh is one data year too few.

    Ember publishes Ukraine only to 2022 and everybody else to 2025. The old
    code took the newest year across all countries and stamped it on every row,
    so the catalogue shipped Ukraine's 2022 reading of 250.5 gCO2e/kWh under
    `carbon_data_year: 2025`. Nothing about the number itself could show that:
    250.5 is an unremarkable intensity, and the stamp was the only place the
    three-year gap was ever going to appear.
    """
    body = written_grid(
        tmp_path,
        GridRefresh(2025, {"FR": 41.4, "NO": 28.1}, {}, "ember", years={"FR": 2025, "NO": 2022}),
    )
    rows = {row["key"]: row for row in yaml.safe_load(body)["countries"]}
    assert rows["FR"]["carbon_data_year"] == 2025
    assert rows["NO"]["carbon_data_year"] == 2022, (
        "the lagging row took the refresh's newest year rather than its own"
    )


def test_a_row_the_refresh_gives_no_year_for_falls_back_to_the_newest(
    tmp_path: pathlib.Path,
) -> None:
    # Only where the source said nothing. Not a default to lean on: it exists so
    # a caller that knows one year for everything still writes a year.
    body = written_grid(tmp_path, GridRefresh(2025, {"FR": 41.4}, {}, "ember"))
    assert "carbon_data_year: 2025" in body


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
    # Deliberately far from anything the catalogue could hold, so that FR lands
    # in `changed` whatever this week's refresh put there. Picking a plausible
    # number here made the test pass only until the catalogue caught up with it.
    invented = 999.5
    answer_both_carbon_paths(
        monkeypatch,
        GridRefresh(
            2025,
            {"FR": invented, "NO": 28.1},
            {"ZZ": "no code"},
            "ember",
            years={"FR": 2025, "NO": 2022},
        ),
    )
    catalog_refresh(grid_args(json=True))
    payload = json.loads(capsys.readouterr().out)
    assert payload["data_year"] == 2025
    assert payload["changed"]["FR"]["now"] == pytest.approx(invented)
    assert payload["skipped"] == {"ZZ": "no code"}
    # The per-country years, and the countries the source has not caught up on.
    # A report that gave only the newest year is the report that let a 2022
    # figure be committed as a 2025 one.
    assert payload["data_year_by_country"] == {"FR": 2025, "NO": 2022}
    assert payload["behind_the_newest_year"] == ["NO"]
    assert payload["citation"] == EMBER_CITATION


# --- Ember's published dataset, parsed without a network -------------------------
#
# The file is some tens of megabytes of every country, every year and every fuel.
# What can go wrong in reading it is not arithmetic: it is picking the wrong row
# of the three the file offers per country-year, or finding nothing at all and
# reporting that as nothing having changed.


#: The shape of Ember's published file, trimmed. The real spellings are kept --
#: including the parenthesised unit in the column name -- because the spellings
#: are what the reader matches on. Ukraine stops in 2022 here as it does there.
PUBLIC_CSV = (
    "Area,ISO 3 code,Year,Area type,Electricity source,"
    f"{EMBER_INTENSITY_COLUMN}\n"
    "France,FRA,2024,Country or economy,Coal,961.627\n"
    f"France,FRA,2024,Country or economy,{EMBER_TOTAL_ROW},44.0\n"
    f"France,FRA,2025,Country or economy,{EMBER_TOTAL_ROW},41.224\n"
    "France,FRA,2025,Country or economy,Coal,961.627\n"
    f"Ukraine,UKR,2022,Country or economy,{EMBER_TOTAL_ROW},250.525\n"
    f"Germany,DEU,2025,Country or economy,{EMBER_TOTAL_ROW},\n"
)


def answer_with_file(monkeypatch: pytest.MonkeyPatch, body: str) -> None:
    """Make the next download return this file instead of opening a socket."""
    from saggio.catalog.refresh import carbon as module

    monkeypatch.setattr(
        module.urllib.request,
        "urlopen",
        lambda request, timeout=0: io.BytesIO(body.encode("utf-8")),
    )


def test_the_published_dataset_is_read_without_a_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(EMBER_KEY_VARIABLE, raising=False)
    answer_with_file(monkeypatch, PUBLIC_CSV)
    refresh = fetch_grid_public(["FR", "UA"])
    assert refresh.rows == {"FR": 41.224, "UA": 250.525}
    assert refresh.citation == EMBER_CITATION
    assert EMBER_API not in refresh.citation


def test_each_country_gets_the_newest_year_it_has_and_not_the_newest_there_is(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The defect this whole reader exists around, read straight off the file.

    France reaches 2025 and Ukraine stops at 2022. The refresh's newest year is
    2025 and Ukraine's is not, and the two have to stay apart all the way to the
    row that gets written.
    """
    answer_with_file(monkeypatch, PUBLIC_CSV)
    refresh = fetch_grid_public(["FR", "UA"])
    assert refresh.year == 2025
    assert refresh.years == {"FR": 2025, "UA": 2022}


def test_one_fuel_is_not_mistaken_for_the_whole_grid(monkeypatch: pytest.MonkeyPatch) -> None:
    # The file carries an intensity per source as well as for the grid. Reading
    # the wrong row would file French *coal* -- 961.6 -- under France, which is
    # a real number, in the right unit, off by a factor of twenty-three.
    answer_with_file(monkeypatch, PUBLIC_CSV)
    assert fetch_grid_public(["FR"]).rows["FR"] == 41.224


def test_a_year_that_is_asked_for_is_taken_literally(monkeypatch: pytest.MonkeyPatch) -> None:
    answer_with_file(monkeypatch, PUBLIC_CSV)
    refresh = fetch_grid_public(["FR", "UA"], year=2024)
    assert refresh.rows == {"FR": 44.0}
    assert "2024" in refresh.skipped["UA"], "a country without that year is named, not served 2022"


def test_a_country_with_no_figure_in_the_file_is_named_rather_than_guessed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    answer_with_file(monkeypatch, PUBLIC_CSV)
    refresh = fetch_grid_public(["FR", "DE"])
    assert "DE" not in refresh.rows
    assert "DE" in refresh.skipped


def test_a_renamed_column_is_an_error_rather_than_an_empty_refresh(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Finding nothing and reporting nothing moved are the same output.

    If the publisher renames the intensity column, every lookup misses and the
    command prints "nothing moved by more than the catalogue's own precision" --
    which is exactly what it prints when the catalogue is perfectly up to date.
    The failure has to be loud at the point it happens.
    """
    answer_with_file(monkeypatch, PUBLIC_CSV.replace(EMBER_INTENSITY_COLUMN, "Intensity"))
    with pytest.raises(RuntimeError) as caught:
        fetch_grid_public(["FR"])
    assert EMBER_INTENSITY_COLUMN in str(caught.value)


def test_asking_the_published_dataset_about_nothing_reaches_no_network() -> None:
    assert fetch_grid_public([]).rows == {}


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
    from saggio.catalog.refresh import tariffs as module

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
    from saggio.catalog.refresh import tariffs as module

    monkeypatch.setattr(module, "_rendered", lambda url, timeout: TARIFF_DOCUMENT)
    refresh = module.fetch_prices(["FR"], names={"FR": "France"})
    assert refresh.collected == "Q3 2026"
    assert refresh.retrieved != refresh.collected


def test_a_country_the_page_does_not_list_is_named_rather_than_guessed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from saggio.catalog.refresh import tariffs as module

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
    from saggio.catalog.refresh import tariffs as module

    monkeypatch.setattr(module, "_rendered", lambda url, timeout: TARIFF_DOCUMENT)
    refresh = module.fetch_prices(["ZA"], names={"ZA": "Africa"})
    assert refresh.rows == {}
    assert "ZA" in refresh.skipped


def test_no_browser_means_no_tariff_rather_than_a_guess(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from saggio.catalog.refresh import tariffs as module

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
    from saggio.catalog.refresh import timezones as module

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
    from saggio.catalog.refresh import timezones as module

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
    from saggio.catalog.refresh import carbon as module

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
    from saggio.catalog.refresh import carbon as module

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
    from saggio.catalog.refresh import carbon as module

    seen: dict[str, str] = {}

    def capture(request: object, timeout: int = 0) -> FakeResponse:
        seen["url"] = request.full_url  # type: ignore[attr-defined]
        return FakeResponse(json.dumps({"data": []}))

    monkeypatch.setattr(module.urllib.request, "urlopen", capture)
    fetch_grid(["FR"], api_key="irrelevant")
    assert "is_aggregate_entity=false" in seen["url"]
    assert "is_aggregate_series" not in seen["url"]


# --- The processor footprints, and the two guards that make them usable ---------
#
# Both guards exist because the source fails silently in two different ways, and
# each failure produces a number indistinguishable from a real one, under the
# name that was asked for. These are the tests that keep the guards in place.


def boavizta(name: str, die_source: str, value: float = 40.66, die: object = 1600) -> str:
    """Return a reply in the shape that API answers with."""
    return json.dumps(
        {
            "impacts": {"gwp": {"embedded": {"value": value, "min": value, "max": value}}},
            "verbose": {
                "name": {"value": name, "status": "COMPLETED", "source": "fuzzy match"},
                "die_size": {"value": die, "status": "COMPLETED", "source": die_source},
            },
        }
    )


def answer_embodied(monkeypatch: pytest.MonkeyPatch, body: str) -> None:
    """Make the next footprint call return this body instead of opening a socket."""
    from saggio.catalog.refresh import embodied as module

    monkeypatch.setattr(
        module.urllib.request, "urlopen", lambda request, timeout=0: FakeResponse(body)
    )


def test_a_footprint_for_the_chip_that_was_asked_about_is_kept(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from saggio.catalog.refresh import fetch_embodied

    answer_embodied(
        monkeypatch, boavizta("AMD EPYC 7742", "io_die_size (416 mm2) + die_size (16x 74 mm²)")
    )
    refresh = fetch_embodied(["epyc-7742"])
    assert refresh.rows["epyc-7742"][0] == 40.66
    assert refresh.refused == {}


def test_a_chip_the_source_substituted_is_refused_by_name(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Asked for an Apple M4 Max, that source answers about an Apple M1 Max --
    # four generations earlier -- and says so nowhere in the reply. Without this
    # guard the catalogue would carry an M1 Max footprint under three different
    # Apple rows, each looking exactly as well-founded as the vendor figures.
    from saggio.catalog.refresh import fetch_embodied

    answer_embodied(monkeypatch, boavizta("Apple M1 Max", "die_size (432 mm²)", 17.65, 432))
    refresh = fetch_embodied(["apple-m4-max"])
    assert refresh.rows == {}
    assert "Apple M1 Max" in refresh.refused["apple-m4-max"]


@pytest.mark.parametrize(
    "die_source",
    [
        "Average value for all families",
        "Linear regression of cpu_manufacture : Completed from name",
    ],
)
def test_a_footprint_computed_from_a_die_it_invented_is_refused(
    monkeypatch: pytest.MonkeyPatch, die_source: str
) -> None:
    # The footprint is a function of the die, so a default die is a default
    # footprint wearing this chip's name. Asked about a chip called
    # `banana chip 9000` that source returns 19.0 kgCO2e by this route, without
    # a word about the chip not existing.
    from saggio.catalog.refresh import fetch_embodied

    answer_embodied(monkeypatch, boavizta("Intel Xeon Gold 6248", die_source, 19.0, 522.0))
    refresh = fetch_embodied(["xeon-gold-6248"])
    assert refresh.rows == {}
    assert "not this chip's" in refresh.refused["xeon-gold-6248"]


def test_a_key_with_no_vendor_name_is_refused_rather_than_guessed() -> None:
    from saggio.catalog.refresh import fetch_embodied

    refresh = fetch_embodied(["default-server-cpu"])
    assert refresh.rows == {}
    assert "no vendor name" in refresh.refused["default-server-cpu"]


def test_the_accelerator_half_of_that_source_is_refused_in_words() -> None:
    # Asked for any GPU by name it answers 575.1 kgCO2e -- the same number for a
    # GTX 1080 Ti, an A100 and an H100 -- because it holds one archetype called
    # "Large GPU". That is three and a half times NVIDIA's own verified figure
    # for an H100. The refusal is published so the reason travels with the
    # decision rather than living in a commit message -- and it is a function
    # rather than a constant because a reader reads it, and a constant is fixed
    # at import while the language is chosen after.
    from saggio.catalog.refresh import accelerators_refused

    assert "575.1" in accelerators_refused()
    assert "archetype" in accelerators_refused()
    with language("fr"):
        assert "575,1" in accelerators_refused()
        assert "archétype" in accelerators_refused()


def test_writing_a_footprint_states_the_die_it_came_from(tmp_path: pathlib.Path) -> None:
    # A figure computed from a die size is a weaker claim than one a vendor
    # published, and the row has to carry which it is.
    from saggio.catalog.refresh import EmbodiedRefresh, apply_embodied

    target = tmp_path / "hardware.yaml"
    target.write_text('cpus:\n  - key: "epyc-7742"\n    tdp_w: 225\n', encoding="utf-8")
    apply_embodied(target, EmbodiedRefresh({"epyc-7742": (40.66, "AMD EPYC 7742", "1600")}, {}))
    body = target.read_text(encoding="utf-8")
    assert "embodied_kgco2e: 40.66" in body
    assert "1600 mm2" in body
    assert "embodied_source_url:" in body
    assert "embodied_retrieved_date:" in body


def test_writing_twice_replaces_rather_than_stacks(tmp_path: pathlib.Path) -> None:
    from saggio.catalog.refresh import EmbodiedRefresh, apply_embodied

    target = tmp_path / "hardware.yaml"
    target.write_text('cpus:\n  - key: "epyc-7742"\n    tdp_w: 225\n', encoding="utf-8")
    apply_embodied(target, EmbodiedRefresh({"epyc-7742": (40.0, "AMD EPYC 7742", "1600")}, {}))
    apply_embodied(target, EmbodiedRefresh({"epyc-7742": (40.66, "AMD EPYC 7742", "1600")}, {}))
    body = target.read_text(encoding="utf-8")
    assert body.count("embodied_kgco2e:") == 1
    assert "40.66" in body


# --- What each refresh command prints, and what it writes -----------------------
#
# The commands added over one afternoon were the least-covered code in the
# package the morning after: `_refresh_embodied` at 46%, `catalog_refresh` at
# 73%. What went untested was not the fetching -- that is stubbed above -- but
# the half a user actually sees: the lines printed, the refusals named, and the
# second, deliberate step that writes.


def grid_args(**over: object) -> argparse.Namespace:
    """Return the arguments `saggio catalog refresh` is called with."""
    base = {
        "catalog": "grid",
        "api_key": None,
        "year": None,
        "write": None,
        "json": False,
        "column": "carbon",
    }
    return argparse.Namespace(**(base | over))


def answer_both_carbon_paths(monkeypatch: pytest.MonkeyPatch, answer: object) -> None:
    """Make either carbon reader return this, so no branch can reach a network.

    The command picks the keyed API or the published dataset depending on
    whether a key is around, which is an environment this suite does not
    control. Stubbing one of the two left the other free to download thirty
    megabytes and, worse, to pass: a test that patched the API path quietly
    fetched the real file and agreed with it, because the real figure for France
    happened to be the one the test had written down.
    """
    import saggio.cli.commands as commands

    monkeypatch.setattr(commands, "fetch_grid", lambda *a, **k: answer)
    monkeypatch.setattr(commands, "fetch_grid_public", lambda *a, **k: answer)


def test_the_carbon_refresh_prints_what_moved_and_offers_the_write(
    capsys, monkeypatch: pytest.MonkeyPatch
) -> None:
    answer_both_carbon_paths(
        monkeypatch, GridRefresh(2025, {"FR": 999.5}, {"ZZ": "no code"}, "ember")
    )
    assert catalog_refresh(grid_args()) == 0
    out = capsys.readouterr().out
    assert "FR" in out and "999.5" in out
    assert "ZZ" in out and "no code" in out
    # A read-only run has to say it was read-only, or a reader may believe the
    # catalogue already moved.
    assert "Read-only" in out


def test_the_carbon_refresh_writes_only_when_told(
    tmp_path: pathlib.Path, capsys, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "grid.yaml"
    target.write_text('countries:\n  - key: "FR"\n    carbon_gco2e_per_kwh: 56\n', encoding="utf-8")
    answer_both_carbon_paths(monkeypatch, GridRefresh(2025, {"FR": 41.2}, {}, "ember"))
    assert catalog_refresh(grid_args(write=str(target))) == 0
    assert "Wrote 1 row" in capsys.readouterr().out
    assert "41.2" in target.read_text(encoding="utf-8")


def test_a_source_that_does_not_answer_fails_the_command(
    monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    import saggio.cli.commands as commands

    def refuse(*_a: object, **_k: object) -> None:
        raise RuntimeError("Ember did not answer: no route to host")

    monkeypatch.setattr(commands, "fetch_grid", refuse)
    monkeypatch.setattr(commands, "fetch_grid_public", refuse)
    # 4 is the exit code for an external dependency that failed, which is not
    # the same as the catalogue being wrong.
    assert catalog_refresh(grid_args()) == 4


def test_the_tariff_refresh_prints_its_cross_check(capsys, monkeypatch: pytest.MonkeyPatch) -> None:
    """Naming the check matters as much as naming the source.

    The tariffs come from one page and are checked against another. A run that
    printed only the source would leave a reader unable to find the comparison.
    """
    import saggio.cli.commands as commands
    from saggio.catalog.refresh import PRICE_CROSSCHECK, PriceRefresh

    monkeypatch.setattr(
        commands,
        "fetch_prices",
        lambda *a, **k: PriceRefresh({"FR": 0.276}, {"ZZ": "not listed"}, "gpp", "Q3 2026"),
    )
    assert catalog_refresh(grid_args(column="price")) == 0
    out = capsys.readouterr().out
    assert "Q3 2026" in out
    assert "ZZ" in out and "not listed" in out
    assert PRICE_CROSSCHECK in out


def test_the_timezone_check_refuses_to_stamp_a_list_that_did_not_check_out(
    tmp_path: pathlib.Path, capsys, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The one case where this command fails rather than reports.

    Stamping a list as verified when it did not verify would be the package's
    own mistake in miniature, so the exit code says the catalogue is wrong.
    """
    import saggio.cli.commands as commands
    from saggio.catalog.refresh import TimezoneCheck

    monkeypatch.setattr(
        commands,
        "check_timezones",
        lambda *a, **k: TimezoneCheck("2026e", 3, {"ZZ": ["Mars/Olympus"]}),
    )
    target = tmp_path / "grid.yaml"
    target.write_text(
        'countries:\n  - key: "ZZ"\n    timezones: ["Mars/Olympus"]\n', encoding="utf-8"
    )
    before = target.read_text(encoding="utf-8")
    assert catalog_refresh(grid_args(column="timezones", write=str(target))) == 1
    out = capsys.readouterr().out
    assert "Mars/Olympus" in out
    assert target.read_text(encoding="utf-8") == before, "a failed check stamped the file anyway"


def test_the_timezone_check_stamps_the_release_when_it_passes(
    tmp_path: pathlib.Path, capsys, monkeypatch: pytest.MonkeyPatch
) -> None:
    import saggio.cli.commands as commands
    from saggio.catalog.refresh import TimezoneCheck

    monkeypatch.setattr(commands, "check_timezones", lambda *a, **k: TimezoneCheck("2026e", 1, {}))
    target = tmp_path / "grid.yaml"
    target.write_text(
        'countries:\n  - key: "FR"\n    timezones: ["Europe/Paris"]\n', encoding="utf-8"
    )
    assert catalog_refresh(grid_args(column="timezones", write=str(target))) == 0
    assert "2026e" in target.read_text(encoding="utf-8")
    assert "Stamped 1" in capsys.readouterr().out


def test_the_footprint_refresh_names_every_refusal_and_the_method(
    capsys, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The least-covered handler in the package, and the one that refuses most.

    Eight of twelve processors are refused, each for its own reason. A run that
    printed only the four it accepted would read as a complete answer.
    """
    import saggio.cli.commands as commands
    from saggio.catalog.refresh import (
        EMBODIED_METHOD_URL,
        EmbodiedRefresh,
        accelerators_refused,
    )

    monkeypatch.setattr(
        commands,
        "fetch_embodied",
        lambda *a, **k: EmbodiedRefresh(
            {"epyc-7742": (40.66, "AMD EPYC 7742", "1600")},
            {"apple-m4-max": "the source answered about 'Apple M1 Max'"},
        ),
    )
    assert (
        catalog_refresh(
            argparse.Namespace(
                catalog="hardware",
                api_key=None,
                year=None,
                write=None,
                json=False,
                column="embodied",
            )
        )
        == 0
    )
    out = capsys.readouterr().out
    assert "40.66" in out and "1600" in out
    assert "apple-m4-max" in out and "Apple M1 Max" in out
    # The method, because a figure computed from a die size is a weaker claim
    # than a published one and a reader has to be able to judge which.
    assert EMBODIED_METHOD_URL in out
    assert accelerators_refused()[:40] in out


def test_the_footprint_refresh_as_json_carries_the_same_refusals(
    capsys, monkeypatch: pytest.MonkeyPatch
) -> None:
    import saggio.cli.commands as commands
    from saggio.catalog.refresh import EmbodiedRefresh

    monkeypatch.setattr(
        commands,
        "fetch_embodied",
        lambda *a, **k: EmbodiedRefresh(
            {"epyc-7742": (40.66, "AMD EPYC 7742", "1600")}, {"xeon-gold-6248": "default die"}
        ),
    )
    catalog_refresh(
        argparse.Namespace(
            catalog="hardware", api_key=None, year=None, write=None, json=True, column="embodied"
        )
    )
    payload = json.loads(capsys.readouterr().out)
    assert payload["found"]["epyc-7742"]["kgco2e"] == 40.66
    assert payload["refused"] == {"xeon-gold-6248": "default die"}
    assert "accelerators" in payload


def test_the_hardware_catalogue_has_only_one_refreshable_column(capsys) -> None:
    assert (
        catalog_refresh(
            argparse.Namespace(
                catalog="hardware", api_key=None, year=None, write=None, json=False, column="carbon"
            )
        )
        == 2
    )
