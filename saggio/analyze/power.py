"""
Reading power from the machine instead of guessing it.

Module summary
--------------
A wattage taken from a datasheet is a guess about a chip; a wattage taken from a
counter is a fact about a run. This module is the thin layer over whatever the
operating system will tell us, and its whole contract is that it returns ``None``
rather than a plausible number when it cannot tell.

Linux publishes energy through the powercap tree as accumulating microjoule
totals, one zone per thing that can be metered. Each zone is read by the name it
gives itself rather than by the shape of its directory, which is what separates
a package from the ``psys`` zone that already contains it and from the memory
zone beside it, whose energy is *not* inside the package figure and was
therefore missing from every reading this module took before. Since Linux 5.10
those files are root-only by default, because sampling them quickly is a side
channel; a machine that keeps them shut is told apart from a machine that has no
counters at all, and :mod:`saggio.analyze.capability` prints what it would take to
open them without ever opening them itself.

macOS was the platform this module used to give up on. It should not have been:
the counters ``powermetrics`` prints are published by ``IOReport``, which answers
an ordinary user, and :mod:`saggio.analyze.apple` reads them — processor cores,
graphics cores, neural engine, and memory, as monotonic counters in units the
library labels itself. Windows still publishes no vendor-neutral processor
counter to an unprivileged process, and says so rather than estimating quietly.

The processor is rarely the expensive part. On the workloads this package exists
for, the accelerator draws several times what the package does, and NVIDIA's
driver reports it without privileges on Linux and on Windows alike, either as an
accumulating energy counter or as an instantaneous board wattage that can be
sampled across the run. Both paths are read here, the counter first because it is
a counter, and whichever one answers says so in the scope it carries. A machine
that answers on one side and not the other reports the side it measured and names
the side it did not, because a package figure presented as the cost of a training
run would be wrong by an order of magnitude. Where NVIDIA's driver is not the one
present, Linux's own graphics drivers publish the same thing through sysfs —
``amdgpu`` as instantaneous watts, ``i915`` and ``xe`` as an accumulating
counter — to an ordinary user and with no vendor tool involved.

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
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final

import os_helper as osh

from . import apple

#: Where Linux publishes its energy zones. The pattern covers ``intel-rapl`` and
#: the ``amd-rapl`` control type newer kernels register on AMD parts, and stops
#: short of ``intel-rapl-mmio``, which is the *same* package published through a
#: second interface: adding both would count one processor twice.
RAPL_ZONE_GLOB: Final[str] = "/sys/class/powercap/[ai]*-rapl:*"

#: Where Linux publishes the processor package energy counters.
RAPL_ENERGY_GLOB: Final[str] = "/sys/class/powercap/intel-rapl:*/energy_uj"

#: Microjoules in a joule, spelled out so the unit conversion reads as physics.
_MICROJOULES_PER_JOULE: Final[float] = 1_000_000.0

#: Microwatts in a watt. The graphics drivers publish power in microwatts.
_MICROWATTS_PER_WATT: Final[float] = 1_000_000.0

#: Where the graphics drivers hang their hardware-monitoring nodes.
GRAPHICS_HWMON_GLOB: Final[str] = "/sys/class/drm/card*/device/hwmon/hwmon*"

#: The drivers that publish power there, by the name they write in ``name``.
#: ``amdgpu`` is AMD's; ``i915`` and ``xe`` are Intel's older and newer ones.
GRAPHICS_DRIVERS: Final[frozenset[str]] = frozenset({"amdgpu", "i915", "xe"})

#: The accumulating energy counter, in microjoules, where a driver keeps one.
GRAPHICS_ENERGY_FILE: Final[str] = "energy1_input"

#: The instantaneous board power, in microwatts, where a driver publishes that
#: instead of a total.
GRAPHICS_POWER_FILE: Final[str] = "power1_average"

#: The zone covering the whole system-on-chip rather than the processor alone.
#: When a machine publishes it, it is the better figure and it already contains
#: the packages, so the packages are not added to it.
_PSYS_ZONE: Final[str] = "psys"

#: How a package zone names itself: ``package-0``, ``package-1``, one per socket.
_PACKAGE_PREFIX: Final[str] = "package"

#: How the memory zone names itself. It is a *subzone* of a package in the sysfs
#: tree but its energy is not inside the package figure, so it is read
#: separately and added rather than skipped as a double count.
_DRAM_ZONE: Final[str] = "dram"

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
        "No readable RAPL counter was found: this is an ARM machine, a container "
        "without the sysfs files, or the files are not world-readable."
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

#: What the graphics counter covers, when Linux's own driver keeps a total.
GRAPHICS_COUNTER_SCOPE: Final[str] = (
    "the graphics device, from the driver's own accumulated energy counter in "
    "sysfs, which needs neither a vendor tool nor administrator rights"
)

#: What the sampled graphics figure covers, and how it was obtained.
GRAPHICS_SAMPLED_SCOPE: Final[str] = (
    "the graphics device, as the mean of {count} readings of instantaneous board "
    "power taken from sysfs every {interval:g} seconds across the run"
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

#: Said when the accelerator answered but its counter went backwards mid-run.
_ACCELERATOR_WRAPPED_NOTE: Final[str] = (
    "The accelerator's energy counter wrapped or reset during the run, so its draw "
    "is not included; the board itself did answer."
)

#: Said when the memory counter answered, so a reader knows the figure includes
#: what Green Algorithms would otherwise have estimated from installed capacity.
_MEMORY_MEASURED_NOTE: Final[str] = (
    "Memory is measured rather than estimated here: the machine publishes its own "
    "memory energy counter, so the figure is what the memory drew rather than what "
    "its installed capacity suggests it would draw."
)

#: Said when a package counter passed its ceiling once and was recovered. The
#: sentence carries the wattage above which a *second* wrap would have happened,
#: because that is the one fact that decides whether the recovery is exact.
_WRAP_RECOVERED_NOTE: Final[str] = (
    "The processor energy counter passed its ceiling once during the run and was "
    "unwrapped by its published range. That recovery is exact as long as the "
    "processor averaged under {ceiling:.0f} W, above which the counter would have "
    "passed the ceiling twice and this figure would understate the run."
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
    #: How many boards answer each tick. The log holds one line per board per
    #: tick, so the machine's draw is the per-reading mean times this count;
    #: averaging the raw lines alone would report an eight-board node at the
    #: wattage of one board.
    board_count: int = 1

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
        answers = _query_nvidia_smi("power.draw")
        if answers is None:
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
        return cls(process=process, log_path=log_path, board_count=max(len(answers), 1))

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
        # One line per board per tick, so the per-reading mean is one board's
        # draw; the machine draws that times the boards answering each tick.
        return sum(readings) / len(readings) * self.board_count, len(readings)


def _read_integer(path: Path) -> int | None:
    """Return the integer a sysfs file holds, or ``None``.

    Parameters
    ----------
    path : pathlib.Path
        The file to read.

    Returns
    -------
    int or None
        Its contents as an integer, or ``None`` when it is absent, unreadable,
        or not a number.

    Examples
    --------
    >>> _read_integer(Path("/nonexistent/energy_uj")) is None
    True
    """
    try:
        return int(path.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return None


def _read_text(path: Path) -> str | None:
    """Return a sysfs file's contents, stripped, or ``None``.

    Parameters
    ----------
    path : pathlib.Path
        The file to read.

    Returns
    -------
    str or None
        Its contents without surrounding whitespace, or ``None`` when it is
        absent or unreadable.

    Examples
    --------
    >>> _read_text(Path("/nonexistent/name")) is None
    True
    """
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError:
        return None


def _zones() -> list[tuple[str, Path]]:
    """Return every readable energy zone on this machine, named as it names itself.

    Reading each zone's own ``name`` file is what separates a package from the
    memory beside it and from the ``psys`` zone above it. The alternative, taking
    the shape of the directory name, cannot tell a memory subzone — whose energy
    sits *outside* the package figure — from a core subzone, whose energy sits
    inside it.

    Returns
    -------
    list of (str, pathlib.Path)
        The zone's own name and its directory, in sysfs order.

    Examples
    --------
    >>> all(isinstance(name, str) for name, _ in _zones())
    True
    """
    found: list[tuple[str, Path]] = []
    for directory in sorted(glob.glob(RAPL_ZONE_GLOB)):
        path = Path(directory)
        try:
            name = (path / "name").read_text(encoding="utf-8").strip()
        except OSError:
            continue
        if name and (path / "energy_uj").exists():
            found.append((name, path))
    return found


def _sum_zones(wanted: list[Path], filename: str) -> int | None:
    """Return the sum of one sysfs file across several zones, or ``None``."""
    total = 0
    read_any = False
    for path in wanted:
        value = _read_integer(path / filename)
        if value is None:
            # One unreadable zone should not void a readable one; if none read,
            # the caller is told there was no measurement rather than half of one.
            continue
        total += value
        read_any = True
    return total if read_any else None


def _compute_zones() -> list[Path]:
    """Return the zones that make up the processor's own draw.

    ``psys`` covers the whole system-on-chip and already contains the packages,
    so when a machine publishes it, it is used alone. Otherwise every package is
    summed, which counts a two-socket machine whole rather than by half.

    Returns
    -------
    list of pathlib.Path
        The directories to read, possibly empty.

    Examples
    --------
    >>> isinstance(_compute_zones(), list)
    True
    """
    zones = _zones()
    system = [path for name, path in zones if name == _PSYS_ZONE]
    if system:
        return system
    return [path for name, path in zones if name.startswith(_PACKAGE_PREFIX)]


@dataclass(slots=True)
class GraphicsSampler:
    """A thread reading what the graphics device is drawing, for the length of a run.

    AMD's driver publishes instantaneous board power rather than a running
    total, so the honest figure over a run is a mean of readings taken across
    it. Reading a file every half second costs nothing next to the run being
    watched, and unlike the accelerator sampler it needs no second process:
    the file is already open to this user.

    Parameters
    ----------
    thread : threading.Thread
        The reader, running until the measured run is over.
    stopping : threading.Event
        Set to ask it to finish.
    readings : list of float
        Watts, one per tick, appended by the thread.

    Examples
    --------
    >>> sampler = GraphicsSampler.start()
    >>> sampler is None or sampler.stop() is None or True
    True
    """

    thread: threading.Thread
    stopping: threading.Event
    readings: list[float] = field(default_factory=list)

    @classmethod
    def start(cls) -> GraphicsSampler | None:
        """Begin reading, or return ``None`` when there is nothing to read.

        Returns
        -------
        GraphicsSampler or None
            A running sampler, or ``None`` when no graphics device publishes
            instantaneous power.

        Examples
        --------
        >>> GraphicsSampler.start() is None or True
        True
        """
        if read_graphics_watts() is None:
            return None
        stopping = threading.Event()
        readings: list[float] = []

        def read_until_stopped() -> None:
            while not stopping.is_set():
                watts = read_graphics_watts()
                if watts is not None:
                    readings.append(watts)
                stopping.wait(_SAMPLE_INTERVAL_MS / 1000.0)

        thread = threading.Thread(target=read_until_stopped, daemon=True)
        thread.start()
        return cls(thread=thread, stopping=stopping, readings=readings)

    def stop(self) -> tuple[float, int] | None:
        """Stop reading and return the mean board power and how many readings it is.

        Returns
        -------
        tuple of (float, int), or None
            Mean watts and the number of readings behind it, or ``None`` when
            too few arrived to average.

        Examples
        --------
        >>> sampler = GraphicsSampler.start()
        >>> sampler is None or sampler.stop() is None or True
        True
        """
        self.stopping.set()
        self.thread.join(timeout=_QUERY_TIMEOUT_SECONDS)
        readings = list(self.readings)
        if len(readings) < _MINIMUM_SAMPLES:
            return None
        return sum(readings) / len(readings), len(readings)


def read_package_energy_microjoules() -> int | None:
    """Return the accumulated processor energy, or ``None``.

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
    return _sum_zones(_compute_zones(), "energy_uj")


