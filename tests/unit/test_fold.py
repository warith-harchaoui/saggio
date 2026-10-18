"""Folding a measurement into a model that already exists."""

from __future__ import annotations

from typing import Any

import pytest

from saggio.analyze.power import IDLE_IS_EXCLUDED, PowerReading, states_idle_is_excluded
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
                    "money": {"value": None, "status": "TODO", "unit": "USD", "currency": "USD"},
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


# --- Holes the third audit found, kept closed -----------------------------------


def test_a_stray_scenario_entry_is_refused_not_crashed_on() -> None:
    model = CostModel.from_mapping({"schema_version": "2.1", "scenarios": ["oops"]})
    fold = fold_measurement(model, seconds=1.0)
    assert fold.refused is not None


def test_an_invalid_model_is_refused_before_folding() -> None:
    broken = model_with()
    broken.data["scenarios"][0]["costs"]["money"].pop("currency")
    fold = fold_measurement(broken, seconds=1.0)
    assert fold.refused is not None
    assert "before folding" in fold.refused


def test_folding_writes_the_energy_its_derivations_stand_on() -> None:
    # A model watching money but not energy still gets the energy row, or the
    # money's derived_from would name nothing and the fold would invalidate it.
    model = model_with()
    model.data["scenarios"][0]["costs"].pop("energy")
    fold = fold_measurement(model, seconds=3600.0)
    assert fold.refused is None
    assert "energy" in fold.model.data["scenarios"][0]["costs"]


# --- The pragmatic scaling factor ----------------------------------------------


def _model_with_a_run_size(**assumptions_extra: Any) -> CostModel:
    model = model_with(
        analysis={
            "evidence_source": "static",
            "archetype": "inference",
            "total_work": {"unit": "num_samples", "stated_as": "5000", "source": "config.py"},
        }
    )
    model.data["assumptions"].update(assumptions_extra)
    return model


def test_a_stated_scaling_factor_projects_the_repeated_runs() -> None:
    folded = fold_measurement(
        _model_with_a_run_size(
            pragmatic_scaling_factor={
                "value": 100,
                "status": "estimated",
                "source_url": "https://doi.org/10.1002/advs.202100707",
                "retrieved_date": "2026-09-18",
                "notes": "A conservative hyper-parameter search.",
            }
        ),
        seconds=3600.0,
    )
    assert folded.refused is None
    repeated = folded.model.data["projections"]["repeated_runs"]["costs"]
    whole = folded.model.data["projections"]["whole_run"]["costs"]
    assert repeated["energy"]["value"] == pytest.approx(whole["energy"]["result"]["value"] * 100)
    assert "assumptions.pragmatic_scaling_factor" in repeated["energy"]["derived_from"]
    # The folded model still validates: the weakest-link rule covers the new
    # projection because its derivation is data like everything else.
    from saggio.model.validate import validate

    assert validate(folded.model).ok


def test_an_open_scaling_factor_keeps_the_projection_open() -> None:
    folded = fold_measurement(
        _model_with_a_run_size(pragmatic_scaling_factor={"value": None, "status": "TODO"}),
        seconds=3600.0,
    )
    assert folded.refused is None
    repeated = folded.model.data["projections"]["repeated_runs"]["costs"]
    assert repeated["energy"]["status"] == "TODO"
    assert repeated["energy"].get("value") is None


def test_no_scaling_factor_means_no_repeated_runs_block() -> None:
    folded = fold_measurement(_model_with_a_run_size(), seconds=3600.0)
    assert folded.refused is None
    assert "repeated_runs" not in folded.model.data.get("projections", {})


def test_folding_keeps_what_the_run_established_about_itself() -> None:
    """A folded model must carry the same boundary an audited one does.

    Before this, `measure --into` wrote the number and dropped everything that
    said what the number covered: which counters answered, the floor the machine
    was already drawing, the share of the machine's processor work the run was,
    and what that share attributes. A model produced one way and a model
    produced the other then described the same machine differently, which for a
    package whose argument is that a figure carries its boundary is the worse
    half to lose.
    """
    established = {
        "command": ["python", "-c", "pass"],
        "exit_code": 0,
        "power_scope": "the whole machine",
        "power_sources": ["system-on-chip"],
        "idle_watts": 8.7,
        "cpu_share": {"share": 0.1, "run_cpu_seconds": 0.4, "machine_cpu_seconds": 4.0},
        "attributed_watts": 2.88,
    }

    folded = fold_measurement(model_with(), seconds=1.0, measurement=established)
    assert folded.refused is None
    written = folded.model.data["measurement"]
    assert written["cpu_share"]["share"] == 0.1
    assert written["attributed_watts"] == 2.88
    assert written["idle_watts"] == 8.7
    assert written["power_sources"] == ["system-on-chip"]


def test_folding_without_a_measurement_block_leaves_the_model_alone() -> None:
    # The parameter is optional, and a caller that has nothing to say about the
    # boundary must not be made to invent one.
    folded = fold_measurement(model_with(), seconds=1.0)
    assert folded.refused is None
    assert "measurement" not in folded.model.data


def test_folding_a_measurement_repairs_the_exclusion_it_falsifies() -> None:
    # A model built from a nameplate rating may truthfully say idle capacity is
    # out. The moment a whole-machine reading is folded in, that line is false.
    model = model_with(
        exclusions=[
            "The people. Salaries, offices, and travel are out of scope.",
            IDLE_IS_EXCLUDED,
        ]
    )
    folded = fold_measurement(
        model,
        seconds=1.0,
        power=PowerReading(21.3, 21.3, "soc", by_domain={"cpu": 18.0}),
        measurement={"idle_watts": 9.9, "attributed_watts": 2.6, "cpu_share": {"share": 0.15}},
    )
    assert folded.refused is None
    lines = folded.model.data["exclusions"]
    assert not any(states_idle_is_excluded(line) for line in lines)
    assert "9.9 W of the 21.3 W" in lines[1]
    assert lines[0].startswith("The people"), "only the idle line moves"
    assert any(
        "idle capacity is no longer claimed to be out" in change for change in folded.changes
    )


def test_a_second_fold_refreshes_the_line_rather_than_leaving_stale_watts() -> None:
    once = fold_measurement(
        model_with(exclusions=[IDLE_IS_EXCLUDED]),
        seconds=1.0,
        power=PowerReading(21.3, 21.3, "soc"),
        measurement={"idle_watts": 9.9},
    )
    assert once.refused is None
    twice = fold_measurement(
        once.model,
        seconds=1.0,
        power=PowerReading(30.0, 30.0, "soc"),
        measurement={"idle_watts": 12.0},
    )
    assert twice.refused is None
    line = twice.model.data["exclusions"][0]
    assert "12.0 W of the 30.0 W" in line
    assert "9.9" not in line, "the first measurement's watts survived the second fold"


def test_a_model_without_an_idle_claim_is_not_given_one() -> None:
    # Folding a measurement is not licence to add prose to somebody's document.
    kept = ["The people. Salaries, offices, and travel are out of scope."]
    folded = fold_measurement(
        model_with(exclusions=list(kept)),
        seconds=1.0,
        power=PowerReading(21.3, 21.3, "soc"),
        measurement={"idle_watts": 9.9},
    )
    assert folded.refused is None
    assert folded.model.data["exclusions"] == kept
