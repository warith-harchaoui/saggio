"""Turning an Apple chip's counters into a reading.

Module summary
--------------
Apple Silicon publishes per-subsystem energy through ``IOReport``, which is
richer than a single package figure: processor cores, graphics cores, the
neural engine and memory each answer separately. Memory is measured rather than
estimated there, which is a different and better quantity than the one Green
Algorithms derives from how much memory is installed.

Author
------
Warith Harchaoui
"""

from __future__ import annotations

from .. import apple
from .reading import PowerReading
from .tables import _MEMORY_MEASURED_NOTE


def _soc_reading(energy: apple.SocEnergy, *, seconds: float) -> PowerReading:
    """Turn an Apple chip's counters into a reading, naming what was read.

    Parameters
    ----------
    energy : saggio.analyze.apple.SocEnergy
        What the chip drew over the run, by subsystem.
    seconds : float
        Wall-clock duration, which the caller timed.

    Returns
    -------
    PowerReading
        Average watts over the run, with the channels that produced it named so
        the figure can be reproduced by anybody with the same machine.

    Examples
    --------
    >>> from saggio.analyze.apple import SocEnergy
    >>> reading = _soc_reading(
    ...     SocEnergy(20.0, 4.0, {"cpu": 18.0, "gpu": 2.0, "memory": 4.0},
    ...               ("CPU Energy", "GPU Energy", "DRAM0")),
    ...     seconds=2.0)
    >>> reading.watts, reading.sources
    (12.0, ('system-on-chip', 'memory'))
    """
    joules = energy.compute_joules + (energy.memory_joules or 0.0)
    sources = ["system-on-chip"]
    scopes = [
        f"The figure covers {apple.SOC_SCOPE}, read from the {', '.join(energy.channels)} counters."
    ]
    if energy.memory_joules is not None:
        sources.append("memory")
        scopes[0] = (
            f"The figure covers {apple.SOC_SCOPE} and {apple.SOC_MEMORY_SCOPE}, "
            f"read from the {', '.join(energy.channels)} counters."
        )
        scopes.append(_MEMORY_MEASURED_NOTE)
    scopes.append(apple.SOC_MODEL_NOTE)
    return PowerReading(
        watts=joules / seconds,
        joules=joules,
        scope=" ".join(scopes),
        sources=tuple(sources),
        # The chip counts these apart, so there is no reason to add them up and
        # then guess the split back out again.
        by_domain={
            domain: value / seconds for domain, value in energy.by_domain.items() if seconds > 0.0
        },
    )
