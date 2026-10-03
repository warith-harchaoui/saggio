"""Checking that a derived number follows from the numbers it names."""

from __future__ import annotations

import pytest

from saggio.model import CostModel, validate
from saggio.model.derivation import (
    candidates,
    combine,
    disagrees,
    parse_unit,
    unreachable,
)

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


def test_every_unit_the_canonical_dimensions_use_parses() -> None:
    from saggio.model.dimensions import CANONICAL_DIMENSIONS

    for dimension in CANONICAL_DIMENSIONS:
        # Money is the one dimension with no physical base: `currency` is a
        # placeholder for whichever ISO 4217 code a model states, and dollars
        # are not convertible into euros by multiplication.
        if dimension.key == "money":
            continue
        assert parse_unit(dimension.unit) is not None, (
            f"{dimension.unit} is a unit the package emits but cannot parse"
        )


def test_an_intensity_keeps_its_denominator() -> None:
    # The bug that made the first version of this module useless: unary plus on
    # a Counter drops non-positive entries, so `gCO2e/kWh` parsed as a mass and
    # compared equal to one. An intensity that has lost its denominator cannot
    # catch anything.
    parsed = parse_unit("gCO2e/kWh")
    assert parsed is not None
    _, dimensions = parsed
    assert dimensions["J"] == -1
    assert dimensions["gCO2e"] == 1


def test_a_watt_is_a_joule_per_second() -> None:
    # Which is why seconds times watts come out as energy with no special case
    # for that pair anywhere in the module.
    parsed = parse_unit("W")
    assert parsed is not None
    _, dimensions = parsed
    assert dict(dimensions) == {"J": 1, "s": -1}


def test_a_scale_is_folded_in_so_prefixes_cannot_be_mixed_up() -> None:
    assert combine([(1.0, "kWh")], "Wh") == pytest.approx(1000.0)
    assert combine([(3600.0, "s")], "h") == pytest.approx(1.0)
    assert combine([(1.0, "kgCO2e")], "gCO2e") == pytest.approx(1000.0)


# --- More than two inputs ----------------------------------------------------


def test_the_product_is_the_reading_when_it_lands_on_the_unit() -> None:
    # Without this, every dimensionless input would be ambiguous — energy times
    # an overhead could as well be energy divided by it — and the commonest
    # derivation in the package would stop being checked exactly.
    assert combine([(0.4, "kWh"), (1.2, "ratio")], "kWh") == pytest.approx(0.48)
    assert combine([(0.4, "kWh"), (1.2, "ratio"), (1.1, "ratio")], "kWh") == pytest.approx(0.528)


def test_amortising_over_a_lifetime_gives_both_readings() -> None:
    # An hour out of a four-year life divides, but nothing in `years` says so
    # rather than multiplying, so the units offer both and neither is guessed.
    values = candidates([(164.0, "kgCO2e"), (4.0, "years"), (1.0, "h")], "gCO2e")
    assert values is not None
    assert len(values) == 2
    assert min(values) == pytest.approx(4.677, abs=1e-3)


def test_a_three_input_value_matching_no_reading_is_still_wrong() -> None:
    # The hole that survived the first fix: a three-input derivation went
    # unchecked, so an embodied figure five orders of magnitude out passed with
    # a perfectly correct list of inputs beside it.
    values = candidates([(164.0, "kgCO2e"), (4.0, "years"), (1.0, "h")], "gCO2e")
    assert values is not None
    assert all(disagrees(1_000_000.0, value) for value in values)


def test_an_impossible_unit_is_caught_however_many_inputs_there_are() -> None:
    # Ruling a unit out needs only the dimensions, so it stays decidable where
    # recomputing the value does not.
    assert unreachable([(1.0, "kWh"), (100.0, "W")], "gCO2e") is not None
    assert unreachable([(1.0, "s"), (1.2, "ratio"), (4.0, "years")], "gCO2e") is not None
    assert candidates([(1.0, "kWh"), (100.0, "W")], "gCO2e") == []


