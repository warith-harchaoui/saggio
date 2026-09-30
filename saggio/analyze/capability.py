"""
What this machine will tell us about its own power, and what it would take.

Module summary
--------------
Every energy counter in this package can answer "no", and the reasons are not
interchangeable. A laptop with no counter at all, a server whose counter exists
but is closed to anybody who is not root, a container that cannot see sysfs, and
a chip nobody has taught this package to read are four different situations with
four different remedies, and a tool that prints "could not measure power" for all
four has told the reader nothing they can act on.

So this module asks each interface the same three questions — is it here, may
*you* read it, and what does it cover — and answers with a state and, where one
exists, the exact thing to run. It never escalates. It does not call ``sudo``,
it does not ask for a password, and it does not quietly fall back to a tool that
would. Where administrator rights are the only way, it says so and stops, because
a measurement tool that acquires privileges on its own behalf is a worse problem
than an estimated wattage.

The one remedy worth reading before running: on Linux since 5.10 the processor's
energy counter is closed to ordinary users on purpose. Reading it quickly enough
is a side channel that recovers secrets from other processes — the PLATYPUS
attack, CVE-2020-8694 — and the kernel's answer was to make it root-only. Opening
it is a real decision about a real trade-off, so the remedy is printed rather
than performed, and the reason travels with it.

Usage example
-------------
>>> from saggio.analyze.capability import probe
>>> interfaces = probe()
>>> all(interface.state in STATES for interface in interfaces)
True

Author
------
Warith Harchaoui
"""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Final

import os_helper as osh

from . import apple
from .power import (
    GRAPHICS_ENERGY_FILE,
    GRAPHICS_POWER_FILE,
    NVIDIA_SMI,
    _graphics_hwmon_directories,
    _zones,
    read_accelerator_energy_millijoules,
    read_graphics_energy_microjoules,
    read_graphics_watts,
    read_memory_energy_microjoules,
    read_package_energy_microjoules,
)

#: The interface answers this user, right now, with no privileges asked for.
READS: Final[str] = "reads"

#: The counter is on this machine and this user may not read it. This is the
#: state with a remedy, and the only one where the reader has a decision to make.
BLOCKED: Final[str] = "blocked"

#: The counter exists only behind administrator rights, and this package will
#: not ask for them. Distinct from ``blocked``: there is no file to open up,
#: only a command that would have to be run as somebody else.
ROOT_ONLY: Final[str] = "root-only"

#: There is nothing here to read. Not a failure, a property of the machine.
ABSENT: Final[str] = "absent"

#: Every state an interface can be in, so a caller can assert on the set.
STATES: Final[frozenset[str]] = frozenset({READS, BLOCKED, ROOT_ONLY, ABSENT})

#: Why the kernel closed the processor's counter, and what opening it costs. The
#: remedy is never printed without it: a reader who opens the counter should know
#: they are reopening a published side channel on a machine they may share.
PLATYPUS_NOTE: Final[str] = (
    "Linux has kept this counter root-only since 5.10 on purpose: sampled fast "
    "enough it leaks what other processes are computing (CVE-2020-8694, the "
    "PLATYPUS attack). Opening it to a group is a judgement about who shares "
    "this machine, which is why it is printed here rather than done for you."
)

#: How to open the processor counter for one session, and how to keep it open.
#: Read-only, and only the energy files: the limits beside them stay shut, so
#: nothing here lets a reader throttle or overheat the machine.
_RAPL_REMEDY: Final[str] = (
    "Until the next reboot:  sudo chmod a+r /sys/class/powercap/*/energy_uj\n"
    "    Across reboots, a udev rule that touches the energy files and nothing "
    "else:\n"
    '      SUBSYSTEM=="powercap", ACTION=="add", '
    'RUN+="/bin/chmod a+r /sys%p/energy_uj"\n'
    "    in /etc/udev/rules.d/99-saggio-rapl.rules."
)

#: What macOS offers behind a password, and why this package does not take it.
_POWERMETRICS_NOTE: Final[str] = (
    "macOS publishes the same figures through powermetrics, which needs "
    "administrator rights. This package will not ask for them; run "
    "`sudo powermetrics --samplers cpu_power -n 1` yourself if you want to "
    "compare it against what was measured here."
)


@dataclass(frozen=True, slots=True)
class Interface:
    """One way of reading power, and whether it is open to this user.

    Parameters
    ----------
    name : str
        What the interface is called, as its own documentation calls it.
    covers : str
        What a figure from it would include.
    state : str
        One of :data:`READS`, :data:`BLOCKED`, :data:`ROOT_ONLY`, :data:`ABSENT`.
    detail : str
        One sentence on why it is in that state.
    remedy : str or None
        Exactly what to run to change a ``blocked`` into a ``reads``, or
        ``None`` when nothing the reader does would help.

    Examples
    --------
    >>> Interface("RAPL", "the processor", READS, "answers", None).state
    'reads'
    """

    name: str
    covers: str
    state: str
    detail: str
    remedy: str | None = None

    def measured(self) -> bool:
        """Return whether this interface would contribute a measured figure.

        Returns
        -------
        bool
            ``True`` only in the ``reads`` state.

        Examples
        --------
        >>> Interface("x", "y", ABSENT, "no").measured()
        False
        """
        return self.state == READS


