"""
The carbon that was emitted before the machine was ever switched on.

Module summary
--------------
Everything else in this package measures or estimates what a run *draws*. None
of it counts what it cost to *build* the thing the run drew through. For a
training job on a recent accelerator that omission is not a rounding error:
manufacturing one HGX H100 baseboard emits 1,312 kgCO2e before it has computed
anything, and a model that reports only the electricity is quietly claiming
that figure is zero.

The arithmetic is the Software Carbon Intensity specification's, ISO/IEC
21031:2024:

    SCI = (E x I + M) per R

``E x I`` is energy times grid intensity, which is the operational carbon this
package already computes. ``R`` is the functional unit, which is this package's
unit of work by construction. ``M`` is the piece that was missing, and the
specification defines it as

    M = TE x TS x RS

the total embodied emissions of the hardware, times the share of its life the
run reserved, times the share of the hardware it reserved.

Three decisions are worth stating, because each of them could have gone the
other way and a reader has to know which way it went.

**The time share is calendar time, not busy time.** ``TS`` is the run's duration
over the hardware's expected lifespan, exactly as the specification writes it.
A card that sits idle for half its life therefore charges that half to nobody.
The common alternative — amortising over busy hours only, so the work that
happens carries all of the embodied carbon — gives a larger number and is not
what the standard says. This package follows the standard and says so in the
note it attaches.

**The lifespan is not in the catalogue.** Every vendor product carbon footprint
here is explicitly cradle-to-gate and excludes the use phase, which means the
vendor has told us the numerator and deliberately not told us the denominator.
How long a card stays in service is a fact about a fleet, not about a part, so
it is an assumption the model states and this module refuses without. Published
figures cluster between three and six years, and that range alone moves the
answer by a factor of two.

**An unpriced part gives a TODO, not a zero.** A catalogue row with no embodied
figure means nobody has read a product carbon footprint for that part, not that
building it was free.

Usage example
-------------
>>> from saggio.estimate.embodied import embodied_carbon
>>> from saggio.model import Quantity
>>> total = Quantity(value=164.0, unit="kgCO2e", status="estimated")
>>> life = Quantity(value=4.0, unit="years", status="estimated")
>>> run = Quantity(value=3600.0, unit="s", status="measured")
>>> round(embodied_carbon(embodied=total, lifetime=life, runtime=run).value, 3)
4.677

Author
------
Warith Harchaoui
"""

from __future__ import annotations

from typing import Final

from ..model.quantity import Quantity
from ..model.taxonomy import TODO, weakest

#: Where the arithmetic comes from.
SCI_SOURCE: Final[str] = (
    "Software Carbon Intensity (SCI) specification, ISO/IEC 21031:2024, "
    "https://sci.greensoftware.foundation/"
)

#: Hours in a year, for turning a lifespan into the same units as a runtime.
#: 365.25 days, so that a four-year life spans the leap day it would contain.
HOURS_PER_YEAR: Final[float] = 365.25 * 24.0

#: Grams in a kilogram. Vendor footprints are published in kilograms; every
#: carbon figure in this package is in grams, and mixing the two silently would
#: be a thousandfold error in the direction that flatters.
GRAMS_PER_KILOGRAM: Final[float] = 1000.0

#: Said on every figure this module produces, because the choice it records is
#: not the only defensible one.
_CALENDAR_NOTE: Final[str] = (
    "Amortised over calendar life, as the SCI specification defines the time "
    "share: idle time is charged to nobody. Amortising over busy hours instead "
    "would give a larger figure and is not what the standard says."
)