def package_wrap_range_microjoules() -> int | None:
    """Return how much energy the processor counters hold before they wrap.

    The counter is a fixed-width accumulator: it counts up, reaches its ceiling,
    and starts again from zero. Knowing the ceiling turns a difference that came
    out negative from a void measurement into an exact one, as long as the run
    was short enough that the counter passed that ceiling only once.

    Returns
    -------
    int or None
        Microjoules, or ``None`` when the kernel does not publish the ceiling.

    Examples
    --------
    >>> value = package_wrap_range_microjoules()
    >>> value is None or value > 0
    True
    """
    total = _sum_zones(_compute_zones(), "max_energy_range_uj")
    return total if total and total > 0 else None


def read_memory_energy_microjoules() -> int | None:
    """Return the accumulated memory energy, or ``None``.

    The memory zone sits under a package in the sysfs tree but its energy is not
    part of that package's figure, so a machine that publishes it has been
    reporting less than it drew every time this package read the package alone.
    Where the counter exists it replaces the memory term Green Algorithms
    estimates from how much memory is installed, which is the same quantity
    reached by a much shorter route.

    Returns
    -------
    int or None
        Microjoules since boot across every memory zone, or ``None``.

    Examples
    --------
    >>> value = read_memory_energy_microjoules()
    >>> value is None or value >= 0
    True
    """
    return _sum_zones([path for name, path in _zones() if name == _DRAM_ZONE], "energy_uj")


