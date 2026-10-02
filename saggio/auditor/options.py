"""What an audit was asked to do, and what it produced.

Module summary
--------------
The two ends of :func:`saggio.auditor.audit`. Separating them from the work
means a caller can read what the options offer without reading how a slice is
timed, which was most of why the original file was hard to enter.

Author
------
Warith Harchaoui
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from ..analyze.run import (
    DEFAULT_BASELINE_SECONDS,
    DEFAULT_TIMEOUT_SECONDS,
    SliceResult,
)
from ..analyze.static import (
    DEFAULT_CAP_FRACTION,
    RepositoryReading,
)
from ..estimate.extrapolate import (
    DEFAULT_PRECISION,
)
from ..estimate.machine import MachineProfile
from ..model.cost_model import CostModel
from ..model.results import Report


@dataclass(slots=True)
class AuditOptions:
    """What the caller wants the audit to do.

    Parameters
    ----------
    run : bool
        Whether to execute a bounded slice of the repository. Requires the user's
        explicit consent, asked for once and recorded.
    use_llm : bool
        Whether to ask a local model to classify the shape of the work. It never
        supplies a number, and its absence never stops an audit.
    country : str or None
        ISO 3166-1 alpha-2 code where the code runs. Stating it is what turns the
        carbon and money figures from ``TODO`` into numbers.
    provider : str or None
        Provider catalogue key, which sets the datacenter overhead.
    instance : str or None
        Instance catalogue key, used for the power figure when the audit is about
        a machine other than this one.
    timeout_seconds : float
        How long a slice may run before it is stopped.
    cap_fraction : float
        The share of a whole run a capped slice aims for.
    source_accelerator : str or None
        Accelerator the measurement is taken on, when it is not this machine's.
        This is what makes a projection possible from a laptop, which has no
        datacenter GPU and therefore nothing to project from otherwise.
    target_accelerator : str or None
        Accelerator to project onto.
    precision : str
        Numeric precision the workload runs in, which decides whether the
        catalogue's throughput figures apply to it at all.
    baseline_seconds : float
        How long to watch the machine before a slice starts, so that what the
        slice added can be told apart from what the machine was already drawing.
        Zero skips it. `saggio measure` has had this knob since the baseline
        existed; without it here, an audit could not be told to skip a second it
        does not need, and a scaling series could not be told either.
    scaling_steps : int
        How many differently sized slices to run in order to measure how the
        work grows with the job. One, the default, runs the single slice this
        package has always run and keeps the linear assumption, recorded as an
        assumption. Three or more replaces that assumption with a fitted
        exponent and the goodness of its fit, at about 1.3 times the cost of
        the single slice, and refuses to project at all when the fit says the
        slices are not measuring one consistent behaviour.
    fetch_prices : bool
        Whether to look up published rates for the models the code names. Off by
        default, because it is the only thing in an audit that reaches the
        network beyond a local model, and an audit without it must produce the
        same model it produces offline, with the prices left open.
    overlay : pathlib.Path or None
        Catalogue overlay directory.

    Examples
    --------
    >>> AuditOptions(country="FR").provider is None
    True
    """

    run: bool = False
    use_llm: bool = True
    country: str | None = None
    provider: str | None = None
    instance: str | None = None
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS
    cap_fraction: float = DEFAULT_CAP_FRACTION
    source_accelerator: str | None = None
    target_accelerator: str | None = None
    precision: str = DEFAULT_PRECISION
    baseline_seconds: float = DEFAULT_BASELINE_SECONDS
    scaling_steps: int = 1
    fetch_prices: bool = False
    overlay: Path | None = None


@dataclass(slots=True)
class AuditResult:
    """The model an audit produced, and the evidence behind it.

    Parameters
    ----------
    model : CostModel
        The cost model.
    report : Report
        The validation verdict for it.
    reading : RepositoryReading
        What reading the code established.
    machine : MachineProfile
        What machine the audit ran on.
    slice_result : SliceResult or None
        What happened when a slice was run, or ``None`` when none was.
    notes : tuple of str
        Everything the user should read before trusting the model, including
        every catalogue row that is missing and every projection that was refused.

    Examples
    --------
    >>> isinstance(AuditOptions().run, bool)
    True
    """

    model: CostModel
    report: Report
    reading: RepositoryReading
    machine: MachineProfile
    slice_result: SliceResult | None = None
    notes: tuple[str, ...] = field(default_factory=tuple)
