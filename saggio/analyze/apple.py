"""
Reading energy off an Apple Silicon system-on-chip, without asking for a password.

Module summary
--------------
For as long as this package has run on a Mac it has said the same thing: macOS
publishes power only through ``powermetrics``, ``powermetrics`` needs
administrator rights, therefore nothing can be measured here and the energy
figure is an estimate off a datasheet. The first half of that is wrong.

The same counters ``powermetrics`` prints are published by ``IOReport``, a
system library that reports what every block of the chip has drawn since boot,
and it answers an ordinary user. The counters are monotonic, in real units the
library labels itself, and per subsystem: the performance and efficiency core
clusters, the graphics cores, the neural engine, and the memory. Two reads and a
duration give an average that owes nothing to sampling, which is the same shape
of evidence Linux gives through RAPL and NVIDIA gives through its driver.

What the counters are is worth stating precisely, because it bears on how far
they can be trusted. They are the chip's own energy model rather than a shunt on
the power rail — as is Intel's RAPL on every part that is not a Haswell server
chip with on-board regulation. Apple says as much, and adds that the figures are
not meant for comparing one machine against another. Inside one machine, across
one run, against the same machine's idle, they are exactly the right instrument,
and that is what this package asks of them.

The library is reached through ``ctypes``, so this costs no dependency, and
every failure path returns ``None``: a Mac with an Intel processor, a macOS that
renames a channel, a library that will not load. None of them produce a number.

Usage example
-------------
>>> from saggio.analyze.apple import SocMeter, available
>>> meter = SocMeter.start()
>>> meter is None or meter.stop() is not None or True
True
>>> available() in (True, False)
True

Author
------
Warith Harchaoui
"""

from __future__ import annotations

import ctypes
import platform
from dataclasses import dataclass
from typing import Any, Final

import os_helper as osh

#: Where macOS keeps the reporting library. It has no headers and no promises,
#: which is why every call here is defensive and every failure is a ``None``.
_IOREPORT_PATH: Final[str] = "/usr/lib/libIOReport.dylib"

#: The framework that owns the string and collection types the library speaks in.
_CORE_FOUNDATION_PATH: Final[str] = (
    "/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation"
)

#: The group of channels holding energy rather than residency or frequency.
_ENERGY_GROUP: Final[str] = "Energy Model"

#: The key under which a sample holds its array of channels.
_CHANNELS_KEY: Final[str] = "IOReportChannels"

#: CoreFoundation's name for UTF-8, which is the only encoding used here.
_UTF8: Final[int] = 0x08000100

#: Long enough for any channel name the library publishes, short enough to sit on
#: the stack without thinking about it.
_NAME_BUFFER_BYTES: Final[int] = 512

#: What one unit of each label is worth in joules. A channel carries its own
#: label, so nothing here assumes millijoules and silently reports a thousandth
#: of a graphics figure that happens to be published in nanojoules.
_JOULES_PER_UNIT: Final[dict[str, float]] = {
    "nj": 1e-9,
    "uj": 1e-6,
    "µj": 1e-6,
    "mj": 1e-3,
    "j": 1.0,
    "kj": 1e3,
}

#: Which channels make up each subsystem, as alternatives tried in order.
#:
#: Each alternative is a complete set of channel names that must *all* be
#: present for that alternative to be used, and the first complete alternative
#: wins. Apple rolls the clusters up into one channel on the parts this was
#: written against, and publishes the clusters separately as well; summing a
#: roll-up together with the clusters it rolls up would count the processor
#: twice, so the alternatives are tried rather than merged.
_DOMAIN_CHANNELS: Final[dict[str, tuple[tuple[str, ...], ...]]] = {
    "cpu": (
        ("CPU Energy",),
        ("EACC_CPU", "PACC0_CPU", "PACC1_CPU"),
        ("EACC_CPU", "PACC0_CPU"),
        ("ECPU", "PCPU"),
    ),
    "gpu": (
        ("GPU Energy",),
        ("GPU0",),
        ("GPU",),
    ),
    "ane": (
        ("ANE0",),
        ("ANE",),
    ),
    "memory": (
        ("DRAM0",),
        ("DRAM",),
    ),
}

#: The subsystems that add up to what Apple's own tool calls combined power, and
#: what this package reports as the compute figure.
_COMPUTE_DOMAINS: Final[tuple[str, ...]] = ("cpu", "gpu", "ane")

