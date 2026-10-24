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
import sys
import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import Final

import os_helper as osh

from ..i18n import say
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
PLATYPUS_NOTE: Final[str] = say("capability.platypus_note")


#: How to open the processor counter for one session, and how to keep it open.
#: Read-only, and only the energy files: the limits beside them stay shut, so
#: nothing here lets a reader throttle or overheat the machine.
def _rapl_remedy() -> str:
    """Return how to open the processor counter, in the language in force.

    The commands are not translated and never will be: a shell line is typed,
    not read. What the catalogue carries is the sentence around each one.

    Returns
    -------
    str
        Two commands, each introduced by a sentence.

    Examples
    --------
    >>> "chmod a+r" in _rapl_remedy()
    True
    """
    return "\n".join(
        (
            say("capability.rapl.remedy.until_reboot")
            + "  sudo chmod a+r /sys/class/powercap/*/energy_uj",
            "    " + say("capability.rapl.remedy.across_reboots"),
            '      SUBSYSTEM=="powercap", ACTION=="add", RUN+="/bin/chmod a+r /sys%p/energy_uj"',
            "    "
            + say(
                "capability.rapl.remedy.in_file",
                path="/etc/udev/rules.d/99-saggio-rapl.rules",
            ),
        )
    )


#: What macOS offers behind a password, and why this package does not take it.
_POWERMETRICS_NOTE_KEY: Final[str] = "capability.powermetrics.note"


#: The platforms this package supports. Not a list of where it happens to
#: import: a list of where its central claim holds. Everything here exists to
#: turn a counter into a number somebody can defend, and Linux and macOS are the
#: two systems that publish those counters to an ordinary process.
SUPPORTED_PLATFORMS: Final[tuple[str, ...]] = ("linux", "darwin")

#: Why Windows is not among them. Written once, said wherever it is needed,
#: because a limit stated four different ways reads as four different limits.
UNSUPPORTED_REASON: Final[str] = say("capability.unsupported")


def is_supported(platform: str | None = None) -> bool:
    """Return whether this package supports the platform it is running on.

    Parameters
    ----------
    platform : str or None, optional
        A ``sys.platform`` string. Defaults to this machine's.

    Returns
    -------
    bool
        True on Linux and macOS, false everywhere else.

    Examples
    --------
    >>> is_supported("linux"), is_supported("darwin"), is_supported("win32")
    (True, True, False)
    >>> is_supported() in (True, False)
    True
    """
    name = sys.platform if platform is None else platform
    return any(name.startswith(supported) for supported in SUPPORTED_PLATFORMS)


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
            name=say("capability.rapl.name"),
            covers=say("capability.rapl.covers"),
            state=ABSENT,
            detail=say("capability.rapl.absent"),
        )
    if read_package_energy_microjoules() is not None:
        memory = read_memory_energy_microjoules()
        names = ", ".join(sorted({name for name, _ in zones}))
        return Interface(
            name=say("capability.rapl.name"),
            covers=say(
                "capability.rapl.covers.with_memory"
                if memory is not None
                else "capability.rapl.covers.without_memory"
            ),
            state=READS,
            detail=say("capability.rapl.reads", zones=names),
        )
    unreadable = [path.name for _, path in zones if not os.access(path / "energy_uj", os.R_OK)]
    return Interface(
        name=say("capability.rapl.name"),
        covers=say("capability.rapl.covers"),
        state=BLOCKED,
        detail=say(
            "capability.rapl.blocked",
            count=len(unreadable) or len(zones),
            why=say("capability.platypus_note"),
        ),
        remedy=_rapl_remedy(),
    )


def _apple_interface() -> Interface:
    """Return the state of an Apple chip's own energy counters."""
    if apple.available():
        return Interface(
            name=say("capability.apple.name"),
            covers=say("capability.apple.covers"),
            state=READS,
            detail=say("capability.apple.reads"),
        )
    return Interface(
        name=say("capability.apple.name"),
        covers=say("capability.apple.covers"),
        state=ABSENT,
        detail=apple.unavailable_reason() or say("capability.apple.absent"),
    )