def _rapl_interface() -> Interface:
    """Return the state of the Linux processor energy counters."""
    zones = _zones()
    if not zones:
        return Interface(
            name="Linux powercap (RAPL)",
            covers="the processor package, and the memory where a zone exists for it",
            state=ABSENT,
            detail=(
                "No powercap zone is published here. That is an ARM machine, a "
                "virtual machine whose host does not pass the counters through, "
                "or a container without /sys/class/powercap mounted."
            ),
        )
    if read_package_energy_microjoules() is not None:
        memory = read_memory_energy_microjoules()
        names = ", ".join(sorted({name for name, _ in zones}))
        return Interface(
            name="Linux powercap (RAPL)",
            covers=(
                "the processor package and its memory"
                if memory is not None
                else "the processor package, but not the memory beside it"
            ),
            state=READS,
            detail=f"Zones answering: {names}.",
        )
    unreadable = [path.name for _, path in zones if not os.access(path / "energy_uj", os.R_OK)]
    return Interface(
        name="Linux powercap (RAPL)",
        covers="the processor package, and the memory where a zone exists for it",
        state=BLOCKED,
        detail=(
            f"{len(unreadable) or len(zones)} zone(s) are here and closed to you. {PLATYPUS_NOTE}"
        ),
        remedy=_RAPL_REMEDY,
    )


def _apple_interface() -> Interface:
    """Return the state of an Apple chip's own energy counters."""
    if apple.available():
        return Interface(
            name="Apple system-on-chip counters (IOReport)",
            covers="the processor cores, graphics cores, neural engine, and memory",
            state=READS,
            detail="Read as an ordinary user; no password is asked for and none is needed.",
        )
    return Interface(
        name="Apple system-on-chip counters (IOReport)",
        covers="the processor cores, graphics cores, neural engine, and memory",
        state=ABSENT,
        detail=apple.unavailable_reason() or "Not an Apple Silicon Mac.",
    )


def _powermetrics_interface() -> Interface:
    """Return the state of the tool macOS ships behind a password."""
    present = shutil.which("powermetrics") is not None
    return Interface(
        name="macOS powermetrics",
        covers="the same subsystems, through Apple's own tool",
        state=ROOT_ONLY if present else ABSENT,
        detail=_POWERMETRICS_NOTE if present else "Not installed on this machine.",
    )


def _nvidia_interface() -> Interface:
    """Return the state of NVIDIA's driver."""
    if shutil.which(NVIDIA_SMI) is None:
        return Interface(
            name="NVIDIA driver (nvidia-smi)",
            covers="the whole accelerator board",
            state=ABSENT,
            detail="No nvidia-smi on PATH, so there is no NVIDIA driver to ask.",
        )
    if read_accelerator_energy_millijoules() is not None:
        return Interface(
            name="NVIDIA driver (nvidia-smi)",
            covers="the whole accelerator board",
            state=READS,
            detail="The board keeps an accumulated energy counter, which is read exactly.",
        )
    return Interface(
        name="NVIDIA driver (nvidia-smi)",
        covers="the whole accelerator board",
        state=READS,
        detail=(
            "The board publishes instantaneous power rather than a total, so it is "
            "sampled across the run and the count of samples travels with the mean."
        ),
    )


def _graphics_interface() -> Interface:
    """Return the state of the graphics drivers Linux ships."""
    directories = _graphics_hwmon_directories()
    if not directories:
        return Interface(
            name="Linux graphics driver (amdgpu, i915, xe)",
            covers="the graphics device",
            state=ABSENT,
            detail="No graphics device here publishes a power sensor through sysfs.",
        )
    if read_graphics_energy_microjoules() is not None:
        return Interface(
            name="Linux graphics driver (amdgpu, i915, xe)",
            covers="the graphics device",
            state=READS,
            detail=(
                f"An accumulated {GRAPHICS_ENERGY_FILE} counter is published to "
                "ordinary users, so no vendor tool and no privileges are needed."
            ),
        )
    if read_graphics_watts() is not None:
        return Interface(
            name="Linux graphics driver (amdgpu, i915, xe)",
            covers="the graphics device",
            state=READS,
            detail=(
                f"{GRAPHICS_POWER_FILE} is published to ordinary users; it is "
                "instantaneous, so it is sampled across the run."
            ),
        )
    blocked = [
        path
        for path in directories
        if not os.access(path / GRAPHICS_ENERGY_FILE, os.R_OK)
        and not os.access(path / GRAPHICS_POWER_FILE, os.R_OK)
    ]
    return Interface(
        name="Linux graphics driver (amdgpu, i915, xe)",
        covers="the graphics device",
        state=BLOCKED if blocked else ABSENT,
        detail=(
            "The monitoring node is here but neither its energy counter nor its "
            "power sensor can be read."
        ),
        remedy=(
            "sudo chmod a+r "
            f"{directories[0]}/{GRAPHICS_ENERGY_FILE} "
            f"{directories[0]}/{GRAPHICS_POWER_FILE}"
            if blocked
            else None
        ),
    )


