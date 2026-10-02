"""Projecting from what was measured to what was not run.

Module summary
--------------
Two projections, both of which refuse rather than guess when they cannot stand
behind the answer: from a timed slice to the whole run, and from this machine to
another accelerator. A projected cost names the projected numbers it came from,
never the measured ones it did not, or a reader following the trail would arrive
at the local machine and wonder why the arithmetic does not work out.

Author
------
Warith Harchaoui
"""

from __future__ import annotations

from typing import Any

from ..analyze.run import (
    SliceResult,
)
from ..catalog.registry import Catalog
from ..estimate.energy import (
    carbon_from_energy,
    facility_energy,
    it_energy_from_runtime,
    money_from_energy,
    water_from_energy,
)
from ..estimate.extrapolate import (
    project_to_completion,
    project_to_machine,
)
from ..estimate.machine import MachineProfile
from ..estimate.scaling import (
    ScalingFit,
)
from ..model.quantity import Quantity
from ..model.taxonomy import ESTIMATED
from .options import AuditOptions
from .paths import (
    GRID_PATH,
    PRICE_PATH,
    PROJECTED_ENERGY_PATH,
    PROJECTED_IT_ENERGY_PATH,
    PROJECTED_POWER_PATH,
    PROJECTED_RUNTIME_PATH,
    PUE_PATH,
    WUE_PATH,
)


def _projections(
    scenario_costs: dict[str, Quantity],
    runtime: Quantity,
    slice_result: SliceResult | None,
    machine: MachineProfile,
    options: AuditOptions,
    *,
    compute_bound: bool | None = None,
    site: dict[str, Quantity] | None = None,
    scaling: ScalingFit | None = None,
) -> tuple[dict[str, Any], list[str]]:
    """Build whatever projections the evidence supports, and say what it does not.

    Parameters
    ----------
    scenario_costs : dict
        The per-unit costs, which a completion projection scales.
    runtime : Quantity
        The measured runtime, which a machine projection scales.
    slice_result : SliceResult or None
        The run, whose completed fraction licenses the completion projection.
    machine : MachineProfile
        The local machine, whose accelerator is the default projection source.
    options : AuditOptions
        What the caller asked for.
    compute_bound : bool or None, optional
        Whether the read established that arithmetic rather than memory limits
        this workload. It decides which end of the speed-up bracket is reported.
    scaling : ScalingFit or None, optional
        How the cost was measured to grow with the size of the job. ``None``
        keeps the linear assumption. A fit that refused refuses the whole-run
        projection with it, and the reason reaches the reader as a note.
    site : dict or None, optional
        The deployment's overhead, tariff and grid intensity, used to turn a
        projected runtime on another accelerator into what that run would cost.
        Without it the projection stops at a duration, which is not the question
        anybody asked.

    Returns
    -------
    tuple
        The projections block, empty when none could be made, and any notes.

    Examples
    --------
    >>> block, notes = _projections({}, Quantity(status="TODO"), None,
    ...                             MachineProfile("linux"), AuditOptions())
    >>> block
    {}
    """
    block: dict[str, Any] = {}
    notes: list[str] = []

    if slice_result is not None and slice_result.may_project():
        whole: dict[str, Any] = {}
        refusals: list[str] = []
        for key, cost in scenario_costs.items():
            projection = project_to_completion(
                cost, fraction=float(slice_result.fraction_completed), scaling=scaling
            )
            if projection.refused:
                refusals.append(str(projection.quantity.notes))
            else:
                whole[key] = projection.to_mapping()
        if whole:
            description = (
                "What the whole run would cost, projected from the slice that was measured."
            )
            if scaling is not None and scaling.usable():
                description = (
                    "What the whole run would cost, projected from the slice that was "
                    "measured and from the exponent by which its cost was measured to "
                    "grow with the size of the job."
                )
            block["whole_run"] = {"description": description, "costs": whole}
        elif refusals:
            # One refusal reaches the reader rather than five copies of it: every
            # cost in a scenario is projected the same way, so they all fail for
            # the same reason.
            notes.append(refusals[0])
    elif options.run:
        notes.append(
            "No whole-run projection was made: the share of the work the slice "
            "covered is not known, so there is nothing to divide by."
        )

    if options.target_accelerator:
        source = options.source_accelerator or machine.gpu_key
        if source is None:
            notes.append(
                f"Projecting onto {options.target_accelerator} needs an accelerator to "
                "project from, and this machine has none in the catalogue. Pass "
                "--source-accelerator with the key of the machine the measurement "
                "represents, for example --source-accelerator RTX-4090."
            )
        else:
            catalog = Catalog.load("hardware", overlay=options.overlay)
            projection = project_to_machine(
                runtime=runtime,
                source_key=source,
                target_key=options.target_accelerator,
                precision=options.precision,
                compute_bound=compute_bound,
                overlay_catalog=catalog,
            )
            elsewhere: dict[str, Any] = {
                "source": source,
                "target": options.target_accelerator,
                "runtime": projection.to_mapping(),
            }
            if projection.refused:
                notes.append(str(projection.quantity.notes))
            elif site is not None:
                elsewhere |= _cost_on_other_hardware(
                    projected_runtime=projection.quantity,
                    target_key=options.target_accelerator,
                    target_row=catalog.rows("gpus").get(options.target_accelerator, {}),
                    site=site,
                )
            block["on_other_hardware"] = elsewhere
    return block, notes


