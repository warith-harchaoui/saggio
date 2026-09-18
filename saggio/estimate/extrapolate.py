"""
Projections: from a slice to a whole run, and from one machine to another.

Module summary
--------------
Two questions come up the moment a measurement exists, and both are projections
rather than measurements, so both have to say what they assumed.

*What would the whole run cost?* Nobody waits three days for a training job to
finish before they can write down its cost. They run a hundredth of it and divide.
That is defensible when the work is uniform, which is why
:func:`project_to_completion` records that assumption instead of hiding it, and
refuses a fraction outside the interval where the arithmetic means anything.

*What would it cost on a different machine?* Swapping a laptop's figure for a
datacenter GPU's is not a matter of swapping wattages: a faster chip finishes
sooner, so it draws more power for less time. :func:`project_to_machine` scales
runtime by the ratio of peak throughputs and power by the target's board power,
which is only sound while the work is compute-bound and the precision matches the
one the catalogue's throughput figures are quoted at. When either condition is
not met, it refuses and says which one.

A projection is never stronger than ``estimated``, whatever it was projected
from. A measurement of something else is not a measurement of this.

Usage example
-------------
>>> from saggio.estimate.extrapolate import project_to_completion
>>> from saggio.model import Quantity
>>> slice_energy = Quantity(value=0.5, unit="kWh", status="measured")
>>> whole = project_to_completion(slice_energy, fraction=0.01)
>>> whole.quantity.value, whole.quantity.status
(50.0, 'estimated')

Author
------
Warith Harchaoui
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Final

from ..catalog.registry import Catalog
from ..model.quantity import Quantity
from ..model.taxonomy import ESTIMATED, TODO, status_strength, weakest

#: Which catalogue column quotes peak throughput at which precision. The relative
#: advantage between two chips changes with precision — an H100 pulls much further
#: ahead of an A100 in BF16 than it does in FP32 — so a projection reads the
#: column for the precision the work actually runs in, and refuses when the
#: catalogue has not been given one, rather than scaling by a figure about
#: different arithmetic.
THROUGHPUT_COLUMNS: Final[dict[str, str]] = {
    "bf16": "peak_bf16_tflops",
    "bfloat16": "peak_bf16_tflops",
    "fp16": "peak_bf16_tflops",
    "float16": "peak_bf16_tflops",
    "fp8": "peak_fp8_tflops",
    "fp32": "peak_fp32_tflops",
    "tf32": "peak_tf32_tflops",
    "int8": "peak_int8_tops",
}

#: The precisions this package knows how to ask about at all.
THROUGHPUT_PRECISIONS: Final[frozenset[str]] = frozenset(THROUGHPUT_COLUMNS)

#: Said when a half-precision workload is scaled by the BF16 column. NVIDIA and
#: AMD quote one dense tensor-core rate covering both for the parts in this
#: catalogue; a part where they differ needs its own column before it is added.
_HALF_PRECISIONS_SHARE_A_COLUMN: Final[str] = (
    "FP16 and BF16 are scaled by the same catalogue column, because the vendors "
    "quote one dense tensor-core rate covering both for these parts."
)

#: The catalogue column holding peak memory bandwidth, which is the other half of
#: what limits a workload and the half that a peak-FLOP/s ratio ignores.
BANDWIDTH_COLUMN: Final[str] = "memory_bandwidth_gbps"

#: The catalogue column holding the board's own memory. A smaller target is not a
#: refusal, because nothing here knows how much memory the run actually used, but
#: it is the first thing that would stop the projected run from starting and the
#: reader has to be told before they act on the number.
MEMORY_COLUMN: Final[str] = "memory_gb"

#: Default precision assumed for a training or inference workload when nothing
#: says otherwise. Mixed-precision training in BF16 is the common case, and the
#: assumption is written into every projection that relies on it.
DEFAULT_PRECISION: Final[str] = "bf16"

#: A projection may claim at most this status, however strong its input was.
_PROJECTION_CEILING: Final[str] = ESTIMATED


@dataclass(slots=True)
class Projection:
    """The result of a projection: a number, its method, and its limits.

    Parameters
    ----------
    quantity : Quantity
        The projected value, or a ``TODO`` when the projection was refused.
    method : str
        One sentence naming the arithmetic, so a reader can redo it.
    assumptions : tuple of str
        What had to be true for the arithmetic to mean anything.
    limits : tuple of str
        Where the projection stops being trustworthy.
    refused : bool
        Whether the projection was declined rather than computed. A refusal with
        a reason is a better answer than a number with a caveat nobody reads.
    bounds : tuple of Quantity or None
        The fastest and the slowest the projection could honestly be, when the
        evidence brackets rather than pins it. A single number for "what would
        this cost on an H100" is a claim nobody can support; the two ends of the
        bracket are claims that can be, and the reader can see how wide they are.

    Examples
    --------
    >>> Projection(Quantity(status="TODO"), "n/a", refused=True).refused
    True
    """

    quantity: Quantity
    method: str
    assumptions: tuple[str, ...] = field(default_factory=tuple)
    limits: tuple[str, ...] = field(default_factory=tuple)
    refused: bool = False
    bounds: tuple[Quantity, Quantity] | None = None

    def to_mapping(self) -> dict[str, Any]:
        """Serialise the projection for a model's projections block.

        The projected quantity is nested under ``result`` rather than ``value``,
        because a mapping with a ``value`` key *is* a quantity as far as the rest
        of this package is concerned, and a projection carrying its method and its
        limits alongside would be read as a quantity with four invented fields.

        Returns
        -------
        dict
            A mapping with the quantity under ``result``, plus the method,
            assumptions, and limits as prose.

        Examples
        --------
        >>> sorted(Projection(Quantity(status="TODO"), "m").to_mapping())
        ['method', 'result']
        """
        mapping: dict[str, Any] = {"method": self.method, "result": self.quantity.to_mapping()}
        if self.bounds is not None:
            fastest, slowest = self.bounds
            mapping["bounds"] = {
                "fastest": fastest.to_mapping(),
                "slowest": slowest.to_mapping(),
            }
        if self.assumptions:
            mapping["assumptions"] = list(self.assumptions)
        if self.limits:
            mapping["limits"] = list(self.limits)
        if self.refused:
            mapping["refused"] = True
        return mapping


def _cap(status: str | None) -> str:
    """Return a status capped at what a projection may claim.

    Parameters
    ----------
    status : str or None
        The status of the measurement being projected.

    Returns
    -------
    str
        ``estimated`` at best, or the input status when it was already weaker.

    Examples
    --------
    >>> _cap("measured")
    'estimated'
    >>> _cap("TODO")
    'TODO'
    """
    if status is None:
        return _PROJECTION_CEILING
    if status_strength(status) > status_strength(_PROJECTION_CEILING):
        return _PROJECTION_CEILING
    return status


def _refusal(unit: str | None, currency: str | None, reason: str) -> Projection:
    """Return a refused projection carrying the reason it was refused.

    Parameters
    ----------
    unit : str or None
        The unit the result would have had.
    currency : str or None
        The currency it would have carried.
    reason : str
        Why the projection was declined, phrased as something to act on.

    Returns
    -------
    Projection
        A refusal.

    Examples
    --------
    >>> _refusal("kWh", None, "fraction is zero").refused
    True
    """
    return Projection(
        quantity=Quantity(unit=unit, currency=currency, status=TODO, notes=reason),
        method="Refused.",
        refused=True,
    )


def project_to_completion(measured: Quantity, *, fraction: float) -> Projection:
    """Project a measured slice of a run to the whole of it.

    Parameters
    ----------
    measured : Quantity
        What the slice cost, on any dimension.
    fraction : float
        How much of the whole run the slice represents, in the interval ``(0, 1]``.
        A fraction of ``0.001`` means the slice was a thousandth of the work.

    Returns
    -------
    Projection
        The whole-run figure, or a refusal. A fraction outside ``(0, 1]`` is
        refused: zero would divide by nothing, and more than one would mean the
        slice was larger than the run it came from.

    Examples
    --------
    >>> whole = project_to_completion(Quantity(value=2.0, unit="kWh", status="measured"),
    ...                               fraction=0.25)
    >>> whole.quantity.value
    8.0
    >>> project_to_completion(Quantity(value=1.0, status="measured"), fraction=0.0).refused
    True
    >>> project_to_completion(Quantity(value=1.0, status="measured"), fraction=1.5).refused
    True
    """
    if not measured.is_known():
        return _refusal(
            measured.unit,
            measured.currency,
            "The slice carries no number, so there is nothing to project.",
        )
    if not 0.0 < fraction <= 1.0:
        return _refusal(
            measured.unit,
            measured.currency,
            f"A completed fraction of {fraction!r} is outside (0, 1]; "
            "it must be the share of the whole run that was actually executed.",
        )

    percent = fraction * 100.0
    return Projection(
        quantity=Quantity(
            value=float(measured.value) / fraction,
            unit=measured.unit,
            currency=measured.currency,
            status=_cap(measured.status),
            notes=f"Projected from a slice covering {percent:g}% of the run.",
        ),
        method=f"Whole run = measured slice / {fraction:g}.",
        assumptions=(
            "The remaining work costs the same per unit as the slice that was run.",
            "Warm-up, checkpointing, and data loading are spread evenly across the run.",
        ),
        limits=(
            "A run whose later stages differ in shape, such as a learning-rate "
            "schedule that changes batch size, will not scale linearly.",
            "One-off costs paid entirely inside the slice are counted as though "
            "they recurred throughout.",
        ),
    )


def project_to_machine(
    *,
    runtime: Quantity,
    source_key: str,
    target_key: str,
    precision: str = DEFAULT_PRECISION,
    compute_bound: bool | None = None,
    overlay_catalog: Catalog | None = None,
) -> Projection:
    """Project a runtime measured on one accelerator onto another.

    Two things limit a workload on an accelerator, and a projection that knows
    about only one of them is optimistic by construction. Arithmetic throughput
    limits work that keeps the tensor cores fed; memory bandwidth limits work that
    spends its time moving weights and activations. Between an A100 and an H100
    those two ratios are 3.2 and 2.2, and real training runs land between them
    while single-stream generation lands near the lower one. Reporting the peak
    FLOP/s ratio alone would overstate the speed-up by half and understate the
    cost of the run in the same proportion.

    So this computes both and reports a bracket. The point estimate is the
    compute ratio when the workload was read as compute-bound, the bandwidth ratio
    when it was read as memory-bound, and the slower of the two when nothing
    established which — because the slower ratio is the longer run, the larger
    bill, and the number a reader is not harmed by having believed.

    Parameters
    ----------
    runtime : Quantity
        Seconds measured on the source accelerator.
    source_key : str
        Catalogue key of the accelerator the measurement came from.
    target_key : str
        Catalogue key of the accelerator to project onto.
    precision : str, optional
        The numeric precision the workload runs in. The catalogue is read for the
        column quoting throughput at that precision, and the projection is refused
        when no such column has been filled in for either part.
    compute_bound : bool or None, optional
        Whether the workload is limited by arithmetic rather than by memory.
        ``None`` means nobody established it, and the conservative end is used.
    overlay_catalog : Catalog or None, optional
        A pre-loaded hardware catalogue.

    Returns
    -------
    Projection
        The projected runtime with its bracket, or a refusal naming exactly what
        is missing: the source row, the target row, a throughput column, or a
        precision this package does not know.

    Examples
    --------
    >>> projected = project_to_machine(
    ...     runtime=Quantity(value=1000.0, unit="s", status="measured"),
    ...     source_key="A100", target_key="H100")
    >>> round(projected.quantity.value, 1)
    464.2
    >>> round(projected.bounds[0].value, 1), round(projected.bounds[1].value, 1)
    (315.5, 464.2)
    >>> compute = project_to_machine(
    ...     runtime=Quantity(value=1000.0, unit="s", status="measured"),
    ...     source_key="A100", target_key="H100", compute_bound=True)
    >>> round(compute.quantity.value, 1)
    315.5
    >>> project_to_machine(runtime=Quantity(value=1.0, status="measured"),
    ...                    source_key="A100", target_key="H100",
    ...                    precision="fp32").refused
    True
    >>> project_to_machine(runtime=Quantity(value=1.0, status="measured"),
    ...                    source_key="A100", target_key="NOT-A-GPU").refused
    True
    """
    if not runtime.is_known():
        return _refusal(
            runtime.unit, None, "The runtime carries no number, so there is nothing to project."
        )

    column = THROUGHPUT_COLUMNS.get(precision.lower())
    if column is None:
        listed = ", ".join(sorted(THROUGHPUT_PRECISIONS))
        return _refusal(
            runtime.unit,
            None,
            f"{precision} is not a precision this package knows how to look up. Known: {listed}.",
        )

    catalog = overlay_catalog if overlay_catalog is not None else Catalog.load("hardware")
    rows = catalog.rows("gpus")
    missing = [key for key in (source_key, target_key) if key not in rows]
    if missing:
        listed = ", ".join(sorted(rows))
        return _refusal(
            runtime.unit,
            None,
            f"{' and '.join(repr(key) for key in missing)} not in the hardware catalogue. "
            f"Known accelerators: {listed}. Add the missing one with "
            "`saggio catalog add gpu`.",
        )

    source_row, target_row = rows[source_key], rows[target_key]
    source_throughput = source_row.get(column)
    target_throughput = target_row.get(column)
    without = [
        key
        for key, value in ((source_key, source_throughput), (target_key, target_throughput))
        if not value
    ]
    if without:
        return _refusal(
            runtime.unit,
            None,
            f"The catalogue has no {column} for {' and '.join(repr(key) for key in without)}, "
            f"so there is no {precision} ratio to scale by. Two chips do not keep the same "
            "ratio across precisions, so scaling this by another precision's figure would be "
            f"a different claim than the one asked for. Add it with `saggio catalog add gpu "
            f"{without[0]} --field {column}=...` from the vendor datasheet, or measure on "
            "the target.",
        )

    compute_speedup = float(target_throughput) / float(source_throughput)
    source_bandwidth = source_row.get(BANDWIDTH_COLUMN)
    target_bandwidth = target_row.get(BANDWIDTH_COLUMN)
    bandwidth_speedup = (
        float(target_bandwidth) / float(source_bandwidth)
        if source_bandwidth and target_bandwidth
        else None
    )

    assumptions = [
        "Both accelerators reach a similar share of their own peak on this workload.",
        "The target has enough memory to hold the same working set, which the "
        "catalogue can contradict but cannot confirm.",
        "One accelerator, and the same batch size and parallelism as were measured.",
    ]
    if precision.lower() in {"fp16", "float16"}:
        assumptions.insert(0, _HALF_PRECISIONS_SHARE_A_COLUMN)
    source_memory = source_row.get(MEMORY_COLUMN)
    target_memory = target_row.get(MEMORY_COLUMN)
    limits = []
    if source_memory and target_memory and float(target_memory) < float(source_memory):
        limits.append(
            f"{target_key} has {float(target_memory):g} GB of memory against "
            f"{float(source_memory):g} GB on {source_key}. Nothing here knows how "
            "much of it the measured run used, so this is a duration for a run that may "
            "not start at all. Check the working set before quoting the figure."
        )
    limits += [
        "Peak throughput and peak bandwidth are datasheet figures, not benchmarks. "
        "A real run reaches a fraction of either, and the fraction differs by chip.",
        "A workload bound by storage, by the data loader, or by the host processor "
        "will not gain from either ratio, and may gain nothing at all.",
        "Multi-accelerator scaling, interconnect, and communication overhead are "
        "not modelled here.",
    ]

    compute_basis = (
        f"the peak {precision} throughput ratio, "
        f"{target_throughput:g} / {source_throughput:g} TFLOP/s"
    )
    bandwidth_basis = (
        "the memory bandwidth ratio, "
        f"{float(target_bandwidth or 0):g} / {float(source_bandwidth or 0):g} GB/s"
    )

    if bandwidth_speedup is None:
        chosen = compute_speedup
        basis = compute_basis
        bounds = None
        limits.insert(
            0,
            f"The catalogue has no {BANDWIDTH_COLUMN} for one of these parts, so nothing "
            "brackets this from below. It is the compute-bound end of the range: an upper "
            "bound on the speed-up, and therefore a lower bound on what the run costs.",
        )
    else:
        fastest_speedup = max(compute_speedup, bandwidth_speedup)
        slowest_speedup = min(compute_speedup, bandwidth_speedup)
        if compute_bound is True:
            chosen = compute_speedup
            basis = f"{compute_basis}, the workload having been read as bound by arithmetic"
        elif compute_bound is False:
            chosen = bandwidth_speedup
            basis = (
                f"{bandwidth_basis}, the workload having been read as bound by memory "
                "rather than by arithmetic"
            )
        else:
            chosen = slowest_speedup
            slower = compute_basis if compute_speedup <= bandwidth_speedup else bandwidth_basis
            basis = (
                f"the slower of the two ratios ({slower}), nothing having established "
                "which of arithmetic and memory limits this workload"
            )
        bounds = (
            Quantity(
                value=float(runtime.value) / fastest_speedup,
                unit=runtime.unit or "s",
                status=_cap(weakest(runtime.status, ESTIMATED)),
                notes=f"Best case: every part of the run gains the full {fastest_speedup:.2f}x.",
            ),
            Quantity(
                value=float(runtime.value) / slowest_speedup,
                unit=runtime.unit or "s",
                status=_cap(weakest(runtime.status, ESTIMATED)),
                notes=f"Worst case within the bracket: {slowest_speedup:.2f}x.",
            ),
        )
        assumptions.insert(
            0,
            f"The workload is limited by arithmetic ({compute_speedup:.2f}x) or by memory "
            f"bandwidth ({bandwidth_speedup:.2f}x), and lands between the two.",
        )

    return Projection(
        quantity=Quantity(
            value=float(runtime.value) / chosen,
            unit=runtime.unit or "s",
            status=_cap(weakest(runtime.status, ESTIMATED)),
            source_url=target_row.get("source_url"),
            retrieved_date=target_row.get("retrieved_date"),
            notes=(
                f"Scaled from {source_key} to {target_key} by {chosen:.2f}x, taken from {basis}."
            ),
        ),
        method=(
            f"Runtime on {target_key} = runtime on {source_key} / {chosen:.2f}, "
            f"where {chosen:.2f} is {basis}."
        ),
        assumptions=tuple(assumptions),
        limits=tuple(limits),
        bounds=bounds,
    )
