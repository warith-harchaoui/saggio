"""Running every counter this machine will answer, over one slice.

Module summary
--------------
The orchestration: start whatever reads here, wait, and turn the difference into
watts with the scope it actually covers. A machine that publishes nothing gets a
reading of nothing rather than a reading of zero, and skips the wait, because
sleeping to measure an absence is time nobody gets back.

Author
------
Warith Harchaoui
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from .. import apple
from .accelerator import AcceleratorSampler, read_accelerator_energy_millijoules
from .graphics import GraphicsSampler, read_graphics_energy_microjoules
from .rapl import (
    package_wrap_range_microjoules,
    read_memory_energy_microjoules,
    read_package_energy_microjoules,
)
from .reading import PowerReading, unavailable_reason
from .soc import _soc_reading
from .tables import (
    _ACCELERATOR_MISSING_NOTE,
    _ACCELERATOR_WRAPPED_NOTE,
    _BOTH_MEASURED_NOTE,
    _MEMORY_MEASURED_NOTE,
    _MICROJOULES_PER_JOULE,
    _MILLIJOULES_PER_JOULE,
    _PACKAGE_MISSING_NOTE,
    _SAMPLE_INTERVAL_MS,
    _WRAP_RECOVERED_NOTE,
    ACCELERATOR_COUNTER_SCOPE,
    ACCELERATOR_SAMPLED_SCOPE,
    GRAPHICS_COUNTER_SCOPE,
    GRAPHICS_SAMPLED_SCOPE,
    RAPL_SCOPE_NOTE,
)


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
