"""Where to look, what to call it, and what the figure covers.

Module summary
--------------
The globs that find a counter, the names a zone calls itself, the conversions
between the units each interface publishes, and the sentences that say what a
figure covers. Those sentences matter as much as the numbers: a counter reads a
package or a board, never the wall socket, and every reading here carries the
scope it actually measured.

Author
------
Warith Harchaoui
"""

from __future__ import annotations

from typing import Final

#: The program NVIDIA ships with its driver, and the only way to ask a board what
#: it is drawing without linking against the management library.
NVIDIA_SMI: Final[str] = "nvidia-smi"


#: How long to wait for the driver to answer a one-shot question before deciding
#: it is not going to. A healthy driver answers in milliseconds; a wedged one
#: must not hold up a measurement.
_QUERY_TIMEOUT_SECONDS: Final[float] = 5.0


#: How often the sampling fallback asks the board what it is drawing. Half a
#: second is short enough to follow a training step and long enough that the
#: sampler costs nothing measurable next to the run it is watching.
_SAMPLE_INTERVAL_MS: Final[int] = 500


#: Below this many samples there is no mean worth the name, and a single reading
#: taken at an arbitrary instant is not an average over a run.
_MINIMUM_SAMPLES: Final[int] = 2


#: Where Linux publishes its energy zones. The pattern covers ``intel-rapl`` and
#: the ``amd-rapl`` control type newer kernels register on AMD parts, and stops
#: short of ``intel-rapl-mmio``, which is the *same* package published through a
#: second interface: adding both would count one processor twice.
RAPL_ZONE_GLOB: Final[str] = "/sys/class/powercap/[ai]*-rapl:*"


#: Where Linux publishes the processor package energy counters.
RAPL_ENERGY_GLOB: Final[str] = "/sys/class/powercap/intel-rapl:*/energy_uj"


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


#: Microjoules in a joule, spelled out so the unit conversion reads as physics.
_MICROJOULES_PER_JOULE: Final[float] = 1_000_000.0


#: Millijoules in a joule. The driver's energy counter is published in millijoules.
_MILLIJOULES_PER_JOULE: Final[float] = 1000.0


#: Microwatts in a watt. The graphics drivers publish power in microwatts.
_MICROWATTS_PER_WATT: Final[float] = 1_000_000.0


#: What the counter covers, carried into the model so a reader knows the boundary.
RAPL_SCOPE_NOTE: Final[str] = (
    "Intel RAPL counts the processor package only: a discrete accelerator's draw "
    "is not included, so a GPU workload measured this way is undercounted."
)


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


#: Said when the memory counter answered, so a reader knows the figure includes
#: what Green Algorithms would otherwise have estimated from installed capacity.
_MEMORY_MEASURED_NOTE: Final[str] = (
    "Memory is measured rather than estimated here: the machine publishes its own "
    "memory energy counter, so the figure is what the memory drew rather than what "
    "its installed capacity suggests it would draw."
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


#: Said when the accelerator answered but its counter went backwards mid-run.
_ACCELERATOR_WRAPPED_NOTE: Final[str] = (
    "The accelerator's energy counter wrapped or reset during the run, so its draw "
    "is not included; the board itself did answer."
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


#: Why no measurement was possible, by platform, phrased so the reader knows it is
#: a property of the machine rather than a failure of the tool.
_UNAVAILABLE_REASON: Final[dict[str, str]] = {
    "darwin": (
        "macOS publishes package power only through powermetrics, which needs "
        "administrator rights and so cannot be read from a library call."
    ),
    "linux": (
        "No readable RAPL counter was found: this is an ARM machine, a container "
        "without the sysfs files, or the files are not world-readable."
    ),
}