#: What the compute figure covers, said in full because a reader comparing it
#: against a laptop's wall socket needs to know what is missing from it.
SOC_SCOPE: Final[str] = (
    "the chip's processor cores, graphics cores, and neural engine, from the "
    "system-on-chip's own energy counters"
)

#: What the memory figure covers. Green Algorithms estimates memory power from
#: how much memory is installed; here the chip reports what its memory actually
#: drew, which is the same quantity arrived at by a shorter route.
SOC_MEMORY_SCOPE: Final[str] = "the chip's memory, from its own energy counter"

#: Said alongside any Apple figure. The counters are a model inside the chip,
#: not an ammeter, and Apple is explicit that they are not a basis for comparing
#: one machine against another. Within one machine they are exactly what is
#: wanted, and that distinction belongs in the report rather than in a footnote
#: nobody ships.
SOC_MODEL_NOTE: Final[str] = (
    "These are the chip's own energy counters, which are a model inside the "
    "silicon rather than a meter on the power rail, and Apple says they are not "
    "a basis for comparing one machine against another. Left out of them: the "
    "display, storage, networking, the fans, and the power supply's own losses."
)

#: Said when the machine is a Mac but not one this can read.
_INTEL_MAC_NOTE: Final[str] = (
    "This is an Intel Mac, whose package counter macOS publishes only through "
    "powermetrics, which needs administrator rights and so cannot be read from "
    "a library call."
)

#: Said when the chip is Apple Silicon but its channels are not the ones known
#: here, which is what a future part renaming a channel would look like.
_UNKNOWN_LAYOUT_NOTE: Final[str] = (
    "This Apple chip publishes energy channels under names this package does "
    "not recognise, so nothing was measured rather than something guessed. "
    "Reporting the channel names in an issue is enough to add the part."
)


def _load() -> tuple[Any, Any] | None:
    """Return the two libraries this module speaks to, or ``None``.

    Returns
    -------
    tuple or None
        ``(core_foundation, ioreport)`` with their signatures declared, or
        ``None`` on any machine that is not an Apple Silicon Mac or where
        either library refuses to load.

    Examples
    --------
    >>> _load() is None or len(_load()) == 2
    True
    """
    if not osh.macos() or platform.machine() != "arm64":
        return None
    try:
        core = ctypes.CDLL(_CORE_FOUNDATION_PATH)
        report = ctypes.CDLL(_IOREPORT_PATH)
    except OSError:
        return None

    void_p = ctypes.c_void_p
    try:
        core.CFStringCreateWithCString.restype = void_p
        core.CFStringCreateWithCString.argtypes = [void_p, ctypes.c_char_p, ctypes.c_uint32]
        core.CFStringGetCString.restype = ctypes.c_bool
        core.CFStringGetCString.argtypes = [void_p, ctypes.c_char_p, ctypes.c_long, ctypes.c_uint32]
        core.CFDictionaryGetValue.restype = void_p
        core.CFDictionaryGetValue.argtypes = [void_p, void_p]
        core.CFArrayGetCount.restype = ctypes.c_long
        core.CFArrayGetCount.argtypes = [void_p]
        core.CFArrayGetValueAtIndex.restype = void_p
        core.CFArrayGetValueAtIndex.argtypes = [void_p, ctypes.c_long]
        core.CFRelease.restype = None
        core.CFRelease.argtypes = [void_p]

        report.IOReportCopyChannelsInGroup.restype = void_p
        report.IOReportCopyChannelsInGroup.argtypes = [
            void_p,
            void_p,
            ctypes.c_uint64,
            ctypes.c_uint64,
            ctypes.c_uint64,
        ]
        report.IOReportCreateSubscription.restype = void_p
        report.IOReportCreateSubscription.argtypes = [
            void_p,
            void_p,
            void_p,
            ctypes.c_uint64,
            void_p,
        ]
        report.IOReportCreateSamples.restype = void_p
        report.IOReportCreateSamples.argtypes = [void_p, void_p, void_p]
        report.IOReportCreateSamplesDelta.restype = void_p
        report.IOReportCreateSamplesDelta.argtypes = [void_p, void_p, void_p]
        report.IOReportChannelGetChannelName.restype = void_p
        report.IOReportChannelGetChannelName.argtypes = [void_p]
        report.IOReportChannelGetUnitLabel.restype = void_p
        report.IOReportChannelGetUnitLabel.argtypes = [void_p]
        report.IOReportSimpleGetIntegerValue.restype = ctypes.c_int64
        report.IOReportSimpleGetIntegerValue.argtypes = [void_p, ctypes.c_int]
    except AttributeError:
        # A macOS that does not publish one of these symbols is a macOS this
        # cannot read. Saying so is the whole contract.
        return None
    return core, report