def _graphics_hwmon_directories() -> list[Path]:
    """Return the monitoring directories the graphics drivers publish.

    Linux hangs a hardware-monitoring node off every graphics device that has
    one, and the driver puts its own name in it: ``amdgpu`` for AMD, ``i915`` or
    ``xe`` for Intel. Both publish power there, and both publish it to an
    ordinary user, which makes this the one accelerator counter on Linux that
    needs neither a vendor tool nor administrator rights.

    Returns
    -------
    list of pathlib.Path
        One directory per graphics device that publishes power, possibly empty.

    Examples
    --------
    >>> isinstance(_graphics_hwmon_directories(), list)
    True
    """
    found: list[Path] = []
    for directory in sorted(glob.glob(GRAPHICS_HWMON_GLOB)):
        path = Path(directory)
        name = _read_text(path / "name")
        if name in GRAPHICS_DRIVERS:
            found.append(path)
    return found


def read_graphics_energy_microjoules() -> int | None:
    """Return the graphics devices' accumulated energy, or ``None``.

    Intel's drivers keep a running total in microjoules, which is the same kind
    of evidence as the processor's counter and needs no sampling. AMD's driver
    publishes what the board is drawing now instead, and is read elsewhere.

    Returns
    -------
    int or None
        Microjoules since the driver loaded, summed across devices, or ``None``
        when no device keeps a total.

    Examples
    --------
    >>> value = read_graphics_energy_microjoules()
    >>> value is None or value >= 0
    True
    """
    return _sum_zones(_graphics_hwmon_directories(), GRAPHICS_ENERGY_FILE)


