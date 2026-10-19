"""The honesty taxonomy: the ordering, and what it refuses to do."""

from __future__ import annotations

import pytest

from saggio.model.taxonomy import (
    ALLOWED_STATUSES,
    ESTIMATED,
    MEASURED,
    PLACEHOLDER,
    STATUS_ORDER,
    TODO,
    is_valid_status,
    overclaims,
    status_meaning,
    status_strength,
    weakest,
)


@pytest.mark.parametrize("status", sorted(ALLOWED_STATUSES))
def test_every_allowed_status_is_valid_and_described(status: str) -> None:
    assert is_valid_status(status)
    assert status_meaning(status)


@pytest.mark.parametrize("status", sorted(ALLOWED_STATUSES))
def test_every_status_is_described_in_every_language(status: str) -> None:
    # The four statuses are the vocabulary the whole package rests on, so a
    # reader who cannot read what one means has been handed a label and no
    # explanation of it.
    from saggio.i18n import language, languages

    said = {}
    for code in languages():
        with language(code):
            said[code] = status_meaning(status)
    assert all(said.values()), f"{status} is undescribed in {[c for c, t in said.items() if not t]}"
    assert len(set(said.values())) == len(said), f"{status} reads the same in every language"


@pytest.mark.parametrize("value", ["guessed", "", None, 3, ["measured"]])
def test_anything_outside_the_vocabulary_is_invalid(value: object) -> None:
    assert not is_valid_status(value)


def test_status_order_runs_strongest_to_weakest() -> None:
    strengths = [status_strength(status) for status in STATUS_ORDER]
    assert strengths == sorted(strengths, reverse=True)


def test_an_unknown_label_ranks_below_todo() -> None:
    # A typo must never let a derived value claim more confidence than it earned,
    # so it has to sort below the weakest real status rather than above it.
    assert status_strength("typoed") < status_strength(TODO)
    assert status_strength(None) < status_strength(TODO)


def test_weakest_picks_the_worst_input() -> None:
    assert weakest(MEASURED, ESTIMATED) == ESTIMATED
    assert weakest(MEASURED, PLACEHOLDER, ESTIMATED) == PLACEHOLDER
    assert weakest(MEASURED, TODO) == TODO


def test_weakest_ignores_absent_inputs() -> None:
    assert weakest(MEASURED, None) == MEASURED
    assert weakest(None, None) is None


def test_weakest_of_nothing_is_nothing() -> None:
    assert weakest() is None


def test_overclaiming_is_only_about_going_upwards() -> None:
    assert overclaims(MEASURED, ESTIMATED)
    assert not overclaims(ESTIMATED, ESTIMATED)
    assert not overclaims(TODO, MEASURED)


def test_no_ceiling_means_nothing_to_enforce() -> None:
    assert not overclaims(MEASURED, None)
    assert not overclaims(None, MEASURED)
