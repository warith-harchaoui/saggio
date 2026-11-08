"""The assumptions an audit takes from the catalogues, and the one it cannot.

Module summary
--------------
Four numbers an audit does not measure and does not invent: what the hardware
draws, what building it emitted, how long it stays in service, and how long the
work runs. Each arrives as a :class:`~saggio.model.quantity.Quantity` carrying
the status it has earned -- usually ``estimated``, and ``TODO`` when the
catalogue has nothing to say, which is not the same as zero.

A fifth is open by construction rather than by accident: the market-based
emission factor of the electricity the organisation contracted for. No
catalogue can hold it, because it is a property of a contract rather than of a
country, so it ships as a ``TODO`` whose notes are the shopping list.

Author
------
Warith Harchaoui
"""

from __future__ import annotations

from ..analyze.power import workload_scope
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
from ..estimate.ghg import market_based_sources
from ..estimate.machine import MachineProfile
from ..i18n import say
from ..model.quantity import Quantity
from ..model.taxonomy import ESTIMATED, MEASURED, TODO
from .naming import describe_command
from .options import AuditOptions


def _how_to_close(machine: MachineProfile, *, part: str | None, section: str | None) -> str:
    """Return the sentences that tell a reader how to close an open footprint.

    A ``TODO`` that only says something is missing hands the reader a search.
    This hands them the two places a figure can go -- the model in front of
    them, or the catalogue every later audit reads -- and the command for each,
    with what is already known about this machine filled in.

    Parameters
    ----------
    machine : MachineProfile
        What this machine is; its product identifier, when the firmware gave
        one, goes into the machine-level command.
    part : str or None
        The catalogue key the footprint belongs to, when one was identified.
    section : str or None
        Its row kind, ``gpu`` or ``cpu``.

    Returns
    -------
    str
        Two to four sentences, in the language in force.

    Examples
    --------
    >>> text = _how_to_close(MachineProfile("darwin", machine_model="Mac14,5"),
    ...                      part="apple-m2-max", section="cpu")
    >>> "saggio catalog add cpu apple-m2-max" in text, "Mac14,5" in text
    (True, True)
    """
    sentences = [say("assumption.embodied.in_model")]
    if part and section:
        sentences.append(say("assumption.embodied.in_catalog", section=section, key=part))
    if machine.machine_model and machine.machine_key is None:
        sentences.append(say("assumption.embodied.as_machine", model=machine.machine_model))
    sentences.append(say("assumption.embodied.where"))
    return " ".join(sentences)


def _embodied_assumption(machine: MachineProfile, options: AuditOptions) -> Quantity:
    """Return what building the hardware this work reserved emitted, or a ``TODO``.

    Read from the catalogue the same way a wattage is, and open the same way
    when the row has no figure: nobody having read a product carbon footprint
    for a part is not the same as the part having been free to build.

    Three rows can answer, tried in this order. An accelerator's, because work
    on an accelerator reserves that card and the card is what its footprint
    covers. Then the whole machine's, because work with no accelerator reserves
    the machine, and a manufacturer that publishes a footprint at all usually
    publishes it for the product it sells rather than for the chip inside. Then
    the processor's, which covers the chip alone and so understates a machine;
    its scope says so.

    Parameters
    ----------
    machine : MachineProfile
        What this machine is, including the accelerator key and the machine's
        own catalogue key when it has them.
    options : AuditOptions
        Carried for the catalogue overlay.

    Returns
    -------
    Quantity
        Kilograms of CO2 equivalent per device, with the footprint's own URL and
        read date -- never the row's, because a footprint is not a datasheet.
        When open, the note says how to close it, command included.

    Examples
    --------
    >>> _embodied_assumption(MachineProfile(platform="darwin"), AuditOptions()).status
    'TODO'
    """
    catalog = Catalog.load("hardware", overlay=options.overlay)
    machine_row = (
        catalog.rows("machines").get(machine.machine_key, {}) if machine.machine_key else {}
    )
    if machine.gpu_key is not None:
        part, section, row = machine.gpu_key, "gpu", catalog.rows("gpus").get(machine.gpu_key, {})
    elif isinstance(machine_row.get("embodied_kgco2e"), (int, float)):
        part, section, row = machine.machine_key, "machine", machine_row
    elif machine.cpu_key is not None and not machine.cpu_is_fallback:
        # No accelerator, so the processor is the hardware this work reserved. Its
        # footprint used to be refused on the grounds that none was catalogued,
        # which stopped being true the day four of them were: a machine whose only
        # chip is known would have gone on reporting TODO while the figure sat in
        # the file beside it.
        part, section, row = machine.cpu_key, "cpu", catalog.rows("cpus").get(machine.cpu_key, {})
    else:
        reason = say(
            "assumption.embodied.generic_cpu"
            if machine.cpu_key is not None
            else "assumption.embodied.nothing_identified"
        )
        return Quantity(
            unit="kgCO2e",
            status=TODO,
            notes=f"{reason} {_how_to_close(machine, part=None, section=None)}",
        )
    figure = row.get("embodied_kgco2e")
    if not isinstance(figure, (int, float)):
        return Quantity(
            unit="kgCO2e",
            status=TODO,
            notes=(
                say("assumption.embodied.no_footprint", part=part)
                + " "
                + _how_to_close(machine, part=part, section=section)
            ),
        )
    return Quantity(
        value=float(figure),
        unit="kgCO2e",
        status=ESTIMATED,
        source_kind="first-party",
        source_url=row.get("embodied_source_url") or row.get("source_url"),
        retrieved_date=row.get("embodied_retrieved_date") or row.get("retrieved_date"),
        notes=str(row.get("embodied_scope") or say("assumption.embodied.published")),
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
        notes=say("assumption.lifetime"),
    )


def _market_factor_assumption() -> Quantity:
    """Return the market-based emission factor, which only a contract states.

    The other half of what scope 2 requires, shipped open for the same reason as
    the lifespan above and a stronger one: a grid average is the location-based
    method by definition, so there is nothing here to derive this from, and a
    package that guessed it would be inventing somebody's electricity contract.

    Returns
    -------
    Quantity
        A ``TODO`` in grams of CO2 equivalent per kilowatt-hour, whose notes name
        the three places the figure may honestly come from, in the order the
        Scope 2 Guidance puts them.

    Examples
    --------
    >>> _market_factor_assumption().status
    'TODO'
    >>> "residual mix" in _market_factor_assumption().notes
    True
    """
    return Quantity(
        unit="gCO2e/kWh",
        status=TODO,
        notes=say("assumption.market_factor", sources=market_based_sources()),
        source_url="",
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
        # Two boundaries, not one. The scope says which silicon the counters
        # see; the workload scope says how much of that silicon was doing this
        # work. A figure that carries only the first lets a reader believe the
        # second was a hundred per cent, which on any machine running anything
        # else it was not.
        measurement = slice_result.to_mapping()
        return Quantity(
            value=slice_result.power.watts,
            unit="W",
            status=MEASURED,
            notes=say(
                "assumption.power.measured",
                scope=slice_result.power.scope,
                boundary=workload_scope(measurement, watts=slice_result.power.watts),
            ),
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
            notes=say(
                "assumption.runtime.measured",
                command=describe_command(slice_result.command),
            ),
        )
    return Quantity(
        unit="s",
        status=TODO,
        notes=say("assumption.runtime.not_measured"),
    )
