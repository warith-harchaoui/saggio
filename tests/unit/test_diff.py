"""Drift: what changed, and which changes fail the gate."""

from __future__ import annotations

from typing import Any

import pytest

from saggio.diff import compare


def model(value: float | None, status: str = "measured", key: str = "energy") -> dict[str, Any]:
    return {
        "scenarios": [
            {"name": "default", "costs": {key: {"value": value, "status": status, "unit": "kWh"}}}
        ]
    }


def test_an_unchanged_model_has_no_changes() -> None:
    comparison = compare(model(1.0), model(1.0))
    assert comparison.changes == []
    assert comparison.passes()


def test_a_number_that_moved_is_reported_as_a_percentage() -> None:
    change = compare(model(1.0), model(1.5)).changes[0]
    assert change.percent_change == pytest.approx(50.0)
    assert change.worse


def test_a_cost_going_down_is_not_worse() -> None:
    change = compare(model(2.0), model(1.0)).changes[0]
    assert change.percent_change == pytest.approx(-50.0)
    assert not change.worse


def test_a_small_move_clears_the_gate() -> None:
    assert compare(model(1.0), model(1.05)).passes()


def test_a_large_move_fails_the_gate() -> None:
    assert not compare(model(1.0), model(1.5)).passes()


def test_the_gate_is_adjustable() -> None:
    assert compare(model(1.0), model(1.5), threshold_percent=60.0).passes()


def test_a_weakened_status_fails_even_when_the_number_did_not_move() -> None:
    # The model now knows less than it did, which is a regression whatever the
    # number says.
    comparison = compare(model(1.0, "measured"), model(1.0, "estimated"))
    assert not comparison.passes()
    assert comparison.changes[0].status_changed()


def test_a_strengthened_status_is_not_a_failure() -> None:
    assert compare(model(1.0, "estimated"), model(1.0, "measured")).passes()


def test_a_quantity_that_disappeared_fails() -> None:
    # The usual way a cost stops being reported is that somebody deleted the field.
    comparison = compare(model(1.0), {"scenarios": [{"name": "default", "costs": {}}]})
    assert not comparison.passes()
    assert comparison.changes[0].disappeared()


def test_a_new_quantity_is_news_not_a_failure() -> None:
    comparison = compare({"scenarios": [{"name": "default", "costs": {}}]}, model(1.0))
    assert comparison.passes()
    assert comparison.changes[0].appeared()


def test_direction_is_read_from_the_dimension_registry() -> None:
    before = {
        "dimensions": [
            {
                "key": "throughput",
                "unit": "req/s",
                "description": "More is better.",
                "higher_is_worse": False,
            }
        ],
        "scenarios": [
            {"name": "d", "costs": {"throughput": {"value": 100.0, "status": "measured"}}}
        ],
    }
    after = {
        **before,
        "scenarios": [
            {"name": "d", "costs": {"throughput": {"value": 50.0, "status": "measured"}}}
        ],
    }
    comparison = compare(before, after)
    assert comparison.changes[0].worse
    assert not comparison.passes()


def test_an_assumption_changing_is_news_not_a_regression() -> None:
    before = {"assumptions": {"pue": {"value": 1.2, "status": "estimated"}}, "scenarios": []}
    after = {"assumptions": {"pue": {"value": 1.5, "status": "estimated"}}, "scenarios": []}
    comparison = compare(before, after)
    assert not comparison.changes[0].worse
    assert comparison.passes()


def test_a_move_from_zero_has_no_percentage() -> None:
    assert compare(model(0.0), model(1.0)).changes[0].percent_change is None


def test_a_move_to_or_from_nothing_has_no_percentage() -> None:
    assert compare(model(None, "TODO"), model(1.0)).changes[0].percent_change is None


def test_the_comparison_renders_as_a_verdict() -> None:
    report = compare(model(1.0), model(5.0)).to_report()
    assert not report.ok
    assert "energy" in report.to_text()


def test_the_comparison_serialises_for_another_tool() -> None:
    payload = compare(model(1.0), model(1.5)).to_mapping()
    assert payload["passes"] is False
    assert payload["changes"][0]["percent_change"] == pytest.approx(50.0)


def test_a_change_describes_itself_in_one_line() -> None:
    described = compare(model(1.0), model(2.0)).changes[0].describe()
    assert "1 -> 2" in described
    assert "+100.0%" in described