def test_one_unknown_unit_silences_the_whole_comparison() -> None:
    # Asserting an impossibility about somebody else's dimension would be
    # inventing exactly the kind of rule this package exists to refuse.
    assert candidates([(1.0, "kWh"), (3.0, "sheep")], "gCO2e") is None
    assert unreachable([(1.0, "kWh"), (3.0, "sheep")], "gCO2e") is None


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
    # A project's own dimension gets silence. `tokens` is not a unit the module
    # knows, and inventing a relationship for it would be the one thing this
    # package refuses to do.
    model = model_with(
        {
            "tokens": {
                "value": 12.0,
                "unit": "tokens",
                "status": "estimated",
                "derived_from": ["scenarios[0].runtime"],
            }
        }
    )
    text = validate(model).to_text()
    assert "does not follow" not in text
    assert "cannot come from" not in text


def test_bytes_cannot_come_from_a_duration() -> None:
    # Data is a dimension the module does know, and a runtime cannot produce
    # it, so claiming otherwise is caught rather than waved through.
    report = validate(
        model_with(
            {
                "egress": {
                    "value": 12.0,
                    "unit": "GB",
                    "status": "estimated",
                    "derived_from": ["scenarios[0].runtime"],
                }
            }
        )
    )
    assert not report.ok
    assert "cannot come from" in report.to_text()


def test_an_embodied_figure_orders_of_magnitude_out_is_caught() -> None:
    # Three inputs, through the validator, which is where the hole actually was.
    model = CostModel.from_mapping(
        {
            "schema_version": "2.0",
            "date_updated": "2026-10-02",
            "unit_of_work": {"name": "one hour", "status": "estimated"},
            "deployment": {"provider": "on-prem", "country": "FR"},
            "assumptions": {
                "embodied": {
                    "value": 164.0,
                    "unit": "kgCO2e",
                    "status": "estimated",
                    "source_url": "https://e.invalid",
                    "retrieved_date": "2026-10-01",
                },
                "lifetime": {
                    "value": 4.0,
                    "unit": "years",
                    "status": "estimated",
                    "source_url": "https://e.invalid",
                    "retrieved_date": "2026-10-01",
                },
            },
            "scenarios": [
                {
                    "name": "default",
                    "runtime": {
                        "value": 3600.0,
                        "unit": "s",
                        "status": "measured",
                        "notes": "timed",
                    },
                    "costs": {
                        "embodied_carbon": {
                            "value": 1_000_000.0,
                            "unit": "gCO2e",
                            "status": "estimated",
                            "derived_from": [
                                "assumptions.embodied",
                                "assumptions.lifetime",
                                "scenarios[0].runtime",
                            ],
                        }
                    },
                }
            ],
        }
    )
    report = validate(model)
    assert not report.ok
    assert "does not follow" in report.to_text()


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


def test_a_measurement_block_vouches_only_for_what_a_run_observes() -> None:
    # The quieter half of the same mistake: a carbon figure marked `measured`,
    # with nothing in the world that could have measured it, inheriting the
    # standing of a stopwatch because the file happened to contain one.
    model = CostModel.from_mapping(
        {
            "schema_version": "2.0",
            "date_updated": "2026-10-02",
            "unit_of_work": {"name": "one request", "status": "estimated"},
            "deployment": {"provider": "on-prem", "country": "FR"},
            "measurement": {"command": ["python", "train.py"], "exit_code": 0},
            "scenarios": [
                {
                    "name": "default",
                    "costs": {
                        "runtime": {"value": 1.0, "unit": "s", "status": "measured"},
                        "energy": {"value": 1.0, "unit": "kWh", "status": "measured"},
                        "carbon": {"value": 1.0, "unit": "gCO2e", "status": "measured"},
                    },
                }
            ],
        }
    )
    text = validate(model).to_text()
    assert "does not observe" in text
    # And it says so about the carbon alone, not about the two the run did see.
    assert text.count("does not observe") == 1
    assert "gCO2e" in text


def test_money_read_off_an_invoice_is_attributed_by_its_note() -> None:
    # A cost genuinely can be measured — off a bill. The rule asks it to say so,
    # not to stop claiming it.
    model = CostModel.from_mapping(
        {
            "schema_version": "2.0",
            "date_updated": "2026-10-02",
            "unit_of_work": {"name": "one request", "status": "estimated"},
            "deployment": {"provider": "aws", "country": "FR"},
            "measurement": {"command": ["python", "train.py"], "exit_code": 0},
            "scenarios": [
                {
                    "name": "default",
                    "costs": {
                        "spend": {
                            "value": 12.4,
                            "unit": "USD",
                            "status": "measured",
                            "notes": "read off the November invoice",
                        }
                    },
                }
            ],
        }
    )
    assert "does not observe" not in validate(model).to_text()


