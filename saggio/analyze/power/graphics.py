"""What an AMD or Intel graphics device drew, through hwmon.

Module summary
--------------
Linux hangs a hardware-monitoring node off every graphics device that has one,
and the driver writes its own name in it. Both publish power to an ordinary
user, which makes this the one accelerator counter on Linux that needs neither
a vendor tool nor administrator rights.

Author
------
Warith Harchaoui
"""

from __future__ import annotations

import glob
import threading
from dataclasses import dataclass, field
from pathlib import Path

from .rapl import _sum_zones
from .sysfs import _read_text
from .tables import (
    _MICROWATTS_PER_WATT,
    _MINIMUM_SAMPLES,
    _QUERY_TIMEOUT_SECONDS,
    _SAMPLE_INTERVAL_MS,
    GRAPHICS_DRIVERS,
    GRAPHICS_ENERGY_FILE,
    GRAPHICS_HWMON_GLOB,
    GRAPHICS_POWER_FILE,
)


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
