"""The processor's own energy counters, through powercap.

Module summary
--------------
Linux publishes a tree of energy zones, each naming itself. Reading that name
rather than the directory's shape is what separates a package from the memory
beside it and from the ``psys`` zone above it -- the memory's energy sits
*outside* the package figure, and ``psys`` already contains the packages, so
summing them would report the machine roughly twice.

Author
------
Warith Harchaoui
"""

from __future__ import annotations

import glob
from pathlib import Path

from .sysfs import _read_integer
from .tables import _DRAM_ZONE, _PACKAGE_PREFIX, _PSYS_ZONE, RAPL_ZONE_GLOB


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