def test_an_unknown_unit_gets_the_benefit_of_the_doubt() -> None:
    # Asserting that somebody's instrument cannot exist would be inventing a
    # rule about their field, which is the mistake this package is built against.
    from saggio.model.validate import _a_run_can_observe

    assert _a_run_can_observe("sheep") is True
    assert _a_run_can_observe("gCO2e") is False


# --- A derivation that goes round in a circle ---------------------------------


def grounded(*references: str) -> dict:
    """Return a quantity, derived from these or sourced when given none."""
    body: dict = {"value": 1.0, "unit": "s", "status": "estimated"}
    if references:
        body["derived_from"] = [f"assumptions.{name}" for name in references]
    else:
        body |= {"source_url": "https://example.invalid", "retrieved_date": "2026-10-01"}
    return body


def model_with_assumptions(assumptions: dict) -> CostModel:
    """Return a model complete enough to validate, with these assumptions."""
    return CostModel.from_mapping(
        {
            "schema_version": "2.1",
            "date_updated": "2026-10-03",
            "unit_of_work": {"name": "one request", "status": "estimated"},
            "deployment": {"provider": "on-prem", "country": "FR"},
            "assumptions": assumptions,
            "scenarios": [
                {
                    "name": "default",
                    "costs": {
                        "time": {"value": 1.0, "unit": "s", "status": "measured", "notes": "t"}
                    },
                }
            ],
        }
    )


def goes_in_a_circle(assumptions: dict) -> bool:
    """Return whether the validator reports a circle in these assumptions."""
    return "circle" in validate(model_with_assumptions(assumptions)).to_text()


@pytest.mark.parametrize(
    ("name", "assumptions"),
    [
        ("two steps", {"a": grounded("b"), "b": grounded("a")}),
        ("three steps", {"a": grounded("b"), "b": grounded("c"), "c": grounded("a")}),
        (
            "five steps",
            {
                "a": grounded("b"),
                "b": grounded("c"),
                "c": grounded("d"),
                "d": grounded("e"),
                "e": grounded("a"),
            },
        ),
        (
            "reached from outside it",
            {"root": grounded("a"), "a": grounded("b"), "b": grounded("a")},
        ),
        (
            "two separate circles",
            {"a": grounded("b"), "b": grounded("a"), "c": grounded("d"), "d": grounded("c")},
        ),
    ],
)
def test_a_derivation_that_goes_in_a_circle_is_reported(name: str, assumptions: dict) -> None:
    """The weakest-link rule assumes a chain can be walked back to a fact.

    A circle has no bottom: every value in it is founded on another value in it,
    so none of them rests on anything measured or sourced. The package would
    compute a status out of nothing and state it as confidently as the rest of
    the page.

    Direct self-reference was already caught, one quantity at a time. A circle
    through an intermediate is invisible from there -- each row names an input
    that exists, carries a plausible status, and resolves -- and only shows when
    the whole graph is laid out.
    """
    assert goes_in_a_circle(assumptions), f"a circle of {name} was not reported"


@pytest.mark.parametrize(
    ("name", "assumptions"),
    [
        (
            "a diamond",
            {
                "top": grounded("left", "right"),
                "left": grounded("base"),
                "right": grounded("base"),
                "base": grounded(),
            },
        ),
        (
            "a long honest chain",
            {"a": grounded("b"), "b": grounded("c"), "c": grounded("d"), "d": grounded()},
        ),
        ("one input named twice", {"a": grounded("b", "b"), "b": grounded()}),
    ],
)
def test_a_graph_that_merely_rejoins_itself_is_not_a_circle(name: str, assumptions: dict) -> None:
    """Two paths to the same fact is ordinary, and must not be called a circle.

    A depth-first walk that marked a node visited rather than *being visited*
    would report every diamond, and a model that states one assumption twice is
    the commonest shape there is.
    """
    assert not goes_in_a_circle(assumptions), f"{name} was reported as a circle"


def test_the_circle_is_named_in_the_order_a_reader_would_follow_it() -> None:
    """An unordered set of names leaves the reader to work out the direction."""
    text = validate(
        model_with_assumptions({"a": grounded("b"), "b": grounded("c"), "c": grounded("a")})
    ).to_text()
    assert "assumptions.a -> assumptions.b -> assumptions.c -> assumptions.a" in text