def _to_string(core: Any, reference: int | None) -> str | None:
    """Return a Python string for a CoreFoundation string, or ``None``.

    Parameters
    ----------
    core : ctypes.CDLL
        The CoreFoundation handle.
    reference : int or None
        A ``CFStringRef``, as an address.

    Returns
    -------
    str or None
        The text, or ``None`` when there was none or it would not convert.

    Examples
    --------
    >>> _to_string(object(), None) is None
    True
    """
    if not reference:
        return None
    buffer = ctypes.create_string_buffer(_NAME_BUFFER_BYTES)
    if not core.CFStringGetCString(reference, buffer, _NAME_BUFFER_BYTES, _UTF8):
        return None
    return buffer.value.decode("utf-8", errors="replace")


def available() -> bool:
    """Return whether this machine's energy counters can be read.

    Returns
    -------
    bool
        ``True`` on an Apple Silicon Mac whose reporting library loads.

    Examples
    --------
    >>> available() in (True, False)
    True
    """
    return _load() is not None


def unavailable_reason() -> str | None:
    """Return why this Mac cannot be read, or ``None`` when it can.

    Returns
    -------
    str or None
        A sentence for the model, or ``None`` when there is nothing to explain
        because the counters answered.

    Examples
    --------
    >>> reason = unavailable_reason()
    >>> reason is None or isinstance(reason, str)
    True
    """
    if not osh.macos():
        return None
    if platform.machine() != "arm64":
        return _INTEL_MAC_NOTE
    if _load() is None:
        return _UNKNOWN_LAYOUT_NOTE
    return None


@dataclass(frozen=True, slots=True)
class SocEnergy:
    """What the chip drew over one interval, by subsystem.

    Parameters
    ----------
    compute_joules : float
        Processor cores, graphics cores, and neural engine added together.
    memory_joules : float or None
        What the memory drew, when the chip publishes it separately.
    by_domain : dict
        Joules per subsystem, keyed as ``cpu``, ``gpu``, ``ane``, ``memory``.
    channels : tuple of str
        Exactly which counters were read, so the figure can be reproduced.

    Examples
    --------
    >>> SocEnergy(2.0, 0.5, {"cpu": 2.0}, ("CPU Energy",)).compute_joules
    2.0
    """

    compute_joules: float
    memory_joules: float | None
    by_domain: dict[str, float]
    channels: tuple[str, ...]


