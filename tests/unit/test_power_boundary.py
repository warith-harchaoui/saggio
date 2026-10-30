"""The second boundary: how much of the metered hardware was doing this work.

A counter meters hardware, not processes. Everything here exists because a model
can state a measured wattage, state that idle capacity is excluded from it, and
be wrong on the second claim by a factor its own measurement block records.
"""

from __future__ import annotations

from saggio.analyze.power import (
    idle_exclusion,
    idle_is_excluded,
    measurement_rows,
    states_idle_is_excluded,
    workload_scope,
)

BUSY = {
    "idle_watts": 16.0,
    "attributed_watts": 4.5,
    "cpu_share": {"share": 0.19, "run_cpu_seconds": 0.5, "machine_cpu_seconds": 2.6},
}


def test_the_scope_says_the_figure_is_the_machines_not_the_runs() -> None:
    assert "whole machine's draw, not this run's alone" in workload_scope(BUSY, watts=23.7)


def test_the_scope_quotes_the_floor_the_machine_was_already_drawing() -> None:
    assert "16.0 W before the slice started" in workload_scope(BUSY, watts=23.7)


def test_the_scope_quotes_the_attributable_share_against_the_total() -> None:
    sentence = workload_scope(BUSY, watts=23.7)
    assert "19% share" in sentence
    assert "4.5 W of the 23.7 W" in sentence


def test_a_measurement_that_established_neither_says_so() -> None:
    # The failure mode this guards: a sentence that names no floor and no share
    # reading as though the figure were the run's own.
    sentence = workload_scope(None)
    assert "upper bound" in sentence
    assert "Nothing here established how much of it was" in sentence


def test_an_estimated_figure_keeps_the_old_exclusion() -> None:
    # A nameplate rating describes a part under load, so a model built on one
    # really does price work being done rather than a machine waiting.
    assert idle_exclusion(BUSY, measured=False) == idle_is_excluded()
    assert states_idle_is_excluded(idle_is_excluded())


def test_a_measured_figure_says_idle_is_in_not_out() -> None:
    line = idle_exclusion(BUSY, measured=True, watts=23.7)
    assert not states_idle_is_excluded(line)
    assert "16.0 W of the 23.7 W" in line


def test_the_measured_line_admits_the_costs_do_not_use_the_attribution() -> None:
    # The attribution is recorded and not spent. Saying so is the difference
    # between a caveat and a claim the numbers do not honour.
    line = idle_exclusion(BUSY, measured=True, watts=23.7)
    assert "the costs below do not use it" in line


def test_a_new_phrasing_that_forgets_to_say_idle_is_in_is_caught() -> None:
    # The sabotage. A list of known-bad strings would pass this line; the
    # predicate asks the opposite question, so a rewrite that drops the marker
    # fails rather than quietly reading as an inclusion.
    invented = "Idle capacity is accounted for somewhere else entirely."
    assert states_idle_is_excluded(invented)


def test_a_line_about_something_else_is_not_an_idle_claim() -> None:
    assert not states_idle_is_excluded("The people. Salaries, offices, and travel are out.")
    assert not states_idle_is_excluded("Making the hardware. Only the electricity is counted.")


def test_a_share_without_watts_still_names_what_it_is_a_share_of() -> None:
    sentence = workload_scope(BUSY)
    assert "19% share of the machine's processor work" in sentence
    assert "4.5 W is attributable" in sentence


def test_a_measurement_block_full_of_strings_does_not_crash_the_sentence() -> None:
    # Measurement blocks are YAML a human may have edited. A string where a
    # number belongs must drop the clause, not raise in the middle of writing a
    # model to disk.
    junk = {"idle_watts": "sixteen", "attributed_watts": None, "cpu_share": "half"}
    assert "Nothing here established" in workload_scope(junk)


def test_a_baseline_above_the_figure_is_not_called_a_floor() -> None:
    # Found by running the thing: the machine grew quieter between the baseline
    # and the slice, and the sentence went on calling 21.8 W a floor under a
    # 17.7 W figure. marginal_watts() already refuses that subtraction; this
    # sentence sits beside it and must refuse it the same way.
    quieter = {"idle_watts": 21.8}
    sentence = workload_scope(quieter, watts=17.7)
    assert "floor" not in sentence
    assert "grew quieter while the slice ran" in sentence


def test_the_exclusion_line_does_not_subtract_a_baseline_it_cannot_subtract() -> None:
    line = idle_exclusion({"idle_watts": 21.8}, measured=True, watts=17.7)
    assert "of the 17.7 W was being drawn" not in line
    assert "21.8 W before the slice against 17.7 W during it" in line


def test_a_floor_is_still_named_when_it_really_is_one() -> None:
    sentence = workload_scope({"idle_watts": 9.0}, watts=17.7)
    assert "9.0 W before the slice started, which is a floor" in sentence


def test_a_second_measurement_refreshes_the_line_the_first_one_wrote() -> None:
    # The other defect the run exposed: fold matched only lines that claimed
    # idle was out, so folding twice left the first measurement's watts standing
    # in a line that no longer matched the predicate which had rewritten it.
    from saggio.analyze.power import is_idle_claim

    first = idle_exclusion({"idle_watts": 9.0}, measured=True, watts=17.7)
    assert not states_idle_is_excluded(first)
    assert is_idle_claim(first), "a second fold would leave stale watts in this line"


def test_a_date_in_a_measurement_block_is_not_given_a_thousands_separator() -> None:
    """A year is not a quantity, and the grouping must not reach it.

    `i18n.number` documents this exact hazard and says the call sites were
    audited before the separator was added, *"because a year grouped as 2 025
    is the exact failure that docstring warns about, and no caller passes
    one"*. One did. `measurement_rows` has a catch-all branch for every scalar
    field it has no special handling for, and `measured_on` arrives through it,
    so every rendered report carried **2,026-10-19**. The key is not written at
    the call site, which is why reading the call sites could not find it.
    """
    rows = dict(measurement_rows({"measured_on": "2026-10-19"}))
    assert "2026-10-19" in rows.values()
    assert not any("2,026" in value for value in rows.values())


def test_a_real_number_in_the_same_branch_still_gets_its_separator() -> None:
    """The fix must not disarm the separator it was narrowing."""
    rows = dict(measurement_rows({"samples": 12345}))
    assert any("12,345" in value for value in rows.values())
