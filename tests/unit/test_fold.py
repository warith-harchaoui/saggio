"""Folding a measurement into a model that already exists."""

from __future__ import annotations

from typing import Any

import pytest

from saggio.analyze.power import PowerReading
from saggio.fold import fold_measurement
from saggio.model import CostModel


def model_with(**extra: Any) -> CostModel:
    """A small but complete model, ready to be folded into."""
    data: dict[str, Any] = {
        "schema_version": "2.1",
        "date_updated": "2026-09-14",
        "unit_of_work": {"name": "one request", "status": "estimated"},
        "deployment": {"provider": "on-prem", "country": "FR"},
        "assumptions": {
            "power_draw": {"value": 100.0, "unit": "W", "status": "estimated"},
            "pue": {"value": 1.2, "unit": "ratio", "status": "estimated"},
            "electricity_price": {
                "value": 0.2,
                "unit": "USD/kWh",
                "currency": "USD",
                "status": "estimated",
            },
            "grid_carbon_intensity": {
                "value": 50.0,
                "unit": "gCO2e/kWh",
                "status": "estimated",
            },
        },
        "scenarios": [
            {
                "name": "as-audited",
                "runtime": {"value": None, "status": "TODO", "unit": "s"},
                "costs": {
                    "time": {"value": None, "status": "TODO", "unit": "s"},
                    "energy": {"value": None, "status": "TODO", "unit": "kWh"},
                    "money": {"value": None, "status": "TODO", "unit": "USD"},
                    "carbon": {"value": None, "status": "TODO", "unit": "gCO2e"},
                },
            }
        ],
    }
    data.update(extra)
    return CostModel.from_mapping(data)


# --- What it refuses ---------------------------------------------------------


def test_a_model_with_no_scenario_is_refused() -> None:
    folded = fold_measurement(
        CostModel.from_mapping({"schema_version": "2.1", "scenarios": []}), seconds=1.0
    )
    assert folded.refused is not None
    assert folded.changes == ()


def test_a_scenario_that_is_not_there_is_refused_by_name() -> None:
    folded = fold_measurement(model_with(), seconds=1.0, scenario="production")
    assert "production" in str(folded.refused)


@pytest.mark.parametrize("units", [0.0, -1.0])
def test_a_command_cannot_have_performed_no_units(units: float) -> None:
    assert fold_measurement(model_with(), seconds=1.0, units=units).refused is not None


def test_a_run_of_no_duration_is_not_a_measurement() -> None:
    assert fold_measurement(model_with(), seconds=0.0).refused is not None


def test_the_model_handed_in_is_never_modified() -> None:
    # A fold that edited in place would leave a caller holding a model that
    # changed under them, and a refusal that had already half-written it.
    model = model_with()
    fold_measurement(model, seconds=2.0)
    assert model.data["scenarios"][0]["runtime"]["status"] == "TODO"


# --- What it writes ----------------------------------------------------------


def test_the_runtime_arrives_measured() -> None:
    folded = fold_measurement(model_with(), seconds=2.0)
    runtime = folded.model.data["scenarios"][0]["runtime"]
    assert runtime["value"] == pytest.approx(2.0)
    assert runtime["status"] == "measured"


def test_the_units_the_command_performed_divide_the_runtime() -> None:
    # A command that scores five hundred samples measured five hundred of them,
    # and a model's figures are per unit.
    folded = fold_measurement(model_with(), seconds=2.0, units=500)
    assert folded.model.data["scenarios"][0]["runtime"]["value"] == pytest.approx(0.004)
    assert "500" in folded.model.data["scenarios"][0]["runtime"]["notes"]


def test_everything_derived_from_the_runtime_is_recomputed() -> None:
    # This is the whole reason the command exists. Writing the runtime by hand
    # leaves these three holding the old value, and a model whose energy does not
    # match its runtime is worse than one that has neither.
    folded = fold_measurement(model_with(), seconds=3600.0)
    costs = folded.model.data["scenarios"][0]["costs"]
    assert costs["energy"]["value"] == pytest.approx(0.12)
    assert costs["money"]["value"] == pytest.approx(0.024)
    assert costs["carbon"]["value"] == pytest.approx(6.0)


