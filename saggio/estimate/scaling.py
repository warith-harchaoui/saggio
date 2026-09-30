"""
How the work grows with the size of the job, measured rather than assumed.

Module summary
--------------
Projecting a measured slice to a whole run means multiplying by the ratio of
their sizes, and that is only right when the work is uniform. Nothing in this
package used to check that. When the assumption is wrong it is wrong by a
*power*, not by a margin: a step that is quadratic in the batch turns a
thousandth of a run into a millionth of its cost, and the projection understates
the bill by three orders of magnitude while looking exactly as confident as a
correct one.

The fix is older than the problem. Goldsmith, Aiken and Wilkerson's *Measuring
Empirical Computational Complexity* (FSE 2007) runs a program over workloads
spanning orders of magnitude, fits cost against a size with a power law
``y = a * x ** b``, and reports the goodness of fit alongside the exponent. The
exponent is the answer, the fit is the warrant, and a bad fit is a finding about
the workload rather than a number to publish.

This module is that method, with this package's refusals attached. It fits on
log-log axes, because a power law is a straight line there and least squares on
the logarithms is the fit the original method uses. It refuses rather than
returning a plausible exponent when the evidence cannot carry one: fewer than
three points, sizes too close together to tell a line from a curve, a
non-positive size or duration that has no logarithm, or a fit too poor to mean
anything. Each refusal names what would resolve it.

What comes out is `measured`, and that is deliberate. An exponent fitted from
timings that all came from a clock is a summary of measurements, in the same way
that watts from an energy counter divided by a duration is a measurement. It is
`measured` **over the sizes that were run** and nowhere else, which is why the
fit carries its range and why a projection beyond that range says how far beyond
it went.

Usage example
-------------
>>> from saggio.estimate.scaling import Observation, fit_power_law
>>> quadratic = [Observation(size=n, seconds=1e-3 * n * n) for n in (10, 40, 160)]
>>> fit = fit_power_law(quadratic)
>>> round(fit.exponent.value, 3), fit.exponent.status
(2.0, 'measured')
>>> fit.refused
False

Author
------
Warith Harchaoui
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Final

from ..model.quantity import Quantity
from ..model.taxonomy import MEASURED, TODO, status_strength

#: How many differently sized runs it takes before an exponent means anything.
#: Two points fit a straight line exactly, on any axes, so two points can be made
#: to agree with every exponent there is and constrain none of them. Three is the
#: smallest number that can disagree with itself, which is the smallest number
#: that can produce a goodness of fit worth reading.
MINIMUM_OBSERVATIONS: Final[int] = 3

#: How far apart the largest and smallest size have to be before the difference
#: between a line and a curve is visible above the noise. At a ratio of four, a
#: quadratic costs four times what a linear one does across the range, which a
#: timing that repeats within a few percent can resolve. Below it, the honest
#: answer is that the runs were all the same size.
MINIMUM_SIZE_RATIO: Final[float] = 4.0

#: How good the fit has to be before the exponent is reported at all. A power law
#: that explains less than this much of the variation on log-log axes is not
#: describing the workload, and the useful output in that case is the refusal:
#: the slice is not representative of the run it was cut from.
DEFAULT_MINIMUM_R_SQUARED: Final[float] = 0.95

#: The unit an exponent carries. Dimensionless, and named rather than left empty
#: so that a reader meeting it in a YAML file knows it is not seconds.
EXPONENT_UNIT: Final[str] = "exponent"

#: Said when the exponent came out near one, which is the assumption every
#: projection in this package used to make silently.
_LINEAR_READING: Final[str] = (
    "The work grew in proportion to the size, so projecting by the ratio of "
    "sizes is sound over the range measured."
)

#: Said when the exponent came out above one, which is the case the assumption
#: got wrong.
_SUPERLINEAR_READING: Final[str] = (
    "The work grew faster than the size, by a power of {exponent:.2f}. Doubling "
    "the job multiplies the cost by {doubling:.2f} rather than by 2, so a "
    "projection that divided by the size ratio would understate the whole run."
)

#: Said when the exponent came out below one, which is usually fixed overhead
#: rather than a sublinear algorithm.
_SUBLINEAR_READING: Final[str] = (
    "The work grew more slowly than the size, by a power of {exponent:.2f}. Over "
    "these sizes the run is dominated by costs that do not grow with the job — "
    "start-up, imports, loading a model — so the slices are mostly measuring "
    "overhead and a projection from them would overstate the whole run."
)


@dataclass(frozen=True, slots=True)
class Observation:
    """One run, of a known size, that took a known time.

    Parameters
    ----------
    size : float
        How much work the run covered, in the units the repository states its
        own size in: iterations, steps, rows, tokens. What the unit is does not
        matter to the fit, as long as every observation uses the same one.
    seconds : float
        How long it took.

    Examples
    --------
    >>> Observation(size=600.0, seconds=12.5).size
    600.0
    """

    size: float
    seconds: float


@dataclass(frozen=True, slots=True)
class ScalingFit:
    """A measured power law, or a refusal to report one.

    Parameters
    ----------
    exponent : Quantity
        The ``b`` of ``y = a * x ** b``, or a ``TODO`` carrying the reason the
        fit was refused.
    coefficient : float or None
        The ``a``, in seconds at size one. Useful for redoing the arithmetic and
        not much else: it absorbs every fixed cost in the run, so it is not a
        figure about the algorithm.
    r_squared : float or None
        How much of the variation the power law explains, on log-log axes.
    observations : tuple of Observation
        Every run the fit was made from, so the arithmetic can be redone.
    method : str
        One sentence naming what was fitted and how.
    reading : str
        What the exponent means for a projection, in plain words.
    limits : tuple of str
        Where the fit stops being evidence.
    refused : bool
        Whether the fit was declined rather than computed.

    Examples
    --------
    >>> refusal = ScalingFit(exponent=Quantity(status="TODO"), method="Refused.",
    ...                      reading="", refused=True)
    >>> refusal.refused, refusal.usable()
    (True, False)
    """

    exponent: Quantity
    method: str
    reading: str
    coefficient: float | None = None
    r_squared: float | None = None
    observations: tuple[Observation, ...] = field(default_factory=tuple)
    limits: tuple[str, ...] = field(default_factory=tuple)
    refused: bool = False

    def usable(self) -> bool:
        """Return whether this fit may be projected with.

        Returns
        -------
        bool
            True when an exponent was computed and carries a number.

        Examples
        --------
        >>> ScalingFit(Quantity(value=1.0, status="measured"), "m", "r").usable()
        True
        """
        return not self.refused and self.exponent.is_known()

    def size_range(self) -> tuple[float, float] | None:
        """Return the smallest and largest size the fit was made from.

        Returns
        -------
        tuple of float, or None
            The range, or ``None`` when there were no observations.

        Examples
        --------
        >>> fit = ScalingFit(Quantity(value=1.0, status="measured"), "m", "r",
        ...                  observations=(Observation(10, 1), Observation(90, 9)))
        >>> fit.size_range()
        (10.0, 90.0)
        """
        if not self.observations:
            return None
        sizes = [float(observation.size) for observation in self.observations]
        return min(sizes), max(sizes)

    def predict(self, size: float) -> float | None:
        """Return the seconds the fit expects at a given size.

        Parameters
        ----------
        size : float
            The size to predict for, in the same units the observations used.

        Returns
        -------
        float or None
            The predicted duration, or ``None`` when this fit carries no numbers
            or the size has no logarithm.

        Examples
        --------
        >>> fit = fit_power_law([Observation(n, 2.0 * n) for n in (1, 10, 100)])
        >>> round(fit.predict(50.0), 6)
        100.0
        >>> fit.predict(0.0) is None
        True
        """
        if not self.usable() or self.coefficient is None or size <= 0.0:
            return None
        return float(self.coefficient) * float(size) ** float(self.exponent.value)

    def to_mapping(self) -> dict[str, Any]:
        """Serialise the fit for a model's measurement block.

        The exponent is nested under ``exponent`` rather than spread across the
        mapping, because a mapping with a ``value`` key *is* a quantity as far as
        the validator is concerned, and the observations beside it would be read
        as invented fields on that quantity.

        Returns
        -------
        dict
            The exponent as a quantity, the fit statistics as plain numbers, the
            observations as a list, and the prose.

        Examples
        --------
        >>> fit = fit_power_law([Observation(n, 2.0 * n) for n in (1, 10, 100)])
        >>> sorted(fit.to_mapping())
        ['exponent', 'limits', 'method', 'observations', 'r_squared', 'reading']
        """
        mapping: dict[str, Any] = {
            "method": self.method,
            "reading": self.reading,
            "exponent": self.exponent.to_mapping(),
        }
        if self.r_squared is not None:
            mapping["r_squared"] = round(float(self.r_squared), 6)
        if self.observations:
            mapping["observations"] = [
                {"size": float(observation.size), "seconds": float(observation.seconds)}
                for observation in self.observations
            ]
        if self.limits:
            mapping["limits"] = list(self.limits)
        if self.refused:
            mapping["refused"] = True
        return mapping


def _refusal(reason: str, observations: tuple[Observation, ...] = ()) -> ScalingFit:
    """Return a refused fit carrying the reason and what would resolve it.

    Parameters
    ----------
    reason : str
        Why no exponent was reported, phrased as something to act on.
    observations : tuple of Observation, optional
        Whatever runs there were, kept so the reader can see the evidence that
        was not enough.

    Returns
    -------
    ScalingFit
        A refusal.

    Examples
    --------
    >>> _refusal("two points fit any line").refused
    True
    """
    return ScalingFit(
        exponent=Quantity(unit=EXPONENT_UNIT, status=TODO, notes=reason),
        method="Refused.",
        reading=reason,
        observations=observations,
        refused=True,
    )


def _reading_for(exponent: float) -> str:
    """Return the plain-words meaning of an exponent.

    Parameters
    ----------
    exponent : float
        The fitted ``b``.

    Returns
    -------
    str
        One or two sentences a reader can act on.

    Examples
    --------
    >>> _reading_for(1.02) == _LINEAR_READING
    True
    >>> "understate" in _reading_for(2.0)
    True
    >>> "overhead" in _reading_for(0.4)
    True
    """
    # A tenth of a power either side of one is inside what three or four timings
    # on a shared machine can resolve, so it is reported as linear rather than as
    # a precision nobody has.
    if abs(exponent - 1.0) <= 0.1:
        return _LINEAR_READING
    if exponent > 1.0:
        return _SUPERLINEAR_READING.format(exponent=exponent, doubling=2.0**exponent)
    return _SUBLINEAR_READING.format(exponent=exponent)


def fit_power_law(
    observations: list[Observation] | tuple[Observation, ...],
    *,
    minimum_r_squared: float = DEFAULT_MINIMUM_R_SQUARED,
    status: str = MEASURED,
) -> ScalingFit:
    """Fit ``seconds = a * size ** b`` and say how well it fits.

    The fit is least squares on log-log axes, which is what makes it a power law:
    ``log y = log a + b log x`` is a straight line whose slope is the exponent.
    The goodness of fit is computed on those same axes, as in the method this
    follows, so an R-squared here is about the power law and not about a line
    through the raw seconds.

    Parameters
    ----------
    observations : list or tuple of Observation
        At least :data:`MINIMUM_OBSERVATIONS` runs, of different sizes, all timed
        the same way and all measuring the same work. Runs taken with a profiler
        attached are fine as long as *every* run was, since the profiler's charge
        per call scales with the calls and mostly cancels in the exponent; mixing
        profiled and unprofiled runs does not, and there is nothing here that can
        detect it.
    minimum_r_squared : float, optional
        How good the fit has to be before an exponent is returned rather than a
        refusal.
    status : str, optional
        The status of the timings the observations came from. ``measured`` when a
        clock produced them, which is the normal case; anything weaker is carried
        through, because a fit cannot be better founded than what it was fitted
        to.

    Returns
    -------
    ScalingFit
        The exponent with its goodness of fit, or a refusal naming what would
        resolve it. Refused when there are too few runs, when the sizes are too
        close together to tell a line from a curve, when a size or a duration is
        not positive and therefore has no logarithm, or when the fit is worse
        than ``minimum_r_squared``.

    Examples
    --------
    A linear workload, and the reading that follows from it:

    >>> linear = [Observation(size=n, seconds=0.01 * n) for n in (100, 400, 1600)]
    >>> fit = fit_power_law(linear)
    >>> round(fit.exponent.value, 3), round(fit.r_squared, 6)
    (1.0, 1.0)
    >>> fit.reading == _LINEAR_READING
    True

    A quadratic one, which is the case a linear projection gets wrong:

    >>> fit = fit_power_law([Observation(n, 1e-6 * n * n) for n in (50, 200, 800)])
    >>> round(fit.exponent.value, 3)
    2.0

    And the refusals, each naming what it needs:

    >>> fit_power_law([Observation(1.0, 1.0), Observation(2.0, 2.0)]).refused
    True
    >>> "orders of magnitude" in fit_power_law(
    ...     [Observation(100, 1), Observation(101, 1.01), Observation(102, 1.02)]
    ... ).exponent.notes
    True
    >>> fit_power_law([Observation(n, 0.0) for n in (1, 10, 100)]).refused
    True
    """
    kept = tuple(observations)

    if len(kept) < MINIMUM_OBSERVATIONS:
        return _refusal(
            f"{len(kept)} timed run(s) is not enough to fit a scaling exponent; "
            f"{MINIMUM_OBSERVATIONS} of different sizes are needed, because two "
            "points fit a straight line exactly and so rule nothing out.",
            kept,
        )

    for observation in kept:
        size, seconds = float(observation.size), float(observation.seconds)
        if not (math.isfinite(size) and math.isfinite(seconds)):
            return _refusal(
                "A run reported a size or a duration that is not a finite number, "
                "so no curve can be fitted through it.",
                kept,
            )
        if size <= 0.0 or seconds <= 0.0:
            return _refusal(
                f"A run of size {size:g} took {seconds:g} s. A power law is fitted "
                "on logarithms, so every size and every duration has to be above "
                "zero; a run too short for the clock to resolve needs a larger "
                "slice, not a smaller one.",
                kept,
            )

    sizes = [float(observation.size) for observation in kept]
    smallest, largest = min(sizes), max(sizes)
    if largest / smallest < MINIMUM_SIZE_RATIO:
        return _refusal(
            f"The sizes run span a factor of {largest / smallest:.2f}, from "
            f"{smallest:g} to {largest:g}. Telling a line from a curve needs them "
            f"to span at least {MINIMUM_SIZE_RATIO:g}, and ideally orders of "
            "magnitude; over a range this narrow every exponent fits about as "
            "well as every other.",
            kept,
        )

    # Least squares on log-log axes: the slope is the exponent, the intercept is
    # the logarithm of the coefficient.
    log_sizes = [math.log(size) for size in sizes]
    log_seconds = [math.log(float(observation.seconds)) for observation in kept]
    count = float(len(kept))
    mean_x = sum(log_sizes) / count
    mean_y = sum(log_seconds) / count
    covariance = sum(
        (x - mean_x) * (y - mean_y) for x, y in zip(log_sizes, log_seconds, strict=True)
    )
    variance = sum((x - mean_x) ** 2 for x in log_sizes)
    if variance <= 0.0:  # pragma: no cover - the size-ratio guard above catches this.
        return _refusal("Every run was the same size, so there is no trend to fit.", kept)

    exponent = covariance / variance
    intercept = mean_y - exponent * mean_x

    residual = sum(
        (y - (intercept + exponent * x)) ** 2 for x, y in zip(log_sizes, log_seconds, strict=True)
    )
    total = sum((y - mean_y) ** 2 for y in log_seconds)
    # A perfectly flat set of durations has nothing to explain, so the fit
    # explains all of it: constant cost is a real answer, and an exponent of zero
    # is what it looks like.
    r_squared = 1.0 if total <= 0.0 else max(0.0, 1.0 - residual / total)

    if r_squared < minimum_r_squared:
        return _refusal(
            f"A power law explains only {r_squared:.2f} of the variation across "
            f"{len(kept)} runs, below the {minimum_r_squared:.2f} required. The "
            "slices are not measuring one consistent behaviour — a cache warming "
            "up, a schedule that changes shape, or a machine doing something else "
            "at the time — so no exponent from them would describe the run.",
            kept,
        )

    # A fit cannot be better founded than the timings it was fitted to, and it is
    # not weakened by being a fit: it is a summary of measurements, like watts
    # from an energy counter over a duration.
    carried = status if status_strength(status) <= status_strength(MEASURED) else MEASURED
    return ScalingFit(
        exponent=Quantity(
            value=exponent,
            unit=EXPONENT_UNIT,
            status=carried,
            notes=(
                f"Fitted over {len(kept)} runs of sizes {smallest:g} to {largest:g}, "
                f"R² = {r_squared:.3f}."
            ),
        ),
        coefficient=math.exp(intercept),
        r_squared=r_squared,
        observations=kept,
        method=(
            f"Least squares of log(seconds) on log(size) over {len(kept)} runs: "
            f"seconds = {math.exp(intercept):.4g} × size^{exponent:.3f}."  # noqa: RUF001 -- the multiplication sign is the correct typography
        ),
        reading=_reading_for(exponent),
        limits=(
            f"The exponent was measured between sizes {smallest:g} and {largest:g}. "
            "Outside that range it is an extrapolation like any other.",
            "A cost that changes shape partway through a real run — a learning-rate "
            "schedule that changes batch size, a dataset that stops fitting in "
            "memory — is not visible in slices that all ran before it.",
        ),
    )
