"""
What changed between two cost models, and whether it matters.

Module summary
--------------
A cost model committed next to the code is only useful if somebody notices when it
stops being true. This module compares two models quantity by quantity and reports
three kinds of change: a number that moved, a status that moved, and a quantity
that appeared or disappeared.

Two of those are easy to under-rate. A status moving from ``measured`` to
``estimated`` is a regression even when the number is identical, because the model
now knows less than it did. A quantity that disappears is a regression too: the
usual way a cost stops being reported is that somebody deleted the field.

The gate is a percentage on the numbers, and it reads the direction from the
dimension registry rather than assuming every increase is bad, so a dimension a
project registered itself is watched exactly as carefully as carbon.

Usage example
-------------
>>> from saggio.diff import compare
>>> def one(value):
...     return {"scenarios": [{"name": "d",
...             "costs": {"energy": {"value": value, "status": "measured"}}}]}
>>> before, after = one(1.0), one(1.5)
>>> comparison = compare(before, after)
>>> comparison.changes[0].percent_change
50.0

Author
------
Warith Harchaoui
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Final

from .model.cost_model import CostModel
from .model.noise import Band, band_for
from .model.quantity import Quantity, source_strength
from .model.results import Report
from .model.taxonomy import status_strength

#: How far a number may move before the gate fails. Ten per cent is the
#: convention this package ships with; a project that needs a tighter or looser
#: gate passes its own.
DEFAULT_DRIFT_THRESHOLD_PERCENT: Final[float] = 10.0

#: The dotted-path segment that marks a quantity as a per-dimension cost, used to
#: read the direction of a change from the dimension registry.
_COSTS_SEGMENT: Final[str] = ".costs."


#: What a side of a change reads as when the quantity carries no number. A
#: ``TODO`` gaining a measurement is the most ordinary good change there is, and
#: it has a side with nothing in it, so both sides are rendered through this.
_NO_NUMBER: Final[str] = "no number"


def _odds(*bands: Band | None) -> str:
    """Return what a band's run count is worth, as a clause.

    A range is not a bound. The next run falls outside a range of ``n`` about
    ``2 / (n + 1)`` of the time with nothing having changed, so a gate that
    excuses a movement for landing inside one should say how often that
    excuse is wrong — and a gate that fails for landing outside should say how
    often *that* is.

    Parameters
    ----------
    *bands : Band or None
        The bands in play. The thinnest decides, since it is the one that will
        be exceeded first.

    Returns
    -------
    str
        A clause, or an empty string when no band came from repeated runs.

    Examples
    --------
    >>> _odds(Band(1.0, 2.0, (), 5))
    ' — a 5-run range, exceeded by unchanged work one time in 3'
    >>> _odds(Band(1.0, 2.0))
    ''
    """
    counted = [band for band in bands if band is not None and band.runs]
    if not counted:
        return ""
    thinnest = min(counted, key=lambda band: band.runs)
    odds = thinnest.outside_odds()
    if odds is None:
        return ""
    return (
        f" — a {thinnest.runs}-run range, exceeded by unchanged work "
        f"one time in {round(1 / odds)}"
    )


def _point(quantity: Quantity | None) -> Band | None:
    """Return a quantity's value as a zero-width band, or ``None``.

    A side that repeated nothing still has a position. Treating it as its own
    value twice over lets one overlap test answer both the two-sided question
    and the one-sided one, instead of two rules that could disagree.

    Parameters
    ----------
    quantity : Quantity or None
        One side of a change.

    Returns
    -------
    Band or None
        The point, or ``None`` when there is no number to place.

    Examples
    --------
    >>> _point(Quantity(value=3.0, status="measured")).low
    3.0
    >>> _point(None) is None
    True
    """
    if quantity is None or not isinstance(quantity.value, (int, float)):
        return None
    if isinstance(quantity.value, bool):
        return None
    return Band(float(quantity.value), float(quantity.value))


def _rendered(value: float | int | None) -> str:
    """Render one side of a numeric change, including the side that has none.

    Parameters
    ----------
    value : float or int or None
        The number, or ``None`` when the quantity is a ``placeholder`` or a
        ``TODO`` and so has no number to show.

    Returns
    -------
    str
        The number, or :data:`_NO_NUMBER`.

    Examples
    --------
    >>> _rendered(2.0)
    '2'
    >>> _rendered(None)
    'no number'
    """
    return _NO_NUMBER if value is None else f"{value:g}"


@dataclass(frozen=True, slots=True)
class Change:
    """One quantity that is not the same in both models.

    Parameters
    ----------
    path : str
        The dotted path of the quantity.
    before : Quantity or None
        What it was, or ``None`` when it did not exist.
    after : Quantity or None
        What it is, or ``None`` when it no longer exists.
    percent_change : float or None
        How far the number moved, as a percentage of the old one. ``None`` when
        either side has no number, or the old number was zero and a percentage of
        zero means nothing.
    worse : bool
        Whether the change is in the direction the dimension calls a regression.
    noise_before : Band or None, optional
        The range repeated measurement left around this figure in the earlier
        model, when it repeated anything.
    noise_after : Band or None, optional
        The same for the later model. Two overlapping ranges mean a second draw
        from each measurement could have produced both numbers, so the movement
        between them is not evidence that anything changed.

    Examples
    --------
    >>> Change("p", None, Quantity(value=1, status="measured"), None, False).appeared()
    True
    """

    path: str
    before: Quantity | None
    after: Quantity | None
    percent_change: float | None
    worse: bool
    noise_before: Band | None = None
    noise_after: Band | None = None

    def within_noise(self) -> bool:
        """Return whether the movement fits inside the ranges both sides measured.

        A side that repeated nothing is its own value twice over, so this one
        test covers the case where only one of the two was repeated: the
        question becomes whether the other's number falls inside the range the
        repeated one actually saw.

        Returns
        -------
        bool
            ``True`` when at least one side recorded a range and the two
            overlap. ``False`` when neither did, which leaves the fixed
            threshold in charge exactly as before.

        Examples
        --------
        >>> wide = Band(1.0, 5.0, ("the power",))
        >>> Change("p", None, None, 300.0, True, wide, Band(4.0, 4.0)).within_noise()
        True
        >>> Change("p", None, None, 300.0, True, wide, Band(9.0, 9.0)).within_noise()
        False
        >>> Change("p", None, None, 300.0, True).within_noise()
        False
        """
        if self.noise_before is None and self.noise_after is None:
            return False
        before = self.noise_before or _point(self.before)
        after = self.noise_after or _point(self.after)
        if before is None or after is None:
            return False
        return before.overlaps(after)

    def noise_phrase(self) -> str:
        """Return what to say about the ranges, or an empty string.

        Returns
        -------
        str
            A clause naming both measured ranges, so a movement excused by
            noise is excused *visibly* and a reader can see how wide the
            excuse was.

        Examples
        --------
        >>> Change("p", None, None, None, False,
        ...        Band(1.0, 5.0, ("the power",)), Band(2.0, 6.0, ("the power",))
        ...        ).noise_phrase()
        'inside the noise both models measured: 1 to 5, then 2 to 6'
        """
        before, after = self.noise_before, self.noise_after
        if before is None and after is None:
            return ""
        if before is not None and after is not None:
            return (
                f"inside the noise both models measured: "
                f"{before.low:.4g} to {before.high:.4g}, then "
                f"{after.low:.4g} to {after.high:.4g}{_odds(before, after)}"
            )
        measured = before if before is not None else after
        side = "the earlier" if before is not None else "the later"
        if measured is None:
            return ""
        return (
            f"inside the noise {side} model measured: "
            f"{measured.low:.4g} to {measured.high:.4g}{_odds(measured)}"
        )

    def units_mismatch(self) -> bool:
        """Return whether the two sides are not even in the same unit or money.

        Returns
        -------
        bool
            ``True`` when both sides carry numbers but in different units or
            currencies, which makes any numeric comparison meaningless and is a
            drift of its own.

        Examples
        --------
        >>> Change("p", Quantity(value=10.0, currency="USD", status="measured"),
        ...        Quantity(value=10.0, currency="EUR", status="measured"),
        ...        None, True).units_mismatch()
        True
        """
        return (
            self.before is not None
            and self.after is not None
            and self.before.is_known()
            and self.after.is_known()
            and (
                (self.before.currency or None) != (self.after.currency or None)
                or (self.before.unit or None) != (self.after.unit or None)
            )
        )

    def appeared(self) -> bool:
        """Return whether the quantity is new.

        Returns
        -------
        bool
            ``True`` when it exists only in the later model.

        Examples
        --------
        >>> Change("p", None, Quantity(value=1), None, False).appeared()
        True
        """
        return self.before is None and self.after is not None

    def disappeared(self) -> bool:
        """Return whether the quantity is gone.

        Returns
        -------
        bool
            ``True`` when it exists only in the earlier model.

        Examples
        --------
        >>> Change("p", Quantity(value=1), None, None, True).disappeared()
        True
        """
        return self.before is not None and self.after is None

    def status_changed(self) -> bool:
        """Return whether the honesty status moved.

        Returns
        -------
        bool
            ``True`` when both sides exist and their statuses differ.

        Examples
        --------
        >>> Change("p", Quantity(status="measured"), Quantity(status="TODO"),
        ...        None, True).status_changed()
        True
        """
        if self.before is None or self.after is None:
            return False
        return self.before.status != self.after.status

    def provenance_weakened(self) -> bool:
        """Return whether the number is now further from whoever sets it.

        A price that was read from a vendor's own price API and is now copied
        from a community aggregator is the same number at the same status, and
        is nonetheless a step down: one more pair of hands between the model and
        the fact. The gate treats that the way it treats a weakened status.

        Returns
        -------
        bool
            ``True`` when both sides exist and the later one declares a weaker
            source kind. A quantity that declared none and still declares none
            has not weakened.

        Examples
        --------
        >>> Change("p", Quantity(source_kind="first-party"),
        ...        Quantity(source_kind="aggregator"), None, False).provenance_weakened()
        True
        >>> Change("p", Quantity(), Quantity(), None, False).provenance_weakened()
        False
        """
        if self.before is None or self.after is None:
            return False
        return source_strength(self.after.source_kind) < source_strength(self.before.source_kind)

    def describe(self, *, threshold_percent: float | None = None) -> str:
        """Return one line saying what changed.

        Parameters
        ----------
        threshold_percent : float or None, optional
            The gate this change is being held to. Given it, the measured
            noise is mentioned only where it decides the verdict: a figure
            that moved two per cent was never going to breach, and saying it
            fits inside a band is clutter on a line nobody was worried about.

        Returns
        -------
        str
            A sentence naming the path and the movement.

        Examples
        --------
        >>> Change("p", Quantity(value=1.0, status="measured"),
        ...        Quantity(value=2.0, status="measured"), 100.0, True).describe()
        'p: 1 -> 2 (+100.0%), worse'
        >>> Change("p", Quantity(status="TODO"),
        ...        Quantity(value=2.0, status="measured"), None, False).describe()
        'p: no number -> 2, TODO -> measured'
        """
        if self.appeared():
            return f"{self.path}: appeared, {self.after.status if self.after else ''}"
        if self.disappeared():
            return f"{self.path}: gone, was {self.before.status if self.before else ''}"
        before, after = self.before, self.after
        parts: list[str] = []
        if before is not None and after is not None and before.value != after.value:
            movement = f" ({self.percent_change:+.1f}%)" if self.percent_change is not None else ""
            parts.append(f"{_rendered(before.value)} -> {_rendered(after.value)}{movement}")
        if before is not None and after is not None:
            if (before.currency or None) != (after.currency or None):
                parts.append(
                    f"currency {before.currency or 'none'} -> {after.currency or 'none'}: "
                    "not the same money"
                )
            elif (before.unit or None) != (after.unit or None):
                parts.append(
                    f"unit {before.unit or 'none'} -> {after.unit or 'none'}: "
                    "the numbers are not comparable"
                )
        if self.status_changed() and before is not None and after is not None:
            parts.append(f"{before.status} -> {after.status}")
        if self.provenance_weakened() and before is not None and after is not None:
            parts.append(f"{before.source_kind or 'no source kind'} -> {after.source_kind}")
        decisive = threshold_percent is None or (
            self.percent_change is not None
            and abs(self.percent_change) > threshold_percent
        )
        if self.worse and decisive and self.within_noise():
            parts.append(self.noise_phrase())
        detail = ", ".join(parts) or "changed"
        return f"{self.path}: {detail}" + (", worse" if self.worse else "")


@dataclass(slots=True)
class Comparison:
    """Everything that differs between two cost models.

    Parameters
    ----------
    changes : list of Change
        Every difference found, in document order.
    threshold_percent : float
        The gate the numbers were held to.

    Examples
    --------
    >>> Comparison().passes()
    True
    """

    changes: list[Change] = field(default_factory=list)
    threshold_percent: float = DEFAULT_DRIFT_THRESHOLD_PERCENT

    def breaches(self) -> list[Change]:
        """Return the changes that fail the gate.

        A change fails when it moved a cost in the worse direction by more than
        the threshold, when it switched a quantity's unit or currency, when it
        weakened a quantity's honesty status, when it weakened its provenance,
        or when it removed a quantity that used to be reported.

        Returns
        -------
        list of Change
            The failing changes.

        Examples
        --------
        >>> gone = Change("p", Quantity(value=1.0, status="measured"), None, None, True)
        >>> Comparison([gone]).breaches()[0].path
        'p'
        """
        failing: list[Change] = []
        for change in self.changes:
            if change.disappeared():
                failing.append(change)
            elif change.units_mismatch():
                # Dollars against euros, or kWh against Wh: there is no percent
                # to be under a threshold, and the switch itself is the drift.
                failing.append(change)
            elif (
                change.worse
                and change.percent_change is not None
                and abs(change.percent_change) > self.threshold_percent
                # A movement between two numbers that each measurement could
                # have produced is not evidence that anything changed. The
                # gate had this evidence in both files it was comparing and
                # read neither, so it fired on every re-measurement and could
                # not tell a regression from a noisy neighbour.
                and not change.within_noise()
            ):
                failing.append(change)
            elif (
                change.before is not None
                and change.after is not None
                and status_strength(change.after.status) < status_strength(change.before.status)
            ):
                failing.append(change)
            elif change.provenance_weakened():
                failing.append(change)
        return failing

    def excused(self) -> list[Change]:
        """Return the changes the measured noise accounts for.

        These are movements past the threshold that the two models' own
        repeated measurements could have produced. They are reported, not
        hidden: a release excused by a hundred-per-cent band should show the
        reader the band.

        Returns
        -------
        list of Change
            The excused changes, in document order.

        Examples
        --------
        >>> Comparison().excused()
        []
        """
        return [
            change
            for change in self.changes
            if change.worse
            and change.percent_change is not None
            and abs(change.percent_change) > self.threshold_percent
            and change.within_noise()
        ]

    def passes(self) -> bool:
        """Return whether the comparison clears the gate.

        Returns
        -------
        bool
            ``True`` when nothing breached it.

        Examples
        --------
        >>> Comparison().passes()
        True
        """
        return not self.breaches()

    def to_report(self) -> Report:
        """Render the comparison as a verdict every surface can print.

        Returns
        -------
        Report
            Breaches as errors, other changes as warnings.

        Examples
        --------
        >>> Comparison().to_report().ok
        True
        """
        report = Report()
        breaching = {id(change) for change in self.breaches()}
        for change in self.changes:
            spoken = change.describe(threshold_percent=self.threshold_percent)
            if id(change) in breaching:
                report.error(change.path, spoken.split(": ", 1)[-1])
            else:
                report.warning(change.path, spoken.split(": ", 1)[-1])
        return report

    def to_mapping(self) -> dict[str, Any]:
        """Serialise the comparison for a JSON surface.

        Returns
        -------
        dict
            A mapping with the verdict, the threshold, and every change.

        Examples
        --------
        >>> Comparison().to_mapping()["passes"]
        True
        """
        return {
            "passes": self.passes(),
            "threshold_percent": self.threshold_percent,
            "excused_by_noise": len(self.excused()),
            "changes": [
                {
                    "path": change.path,
                    "before": change.before.to_mapping() if change.before else None,
                    "after": change.after.to_mapping() if change.after else None,
                    "percent_change": change.percent_change,
                    "worse": change.worse,
                    "within_noise": change.within_noise(),
                    "noise_before": (
                        change.noise_before.to_mapping() if change.noise_before else None
                    ),
                    "noise_after": (
                        change.noise_after.to_mapping() if change.noise_after else None
                    ),
                    "description": change.describe(threshold_percent=self.threshold_percent),
                }
                for change in self.changes
            ],
        }


def _percent_change(before: Quantity, after: Quantity) -> float | None:
    """Return how far a number moved, as a percentage of what it was.

    Parameters
    ----------
    before : Quantity
        The earlier quantity.
    after : Quantity
        The later one.

    Returns
    -------
    float or None
        The signed percentage, or ``None`` when either side has no number or the
        earlier one was zero, since a percentage of zero says nothing.

    Examples
    --------
    >>> _percent_change(Quantity(value=2.0, status="measured"),
    ...                 Quantity(value=3.0, status="measured"))
    50.0
    >>> _percent_change(Quantity(value=0.0), Quantity(value=1.0)) is None
    True
    """
    if not (before.is_known() and after.is_known()):
        return None
    if float(before.value) == 0.0:
        return None
    return (float(after.value) - float(before.value)) / float(before.value) * 100.0


def _is_worse(path: str, model: CostModel, percent: float | None) -> bool:
    """Return whether a movement is in the direction the dimension calls worse.

    Parameters
    ----------
    path : str
        The dotted path of the quantity.
    model : CostModel
        The later model, whose registry says which way is worse.
    percent : float or None
        The signed movement.

    Returns
    -------
    bool
        ``True`` when the movement is a regression on this dimension. A quantity
        that is not a per-dimension cost, such as an assumption, is never called
        worse: an assumption changing is news, not a regression.

    Examples
    --------
    >>> model = CostModel.from_mapping({})
    >>> _is_worse("scenarios[0].costs.energy", model, 20.0)
    True
    >>> _is_worse("assumptions.pue", model, 20.0)
    False
    """
    if percent is None or _COSTS_SEGMENT not in path:
        return False
    key = path.rsplit(_COSTS_SEGMENT, 1)[1]
    registry = model.registry
    if key not in registry:
        return percent > 0.0
    return percent > 0.0 if registry.get(key).higher_is_worse else percent < 0.0


def compare(
    before: CostModel | dict[str, Any],
    after: CostModel | dict[str, Any],
    *,
    threshold_percent: float = DEFAULT_DRIFT_THRESHOLD_PERCENT,
) -> Comparison:
    """Compare two cost models quantity by quantity.

    Parameters
    ----------
    before : CostModel or dict
        The earlier model.
    after : CostModel or dict
        The later one.
    threshold_percent : float, optional
        How far a cost may move in the worse direction before the gate fails.

    Returns
    -------
    Comparison
        Every difference, and whether the gate passes.

    Examples
    --------
    >>> comparison = compare({"a": {"value": 1.0, "status": "measured"}},
    ...                      {"a": {"value": 1.0, "status": "TODO"}})
    >>> comparison.passes()
    False
    """
    earlier = before if isinstance(before, CostModel) else CostModel.from_mapping(before)
    later = after if isinstance(after, CostModel) else CostModel.from_mapping(after)

    earlier_quantities = dict(earlier.typed_quantities())
    later_quantities = dict(later.typed_quantities())
    every_path = list(earlier_quantities) + [
        path for path in later_quantities if path not in earlier_quantities
    ]

    changes: list[Change] = []
    for path in every_path:
        old = earlier_quantities.get(path)
        new = later_quantities.get(path)
        if old is not None and new is not None and old == new:
            continue
        # A number in dollars against a number in euros, or kWh against Wh, is
        # not a percentage: the unit change IS the drift, and a silent currency
        # switch is exactly what this gate exists to catch.
        mismatched = (
            old is not None
            and new is not None
            and old.is_known()
            and new.is_known()
            and (
                (old.currency or None) != (new.currency or None)
                or (old.unit or None) != (new.unit or None)
            )
        )
        percent = (
            _percent_change(old, new)
            if not mismatched and old is not None and new is not None
            else None
        )
        worse = mismatched or _is_worse(path, later, percent) or (old is not None and new is None)
        changes.append(
            Change(
                path=path,
                before=old,
                after=new,
                percent_change=percent,
                worse=worse,
                noise_before=band_for(earlier, path),
                noise_after=band_for(later, path),
            )
        )

    return Comparison(changes=changes, threshold_percent=threshold_percent)
