"""Repeating a measurement, because one run bounds nothing.

The finding these exist for: `examples/render.yaml` was measured twice on one
machine with no change to the measured code, and the runtime moved 2.3% while
everything derived from the power moved 76.6%. Both carried the word
`measured`.
"""

from __future__ import annotations

import sys

import pytest

from saggio.analyze.power import PowerReading, measurement_rows
from saggio.analyze.repeat import (
    MEASURED_ONCE,
    WIDE_SPREAD,
    SliceSeries,
    Spread,
    run_slices,
    spread_note,
)
from saggio.analyze.run import SliceResult


def _run(seconds: float, watts: float | None = None) -> SliceResult:
    reading = PowerReading(watts, watts, "soc" if watts is not None else "")
    return SliceResult(("x",), 0, seconds, reading)


# --- What a spread says ------------------------------------------------------


def test_the_spread_is_the_range_over_the_median() -> None:
    spread = Spread((1.0, 2.0, 3.0))
    assert (spread.low, spread.median, spread.high) == (1.0, 2.0, 3.0)
    assert spread.relative == 1.0


def test_a_median_of_zero_yields_no_proportion_rather_than_a_crash() -> None:
    # A proportion of nothing is not a proportion, and a ZeroDivisionError in
    # the middle of writing a model to disk is the worst place to find out.
    assert Spread((0.0, 0.0)).relative is None
    assert not Spread((0.0, 0.0)).wide()


def test_the_gate_is_the_one_diff_applies() -> None:
    # Deliberately the same threshold: a figure that moves this much between
    # two runs of unchanged code would fail `saggio diff` on a release.
    assert WIDE_SPREAD == 0.10
    assert Spread((1.0, 1.11)).wide()
    assert not Spread((1.0, 1.09)).wide()


# --- Which run the model carries --------------------------------------------


def test_the_model_carries_one_real_run_and_not_a_median_per_field() -> None:
    # A model's energy is its runtime times its power. Medians taken from
    # different runs would state a pair that never occurred together.
    runs = (_run(3.0, 30.0), _run(1.0, 10.0), _run(2.0, 99.0))
    chosen = SliceSeries(runs).representative()
    assert (chosen.wall_seconds, chosen.power.watts) == (2.0, 99.0)


def test_an_even_number_of_runs_picks_deterministically() -> None:
    runs = (_run(4.0), _run(1.0), _run(3.0), _run(2.0))
    assert SliceSeries(runs).representative().wall_seconds == 2.0


# --- What the block records --------------------------------------------------


def test_one_run_records_no_spread_at_all() -> None:
    # Nothing changes for a caller who did not ask for repeats.
    block = SliceSeries((_run(1.0, 10.0),)).to_mapping()
    assert "repeats" not in block
    assert "spread" not in block


def test_several_runs_record_the_range_and_the_runs_it_came_from() -> None:
    block = SliceSeries((_run(1.0, 10.0), _run(2.0, 20.0), _run(3.0, 30.0))).to_mapping()
    assert block["repeats"] == 3
    assert block["spread"]["runtime_s"]["low"] == 1.0
    assert block["spread"]["power_w"]["high"] == 30.0
    assert block["spread"]["power_w"]["runs"] == [10.0, 20.0, 30.0]


def test_a_power_spread_is_withheld_unless_every_run_measured_power() -> None:
    # A spread over the runs that answered covers a different population from
    # the runtime's, and printing the two side by side would invite a
    # comparison that was never about the same runs.
    series = SliceSeries((_run(1.0, 10.0), _run(2.0, None)))
    assert series.power_spread() is None
    assert "power_w" not in series.to_mapping()["spread"]


def test_a_wide_spread_warns_with_the_range_in_it() -> None:
    warnings = SliceSeries((_run(1.0, 16.0), _run(1.01, 21.0))).warnings()
    assert len(warnings) == 1, "the runtime moved 1%, the power 31%"
    assert "16" in warnings[0] and "21" in warnings[0]
    assert "saggio diff" in warnings[0]


def test_a_single_run_warns_about_nothing_because_it_knows_nothing() -> None:
    assert SliceSeries((_run(1.0, 10.0),)).warnings() == []


# --- The sentence a quantity carries -----------------------------------------


def test_a_quantity_measured_once_says_so_rather_than_saying_nothing() -> None:
    # Silence reads as stability, and this is the figure that is not stable.
    assert spread_note(None, "runtime_s") == MEASURED_ONCE
    assert spread_note({"repeats": 1}, "runtime_s") == MEASURED_ONCE
    assert "--repeat" in MEASURED_ONCE


def test_the_sentence_quotes_the_range_the_repeats_established() -> None:
    block = SliceSeries((_run(1.0, 16.0), _run(2.0, 21.0), _run(3.0, 18.0))).to_mapping()
    assert spread_note(block, "runtime_s").startswith("The median of 3 runs")
    assert "1 s to 3 s" in spread_note(block, "runtime_s")


