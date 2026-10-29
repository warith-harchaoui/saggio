"""The pedigree matrix: a qualitative judgement turned into an interval.

Module summary
--------------
Four statuses say how well founded a number is. They are coarse on purpose, and
the coarseness has a cost: two figures both labelled ``estimated`` can be an
order of magnitude apart in how much they deserve to be believed, and the label
cannot tell them apart.

Life-cycle assessment solved this before this package existed. The **pedigree
matrix** scores a datum on named axes -- how reliable the source, how complete,
how recent, how close geographically, how close technologically -- then turns
those scores into an uncertainty factor, so the figure carries a spread rather
than a label. The scoring is a judgement; the conversion is arithmetic, and the
arithmetic is published.

This module implements that conversion and nothing else. It does not score
anything, because a score is a reading of where a number came from and only the
person who fetched it can make it.

What is implemented, and what is refused
----------------------------------------
The **transformation table** and the **combining formula** are published, cited
below, and implemented here exactly as published.

The **basic uncertainty** is not. In ecoinvent it comes from a table indexed by
the kind of flow -- thermal energy, transport services, carbon dioxide emitted
to air -- and those rows describe an inventory of industrial processes, not the
dimensions this package carries. Transposing them would be inventing a
calibration. So it has to be stated, and until it is, a quality block produces
no interval at all: the field stays open, which is the same answer this package
gives to a country nobody named.

Two cells of the table are **blank** in the source, and a blank is not 1.00. The
matrix defines no such mode for that indicator, so a model that scores one is
refused rather than quietly given the benefit of the doubt.

Usage example
-------------
>>> scores = Scores(reliability=2, completeness=3, temporal=3,
...                 geographical=1, technological=3)
>>> round(spread(scores, basic_uncertainty=1.05), 4)
1.2491
>>> low, high = interval(1.0, spread(scores, basic_uncertainty=1.05))
>>> round(low, 4), round(high, 4)
(0.8006, 1.2491)

Sources
-------
- Frischknecht, R. and Jungbluth, N., eds. (2004). *Overview and Methodology*,
  ecoinvent report no. 1. The transformation table is p. 46; the formula that
  combines the factors is p. 44.
- Ciroth, A., with Muller, S. and Weidema, B. (2012). *Refining the pedigree
  matrix approach in ecoinvent*, version 7.1, which reproduces both and states
  that ecoinvent 3.0 applies the same values with the sample-size factor
  removed.
- Weidema, B. P. and Wesnaes, M. S. (1996). *Data quality management for life
  cycle inventories*, which brought the matrix into life-cycle assessment.
- Funtowicz, S. O. and Ravetz, J. R. (1990). *Uncertainty and Quality in Science
  for Policy*, where the pedigree idea begins.

Author
------
Warith Harchaoui
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Final

#: The five indicators ecoinvent 3 scores, in the order the source lists them,
#: with the key each one takes in a model's ``quality`` block.
INDICATORS: Final[tuple[str, ...]] = (
    "reliability",
    "completeness",
    "temporal",
    "geographical",
    "technological",
)

#: The sixth indicator, scored in ecoinvent 2 and removed in 3. Accepted when a
#: model states it, never required: a model that does not mention it gets the
#: version 3 behaviour, which is the current one.
SAMPLE_SIZE: Final[str] = "sample_size"

#: Every indicator a ``quality`` block may score.
SCORED: Final[tuple[str, ...]] = (*INDICATORS, SAMPLE_SIZE)

#: The transformation table, exactly as published: the default uncertainty
#: factors contributing to the square of the geometric standard deviation
#: (Frischknecht and Jungbluth 2004, p. 46), applied unchanged by ecoinvent 3.
#:
#: ``None`` is a cell the published table leaves empty. It is not 1.00 and it is
#: not an oversight here: the matrix defines no mode for that score on that
#: indicator, so a model claiming it is refused rather than given a free pass.
FACTORS: Final[dict[str, tuple[float | None, ...]]] = {
    "reliability": (1.00, 1.05, 1.10, 1.20, 1.50),
    "completeness": (1.00, 1.02, 1.05, 1.10, 1.20),
    "temporal": (1.00, 1.03, 1.10, 1.20, 1.50),
    "geographical": (1.00, 1.01, 1.02, None, 1.10),
    "technological": (1.00, None, 1.20, 1.50, 2.00),
    SAMPLE_SIZE: (1.00, 1.02, 1.05, 1.10, 1.20),
}

#: The scores the matrix defines, best first.
SCORE_RANGE: Final[tuple[int, ...]] = (1, 2, 3, 4, 5)

#: The share of the distribution the interval covers, by construction of the
#: published formula. Named rather than written into prose twice.
CONFIDENCE: Final[int] = 95


@dataclass(frozen=True, slots=True)
class Scores:
    """One reading of where a number came from, on the five named axes.

    Parameters
    ----------
    reliability : int
        How the source was verified: 1 for a verified measurement, 5 for a
        non-qualified estimate.
    completeness : int
        How much of the relevant population the datum covers.
    temporal : int
        How close the datum's period is to the period being modelled.
    geographical : int
        How close its place is to the place being modelled.
    technological : int
        How close its technology, process and materials are.
    sample_size : int or None
        Scored in ecoinvent 2 and dropped in 3. ``None`` -- the default -- is
        the current behaviour; state it only to reproduce an older figure.

    Examples
    --------
    >>> Scores(1, 1, 1, 1, 1).as_mapping()["reliability"]
    1
    >>> Scores(1, 1, 1, 1, 1, sample_size=2).as_mapping()["sample_size"]
    2
    """

    reliability: int
    completeness: int
    temporal: int
    geographical: int
    technological: int
    sample_size: int | None = None

    def as_mapping(self) -> dict[str, int]:
        """Return the scores as a mapping, omitting a sample size nobody stated.

        Examples
        --------
        >>> sorted(Scores(1, 2, 3, 1, 3).as_mapping())
        ['completeness', 'geographical', 'reliability', 'technological', 'temporal']
        """
        mapping = {
            "reliability": self.reliability,
            "completeness": self.completeness,
            "temporal": self.temporal,
            "geographical": self.geographical,
            "technological": self.technological,
        }
        if self.sample_size is not None:
            mapping[SAMPLE_SIZE] = self.sample_size
        return mapping


def is_defined(indicator: str, score: object) -> bool:
    """Return whether the published matrix defines a factor for this cell.

    Parameters
    ----------
    indicator : str
        One of :data:`SCORED`.
    score : object
        The score claimed, usually straight out of a parsed model.

    Returns
    -------
    bool
        ``False`` for an unknown indicator, a score outside one to five, and the
        two cells the source leaves blank.

    Examples
    --------
    >>> is_defined("reliability", 3)
    True
    >>> is_defined("geographical", 4)          # blank in the published table
    False
    >>> is_defined("technological", 2)         # blank in the published table
    False
    >>> is_defined("charisma", 1)
    False
    """
    row = FACTORS.get(indicator)
    if row is None:
        return False
    if not isinstance(score, int) or isinstance(score, bool):
        return False
    if score not in SCORE_RANGE:
        return False
    return row[score - 1] is not None


def factor(indicator: str, score: int) -> float:
    """Return the published uncertainty factor for one scored indicator.

    Parameters
    ----------
    indicator : str
        One of :data:`SCORED`.
    score : int
        One to five.

    Returns
    -------
    float
        The factor from the published table.

    Raises
    ------
    KeyError
        When the matrix defines no factor for that cell, which the caller is
        expected to have checked with :func:`is_defined`.

    Examples
    --------
    >>> factor("reliability", 5)
    1.5
    >>> factor("technological", 2)
    Traceback (most recent call last):
        ...
    KeyError: 'the pedigree matrix defines no factor for technological at score 2'
    """
    if not is_defined(indicator, score):
        raise KeyError(f"the pedigree matrix defines no factor for {indicator} at score {score}")
    value = FACTORS[indicator][score - 1]
    assert value is not None  # noqa: S101 - guaranteed by is_defined just above
    return value


def spread(scores: Scores, *, basic_uncertainty: float) -> float:
    r"""Return the square of the geometric standard deviation, as published.

    The formula is Frischknecht and Jungbluth 2004, p. 44:

    .. math::

        \sigma_g^2 = \exp\sqrt{\sum_i \left[\ln U_i\right]^2
                                  + \left[\ln U_b\right]^2}

    where :math:`U_i` are the factors for the scored indicators and
    :math:`U_b` is the basic uncertainty. It holds under the assumption the
    source states and this package repeats rather than hides: that the quantity
    is lognormally distributed.

    Parameters
    ----------
    scores : Scores
        The five indicator scores, and a sample size when one is stated.
    basic_uncertainty : float
        The basic uncertainty factor for this kind of quantity. It is not
        derivable from the scores and this package does not supply it.

    Returns
    -------
    float
        The factor the value is divided and multiplied by to get the interval.
        Never below 1.0.

    Raises
    ------
    KeyError
        When any score names a cell the matrix leaves blank.
    ValueError
        When the basic uncertainty is not a factor at or above one.

    Examples
    --------
    >>> perfect = Scores(1, 1, 1, 1, 1)
    >>> spread(perfect, basic_uncertainty=1.0)
    1.0
    >>> round(spread(Scores(5, 5, 5, 5, 5), basic_uncertainty=1.05), 4)
    2.5196
    """
    if not isinstance(basic_uncertainty, (int, float)) or isinstance(basic_uncertainty, bool):
        raise ValueError("the basic uncertainty must be a number")
    if not math.isfinite(basic_uncertainty) or basic_uncertainty < 1.0:
        raise ValueError("the basic uncertainty is a factor and cannot be below one")
    total = math.log(float(basic_uncertainty)) ** 2
    for indicator, score in scores.as_mapping().items():
        total += math.log(factor(indicator, score)) ** 2
    return math.exp(math.sqrt(total))


def interval(value: float, deviation: float) -> tuple[float, float]:
    """Return the interval a value and its spread describe.

    Parameters
    ----------
    value : float
        The geometric mean -- the number the model states.
    deviation : float
        The square of the geometric standard deviation, from :func:`spread`.

    Returns
    -------
    tuple of float
        The low and high ends, the value divided and multiplied by the spread.

    Examples
    --------
    >>> interval(100.0, 1.0)
    (100.0, 100.0)
    >>> low, high = interval(100.0, 2.0)
    >>> low, high
    (50.0, 200.0)
    """
    return value / deviation, value * deviation