def _hours(duration: Quantity) -> float | None:
    """Return a duration in hours, whatever unit it was written in.

    Parameters
    ----------
    duration : Quantity
        A runtime in seconds, minutes, hours, days, or years.

    Returns
    -------
    float or None
        The duration in hours, or ``None`` when the unit is not one this
        module knows how to convert. Guessing would turn a unit nobody checked
        into a number everybody believes.

    Examples
    --------
    >>> _hours(Quantity(value=3600.0, unit="s", status="measured"))
    1.0
    >>> _hours(Quantity(value=2.0, unit="years", status="estimated"))
    17532.0
    >>> _hours(Quantity(value=1.0, unit="furlongs", status="estimated")) is None
    True
    """
    if not duration.is_known():
        return None
    value = float(duration.value)
    unit = (duration.unit or "").strip().lower()
    if unit in {"s", "sec", "secs", "second", "seconds"}:
        return value / 3600.0
    if unit in {"min", "mins", "minute", "minutes"}:
        return value / 60.0
    if unit in {"h", "hr", "hrs", "hour", "hours"}:
        return value
    if unit in {"d", "day", "days"}:
        return value * 24.0
    if unit in {"y", "yr", "yrs", "year", "years"}:
        return value * HOURS_PER_YEAR
    return None


def embodied_carbon(
    *,
    embodied: Quantity,
    lifetime: Quantity,
    runtime: Quantity,
    resource_share: Quantity | None = None,
) -> Quantity:
    """Return the manufacturing carbon one unit of work is answerable for.

    ``M = TE x TS x RS``, where the time share is the run's duration over the
    hardware's expected lifespan and the resource share is the fraction of the
    hardware the run reserved.

    Parameters
    ----------
    embodied : Quantity
        What building the hardware emitted, in ``kgCO2e``, for the whole of
        whatever the figure covers — one card, or one baseboard, as long as the
        resource share is expressed against the same thing.
    lifetime : Quantity
        How long the hardware is expected to stay in service. Not a catalogue
        value: every vendor footprint here excludes the use phase on purpose, so
        the vendor has given the numerator and withheld the denominator.
    runtime : Quantity
        How long one unit of work reserves the hardware.
    resource_share : Quantity or None, optional
        The fraction of the hardware the run reserved, in the interval
        ``(0, 1]``. ``None`` means all of it, which is the ordinary case for a
        per-device figure.

    Returns
    -------
    Quantity
        Grams of CO2 equivalent per unit of work, naming its inputs, or a
        ``TODO`` carrying the reason there is no figure. Never stronger than
        ``estimated``: a measured runtime multiplied by a published footprint is
        an inference about a part, not a reading off this machine.

    Examples
    --------
    An hour on an H100 whose share of one baseboard's footprint is 164 kg, over
    a four-year life:

    >>> hour = Quantity(value=1.0, unit="h", status="measured")
    >>> life = Quantity(value=4.0, unit="years", status="estimated")
    >>> card = Quantity(value=164.0, unit="kgCO2e", status="estimated")
    >>> figure = embodied_carbon(embodied=card, lifetime=life, runtime=hour)
    >>> round(figure.value, 3), figure.unit, figure.status
    (4.677, 'gCO2e', 'estimated')

    Half a card, half the carbon:

    >>> half = Quantity(value=0.5, unit="ratio", status="estimated")
    >>> round(embodied_carbon(embodied=card, lifetime=life, runtime=hour,
    ...                       resource_share=half).value, 3)
    2.339

    And the refusals, each saying what would close it:

    >>> nothing = Quantity(unit="kgCO2e", status="TODO")
    >>> embodied_carbon(embodied=nothing, lifetime=life, runtime=hour).status
    'TODO'
    >>> zero_life = Quantity(value=0.0, unit="years", status="estimated")
    >>> "lifespan" in embodied_carbon(embodied=card, lifetime=zero_life,
    ...                               runtime=hour).notes
    True
    """
    if not embodied.is_known():
        return Quantity(
            unit="gCO2e",
            status=TODO,
            notes=(
                "No product carbon footprint is on file for this hardware, so the "
                "carbon of building it is open. Nobody has read one for this part; "
                "that is not the same as it having been free to build. Add an "
                "`embodied_kgco2e` to the catalogue row with the footprint's own URL "
                "and the date it was read."
            ),
        )

    lifetime_hours = _hours(lifetime)
    if lifetime_hours is None or lifetime_hours <= 0.0:
        return Quantity(
            unit="gCO2e",
            status=TODO,
            notes=(
                "The hardware's expected lifespan is not stated, so there is nothing "
                "to amortise over. Every vendor footprint here is cradle-to-gate and "
                "excludes the use phase on purpose: the vendor gave the numerator and "
                "withheld the denominator. State `assumptions.hardware_lifetime`; "
                "published figures cluster between three and six years, and that range "
                "alone moves this number by a factor of two."
            ),
        )

    run_hours = _hours(runtime)
    if run_hours is None or run_hours < 0.0:
        return Quantity(
            unit="gCO2e",
            status=TODO,
            notes=(
                "The runtime of one unit of work is not known in a unit this can "
                "convert, so the share of the hardware's life it reserved is open."
            ),
        )

    share = 1.0
    if resource_share is not None:
        if not resource_share.is_known():
            return Quantity(
                unit="gCO2e",
                status=TODO,
                notes=(
                    "A resource share was offered and carries no number, so what "
                    "fraction of the hardware this work reserved is open."
                ),
            )
        share = float(resource_share.value)
        if not 0.0 < share <= 1.0:
            return Quantity(
                unit="gCO2e",
                status=TODO,
                notes=(
                    f"A resource share of {share!r} is outside (0, 1]: a unit of work "
                    "cannot reserve a negative part of a machine, nor more of one than "
                    "there is."
                ),
            )

    time_share = run_hours / lifetime_hours
    grams = float(embodied.value) * GRAMS_PER_KILOGRAM * time_share * share
    return Quantity(
        value=grams,
        unit="gCO2e",
        status=weakest("estimated", embodied.status, lifetime.status),
        notes=(
            f"M = TE x TS x RS: {embodied.value:g} kgCO2e of manufacturing, times "
            f"{run_hours:g} h over a {lifetime_hours / HOURS_PER_YEAR:.2f}-year life, "
            f"times a resource share of {share:g}. {_CALENDAR_NOTE}"
        ),
    )


