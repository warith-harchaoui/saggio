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

from ...i18n import DEFAULT_LANGUAGE, current_language, languages, phrase, say
from ...i18n import number as localised

#: The phrase that marks an exclusion line as saying idle capacity is *in* the
#: figures, and the words such a line starts with. Both are catalogue keys now:
#: a line written during a French audit has to be recognised by the fold just
#: as an English one is, so the recognisers below check every language rather
#: than one. A list of known-bad strings would have the opposite failure mode —
#: it goes stale in the direction that hides the fault.
_MARKER_KEY: Final[str] = "boundary.included_marker"
_PREFIX_KEY: Final[str] = "boundary.idle_prefix"


def included_marker(code: str = DEFAULT_LANGUAGE) -> str:
    """Return the phrase that says idle capacity is inside the figures.

    Parameters
    ----------
    code : str, optional
        A language tag.

    Returns
    -------
    str
        The phrase, lowercase, as the recognisers compare it.

    Examples
    --------
    >>> included_marker()
    'inside these figures'
    """
    return phrase(_MARKER_KEY, language=code, table="message").strip().lower()


def idle_prefix(code: str = DEFAULT_LANGUAGE) -> str:
    """Return the words an exclusion line about idle capacity starts with.

    Parameters
    ----------
    code : str, optional
        A language tag.

    Returns
    -------
    str
        The prefix, lowercase.

    Examples
    --------
    >>> idle_prefix()
    'idle capacity'
    """
    return phrase(_PREFIX_KEY, language=code, table="message").strip().lower()


#: Kept for the callers that have always imported it, in the authored language.
INCLUDED_MARKER: Final[str] = (
    phrase(_MARKER_KEY, language=DEFAULT_LANGUAGE, table="message").strip().lower()
)


