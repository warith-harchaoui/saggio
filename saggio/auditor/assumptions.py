"""The assumptions an audit takes from the catalogues.

Module summary
--------------
Four numbers an audit does not measure and does not invent: what the hardware
draws, what building it emitted, how long it stays in service, and how long the
work runs. Each arrives as a :class:`~saggio.model.quantity.Quantity` carrying
the status it has earned -- usually ``estimated``, and ``TODO`` when the
catalogue has nothing to say, which is not the same as zero.

Author
------
Warith Harchaoui
"""

from __future__ import annotations

from ..analyze.run import (
    SliceResult,
)
from ..analyze.static import (
    RepositoryReading,
)
from ..catalog.registry import Catalog
from ..estimate.context import DeploymentContext
from ..estimate.energy import (
    node_power,
)
from ..estimate.machine import MachineProfile
from ..model.quantity import Quantity
from ..model.taxonomy import ESTIMATED, MEASURED, TODO
from .naming import describe_command
from .options import AuditOptions


def _embodied_assumption(machine: MachineProfile, options: AuditOptions) -> Quantity:
    """Return what building this machine's accelerator emitted, or a ``TODO``.

    Read from the catalogue the same way a wattage is, and open the same way
    when the row has no figure: nobody having read a product carbon footprint
    for a part is not the same as the part having been free to build.

    Parameters
    ----------
    machine : MachineProfile
        What this machine is, including the accelerator key when it has one.
    options : AuditOptions
        Carried for the catalogue overlay.

    Returns
    -------
    Quantity
        Kilograms of CO2 equivalent per device, with the footprint's own URL and
        read date — never the row's, because a footprint is not a datasheet.

    Examples
    --------
    >>> _embodied_assumption(MachineProfile(platform="darwin"), AuditOptions()).status
    'TODO'
    """
    catalog = Catalog.load("hardware", overlay=options.overlay)
    if machine.gpu_key is not None:
        part, section, row = machine.gpu_key, "gpu", catalog.rows("gpus").get(machine.gpu_key, {})
    elif machine.cpu_key is not None and not machine.cpu_is_fallback:
        # No accelerator, so the processor is the hardware this work reserved. Its
        # footprint used to be refused on the grounds that none was catalogued,
        # which stopped being true the day four of them were: a machine whose only
        # chip is known would have gone on reporting TODO while the figure sat in
        # the file beside it.
        part, section, row = machine.cpu_key, "cpu", catalog.rows("cpus").get(machine.cpu_key, {})
    else:
        return Quantity(
            unit="kgCO2e",
            status=TODO,
            notes=(
                "No accelerator was identified, and the processor resolved only to a "
                "generic default, whose footprint would be a generic default too. "
                "Excluded rather than assumed to be zero."
                if machine.cpu_key is not None
                else "Neither an accelerator nor a processor could be identified, so "
                "the carbon of building this machine is not something this model can "
                "state. Excluded rather than assumed to be zero."
            ),
        )
    figure = row.get("embodied_kgco2e")
    if not isinstance(figure, (int, float)):
        return Quantity(
            unit="kgCO2e",
            status=TODO,
            notes=(
                f"No product carbon footprint is on file for {part}. Add "
                "`embodied_kgco2e` to its catalogue row with the footprint's own URL "
                f"and the date it was read; `saggio catalog add {section}` does the rest."
            ),
        )
    return Quantity(
        value=float(figure),
        unit="kgCO2e",
        status=ESTIMATED,
        source_kind="first-party",
        source_url=row.get("embodied_source_url") or row.get("source_url"),
        retrieved_date=row.get("embodied_retrieved_date") or row.get("retrieved_date"),
        notes=str(row.get("embodied_scope") or "Published product carbon footprint."),
    )


def _lifetime_assumption() -> Quantity:
    """Return the hardware lifespan, which nobody but the operator knows.

    Shipped open on purpose. Every published footprint in the catalogue is
    cradle-to-gate and excludes the use phase, so the vendor gave the numerator
    and deliberately withheld the denominator; how long a card stays in service
    is a fact about a fleet. Filling it in with a plausible four years would put
    a number nobody checked under every embodied figure in the report.

    Returns
    -------
    Quantity
        A ``TODO`` naming the range published figures cluster in and what
        choosing within it does to the answer.

    Examples
    --------
    >>> _lifetime_assumption().status
    'TODO'
    """
    return Quantity(
        unit="years",
        status=TODO,
        notes=(
            "How long this hardware stays in service, which only you know. The "
            "published footprints are cradle-to-gate and exclude the use phase, so "
            "none of them states a lifespan. Reported figures cluster between three "
            "and six years; choosing within that range moves the embodied carbon by "
            "a factor of two, which is why this is asked rather than assumed."
        ),
    )


def _power_assumption(
    machine: MachineProfile,
    context: DeploymentContext,
    slice_result: SliceResult | None,
) -> Quantity:
    """Decide what the machine draws, preferring a measurement.

    The order is measurement, then a named instance shape, then a sum over this
    machine's parts. Each falls back to the next only when the one before it
    produced no number, and the result says which it was.

    Parameters
    ----------
    machine : MachineProfile
        The local machine.
    context : DeploymentContext
        The deployment, which may name an instance shape.
    slice_result : SliceResult or None
        A run that may have measured power.

    Returns
    -------
    Quantity
        Watts, at the strongest status that is actually justified.

    Examples
    --------
    >>> quantity = _power_assumption(MachineProfile("linux"), DeploymentContext.build(), None)
    >>> quantity.unit
    'W'
    """
    if slice_result is not None and slice_result.power.measured():
        return Quantity(
            value=slice_result.power.watts,
            unit="W",
            status=MEASURED,
            notes=f"Read from the machine while the slice ran. {slice_result.power.scope}",
        )
    if context.instance:
        from_catalog = context.instance_power()
        if from_catalog.is_known():
            return from_catalog
    return node_power(
        cpu_key=machine.cpu_key,
        physical_cores=machine.physical_cores,
        memory_gb=machine.memory_gb,
        gpu_key=machine.gpu_key,
        accelerator_count=machine.accelerator_count,
        overlay_catalog=Catalog.load("hardware", overlay=context.overlay),
    )


def _runtime_assumption(reading: RepositoryReading, slice_result: SliceResult | None) -> Quantity:
    """Decide how long one unit of work takes.

    Parameters
    ----------
    reading : RepositoryReading
        The static reading, used only for its description of the workload.
    slice_result : SliceResult or None
        A run that may have timed it.

    Returns
    -------
    Quantity
        Seconds, ``measured`` when a slice ran cleanly, otherwise ``TODO``. There
        is deliberately no estimate here: nothing about reading a repository tells
        you how long it runs, and a made-up runtime would propagate into every
        other number in the model.

    Examples
    --------
    >>> from pathlib import Path
    >>> _runtime_assumption(RepositoryReading(root=Path(".")), None).status
    'TODO'
    """
    if slice_result is not None and slice_result.succeeded():
        return Quantity(
            value=slice_result.wall_seconds,
            unit="s",
            status=MEASURED,
            notes=f"Wall-clock time of `{describe_command(slice_result.command)}`.",
        )
    return Quantity(
        unit="s",
        status=TODO,
        notes=(
            "No run was measured. Measure the real command with "
            "`saggio measure`, or audit again with --run."
        ),
    )
