"""Assembling the model, and auditing a repository that is not here yet.

Module summary
--------------
The orchestration: read the repository, take what the catalogues know, measure a
slice when asked, project from it, and write a model whose every number says how
far it can be trusted. Also the clone, for a repository given as a URL.

Author
------
Warith Harchaoui
"""

from __future__ import annotations

import subprocess
from datetime import date
from pathlib import Path
from typing import Any, Final

import os_helper as osh

from ..analyze import llm
from ..analyze.static import (
    read_repository,
)
from ..estimate.context import DeploymentContext
from ..estimate.embodied import embodied_carbon
from ..estimate.energy import (
    carbon_from_energy,
    facility_energy,
    it_energy_from_runtime,
    money_from_energy,
    water_from_energy,
)
from ..estimate.machine import detect_machine
from ..model.cost_model import CostModel
from ..model.quantity import Quantity
from ..model.schema import SCHEMA_VERSION
from ..model.taxonomy import TODO
from ..model.validate import validate
from .assumptions import (
    _embodied_assumption,
    _lifetime_assumption,
    _power_assumption,
    _runtime_assumption,
)
from .blocks import _model_blocks, _service_blocks, _unit_of_work
from .measuring import _run_a_slice
from .naming import _repository_summary, repository_name
from .options import AuditOptions, AuditResult
from .paths import (
    EMBODIED_PATH,
    ENERGY_PATH,
    GRID_PATH,
    IT_ENERGY_PATH,
    LIFETIME_PATH,
    POWER_PATH,
    PRICE_PATH,
    PUE_PATH,
    RUNTIME_PATH,
    SCENARIO_NAME,
    WUE_PATH,
)
from .projections import _projections

#: Timeout for cloning a repository, so a hung network does not hang an audit.
_CLONE_TIMEOUT_SECONDS: Final[float] = 300.0


def audit(
    path: str | Path, *, options: AuditOptions | None = None, origin: str | None = None
) -> AuditResult:
    """Build a cost model for a repository.

    Parameters
    ----------
    path : str or pathlib.Path
        The repository root.
    options : AuditOptions or None, optional
        What the audit should do; sensible defaults when not given, which means
        reading the code without running it.
    origin : str or None, optional
        Where the tree came from, when it is not where it lives. A clone lands in
        a temporary directory whose name and path say nothing about the project
        and will not exist tomorrow, so :func:`audit_git_url` passes the URL here
        and the model records that instead.

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
    '2.1'
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
    elif settings.country and context.grid_intensity().status == TODO:
        # The user named a country and it is kept as stated, but the grid
        # catalogue has no row for it — a miss that belongs in the notes, next
        # to the machine's, not only in a log line that scrolls away.
        notes.append(
            f"The grid catalogue has no row for {context.country!r}, so its carbon "
            "intensity and tariff stay open. Add it with `saggio catalog add country`."
        )

    slice_result, scaling, slice_notes = _run_a_slice(reading, settings)
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
    embodied = _embodied_assumption(machine, settings)
    lifetime = _lifetime_assumption()

    machine_energy = it_energy_from_runtime(runtime, power).with_derivation(
        RUNTIME_PATH, POWER_PATH
    )
    energy = facility_energy(machine_energy, pue).with_derivation(IT_ENERGY_PATH, PUE_PATH)
    costs: dict[str, Quantity] = {
        "time": Quantity(
            value=runtime.value,
            unit="s",
            status=runtime.status,
            notes=runtime.notes,
        ).with_derivation(RUNTIME_PATH),
        "energy": energy,
        "money": money_from_energy(energy, price).with_derivation(ENERGY_PATH, PRICE_PATH),
        "carbon": carbon_from_energy(energy, grid).with_derivation(ENERGY_PATH, GRID_PATH),
        "embodied_carbon": embodied_carbon(
            embodied=embodied, lifetime=lifetime, runtime=runtime
        ).with_derivation(EMBODIED_PATH, LIFETIME_PATH, RUNTIME_PATH),
        "water": water_from_energy(machine_energy, wue).with_derivation(IT_ENERGY_PATH, WUE_PATH),
    }

    projections, projection_notes = _projections(
        costs,
        runtime,
        slice_result,
        machine,
        settings,
        compute_bound=reading.is_compute_bound(),
        site={
            "pue": pue,
            "electricity_price": price,
            "grid_carbon_intensity": grid,
            "water_usage_effectiveness": wue,
        },
        scaling=scaling,
    )
    notes.extend(projection_notes)

    deployment = context.to_mapping() | machine.to_mapping()
    if origin is not None and not Path(origin).exists():
        # The tree was cloned, so the processor, the core count and the operating
        # system below are the auditing machine's. Somebody reading a model of a
        # training framework would otherwise take a laptop's figures for the place
        # that framework runs, and every energy number under them with it.
        deployment["machine_provenance"] = (
            "This describes the machine that ran the audit, not where the code "
            f"runs. {origin} was cloned and read here. Replace the machine, the "
            "provider and the country with the ones it actually runs on before "
            "any number below means anything about this project."
        )
    data: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "date_updated": date.today().isoformat(),
        "project": {
            "name": repository_name(origin) if origin else reading.root.name,
            "audited_from": origin or osh.path_without_home(str(reading.root)),
        },
        "unit_of_work": _unit_of_work(reading),
        "deployment": deployment,
        "assumptions": {
            "power_draw": power.to_mapping(),
            "pue": pue.to_mapping(),
            "electricity_price": price.to_mapping(),
            "grid_carbon_intensity": grid.to_mapping(),
            "water_usage_effectiveness": wue.to_mapping(),
            "hardware_embodied_carbon": embodied.to_mapping(),
            "hardware_lifetime": lifetime.to_mapping(),
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
    if reading.models:
        data["models_called"] = _model_blocks(reading, settings)
    if slice_result is not None:
        data["measurement"] = slice_result.to_mapping()
        if scaling is not None:
            # The exponent travels with the measurement rather than with the
            # projection that used it, because it is a fact about the workload
            # and stays true if nobody ever projects from it.
            data["measurement"]["scaling"] = scaling.to_mapping()
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


def audit_git_url(url: str, *, options: AuditOptions | None = None) -> AuditResult:
    """Clone a public repository into a temporary directory and audit it.

    Any URL ``git clone`` understands works: GitHub, GitLab, Codeberg, a
    self-hosted forge, an scp-style address. Nothing here is specific to one host,
    because nothing here does anything but hand the URL to git.

    Parameters
    ----------
    url : str
        A git URL.
    options : AuditOptions or None, optional
        What the audit should do.

    Returns
    -------
    AuditResult
        The model, its verdict, and the evidence. The model names the repository
        after the URL and records the URL as where it was audited from, rather
        than the temporary directory the clone happened to land in, which is
        nobody's business and gone by the time anyone reads the model.

    Raises
    ------
    RuntimeError
        If ``git`` is not on the path, or the clone fails, with the reason.

    Examples
    --------
    >>> audit_git_url("not a url")
    Traceback (most recent call last):
        ...
    RuntimeError: ...
    """
    folder = osh.make_temporary_directory(prefix="audit-")
    target = Path(folder) / repository_name(url)
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
    return audit(target, options=options, origin=url)