def idle_is_excluded() -> str:
    """Return what the exclusions list says when the power was not measured here.

    A nameplate rating describes a part under load, so a model built on one
    really does price work being done rather than a machine waiting to do it.

    Returns
    -------
    str
        The line, in the language in force.

    Examples
    --------
    >>> idle_is_excluded().startswith("Idle capacity.")
    True
    """
    return say("boundary.idle_excluded")


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
    parts = [say("boundary.whole_machine")]
    if idle is not None:
        # A baseline above the figure it is a baseline for is not a floor under
        # anything: the machine grew quieter, so whatever else was busy stopped.
        # :meth:`saggio.analyze.run.SliceResult.marginal_watts` already refuses
        # the subtraction in that case, and a sentence that went on calling the
        # baseline a floor would contradict the field beside it.
        if watts is not None and idle >= watts:
            parts.append(
                say(
                    "boundary.grew_quieter",
                    idle=localised(f"{idle:.1f} W"),
                    watts=localised(f"{watts:.1f} W"),
                )
            )
        elif watts is not None:
            parts.append(say("boundary.floor_under", idle=localised(f"{idle:.1f} W")))
        else:
            parts.append(say("boundary.already_drawing", idle=localised(f"{idle:.1f} W")))
    if attributed is not None and share is not None:
        against = (
            say("boundary.attributable.against", watts=localised(f"{watts:.1f} W"))
            if watts is not None
            else ""
        )
        parts.append(
            say(
                "boundary.attributable",
                share=localised(f"{share:.0%}"),
                attributed=localised(f"{attributed:.1f} W"),
                against=against,
            )
        )
    parts.append(
        say("boundary.prices_the_machine")
        if idle is not None or attributed is not None
        else say("boundary.nothing_established")
    )
    return " ".join(parts)


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
    >>> idle_exclusion(measured=False) == idle_is_excluded()
    True
    >>> states_idle_is_excluded(idle_exclusion({"idle_watts": 16.0}, measured=True))
    False
    """
    if not measured:
        return idle_is_excluded()
    idle = _number(measurement.get("idle_watts")) if isinstance(measurement, Mapping) else None
    attributed, share = _attribution(measurement)
    # The marker is passed in rather than written into the sentence, so the
    # phrase the fold recognises and the phrase a reader sees cannot drift apart.
    line = say(
        "boundary.idle_included",
        prefix=phrase(_PREFIX_KEY, language=current_language(), table="message"),
        marker=phrase(_MARKER_KEY, language=current_language(), table="message"),
    )
    if idle is not None and watts is not None and idle < watts:
        line += say(
            "boundary.idle_included.floor_within",
            idle=localised(f"{idle:.1f} W"),
            watts=localised(f"{watts:.1f} W"),
        )
    elif idle is not None and watts is not None:
        line += say(
            "boundary.idle_included.floor_above",
            idle=f"{idle:.1f} W",
            watts=f"{watts:.1f} W",
        )
    elif idle is not None:
        line += say("boundary.idle_included.floor_only", idle=localised(f"{idle:.1f} W"))
    line += "."
    if attributed is not None and share is not None:
        line += " " + say(
            "boundary.idle_included.attributable",
            attributed=localised(f"{attributed:.1f} W"),
            share=localised(f"{share:.0%}"),
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
    >>> is_idle_claim(idle_is_excluded())
    True
    >>> is_idle_claim(idle_exclusion({"idle_watts": 9.0}, measured=True, watts=12.0))
    True
    >>> is_idle_claim("The people. Salaries are out of scope.")
    False
    """
    # Every language, not the one in force: a model written during a French
    # audit is rendered and folded by whatever language the next command runs
    # in, and a line it no longer recognises is a line it silently leaves stale
    # — which is the defect the fold was taught to avoid in the first place.
    start = line.strip().lower()
    return any(start.startswith(idle_prefix(code)) for code in languages())


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
    >>> states_idle_is_excluded(idle_is_excluded())
    True
    >>> states_idle_is_excluded("The people. Salaries are out of scope.")
    False
    """
    if not is_idle_claim(line):
        return False
    lowered = line.strip().lower()
    return not any(included_marker(code) in lowered for code in languages())


#: How each field of a measurement block is labelled and what unit it carries.
#: A block is written once and read on four surfaces; a bare ``2.65`` under the
#: heading "attributed watts" is a number a reader has to guess the meaning of,
#: and the guess they make is that it is the figure the costs used.
#: Field to the unit it carries. The label itself is a catalogue key built from
#: the field's own name, so adding a field means adding one sentence and not
#: touching this.
_FIELD_UNITS: Final[dict[str, str]] = {
    "exit_code": "",
    "measured_on": "",
    "power_scope": "",
    "cpu_seconds": " s",
    "fraction_completed": "",
    "idle_watts": " W",
    "marginal_watts": " W",
    "power_note": "",
    "attributed_watts": " W",
    "attributed_scope": "",
    "truncated": "",
    "repeats": "",
}

#: Rendered separately by both reports: the command as a code block, the profile
#: as its own table, the warnings as a list.
_RENDERED_ELSEWHERE: Final[frozenset[str]] = frozenset({"command", "hot_path", "warnings"})

#: Counters whose name has a wording of its own in the catalogue. A counter not
#: listed here is shown under its own key, which is better than a label somebody
#: invented for it.
_NAMED_DOMAINS: Final[tuple[str, ...]] = ("cpu", "gpu", "ane", "memory")


def measurement_rows(
    measurement: Mapping[str, Any] | None, *, skip: tuple[str, ...] = ()
) -> list[tuple[str, str]]:
    """Return a measurement block as labelled rows, in the order it was written.

    Both reports used to render this block with one comprehension that printed
    every scalar and skipped anything nested. Three fields are nested, and all
    three are the ones a reader needs: ``cpu_share`` — the share that is the
    entire justification for the attributed figure printed above it —
    ``power_sources``, and ``power_by_domain``, the only split in a report that
    is measured rather than modelled. The Markdown report, which is what the
    gallery commits beside every model, showed none of them.

    Parameters
    ----------
    measurement : Mapping or None
        The block, as :meth:`saggio.analyze.run.SliceResult.to_mapping` writes it.
    skip : tuple of str, optional
        Keys a caller renders some other way. The HTML report draws
        ``power_by_domain`` as a figure and passes it here.

    Returns
    -------
    list of tuple
        ``(label, value)`` pairs, both already strings.

    Examples
    --------
    >>> measurement_rows({"attributed_watts": 2.65})
    [('attributable to the run', '2.65 W')]
    >>> measurement_rows({"cpu_share": {"share": 0.147}})
    [("the run's share of the machine's processor work", '14.7%')]
    >>> measurement_rows({"power_sources": ["system-on-chip", "memory"]})
    [('counters that answered', 'system-on-chip, memory')]
    """
    if not isinstance(measurement, Mapping):
        return []
    rows: list[tuple[str, str]] = []
    for key, value in measurement.items():
        if key in _RENDERED_ELSEWHERE or key in skip:
            continue
        if key == "cpu_share":
            row = _share_row(value)
        elif key == "power_by_domain":
            row = _domain_row(value)
        elif key == "power_sources":
            row = _sources_row(value)
        elif key == "spread":
            row = _spread_row(value)
        elif isinstance(value, (dict, list)):
            # A block this module does not know how to label is still shown,
            # because the alternative is what this function exists to undo.
            row = (str(key).replace("_", " "), str(value))
        else:
            unit = _FIELD_UNITS.get(key, "")
            label = (
                say(f"boundary.field.{key}") if key in _FIELD_UNITS else str(key).replace("_", " ")
            )
            row = (label, localised(f"{value}{unit}"))
        if row is not None:
            rows.append(row)
    return rows


def _share_row(value: Any) -> tuple[str, str] | None:
    """Return the processor-work share as one labelled row, or ``None``."""
    if not isinstance(value, Mapping):
        return None
    share = _number(value.get("share"))
    if share is None:
        return None
    run = _number(value.get("run_cpu_seconds"))
    machine = _number(value.get("machine_cpu_seconds"))
    detail = (
        say(
            "boundary.row.share_detail",
            run=localised(f"{run:g} s"),
            machine=localised(f"{machine:g} s"),
        )
        if run and machine
        else ""
    )
    return (say("boundary.row.share"), localised(f"{share:.1%}") + detail)


def _domain_row(value: Any) -> tuple[str, str] | None:
    """Return the per-subsystem split as one labelled row, or ``None``."""
    if not isinstance(value, Mapping) or not value:
        return None
    parts = [
        f"{say(f'boundary.domain.{key}') if str(key) in _NAMED_DOMAINS else key} {number:g} W"
        for key, raw in value.items()
        if (number := _number(raw)) is not None
    ]
    return (say("boundary.row.domains"), ", ".join(parts)) if parts else None


def _spread_row(value: Any) -> tuple[str, str] | None:
    """Return how far the repeated figures moved, as one labelled row.

    The whole point of repeating a measurement is this row. A block that
    recorded the spread and rendered it as ``spread | {'runtime_s': ...}`` —
    which is what the generic fallback does to a nested value — would have
    taken the trouble and kept the answer to itself.

    Parameters
    ----------
    value : object
        The ``spread`` block, keyed by figure.

    Returns
    -------
    tuple or None
        ``(label, value)``, or ``None`` when there is nothing to say.

    Examples
    --------
    >>> _spread_row({"runtime_s": {"low": 1.0, "high": 2.0, "relative": 0.5}})
    ('how far the figures moved across those runs', 'runtime 1 s to 2 s (50%)')
    >>> _spread_row({"power_w": {"low": 16.132957, "high": 37.363475}})[1]
    'power 16.13 W to 37.36 W'
    """
    if not isinstance(value, Mapping) or not value:
        return None
    units = {"runtime_s": "s", "power_w": "W", "idle_w": "W", "attributed_w": "W"}
    parts: list[str] = []
    for key, block in value.items():
        if not isinstance(block, Mapping):
            continue
        low, high = _number(block.get("low")), _number(block.get("high"))
        if low is None or high is None:
            continue
        unit = units.get(str(key), "")
        name = say(f"boundary.spread.{key}") if str(key) in units else str(key)
        relative = _number(block.get("relative"))
        width = f" ({relative:.0%})" if relative is not None else ""
        parts.append(f"{name} {low:.4g} {unit} to {high:.4g} {unit}{width}".replace("  ", " "))
    return (say("boundary.row.spread"), ", ".join(parts)) if parts else None


def _sources_row(value: Any) -> tuple[str, str] | None:
    """Return which counters answered as one labelled row, or ``None``."""
    if not isinstance(value, (list, tuple)) or not value:
        return None
    return (say("boundary.row.sources"), ", ".join(str(item) for item in value))
