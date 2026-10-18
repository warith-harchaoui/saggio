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


# --- Provenance --------------------------------------------------------------


def test_a_price_that_fell_back_to_an_aggregator_fails_the_gate() -> None:
    # Same number, same status: only the distance to whoever sets it changed,
    # and that is a regression the gate has to see.
    earlier = {"p": {"value": 3e-06, "status": "estimated", "source_kind": "first-party"}}
    later = {"p": {"value": 3e-06, "status": "estimated", "source_kind": "aggregator"}}
    comparison = compare(earlier, later)
    assert not comparison.passes()
    assert "first-party -> aggregator" in comparison.changes[0].describe()


def test_a_price_a_human_took_over_does_not_fail_the_gate() -> None:
    earlier = {"p": {"value": 3e-06, "status": "estimated", "source_kind": "aggregator"}}
    later = {"p": {"value": 3e-06, "status": "measured", "source_kind": "stated"}}
    assert compare(earlier, later).passes()


def test_a_quantity_that_never_declared_a_source_kind_has_not_weakened() -> None:
    earlier = {"p": {"value": 1.0, "status": "estimated"}}
    later = {"p": {"value": 1.0, "status": "estimated", "notes": "same number"}}
    assert compare(earlier, later).passes()


# --- Holes the third audit found, kept closed -----------------------------------


def test_a_currency_switch_fails_the_gate_even_at_the_same_number() -> None:
    # 10 USD -> 10 EUR is not "no change"; it is the drift the gate exists for.
    before = {
        "scenarios": [
            {
                "name": "s",
                "costs": {"money": {"value": 10.0, "currency": "USD", "status": "measured"}},
            }
        ]
    }
    after = {
        "scenarios": [
            {
                "name": "s",
                "costs": {"money": {"value": 10.0, "currency": "EUR", "status": "measured"}},
            }
        ]
    }
    comparison = compare(before, after)
    assert not comparison.passes()
    assert any("not the same money" in change.describe() for change in comparison.changes)


def test_a_unit_switch_is_named_not_compared_numerically() -> None:
    before = {
        "scenarios": [
            {"name": "s", "costs": {"energy": {"value": 1.0, "unit": "kWh", "status": "measured"}}}
        ]
    }
    after = {
        "scenarios": [
            {
                "name": "s",
                "costs": {"energy": {"value": 1000.0, "unit": "Wh", "status": "measured"}},
            }
        ]
    }
    comparison = compare(before, after)
    change = next(c for c in comparison.changes if "energy" in c.path)
    assert change.percent_change is None
    assert change.worse
    assert "not comparable" in change.describe()


# --- The gate reads the noise the models measured ----------------------------

#: Two models of the same work, each measured five times. The power moved by a
#: factor of two between them — and each one's own measurement says it moves
#: that much between runs.
def _repeated(power: float, low: float, high: float) -> dict:
    return {
        "schema_version": "2.1",
        "measurement": {
            "repeats": 5,
            "spread": {"power_w": {"low": low, "median": (low + high) / 2, "high": high}},
        },
        "assumptions": {"power_draw": {"value": power, "unit": "W", "status": "measured"}},
        "scenarios": [
            {
                "name": "as-audited",
                "costs": {
                    "carbon": {
                        "value": power,
                        "unit": "gCO2e",
                        "status": "estimated",
                        "derived_from": ["assumptions.power_draw"],
                    }
                },
            }
        ],
    }


def test_a_movement_inside_both_measured_ranges_does_not_fail_the_gate() -> None:
    # The defect: the gate fired on every re-measurement of unchanged code and
    # could not tell a regression from a noisy neighbour.
    comparison = compare(_repeated(17.0, 16.0, 37.0), _repeated(35.0, 30.0, 40.0))
    carbon = next(c for c in comparison.changes if c.path.endswith("costs.carbon"))
    assert carbon.percent_change is not None and carbon.percent_change > 100.0
    assert carbon.within_noise()
    assert comparison.passes()
    assert len(comparison.excused()) == 1


def test_a_movement_outside_the_measured_ranges_still_fails() -> None:
    # The sabotage. Same noise, a real regression on top of it.
    comparison = compare(_repeated(17.0, 16.0, 18.0), _repeated(35.0, 34.0, 36.0))
    assert not comparison.passes()
    assert comparison.excused() == []


def test_an_excused_movement_is_reported_with_the_band_that_excused_it() -> None:
    # Excused visibly. A release waved through by a hundred-per-cent band
    # should show the reader the band.
    comparison = compare(_repeated(17.0, 16.0, 37.0), _repeated(35.0, 30.0, 40.0))
    carbon = next(c for c in comparison.changes if c.path.endswith("costs.carbon"))
    spoken = carbon.describe(threshold_percent=comparison.threshold_percent)
    assert "inside the noise both models measured" in spoken
    assert "16 to 37" in spoken and "30 to 40" in spoken


def test_a_small_movement_does_not_mention_noise_nobody_was_worried_about() -> None:
    comparison = compare(_repeated(17.0, 16.0, 37.0), _repeated(17.5, 16.0, 37.0))
    carbon = next(c for c in comparison.changes if c.path.endswith("costs.carbon"))
    assert "inside the noise" not in carbon.describe(threshold_percent=10.0)


def test_one_side_repeated_and_the_other_not_still_answers() -> None:
    # The older model was measured once. The question becomes whether its
    # number falls inside the range the repeated one actually saw.
    once = _repeated(20.0, 0.0, 0.0)
    del once["measurement"]
    comparison = compare(once, _repeated(35.0, 18.0, 40.0))
    carbon = next(c for c in comparison.changes if c.path.endswith("costs.carbon"))
    assert carbon.within_noise()
    assert "inside the noise the later model measured" in carbon.describe(threshold_percent=10.0)


def test_two_models_that_repeated_nothing_are_gated_exactly_as_before() -> None:
    before, after = _repeated(10.0, 0.0, 0.0), _repeated(30.0, 0.0, 0.0)
    del before["measurement"], after["measurement"]
    comparison = compare(before, after)
    carbon = next(c for c in comparison.changes if c.path.endswith("costs.carbon"))
    assert not carbon.within_noise()
    assert not comparison.passes()


def test_noise_never_excuses_a_weakened_status() -> None:
    # The bands only ever excuse the threshold. A measurement turning back into
    # a TODO is a different breach and stays one.
    before = _repeated(17.0, 16.0, 37.0)
    after = _repeated(35.0, 30.0, 40.0)
    after["assumptions"]["power_draw"]["status"] = "TODO"
    assert not compare(before, after).passes()


def test_the_json_surface_carries_the_bands_it_judged_on() -> None:
    payload = compare(_repeated(17.0, 16.0, 37.0), _repeated(35.0, 30.0, 40.0)).to_mapping()
    assert payload["excused_by_noise"] == 1
    carbon = next(c for c in payload["changes"] if c["path"].endswith("costs.carbon"))
    assert carbon["within_noise"] is True
    assert carbon["noise_before"]["low"] == 16.0
    assert carbon["noise_after"]["high"] == 40.0