def software_carbon_intensity(*, operational: Quantity, embodied: Quantity) -> Quantity:
    """Return the SCI score: operational plus embodied, per unit of work.

    The specification's ``(E x I + M) per R``. Both halves are already per unit
    of work here — ``R`` is this package's unit of work — so the score is their
    sum, and the sum is only as well founded as the weaker half.

    Parameters
    ----------
    operational : Quantity
        Grid emissions for the energy the run drew, in ``gCO2e``.
    embodied : Quantity
        Manufacturing emissions amortised onto the run, in ``gCO2e``.

    Returns
    -------
    Quantity
        The score, or a ``TODO`` when either half is open. A score that silently
        dropped the open half would be an understatement wearing the authority
        of a standard.

    Examples
    --------
    >>> operational = Quantity(value=26.9, unit="gCO2e", status="estimated")
    >>> made = Quantity(value=4.7, unit="gCO2e", status="estimated")
    >>> score = software_carbon_intensity(operational=operational, embodied=made)
    >>> round(score.value, 1), score.status
    (31.6, 'estimated')
    >>> open_half = Quantity(unit="gCO2e", status="TODO")
    >>> software_carbon_intensity(operational=operational, embodied=open_half).status
    'TODO'
    """
    if not operational.is_known() or not embodied.is_known():
        missing = "operational" if not operational.is_known() else "embodied"
        return Quantity(
            unit="gCO2e",
            status=TODO,
            notes=(
                f"The {missing} half of this score is open, so the score is. SCI is "
                "the sum of both; reporting one of them under the name of the "
                "standard would understate it with the standard's authority."
            ),
        )
    return Quantity(
        value=float(operational.value) + float(embodied.value),
        unit="gCO2e",
        status=weakest(operational.status, embodied.status),
        notes=(f"SCI = (E x I + M) per R, where R is this model's unit of work. {SCI_SOURCE}"),
    )
