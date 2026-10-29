"""The pedigree matrix, held to the table it was copied from.

A transformation table typed out of a paper is the kind of thing that is right
the day it is written and wrong the day somebody tidies it. These tests hold
the copy to the published one cell by cell, hold the formula to a worked
example anybody can recompute by hand, and hold the two blank cells open --
because the tempting fix for a blank is to write 1.00 in it, and 1.00 is a
claim the source does not make.
"""

from __future__ import annotations

import doctest
import math

import pytest

from saggio.model import pedigree

#: The published table, written out a second time, on purpose. This is the one
#: place in this repository where a second copy earns its keep: the module's
#: copy is what the code reads, and this one is what a reviewer checks against
#: the paper. Two copies that must agree is exactly how a typo is caught.
#:
#: Frischknecht and Jungbluth 2004, p. 46, reproduced in Ciroth 2012 Figure 3.
PUBLISHED: dict[str, tuple[float | None, ...]] = {
    "reliability": (1.00, 1.05, 1.10, 1.20, 1.50),
    "completeness": (1.00, 1.02, 1.05, 1.10, 1.20),
    "temporal": (1.00, 1.03, 1.10, 1.20, 1.50),
    "geographical": (1.00, 1.01, 1.02, None, 1.10),
    "technological": (1.00, None, 1.20, 1.50, 2.00),
    "sample_size": (1.00, 1.02, 1.05, 1.10, 1.20),
}


def test_every_cell_is_the_published_one() -> None:
    assert pedigree.FACTORS == PUBLISHED


@pytest.mark.parametrize(("indicator", "score"), [("geographical", 4), ("technological", 2)])
def test_a_blank_cell_stays_blank(indicator: str, score: int) -> None:
    """The source leaves these two empty, and empty is not one.

    Writing 1.00 here would say "this mode is as good as the best", which the
    matrix does not say about a mode it declines to define.
    """
    assert pedigree.FACTORS[indicator][score - 1] is None
    assert not pedigree.is_defined(indicator, score)
    with pytest.raises(KeyError):
        pedigree.factor(indicator, score)


def test_the_best_possible_reading_adds_nothing() -> None:
    """Five ones and a basic uncertainty of one give a spread of exactly one.

    Every logarithm in the formula is ln(1.0) = 0, so the interval collapses on
    the value. It is the one case the formula can be checked against by hand
    with no arithmetic at all.
    """
    assert pedigree.spread(pedigree.Scores(1, 1, 1, 1, 1), basic_uncertainty=1.0) == 1.0


def test_the_formula_is_the_published_one() -> None:
    """Recompute one reading independently, from the factors themselves.

    Written as the source writes it rather than as the module writes it, so a
    rearrangement of the implementation that changed the answer would show up
    here rather than agreeing with itself.
    """
    scores = pedigree.Scores(
        reliability=4, completeness=3, temporal=5, geographical=2, technological=3
    )
    basic = 1.05
    by_hand = math.exp(
        math.sqrt(
            math.log(1.20) ** 2
            + math.log(1.05) ** 2
            + math.log(1.50) ** 2
            + math.log(1.01) ** 2
            + math.log(1.20) ** 2
            + math.log(basic) ** 2
        )
    )
    assert pedigree.spread(scores, basic_uncertainty=basic) == pytest.approx(by_hand)


def test_the_sample_size_is_absent_unless_stated() -> None:
    """The sample size was dropped in ecoinvent 3, so silence gets the current rule."""
    without = pedigree.spread(pedigree.Scores(3, 3, 3, 3, 3), basic_uncertainty=1.05)
    with_it = pedigree.spread(pedigree.Scores(3, 3, 3, 3, 3, sample_size=5), basic_uncertainty=1.05)
    assert with_it > without
    assert "sample_size" not in pedigree.Scores(3, 3, 3, 3, 3).as_mapping()


def test_a_worse_reading_is_never_a_narrower_interval() -> None:
    """Monotonicity, which is the property that makes the scores mean anything.

    If scoring a datum worse could tighten its interval, the whole exercise
    would be an invitation to score generously.
    """
    previous = 0.0
    for score in pedigree.SCORE_RANGE:
        if not pedigree.is_defined("reliability", score):
            continue
        spread = pedigree.spread(pedigree.Scores(score, 1, 1, 1, 1), basic_uncertainty=1.05)
        assert spread >= previous
        previous = spread


def test_the_basic_uncertainty_is_a_factor() -> None:
    """Below one it would *narrow* the interval, which is not what it is for."""
    with pytest.raises(ValueError, match="below one"):
        pedigree.spread(pedigree.Scores(1, 1, 1, 1, 1), basic_uncertainty=0.9)
    with pytest.raises(ValueError, match="must be a number"):
        pedigree.spread(pedigree.Scores(1, 1, 1, 1, 1), basic_uncertainty="1.05")


def test_the_interval_is_symmetric_in_the_logarithm() -> None:
    """A lognormal interval multiplies and divides by the same factor."""
    low, high = pedigree.interval(100.0, 1.25)
    assert high / 100.0 == pytest.approx(100.0 / low)


def test_the_module_s_own_examples_run() -> None:
    assert doctest.testmod(pedigree, verbose=False).failed == 0
