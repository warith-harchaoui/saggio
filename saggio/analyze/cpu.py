"""
What share of the machine's processor work this run actually was.

Module summary
--------------
A counter measures the machine. The baseline in :mod:`saggio.analyze.run`
answers that by watching the machine before the slice starts and subtracting,
which works and rests on something nobody checked: that the rest of the machine
kept doing what it was doing. This module answers the same question a second
way, and the second way does not need that assumption.

Every operating system that will tell you anything keeps a running total of
processor time, machine-wide, split into what it spent working and what it spent
idle. Read it before the slice and after, and the difference is how many
processor-seconds the whole machine spent working while the slice ran. The slice
already knows its own, from ``RUSAGE_CHILDREN``. The ratio is its share of the
work, and multiplying the measured draw by that share attributes the draw rather
than subtracting a floor from it.

This is how Kepler and GreenAlgorithms4HPC split a node's energy between the
things running on it, and the two answers are worth having together: the
baseline one is right when the machine was quiet, the share one is right when it
was busy, and when they disagree the disagreement is the finding.

One limit, stated here because it decides what the number may be used for. A
share of *processor* work is a claim about *processor* energy. An accelerator's
draw is not proportional to anything in this file: a run that keeps a GPU busy
while using almost no processor time would be attributed almost none of the
machine's energy, which would be wrong by the size of the GPU. The share is
reported for what it is, and never applied to an accelerator figure.

Linux publishes the totals in ``/proc/stat``, in clock ticks. macOS publishes
them through the Mach call ``host_processor_info``, per logical processor, which
answers an ordinary user. Those are the two platforms this package supports, and
the absence of any third readable total is one of the reasons why.

Usage example
-------------
>>> from saggio.analyze.cpu import machine_cpu_seconds
>>> total = machine_cpu_seconds()
>>> total is None or total > 0.0
True

Author
------
Warith Harchaoui
"""

from __future__ import annotations

import ctypes
import ctypes.util
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Final

#: Where Linux keeps the machine-wide processor totals.
PROC_STAT: Final[Path] = Path("/proc/stat")

#: ``PROCESSOR_CPU_LOAD_INFO``, the flavour of :c:func:`host_processor_info`
#: that returns per-processor tick counts.
_PROCESSOR_CPU_LOAD_INFO: Final[int] = 2

#: How many states that flavour returns per processor: user, system, idle, nice.
_CPU_STATES: Final[int] = 4

#: macOS reports those ticks at a hundred to the second, independently of
#: ``SC_CLK_TCK``, which is also a hundred on every build this runs on but is a
#: different constant and would be the wrong one to reach for.
_DARWIN_TICKS_PER_SECOND: Final[float] = 100.0

#: Below this many processor-seconds of machine-wide work, the difference
#: between two readings is mostly the resolution of the counter rather than the
#: work. A tenth of a second across a dozen processors is a handful of ticks.
MINIMUM_MACHINE_SECONDS: Final[float] = 0.5


def _linux_cpu_seconds() -> float | None:
    """Return busy processor-seconds since boot, from ``/proc/stat``.

    Idle and I/O wait are excluded: a processor waiting on a disk is not doing
    work anybody should be charged for, and counting it would shrink every
    share by whatever the machine happened to be waiting on.

    Returns
    -------
    float or None
        Busy processor-seconds, or ``None`` when the file is absent or
        unreadable.

    Examples
    --------
    >>> _linux_cpu_seconds() is None or _linux_cpu_seconds() > 0.0
    True
    """
    try:
        first = PROC_STAT.read_text(encoding="utf-8").split("\n", 1)[0]
    except OSError:
        return None
    fields = first.split()
    if not fields or fields[0] != "cpu":
        return None
    try:
        ticks = [int(field) for field in fields[1:]]
    except ValueError:
        return None
    if len(ticks) < 4:
        return None
    # user, nice, system, idle, iowait, irq, softirq, steal, ...
    idle = ticks[3] + (ticks[4] if len(ticks) > 4 else 0)
    busy = sum(ticks) - idle
    per_second = os.sysconf("SC_CLK_TCK")
    if not per_second or per_second <= 0:
        return None
    return busy / float(per_second)


