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

The processor is rarely the expensive part. On the workloads this package exists
for, the accelerator draws several times what the package does, and NVIDIA's
driver reports it without privileges on Linux and on Windows alike, either as an
accumulating energy counter or as an instantaneous board wattage that can be
sampled across the run. Both paths are read here, the counter first because it is
a counter, and whichever one answers says so in the scope it carries. A machine
that answers on one side and not the other reports the side it measured and names
the side it did not, because a package figure presented as the cost of a training
run would be wrong by an order of magnitude.

Usage example
-------------
>>> from saggio.analyze.power import PowerMeter
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
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
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


#: The program NVIDIA ships with its driver, and the only way to ask a board what
#: it is drawing without linking against the management library.
NVIDIA_SMI: Final[str] = "nvidia-smi"

#: Millijoules in a joule. The driver's energy counter is published in millijoules.
_MILLIJOULES_PER_JOULE: Final[float] = 1000.0

#: How often the sampling fallback asks the board what it is drawing. Half a
#: second is short enough to follow a training step and long enough that the
#: sampler costs nothing measurable next to the run it is watching.
_SAMPLE_INTERVAL_MS: Final[int] = 500

#: Below this many samples there is no mean worth the name, and a single reading
#: taken at an arbitrary instant is not an average over a run.
_MINIMUM_SAMPLES: Final[int] = 2

#: How long to wait for the driver to answer a one-shot question before deciding
#: it is not going to. A healthy driver answers in milliseconds; a wedged one
#: must not hold up a measurement.
_QUERY_TIMEOUT_SECONDS: Final[float] = 5.0

#: What the accelerator counter covers, carried into the model so a reader knows
#: the boundary of the figure.
ACCELERATOR_COUNTER_SCOPE: Final[str] = (
    "the whole accelerator board, from the driver's accumulated energy counter"
)

#: What the sampled figure covers, and how it was obtained, because a mean of
#: samples and a counter difference are not the same kind of number.
ACCELERATOR_SAMPLED_SCOPE: Final[str] = (
    "the whole accelerator board, as the mean of {count} readings of instantaneous "
    "board power taken every {interval:g} seconds across the run"
)

#: Said when the processor and the accelerator both answered, replacing the note
#: about undercounting, which stops being true the moment the board is included.
_BOTH_MEASURED_NOTE: Final[str] = (
    "The figure is the processor package and the accelerator board added "
    "together. What neither counter sees is the rest of the machine: memory "
    "outside the package, storage, fans, and the power supply's own losses."
)

#: Said when the accelerator was measured and the processor was not, so that
#: nobody reads an accelerator figure as the draw of the whole machine.
_PACKAGE_MISSING_NOTE: Final[str] = (
    "The processor package is not included: no readable counter on this machine, "
    "so the figure is the accelerator alone and understates the total."
)

#: Said when the processor was measured and the accelerator was not.
_ACCELERATOR_MISSING_NOTE: Final[str] = (
    "No NVIDIA accelerator answered, so nothing outside the processor package is included."
)