def test_a_measured_runtime_does_not_make_the_energy_measured() -> None:
    # The power came from a datasheet, so the product of the two is an estimate.
    # The weakest-link rule is not applied afterwards; it is what comes out.
    folded = fold_measurement(model_with(), seconds=3600.0)
    costs = folded.model.data["scenarios"][0]["costs"]
    assert costs["time"]["status"] == "measured"
    assert costs["energy"]["status"] == "estimated"


def test_every_derived_cost_names_what_it_came_from() -> None:
    folded = fold_measurement(model_with(), seconds=10.0)
    energy = folded.model.data["scenarios"][0]["costs"]["energy"]
    assert "assumptions.pue" in energy["derived_from"]
    assert "assumptions.machine_energy" in energy["derived_from"]


def test_a_dimension_the_model_never_carried_is_not_invented() -> None:
    # Folding a measurement answers the questions a model already asked. It does
    # not decide the model should have asked more of them.
    folded = fold_measurement(model_with(), seconds=10.0)
    assert "water" not in folded.model.data["scenarios"][0]["costs"]


def test_what_moved_is_reported_rather_than_written_in_silence() -> None:
    folded = fold_measurement(model_with(), seconds=10.0)
    assert any("runtime" in change for change in folded.changes)
    assert any("TODO -> measured" in change for change in folded.changes)


# --- Power -------------------------------------------------------------------


def test_a_measured_power_replaces_the_datasheet_figure() -> None:
    folded = fold_measurement(
        model_with(),
        seconds=3600.0,
        power=PowerReading(watts=200.0, joules=720000.0, scope="the board", sources=("board",)),
    )
    power = folded.model.data["assumptions"]["power_draw"]
    assert power["value"] == pytest.approx(200.0)
    assert power["status"] == "measured"
    # Runtime measured times power measured is a measured energy for the machine.
    assert folded.model.data["assumptions"]["machine_energy"]["status"] == "measured"
    # The building's energy is that times a datacenter overhead nobody measured,
    # so it weakens by one step, and the money and carbon below it with it.
    assert folded.model.data["scenarios"][0]["costs"]["energy"]["status"] == "estimated"


def test_a_machine_that_measured_nothing_leaves_the_estimate_alone() -> None:
    # Replacing a sourced estimate with silence would lose the only figure there
    # was, and the run still measured a duration worth keeping.
    folded = fold_measurement(
        model_with(),
        seconds=3600.0,
        power=PowerReading(watts=None, joules=None, scope="no counter here"),
    )
    assert folded.model.data["assumptions"]["power_draw"]["status"] == "estimated"
    assert folded.model.data["assumptions"]["power_draw"]["value"] == pytest.approx(100.0)


# --- The whole run -----------------------------------------------------------


def test_a_whole_run_is_projected_when_the_model_says_how_long_one_is() -> None:
    model = model_with(
        analysis={
            "evidence_source": "static",
            "archetype": "inference",
            "total_work": {"unit": "num_samples", "stated_as": "5000", "source": "config.py"},
        }
    )
    folded = fold_measurement(model, seconds=1.0, units=1)
    whole = folded.model.data["projections"]["whole_run"]
    assert whole["costs"]["time"]["result"]["value"] == pytest.approx(5000.0)
    # The assumption that one unit of work is one of the things the repository
    # counts is stated, because when it is false the projection is wrong by
    # exactly the difference.
    assert "assumes one unit of work" in whole["description"]


def test_no_whole_run_is_projected_when_nothing_says_how_long_one_is() -> None:
    folded = fold_measurement(model_with(), seconds=1.0)
    assert "projections" not in folded.model.data


def test_a_stated_run_length_that_is_not_a_number_projects_nothing() -> None:
    model = model_with(
        analysis={"total_work": {"unit": "epochs", "stated_as": "many", "source": "config.py"}}
    )
    assert "projections" not in fold_measurement(model, seconds=1.0).model.data