def _darwin_cpu_seconds() -> float | None:
    """Return busy processor-seconds since boot, from ``host_processor_info``.

    Reached through ``ctypes`` so this costs no dependency, the same way
    :mod:`saggio.analyze.apple` reaches ``IOReport``. Every failure path returns
    ``None``: a library that will not load, a call that fails, a kernel that
    changes the shape of what it returns.

    Returns
    -------
    float or None
        Busy processor-seconds, or ``None`` when the call did not answer.

    Examples
    --------
    >>> _darwin_cpu_seconds() is None or _darwin_cpu_seconds() > 0.0
    True
    """
    name = ctypes.util.find_library("c")
    if name is None:  # pragma: no cover - a libc-less machine.
        return None
    try:
        libc = ctypes.CDLL(name, use_errno=True)
        libc.mach_host_self.restype = ctypes.c_uint
        host = libc.mach_host_self()
        processors = ctypes.c_uint(0)
        info = ctypes.POINTER(ctypes.c_int)()
        count = ctypes.c_uint(0)
        result = libc.host_processor_info(
            host,
            _PROCESSOR_CPU_LOAD_INFO,
            ctypes.byref(processors),
            ctypes.byref(info),
            ctypes.byref(count),
        )
    except (OSError, AttributeError, ValueError):  # pragma: no cover - defensive.
        return None
    if result != 0 or not processors.value:
        return None
    if count.value < processors.value * _CPU_STATES:  # pragma: no cover - shape change.
        return None
    # Per processor: user, system, idle, nice. Everything but idle is work.
    ticks = 0
    for processor in range(processors.value):
        base = processor * _CPU_STATES
        ticks += info[base] + info[base + 1] + info[base + 3]
    return ticks / _DARWIN_TICKS_PER_SECOND


def machine_cpu_seconds() -> float | None:
    """Return how many processor-seconds this machine has spent working.

    Machine-wide and since boot, so only differences between two readings mean
    anything. Idle is excluded on both platforms.

    Returns
    -------
    float or None
        Busy processor-seconds, or ``None`` on a platform that does not publish
        them to an ordinary process. Windows is that platform here.

    Examples
    --------
    >>> total = machine_cpu_seconds()
    >>> total is None or total > 0.0
    True
    """
    if sys.platform.startswith("linux"):
        return _linux_cpu_seconds()
    if sys.platform == "darwin":
        return _darwin_cpu_seconds()
    return None


def unavailable_reason() -> str:
    """Return why this machine cannot report its own processor time.

    Returns
    -------
    str
        One sentence, naming the platform and what it does not publish.

    Examples
    --------
    >>> "processor time" in unavailable_reason()
    True
    """
    if sys.platform.startswith("linux"):
        return f"{PROC_STAT} does not publish machine-wide processor time here."
    if sys.platform == "darwin":
        return "host_processor_info did not answer, so machine-wide processor time is unknown."
    return (
        f"{sys.platform} is not a platform this package supports, so it reads no "
        "machine-wide processor time here. saggio supports Linux and macOS."
    )


