"""
Turning a repository into a cost model.

Module summary
--------------
The module is called ``auditor`` and the function it exists for is called
``audit``, because ``saggio.audit`` would otherwise mean the
module in one import and the function in another, and monkeypatching the first
would silently patch the second.

This is the orchestrator, and the only place in the package where the three ways
of knowing meet. Reading the code establishes its shape and its size. The
operating system establishes what machine this is. The catalogues establish what
that machine draws and what the local grid emits. Running a bounded slice, when
the user has agreed to it, replaces the weakest of those guesses with a
measurement. The result is a cost model where every number says which of those it
came from.

The audit refuses to improve a number by pretending. A country nobody stated stays
open; a provider that publishes no water figure yields no water figure; a slice
that failed projects to nothing. Each of those is written into the model as a
``TODO`` with a sentence saying what would close it, which is the most useful
thing an incomplete model can do.

Usage example
-------------
>>> from saggio.auditor import audit, AuditOptions
>>> result = audit(".", options=AuditOptions(run=False, use_llm=False, country="FR"))
>>> result.report.ok
True

Author
------
Warith Harchaoui
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Final

import os_helper as osh

from .analyze import llm
from .analyze.run import DEFAULT_TIMEOUT_SECONDS, SliceResult, require_consent, run_slice
from .analyze.static import (
    DEFAULT_CAP_FRACTION,
    RepositoryReading,
    capped_entrypoint_command,
    read_repository,
)
from .catalog.registry import Catalog
from .estimate.context import DeploymentContext
from .estimate.energy import (
    carbon_from_energy,
    facility_energy,
    it_energy_from_runtime,
    money_from_energy,
    node_power,
    water_from_energy,
)
from .estimate.extrapolate import (
    DEFAULT_PRECISION,
    project_to_completion,
    project_to_machine,
)
from .estimate.machine import MachineProfile, detect_machine
from .model.cost_model import CostModel
from .model.quantity import Quantity
from .model.results import Report
from .model.schema import SCHEMA_VERSION
from .model.taxonomy import MEASURED, TODO
from .model.validate import validate

#: The scenario an audit writes, and the dotted path everything in it derives from.
SCENARIO_NAME: Final[str] = "as-audited"
_SCENARIO_PATH: Final[str] = "scenarios[0]"

#: Dotted paths of the assumptions, used to wire up ``derived_from``. They are
#: constants rather than literals scattered through the code because the
#: validator resolves them and a typo would turn into a false error.
_POWER_PATH: Final[str] = "assumptions.power_draw"
_PUE_PATH: Final[str] = "assumptions.pue"
_PRICE_PATH: Final[str] = "assumptions.electricity_price"
_GRID_PATH: Final[str] = "assumptions.grid_carbon_intensity"
_WUE_PATH: Final[str] = "assumptions.water_usage_effectiveness"
_RUNTIME_PATH: Final[str] = f"{_SCENARIO_PATH}.runtime"
_IT_ENERGY_PATH: Final[str] = "assumptions.machine_energy"
_ENERGY_PATH: Final[str] = f"{_SCENARIO_PATH}.costs.energy"

#: What one unit of work is, per archetype, when the repository does not say. It
#: is phrased as a question the user should answer rather than as a fact.
_UNIT_BY_ARCHETYPE: Final[dict[str, str]] = {
    "training": "one training run to completion",
    "inference": "one inference on a median-sized input",
    "service": "one request handled end to end",
    "batch-pipeline": "one pass over one day of input data",
    "command-line-tool": "one invocation of the command",
    "library": "one call to the library's main entry point",
}

#: Timeout for cloning a repository, so a hung network does not hang an audit.
_CLONE_TIMEOUT_SECONDS: Final[float] = 300.0


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


def describe_command(command: tuple[str, ...]) -> str:
    """Render a command for a note, short enough to read and free of a home path.

    The full path of a Python interpreter is most of the line and none of the
    information, and a model that will be committed and shared should not carry
    somebody's home directory in it.

    Parameters
    ----------
    command : tuple of str
        The command as it was run.

    Returns
    -------
    str
        A readable one-line form.

    Examples
    --------
    >>> describe_command(("/opt/conda/bin/python", "/repo/train.py", "--max_iters", "600"))
    'python train.py --max_iters 600'
    >>> describe_command(())
    ''
    """
    if not command:
        return ""
    parts = [Path(command[0]).name]
    for part in command[1:]:
        # Only turn something that looks like a path into a basename; a flag or a
        # value would be unrecognisable without it.
        parts.append(Path(part).name if "/" in part or "\\" in part else part)
    return " ".join(parts)


def _unit_of_work(reading: RepositoryReading) -> dict[str, Any]:
    """Describe one unit of work, or say that nobody has yet.

    Parameters
    ----------
    reading : RepositoryReading
        The static reading, whose archetype suggests a unit.

    Returns
    -------
    dict
        The unit block. Its status is ``placeholder``, never ``estimated``: a
        guess at what somebody meant to measure is a structural stand-in, and
        calling it an estimate would be claiming it was derived from something.

    Examples
    --------
    >>> _unit_of_work(RepositoryReading(root=Path("."), archetype="training"))["status"]
    'placeholder'
    """
    suggestion = _UNIT_BY_ARCHETYPE.get(reading.archetype)
    if suggestion is None:
        return {
            "name": "TODO: the one thing whose cost this model reports",
            "description": (
                "Reading the code did not make the unit obvious. State it "
                "precisely enough that two people would count it the same way."
            ),
            "status": TODO,
            "out_of_scope": [],
        }
    return {
        "name": suggestion,
        "description": (
            f"Proposed from the repository's shape, which reads as {reading.archetype}. "
            "Confirm or replace it: every number below is per one of these, so the "
            "whole model means whatever this sentence means."
        ),
        "status": "placeholder",
        "out_of_scope": [],
    }


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


def _service_blocks(reading: RepositoryReading) -> list[dict[str, Any]]:
    """Describe each paid service the code calls, with a price left open.

    A price is deliberately not fetched. API prices change, a stale one shipped as
    authoritative is exactly the failure this package exists to prevent, and the
    only honest thing an automated audit can do is name the service, quote the
    line that proves it is used, and point at the page where the current number
    lives.

    Parameters
    ----------
    reading : RepositoryReading
        The static reading, carrying the service hits.

    Returns
    -------
    list of dict
        One block per detected service.

    Examples
    --------
    >>> _service_blocks(RepositoryReading(root=Path(".")))
    []
    """
    blocks: list[dict[str, Any]] = []
    for hit in reading.services:
        block = hit.to_mapping()
        if hit.pricing_source_url:
            block["pricing_source_url"] = hit.pricing_source_url
        block["price_per_unit"] = Quantity(
            unit="currency",
            status=TODO,
            source_url=hit.pricing_source_url or None,
            notes=(
                "Read the current price from the page above and record what one "
                "unit of work spends. It is left open because a price copied "
                "today is wrong by next quarter."
            ),
        ).to_mapping()
        blocks.append(block)
    return blocks


def _run_a_slice(
    reading: RepositoryReading, options: AuditOptions
) -> tuple[SliceResult | None, list[str]]:
    """Run a bounded slice, if the user allows it and there is one to run.

    Parameters
    ----------
    reading : RepositoryReading
        The static reading, which supplies the command and the fraction.
    options : AuditOptions
        What the caller asked for.

    Returns
    -------
    tuple
        The result, or ``None``, and any notes for the reader.

    Examples
    --------
    >>> _run_a_slice(RepositoryReading(root=Path(".")), AuditOptions(run=False))[0] is None
    True
    """
    notes: list[str] = []
    if not options.run:
        return None, notes
    if not require_consent():
        notes.append(
            "Running the code was declined, so every number below comes from "
            "reading it and from the catalogues, never from a measurement."
        )
        return None, notes

    command, fraction = capped_entrypoint_command(reading, cap_fraction=options.cap_fraction)
    if command is None:
        if not reading.has_tests:
            notes.append(
                "There was nothing safe to run: no entry point with a stated work "
                "size, and no test suite. Measure your own command with "
                "`saggio measure`."
            )
            return None, notes
        command, fraction = reading.test_command, None
        notes.append(
            "No entry point with a stated work size was found, so the repository's "
            "own test suite was run instead. It covers an unknown share of a real "
            "workload, so no whole-run projection follows from it."
        )

    osh.info(f"Running a slice: {' '.join(command)}")
    result = run_slice(
        command,
        working_directory=reading.root,
        timeout_seconds=options.timeout_seconds,
        fraction_completed=fraction,
        profile=True,
    )
    notes.extend(result.warnings)
    return result, notes


def _projections(
    scenario_costs: dict[str, Quantity],
    runtime: Quantity,
    slice_result: SliceResult | None,
    machine: MachineProfile,
    options: AuditOptions,
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
        for key, cost in scenario_costs.items():
            projection = project_to_completion(
                cost, fraction=float(slice_result.fraction_completed)
            )
            if not projection.refused:
                whole[key] = projection.to_mapping()
        if whole:
            block["whole_run"] = {
                "description": (
                    "What the whole run would cost, projected from the slice that was measured."
                ),
                "costs": whole,
            }
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
            projection = project_to_machine(
                runtime=runtime,
                source_key=source,
                target_key=options.target_accelerator,
                precision=options.precision,
                overlay_catalog=Catalog.load("hardware", overlay=options.overlay),
            )
            block["on_other_hardware"] = {
                "source": source,
                "target": options.target_accelerator,
                "runtime": projection.to_mapping(),
            }
            if projection.refused:
                notes.append(str(projection.quantity.notes))
    return block, notes


def audit(path: str | Path, *, options: AuditOptions | None = None) -> AuditResult:
    """Build a cost model for a repository.

    Parameters
    ----------
    path : str or pathlib.Path
        The repository root.
    options : AuditOptions or None, optional
        What the audit should do; sensible defaults when not given, which means
        reading the code without running it.

    Returns
    -------
    AuditResult
        The model, its validation verdict, and the evidence behind it.

    Raises
    ------
    AssertionError
        If the path is not a directory.

    Examples
    --------
    >>> result = audit(".", options=AuditOptions(run=False, use_llm=False))
    >>> result.model.data["schema_version"]
    '2.0'
    """
    settings = options or AuditOptions()
    notes: list[str] = []

    reading = read_repository(path, overlay=settings.overlay)
    machine = detect_machine(overlay=settings.overlay)
    notes.extend(machine.catalog_misses)
    notes.extend(reading.work_size_conflicts)

    context = DeploymentContext.build(
        country=settings.country,
        provider=settings.provider,
        instance=settings.instance,
        overlay=settings.overlay,
    )
    if context.country is None:
        notes.append(
            "No country was resolved, so the carbon and money figures are open. "
            "Pass --country with an ISO code, for example --country FR."
        )

    slice_result, slice_notes = _run_a_slice(reading, settings)
    notes.extend(slice_notes)

    analysis = reading.to_mapping()
    if settings.use_llm:
        classification = llm.classify(_repository_summary(reading))
        if classification is not None:
            # The model's answer is merged under the static reading, never over
            # it: a number read from a file outranks a sentence from a model.
            for key, value in classification.to_mapping().items():
                analysis.setdefault(key, value)
            analysis["evidence_source"] = f"static + llm:{classification.model}"
        else:
            analysis.setdefault(
                "llm_note", "No local model was reachable; the read is static only."
            )

    power = _power_assumption(machine, context, slice_result)
    runtime = _runtime_assumption(reading, slice_result)
    pue = context.pue()
    price = context.electricity_price()
    grid = context.grid_intensity()
    wue = context.water_effectiveness()

    machine_energy = it_energy_from_runtime(runtime, power).with_derivation(
        _RUNTIME_PATH, _POWER_PATH
    )
    energy = facility_energy(machine_energy, pue).with_derivation(_IT_ENERGY_PATH, _PUE_PATH)
    costs: dict[str, Quantity] = {
        "time": Quantity(
            value=runtime.value,
            unit="s",
            status=runtime.status,
            notes=runtime.notes,
        ).with_derivation(_RUNTIME_PATH),
        "energy": energy,
        "money": money_from_energy(energy, price).with_derivation(_ENERGY_PATH, _PRICE_PATH),
        "carbon": carbon_from_energy(energy, grid).with_derivation(_ENERGY_PATH, _GRID_PATH),
        "water": water_from_energy(machine_energy, wue).with_derivation(_IT_ENERGY_PATH, _WUE_PATH),
    }

    projections, projection_notes = _projections(costs, runtime, slice_result, machine, settings)
    notes.extend(projection_notes)

    deployment = context.to_mapping() | machine.to_mapping()
    data: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "date_updated": date.today().isoformat(),
        "project": {
            "name": reading.root.name,
            "audited_from": osh.path_without_home(str(reading.root)),
        },
        "unit_of_work": _unit_of_work(reading),
        "deployment": deployment,
        "assumptions": {
            "power_draw": power.to_mapping(),
            "pue": pue.to_mapping(),
            "electricity_price": price.to_mapping(),
            "grid_carbon_intensity": grid.to_mapping(),
            "water_usage_effectiveness": wue.to_mapping(),
            "machine_energy": machine_energy.to_mapping(),
        },
        "scenarios": [
            {
                "name": SCENARIO_NAME,
                "description": (
                    "One unit of work as this audit found it, on the machine it ran on."
                ),
                "runtime": runtime.to_mapping(),
                "costs": {key: value.to_mapping() for key, value in costs.items()},
            }
        ],
        "analysis": analysis,
        "exclusions": [
            "Making the hardware. Only the electricity to run it is counted.",
            "The people. Salaries, offices, and travel are out of scope.",
            "Idle capacity. This is the cost of one unit of work, not of being ready.",
        ],
        "provenance_rules": [
            "Every sourced value carries source_url and retrieved_date.",
            "A derived value names its inputs and never outranks the weakest of them.",
            "The country is stated by a human, never inferred from a developer's locale.",
        ],
    }
    if reading.services:
        data["external_services"] = _service_blocks(reading)
    if slice_result is not None:
        data["measurement"] = slice_result.to_mapping()
    if projections:
        data["projections"] = projections

    model = CostModel.from_mapping(data)
    return AuditResult(
        model=model,
        report=validate(model),
        reading=reading,
        machine=machine,
        slice_result=slice_result,
        notes=tuple(notes),
    )


def _repository_summary(reading: RepositoryReading) -> str:
    """Describe a repository for the local model, in prose and without numbers.

    Parameters
    ----------
    reading : RepositoryReading
        The static reading.

    Returns
    -------
    str
        A short description: languages, frameworks, entry point, tests.

    Examples
    --------
    >>> "Languages" in _repository_summary(RepositoryReading(root=Path(".")))
    True
    """
    lines = [
        f"Name: {reading.root.name}",
        f"Languages: {', '.join(reading.languages) or 'none detected'}",
        f"Frameworks: {', '.join(reading.frameworks) or 'none detected'}",
        f"Archetype from filenames: {reading.archetype}",
        f"Entry point: {reading.entrypoint or 'none found'}",
        f"Has a test suite: {reading.has_tests}",
    ]
    if reading.services:
        lines.append(f"Paid services called: {', '.join(hit.key for hit in reading.services)}")
    return "\n".join(lines)


def audit_github(url: str, *, options: AuditOptions | None = None) -> AuditResult:
    """Clone a public repository into a temporary directory and audit it.

    Parameters
    ----------
    url : str
        A git URL.
    options : AuditOptions or None, optional
        What the audit should do.

    Returns
    -------
    AuditResult
        The model, its verdict, and the evidence.

    Raises
    ------
    RuntimeError
        If ``git`` is not on the path, or the clone fails, with the reason.

    Examples
    --------
    >>> audit_github("not a url")
    Traceback (most recent call last):
        ...
    RuntimeError: ...
    """
    folder = osh.make_temporary_directory(prefix="audit-")
    target = Path(folder) / "repository"
    try:
        completed = subprocess.run(  # noqa: S603 - a list, never a shell.
            # S607: git is resolved from PATH on purpose. Hard-coding a path would
            # be wrong on every platform in a different way, and the alternative
            # to trusting PATH here is not offering the feature at all.
            ["git", "clone", "--depth", "1", "--quiet", url, str(target)],  # noqa: S607
            capture_output=True,
            text=True,
            timeout=_CLONE_TIMEOUT_SECONDS,
            check=False,
        )
    except FileNotFoundError as exc:
        raise RuntimeError(
            "git is not on the PATH, and cloning needs it. Install git, or clone "
            "the repository yourself and audit the directory."
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"Cloning {url} took longer than {_CLONE_TIMEOUT_SECONDS:g} s.") from exc
    if completed.returncode != 0:
        detail = (completed.stderr or "").strip().splitlines()[-1:] or ["no output"]
        raise RuntimeError(f"Could not clone {url}: {detail[0]}")
    return audit(target, options=options)
