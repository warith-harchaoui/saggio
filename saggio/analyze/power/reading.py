"""What was measured, and what the figure covers.

Module summary
--------------
One reading, carrying the watts, the counters that answered, and the sentence
saying what they cover. A reading that could not be taken is not a reading of
zero, and ``unavailable_reason`` says why rather than leaving a caller to guess.

Author
------
Warith Harchaoui
"""

from __future__ import annotations

from dataclasses import dataclass, field

import os_helper as osh

from .. import apple
from .tables import _UNAVAILABLE_REASON


def unavailable_reason() -> str:
    """Return why this machine cannot report measured power.

    Returns
    -------
    str
        A sentence naming the platform limitation, written into the model so a
        reader does not have to wonder why a figure says ``estimated``.

    Examples
    --------
    >>> "power" in unavailable_reason() or "counter" in unavailable_reason()
    True
    """
    if osh.macos():
        # An Apple Silicon Mac has its own counters and its own reasons for not
        # answering; only an Intel Mac falls back to the powermetrics sentence.
        return apple.unavailable_reason() or _UNAVAILABLE_REASON["darwin"]
    return _UNAVAILABLE_REASON["linux"]


@dataclass(frozen=True, slots=True)
class PowerReading:
    """The outcome of trying to measure power across a run.

    Parameters
    ----------
    watts : float or None
        Average watts over the interval, or ``None`` when nothing was measured.
    joules : float or None
        Energy consumed over the interval, or ``None``.
    scope : str
        What the figure covers, or why there is none.
    by_domain : dict
        Average watts per subsystem, keyed ``cpu``, ``gpu``, ``ane``, ``memory``,
        where the machine publishes them apart. Empty where it publishes one
        number for the lot. This is what lets a figure show where the power went
        instead of asserting a split, and what lets a share of *processor* work
        price the processor's draw rather than the whole chip's.
    sources : tuple of str
        Which counters answered, named the way a reader would name them. A
        figure that covers the processor alone and one that covers the processor
        and the accelerator are different figures, and a model that carries the
        second without saying so invites the reader to compare two numbers that
        were never about the same hardware.

    Examples
    --------
    >>> PowerReading(None, None, "no counter").measured()
    False
    >>> PowerReading(300.0, 600.0, "board", ("accelerator",)).sources
    ('accelerator',)
    """

    watts: float | None
    joules: float | None
    scope: str
    sources: tuple[str, ...] = ()
    by_domain: dict[str, float] = field(default_factory=dict)

    def measured(self) -> bool:
        """Return whether a real figure was obtained.

        Returns
        -------
        bool
            ``True`` when a counter produced a number.

        Examples
        --------
        >>> PowerReading(12.0, 24.0, "RAPL").measured()
        True
        """
        return self.watts is not None