def _powermetrics_interface() -> Interface:
    """Return the state of the tool macOS ships behind a password."""
    present = shutil.which("powermetrics") is not None
    return Interface(
        name=say("capability.powermetrics.name"),
        covers=say("capability.powermetrics.covers"),
        state=ROOT_ONLY if present else ABSENT,
        detail=say(_POWERMETRICS_NOTE_KEY if present else "capability.powermetrics.absent"),
    )


def _nvidia_interface() -> Interface:
    """Return the state of NVIDIA's driver."""
    if shutil.which(NVIDIA_SMI) is None:
        return Interface(
            name=say("capability.nvidia.name"),
            covers=say("capability.nvidia.covers"),
            state=ABSENT,
            detail=say("capability.nvidia.absent"),
        )
    if read_accelerator_energy_millijoules() is not None:
        return Interface(
            name=say("capability.nvidia.name"),
            covers=say("capability.nvidia.covers"),
            state=READS,
            detail=say("capability.nvidia.energy"),
        )
    return Interface(
        name=say("capability.nvidia.name"),
        covers=say("capability.nvidia.covers"),
        state=READS,
        detail=say("capability.nvidia.sampled"),
    )


def _graphics_interface() -> Interface:
    """Return the state of the graphics drivers Linux ships."""
    directories = _graphics_hwmon_directories()
    if not directories:
        return Interface(
            name=say("capability.graphics.name"),
            covers=say("capability.graphics.covers"),
            state=ABSENT,
            detail=say("capability.graphics.absent"),
        )
    if read_graphics_energy_microjoules() is not None:
        return Interface(
            name=say("capability.graphics.name"),
            covers=say("capability.graphics.covers"),
            state=READS,
            detail=say("capability.graphics.energy", file=GRAPHICS_ENERGY_FILE),
        )
    if read_graphics_watts() is not None:
        return Interface(
            name=say("capability.graphics.name"),
            covers=say("capability.graphics.covers"),
            state=READS,
            detail=say("capability.graphics.power", file=GRAPHICS_POWER_FILE),
        )
    blocked = [
        path
        for path in directories
        if not os.access(path / GRAPHICS_ENERGY_FILE, os.R_OK)
        and not os.access(path / GRAPHICS_POWER_FILE, os.R_OK)
    ]
    return Interface(
        name=say("capability.graphics.name"),
        covers=say("capability.graphics.covers"),
        state=BLOCKED if blocked else ABSENT,
        detail=say("capability.graphics.blocked"),
        remedy=(
            "sudo chmod a+r "
            f"{directories[0]}/{GRAPHICS_ENERGY_FILE} "
            f"{directories[0]}/{GRAPHICS_POWER_FILE}"
            if blocked
            else None
        ),
    )


def _node_interface() -> Interface:
    """Return the state of the whole-node meters a datacentre has."""
    return Interface(
        name=say("capability.node.name"),
        covers=say("capability.node.covers"),
        state=ROOT_ONLY,
        detail=say("capability.node.detail"),
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


#: How wide this block's paragraphs are set. The explanations here say why a
#: counter is closed and what it would take to open it, and one of them ran to
#: 384 characters on one line -- a terminal turns that into a wall with no left
#: edge to come back to.
_PROSE_WIDTH: Final[int] = 76


def _wrapped(text: str, indent: str = "    ") -> list[str]:
    """Return one paragraph as indented lines, or nothing when it is empty.

    Examples
    --------
    >>> _wrapped("")
    []
    >>> _wrapped("short", indent="  ")
    ['  short']
    """
    if not text:
        return []
    return [f"{indent}{line}" for line in textwrap.wrap(text, width=_PROSE_WIDTH - len(indent))]


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
        lines.extend(_wrapped(say("capability.summary.covers", covers=interface.covers)))
        lines.extend(_wrapped(interface.detail))
        if interface.remedy:
            lines.extend(_wrapped(say("capability.summary.remedy", remedy=interface.remedy)))
        lines.append("")
    if not measurable():
        lines.extend(_wrapped(say("capability.nothing_measures_detail"), indent=""))
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
