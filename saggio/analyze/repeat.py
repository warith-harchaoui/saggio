"""Running a slice more than once, because one run bounds nothing.

Module summary
--------------
A single measurement tells you what happened once. It does not tell you whether
it would happen again, and the two figures a slice produces do not behave the
same way at all.

This package's own gallery proved it. ``examples/render.yaml`` was measured
twice, on one machine, with not a line of the measured code changed between
them. The runtime moved **2.3%**; everything derived from the power moved
**76.6%**, far enough that ``saggio diff`` failed its own gate on its own
flagship model. The runtime is a property of the work. The wattage is a
property of the room — a counter meters the machine, so it reports whatever
else the machine was doing, and that is not the same thing twice.

Both figures carried the same word, ``measured``, in a four-state vocabulary
whose entire proposition is saying how far a number can be trusted. A state
that cannot tell 2% from 77% is not doing that job.

So: run it ``N`` times and say the spread. No fifth status is invented here —
inventing one before measuring the thing it would describe is how the problem
started. What is added is a number beside the number: the range the figure
moved across the repeats, written into the model and stated in the notes of
every quantity the repeats bound.

The value written into the model is one real run's — the one whose runtime is
the median — and not a median assembled per field. A model's figures have to be
mutually consistent: its energy is its runtime times its power, and medians
taken from different runs would describe a run that never happened.

Usage example
-------------
>>> import sys
>>> series = run_slices([sys.executable, "-c", "pass"], repeats=2, profile=False,
...                     baseline_seconds=0.0)
>>> len(series.runs), series.to_mapping()["repeats"]
(2, 2)

Author
------
Warith Harchaoui
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from pathlib import Path
from statistics import median
from typing import Any, Final

from ..i18n import number as localised
from ..i18n import say
from .run import (
    DEFAULT_BASELINE_SECONDS,
    DEFAULT_TIMEOUT_SECONDS,
    SliceResult,
    run_slice,
)

#: A spread wider than this is reported as a warning rather than left to a
#: reader to notice. It is the threshold ``saggio diff`` gates on, deliberately:
#: a figure that moves this much between two runs of unchanged code would fail
#: that gate, and a reader is better told before they commit it than after.
WIDE_SPREAD: Final[float] = 0.10

#: Why a repeated measurement has no function-level profile, and what a single
#: run can say about its own repeatability, which is nothing. Both are catalogue
#: keys: they end up in a model file, and a model written during a French audit
#: should read as French throughout.
_PROFILE_SKIPPED_KEY: Final[str] = "repeat.profile_skipped"
_MEASURED_ONCE_KEY: Final[str] = "repeat.measured_once"


def measured_once() -> str:
    """Return what one run says about how far a second would move.

    Returns
    -------
    str
        The sentence, in the language in force.

    Examples
    --------
    >>> measured_once().startswith("Measured once")
    True
    """
    return say(_MEASURED_ONCE_KEY)


@dataclass(frozen=True, slots=True)
class Spread:
    """What one figure did across several runs of the same command.

    Parameters
    ----------
    values : tuple of float
        One value per run, in the order the runs happened.

    Examples
    --------
    >>> Spread((1.0, 2.0, 3.0)).median
    2.0
    >>> round(Spread((1.0, 2.0, 3.0)).relative, 2)
    1.0
    """

    values: tuple[float, ...]

    @property
    def low(self) -> float:
        """Return the smallest value seen.

        Returns
        -------
        float
            The minimum.

        Examples
        --------
        >>> Spread((3.0, 1.0)).low
        1.0
        """
        return min(self.values)

    @property
    def high(self) -> float:
        """Return the largest value seen.

        Returns
        -------
        float
            The maximum.

        Examples
        --------
        >>> Spread((3.0, 1.0)).high
        3.0
        """
        return max(self.values)

    @property
    def median(self) -> float:
        """Return the middle value.

        Returns
        -------
        float
            The median, which is what the model carries.

        Examples
        --------
        >>> Spread((1.0, 5.0, 2.0)).median
        2.0
        """
        return float(median(self.values))

    @property
    def relative(self) -> float | None:
        """Return the range as a fraction of the median, or ``None``.

        Returns
        -------
        float or None
            ``(high - low) / median``, and ``None`` where the median is zero,
            because a proportion of nothing is not a proportion.

        Examples
        --------
        >>> Spread((0.0, 0.0)).relative is None
        True
        """
        middle = self.median
        if middle == 0.0:
            return None
        return (self.high - self.low) / middle

    def outside_odds(self) -> float:
        """Return how often the next run would land outside this range.

        Exactly ``2 / (n + 1)``, and that is a fact rather than an estimate.
        Among ``n + 1`` exchangeable draws from any continuous distribution,
        each is equally likely to be the largest, so the new one is a fresh
        maximum with probability ``1 / (n + 1)``; the same holds for the
        minimum; and it cannot be both. No shape is assumed and none is fitted.

        The one thing it does assume is that nothing changed between the runs —
        which is the very proposition a drift gate is testing, so this is the
        rate at which such a gate cries wolf on unchanged work.

        Returns
        -------
        float
            A probability in ``(0, 1]``. Five runs give ``1/3``; to halve it,
            roughly double the runs.

        Examples
        --------
        >>> Spread((1.0, 2.0, 3.0, 4.0, 5.0)).outside_odds()
        0.3333333333333333
        >>> round(Spread(tuple(float(n) for n in range(11))).outside_odds(), 4)
        0.1667
        """
        return 2.0 / (len(self.values) + 1)

    def wide(self) -> bool:
        """Return whether this spread would fail the drift gate.

        Returns
        -------
        bool
            ``True`` when the range exceeds :data:`WIDE_SPREAD` of the median.

        Examples
        --------
        >>> Spread((1.0, 1.5)).wide()
        True
        >>> Spread((1.0, 1.01)).wide()
        False
        """
        relative = self.relative
        return relative is not None and relative > WIDE_SPREAD

    def to_mapping(self) -> dict[str, Any]:
        """Serialise the spread for the model's measurement block.

        Returns
        -------
        dict
            The three figures a reader needs and the per-run values they came
            from, so the claim can be checked rather than taken.

        Examples
        --------
        >>> sorted(Spread((1.0, 2.0)).to_mapping())
        ['high', 'low', 'median', 'outside_odds', 'relative', 'runs']
        """
        relative = self.relative
        return {
            "outside_odds": round(self.outside_odds(), 4),
            "low": round(self.low, 6),
            "median": round(self.median, 6),
            "high": round(self.high, 6),
            "relative": round(relative, 4) if relative is not None else None,
            "runs": [round(value, 6) for value in self.values],
        }


@dataclass(frozen=True, slots=True)
class SliceSeries:
    """Several runs of one command, and what they agreed about.

    Parameters
    ----------
    runs : tuple of SliceResult
        The runs, in the order they happened. At least one.

    Examples
    --------
    >>> from saggio.analyze.power import PowerReading
    >>> one = SliceResult(("x",), 0, 1.0, PowerReading(10.0, 10.0, "soc"))
    >>> two = SliceResult(("x",), 0, 2.0, PowerReading(20.0, 20.0, "soc"))
    >>> SliceSeries((one, two)).representative().wall_seconds
    1.0
    """

    runs: tuple[SliceResult, ...]

    def representative(self) -> SliceResult:
        """Return the run whose figures the model should carry.

        Returns
        -------
        SliceResult
            The run with the median runtime — the lower of the two middle runs
            when there is an even number, so the choice is deterministic. One
            real run rather than a median per field, because a model's energy is
            its runtime times its power and mixing runs would state a pair that
            never occurred together.

        Examples
        --------
        >>> from saggio.analyze.power import PowerReading
        >>> runs = tuple(SliceResult(("x",), 0, s, PowerReading(None, None, ""))
        ...              for s in (3.0, 1.0, 2.0))
        >>> SliceSeries(runs).representative().wall_seconds
        2.0
        """
        ordered = sorted(self.runs, key=lambda run: run.wall_seconds)
        return ordered[(len(ordered) - 1) // 2]

    def runtime_spread(self) -> Spread:
        """Return what the wall-clock time did across the runs.

        Returns
        -------
        Spread
            One value per run.

        Examples
        --------
        >>> from saggio.analyze.power import PowerReading
        >>> runs = (SliceResult(("x",), 0, 1.0, PowerReading(None, None, "")),)
        >>> SliceSeries(runs).runtime_spread().values
        (1.0,)
        """
        return Spread(tuple(run.wall_seconds for run in self.runs))

    def power_spread(self) -> Spread | None:
        """Return what the measured power did across the runs, or ``None``.

        Returns
        -------
        Spread or None
            ``None`` unless every run measured power. A spread over the runs
            that answered would be a spread of a different population from the
            runtime's, and reporting the two side by side as though they covered
            the same runs is the kind of quiet mismatch this package exists to
            refuse.

        Examples
        --------
        >>> from saggio.analyze.power import PowerReading
        >>> runs = (SliceResult(("x",), 0, 1.0, PowerReading(None, None, "")),)
        >>> SliceSeries(runs).power_spread() is None
        True
        """
        watts = [run.power.watts for run in self.runs]
        if any(value is None for value in watts):
            return None
        return Spread(tuple(float(value) for value in watts if value is not None))

    def idle_spread(self) -> Spread | None:
        """Return what the machine's floor did across the runs, or ``None``.

        Each run in a series takes its own baseline, so the floors are five
        separate readings of a thing that moves. Only the representative run's
        was written down, which meant the one comparison this package most
        needs to make — is subtracting the floor more or less stable than
        attributing by domain? — could not be made from a committed model.

        Returns
        -------
        Spread or None
            ``None`` unless every run measured a floor, for the same reason
            :meth:`power_spread` withholds a partial one.

        Examples
        --------
        >>> from saggio.analyze.power import PowerReading
        >>> runs = (SliceResult(("x",), 0, 1.0, PowerReading(9.0, 9.0, "soc")),)
        >>> SliceSeries(runs).idle_spread() is None
        True
        """
        floors = [run.baseline.watts if run.baseline else None for run in self.runs]
        if any(value is None for value in floors):
            return None
        return Spread(tuple(float(value) for value in floors if value is not None))

    def attributed_spread(self) -> Spread | None:
        """Return what the domain attribution did across the runs, or ``None``.

        The third of the three answers, and the reason all three are recorded:
        a model that names one of them as its method should let a reader see
        how the other two behaved on the same five runs.

        Returns
        -------
        Spread or None
            ``None`` unless every run produced an attributable figure.

        Examples
        --------
        >>> from saggio.analyze.power import PowerReading
        >>> runs = (SliceResult(("x",), 0, 1.0, PowerReading(9.0, 9.0, "soc")),)
        >>> SliceSeries(runs).attributed_spread() is None
        True
        """
        shares = [run.attributed_watts() for run in self.runs]
        if any(value is None for value in shares):
            return None
        return Spread(tuple(float(value) for value in shares if value is not None))

    def warnings(self) -> list[str]:
        """Return what a reader must know before trusting the figures.

        Returns
        -------
        list of str
            One sentence per figure that moved more than the drift gate allows,
            naming the range rather than only the fact of it.

        Examples
        --------
        >>> from saggio.analyze.power import PowerReading
        >>> runs = tuple(SliceResult(("x",), 0, s, PowerReading(s, s, "soc"))
        ...              for s in (1.0, 2.0))
        >>> len(SliceSeries(runs).warnings())
        2
        """
        if len(self.runs) < 2:
            return []
        spreads: dict[str, Any] = {"runtime_s": self.runtime_spread().to_mapping()}
        power = self.power_spread()
        if power is not None:
            spreads["power_w"] = power.to_mapping()
        # Through the same function a contract test calls on a committed file,
        # so the warning a model carries and the warning its own numbers produce
        # cannot drift apart without something failing.
        return spread_warnings({"repeats": len(self.runs), "spread": spreads})

    def with_warning(self, warning: str) -> SliceSeries:
        """Return the series with one more sentence on its representative run.

        Parameters
        ----------
        warning : str
            What a reader must know. Attached to the run the model will carry,
            because that is the run whose block gets written.

        Returns
        -------
        SliceSeries
            A new series; this one is not modified.

        Examples
        --------
        >>> from saggio.analyze.power import PowerReading
        >>> one = SliceResult(("x",), 0, 1.0, PowerReading(None, None, ""))
        >>> SliceSeries((one,)).with_warning("read this").runs[0].warnings
        ('read this',)
        """
        chosen = self.representative()
        return SliceSeries(
            tuple(
                replace(run, warnings=(*run.warnings, warning)) if run is chosen else run
                for run in self.runs
            )
        )

    def to_mapping(self) -> dict[str, Any]:
        """Serialise the series as a model's measurement block.

        Returns
        -------
        dict
            The representative run's own block, plus how many runs there were
            and what each figure did across them. A single run produces exactly
            what it produced before, so nothing changes for a caller that did
            not ask for repeats.

        Examples
        --------
        >>> from saggio.analyze.power import PowerReading
        >>> one = SliceResult(("x",), 0, 1.0, PowerReading(None, None, ""))
        >>> "repeats" in SliceSeries((one,)).to_mapping()
        False
        """
        mapping = dict(self.representative().to_mapping())
        if len(self.runs) < 2:
            return mapping
        spreads: dict[str, Any] = {"runtime_s": self.runtime_spread().to_mapping()}
        power = self.power_spread()
        if power is not None:
            spreads["power_w"] = power.to_mapping()
        attributed = self.attributed_spread()
        if attributed is not None:
            spreads["attributed_w"] = attributed.to_mapping()
        floors = self.idle_spread()
        if floors is not None:
            # The floors the runs were measured above, which move as much as
            # the totals do. Without them a reader cannot tell whether
            # subtracting one is a steadier answer than attributing by domain.
            spreads["idle_w"] = floors.to_mapping()
        mapping["repeats"] = len(self.runs)
        mapping["spread"] = spreads
        mapping["warnings"] = [*mapping.get("warnings", []), *self.warnings()]
        return mapping


#: The unit each repeated figure carries. What it is *called* is a catalogue
#: key built from the same name.
_SPREAD_UNITS: Final[dict[str, str]] = {"runtime_s": "s", "power_w": "W"}


def spread_warnings(measurement: Mapping[str, Any] | None) -> list[str]:
    """Return what a repeated measurement obliges a reader to be told.

    Written from the block rather than from the runs, so that the warning a
    committed model carries can be regenerated from that model's own numbers
    and compared with what it says. A sentence stored next to the figures it
    describes, with nothing comparing the two, is the shape every prose fault
    in this repository has had.

    Parameters
    ----------
    measurement : Mapping or None
        A measurement block carrying ``repeats`` and ``spread``.

    Returns
    -------
    list of str
        One sentence per figure that moved more than the drift gate allows,
        naming the range rather than only the fact of it. In the order the
        figures are listed in :data:`_SPREAD_LABELS`, which is the order they
        are written, so two lists can be compared element by element.

    Examples
    --------
    >>> spread_warnings(None)
    []
    >>> block = {"repeats": 2, "spread": {"power_w": {"low": 16.0, "median": 18.0,
    ...          "high": 21.0, "relative": 0.2778}}}
    >>> "16 W to 21 W" in spread_warnings(block)[0]
    True
    """
    if not isinstance(measurement, Mapping):
        return []
    repeats = measurement.get("repeats")
    spreads = measurement.get("spread")
    if not isinstance(repeats, int) or repeats < 2 or not isinstance(spreads, Mapping):
        return []
    found: list[str] = []
    for key, unit in _SPREAD_UNITS.items():
        block = spreads.get(key)
        if not isinstance(block, Mapping):
            continue
        low, high = block.get("low"), block.get("high")
        relative = block.get("relative")
        if not isinstance(low, (int, float)) or not isinstance(high, (int, float)):
            continue
        if not isinstance(relative, (int, float)) or relative <= WIDE_SPREAD:
            continue
        found.append(
            say(
                "repeat.wide",
                figure=say(f"repeat.figure.{key}"),
                low=localised(f"{low:.4g} {unit}"),
                high=localised(f"{high:.4g} {unit}"),
                repeats=repeats,
                relative=localised(f"{relative:.0%}"),
            )
        )
    return found


def _as_odds(probability: float) -> str:
    """Return a probability as the plain phrase a reader can hold.

    Parameters
    ----------
    probability : float
        A number in ``(0, 1]``.

    Returns
    -------
    str
        ``"one time in 3"`` rather than ``"0.3333"``: the figure is about how
        often a reader will be surprised, and a reader counts occasions.

    Examples
    --------
    >>> _as_odds(1 / 3)
    'one time in 3'
    >>> _as_odds(1.0)
    'every time'
    """
    if probability >= 1.0:
        return say("repeat.odds.every_time")
    return say("repeat.odds.one_in", count=round(1.0 / probability))


def spread_note(measurement: Mapping[str, Any] | None, key: str) -> str:
    """Return the sentence bounding how far a figure would move again.

    Parameters
    ----------
    measurement : Mapping or None
        A measurement block, which may carry ``repeats`` and ``spread``.
    key : str
        Which spread to describe: ``"runtime_s"`` or ``"power_w"``.

    Returns
    -------
    str
        One sentence, ready to follow a quantity's own notes. A measurement
        that repeated nothing says so rather than saying nothing: silence
        reads as stability, and this is the figure that is not stable.

    Examples
    --------
    >>> spread_note(None, "runtime_s") == measured_once()
    True
    >>> block = {"repeats": 3, "spread": {"runtime_s":
    ...          {"low": 1.0, "median": 2.0, "high": 3.0, "relative": 1.0}}}
    >>> spread_note(block, "runtime_s").startswith("The median of 3 runs")
    True
    >>> power = {"repeats": 3, "spread": {"power_w":
    ...          {"low": 10.0, "median": 20.0, "high": 30.0, "relative": 1.0}}}
    >>> "is a different run's" in spread_note(power, "power_w")
    True
    """
    if not isinstance(measurement, Mapping):
        return measured_once()
    repeats = measurement.get("repeats")
    spreads = measurement.get("spread")
    if not isinstance(repeats, int) or repeats < 2 or not isinstance(spreads, Mapping):
        return measured_once()
    block = spreads.get(key)
    if not isinstance(block, Mapping):
        return measured_once()
    low, high, relative = block.get("low"), block.get("high"), block.get("relative")
    if not isinstance(low, (int, float)) or not isinstance(high, (int, float)):
        return measured_once()
    unit = " s" if key == "runtime_s" else " W"
    middle = block.get("median")
    width = (
        say("repeat.width", relative=localised(f"{relative:.0%}"))
        if isinstance(relative, float)
        else ""
    )
    if key == "runtime_s":
        # The model carries this figure exactly: the representative run is
        # chosen by runtime, so the runtime it carries is the median one.
        opening = say("repeat.opening.runtime", repeats=repeats)
    else:
        # It does not carry this one. The run the model carries was chosen by
        # its runtime, so the power beside it is that run's power and not the
        # middle of the five — saying "median" here would be false by however
        # far the two happen to differ, which on the gallery's own model is
        # 17.4 W against 19.4 W.
        middling = f" ({middle:.4g}{unit})" if isinstance(middle, (int, float)) else ""
        opening = say("repeat.opening.other", repeats=repeats, middle=middling)
    # What the range is worth, which is a different question from how wide it
    # is. A reader who is told only the width reads it as a bound; it is not
    # one, and the odds say by how much.
    odds = 2.0 / (repeats + 1)
    return say(
        "repeat.ranged",
        opening=opening,
        low=localised(f"{low:.4g}{unit}"),
        high=localised(f"{high:.4g}{unit}"),
        width=width,
        repeats=repeats,
        odds=_as_odds(odds),
    )


def run_slices(
    command: Sequence[str],
    *,
    repeats: int = 1,
    working_directory: str | Path | None = None,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    fraction_completed: float | None = None,
    profile: bool = True,
    baseline_seconds: float = DEFAULT_BASELINE_SECONDS,
) -> SliceSeries:
    """Run a command several times and return every run.

    Parameters
    ----------
    command : sequence of str
        What to run. Passed as a list, never through a shell.
    repeats : int, optional
        How many times. One is the old behaviour exactly.
    working_directory : str or pathlib.Path or None, optional
        Where to run it.
    timeout_seconds : float, optional
        How long to allow each run before stopping it.
    fraction_completed : float or None, optional
        The share of a whole run each covers.
    profile : bool, optional
        Whether to wrap a Python command in the profiler. **Ignored when
        ``repeats`` is above one**, and the series says so. The profiler changes
        what is being timed, so a series with one profiled run and four plain
        ones would report a spread that the profiler put there. Take the profile
        with a single run; take the spread with several.
    baseline_seconds : float, optional
        How long to watch the machine before each run. The baseline is taken
        again for every repeat, because the thing it measures — what else the
        machine is doing — is exactly the thing that changes between them.

    Returns
    -------
    SliceSeries
        Every run, in order. A run that exits non-zero stops the series there:
        measuring a failure five times measures five failures.

    Raises
    ------
    ValueError
        If ``repeats`` is below one, which asks for a measurement of nothing.

    Examples
    --------
    >>> import sys
    >>> series = run_slices([sys.executable, "-c", "pass"], repeats=1,
    ...                     profile=False, baseline_seconds=0.0)
    >>> len(series.runs)
    1
    """
    if repeats < 1:
        raise ValueError(say("repeat.cannot_run", repeats=repeats))
    runs: list[SliceResult] = []
    for _ in range(repeats):
        result = run_slice(
            command,
            working_directory=working_directory,
            timeout_seconds=timeout_seconds,
            fraction_completed=fraction_completed,
            # No run in a series carries the profiler; see the parameter's note.
            profile=profile and repeats == 1,
            baseline_seconds=baseline_seconds,
        )
        runs.append(result)
        if result.exit_code != 0 or result.truncated:
            break
    series = SliceSeries(tuple(runs))
    if profile and repeats > 1:
        return series.with_warning(say(_PROFILE_SKIPPED_KEY))
    return series