@dataclass(frozen=True, slots=True)
class CpuShare:
    """What share of the machine's processor work one run was.

    Parameters
    ----------
    share : float or None
        The run's processor-seconds over the machine's, in ``(0, 1]``, or
        ``None`` when it could not be established.
    run_seconds : float or None
        Processor-seconds the run itself used.
    machine_seconds : float or None
        Processor-seconds the whole machine used over the same window.
    reason : str or None
        Why there is no share, when there is none.

    Examples
    --------
    >>> CpuShare(share=0.5, run_seconds=1.0, machine_seconds=2.0).known()
    True
    >>> CpuShare(reason="no counter").known()
    False
    """

    share: float | None = None
    run_seconds: float | None = None
    machine_seconds: float | None = None
    reason: str | None = None

    def known(self) -> bool:
        """Return whether a share was established.

        Returns
        -------
        bool
            True when there is a number to use.

        Examples
        --------
        >>> CpuShare(share=0.25).known()
        True
        """
        return self.share is not None

    def to_mapping(self) -> dict[str, object]:
        """Serialise the share for the model's measurement block.

        Returns
        -------
        dict
            Plain numbers and prose. The share is diagnostic context about how
            the run was attributed, not a cost, so it is not a quantity.

        Examples
        --------
        >>> sorted(CpuShare(share=0.5, run_seconds=1.0, machine_seconds=2.0).to_mapping())
        ['machine_cpu_seconds', 'run_cpu_seconds', 'share']
        """
        mapping: dict[str, object] = {}
        if self.share is not None:
            mapping["share"] = round(self.share, 6)
        if self.run_seconds is not None:
            mapping["run_cpu_seconds"] = round(self.run_seconds, 3)
        if self.machine_seconds is not None:
            mapping["machine_cpu_seconds"] = round(self.machine_seconds, 3)
        if self.reason:
            mapping["unknown_because"] = self.reason
        return mapping


@dataclass(slots=True)
class CpuShareMeter:
    """Reads the machine's processor total before a run and after it.

    Parameters
    ----------
    started_at : float or None
        The opening reading, or ``None`` when this machine publishes none.

    Examples
    --------
    >>> meter = CpuShareMeter.start()
    >>> isinstance(meter, CpuShareMeter)
    True
    """

    started_at: float | None

    @classmethod
    def start(cls) -> CpuShareMeter:
        """Take the opening reading.

        Returns
        -------
        CpuShareMeter
            A meter holding whatever the machine was willing to say.

        Examples
        --------
        >>> CpuShareMeter.start().started_at is None or True
        True
        """
        return cls(started_at=machine_cpu_seconds())

    def stop(self, *, run_cpu_seconds: float | None) -> CpuShare:
        """Close the reading and return the run's share of the work.

        Parameters
        ----------
        run_cpu_seconds : float or None
            Processor time the run itself used, from ``RUSAGE_CHILDREN``.

        Returns
        -------
        CpuShare
            The share, or a refusal naming what stopped it. Refused when the
            machine publishes no total, when the run's own processor time is
            unknown, when the window was too short for the counter's resolution
            to mean anything, or when the run appears to have used more
            processor time than the machine did — which is not a share, it is a
            sign that one of the two numbers is not what it is supposed to be.

        Examples
        --------
        >>> CpuShareMeter(started_at=None).stop(run_cpu_seconds=1.0).known()
        False
        """
        if self.started_at is None:
            return CpuShare(reason=unavailable_reason())
        if run_cpu_seconds is None:
            return CpuShare(
                reason=(
                    "The run's own processor time is unknown on this platform, so its "
                    "share of the machine's cannot be worked out."
                )
            )
        ended_at = machine_cpu_seconds()
        if ended_at is None or ended_at < self.started_at:
            return CpuShare(
                run_seconds=run_cpu_seconds,
                reason=(
                    "The machine's processor total did not read back, or went "
                    "backwards, so there is no window to compare against."
                ),
            )
        machine = ended_at - self.started_at
        if machine < MINIMUM_MACHINE_SECONDS:
            return CpuShare(
                run_seconds=run_cpu_seconds,
                machine_seconds=machine,
                reason=(
                    f"The machine did {machine:.3f} processor-seconds of work while this "
                    f"ran, below the {MINIMUM_MACHINE_SECONDS:g} s needed for the "
                    "difference to be work rather than the counter's resolution. "
                    "Measure a longer slice."
                ),
            )
        if run_cpu_seconds > machine:
            return CpuShare(
                run_seconds=run_cpu_seconds,
                machine_seconds=machine,
                reason=(
                    f"The run reports {run_cpu_seconds:.3f} processor-seconds and the "
                    f"machine {machine:.3f}, which cannot both be right: a part cannot "
                    "exceed the whole. One of the two counters is measuring something "
                    "other than what it is being read as, so no share is reported."
                ),
            )
        return CpuShare(
            share=run_cpu_seconds / machine,
            run_seconds=run_cpu_seconds,
            machine_seconds=machine,
        )
