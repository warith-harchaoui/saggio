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

#: The precisions the catalogue's throughput figures are quoted at. A workload in
#: any other precision cannot be scaled by them, because the relative advantage
#: between two chips changes with precision: an H100 pulls much further ahead of
#: an A100 in BF16 than it does in FP32.
THROUGHPUT_PRECISIONS: Final[frozenset[str]] = frozenset({"bf16", "fp16", "float16", "bfloat16"})

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
    overlay_catalog: Catalog | None = None,
) -> Projection:
    """Project a runtime measured on one accelerator onto another.

    The scaling is the ratio of peak throughputs at the stated precision: a target
    with twice the throughput is assumed to finish in half the time. That holds
    only while the work is compute-bound. A workload waiting on memory bandwidth,
    on storage, or on a data loader will not speed up this way, which is why the
    limits say so rather than the number pretending otherwise.

    Parameters
    ----------
    runtime : Quantity
        Seconds measured on the source accelerator.
    source_key : str
        Catalogue key of the accelerator the measurement came from.
    target_key : str
        Catalogue key of the accelerator to project onto.
    precision : str, optional
        The numeric precision the workload runs in. Only the precisions in
        :data:`THROUGHPUT_PRECISIONS` can be projected, because those are the ones
        the catalogue quotes throughput at.
    overlay_catalog : Catalog or None, optional
        A pre-loaded hardware catalogue.

    Returns
    -------
    Projection
        The projected runtime, or a refusal naming exactly what is missing: the
        source row, the target row, a throughput figure, or a precision the
        catalogue cannot speak to.

    Examples
    --------
    >>> projected = project_to_machine(
    ...     runtime=Quantity(value=1000.0, unit="s", status="measured"),
    ...     source_key="A100", target_key="H100")
    >>> round(projected.quantity.value, 1)
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

    if precision.lower() not in THROUGHPUT_PRECISIONS:
        listed = ", ".join(sorted(THROUGHPUT_PRECISIONS))
        return _refusal(
            runtime.unit,
            None,
            f"The catalogue quotes peak throughput at {listed} only, and this workload "
            f"runs in {precision}. Two chips do not keep the same ratio across precisions, "
            "so scaling by a BF16 figure would overstate the faster one. Measure on the "
            "target, or add a throughput figure for this precision to the catalogue.",
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
    source_throughput = source_row.get("peak_bf16_tflops")
    target_throughput = target_row.get("peak_bf16_tflops")
    without = [
        key
        for key, value in ((source_key, source_throughput), (target_key, target_throughput))
        if not value
    ]
    if without:
        return _refusal(
            runtime.unit,
            None,
            f"{' and '.join(repr(key) for key in without)} has no peak throughput in the "
            "catalogue, so there is no ratio to scale by. Add peak_bf16_tflops from the "
            "vendor datasheet.",
        )

    speedup = float(target_throughput) / float(source_throughput)
    return Projection(
        quantity=Quantity(
            value=float(runtime.value) / speedup,
            unit=runtime.unit or "s",
            status=_cap(weakest(runtime.status, ESTIMATED)),
            source_url=target_row.get("source_url"),
            retrieved_date=target_row.get("retrieved_date"),
            notes=(
                f"Scaled from {source_key} to {target_key} by a peak-throughput ratio of "
                f"{speedup:.2f}x at {precision}."
            ),
        ),
        method=(
            f"Runtime on {target_key} = runtime on {source_key} x "
            f"({source_throughput} / {target_throughput}) peak {precision} TFLOP/s."
        ),
        assumptions=(
            "The workload is compute-bound, so peak throughput is what limits it.",
            f"Both accelerators reach a similar share of peak at {precision}.",
            "The target has enough memory to hold the same working set.",
        ),
        limits=(
            "A workload bound by memory bandwidth, storage, or the data loader "
            "will not gain the full ratio, and may gain none of it.",
            "Peak throughput is a datasheet figure, not a benchmark; real speedups "
            "are usually smaller.",
            "Multi-accelerator scaling, interconnect, and communication overhead "
            "are not modelled here.",
        ),
    )