def test_the_power_sentence_does_not_call_the_carried_figure_a_median() -> None:
    # It is not one. The run the model carries is chosen by its runtime, so the
    # power beside it is that run's power — 16 W here, while the middle power of
    # the three is 18 W. Calling it the median would be false by that gap, and
    # on the gallery's own model the gap is 17.4 W against 19.4 W.
    block = SliceSeries((_run(1.0, 16.0), _run(2.0, 21.0), _run(3.0, 18.0))).to_mapping()
    note = spread_note(block, "power_w")
    assert not note.startswith("The median")
    assert "is a different run's" in note
    assert "16 W to 21 W" in note


def test_a_malformed_spread_block_falls_back_to_the_honest_default() -> None:
    # Measurement blocks are YAML a human may have edited.
    assert spread_note({"repeats": 3, "spread": "lots"}, "runtime_s") == MEASURED_ONCE
    assert spread_note({"repeats": "three", "spread": {}}, "runtime_s") == MEASURED_ONCE


# --- The report row ----------------------------------------------------------


def test_the_spread_reaches_the_report_as_a_sentence_not_a_dict() -> None:
    # The whole point of repeating a measurement is this row. Rendering it as
    # `spread | {'runtime_s': ...}` would take the trouble and keep the answer.
    block = SliceSeries((_run(1.0, 16.0), _run(2.0, 21.0))).to_mapping()
    rows = dict(measurement_rows(block))
    assert rows["times the command was run"] == "2"
    assert "runtime 1 s to 2 s" in rows["how far the figures moved across those runs"]


# --- Running it for real -----------------------------------------------------


def test_repeating_runs_the_command_that_many_times() -> None:
    series = run_slices(
        [sys.executable, "-c", "pass"], repeats=3, profile=False, baseline_seconds=0.0
    )
    assert len(series.runs) == 3
    assert all(run.exit_code == 0 for run in series.runs)


def test_a_failing_command_stops_the_series_rather_than_measuring_it_five_times() -> None:
    series = run_slices(
        [sys.executable, "-c", "raise SystemExit(3)"],
        repeats=4,
        profile=False,
        baseline_seconds=0.0,
    )
    assert len(series.runs) == 1, "measuring a failure four times measures four failures"
    assert series.runs[0].exit_code == 3


def test_asking_for_no_runs_is_refused() -> None:
    with pytest.raises(ValueError, match="cannot be run 0 times"):
        run_slices([sys.executable, "-c", "pass"], repeats=0)


def test_no_run_in_a_series_is_profiled_while_the_others_are_not() -> None:
    # The defect this closes, found by running the thing: the first run carried
    # the profiler and the rest did not, so the reported spread would have had
    # the profiler's overhead in it and nothing would have said so.
    series = run_slices(
        [sys.executable, "-c", "pass"], repeats=2, profile=True, baseline_seconds=0.0
    )
    assert all(not run.hot_path for run in series.runs)
    assert any("profiler changes what is being timed" in w for w in series.to_mapping()["warnings"])


def test_a_single_run_still_gets_its_profile() -> None:
    series = run_slices(
        [sys.executable, "-c", "pass"], repeats=1, profile=True, baseline_seconds=0.0
    )
    assert not any("profiler changes" in w for w in series.to_mapping().get("warnings", []))


# --- What a range of five is worth -------------------------------------------


def test_the_odds_the_next_run_falls_outside_are_two_over_n_plus_one() -> None:
    # Not an estimate and not a fit: among n+1 exchangeable draws from any
    # continuous distribution each is equally likely to be the largest, so the
    # new one is a fresh maximum with probability 1/(n+1), a fresh minimum with
    # the same, and it cannot be both.
    for count in (3, 5, 11, 21):
        spread = Spread(tuple(float(n) for n in range(count)))
        assert spread.outside_odds() == pytest.approx(2.0 / (count + 1))


def test_five_runs_are_exceeded_one_time_in_three() -> None:
    assert Spread((1.0, 2.0, 3.0, 4.0, 5.0)).outside_odds() == pytest.approx(1 / 3)


def test_doubling_the_runs_roughly_halves_the_odds() -> None:
    # The lever a reader has. Worth asserting because it is the reason the
    # figure is printed at all.
    five, eleven = Spread((1.0,) * 5), Spread((1.0,) * 11)
    assert five.outside_odds() / eleven.outside_odds() == pytest.approx(2.0)


def test_the_block_records_the_odds_beside_the_range() -> None:
    block = SliceSeries(tuple(_run(1.0 + n / 10, 10.0 + n) for n in range(5))).to_mapping()
    assert block["spread"]["runtime_s"]["outside_odds"] == pytest.approx(1 / 3, abs=1e-4)


def test_the_sentence_says_a_range_is_not_a_bound() -> None:
    # Silence about what a range is worth reads as a guarantee it does not give.
    block = SliceSeries(tuple(_run(1.0 + n / 10, 10.0 + n) for n in range(5))).to_mapping()
    note = spread_note(block, "runtime_s")
    assert "is not a bound" in note
    assert "one time in 3" in note
    assert "whatever the shape of the variation" in note