def _windows_interface() -> Interface:
    """Return the state of what Windows offers a library."""
    return Interface(
        name="Windows processor energy",
        covers="the processor package",
        state=ABSENT,
        detail=(
            "Windows publishes no vendor-neutral processor energy counter to an "
            "unprivileged process. The Energy Meter Interface exists but only on "
            "devices whose manufacturer implemented it and only through a driver, "
            "and powercfg's per-application estimates are a battery model rather "
            "than a counter. An accelerator here is still measured through its own "
            "driver; the processor is estimated from the hardware catalogue, and "
            "the report says so."
        ),
    )


def _node_interface() -> Interface:
    """Return the state of the whole-node meters a datacentre has."""
    return Interface(
        name="Baseboard controller (IPMI, DCMI, Redfish)",
        covers="the whole node, including fans, storage, and the power supply's losses",
        state=ROOT_ONLY,
        detail=(
            "A server's own meter is the only figure here that covers the whole "
            "machine rather than a part of it, and it is reached with credentials "
            "for the management controller rather than a file. This package does "
            "not hold those credentials and does not ask for them; on a cluster, "
            "the figure your operator already collects is the better one, and the "
            "model can carry it as a measured value."
        ),
    )


def probe() -> tuple[Interface, ...]:
    """Return every power interface relevant to this machine, in reading order.

    Interfaces belonging to other platforms are left out rather than listed as
    absent: a Linux user is not helped by being told that macOS ships a tool
    they do not have.

    Returns
    -------
    tuple of Interface
        What this machine offers, what it withholds, and what it would take.

    Examples
    --------
    >>> interfaces = probe()
    >>> len(interfaces) >= 2
    True
    >>> all(interface.state in STATES for interface in interfaces)
    True
    """
    if osh.macos():
        return (_apple_interface(), _powermetrics_interface(), _node_interface())
    if osh.windows():
        return (_windows_interface(), _nvidia_interface(), _node_interface())
    return (
        _rapl_interface(),
        _nvidia_interface(),
        _graphics_interface(),
        _node_interface(),
    )


def measurable() -> bool:
    """Return whether anything on this machine would produce a measured figure.

    Returns
    -------
    bool
        ``True`` when at least one interface reads.

    Examples
    --------
    >>> measurable() in (True, False)
    True
    """
    return any(interface.measured() for interface in probe())


def summary() -> str:
    """Return the probe as text, for a terminal or a report.

    Returns
    -------
    str
        One block per interface: its state, what it covers, why, and the remedy
        where there is one.

    Examples
    --------
    >>> "reads" in summary() or "absent" in summary()
    True
    """
    lines: list[str] = []
    for interface in probe():
        lines.append(f"[{interface.state}] {interface.name}")
        lines.append(f"    covers: {interface.covers}")
        lines.append(f"    {interface.detail}")
        if interface.remedy:
            lines.append(f"    to open it: {interface.remedy}")
        lines.append("")
    if not measurable():
        lines.append(
            "Nothing here measures power, so energy will be estimated from the "
            "hardware catalogue and every figure derived from it will say "
            "`estimated` rather than `measured`. That is a weaker number, not a "
            "wrong one."
        )
    return "\n".join(lines).rstrip() + "\n"


def paths_read() -> tuple[str, ...]:
    """Return the files this machine would be read from, for the record.

    A reader who wants to check a figure by hand needs the paths, and a reader
    auditing what this package touches needs them more.

    Returns
    -------
    tuple of str
        Filesystem paths, empty on a machine read through a library or a tool
        rather than through files.

    Examples
    --------
    >>> all(isinstance(path, str) for path in paths_read())
    True
    """
    paths: list[Path] = [path / "energy_uj" for _, path in _zones()]
    for directory in _graphics_hwmon_directories():
        for filename in (GRAPHICS_ENERGY_FILE, GRAPHICS_POWER_FILE):
            if (directory / filename).exists():
                paths.append(directory / filename)
    return tuple(str(path) for path in paths)
