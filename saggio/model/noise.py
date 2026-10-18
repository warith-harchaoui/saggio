"""The band a repeated measurement leaves around every figure it reached.

Module summary
--------------
``saggio measure --repeat N`` records what each measured figure did across the
runs. On this package's own gallery model that is a 15% range on the runtime and
a **109%** range on the power, from five runs of one command on one machine a
minute apart.

``saggio diff`` then gated a release at ten per cent, against numbers whose own
measurement said they move by a hundred. The gate fired on every re-measurement
and could not tell a regression from a noisy neighbour — it had the evidence in
both files it was comparing, and read neither.

This module turns that evidence into a band. A figure the measurement bounded
directly — the runtime, the power — takes its own recorded range. A figure
derived from them takes the product of theirs, found by walking ``derived_from``
backwards, which is exact while each step is proportional to its inputs and is
how every cost in a model is built: energy is runtime times power, money is
energy times a price, carbon is energy times an intensity. A projection takes its
scenario cost's band, by a link made here rather than in the model: a projection
divides by a fraction nobody named, so claiming it *derives* from that cost is
false and the validator says so — but a band needs only proportionality, which
is the weaker claim a division by a constant actually supports. A figure that
reaches no measured range gets no band and is gated the way it always was.

What a band is **not**: a confidence interval. Five runs are five runs, not a
distribution, and the range they spanned is a floor under the variation rather
than an estimate of it. It says *this figure was observed to move this far*,
which is a weaker claim than a statistic and the only one the evidence supports.

Usage example
-------------
>>> from saggio.model.cost_model import CostModel
>>> model = CostModel.from_mapping({
...     "measurement": {"repeats": 3,
...                     "spread": {"power_w": {"low": 8.0, "median": 10.0, "high": 12.0}}},
...     "assumptions": {"power_draw": {"value": 10.0, "unit": "W", "status": "measured"}}})
>>> band = band_for(model, "assumptions.power_draw")
>>> band.low, band.high
(8.0, 12.0)

Author
------
Warith Harchaoui
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from .cost_model import CostModel

#: Which spread block bounds which quantity, and where that figure's own sample
#: is read from. The representative run is chosen by its runtime, so the runtime
#: the model carries *is* the spread's median, while the power it carries is
#: that run's power and not the middle of the series — two different anchors for
#: the same arithmetic, and getting them the same way round would scale every
#: band by however far the two happen to differ.
_POWER_PATH = "assumptions.power_draw"
_RUNTIME_KEY = "runtime_s"
_POWER_KEY = "power_w"

#: A projection's result is the scenario cost of the same dimension divided by
#: the fraction of the run the slice covered. It deliberately carries no
#: ``derived_from``, and an attempt to give it one is refused by the validator
#: with the right reason: *states 18000000.0 but does not follow from
#: scenarios[0].costs.time*. ``derived_from`` claims the value **follows
#: arithmetically** from the inputs named, and this one does not — the divisor
#: is not among them.
#:
#: A band needs something weaker. It needs the figure to be **proportional** to
#: what it came from, which a division by a constant fraction is. So the link is
#: made here, where the weaker claim is the one being made, rather than in the
#: model, where the stronger one would be false.
_PROJECTION = re.compile(
    r"^projections\.[^.]+\.costs\.(?P<dimension>[^.]+)\.(result|bounds\.[^.]+)$"
)

#: Which scenario a projection was built from. The auditor and ``fold`` both
#: write exactly one, and both project from it.
_PROJECTED_FROM = "scenarios[0].costs.{dimension}"


@dataclass(frozen=True, slots=True)
class Band:
    """The range a figure was observed to move across repeated measurement.

    Parameters
    ----------
    low : float
        The smallest value the recorded ranges allow for this figure.
    high : float
        The largest.
    sources : tuple of str
        Which measured figures the band came from, so a reader is never asked
        to take the width on trust.

    Examples
    --------
    >>> Band(1.0, 2.0, ("runtime",)).overlaps(Band(1.5, 3.0, ("runtime",)))
    True
    >>> Band(1.0, 2.0, ()).overlaps(Band(2.5, 3.0, ()))
    False
    """

    low: float
    high: float
    sources: tuple[str, ...] = ()

    def overlaps(self, other: Band) -> bool:
        """Return whether two bands share any value at all.

        Overlapping bands mean a second draw from each measurement could have
        produced the same number twice. That is the whole test: a movement
        between two values that each measurement could have given is not
        evidence that anything changed.

        Parameters
        ----------
        other : Band
            The other side's band. A side with no recorded range is its own
            value twice over, so this one test covers both cases.

        Returns
        -------
        bool
            ``True`` when the ranges touch.

        Examples
        --------
        >>> Band(1.0, 2.0).overlaps(Band(2.0, 5.0))
        True
        """
        return self.low <= other.high and other.low <= self.high

    def width(self) -> float | None:
        """Return the range as a fraction of its midpoint, or ``None``.

        Returns
        -------
        float or None
            ``(high - low)`` over the midpoint, and ``None`` when the midpoint
            is zero.

        Examples
        --------
        >>> Band(8.0, 12.0).width()
        0.4
        """
        middle = (self.low + self.high) / 2.0
        if middle == 0.0:
            return None
        return (self.high - self.low) / middle

    def describe(self) -> str:
        """Return the band as a phrase for a diff line.

        Returns
        -------
        str
            The range and what it was measured from.

        Examples
        --------
        >>> Band(8.0, 12.0, ("power",)).describe()
        'measured range 8 to 12, from power'
        """
        named = f", from {' and '.join(self.sources)}" if self.sources else ""
        return f"measured range {self.low:.4g} to {self.high:.4g}{named}"

    def to_mapping(self) -> dict[str, Any]:
        """Serialise the band for the JSON surface.

        Returns
        -------
        dict
            Plain numbers and the names behind them.

        Examples
        --------
        >>> sorted(Band(1.0, 2.0, ("runtime",)).to_mapping())
        ['high', 'low', 'sources']
        """
        return {
            "low": self.low,
            "high": self.high,
            "sources": list(self.sources),
        }


def _number(value: Any) -> float | None:
    """Return ``value`` as a float, or ``None`` when it is not one.

    Parameters
    ----------
    value : object
        Anything read out of a model, which is YAML a human may have edited.

    Returns
    -------
    float or None
        The number, or ``None``.

    Examples
    --------
    >>> _number(2), _number("2"), _number(True)
    (2.0, None, None)
    """
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def _spread(model: CostModel, key: str) -> Mapping[str, Any] | None:
    """Return one recorded spread block, or ``None``.

    Parameters
    ----------
    model : CostModel
        The model, which may carry a measurement block.
    key : str
        ``"runtime_s"`` or ``"power_w"``.

    Returns
    -------
    Mapping or None
        The block, or ``None`` when the model repeated nothing.

    Examples
    --------
    >>> from saggio.model.cost_model import CostModel
    >>> _spread(CostModel.from_mapping({}), "runtime_s") is None
    True
    """
    measurement = model.data.get("measurement")
    if not isinstance(measurement, Mapping):
        return None
    spreads = measurement.get("spread")
    if not isinstance(spreads, Mapping):
        return None
    block = spreads.get(key)
    return block if isinstance(block, Mapping) else None


def _factor(model: CostModel, key: str) -> tuple[float, float] | None:
    """Return one measured figure's range as a pair of multipliers.

    The multipliers are relative to the sample the model actually carries, so
    that applying them to any figure proportional to that one gives the range
    for it too.

    Parameters
    ----------
    model : CostModel
        The model.
    key : str
        ``"runtime_s"`` or ``"power_w"``.

    Returns
    -------
    tuple or None
        ``(low_multiplier, high_multiplier)``, or ``None`` where nothing was
        repeated, the block is malformed, or the anchor is zero and a ratio to
        it means nothing.

    Examples
    --------
    >>> from saggio.model.cost_model import CostModel
    >>> model = CostModel.from_mapping({"measurement": {"spread": {
    ...     "runtime_s": {"low": 1.0, "median": 2.0, "high": 4.0}}}})
    >>> _factor(model, "runtime_s")
    (0.5, 2.0)
    """
    block = _spread(model, key)
    if block is None:
        return None
    low, high = _number(block.get("low")), _number(block.get("high"))
    if low is None or high is None:
        return None
    if key == _RUNTIME_KEY:
        # The representative run is the median-runtime one, so the runtime the
        # model carries is this block's median by construction.
        anchor = _number(block.get("median"))
    else:
        # Not the median: the carried power is the median-*runtime* run's power.
        raw = model.get(_POWER_PATH)
        anchor = _number(raw.get("value")) if isinstance(raw, Mapping) else None
    if anchor is None or anchor == 0.0:
        return None
    return (low / anchor, high / anchor)


def _sources(model: CostModel, path: str, seen: set[str] | None = None) -> set[str]:
    """Return which measured figures a quantity's value rests on.

    Walks ``derived_from`` backwards. A quantity that is itself one of the
    measured figures answers for itself; anything else answers with whatever
    its inputs answer, de-duplicated so a figure reached by two routes is
    counted once rather than squared.

    Parameters
    ----------
    model : CostModel
        The model.
    path : str
        The dotted path of the quantity.
    seen : set of str or None, optional
        Paths already visited, which stops a malformed model with a cycle in
        its derivations from recursing until the stack runs out.

    Returns
    -------
    set of str
        Any of ``"runtime_s"`` and ``"power_w"``.

    Examples
    --------
    >>> from saggio.model.cost_model import CostModel
    >>> model = CostModel.from_mapping({"assumptions": {
    ...     "power_draw": {"value": 1.0, "status": "measured"}}})
    >>> _sources(model, "assumptions.power_draw")
    {'power_w'}
    """
    seen = set() if seen is None else seen
    if path in seen:
        return set()
    seen.add(path)
    if path == _POWER_PATH:
        return {_POWER_KEY}
    if path.endswith(".runtime") or path.endswith(".costs.time"):
        return {_RUNTIME_KEY}
    projected = _PROJECTION.match(path)
    if projected is not None:
        return _sources(
            model,
            _PROJECTED_FROM.format(dimension=projected.group("dimension")),
            seen,
        )
    raw = model.get(path)
    if not isinstance(raw, Mapping):
        return set()
    inputs = raw.get("derived_from")
    if not isinstance(inputs, list):
        return set()
    found: set[str] = set()
    for entry in inputs:
        if isinstance(entry, str):
            found |= _sources(model, entry, seen)
    return found


def band_for(model: CostModel, path: str) -> Band | None:
    """Return the range repeated measurement leaves around one quantity.

    Parameters
    ----------
    model : CostModel
        The model, which carries both the quantity and the spreads.
    path : str
        The dotted path of the quantity.

    Returns
    -------
    Band or None
        The band, or ``None`` when the quantity has no number or reaches no
        measured range. ``None`` is not a narrow band: it means nothing here
        bounds the figure, and the caller gates it the way it always did.

    Examples
    --------
    >>> from saggio.model.cost_model import CostModel
    >>> CostModel.from_mapping({}).data == {}
    True
    >>> band_for(CostModel.from_mapping({}), "a") is None
    True
    """
    raw = model.get(path)
    if not isinstance(raw, Mapping):
        return None
    value = _number(raw.get("value"))
    if value is None:
        return None
    keys = _sources(model, path)
    if not keys:
        return None
    low = high = 1.0
    named: list[str] = []
    for key in sorted(keys):
        factor = _factor(model, key)
        if factor is None:
            return None
        low *= factor[0]
        high *= factor[1]
        named.append("the runtime" if key == _RUNTIME_KEY else "the power")
    # A negative figure would swap the ends; costs are not negative, but the
    # arithmetic should not quietly produce a band whose low exceeds its high.
    ends = sorted((value * low, value * high))
    return Band(ends[0], ends[1], tuple(named))
