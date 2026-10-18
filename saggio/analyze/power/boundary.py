"""What a measured power figure covers besides the run it is charged to.

Module summary
--------------
A counter meters hardware, not processes. When a slice is measured on a machine
that is also doing other things, the watts that come back are the machine's, and
a model that prices one unit of work with them has priced the whole machine for
the duration of the run.

That is a legitimate figure — it is the one a meter can see, and the only one it
can see — but it is not the figure a reader assumes. The sentences here say so,
out of what the measurement itself established: the floor the machine was
drawing before the slice started, and the share of the machine's processor work
the slice turned out to be.

They live in one module because three places write them. The auditor writes one
when it runs a slice; :func:`saggio.fold.fold_measurement` writes the same one
when a measurement is folded in by hand; and the exclusions list, which until now
told every reader the opposite, writes the third. A model whose power was read
off a whole machine while its own exclusions claimed idle capacity was out was
asserting something its own measurement block refuted — by a factor of eleven in
``examples/walkthrough/5-run.yaml``, which carried 31.9 W as the price and 2.9 W
as the attributable share.

Usage example
-------------
>>> scope = workload_scope({"idle_watts": 16.0, "attributed_watts": 4.5,
...                         "cpu_share": {"share": 0.19}}, watts=23.7)
>>> "whole machine" in scope
True

Author
------
Warith Harchaoui
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Final

#: The phrase that marks an exclusion line as saying idle capacity is *in* the
#: figures. It is declared here, beside the function that writes it, so that a
#: new phrasing which forgets to say so is caught rather than quietly accepted.
#: A list of known-bad strings would have the opposite failure mode: it goes
#: stale in the direction that hides the fault.
INCLUDED_MARKER: Final[str] = "inside these figures"

_WHOLE_MACHINE: Final[str] = (
    "This is the whole machine's draw, not this run's alone: these counters "
    "meter hardware and not processes, so whatever else the machine was doing "
    "while the command ran is inside the figure."
)

_GREW_QUIETER: Final[str] = (
    " The machine was drawing {idle:.1f} W before the slice and {watts:.1f} W "
    "during it, so it grew quieter while the slice ran: whatever else was busy "
    "stopped, and the baseline bounds nothing about this figure."
)

_NOTHING_ESTABLISHED: Final[str] = (
    " Nothing here established how much of it was, so treat the figure as an "
    "upper bound on what the run cost and not as what it cost."
)

_PRICES_THE_MACHINE: Final[str] = (
    " Every cost derived from it therefore prices the machine, not the process."
)

#: What the exclusions list says when the power figure was not read off this
#: machine. A nameplate rating describes a part under load, so a model built on
#: one really does price work being done rather than a machine waiting to do it.
IDLE_IS_EXCLUDED: Final[str] = (
    "Idle capacity. This is the cost of one unit of work, not of being ready."
)


def _number(value: Any) -> float | None:
    """Return ``value`` as a float, or ``None`` when it is not a number.

    Parameters
    ----------
    value : object
        Anything read out of a measurement mapping, which is plain YAML and may
        hold a string, ``None``, or a nested block where a number was expected.

    Returns
    -------
    float or None
        The number, or ``None``.

    Examples
    --------
    >>> _number(3), _number("3"), _number(None)
    (3.0, None, None)
    """
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def _attribution(measurement: Mapping[str, Any] | None) -> tuple[float | None, float | None]:
    """Return the attributable watts and the share they came from.

    Parameters
    ----------
    measurement : Mapping or None
        A measurement block as
        :meth:`saggio.analyze.run.SliceResult.to_mapping` writes it.

    Returns
    -------
    tuple
        ``(attributed_watts, share)``, each ``None`` where the block does not
        carry it. The two travel together because a watt figure without the
        share that produced it is a number nobody can argue with.

    Examples
    --------
    >>> _attribution({"attributed_watts": 4.5, "cpu_share": {"share": 0.19}})
    (4.5, 0.19)
    >>> _attribution(None)
    (None, None)
    """
    if not isinstance(measurement, Mapping):
        return None, None
    attributed = _number(measurement.get("attributed_watts"))
    share_block = measurement.get("cpu_share")
    share = _number(share_block.get("share")) if isinstance(share_block, Mapping) else None
    return attributed, share


def workload_scope(
    measurement: Mapping[str, Any] | None = None, *, watts: float | None = None
) -> str:
    """Return the sentence saying what a measured power figure covers.

    The hardware boundary — which counters answered, and what silicon they see —
    is already in :attr:`saggio.analyze.power.PowerReading.scope`. This is the
    other boundary, the one that was missing: how much of the metered hardware
    was doing *this* work.

    Parameters
    ----------
    measurement : Mapping or None, optional
        The measurement block, which may carry ``idle_watts``,
        ``attributed_watts`` and ``cpu_share``. Without it the sentence says the
        figure is the machine's and that nothing established how much of it was
        the run, which is the honest reading of a measurement that recorded no
        floor and no share.
    watts : float or None, optional
        The figure the sentence is about, so the attributable share can be
        quoted against the total it is a share of.

    Returns
    -------
    str
        One to three sentences, ready to follow the hardware scope in a
        quantity's notes.

    Examples
    --------
    >>> workload_scope().endswith("not as what it cost.")
    True
    >>> "16.0 W" in workload_scope({"idle_watts": 16.0})
    True
    >>> "19%" in workload_scope({"attributed_watts": 4.5,
    ...                          "cpu_share": {"share": 0.19}}, watts=23.7)
    True
    """
    idle = _number(measurement.get("idle_watts")) if isinstance(measurement, Mapping) else None
    attributed, share = _attribution(measurement)
    parts = [_WHOLE_MACHINE]
    if idle is not None:
        # A baseline above the figure it is a baseline for is not a floor under
        # anything: the machine grew quieter, so whatever else was busy stopped.
        # :meth:`saggio.analyze.run.SliceResult.marginal_watts` already refuses
        # the subtraction in that case, and a sentence that went on calling the
        # baseline a floor would contradict the field beside it.
        if watts is not None and idle >= watts:
            parts.append(_GREW_QUIETER.format(idle=idle, watts=watts))
        elif watts is not None:
            parts.append(
                f" The machine was already drawing {idle:.1f} W before the slice "
                f"started, which is a floor under how much of the figure was not "
                f"this run."
            )
        else:
            parts.append(f" The machine was already drawing {idle:.1f} W before the slice started.")
    if attributed is not None and share is not None:
        against = f" of the {watts:.1f} W" if watts is not None else ""
        parts.append(
            f" By the run's {share:.0%} share of the machine's processor work, "
            f"{attributed:.1f} W{against} is attributable to it."
        )
    if idle is None and attributed is None:
        parts.append(_NOTHING_ESTABLISHED)
    else:
        parts.append(_PRICES_THE_MACHINE)
    return "".join(parts)


def idle_exclusion(
    measurement: Mapping[str, Any] | None = None,
    *,
    measured: bool,
    watts: float | None = None,
) -> str:
    """Return the exclusion line that is true of this model's power figure.

    Parameters
    ----------
    measurement : Mapping or None, optional
        The measurement block, used for the floor and the attributable share.
    measured : bool
        Whether the power figure was read off this machine. When it was, idle
        capacity is in the figures and saying otherwise is false; when it was
        not, the figure is a nameplate rating and the old line holds.
    watts : float or None, optional
        The power figure, quoted beside the floor so the two can be compared.

    Returns
    -------
    str
        One line for the model's ``exclusions`` list.

    Examples
    --------
    >>> idle_exclusion(measured=False) == IDLE_IS_EXCLUDED
    True
    >>> states_idle_is_excluded(idle_exclusion({"idle_watts": 16.0}, measured=True))
    False
    """
    if not measured:
        return IDLE_IS_EXCLUDED
    idle = _number(measurement.get("idle_watts")) if isinstance(measurement, Mapping) else None
    attributed, share = _attribution(measurement)
    line = (
        f"Idle capacity is {INCLUDED_MARKER}, not outside them. The power was "
        "read from the machine's own counters, which meter hardware and not "
        "processes"
    )
    if idle is not None and watts is not None and idle < watts:
        line += f", and {idle:.1f} W of the {watts:.1f} W was being drawn before the slice started"
    elif idle is not None and watts is not None:
        line += (
            f", and the machine was drawing {idle:.1f} W before the slice against "
            f"{watts:.1f} W during it"
        )
    elif idle is not None:
        line += f", and {idle:.1f} W was being drawn before the slice started"
    line += "."
    if attributed is not None and share is not None:
        line += (
            f" The measurement block carries {attributed:.1f} W as the run's "
            f"attributable share, from its {share:.0%} of the machine's "
            f"processor work; the costs below do not use it."
        )
    return line


def is_idle_claim(line: str) -> bool:
    """Return whether an exclusion line is about idle capacity at all.

    This is the question :func:`saggio.fold._rewrite_idle_exclusion` has to ask.
    Asking the narrower one — whether the line claims idle is *out* — meant a
    second measurement folded into the same model left the first measurement's
    watts standing in a line nobody would re-read, because the line no longer
    matched the predicate that had rewritten it once.

    Parameters
    ----------
    line : str
        One entry from a model's ``exclusions`` list.

    Returns
    -------
    bool
        ``True`` for a line about idle capacity, whichever way it reads.

    Examples
    --------
    >>> is_idle_claim(IDLE_IS_EXCLUDED)
    True
    >>> is_idle_claim(idle_exclusion({"idle_watts": 9.0}, measured=True, watts=12.0))
    True
    >>> is_idle_claim("The people. Salaries are out of scope.")
    False
    """
    return line.strip().lower().startswith("idle capacity")


def states_idle_is_excluded(line: str) -> bool:
    """Return whether an exclusion line tells a reader idle capacity is out.

    Parameters
    ----------
    line : str
        One entry from a model's ``exclusions`` list.

    Returns
    -------
    bool
        ``True`` when the line is about idle capacity and does not say it is in.

    Examples
    --------
    >>> states_idle_is_excluded(IDLE_IS_EXCLUDED)
    True
    >>> states_idle_is_excluded("The people. Salaries are out of scope.")
    False
    """
    if not is_idle_claim(line):
        return False
    return INCLUDED_MARKER not in line.strip().lower()