def _query_nvidia_smi(field_name: str) -> list[str] | None:
    """Ask the NVIDIA driver one question about every board, or return ``None``.

    Parameters
    ----------
    field_name : str
        The query field, as ``nvidia-smi --help-query-gpu`` spells it.

    Returns
    -------
    list of str or None
        One raw answer per board, or ``None`` when there is no driver to ask,
        the driver did not answer, or a board answered that it does not know.

    Examples
    --------
    >>> answers = _query_nvidia_smi("power.draw")
    >>> answers is None or all(isinstance(answer, str) for answer in answers)
    True
    """
    if shutil.which(NVIDIA_SMI) is None:
        return None
    try:
        completed = subprocess.run(  # noqa: S603 - a fixed argument list, never a shell.
            [
                NVIDIA_SMI,
                f"--query-gpu={field_name}",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=_QUERY_TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if completed.returncode != 0:
        return None
    answers = [line.strip() for line in completed.stdout.splitlines() if line.strip()]
    if not answers:
        return None
    # A board that does not implement the field answers "[N/A]" rather than
    # failing. Half an answer across two boards is not an answer about the
    # machine, so one unsupported board voids the query.
    if any(answer.startswith("[") for answer in answers):
        return None
    return answers


def read_accelerator_energy_millijoules() -> int | None:
    """Return the accelerators' accumulated energy, or ``None``.

    Every board present is summed, so a machine with eight of them is counted
    whole. The counter runs from the moment the driver loaded, which makes it the
    accelerator's exact equivalent of the processor package counter: two readings
    and a duration give an average that owes nothing to sampling.

    Returns
    -------
    int or None
        Millijoules since the driver loaded, or ``None`` when no board reports
        the counter.

    Examples
    --------
    >>> value = read_accelerator_energy_millijoules()
    >>> value is None or value >= 0
    True
    """
    answers = _query_nvidia_smi("total_energy_consumption")
    if answers is None:
        return None
    try:
        return sum(int(float(answer)) for answer in answers)
    except ValueError:
        return None


@dataclass(slots=True)
class AcceleratorSampler:
    """A driver process logging board power for the length of a run.

    Older drivers and most consumer boards publish what they are drawing right
    now and keep no running total. The honest answer there is a mean of readings
    taken across the run, which is what this collects: the driver does its own
    timing in its own process, writing to a file rather than a pipe so that a run
    long enough to matter cannot fill a buffer and stall behind it.

    Parameters
    ----------
    process : subprocess.Popen
        The logging process, running until the measured run is over.
    log_path : pathlib.Path
        Where it is writing its readings.

    Examples
    --------
    >>> AcceleratorSampler.start() is None or True
    True
    """

    process: subprocess.Popen[str]
    log_path: Path = field(default_factory=Path)

    @classmethod
    def start(cls) -> AcceleratorSampler | None:
        """Begin logging, or return ``None`` when there is nothing to log.

        Returns
        -------
        AcceleratorSampler or None
            A running sampler, or ``None`` when no driver answered.

        Examples
        --------
        >>> sampler = AcceleratorSampler.start()
        >>> sampler is None or sampler.stop() is not None
        True
        """
        if _query_nvidia_smi("power.draw") is None:
            return None
        handle = tempfile.NamedTemporaryFile(
            mode="w", suffix=".watts", prefix="saggio-", delete=False, encoding="utf-8"
        )
        log_path = Path(handle.name)
        try:
            process = subprocess.Popen(  # noqa: S603 - a fixed argument list, never a shell.
                [
                    NVIDIA_SMI,
                    "--query-gpu=power.draw",
                    "--format=csv,noheader,nounits",
                    f"-lms={_SAMPLE_INTERVAL_MS}",
                ],
                stdout=handle,
                stderr=subprocess.DEVNULL,
                text=True,
            )
        except (OSError, subprocess.SubprocessError):
            handle.close()
            log_path.unlink(missing_ok=True)
            return None
        return cls(process=process, log_path=log_path)

    def stop(self) -> tuple[float, int] | None:
        """Stop logging and return the mean board power and how many readings it is.

        Returns
        -------
        tuple of (float, int), or None
            Mean watts across every board and every reading, with the number of
            readings it was averaged over, or ``None`` when too few arrived to
            average. The count travels with the mean because a mean of four
            readings and a mean of four thousand deserve different trust, and the
            reader cannot tell them apart from the number alone.

        Examples
        --------
        >>> sampler = AcceleratorSampler.start()
        >>> sampler is None or sampler.stop() is None or True
        True
        """
        try:
            self.process.terminate()
            self.process.wait(timeout=_QUERY_TIMEOUT_SECONDS)
        except (OSError, subprocess.SubprocessError):
            self.process.kill()
        try:
            lines = self.log_path.read_text(encoding="utf-8").splitlines()
        except OSError:
            lines = []
        finally:
            self.log_path.unlink(missing_ok=True)
        readings: list[float] = []
        for line in lines:
            for cell in line.split(","):
                try:
                    readings.append(float(cell.strip()))
                except ValueError:
                    # "[N/A]" and the driver's own noise. A line that is not a
                    # number is not a reading, and pretending otherwise would
                    # drag the mean towards a figure nobody measured.
                    continue
        if len(readings) < _MINIMUM_SAMPLES:
            return None
        return sum(readings) / len(readings), len(readings)


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
    sources : tuple of str
        Which counters answered, named the way a reader would name them. A
        figure that covers the processor alone and one that covers the processor
        and the accelerator are different figures, and a model that carries the
        second without saying so invites the reader to compare two numbers that
        were never about the same hardware.

    Examples
    --------
    >>> PowerReading(None, None, "no counter").measured()
    False
    >>> PowerReading(300.0, 600.0, "board", ("accelerator",)).sources
    ('accelerator',)
    """

    watts: float | None
    joules: float | None
    scope: str
    sources: tuple[str, ...] = ()

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
    """The counters on this machine, read before and after a run.

    Parameters
    ----------
    started_at : int or None
        The processor package counter when the run began, or ``None`` when there
        is no such counter on this machine.
    accelerator_started_at : int or None
        The accelerators' accumulated energy when the run began, or ``None``
        when no board keeps a running total.
    sampler : AcceleratorSampler or None
        A driver process logging board power, started only when no accumulated
        counter was available to read instead.

    Examples
    --------
    >>> PowerMeter.start().stop(seconds=0.0).measured()
    False
    """

    started_at: int | None
    accelerator_started_at: int | None = None
    sampler: AcceleratorSampler | None = None

    @classmethod
    def start(cls) -> PowerMeter:
        """Take the opening readings.

        The accumulated accelerator counter is preferred over sampling, and the
        sampler is only started when that counter is absent, so a machine that
        keeps a running total is never asked to log half a million readings.

        Returns
        -------
        PowerMeter
            A meter holding whatever this machine was willing to say, which on
            some machines is nothing.

        Examples
        --------
        >>> isinstance(PowerMeter.start(), PowerMeter)
        True
        """
        accelerator_started_at = read_accelerator_energy_millijoules()
        return cls(
            started_at=read_package_energy_microjoules(),
            accelerator_started_at=accelerator_started_at,
            sampler=None if accelerator_started_at is not None else AcceleratorSampler.start(),
        )

    def _package_joules(self) -> tuple[float | None, str | None]:
        """Return the package energy over the run, or the reason there is none."""
        if self.started_at is None:
            return None, unavailable_reason()
        ended_at = read_package_energy_microjoules()
        if ended_at is None or ended_at < self.started_at:
            return None, (
                "The package energy counter wrapped or reset during the run, "
                "so the difference is not a measurement."
            )
        return (ended_at - self.started_at) / _MICROJOULES_PER_JOULE, None

    def _accelerator_watts(self, *, seconds: float) -> tuple[float | None, str | None]:
        """Return the mean accelerator power over the run, and how it was obtained."""
        if self.accelerator_started_at is not None:
            ended_at = read_accelerator_energy_millijoules()
            if ended_at is None or ended_at < self.accelerator_started_at:
                return None, None
            joules = (ended_at - self.accelerator_started_at) / _MILLIJOULES_PER_JOULE
            return joules / seconds, ACCELERATOR_COUNTER_SCOPE
        if self.sampler is None:
            return None, None
        sampled = self.sampler.stop()
        if sampled is None:
            return None, None
        mean_watts, count = sampled
        # The sampler writes one line per board per tick, so on a machine with
        # eight boards the count of readings is eight times the count of ticks.
        # The sentence says readings, which is what was counted.
        return mean_watts, ACCELERATOR_SAMPLED_SCOPE.format(
            count=count, interval=_SAMPLE_INTERVAL_MS / 1000.0
        )

    def stop(self, *, seconds: float) -> PowerReading:
        """Take the closing readings and return the average power over the run.

        Parameters
        ----------
        seconds : float
            Wall-clock duration of the run, which the caller timed.

        Returns
        -------
        PowerReading
            The measured average of whatever answered, naming what it covers and
            what it leaves out. A counter that went backwards, which happens when
            it wraps or the machine resets it, yields no number for that counter:
            a wrapped delta is not a measurement, and reporting it as one would be
            worse than admitting there is none.

        Examples
        --------
        >>> PowerMeter(started_at=None).stop(seconds=1.0).watts is None
        True
        >>> PowerMeter(started_at=0).stop(seconds=0.0).watts is None
        True
        """
        if seconds <= 0.0:
            if self.sampler is not None:
                self.sampler.stop()
            return PowerReading(
                None, None, "The run was too short to divide energy by its duration."
            )

        package_joules, package_reason = self._package_joules()
        accelerator_watts, accelerator_scope = self._accelerator_watts(seconds=seconds)

        sources: list[str] = []
        scopes: list[str] = []
        watts = 0.0
        if package_joules is not None:
            sources.append("processor package")
            watts += package_joules / seconds
        if accelerator_watts is not None:
            sources.append("accelerator")
            scopes.append(f"The accelerator figure covers {accelerator_scope}.")
            watts += accelerator_watts

        if not sources:
            return PowerReading(None, None, package_reason or unavailable_reason())

        if accelerator_watts is None:
            # RAPL_SCOPE_NOTE is about what the package counter misses, which is
            # only worth saying when nothing else made up for it.
            scopes.insert(0, RAPL_SCOPE_NOTE)
            scopes.append(_ACCELERATOR_MISSING_NOTE)
        elif package_joules is None:
            scopes.append(_PACKAGE_MISSING_NOTE)
        else:
            scopes.insert(0, _BOTH_MEASURED_NOTE)

        return PowerReading(
            watts=watts,
            joules=watts * seconds,
            scope=" ".join(scopes),
            sources=tuple(sources),
        )