def _cost_on_other_hardware(
    *,
    projected_runtime: Quantity,
    target_key: str,
    target_row: dict[str, Any],
    site: dict[str, Quantity],
) -> dict[str, Any]:
    """Turn a projected runtime on another accelerator into what it would cost.

    A duration is not the question. "What would this cost on an H100" is, and the
    answer is the projected runtime against the target board's power, the same
    datacenter overhead, and the same tariff and grid the deployment states. That
    last part is an assumption large enough to be written down rather than
    implied: moving work to another accelerator usually means moving it to
    another place, and the place is what sets the price and the carbon.

    Parameters
    ----------
    projected_runtime : Quantity
        Seconds on the target, as projected.
    target_key : str
        The catalogue key of the target, named in the power figure's notes.
    target_row : dict
        Its catalogue row, for the board power and that row's provenance.
    site : dict
        ``pue``, ``electricity_price`` and ``grid_carbon_intensity`` as the
        deployment states them.

    Returns
    -------
    dict
        The power assumed and the costs that follow, plus the sentence naming
        what was held constant. Empty of costs when the catalogue has no board
        power for the target.

    Examples
    --------
    >>> block = _cost_on_other_hardware(
    ...     projected_runtime=Quantity(value=3600.0, unit="s", status="estimated"),
    ...     target_key="H100", target_row={"tdp_w": 700},
    ...     site={"pue": Quantity(value=1.2, unit="ratio", status="estimated"),
    ...           "electricity_price": Quantity(value=0.2, unit="USD/kWh",
    ...                                         currency="USD", status="estimated"),
    ...           "grid_carbon_intensity": Quantity(value=56, unit="gCO2e/kWh",
    ...                                             status="estimated")})
    >>> round(block["costs"]["energy"]["value"], 3)
    0.84
    """
    board_watts = target_row.get("tdp_w")
    if not board_watts:
        return {
            "costs_note": (
                f"The catalogue has no board power for {target_key}, so the projection "
                "stops at a duration. Add tdp_w from the vendor datasheet with "
                f"`saggio catalog add gpu {target_key}` and it will carry a cost."
            )
        }
    power = Quantity(
        value=float(board_watts),
        unit="W",
        status=ESTIMATED,
        source_url=target_row.get("source_url"),
        retrieved_date=target_row.get("retrieved_date"),
        notes=(
            f"Board power for {target_key} from the catalogue, at the default power cap. "
            "The host processor, the memory outside the board, and the rest of the node "
            "are not included, so this understates a whole machine."
        ),
    )
    machine_energy = it_energy_from_runtime(projected_runtime, power).with_derivation(
        PROJECTED_RUNTIME_PATH, PROJECTED_POWER_PATH
    )
    energy = facility_energy(machine_energy, site["pue"]).with_derivation(
        PROJECTED_IT_ENERGY_PATH, PUE_PATH
    )
    return {
        "power_draw": power.to_mapping(),
        "machine_energy": machine_energy.to_mapping(),
        "costs": {
            "time": Quantity(
                value=projected_runtime.value,
                unit="s",
                status=projected_runtime.status,
                notes=projected_runtime.notes,
            )
            .with_derivation(PROJECTED_RUNTIME_PATH)
            .to_mapping(),
            "energy": energy.to_mapping(),
            "money": money_from_energy(energy, site["electricity_price"])
            .with_derivation(PROJECTED_ENERGY_PATH, PRICE_PATH)
            .to_mapping(),
            "carbon": carbon_from_energy(energy, site["grid_carbon_intensity"])
            .with_derivation(PROJECTED_ENERGY_PATH, GRID_PATH)
            .to_mapping(),
            # Water tracks the machine's own energy, exactly as in the scenario
            # above; leaving it out of the projection would silently drop a
            # dimension the model watches everywhere else.
            "water": water_from_energy(
                machine_energy, site.get("water_usage_effectiveness", Quantity())
            )
            .with_derivation(PROJECTED_IT_ENERGY_PATH, WUE_PATH)
            .to_mapping(),
        },
        "held_constant": (
            "The country, the tariff, the grid carbon intensity and the datacenter "
            "overhead are the ones stated for this deployment. Running the work on "
            "another accelerator usually means running it somewhere else, and where "
            "it runs is what sets the price and the carbon. Restate them before "
            "quoting these figures for a different site."
        ),
    }
