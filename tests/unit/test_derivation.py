"""Checking that a derived number follows from the numbers it names."""

from __future__ import annotations

import pytest

from saggio.model import CostModel, validate
from saggio.model.derivation import KIND_OF_UNIT, combine, disagrees, unreachable

# --- The arithmetic ----------------------------------------------------------


def test_seconds_times_watts_give_kilowatt_hours() -> None:
    assert combine([(3600.0, "s"), (400.0, "W")], "kWh") == pytest.approx(0.4)


def test_the_order_of_the_inputs_does_not_matter() -> None:
    assert combine([(400.0, "W"), (3600.0, "s")], "kWh") == pytest.approx(0.4)


def test_a_dimensionless_factor_leaves_the_unit_alone() -> None:
    assert combine([(0.4, "kWh"), (1.2, "ratio")], "kWh") == pytest.approx(0.48)


def test_an_intensity_cancels_its_denominator() -> None:
    assert combine([(0.48, "kWh"), (56.0, "gCO2e/kWh")], "gCO2e") == pytest.approx(26.88)


def test_a_price_works_the_same_way_as_an_intensity() -> None:
    assert combine([(0.48, "kWh"), (0.24, "USD/kWh")], "USD") == pytest.approx(0.1152)


def test_a_single_input_restated_in_its_own_unit_is_the_identity() -> None:
    assert combine([(3600.0, "s")], "s") == pytest.approx(3600.0)


def test_an_intensity_that_cancels_but_gives_the_wrong_numerator_is_refused() -> None:
    # kWh times USD/kWh is USD, never grams. Returning the product here would
    # have let a price be labelled as carbon.
    assert combine([(0.48, "kWh"), (0.24, "USD/kWh")], "gCO2e") is None


@pytest.mark.parametrize(
    "inputs",
    [
        [(1.0, "furlong")],
        [(1.0, "s"), (1.2, "ratio")],
        [(1.0, "kgCO2e"), (4.0, "years"), (3600.0, "s")],
    ],
)
def test_a_relationship_this_does_not_know_gets_no_answer(inputs: list) -> None:
    # Silence is the ordinary answer. A dimension somebody registered this
    # morning must not fail because this module has not heard of it.
    assert combine(inputs, "gCO2e") is None


# --- The impossibility -------------------------------------------------------


def test_a_duration_times_a_plain_number_can_never_be_carbon() -> None:
    assert unreachable([(1.0, "s"), (1.2, "ratio")], "gCO2e") is not None


def test_two_units_of_the_same_kind_are_left_alone() -> None:
    # Seconds to minutes is a conversion this does not perform, so it says
    # nothing rather than calling a correct model wrong.
    assert unreachable([(3600.0, "s")], "min") is None


def test_an_unknown_unit_is_somebody_elses_dimension() -> None:
    assert unreachable([(1.0, "widgets")], "gCO2e") is None
    assert unreachable([(1.0, "s")], "widgets") is None


def test_two_carrying_inputs_are_beyond_what_it_claims_to_know() -> None:
    assert unreachable([(1.0, "kWh"), (56.0, "gCO2e/kWh")], "gCO2e") is None


def test_every_unit_the_canonical_dimensions_use_has_a_kind() -> None:
    from saggio.model.dimensions import CANONICAL_DIMENSIONS

    for dimension in CANONICAL_DIMENSIONS:
        # Money is the one dimension with no physical kind: `currency` is a
        # placeholder for whichever ISO 4217 code a model states, and dollars
        # are not convertible into euros by multiplication.
        if dimension.key == "money":
            continue
        assert dimension.unit in KIND_OF_UNIT, f"{dimension.unit} has no kind on file"


# --- The tolerance -----------------------------------------------------------


@pytest.mark.parametrize(
    ("stated", "expected", "bad"),
    [
        (0.4, 0.4, False),
        (0.401, 0.4, False),
        (0.5, 0.4, True),
        (0.00004, 0.4, True),
        (0.0, 0.0, False),
    ],
)
def test_what_counts_as_disagreement(stated: float, expected: float, bad: bool) -> None:
    assert disagrees(stated, expected) is bad


# --- End to end, through the validator ---------------------------------------


def model_with(costs: dict, runtime: float = 3600.0) -> CostModel:
    return CostModel.from_mapping(
        {
            "schema_version": "2.0",
            "date_updated": "2026-10-02",
            "unit_of_work": {"name": "one request", "status": "estimated"},
            "deployment": {"provider": "on-prem", "country": "FR"},
            "assumptions": {
                "power_draw": {
                    "value": 400.0,
                    "unit": "W",
                    "status": "estimated",
                    "source_url": "https://e.invalid",
                    "retrieved_date": "2026-10-01",
                },
                "pue": {
                    "value": 1.2,
                    "unit": "ratio",
                    "status": "estimated",
                    "source_url": "https://e.invalid",
                    "retrieved_date": "2026-10-01",
                },
            },
            "scenarios": [
                {
                    "name": "default",
                    "runtime": {
                        "value": runtime,
                        "unit": "s",
                        "status": "measured",
                        "notes": "timed",
                    },
                    "costs": costs,
                }
            ],
        }
    )


