"""The carbon that was emitted before the machine was switched on."""

from __future__ import annotations

import pytest

from saggio.estimate.embodied import (
    GRAMS_PER_KILOGRAM,
    HOURS_PER_YEAR,
    embodied_carbon,
    software_carbon_intensity,
)
from saggio.model import Quantity


def kg(value: float) -> Quantity:
    return Quantity(value=value, unit="kgCO2e", status="estimated")


def years(value: float) -> Quantity:
    return Quantity(value=value, unit="years", status="estimated")


def hours(value: float) -> Quantity:
    return Quantity(value=value, unit="h", status="measured")


# --- The arithmetic ----------------------------------------------------------


def test_a_whole_lifetime_of_work_carries_the_whole_footprint() -> None:
    # The sanity check the formula has to pass: run the thing for its entire
    # life and you are answerable for all of what building it emitted.
    whole = embodied_carbon(embodied=kg(164.0), lifetime=years(4.0), runtime=years(4.0))
    assert whole.value == pytest.approx(164.0 * GRAMS_PER_KILOGRAM)


def test_an_hour_of_a_four_year_card_is_that_share_of_it() -> None:
    figure = embodied_carbon(embodied=kg(164.0), lifetime=years(4.0), runtime=hours(1.0))
    assert figure.value == pytest.approx(164_000.0 / (4.0 * HOURS_PER_YEAR))


def test_half_the_hardware_is_half_the_carbon() -> None:
    full = embodied_carbon(embodied=kg(164.0), lifetime=years(4.0), runtime=hours(1.0))
    half = embodied_carbon(
        embodied=kg(164.0),
        lifetime=years(4.0),
        runtime=hours(1.0),
        resource_share=Quantity(value=0.5, unit="ratio", status="estimated"),
    )
    assert half.value == pytest.approx(full.value / 2.0)


def test_kilograms_become_grams_rather_than_staying_kilograms() -> None:
    # Vendors publish kilograms; every carbon figure here is in grams. Mixing
    # them silently would be a thousandfold error in the flattering direction.
    figure = embodied_carbon(embodied=kg(1.0), lifetime=years(1.0), runtime=years(1.0))
    assert figure.unit == "gCO2e"
    assert figure.value == pytest.approx(1000.0)


@pytest.mark.parametrize(
    ("unit", "value", "expected_hours"),
    [
        ("s", 3600.0, 1.0),
        ("seconds", 7200.0, 2.0),
        ("minutes", 30.0, 0.5),
        ("h", 5.0, 5.0),
        ("days", 1.0, 24.0),
        ("years", 1.0, HOURS_PER_YEAR),
    ],
)
def test_a_runtime_is_converted_from_whatever_unit_it_was_written_in(
    unit: str, value: float, expected_hours: float
) -> None:
    figure = embodied_carbon(
        embodied=kg(1.0),
        lifetime=Quantity(value=1.0, unit="h", status="estimated"),
        runtime=Quantity(value=value, unit=unit, status="measured"),
    )
    assert figure.value == pytest.approx(1000.0 * expected_hours)


def test_a_unit_nobody_taught_it_is_refused_rather_than_guessed() -> None:
    figure = embodied_carbon(
        embodied=kg(164.0),
        lifetime=years(4.0),
        runtime=Quantity(value=1.0, unit="furlongs", status="measured"),
    )
    assert figure.status == "TODO"


# --- The refusals ------------------------------------------------------------


def test_an_unpriced_part_gives_an_open_figure_not_a_zero() -> None:
    figure = embodied_carbon(
        embodied=Quantity(unit="kgCO2e", status="TODO"), lifetime=years(4.0), runtime=hours(1.0)
    )
    assert figure.status == "TODO"
    assert figure.value is None
    assert "free to build" in str(figure.notes)


def test_no_lifetime_means_nothing_to_amortise_over() -> None:
    figure = embodied_carbon(
        embodied=kg(164.0), lifetime=Quantity(unit="years", status="TODO"), runtime=hours(1.0)
    )
    assert figure.status == "TODO"
    assert "three and six years" in str(figure.notes)


@pytest.mark.parametrize("lifetime", [0.0, -1.0])
def test_a_lifetime_that_is_not_positive_is_refused(lifetime: float) -> None:
    assert (
        embodied_carbon(embodied=kg(164.0), lifetime=years(lifetime), runtime=hours(1.0)).status
        == "TODO"
    )


@pytest.mark.parametrize("share", [0.0, -0.5, 1.5])
def test_a_resource_share_outside_zero_to_one_is_refused(share: float) -> None:
    figure = embodied_carbon(
        embodied=kg(164.0),
        lifetime=years(4.0),
        runtime=hours(1.0),
        resource_share=Quantity(value=share, unit="ratio", status="estimated"),
    )
    assert figure.status == "TODO"


# --- What it may claim -------------------------------------------------------


def test_a_published_footprint_on_a_measured_runtime_is_still_only_estimated() -> None:
    # A measured runtime multiplied by somebody's published figure is an
    # inference about a part, not a reading off this machine.
    figure = embodied_carbon(embodied=kg(164.0), lifetime=years(4.0), runtime=hours(1.0))
    assert figure.status == "estimated"


def test_the_note_says_which_convention_was_used() -> None:
    figure = embodied_carbon(embodied=kg(164.0), lifetime=years(4.0), runtime=hours(1.0))
    assert "calendar life" in str(figure.notes)
    assert "busy hours" in str(figure.notes)


# --- The score ---------------------------------------------------------------


def test_the_score_is_the_two_halves_added() -> None:
    score = software_carbon_intensity(
        operational=Quantity(value=26.9, unit="gCO2e", status="estimated"),
        embodied=Quantity(value=4.7, unit="gCO2e", status="estimated"),
    )
    assert score.value == pytest.approx(31.6)


def test_an_open_half_opens_the_score_rather_than_being_dropped() -> None:
    # Reporting one half under the name of a standard would understate it with
    # the standard's authority.
    score = software_carbon_intensity(
        operational=Quantity(value=26.9, unit="gCO2e", status="estimated"),
        embodied=Quantity(unit="gCO2e", status="TODO"),
    )
    assert score.status == "TODO"
    assert score.value is None


def test_the_score_is_never_stronger_than_its_weaker_half() -> None:
    score = software_carbon_intensity(
        operational=Quantity(value=1.0, unit="gCO2e", status="measured"),
        embodied=Quantity(value=1.0, unit="gCO2e", status="estimated"),
    )
    assert score.status == "estimated"


def test_the_score_names_the_standard_it_implements() -> None:
    score = software_carbon_intensity(
        operational=Quantity(value=1.0, unit="gCO2e", status="estimated"),
        embodied=Quantity(value=1.0, unit="gCO2e", status="estimated"),
    )
    assert "21031" in str(score.notes)


# --- The catalogue it reads from --------------------------------------------


@pytest.mark.parametrize(("key", "expected"), [("A100", 127.6), ("H100", 164.0), ("B200", 284.25)])
def test_the_catalogue_carries_a_sourced_footprint(key: str, expected: float) -> None:
    from saggio.catalog.registry import Catalog

    row = Catalog.bundled("hardware").rows("gpus")[key]
    assert row["embodied_kgco2e"] == pytest.approx(expected)
    # A footprint is not a datasheet, so it carries its own provenance.
    assert row["embodied_source_url"].startswith("https://")
    assert row["embodied_retrieved_date"]
    assert "cradle-to-gate" in row["embodied_scope"]
