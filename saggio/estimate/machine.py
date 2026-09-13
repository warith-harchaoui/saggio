"""
What this machine is, and what the catalogue knows about it.

Module summary
--------------
Before anything can be estimated, the tool has to know what it is running on.
That question is entirely about the operating system, and ``os-helper`` already
answers it on macOS, Linux, and Windows: CPU model and core count, installed
memory, discrete GPUs and their memory, Apple Silicon chip name. This module does
not re-implement any of that. It asks ``os-helper``, then does the one thing
``os-helper`` cannot: match the answers against the power catalogue.

The matching is deliberately explicit about failure. When a CPU or a GPU is not
in the catalogue, the profile says so by name, in
:attr:`MachineProfile.catalog_misses`. That string is the whole contribution
loop: it tells a user, or an agent, exactly which row to look up and add, and it
is the reason a power figure is never quietly invented.

Usage example
-------------
>>> from saggio.estimate.machine import detect_machine
>>> profile = detect_machine()
>>> profile.logical_cores >= 1
True

Author
------
Warith Harchaoui
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Final

import os_helper as osh

from ..catalog.registry import Catalog

#: Substrings that identify a CPU family in the catalogue, tried in order. The
#: first match wins, so the more specific patterns come first.
_CPU_PATTERNS: Final[tuple[tuple[str, str], ...]] = (
    (r"m4\s*max", "apple-m4-max"),
    (r"m3\s*max", "apple-m3-max"),
    (r"m2\s*max", "apple-m2-max"),
    (r"apple\s*m\d", "apple-m-series"),
    (r"epyc.*9654", "epyc-9654"),
    (r"epyc.*7742", "epyc-7742"),
    (r"xeon.*8175", "xeon-platinum-8175"),
    (r"xeon.*6248", "xeon-gold-6248"),
    (r"i9-13900", "core-i9-13900k"),
    (r"ryzen\s*9\s*7950", "ryzen-9-7950x"),
)

#: Substrings that identify a GPU in the catalogue, tried in order.
_GPU_PATTERNS: Final[tuple[tuple[str, str], ...]] = (
    (r"h200", "H200"),
    (r"h100", "H100"),
    (r"b200", "B200"),
    (r"b100", "B100"),
    (r"a100.*80", "A100-80GB"),
    (r"a100.*40", "A100-40GB"),
    (r"a100", "A100"),
    (r"a10g", "A10G"),
    (r"l40s", "L40S"),
    (r"\bl4\b", "L4"),
    (r"\bt4\b", "T4"),
    (r"v100", "V100"),
    (r"p100", "P100"),
    (r"mi325", "MI325X"),
    (r"mi300", "MI300X"),
    (r"mi250", "MI250X"),
    (r"5090", "RTX-5090"),
    (r"4090", "RTX-4090"),
    (r"3090", "RTX-3090"),
    (r"a6000", "RTX-A6000"),
)

#: Catalogue key used when the CPU is recognised as nothing in particular. Which
#: of the two is chosen depends on whether the machine looks like a server.
_FALLBACK_SERVER_CPU: Final[str] = "default-server-cpu"
_FALLBACK_DESKTOP_CPU: Final[str] = "default-desktop-cpu"

#: A machine with at least this many physical cores is assumed to be a server
#: rather than a laptop, which changes the per-core power fallback.
_SERVER_CORE_THRESHOLD: Final[int] = 24


def _match_key(text: str, patterns: tuple[tuple[str, str], ...]) -> str | None:
    """Return the catalogue key whose pattern first matches a device name.

    Parameters
    ----------
    text : str
        A device name as the operating system reports it.
    patterns : tuple
        Pairs of regular expression and catalogue key, in priority order.

    Returns
    -------
    str or None
        The matched key, or ``None`` when nothing matched.

    Examples
    --------
    >>> _match_key("NVIDIA A100-SXM4-80GB", _GPU_PATTERNS)
    'A100-80GB'
    >>> _match_key("Some Unreleased Chip", _GPU_PATTERNS) is None
    True
    """
    lowered = text.lower()
    for pattern, key in patterns:
        if re.search(pattern, lowered):
            return key
    return None


@dataclass(slots=True)
class MachineProfile:
    """What the tool knows about the machine a measurement was taken on.

    Parameters
    ----------
    platform : str
        The operating system name, as ``os_helper.platform_name`` reports it.
    cpu_model : str or None
        The CPU as the operating system names it.
    cpu_key : str or None
        The catalogue key its power figure comes from, or ``None`` when even the
        generic fallback could not be resolved.
    cpu_is_fallback : bool
        Whether ``cpu_key`` is a generic default rather than this actual CPU.
        A report says so, because a generic per-core wattage is a much weaker
        claim than a matched datasheet.
    physical_cores : int
        Physical cores, used for the per-core power estimate.
    logical_cores : int
        Logical cores, reported for context.
    memory_gb : float
        Installed memory in gigabytes.
    gpu_names : tuple of str
        Discrete GPUs as the operating system names them.
    gpu_key : str or None
        The catalogue key of the first GPU, or ``None`` when there is no discrete
        GPU or it is not in the catalogue.
    accelerator_count : int
        How many discrete GPUs are installed.
    apple_chip : str or None
        The Apple Silicon chip name, when this is one.
    catalog_misses : tuple of str
        Devices the operating system reported that the catalogue does not know,
        each as a sentence naming what to add.

    Examples
    --------
    >>> profile = MachineProfile(platform="linux", physical_cores=8, logical_cores=16)
    >>> profile.has_accelerator()
    False
    """

    platform: str
    cpu_model: str | None = None
    cpu_key: str | None = None
    cpu_is_fallback: bool = False
    physical_cores: int = 1
    logical_cores: int = 1
    memory_gb: float = 0.0
    gpu_names: tuple[str, ...] = field(default_factory=tuple)
    gpu_key: str | None = None
    accelerator_count: int = 0
    apple_chip: str | None = None
    catalog_misses: tuple[str, ...] = field(default_factory=tuple)

    def has_accelerator(self) -> bool:
        """Return whether the machine has a discrete GPU.

        Returns
        -------
        bool
            ``True`` when at least one discrete GPU was detected. Apple Silicon
            reports ``False``: its GPU is part of the package the CPU figure
            already covers, so counting it again would double the power.

        Examples
        --------
        >>> MachineProfile("darwin", apple_chip="Apple M2 Max").has_accelerator()
        False
        """
        return self.accelerator_count > 0

    def describe(self) -> str:
        """Return a one-line human description of the machine.

        Returns
        -------
        str
            Something a report can print as the provenance of a measurement.

        Examples
        --------
        >>> MachineProfile("linux", cpu_model="EPYC 7742", physical_cores=64,
        ...                gpu_names=("NVIDIA A100",), accelerator_count=1).describe()
        'EPYC 7742 (64 cores), 1x NVIDIA A100, on linux'
        """
        parts: list[str] = []
        if self.cpu_model:
            parts.append(f"{self.cpu_model} ({self.physical_cores} cores)")
        if self.gpu_names:
            parts.append(f"{self.accelerator_count}x {self.gpu_names[0]}")
        parts.append(f"on {self.platform}")
        return ", ".join(parts)

    def to_mapping(self) -> dict[str, Any]:
        """Serialise the profile for the model's deployment block.

        Returns
        -------
        dict
            Plain values, no numbers that a cost model would have to wrap in a
            quantity: core counts and memory are facts about the machine, not
            costs, and the schema exempts them by path.

        Examples
        --------
        >>> sorted(MachineProfile("linux").to_mapping())[:2]
        ['logical_cores', 'operating_system']
        """
        mapping: dict[str, Any] = {
            "operating_system": self.platform,
            "logical_cores": self.logical_cores,
            "physical_cores": self.physical_cores,
        }
        if self.cpu_model:
            mapping["cpu"] = self.cpu_model
        if self.gpu_names:
            mapping["gpu"] = self.gpu_names[0]
            mapping["accelerator_count"] = self.accelerator_count
        return mapping


def detect_machine(*, overlay: Path | None = None) -> MachineProfile:
    """Inspect the local machine and match it against the power catalogue.

    Every fact here comes from ``os-helper``, which owns the per-operating-system
    probing. This function only translates those facts into catalogue keys and
    records, by name, whatever the catalogue could not match.

    Parameters
    ----------
    overlay : pathlib.Path or None, optional
        Catalogue overlay directory; defaults to the user's own.

    Returns
    -------
    MachineProfile
        What was detected. This function never raises: an unreadable machine
        yields a profile full of ``None``, which is an honest answer, whereas an
        exception in the middle of an audit is not.

    Examples
    --------
    >>> detect_machine().platform in {"darwin", "linux", "windows"}
    True
    """
    try:
        info = osh.hardware_info()
    except Exception as exc:
        osh.warning(f"Could not inspect the local machine: {exc}")
        return MachineProfile(platform=osh.platform_name())

    catalog = Catalog.load("hardware", overlay=overlay)
    known_cpus = catalog.rows("cpus")
    known_gpus = catalog.rows("gpus")
    misses: list[str] = []

    cpu_info = info.get("cpu") if isinstance(info.get("cpu"), dict) else {}
    cpu_model = cpu_info.get("model") or info.get("apple_chip")
    physical = int(cpu_info.get("physical_cores") or 0) or 1
    logical = int(cpu_info.get("logical_cores") or physical)

    cpu_key = _match_key(str(cpu_model), _CPU_PATTERNS) if cpu_model else None
    cpu_is_fallback = False
    if cpu_key is None or cpu_key not in known_cpus:
        if cpu_model:
            misses.append(
                f"CPU {cpu_model!r} is not in the catalogue; add it with "
                f"`saggio catalog add cpu` once you have a datasheet TDP"
            )
        cpu_key = (
            _FALLBACK_SERVER_CPU if physical >= _SERVER_CORE_THRESHOLD else _FALLBACK_DESKTOP_CPU
        )
        cpu_is_fallback = True

    detected_gpus = info.get("gpus") if isinstance(info.get("gpus"), list) else []
    gpu_names = tuple(str(entry.get("name")) for entry in detected_gpus if entry.get("name"))
    gpu_key: str | None = None
    if gpu_names:
        gpu_key = _match_key(gpu_names[0], _GPU_PATTERNS)
        if gpu_key is None or gpu_key not in known_gpus:
            misses.append(
                f"GPU {gpu_names[0]!r} is not in the catalogue; add it with "
                f"`saggio catalog add gpu` once you have a datasheet TDP"
            )
            gpu_key = None

    return MachineProfile(
        platform=str(info.get("platform") or osh.platform_name()),
        cpu_model=str(cpu_model) if cpu_model else None,
        cpu_key=cpu_key,
        cpu_is_fallback=cpu_is_fallback,
        physical_cores=physical,
        logical_cores=logical,
        memory_gb=float(info.get("ram_gb") or 0.0),
        gpu_names=gpu_names,
        gpu_key=gpu_key,
        accelerator_count=len(gpu_names),
        apple_chip=str(info["apple_chip"]) if info.get("apple_chip") else None,
        catalog_misses=tuple(misses),
    )
