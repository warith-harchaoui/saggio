"""
Putting a measurement into a model that already exists.

Module summary
--------------
There are two ways a measured number reaches a cost model. ``saggio audit --run``
takes both steps at once: it reads the repository, runs a slice of it, and writes
the model. That path asks for consent first, because it executes somebody else's
code.

This is the other way. The command was run separately, by a person who typed it,
and what remains is to put the number where it belongs. Doing that by hand looks
easy and is not: writing a measured runtime into a model leaves every figure
derived from it holding the old value, and a model whose energy no longer matches
its runtime is worse than one that never had either, because it looks finished.

So the whole job is done here. The runtime goes in, the power goes in when the
machine reported one, and everything downstream is recomputed from the model's own
assumptions by the same functions the auditor uses. The result is validated before
it is written, and a measurement of a run that failed is refused outright: a
command that exited non-zero measured a failure, and a failure has no cost per
unit of work because it produced no units.

Usage example
-------------
>>> from saggio.fold import fold_measurement
>>> from saggio.model import CostModel
>>> model = CostModel.from_mapping({"schema_version": "2.1", "scenarios": []})
>>> fold_measurement(model, seconds=1.0, units=1).refused is not None
True

Author
------
Warith Harchaoui
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .analyze.power import PowerReading
from .estimate.energy import (
    carbon_from_energy,
    facility_energy,
    it_energy_from_runtime,
    money_from_energy,
    water_from_energy,
)
from .estimate.extrapolate import project_to_completion
from .model.cost_model import CostModel
from .model.quantity import Quantity
from .model.taxonomy import MEASURED
from .model.validate import validate

#: Where the assumptions a derived cost leans on are kept.
_POWER_PATH = "assumptions.power_draw"
_PUE_PATH = "assumptions.pue"
_PRICE_PATH = "assumptions.electricity_price"
_GRID_PATH = "assumptions.grid_carbon_intensity"
_WUE_PATH = "assumptions.water_usage_effectiveness"
_IT_ENERGY_PATH = "assumptions.machine_energy"


@dataclass(frozen=True, slots=True)
class Fold:
    """What folding a measurement into a model did, or why it did nothing.

    Parameters
    ----------
    model : CostModel
        The model after the fold. Unchanged when the fold was refused.
    changes : tuple of str
        One sentence per figure that moved, for a caller to print. A fold that
        silently rewrote six numbers would be the kind of quiet edit this package
        exists to make impossible.
    refused : str or None
        Why nothing was written, or ``None`` when something was.

    Examples
    --------
    >>> Fold(CostModel.from_mapping({}), (), "nothing to fold into").refused
    'nothing to fold into'
    """

    model: CostModel
    changes: tuple[str, ...] = field(default_factory=tuple)
    refused: str | None = None


def _scenario_index(data: dict[str, Any], name: str | None) -> int | None:
    """Return which scenario to fold into, or ``None`` when there is no answer."""
    scenarios = data.get("scenarios")
    if not isinstance(scenarios, list) or not scenarios:
        return None
    if name is None:
        # The first *mapping*: a stray string at position 0 is not a scenario,
        # and indexing it blindly crashed instead of refusing.
        return next(
            (index for index, entry in enumerate(scenarios) if isinstance(entry, dict)), None
        )
    for index, scenario in enumerate(scenarios):
        if isinstance(scenario, dict) and str(scenario.get("name")) == name:
            return index
    return None


def _assumption(data: dict[str, Any], key: str) -> Quantity:
    """Return an assumption as a quantity, or an empty one when it is absent."""
    raw = (data.get("assumptions") or {}).get(key)
    return Quantity.from_mapping(raw) if isinstance(raw, dict) else Quantity()


def fold_measurement(
    model: CostModel,
    *,
    seconds: float,
    units: float = 1.0,
    power: PowerReading | None = None,
    scenario: str | None = None,
    command: str | None = None,
) -> Fold:
    """Write a measured runtime into a model and recompute what follows from it.

    Parameters
    ----------
    model : CostModel
        The model to fold into. It is not modified; a new one is returned.
    seconds : float
        Wall-clock seconds the command took.
    units : float, optional
        How many units of work the command performed. The runtime recorded is
        ``seconds / units``, because a model's figures are per unit and a command
        that scores five hundred samples measured five hundred of them.
    power : PowerReading or None, optional
        What the machine said it drew. A reading that measured nothing leaves the
        model's existing power assumption alone rather than replacing a sourced
        estimate with silence.
    scenario : str or None, optional
        Which scenario to fold into, by name. The first one when not given.
    command : str or None, optional
        The command that was run, recorded in the runtime's notes so a reader can
        see what was timed.

    Returns
    -------
    Fold
        The new model and what moved, or a refusal and the reason.

    Examples
    --------
    >>> model = CostModel.from_mapping({"schema_version": "2.1", "scenarios": []})
    >>> fold_measurement(model, seconds=1.0).refused
    'This model has no scenario to fold a measurement into.'
    >>> fold_measurement(model, seconds=1.0, units=0).refused
    'A command cannot have performed 0 units of work.'
    """
    if units <= 0:
        return Fold(model, refused=f"A command cannot have performed {units:g} units of work.")
    if seconds <= 0:
        return Fold(model, refused="A run of no duration is not a measurement of one.")

    data = model.data
    index = _scenario_index(data, scenario)
    if index is None:
        if scenario is not None:
            return Fold(model, refused=f"This model has no scenario named {scenario!r}.")
        return Fold(model, refused="This model has no scenario to fold a measurement into.")

    before = validate(model)
    if not before.ok:
        listed = "; ".join(
            f"{issue.path}: {issue.message}" if issue.path else issue.message
            for issue in before.errors[:3]
        )
        # Refusing up front keeps the post-fold check meaningful: without this,
        # folding into one scenario could paper over an existing fault while
        # folding into another was blamed for it.
        return Fold(model, refused=f"The model does not validate before folding: {listed}")

    updated: dict[str, Any] = _deep_copy(data)
    target = updated["scenarios"][index]
    scenario_path = f"scenarios[{index}]"
    changes: list[str] = []

    timed = (
        f"Timed with `saggio measure`: {command}." if command else "Timed with `saggio measure`."
    )
    per_unit = (
        f" The command performed {units:g} units of work, so the figure is the "
        f"wall-clock time divided by {units:g}."
        if units != 1
        else ""
    )
    runtime = Quantity(
        value=seconds / units,
        unit="s",
        status=MEASURED,
        notes=f"{timed}{per_unit}",
    )
    changes.append(_moved("runtime", target.get("runtime"), runtime))
    target["runtime"] = runtime.to_mapping()

    power_quantity = _assumption(updated, "power_draw")
    if power is not None and power.measured():
        measured_power = Quantity(
            value=power.watts,
            unit="W",
            status=MEASURED,
            notes=f"Read from the machine while the command ran. {power.scope}",
        )
        changes.append(_moved("power draw", power_quantity.to_mapping(), measured_power))
        updated.setdefault("assumptions", {})["power_draw"] = measured_power.to_mapping()
        power_quantity = measured_power

    machine_energy = it_energy_from_runtime(runtime, power_quantity).with_derivation(
        f"{scenario_path}.runtime", _POWER_PATH
    )
    energy = facility_energy(machine_energy, _assumption(updated, "pue")).with_derivation(
        _IT_ENERGY_PATH, _PUE_PATH
    )
    updated.setdefault("assumptions", {})["machine_energy"] = machine_energy.to_mapping()

    costs = target.setdefault("costs", {})
    recomputed = {
        "time": Quantity(
            value=runtime.value, unit="s", status=runtime.status, notes=runtime.notes
        ).with_derivation(f"{scenario_path}.runtime"),
        "energy": energy,
        "money": money_from_energy(
            energy, _assumption(updated, "electricity_price")
        ).with_derivation(f"{scenario_path}.costs.energy", _PRICE_PATH),
        "carbon": carbon_from_energy(
            energy, _assumption(updated, "grid_carbon_intensity")
        ).with_derivation(f"{scenario_path}.costs.energy", _GRID_PATH),
        "water": water_from_energy(
            machine_energy, _assumption(updated, "water_usage_effectiveness")
        ).with_derivation(_IT_ENERGY_PATH, _WUE_PATH),
    }
    # A dimension the model never carried is not introduced here — with one
    # exception. Money and carbon derive from the energy cost by path, so a
    # model that watches either without watching energy still needs the energy
    # row written, or its derivations would name nothing and the fold would
    # invalidate a model it just improved.
    wanted = {key for key in recomputed if key in costs or key == "time"}
    if wanted & {"money", "carbon"}:
        wanted.add("energy")
    for key, quantity in recomputed.items():
        if key not in wanted:
            continue
        changes.append(_moved(key, costs.get(key), quantity))
        costs[key] = quantity.to_mapping()

    whole = _whole_run(updated, costs, scenario_path)
    if whole is not None:
        updated["projections"] = dict(updated.get("projections") or {}) | {"whole_run": whole}
        changes.append("whole run: projected from the per-unit costs above")

    folded = CostModel.from_mapping(updated, path=model.path)
    verdict = validate(folded)
    if not verdict.ok:
        listed = "; ".join(
            f"{issue.path}: {issue.message}" if issue.path else issue.message
            for issue in verdict.errors[:3]
        )
        return Fold(model, refused=f"The model would no longer validate: {listed}")
    return Fold(folded, changes=tuple(change for change in changes if change))


def _whole_run(
    data: dict[str, Any], costs: dict[str, Any], scenario_path: str
) -> dict[str, Any] | None:
    """Project the per-unit costs to a whole run, when the model says how long one is.

    The audit already read how much work a full run performs out of the
    repository's own configuration, and it is sitting in the analysis block. Using
    it here rests on one assumption worth stating rather than implying: that one
    unit of work is one of the things that configuration counts. When it is not,
    the projection is wrong by whatever the difference is, so the sentence saying
    so travels with it.

    Parameters
    ----------
    data : dict
        The model being folded into.
    costs : dict
        The per-unit costs just recomputed.
    scenario_path : str
        Dotted path of the scenario they belong to.

    Returns
    -------
    dict or None
        A projections block, or ``None`` when the model does not say how much
        work a whole run performs.

    Examples
    --------
    >>> _whole_run({}, {}, "scenarios[0]") is None
    True
    """
    stated = ((data.get("analysis") or {}).get("total_work") or {}).get("stated_as")
    try:
        units_in_a_run = float(str(stated))
    except (TypeError, ValueError):
        return None
    if units_in_a_run <= 1:
        return None

    projected: dict[str, Any] = {}
    for key, raw in costs.items():
        if not isinstance(raw, dict):
            continue
        projection = project_to_completion(
            Quantity.from_mapping(raw), fraction=1.0 / units_in_a_run
        )
        if not projection.refused:
            projected[key] = projection.to_mapping()
    if not projected:
        return None

    unit = ((data.get("analysis") or {}).get("total_work") or {}).get("unit") or "units"
    source = ((data.get("analysis") or {}).get("total_work") or {}).get("source") or "the analysis"
    return {
        "description": (
            f"What a whole run would cost, from the per-unit costs in {scenario_path}. "
            f"A whole run performs {units_in_a_run:g} {unit}, as {source} states. This "
            f"assumes one unit of work is one {unit.rstrip('s')}; if the model's unit of "
            "work means something else, restate this."
        ),
        "costs": projected,
    }


def _moved(label: str, before: object, after: Quantity) -> str:
    """Return a sentence for a figure that changed, or an empty string.

    Parameters
    ----------
    label : str
        What changed, as a reader would name it.
    before : object
        The old mapping, if there was one.
    after : Quantity
        The new value.

    Returns
    -------
    str
        One sentence, or ``""`` when nothing worth reporting happened.

    Examples
    --------
    >>> _moved("runtime", None, Quantity(value=2.0, unit="s", status="measured"))
    'runtime: not known -> 2 s, TODO -> measured'
    """
    old = Quantity.from_mapping(before) if isinstance(before, dict) else Quantity()
    if old.value == after.value and old.status == after.status:
        return ""
    was = f"{old.value:g} {old.unit or ''}".strip() if old.is_known() else "not known"
    now = f"{after.value:g} {after.unit or ''}".strip() if after.is_known() else "not known"
    return f"{label}: {was} -> {now}, {old.status} -> {after.status}"


def _deep_copy(value: Any) -> Any:
    """Return a copy deep enough that folding cannot reach into the caller's model."""
    if isinstance(value, dict):
        return {key: _deep_copy(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_deep_copy(item) for item in value]
    return value
