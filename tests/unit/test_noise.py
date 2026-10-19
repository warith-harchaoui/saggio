"""The band a repeated measurement leaves around a figure.

The defect these exist for: `saggio diff` gated a release at ten per cent
against numbers whose own measurement block said they move by a hundred. It had
the evidence in both files it was comparing and read neither.
"""

from __future__ import annotations

import pytest

from saggio.model import CostModel
from saggio.model.noise import Band, band_for

#: A model shaped like one `measure --repeat 5 --into` writes, with round
#: numbers so the arithmetic below can be read rather than trusted.
MEASURED = {
    "schema_version": "2.1",
    "measurement": {
        "repeats": 5,
        "spread": {
            "runtime_s": {
                "low": 1.0,
                "median": 2.0,
                "high": 4.0,
                "runs": [1.0, 2.0, 2.0, 3.0, 4.0],
            },
            "power_w": {
                "low": 5.0,
                "median": 30.0,
                "high": 20.0,
                "runs": [5.0, 10.0, 30.0, 15.0, 20.0],
            },
        },
    },
    "assumptions": {
        "power_draw": {"value": 10.0, "unit": "W", "status": "measured"},
        "machine_energy": {
            "value": 100.0,
            "unit": "kWh",
            "status": "measured",
            "derived_from": ["scenarios[0].runtime", "assumptions.power_draw"],
        },
        "pue": {"value": 1.5, "unit": "ratio", "status": "estimated"},
    },
    "scenarios": [
        {
            "name": "as-audited",
            "runtime": {"value": 2.0, "unit": "s", "status": "measured"},
            "costs": {
                "time": {"value": 2.0, "unit": "s", "status": "measured"},
                "energy": {
                    "value": 150.0,
                    "unit": "kWh",
                    "status": "estimated",
                    "derived_from": ["assumptions.machine_energy", "assumptions.pue"],
                },
            },
        }
    ],
    "projections": {
        "whole_run": {"costs": {"energy": {"result": {"value": 1500.0, "status": "estimated"}}}}
    },
}


def model() -> CostModel:
    return CostModel.from_mapping(MEASURED)


# --- What a band is ----------------------------------------------------------


def test_overlapping_bands_mean_one_number_could_have_been_the_other() -> None:
    assert Band(1.0, 5.0).overlaps(Band(4.0, 9.0))
    assert Band(1.0, 5.0).overlaps(Band(5.0, 9.0)), "touching at a point is overlapping"
    assert not Band(1.0, 5.0).overlaps(Band(5.1, 9.0))


def test_a_band_names_what_it_was_measured_from() -> None:
    # A width a reader cannot trace is a width they have to take on trust.
    assert "from the power" in Band(1.0, 2.0, ("the power",)).describe()


# --- Where a band comes from -------------------------------------------------


def test_the_power_band_is_anchored_on_the_figure_the_model_carries() -> None:
    # Not on the spread's median. The representative run is chosen by runtime,
    # so the power beside it is that run's power — 10 W here against a middle
    # of 30 W — and anchoring on the median would scale the band by three.
    band = band_for(model(), "assumptions.power_draw")
    assert (band.low, band.high) == (5.0, 20.0)


def test_the_runtime_band_is_anchored_on_the_spread_median() -> None:
    # Which is the representative run's own wall-clock time, by construction.
    band = band_for(model(), "scenarios[0].runtime")
    assert (band.low, band.high) == (1.0, 4.0)


def test_a_cost_scaled_from_the_runtime_is_scaled_the_same_way() -> None:
    assert band_for(model(), "scenarios[0].costs.time") == Band(1.0, 4.0, ("the runtime",), 5)


def test_a_figure_derived_from_both_multiplies_both_ranges() -> None:
    # machine_energy is 100, runtime moved x0.5 to x2, power x0.5 to x2.
    band = band_for(model(), "assumptions.machine_energy")
    assert (band.low, band.high) == (25.0, 400.0)
    assert band.sources == ("the power", "the runtime")


def test_the_walk_is_transitive_through_derived_from() -> None:
    # energy -> machine_energy -> runtime and power. The PUE is an estimate and
    # contributes no range, which is right: it is not a thing anybody measured
    # five times.
    band = band_for(model(), "scenarios[0].costs.energy")
    assert (band.low, band.high) == (37.5, 600.0)


def test_a_projection_takes_its_scenario_costs_band() -> None:
    # Linked here and not in the model: a projection divides by a fraction
    # nobody named, so claiming it *derives* from the cost is false and the
    # validator refuses it. A band needs only proportionality.
    band = band_for(model(), "projections.whole_run.costs.energy.result")
    assert (band.low, band.high) == (375.0, 6000.0)


def test_an_estimate_nobody_repeated_gets_no_band_at_all() -> None:
    # And no band is not a narrow band: it means nothing bounds this figure,
    # so the caller gates it exactly as it always did.
    assert band_for(model(), "assumptions.pue") is None


def test_a_model_that_repeated_nothing_bounds_nothing() -> None:
    once = {k: v for k, v in MEASURED.items() if k != "measurement"}
    assert band_for(CostModel.from_mapping(once), "assumptions.power_draw") is None


def test_a_malformed_spread_block_yields_no_band_rather_than_a_wrong_one() -> None:
    broken = {**MEASURED, "measurement": {"repeats": 5, "spread": {"power_w": {"low": "five"}}}}
    assert band_for(CostModel.from_mapping(broken), "assumptions.power_draw") is None


def test_a_derivation_cycle_terminates() -> None:
    looped = {
        "schema_version": "2.1",
        "measurement": {
            "repeats": 2,
            "spread": {"runtime_s": {"low": 1.0, "median": 2.0, "high": 3.0}},
        },
        "assumptions": {
            "a": {"value": 1.0, "status": "estimated", "derived_from": ["assumptions.b"]},
            "b": {"value": 1.0, "status": "estimated", "derived_from": ["assumptions.a"]},
        },
    }
    assert band_for(CostModel.from_mapping(looped), "assumptions.a") is None


def test_a_band_carries_how_many_runs_it_came_from() -> None:
    # The width of a range means little without the count behind it.
    band = band_for(model(), "assumptions.power_draw")
    assert band.runs == 5
    assert band.outside_odds() == pytest.approx(1 / 3)


def test_a_band_from_two_ranges_is_only_as_founded_as_the_thinner() -> None:
    thin = {**MEASURED}
    thin["measurement"] = {
        "repeats": 3,
        "spread": {
            "runtime_s": {"low": 1.0, "median": 2.0, "high": 4.0, "runs": [1.0, 2.0, 4.0]},
            "power_w": {"low": 5.0, "median": 30.0, "high": 20.0, "runs": [5.0] * 5},
        },
    }
    band = band_for(CostModel.from_mapping(thin), "assumptions.machine_energy")
    assert band.runs == 3, "a product of two ranges is no better founded than the thinner"


def test_a_side_that_repeated_nothing_claims_no_odds() -> None:
    assert Band(1.0, 2.0).outside_odds() is None