def read_graphics_watts() -> float | None:
    """Return what the graphics devices are drawing right now, or ``None``.

    Returns
    -------
    float or None
        Watts, summed across devices, or ``None`` when none publishes it.

    Examples
    --------
    >>> value = read_graphics_watts()
    >>> value is None or value >= 0.0
    True
    """
    total = _sum_zones(_graphics_hwmon_directories(), GRAPHICS_POWER_FILE)
    return None if total is None else total / _MICROWATTS_PER_WATT


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
        # An Apple Silicon Mac has its own counters and its own reasons for not
        # answering; only an Intel Mac falls back to the powermetrics sentence.
        return apple.unavailable_reason() or _UNAVAILABLE_REASON["darwin"]
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
    by_domain : dict
        Average watts per subsystem, keyed ``cpu``, ``gpu``, ``ane``, ``memory``,
        where the machine publishes them apart. Empty where it publishes one
        number for the lot. This is what lets a figure show where the power went
        instead of asserting a split, and what lets a share of *processor* work
        price the processor's draw rather than the whole chip's.
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
    by_domain: dict[str, float] = field(default_factory=dict)

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


def _soc_reading(energy: apple.SocEnergy, *, seconds: float) -> PowerReading:
    """Turn an Apple chip's counters into a reading, naming what was read.

    Parameters
    ----------
    energy : saggio.analyze.apple.SocEnergy
        What the chip drew over the run, by subsystem.
    seconds : float
        Wall-clock duration, which the caller timed.

    Returns
    -------
    PowerReading
        Average watts over the run, with the channels that produced it named so
        the figure can be reproduced by anybody with the same machine.

    Examples
    --------
    >>> from saggio.analyze.apple import SocEnergy
    >>> reading = _soc_reading(
    ...     SocEnergy(20.0, 4.0, {"cpu": 18.0, "gpu": 2.0, "memory": 4.0},
    ...               ("CPU Energy", "GPU Energy", "DRAM0")),
    ...     seconds=2.0)
    >>> reading.watts, reading.sources
    (12.0, ('system-on-chip', 'memory'))
    """
    joules = energy.compute_joules + (energy.memory_joules or 0.0)
    sources = ["system-on-chip"]
    scopes = [
        f"The figure covers {apple.SOC_SCOPE}, read from the {', '.join(energy.channels)} counters."
    ]
    if energy.memory_joules is not None:
        sources.append("memory")
        scopes[0] = (
            f"The figure covers {apple.SOC_SCOPE} and {apple.SOC_MEMORY_SCOPE}, "
            f"read from the {', '.join(energy.channels)} counters."
        )
        scopes.append(_MEMORY_MEASURED_NOTE)
    scopes.append(apple.SOC_MODEL_NOTE)
    return PowerReading(
        watts=joules / seconds,
        joules=joules,
        scope=" ".join(scopes),
        sources=tuple(sources),
        # The chip counts these apart, so there is no reason to add them up and
        # then guess the split back out again.
        by_domain={
            domain: value / seconds for domain, value in energy.by_domain.items() if seconds > 0.0
        },
    )


