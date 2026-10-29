"""The interval: what a quantity says when it will not say a single number.

A status ranks how well *founded* a number is. Nothing until now said how
precisely it is *known*, and the two are independent: a figure can be
impeccably sourced and still only pin the answer down within a factor of three.
These tests cover the interval, the rules that make it mean something, and the
rule that matters most -- that a derived value may not be narrower than the
numbers it came from, which is the weakest-link rule applied to precision.
"""

from __future__ import annotations

import pytest

from saggio.model.quantity import Quantity
from saggio.model.results import Report
from saggio.model.validate import _check_bracket, _check_inherited_bracket, _check_quality


def _say(check, path: str, *args) -> str:
    report = Report()
    check(path, *args, report)
    return report.to_text()


# --------------------------------------------------------------------------- #
# the shape of an interval
# --------------------------------------------------------------------------- #
def test_a_point_is_not_an_interval() -> None:
    assert Quantity(value=1.0).bracket() is None
    assert not Quantity(value=1.0).is_bracketed()


def test_half_an_interval_is_refused() -> None:
    """The side that is missing is the side a reader worries about."""
    said = _say(_check_bracket, "e", Quantity(value=1.0, low=0.5, status="estimated"))
    assert "half an interval" in said or "no high one" in said


def test_an_inverted_interval_is_refused() -> None:
    said = _say(_check_bracket, "e", Quantity(value=1.0, low=2.0, high=0.5, status="estimated"))
    assert "backwards" in said


def test_a_value_outside_its_own_interval_is_refused() -> None:
    said = _say(_check_bracket, "e", Quantity(value=9.0, low=1.0, high=2.0, status="estimated"))
    assert "outside the interval" in said


def test_a_todo_may_not_carry_an_interval() -> None:
    """A TODO holds a field open. An interval is already an answer."""
    said = _say(_check_bracket, "e", Quantity(low=1.0, high=2.0, status="TODO"))
    assert "holds a field open" in said


def test_a_negative_end_is_refused() -> None:
    said = _say(_check_bracket, "e", Quantity(value=1.0, low=-1.0, high=2.0, status="estimated"))
    assert "cannot be negative" in said


def test_a_well_formed_interval_passes() -> None:
    good = Quantity(value=1.0, low=0.5, high=2.0, status="estimated")
    assert _say(_check_bracket, "e", good) == ""


def test_the_span_is_a_ratio() -> None:
    """A ratio, because two dimensions cannot be subtracted from each other."""
    assert Quantity(value=1.0, low=0.5, high=2.0).spans() == 4.0
    assert Quantity(value=1.0, low=0.0, high=2.0).spans() is None


def test_an_interval_survives_a_round_trip() -> None:
    mapping = {"value": 1.0, "unit": "kWh", "status": "estimated", "low": 0.8, "high": 1.3}
    assert Quantity.from_mapping(mapping).to_mapping() == mapping


# --------------------------------------------------------------------------- #
# the rule that matters: precision cannot be invented downstream
# --------------------------------------------------------------------------- #
_RUNTIME = {"value": 3600.0, "unit": "s"}
_POWER = {"value": 400.0, "unit": "W", "low": 200.0, "high": 800.0}


def test_a_derived_point_from_a_bracketed_input_is_refused() -> None:
    """The hole this closes.

    Energy from a runtime and a power known only within a factor of two is not
    a single confident number, and before this nothing said so: the status rule
    passed it, and so did the arithmetic rule, because the stated value really
    is runtime times the mid power.
    """
    energy = Quantity(
        value=1440000.0, unit="J", status="estimated", derived_from=("runtime", "power")
    )
    said = _say(_check_inherited_bracket, "energy", energy, [_RUNTIME, _POWER])
    assert "more precisely" in said
    assert "'power'" in said


def test_the_interval_the_inputs_force_is_accepted() -> None:
    energy = Quantity(
        value=1440000.0,
        unit="J",
        status="estimated",
        low=720000.0,
        high=2880000.0,
        derived_from=("runtime", "power"),
    )
    assert _say(_check_inherited_bracket, "energy", energy, [_RUNTIME, _POWER]) == ""


def test_a_narrower_interval_than_the_inputs_force_is_refused() -> None:
    energy = Quantity(
        value=1440000.0,
        unit="J",
        status="estimated",
        low=1400000.0,
        high=1500000.0,
        derived_from=("runtime", "power"),
    )
    said = _say(_check_inherited_bracket, "energy", energy, [_RUNTIME, _POWER])
    assert "does not follow" in said


