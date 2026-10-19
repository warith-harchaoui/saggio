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

from ...i18n import say

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


#: The keys of every sentence this module used to hold as a constant. A constant
#: carries one language by construction, and these end up in a model file beside
#: the figure they bound.
_SCOPE_KEYS: Final[dict[str, str]] = {
    "rapl": "power.rapl_scope",
    "accelerator_counter": "power.accelerator.counter",
    "accelerator_sampled": "power.accelerator.sampled",
    "graphics_counter": "power.graphics.counter",
    "graphics_sampled": "power.graphics.sampled",
    "memory_measured": "power.memory_measured",
    "both_measured": "power.both_measured",
    "package_missing": "power.package_missing",
    "accelerator_missing": "power.accelerator_missing",
    "accelerator_wrapped": "power.accelerator_wrapped",
    "wrap_recovered": "power.wrap_recovered",
}


def scope_note(which: str, **arguments: object) -> str:
    """Return one boundary sentence, in the language in force.

    Parameters
    ----------
    which : str
        Which sentence, by the short name :data:`_SCOPE_KEYS` keys it under.
    **arguments
        What the sentence names in braces, already formatted.

    Returns
    -------
    str
        The sentence.

    Examples
    --------
    >>> scope_note("rapl").startswith("Intel RAPL")
    True
    >>> "12 readings" in scope_note(
    ...     "accelerator_sampled", count=12, interval="0.5 seconds"
    ... )
    True
    """
    return say(_SCOPE_KEYS[which], **arguments)


def rapl_scope_note() -> str:
    """Return what the processor counter covers, and what it misses.

    Kept under its own name because the audit carries it into the model beside
    a measured power figure, and a reader of that file is the person the
    sentence is for.

    Returns
    -------
    str
        The sentence, in the language in force.

    Examples
    --------
    >>> "processor package only" in rapl_scope_note()
    True
    """
    return scope_note("rapl")


def unavailable_reason(platform: str) -> str:
    """Return why no measurement was possible here, by platform.

    Phrased so a reader knows it is a property of the machine rather than a
    failure of the tool.

    Parameters
    ----------
    platform : str
        ``sys.platform``.

    Returns
    -------
    str
        The sentence, or an empty string for a platform with nothing to say.

    Examples
    --------
    >>> "powermetrics" in unavailable_reason("darwin")
    True
    >>> unavailable_reason("plan9")
    ''
    """
    return say(f"power.unavailable.{platform}") if platform in ("darwin", "linux") else ""