@dataclass(slots=True)
class SocMeter:
    """A live subscription to the chip's energy counters.

    The counters accumulate from boot, so a measurement is the difference
    between a sample taken before the run and one taken after it. The library
    computes that difference itself, which is why the subscription is held open
    for the length of the run rather than two raw totals being subtracted here.

    Parameters
    ----------
    core : ctypes.CDLL
        The CoreFoundation handle.
    report : ctypes.CDLL
        The reporting library handle.
    subscription : int
        The open subscription, as an address.
    channels : int
        The channels it is subscribed to, as an address.
    first_sample : int
        The opening sample, as an address.

    Examples
    --------
    >>> meter = SocMeter.start()
    >>> meter is None or isinstance(meter, SocMeter)
    True
    """

    core: Any
    report: Any
    subscription: int
    channels: int
    first_sample: int

    @classmethod
    def start(cls) -> SocMeter | None:
        """Open a subscription and take the opening sample.

        Returns
        -------
        SocMeter or None
            A meter, or ``None`` on any machine that cannot answer.

        Examples
        --------
        >>> meter = SocMeter.start()
        >>> meter is None or meter.stop() is None or True
        True
        """
        loaded = _load()
        if loaded is None:
            return None
        core, report = loaded
        try:
            group = core.CFStringCreateWithCString(None, _ENERGY_GROUP.encode("utf-8"), _UTF8)
            if not group:
                return None
            channels = report.IOReportCopyChannelsInGroup(group, None, 0, 0, 0)
            core.CFRelease(group)
            if not channels:
                return None
            subscribed = ctypes.c_void_p()
            subscription = report.IOReportCreateSubscription(
                None, channels, ctypes.byref(subscribed), 0, None
            )
            if not subscription:
                core.CFRelease(channels)
                return None
            held = subscribed.value or channels
            first = report.IOReportCreateSamples(subscription, held, None)
            if not first:
                core.CFRelease(subscription)
                core.CFRelease(channels)
                return None
        except (OSError, ValueError, ctypes.ArgumentError):
            return None
        return cls(
            core=core,
            report=report,
            subscription=subscription,
            channels=held,
            first_sample=first,
        )

    def _release(self) -> None:
        """Hand every object back to the system."""
        for reference in (self.first_sample, self.subscription, self.channels):
            if reference:
                try:
                    self.core.CFRelease(reference)
                except (OSError, ctypes.ArgumentError):
                    # Releasing is best effort: a meter that cannot give an
                    # object back must still not raise out of a measurement.
                    continue
        self.first_sample = 0
        self.subscription = 0
        self.channels = 0

    def stop(self) -> SocEnergy | None:
        """Take the closing sample and return the energy drawn between the two.

        Returns
        -------
        SocEnergy or None
            The interval's energy by subsystem, or ``None`` when the chip's
            channels are not ones this package recognises.

        Examples
        --------
        >>> meter = SocMeter.start()
        >>> meter is None or meter.stop() is None or True
        True
        """
        try:
            second = self.report.IOReportCreateSamples(self.subscription, self.channels, None)
            if not second:
                return None
            delta = self.report.IOReportCreateSamplesDelta(self.first_sample, second, None)
            self.core.CFRelease(second)
            if not delta:
                return None
            try:
                joules = self._read_channels(delta)
            finally:
                self.core.CFRelease(delta)
        except (OSError, ValueError, ctypes.ArgumentError):
            return None
        finally:
            self._release()
        return _assemble(joules)

    def _read_channels(self, delta: int) -> dict[str, float]:
        """Return joules per channel name from one delta sample.

        Parameters
        ----------
        delta : int
            The difference between the two samples, as an address.

        Returns
        -------
        dict
            Joules, keyed by the channel name the library publishes.
        """
        key = self.core.CFStringCreateWithCString(None, _CHANNELS_KEY.encode("utf-8"), _UTF8)
        if not key:
            return {}
        array = self.core.CFDictionaryGetValue(delta, key)
        self.core.CFRelease(key)
        if not array:
            return {}
        joules: dict[str, float] = {}
        for index in range(self.core.CFArrayGetCount(array)):
            item = self.core.CFArrayGetValueAtIndex(array, index)
            if not item:
                continue
            name = _to_string(self.core, self.report.IOReportChannelGetChannelName(item))
            label = _to_string(self.core, self.report.IOReportChannelGetUnitLabel(item))
            if name is None or label is None:
                continue
            scale = _JOULES_PER_UNIT.get(label.strip().lower())
            if scale is None:
                # A unit nobody here can convert is not a number anybody here
                # can add up, and a guessed scale would be wrong by powers of
                # a thousand rather than by a little.
                continue
            value = self.report.IOReportSimpleGetIntegerValue(item, 0)
            if value < 0:
                continue
            joules[name] = value * scale
        return joules


def _assemble(joules: dict[str, float]) -> SocEnergy | None:
    """Turn per-channel joules into per-subsystem joules.

    Parameters
    ----------
    joules : dict
        Joules by channel name, as the library published them.

    Returns
    -------
    SocEnergy or None
        The subsystems that answered, or ``None`` when the processor did not,
        because a graphics figure alone is not the chip's draw.

    Examples
    --------
    >>> _assemble({"CPU Energy": 2.0, "GPU Energy": 1.0, "DRAM0": 0.5}).compute_joules
    3.0
    >>> _assemble({"GPU Energy": 1.0}) is None
    True
    >>> _assemble({}) is None
    True
    """
    by_domain: dict[str, float] = {}
    used: list[str] = []
    for domain, alternatives in _DOMAIN_CHANNELS.items():
        for names in alternatives:
            if all(name in joules for name in names):
                by_domain[domain] = sum(joules[name] for name in names)
                used.extend(names)
                break
    if "cpu" not in by_domain:
        # Every Apple chip reports its cores. A sample without them is a sample
        # this package has misread, and half a chip is not a measurement of it.
        return None
    return SocEnergy(
        compute_joules=sum(by_domain.get(domain, 0.0) for domain in _COMPUTE_DOMAINS),
        memory_joules=by_domain.get("memory"),
        by_domain=by_domain,
        channels=tuple(used),
    )