def test_a_value_that_does_not_follow_from_its_inputs_is_an_error() -> None:
    # The gap this whole module exists to close: four orders of magnitude out,
    # with a perfectly correct derivation beside it.
    report = validate(
        model_with(
            {
                "energy": {
                    "value": 0.00004,
                    "unit": "kWh",
                    "status": "estimated",
                    "derived_from": ["scenarios[0].runtime", "assumptions.power_draw"],
                }
            }
        )
    )
    assert not report.ok
    assert "does not follow" in report.to_text()


def test_a_value_that_does_follow_passes() -> None:
    assert validate(
        model_with(
            {
                "energy": {
                    "value": 0.4,
                    "unit": "kWh",
                    "status": "estimated",
                    "derived_from": ["scenarios[0].runtime", "assumptions.power_draw"],
                }
            }
        )
    ).ok


def test_rounding_on_the_way_into_yaml_is_tolerated() -> None:
    assert validate(
        model_with(
            {
                "energy": {
                    "value": 0.4001,
                    "unit": "kWh",
                    "status": "estimated",
                    "derived_from": ["scenarios[0].runtime", "assumptions.power_draw"],
                }
            }
        )
    ).ok


def test_a_unit_the_inputs_cannot_produce_is_an_error() -> None:
    report = validate(
        model_with(
            {
                "carbon": {
                    "value": 1.0,
                    "unit": "gCO2e",
                    "status": "estimated",
                    "derived_from": ["scenarios[0].runtime", "assumptions.pue"],
                }
            }
        )
    )
    assert not report.ok
    assert "cannot come from" in report.to_text()


def test_a_dimension_this_does_not_know_is_left_alone() -> None:
    # A project's own dimension gets the same silence as any other unknown.
    model = model_with(
        {
            "egress": {
                "value": 12.0,
                "unit": "GB",
                "status": "estimated",
                "derived_from": ["scenarios[0].runtime"],
            }
        }
    )
    assert "does not follow" not in validate(model).to_text()


def test_every_committed_example_survives_the_check() -> None:
    # The package's own output has to pass the rule it now enforces.
    import pathlib

    import yaml

    root = pathlib.Path(__file__).resolve().parents[2] / "examples"
    for path in sorted(root.rglob("*.yaml")):
        text = validate(
            CostModel.from_mapping(yaml.safe_load(path.read_text(encoding="utf-8")))
        ).to_text()
        assert "does not follow" not in text, f"{path.name}: {text}"
        assert "cannot come from" not in text, f"{path.name}: {text}"


# --- A measured value says what measured it ----------------------------------


def test_a_bare_measured_value_is_warned_about() -> None:
    model = CostModel.from_mapping(
        {
            "schema_version": "2.0",
            "date_updated": "2026-10-02",
            "unit_of_work": {"name": "one", "status": "estimated"},
            "deployment": {"provider": "on-prem", "country": "FR"},
            "scenarios": [
                {
                    "name": "s",
                    "runtime": {"value": 1.0, "unit": "s", "status": "measured"},
                    "costs": {},
                }
            ],
        }
    )
    assert "what measured it" in validate(model).to_text()


def test_a_note_is_enough_to_say_what_measured_it() -> None:
    model = CostModel.from_mapping(
        {
            "schema_version": "2.0",
            "date_updated": "2026-10-02",
            "unit_of_work": {"name": "one", "status": "estimated"},
            "deployment": {"provider": "on-prem", "country": "FR"},
            "scenarios": [
                {
                    "name": "s",
                    "runtime": {
                        "value": 1.0,
                        "unit": "s",
                        "status": "measured",
                        "notes": "wall clock around `python train.py`",
                    },
                    "costs": {},
                }
            ],
        }
    )
    assert "what measured it" not in validate(model).to_text()


def test_a_measurement_block_vouches_for_the_whole_model() -> None:
    model = CostModel.from_mapping(
        {
            "schema_version": "2.0",
            "date_updated": "2026-10-02",
            "unit_of_work": {"name": "one", "status": "estimated"},
            "deployment": {"provider": "on-prem", "country": "FR"},
            "measurement": {"command": ["python", "train.py"], "power_scope": "processor package"},
            "scenarios": [
                {
                    "name": "s",
                    "runtime": {"value": 1.0, "unit": "s", "status": "measured"},
                    "costs": {},
                }
            ],
        }
    )
    assert "what measured it" not in validate(model).to_text()


def test_an_unattributed_measurement_is_a_warning_and_not_a_failure() -> None:
    # Somebody may genuinely have measured this with their own wattmeter.
    # Refusing their model would be refusing the truth.
    model = CostModel.from_mapping(
        {
            "schema_version": "2.0",
            "date_updated": "2026-10-02",
            "unit_of_work": {"name": "one", "status": "estimated"},
            "deployment": {"provider": "on-prem", "country": "FR"},
            "scenarios": [
                {
                    "name": "s",
                    "runtime": {"value": 1.0, "unit": "s", "status": "measured"},
                    "costs": {},
                }
            ],
        }
    )
    assert validate(model).ok
