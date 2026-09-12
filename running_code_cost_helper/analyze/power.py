"""
Reading power from the machine instead of guessing it.

Module summary
--------------
A wattage taken from a datasheet is a guess about a chip; a wattage taken from a
counter is a fact about a run. This module is the thin layer over whatever the
operating system will tell us, and its whole contract is that it returns ``None``
rather than a plausible number when it cannot tell.

Linux exposes Intel's running average power limit counters through sysfs as an
accumulating microjoule total, readable without privileges once the files are.
Two readings and a duration give an average. The counter covers the processor
package only, so on a GPU workload it undercounts, and the caller says so.

macOS exposes the same kind of figure through ``powermetrics``, which requires
administrator rights and therefore cannot be a library call; Windows exposes
nothing comparable without a vendor driver. On both, this module reports that it
could not measure, and the estimate that follows is labelled as an estimate.

Usage example
-------------
>>> from running_code_cost_helper.analyze.power import PowerMeter
>>> meter = PowerMeter.start()
>>> reading = meter.stop(seconds=1.0)
>>> reading.watts is None or reading.watts >= 0.0
True

Author
------
Warith Harchaoui
"""

from __future__ import annotations

import glob
from dataclasses import dataclass
from typing import Final

import os_helper as osh

#: Where Linux publishes the processor package energy counters.
RAPL_ENERGY_GLOB: Final[str] = "/sys/class/powercap/intel-rapl:*/energy_uj"

#: Microjoules in a joule, spelled out so the unit conversion reads as physics.
_MICROJOULES_PER_JOULE: Final[float] = 1_000_000.0

#: What the counter covers, carried into the model so a reader knows the boundary.
RAPL_SCOPE_NOTE: Final[str] = (
    "Intel RAPL counts the processor package only: a discrete accelerator's draw "
    "is not included, so a GPU workload measured this way is undercounted."
)

#: Why no measurement was possible, by platform, phrased so the reader knows it is
#: a property of the machine rather than a failure of the tool.
_UNAVAILABLE_REASON: Final[dict[str, str]] = {
    "darwin": (
        "macOS publishes package power only through powermetrics, which needs "
        "administrator rights and so cannot be read from a library call."
    ),
    "windows": (
        "Windows exposes no vendor-neutral package energy counter, so power here "
        "is estimated from the hardware catalogue rather than measured."
    ),
    "linux": (
        "No readable Intel RAPL counter was found: this is an AMD or ARM machine, "
        "a container without the sysfs files, or the files are not world-readable."
    ),
}


def read_package_energy_microjoules() -> int | None:
    """Return the accumulated processor package energy, or ``None``.

    Every package domain present is summed, so a two-socket machine is counted
    whole rather than by half.

    Returns
    -------
    int or None
        Microjoules since boot, or ``None`` when no counter could be read.

    Examples
    --------
    >>> value = read_package_energy_microjoules()
    >>> value is None or value >= 0
    True
    """
    paths = glob.glob(RAPL_ENERGY_GLOB)
    if not paths:
        return None
    total = 0
    read_any = False
    for path in paths:
        try:
            with open(path, encoding="utf-8") as handle:
                total += int(handle.read().strip())
            read_any = True
        except (OSError, ValueError):
            # One unreadable domain should not void a readable one. If none read,
            # the check below returns None and the caller estimates instead.
            continue
    return total if read_any else None


def unavailable_reason() -> str:
    """Return why this machine cannot report measured power.

    Returns
    -------
    str
        A sentence naming the platform limitation, written into the model so a
        reader does not have to wonder why a figure says ``estimated``.

    Examples
    --------
    >>> "power" in unavailable_reason() or "counter" in unavailable_reason()
    True
    """
    if osh.macos():
        return _UNAVAILABLE_REASON["darwin"]
    if osh.windows():
        return _UNAVAILABLE_REASON["windows"]
    return _UNAVAILABLE_REASON["linux"]


@dataclass(frozen=True, slots=True)
class PowerReading:
    """The outcome of trying to measure power across a run.

    Parameters
    ----------
    watts : float or None
        Average watts over the interval, or ``None`` when nothing was measured.
    joules : float or None
        Energy consumed over the interval, or ``None``.
    scope : str
        What the figure covers, or why there is none.

    Examples
    --------
    >>> PowerReading(None, None, "no counter").measured()
    False
    """

    watts: float | None
    joules: float | None
    scope: str

    def measured(self) -> bool:
        """Return whether a real figure was obtained.

        Returns
        -------
        bool
            ``True`` when a counter produced a number.

        Examples
        --------
        >>> PowerReading(12.0, 24.0, "RAPL").measured()
        True
        """
        return self.watts is not None


@dataclass(slots=True)
class PowerMeter:
    """A pair of counter readings around a run.

    Parameters
    ----------
    started_at : int or None
        The counter value when the run began, or ``None`` when there is no
        counter on this machine.

    Examples
    --------
    >>> PowerMeter.start().stop(seconds=0.0).measured()
    False
    """

    started_at: int | None

    @classmethod
    def start(cls) -> PowerMeter:
        """Take the opening reading.

        Returns
        -------
        PowerMeter
            A meter holding the starting counter value, or holding ``None`` when
            the machine has no counter to read.

        Examples
        --------
        >>> isinstance(PowerMeter.start(), PowerMeter)
        True
        """
        return cls(started_at=read_package_energy_microjoules())

    def stop(self, *, seconds: float) -> PowerReading:
        """Take the closing reading and return the average power over the run.

        Parameters
        ----------
        seconds : float
            Wall-clock duration of the run, which the caller timed.

        Returns
        -------
        PowerReading
            The measured average, or a reading with no number and the reason.
            A counter that went backwards, which happens when it wraps or the
            machine resets it, yields no number: a wrapped delta is not a
            measurement, and reporting it as one would be worse than admitting
            there is none.

        Examples
        --------
        >>> PowerMeter(started_at=None).stop(seconds=1.0).watts is None
        True
        >>> PowerMeter(started_at=0).stop(seconds=0.0).watts is None
        True
        """
        if self.started_at is None:
            return PowerReading(None, None, unavailable_reason())
        if seconds <= 0.0:
            return PowerReading(
                None, None, "The run was too short to divide energy by its duration."
            )
        ended_at = read_package_energy_microjoules()
        if ended_at is None or ended_at < self.started_at:
            return PowerReading(
                None,
                None,
                "The package energy counter wrapped or reset during the run, "
                "so the difference is not a measurement.",
            )
        joules = (ended_at - self.started_at) / _MICROJOULES_PER_JOULE
        return PowerReading(watts=joules / seconds, joules=joules, scope=RAPL_SCOPE_NOTE)
