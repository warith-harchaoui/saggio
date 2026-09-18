"""
saggio: what it costs to run your code, and how much to trust it.

Module summary
--------------
This package answers one question about a piece of software, per unit of work:
what does running it cost? Money, time, energy, carbon, water, and whatever else
your team decides to watch. The answer is a YAML file you commit next to the code,
and reports rendered from it.

What makes the answer worth having is the second half of every number: its
*status*. ``measured`` means a counter said so. ``estimated`` means a sourced
formula said so. ``placeholder`` means the field is being held open. ``TODO`` means
a human has to supply it. A derived value names the numbers it came from and may
never claim to be better founded than the weakest of them, and the validator
enforces that by walking the file rather than by trusting it.

The package is organised in four layers with a strict direction of dependency.
:mod:`~saggio.model` is the pure vocabulary and the rules.
:mod:`~saggio.catalog` holds sourced facts about the world.
:mod:`~saggio.estimate` and
:mod:`~saggio.analyze` turn facts and measurements into numbers.
:mod:`~saggio.report` and
:mod:`~saggio.cli` are ways of reaching all of it. Nothing lower
imports anything higher, so the command line can do nothing a library caller
cannot.

Usage example
-------------
>>> import saggio
>>> result = saggio.audit(".", options=saggio.AuditOptions(run=False, use_llm=False))
>>> result.report.ok
True
>>> saggio.render_markdown(result.model).startswith("# Cost of running")
True

Author
------
Warith Harchaoui, Ph.D. — https://linkedin.com/in/warith-harchaoui/
"""

from __future__ import annotations

from typing import Final

#: The installed version, kept in step with pyproject.toml at release.
__version__: Final[str] = "1.0.0"

__author__: Final[str] = "Warith Harchaoui, Ph.D."
__email__: Final[str] = "warith.harchaoui@sev7n.io"

from .analyze import (
    RepositoryReading,
    SliceResult,
    read_repository,
    run_slice,
)
from .auditor import AuditOptions, AuditResult, audit, audit_git_url, repository_name
from .catalog import Catalog, add_row, stale_report
from .diff import Change, Comparison, compare
from .estimate import (
    DeploymentContext,
    MachineProfile,
    Projection,
    car_km,
    carbon_from_energy,
    detect_machine,
    energy_from_runtime,
    equivalences,
    flight_fraction,
    it_energy_from_runtime,
    money_from_energy,
    node_power,
    project_to_completion,
    project_to_machine,
    tree_months,
    water_from_energy,
)
from .fold import Fold, fold_measurement
from .model import (
    CANONICAL_DIMENSIONS,
    ESTIMATED,
    MEASURED,
    PLACEHOLDER,
    SCHEMA_VERSION,
    TODO,
    CostModel,
    Dimension,
    DimensionRegistry,
    Issue,
    Quantity,
    Report,
    overall_status,
    validate,
    weakest,
)
from .report import render_dashboard, render_html, render_markdown, render_office
from .templates import DEFAULT_TEMPLATE, TEMPLATES, template_mapping, template_text

__all__ = [
    "__version__",
    "__author__",
    "__email__",
    # The model and its rules.
    "CostModel",
    "Quantity",
    "Dimension",
    "DimensionRegistry",
    "CANONICAL_DIMENSIONS",
    "SCHEMA_VERSION",
    "MEASURED",
    "ESTIMATED",
    "PLACEHOLDER",
    "TODO",
    "weakest",
    "validate",
    "overall_status",
    "Report",
    "Issue",
    # Facts about the world.
    "Catalog",
    "add_row",
    "stale_report",
    # Estimation.
    "DeploymentContext",
    "MachineProfile",
    "detect_machine",
    "node_power",
    "it_energy_from_runtime",
    "energy_from_runtime",
    "carbon_from_energy",
    "water_from_energy",
    "money_from_energy",
    "tree_months",
    "car_km",
    "flight_fraction",
    "equivalences",
    "Projection",
    "project_to_completion",
    "project_to_machine",
    # Reading and running a repository.
    "RepositoryReading",
    "read_repository",
    "SliceResult",
    "run_slice",
    # The whole job.
    "AuditOptions",
    "AuditResult",
    "audit",
    "audit_git_url",
    "repository_name",
    "Fold",
    "compare",
    "fold_measurement",
    "Comparison",
    "Change",
    # Reports.
    "render_markdown",
    "render_html",
    "render_office",
    "render_dashboard",
    "template_text",
    "template_mapping",
    "TEMPLATES",
    "DEFAULT_TEMPLATE",
]
