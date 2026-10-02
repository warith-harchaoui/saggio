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
library labels itself. Those two systems are the two this package supports; see
:data:`saggio.analyze.capability.SUPPORTED_PLATFORMS` for why there is no
third.

The processor is rarely the expensive part. On the workloads this package exists
for, the accelerator draws several times what the package does, and NVIDIA's
driver reports it without privileges, either as an
accumulating energy counter or as an instantaneous board wattage that can be
sampled across the run. Both paths are read here, the counter first because it is
a counter, and whichever one answers says so in the scope it carries. A machine
that answers on one side and not the other reports the side it measured and names
the side it did not, because a package figure presented as the cost of a training
run would be wrong by an order of magnitude. Where NVIDIA's driver is not the one
present, Linux's own graphics drivers publish the same thing through sysfs —
``amdgpu`` as instantaneous watts, ``i915`` and ``xe`` as an accumulating
counter — to an ordinary user and with no vendor tool involved.

What is where
-------------
Split by **where the energy comes from**, which is the structure the problem
actually has: four interfaces, each with its own units, its own failure mode and
its own scope.

========================================= =====================================
:mod:`~saggio.analyze.power.tables`       globs, zone names, unit conversions,
                                          and the sentences that say what a
                                          figure covers
:mod:`~saggio.analyze.power.sysfs`        reading a number out of the kernel, or
                                          admitting it could not
:mod:`~saggio.analyze.power.rapl`         the processor's own counters, by zone
                                          name rather than directory shape
:mod:`~saggio.analyze.power.accelerator`  NVIDIA, by counter or by sampling
:mod:`~saggio.analyze.power.graphics`     AMD and Intel, through hwmon
:mod:`~saggio.analyze.power.soc`          Apple Silicon, per subsystem
:mod:`~saggio.analyze.power.reading`      what was measured, and what it covers
:mod:`~saggio.analyze.power.meter`        running everything that answers here
========================================= =====================================

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

from .accelerator import (
    AcceleratorSampler,
    _query_nvidia_smi,
    read_accelerator_energy_millijoules,
)
from .graphics import (
    GraphicsSampler,
    _graphics_hwmon_directories,
    read_graphics_energy_microjoules,
    read_graphics_watts,
)
from .meter import PowerMeter, measure_for
from .rapl import (
    _zones,
    package_wrap_range_microjoules,
    read_memory_energy_microjoules,
    read_package_energy_microjoules,
)
from .reading import PowerReading, unavailable_reason
from .soc import _soc_reading
from .tables import (
    GRAPHICS_ENERGY_FILE,
    GRAPHICS_HWMON_GLOB,
    GRAPHICS_POWER_FILE,
    NVIDIA_SMI,
    RAPL_ENERGY_GLOB,
    RAPL_SCOPE_NOTE,
    RAPL_ZONE_GLOB,
)

__all__ = [
    "AcceleratorSampler",
    "GRAPHICS_ENERGY_FILE",
    "GRAPHICS_HWMON_GLOB",
    "GRAPHICS_POWER_FILE",
    "GraphicsSampler",
    "NVIDIA_SMI",
    "PowerMeter",
    "PowerReading",
    "RAPL_ENERGY_GLOB",
    "RAPL_SCOPE_NOTE",
    "RAPL_ZONE_GLOB",
    "measure_for",
    "package_wrap_range_microjoules",
    "read_accelerator_energy_millijoules",
    "read_graphics_energy_microjoules",
    "read_graphics_watts",
    "read_memory_energy_microjoules",
    "read_package_energy_microjoules",
    "unavailable_reason",
    "_graphics_hwmon_directories",
    "_query_nvidia_smi",
    "_soc_reading",
    "_zones",
]
