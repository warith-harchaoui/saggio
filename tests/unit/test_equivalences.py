"""Carbon restated as trees, kilometres, and flights, without gaining confidence."""

from __future__ import annotations

import pytest

from saggio.estimate.equivalences import (
    CAR_GCO2_PER_KM,
    FLIGHT_GCO2,
    TREE_MONTH_GCO2,
    car_km,
    equivalences,
    flight_fraction,
    tree_months,
)
from saggio.model import Quantity


def carbon(value: float | None, status: str = "estimated") -> Quantity:
    return Quantity(value=value, unit="gCO2e", status=status)


# --- The arithmetic ----------------------------------------------------------


def test_a_years_worth_of_tree_is_twelve_tree_months() -> None:
    assert tree_months(carbon(11_000.0)).value == pytest.approx(12.0)


def test_the_papers_worked_example_lands_near_its_figure() -> None:
    # The paper's Figure 1: 1.50 kg CO2e reads as 1.64 tree-months.
    assert tree_months(carbon(1_500.0)).value == pytest.approx(1.64, abs=0.01)


def test_a_european_car_kilometre_is_175_grams() -> None:
    assert car_km(carbon(175.0)).value == pytest.approx(1.0)


def test_an_american_car_is_dirtier_per_kilometre() -> None:
    assert car_km(carbon(1000.0), "US").value < car_km(carbon(1000.0), "EU").value


def test_half_a_paris_london_flight() -> None:
    assert flight_fraction(carbon(25_000.0), "paris-london").value == pytest.approx(0.5)


def test_a_fraction_may_exceed_one() -> None:
    assert flight_fraction(carbon(150_000.0), "paris-london").value == pytest.approx(3.0)


# --- Confidence --------------------------------------------------------------


def test_a_measured_carbon_still_gives_an_estimated_equivalence() -> None:
    # The conversion factor is a published average; the tree is an average tree.
    assert tree_months(carbon(1000.0, "measured")).status == "estimated"


def test_an_open_carbon_gives_an_open_equivalence() -> None:
    for restated in (tree_months, car_km, flight_fraction):
        result = restated(carbon(None, "TODO"))
        assert result.status == "TODO"
        assert result.value is None


def test_every_equivalence_names_its_source() -> None:
    for restated in equivalences(carbon(50_000.0)).values():
        assert restated.source_url


# --- Refusals ----------------------------------------------------------------


def test_an_unknown_region_is_refused_not_defaulted() -> None:
    with pytest.raises(ValueError, match="region"):
        car_km(carbon(1000.0), "MARS")


def test_an_unknown_route_is_refused_not_defaulted() -> None:
    with pytest.raises(ValueError, match="flight"):
        flight_fraction(carbon(1000.0), "paris-tokyo")


# --- The convenience ---------------------------------------------------------


def test_the_full_set_has_the_three_restatements() -> None:
    assert sorted(equivalences(carbon(1e6))) == ["car_km", "flight", "tree_months"]


def test_the_flight_is_chosen_to_keep_the_fraction_readable() -> None:
    # A small figure reads against the short hop, a huge one against the long haul.
    small = equivalences(carbon(10_000.0))["flight"]
    huge = equivalences(carbon(1e8))["flight"]
    assert "paris-london" in small.unit
    assert "new-york-melbourne" in huge.unit


def test_the_coefficients_are_the_papers() -> None:
    assert TREE_MONTH_GCO2 == pytest.approx(11_000.0 / 12.0)
    assert CAR_GCO2_PER_KM == {"EU": 175.0, "US": 251.0}
    assert FLIGHT_GCO2["paris-london"] == 50_000.0