def test_a_wider_interval_is_a_choice_and_not_a_fault() -> None:
    """Widening is modelling judgement. Narrowing is a claim nobody earned."""
    energy = Quantity(
        value=1440000.0,
        unit="J",
        status="estimated",
        low=100000.0,
        high=9000000.0,
        derived_from=("runtime", "power"),
    )
    assert _say(_check_inherited_bracket, "energy", energy, [_RUNTIME, _POWER]) == ""


def test_an_unknown_unit_still_has_to_carry_an_interval() -> None:
    """Where the house rule about unknown dimensions does and does not apply.

    Everywhere else, a unit this package does not know buys silence: inventing
    an arithmetic rule for somebody else's dimension is the thing it refuses.
    Here the two halves of the rule part company. *That* a derived value must
    carry an interval when an input carries one needs no units at all -- a
    number computed from something known within a factor of four is not known
    better than that, whatever it measures. Only the *width* needs the units,
    and that half does stay silent.
    """
    odd = Quantity(value=5.0, unit="glorps", status="estimated", derived_from=("runtime", "power"))
    assert "more precisely" in _say(_check_inherited_bracket, "x", odd, [_RUNTIME, _POWER])


def test_an_unknown_unit_is_not_second_guessed_on_the_width() -> None:
    """Any interval at all is accepted when the units cannot say which is right."""
    odd = Quantity(
        value=5.0,
        unit="glorps",
        status="estimated",
        low=4.0,
        high=6.0,
        derived_from=("runtime", "power"),
    )
    assert _say(_check_inherited_bracket, "x", odd, [_RUNTIME, _POWER]) == ""


# --------------------------------------------------------------------------- #
# the pedigree block
# --------------------------------------------------------------------------- #
_GOOD_SCORES = {
    "reliability": 2,
    "completeness": 3,
    "temporal": 3,
    "geographical": 1,
    "technological": 3,
}


def test_a_quality_block_without_a_basic_uncertainty_produces_nothing() -> None:
    """And that is a warning, not an error: an open field is a correct answer."""
    said = _say(
        _check_quality, "e", Quantity(value=1.0, status="estimated", quality=dict(_GOOD_SCORES))
    )
    assert "WARNING" in said
    assert "no interval follows" in said


def test_a_blank_cell_of_the_matrix_is_refused() -> None:
    scored = {**_GOOD_SCORES, "geographical": 4}
    said = _say(_check_quality, "e", Quantity(value=1.0, status="estimated", quality=scored))
    assert "leaves that cell blank" in said


def test_a_partial_reading_is_refused() -> None:
    """Four indicators out of five would understate the spread."""
    said = _say(
        _check_quality,
        "e",
        Quantity(value=1.0, status="estimated", quality={"reliability": 2}),
    )
    assert "not completeness" in said or "completeness" in said


def test_the_scores_must_produce_the_stated_interval() -> None:
    scored = {**_GOOD_SCORES, "basic_uncertainty": 1.05}
    wrong = Quantity(value=1.0, status="estimated", low=0.99, high=1.01, quality=scored)
    said = _say(_check_quality, "e", wrong)
    assert "has to be the one the scores produce" in said


def test_a_quality_block_with_no_interval_is_told_which_one_to_write() -> None:
    scored = {**_GOOD_SCORES, "basic_uncertainty": 1.05}
    said = _say(_check_quality, "e", Quantity(value=1.0, status="estimated", quality=scored))
    assert "0.800" in said and "1.24" in said


def test_the_interval_the_scores_give_is_accepted() -> None:
    from saggio.model import pedigree

    scored = {**_GOOD_SCORES, "basic_uncertainty": 1.05}
    deviation = pedigree.spread(pedigree.Scores(2, 3, 3, 1, 3), basic_uncertainty=1.05)
    low, high = pedigree.interval(1.0, deviation)
    good = Quantity(value=1.0, status="estimated", low=low, high=high, quality=scored)
    assert _say(_check_quality, "e", good) == ""


def test_an_indicator_the_matrix_does_not_define_is_refused() -> None:
    scored = {**_GOOD_SCORES, "charisma": 1, "basic_uncertainty": 1.05}
    said = _say(_check_quality, "e", Quantity(value=1.0, status="estimated", quality=scored))
    assert "which the pedigree matrix does not define" in said


@pytest.mark.parametrize("score", [0, 6, 2.5, "two", True])
def test_a_score_outside_the_matrix_is_refused(score: object) -> None:
    scored = {**_GOOD_SCORES, "reliability": score, "basic_uncertainty": 1.05}
    said = _say(_check_quality, "e", Quantity(value=1.0, status="estimated", quality=scored))
    assert said != ""
