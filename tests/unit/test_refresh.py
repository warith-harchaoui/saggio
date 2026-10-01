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

    monkeypatch.setattr(
        commands,
        "fetch_grid",
        lambda *a, **k: GridRefresh(2025, {"FR": 41.4}, {"ZZ": "no code"}, "ember"),
    )
    args = argparse.Namespace(catalog="grid", api_key=None, year=None, write=None, json=True)
    catalog_refresh(args)
    payload = json.loads(capsys.readouterr().out)
    assert payload["data_year"] == 2025
    assert payload["changed"]["FR"]["now"] == pytest.approx(41.4)
    assert payload["skipped"] == {"ZZ": "no code"}