def measure_for(seconds: float) -> PowerReading:
    """Measure what this machine draws over a fixed interval.

    This measures the *machine*, not any particular program: whatever else is
    running is in the figure. That is what makes it useful as a baseline — the
    draw a run has to be compared against before any of it can be called the
    run's own cost.

    Parameters
    ----------
    seconds : float
        How long to watch. Zero or less measures nothing.

    Returns
    -------
    PowerReading
        The average over the interval, or a reading that says why there is none.

    Examples
    --------
    >>> measure_for(0.0).measured()
    False
    """
    meter = PowerMeter.start()
    # A machine with no counter is not made to wait: the second would buy a
    # reading that says "not measured", which the meter can say immediately.
    if seconds > 0.0 and meter.reads_anything():
        time.sleep(seconds)
        return meter.stop(seconds=seconds)
    return meter.stop(seconds=0.0)


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
    memory_started_at : int or None
        The memory counter when the run began, or ``None`` when this machine
        publishes no such counter. Its energy is outside the package figure, so
        a machine that has it has been reporting less than it drew until now.
    wrap_range : int or None
        How much the processor counters hold before they start again from zero,
        which turns one wrap from a void measurement into an exact one.
    soc : saggio.analyze.apple.SocMeter or None
        An open subscription to an Apple chip's own energy counters, on the
        machines that have them.
    graphics_started_at : int or None
        The graphics driver's accumulated energy when the run began, read from
        sysfs, or ``None`` when NVIDIA already answered or no driver keeps one.
    graphics_sampler : GraphicsSampler or None
        A thread reading instantaneous graphics power, started only when no
        accumulated counter was available to read instead.

    Examples
    --------
    >>> PowerMeter.start().stop(seconds=0.0).measured()
    False
    """

    started_at: int | None
    accelerator_started_at: int | None = None
    sampler: AcceleratorSampler | None = None
    memory_started_at: int | None = None
    wrap_range: int | None = None
    soc: apple.SocMeter | None = None
    graphics_started_at: int | None = None
    graphics_sampler: GraphicsSampler | None = None

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
        started_at = read_package_energy_microjoules()
        sampler = None if accelerator_started_at is not None else AcceleratorSampler.start()
        # The graphics drivers are only consulted when NVIDIA's did not answer:
        # two readings of the same board added together would double it.
        nvidia_answered = accelerator_started_at is not None or sampler is not None
        graphics_started_at = None if nvidia_answered else read_graphics_energy_microjoules()
        return cls(
            started_at=started_at,
            accelerator_started_at=accelerator_started_at,
            sampler=sampler,
            memory_started_at=read_memory_energy_microjoules(),
            wrap_range=package_wrap_range_microjoules() if started_at is not None else None,
            soc=apple.SocMeter.start(),
            graphics_started_at=graphics_started_at,
            graphics_sampler=(
                None
                if nvidia_answered or graphics_started_at is not None
                else GraphicsSampler.start()
            ),
        )

    def reads_anything(self) -> bool:
        """Return whether any counter answered when this meter started.

        A meter that answered nothing will still answer nothing a second later,
        so there is no point watching it for one. Asked here rather than of
        :mod:`saggio.analyze.capability`, whose ``probe()`` runs ``nvidia-smi``
        and is far too expensive to put in the path of every measured run: the
        meter has already done the discovery by the time it exists.

        Returns
        -------
        bool
            True when at least one counter produced an opening reading.

        Examples
        --------
        >>> PowerMeter(started_at=None).reads_anything()
        False
        >>> PowerMeter(started_at=12345).reads_anything()
        True
        """
        return any(
            (
                self.started_at is not None,
                self.accelerator_started_at is not None,
                self.sampler is not None,
                self.memory_started_at is not None,
                self.soc is not None,
                self.graphics_started_at is not None,
                self.graphics_sampler is not None,
            )
        )

    def _package_joules(self, *, seconds: float) -> tuple[float | None, str | None]:
        """Return the package energy over the run, or the reason there is none.

        Parameters
        ----------
        seconds : float
            Wall-clock duration, needed only to phrase the ceiling above which a
            recovered wrap would have been two wraps.
        """
        if self.started_at is None:
            return None, unavailable_reason()
        ended_at = read_package_energy_microjoules()
        if ended_at is None:
            return None, (
                "The package energy counter stopped answering during the run, "
                "so there is no difference to take."
            )
        if ended_at >= self.started_at:
            return (ended_at - self.started_at) / _MICROJOULES_PER_JOULE, None
        if self.wrap_range is None:
            return None, (
                "The package energy counter wrapped or reset during the run and "
                "the kernel publishes no range for it, so the difference is not a "
                "measurement."
            )
        recovered = (self.wrap_range + ended_at - self.started_at) / _MICROJOULES_PER_JOULE
        if recovered < 0.0:
            # The counter did not wrap: it was reset, by a suspend or by another
            # reader. Two unknowable totals do not make a difference.
            return None, (
                "The package energy counter was reset rather than wrapped during "
                "the run, so the difference is not a measurement."
            )
        ceiling = self.wrap_range / _MICROJOULES_PER_JOULE / seconds
        return recovered, _WRAP_RECOVERED_NOTE.format(ceiling=ceiling)

    def _memory_joules(self) -> float | None:
        """Return what the memory drew over the run, or ``None``."""
        if self.memory_started_at is None:
            return None
        ended_at = read_memory_energy_microjoules()
        if ended_at is None or ended_at < self.memory_started_at:
            return None
        return (ended_at - self.memory_started_at) / _MICROJOULES_PER_JOULE

    def _graphics_watts(self, *, seconds: float) -> tuple[float | None, str | None]:
        """Return the mean graphics power over the run, and how it was obtained.

        This is the driver-published path that needs no vendor tool and no
        administrator rights: Intel keeps a running total, AMD publishes what
        the board is drawing now and is sampled.
        """
        if self.graphics_started_at is not None:
            ended_at = read_graphics_energy_microjoules()
            if ended_at is None or ended_at < self.graphics_started_at:
                return None, None
            joules = (ended_at - self.graphics_started_at) / _MICROJOULES_PER_JOULE
            return joules / seconds, GRAPHICS_COUNTER_SCOPE
        if self.graphics_sampler is None:
            return None, None
        sampled = self.graphics_sampler.stop()
        if sampled is None:
            return None, None
        mean_watts, count = sampled
        return mean_watts, GRAPHICS_SAMPLED_SCOPE.format(
            count=count, interval=_SAMPLE_INTERVAL_MS / 1000.0
        )

    def _accelerator_watts(self, *, seconds: float) -> tuple[float | None, str | None]:
        """Return the mean accelerator power over the run, and how it was obtained.

        NVIDIA's driver is asked first because it is the one this package was
        written for; the graphics drivers Linux ships answer for everybody else,
        and they answer an ordinary user, which the vendor tool on a locked-down
        machine may not.
        """
        if self.accelerator_started_at is None and self.sampler is None:
            return self._graphics_watts(seconds=seconds)
        if self.accelerator_started_at is not None:
            ended_at = read_accelerator_energy_millijoules()
            if ended_at is None:
                return None, None
            if ended_at < self.accelerator_started_at:
                # The board answered; its counter wrapped or was reset. Saying
                # "no accelerator answered" here would mislabel a measurement
                # problem as an absence of hardware.
                return None, _ACCELERATOR_WRAPPED_NOTE
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
            if self.graphics_sampler is not None:
                self.graphics_sampler.stop()
            if self.soc is not None:
                self.soc.stop()
            return PowerReading(
                None, None, "The run was too short to divide energy by its duration."
            )

        if self.soc is not None:
            # An Apple chip has no RAPL zone and can host no NVIDIA board, so
            # when its counters answer they are the whole of what this machine
            # will say, and the rest of this method has nothing to add.
            soc_energy = self.soc.stop()
            if soc_energy is not None:
                return _soc_reading(soc_energy, seconds=seconds)

        package_joules, package_reason = self._package_joules(seconds=seconds)
        memory_joules = self._memory_joules()
        accelerator_watts, accelerator_scope = self._accelerator_watts(seconds=seconds)

        sources: list[str] = []
        scopes: list[str] = []
        watts = 0.0
        if package_joules is not None:
            sources.append("processor package")
            watts += package_joules / seconds
        if memory_joules is not None:
            sources.append("memory")
            watts += memory_joules / seconds
        if accelerator_watts is not None:
            sources.append("accelerator")
            scopes.append(f"The accelerator figure covers {accelerator_scope}.")
            watts += accelerator_watts

        if not sources:
            return PowerReading(None, None, package_reason or unavailable_reason())

        if accelerator_watts is None:
            # RAPL_SCOPE_NOTE is about what the package counter misses, which is
            # only worth saying when nothing else made up for it. When the
            # accelerator answered but its counter wrapped, that reason arrives
            # in accelerator_scope and is told instead of the absence line.
            scopes.insert(0, RAPL_SCOPE_NOTE)
            scopes.append(accelerator_scope or _ACCELERATOR_MISSING_NOTE)
        elif package_joules is None:
            scopes.append(_PACKAGE_MISSING_NOTE)
        else:
            scopes.insert(0, _BOTH_MEASURED_NOTE)
        if memory_joules is not None:
            scopes.append(_MEMORY_MEASURED_NOTE)
        if package_reason is not None and package_joules is not None:
            # A recovered wrap is a measurement with a condition attached, and
            # the condition travels with the number rather than being dropped
            # because the number turned out to exist.
            scopes.append(package_reason)

        return PowerReading(
            watts=watts,
            joules=watts * seconds,
            scope=" ".join(scopes),
            sources=tuple(sources),
        )
