"""The catalogues: provenance, overlays, and staleness that matches the fact."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest
import yaml

from running_code_cost_helper.catalog.registry import (
    BUNDLED_CATALOGS,
    SECTION_OF_KIND,
    Catalog,
    add_row,
    carries_numbers,
    days_since,
    is_stale,
    overlay_directory,
    require_provenance,
    stale_after_days,
    stale_report,
)


@pytest.mark.parametrize("name", BUNDLED_CATALOGS)
def test_every_bundled_catalogue_loads_and_has_rows(name: str, overlay: Path) -> None:
    catalog = Catalog.load(name, overlay=overlay)
    assert catalog.sections()
    assert any(catalog.rows(section) for section in catalog.sections())


def test_an_unknown_catalogue_is_refused_by_name() -> None:
    with pytest.raises(ValueError, match="Unknown catalogue"):
        Catalog.load("vibes")


def test_a_missing_row_is_a_normal_answer(overlay: Path) -> None:
    assert Catalog.load("grid", overlay=overlay).row("countries", "ZZ") is None


def test_a_missing_section_iterates_empty(overlay: Path) -> None:
    assert Catalog.load("hardware", overlay=overlay).rows("nonexistent") == {}


# --- Overlays ----------------------------------------------------------------


def test_an_overlay_row_replaces_a_bundled_one(overlay: Path) -> None:
    add_row(
        "gpu",
        {
            "key": "A100",
            "tdp_w": 1,
            "source_url": "https://example.invalid",
            "retrieved_date": "2026-09-12",
        },
        overlay=overlay,
    )
    assert Catalog.load("hardware", overlay=overlay).row("gpus", "A100")["tdp_w"] == 1


def test_an_overlay_row_can_be_new(overlay: Path) -> None:
    add_row(
        "gpu",
        {
            "key": "FUTURE-1",
            "tdp_w": 900,
            "source_url": "https://example.invalid",
            "retrieved_date": "2026-09-12",
        },
        overlay=overlay,
    )
    assert "FUTURE-1" in Catalog.load("hardware", overlay=overlay).keys("gpus")


def test_adding_the_same_key_twice_updates_rather_than_duplicates(overlay: Path) -> None:
    for wattage in (100, 200):
        add_row(
            "gpu",
            {
                "key": "X",
                "tdp_w": wattage,
                "source_url": "https://example.invalid",
                "retrieved_date": "2026-09-12",
            },
            overlay=overlay,
        )
    written = yaml.safe_load((overlay / "hardware.yaml").read_text(encoding="utf-8"))
    assert [row["key"] for row in written["gpus"]] == ["X"]
    assert written["gpus"][0]["tdp_w"] == 200


def test_bundled_order_survives_an_overlay(overlay: Path) -> None:
    before = Catalog.load("hardware", overlay=overlay).keys("gpus")
    add_row(
        "gpu",
        {"key": "ZZZ", "tdp_w": 1, "source_url": "u", "retrieved_date": "2026-09-12"},
        overlay=overlay,
    )
    after = Catalog.load("hardware", overlay=overlay).keys("gpus")
    assert after[: len(before)] == before


def test_an_unreadable_overlay_does_not_stop_the_bundled_data(overlay: Path) -> None:
    (overlay / "hardware.yaml").write_text("gpus: [unterminated\n", encoding="utf-8")
    assert "A100" in Catalog.load("hardware", overlay=overlay).keys("gpus")


def test_the_overlay_directory_is_created_on_demand() -> None:
    assert overlay_directory().is_dir()


# --- Provenance --------------------------------------------------------------


@pytest.mark.parametrize(
    ("row", "complaint"),
    [
        ({}, "needs a key"),
        ({"key": "X"}, "source_url"),
        ({"key": "X", "source_url": "u"}, "retrieved_date"),
        ({"key": "X", "source_url": "u", "retrieved_date": "yesterday"}, "retrieved_date"),
    ],
)
def test_a_row_without_provenance_is_refused(row: dict, complaint: str) -> None:
    with pytest.raises(ValueError, match=complaint):
        require_provenance(row)


def test_a_row_with_provenance_is_accepted() -> None:
    require_provenance({"key": "X", "source_url": "u", "retrieved_date": "2026-09-12"})


def test_adding_an_unknown_kind_lists_the_known_ones(overlay: Path) -> None:
    with pytest.raises(ValueError, match="Known kinds"):
        add_row("vibes", {"key": "X"}, overlay=overlay)


@pytest.mark.parametrize("kind", sorted(SECTION_OF_KIND))
def test_every_kind_can_be_added_and_read_back(kind: str, overlay: Path) -> None:
    add_row(
        kind,
        {
            "key": "TEST-KEY",
            "source_url": "https://example.invalid",
            "retrieved_date": "2026-09-12",
        },
        overlay=overlay,
    )
    name, section = SECTION_OF_KIND[kind]
    assert Catalog.load(name, overlay=overlay).row(section, "TEST-KEY") is not None


# --- Freshness ---------------------------------------------------------------


def test_a_tariff_goes_stale_long_before_a_datasheet() -> None:
    assert stale_after_days("country") < stale_after_days("gpu")


def test_staleness_is_measured_against_the_right_threshold() -> None:
    row = {"tdp_w": 1, "retrieved_date": "2026-01-01"}
    assert is_stale(row, "country", today=date(2026, 6, 1))
    assert not is_stale(row, "gpu", today=date(2026, 6, 1))


def test_a_row_asserting_a_number_with_no_date_is_stale() -> None:
    assert is_stale({"tdp_w": 1}, "gpu")


def test_a_row_asserting_nothing_numeric_never_goes_stale() -> None:
    # A service row says where a price lives, not what it is. A pointer cannot be
    # out of date; the price somebody copied out of it can, and that lives in
    # their model where the validator watches it.
    assert not is_stale({"pricing_source_url": "https://example.invalid"}, "service")
    assert not carries_numbers({"key": "openai", "detect": ["import openai"]})


def test_booleans_do_not_count_as_numbers() -> None:
    assert not carries_numbers({"key": "X", "enabled": True})


@pytest.mark.parametrize(
    ("value", "expected"), [("2026-01-01", 60), ("not a date", None), (None, None), (7, None)]
)
def test_the_age_of_a_provenance_date(value: object, expected: int | None) -> None:
    assert days_since(value, today=date(2026, 3, 2)) == expected


def test_the_bundled_catalogues_are_fresh_today(overlay: Path) -> None:
    # This is the gate that stops the package shipping numbers nobody has looked
    # at. When it fails, the fix is to re-read the sources, not to raise the
    # threshold.
    assert stale_report(overlay=overlay, today=date(2026, 9, 12)) == {}


def test_the_report_names_what_went_stale(overlay: Path) -> None:
    stale = stale_report(overlay=overlay, today=date(2030, 1, 1))
    assert "country" in stale
    assert "FR" in stale["country"]
