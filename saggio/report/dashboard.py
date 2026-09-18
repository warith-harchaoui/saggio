"""
The dashboard: several cost models on one page.

Module summary
--------------
A team does not run one project, and the Cambridge Green Algorithms dashboard
showed why the aggregate view matters: the footprint people act on is the one
they can see next to everyone else's. This page is that view for saggio models:
every ``cost_of_running.yaml`` a team commits, side by side.

One honesty rule shapes the whole page. Each project defines its own unit of
work, so costs per unit do **not** compare across rows, and the page says so
where the table starts instead of letting bar lengths imply a ranking that does
not exist. The one thing that does compare exactly is the *share* of each model
that is measured, estimated, or still open, and that is the figure the page
leads with.

The page is assembled from the same shell, stylesheet, script, and translations
as the single-model report, so it opens offline, follows the reader's theme, and
speaks the same two languages.

Usage example
-------------
>>> from saggio.report.dashboard import render_dashboard
>>> from saggio.templates import template_mapping
>>> page = render_dashboard([template_mapping("annotated")])
>>> page.startswith("<!doctype html>")
True

Author
------
Warith Harchaoui
"""

from __future__ import annotations

import json
from typing import Any, Final

from ..model.cost_model import CostModel
from ..model.quantity import Quantity, looks_like_quantity
from ..model.validate import overall_status
from .figures import count_statuses, honesty_overview
from .html import (
    PROJECT_URL,
    _asset,
    _badge,
    _escape,
    _fill,
    _heading,
    _logo_data_uri,
    _table,
    translations,
)
from .markdown import format_quantity

#: The cost columns every row shows, in reading order. These are the canonical
#: dimensions; a model's own extra dimensions belong on its own report page,
#: where their definitions sit next to them.
_COLUMNS: Final[list[tuple[str, str]]] = [
    ("money", "Money"),
    ("time", "Time"),
    ("energy", "Energy"),
    ("carbon", "Carbon"),
    ("water", "Water"),
]


def _project_name(model: CostModel, ordinal: int) -> str:
    """Return what a model should be called on the dashboard.

    Parameters
    ----------
    model : CostModel
        The model.
    ordinal : int
        Its position, for the fallback name.

    Returns
    -------
    str
        The project's own name, or an honest placeholder that says the model
        did not state one.

    Examples
    --------
    >>> _project_name(CostModel.from_mapping({"project": {"name": "demo"}}), 0)
    'demo'
    >>> _project_name(CostModel.from_mapping({}), 2)
    'unnamed project 3'
    """
    project = model.data.get("project")
    name = project.get("name") if isinstance(project, dict) else None
    return str(name) if name else f"unnamed project {ordinal + 1}"


def _cost_cell(costs: dict[str, Any], key: str) -> str:
    """Render one cost of one scenario as a table cell.

    Parameters
    ----------
    costs : dict
        The scenario's costs.
    key : str
        The dimension to show.

    Returns
    -------
    str
        A value with its badge, or an em dash when the scenario does not carry
        the dimension at all. A dimension that exists but is open renders as
        the word, never as a blank.

    Examples
    --------
    >>> "2 USD" in _cost_cell({"money": {"value": 2.0, "currency": "USD",
    ...                                  "status": "measured"}}, "money")
    True
    >>> _cost_cell({}, "money")
    '<td class="muted">—</td>'
    """
    raw = costs.get(key)
    if not looks_like_quantity(raw):
        return '<td class="muted">—</td>'
    quantity = Quantity.from_mapping(raw)
    return f"<td>{_escape(format_quantity(quantity))} {_badge(quantity.status)}</td>"


def _rows(models: list[CostModel]) -> list[str]:
    """Build the overview table's rows, one per project scenario.

    Parameters
    ----------
    models : list of CostModel
        The models, in the order they were given.

    Returns
    -------
    list of str
        Table row markup. A project with several scenarios gets one row each,
        named ``project — scenario``; a project with none still gets a row, so
        the dashboard shows it exists rather than silently dropping it.

    Examples
    --------
    >>> rows = _rows([CostModel.from_mapping({"project": {"name": "x"}})])
    >>> len(rows)
    1
    """
    rows: list[str] = []
    for ordinal, model in enumerate(models):
        name = _project_name(model, ordinal)
        weakest = overall_status(model)
        scenarios = model.scenarios() or [{}]
        several = len(scenarios) > 1
        for scenario in scenarios:
            label = name
            if several and scenario.get("name"):
                label = f"{name} — {scenario['name']}"
            unit = model.data.get("unit_of_work")
            unit_name = unit.get("name") if isinstance(unit, dict) else None
            costs = scenario.get("costs")
            costs = costs if isinstance(costs, dict) else {}
            cells = "".join(_cost_cell(costs, key) for key, _ in _COLUMNS)
            rows.append(
                f"<tr><td>{_escape(label)}</td>"
                f'<td class="muted">{_escape(unit_name) or "—"}</td>'
                f"<td>{_badge(weakest)}</td>"
                f"{cells}</tr>"
            )
    return rows


def render_dashboard(models: list[CostModel | dict[str, Any]]) -> str:
    """Render several cost models as one self-contained HTML page.

    Parameters
    ----------
    models : list of CostModel or dict
        The models, typically every committed ``cost_of_running.yaml`` a team
        has.

    Returns
    -------
    str
        A complete document on the report's own shell: inlined stylesheet,
        script, logo, and translations, no request to anybody.

    Raises
    ------
    ValueError
        If no model was given: a dashboard of nothing would render a page that
        looks like an empty team rather than a mistake.

    Examples
    --------
    >>> from saggio.templates import template_mapping
    >>> page = render_dashboard([template_mapping("annotated"),
    ...                          template_mapping("minimal")])
    >>> "How well founded each model is" in page
    True
    >>> render_dashboard([])
    Traceback (most recent call last):
        ...
    ValueError: A dashboard needs at least one cost model.
    """
    if not models:
        raise ValueError("A dashboard needs at least one cost model.")
    wrapped = [
        model if isinstance(model, CostModel) else CostModel.from_mapping(model) for model in models
    ]

    overview = honesty_overview(
        [
            (_project_name(model, index), count_statuses(model))
            for index, model in enumerate(wrapped)
        ]
    )
    table = _table(
        ["Project", "Unit of work", "Weakest"] + [label for _, label in _COLUMNS],
        _rows(wrapped),
        widths=[20, 17, 10, 11, 10, 11, 11, 10],
    )

    count = len(wrapped)
    title = f"Cost of running {count} project" + ("s" if count > 1 else "")
    body = "".join(
        [
            f"<h1>{_escape(title)}</h1>",
            '<p class="muted" data-i18n="dashboard.lede">Every committed cost model, '
            "side by side. Each project defines its own unit of work, so the costs "
            "below are per that project's unit and the rows do not compare with each "
            "other; how well founded each model is compares exactly.</p>",
            _heading(2, "How well founded each model is", "section.honesty"),
            f"<figure>{overview}</figure>" if overview else "",
            _heading(2, "What one unit costs, per project", "section.costs"),
            table,
        ]
    )

    languages = "".join(
        f'<option value="{_escape(code)}">{_escape(code.upper())}</option>'
        for code in sorted(translations())
    )
    # The script expects the page's data blob; the dashboard has no what-if
    # panel, so the machine energy is honestly absent and the catalogues empty.
    payload = {
        "i18n": translations(),
        "machine_energy_kwh": None,
        "countries": {},
        "providers": {},
    }
    return _fill(
        _asset("report.html"),
        LANG="en",
        TITLE=_escape(title),
        LOGO=_logo_data_uri(),
        STYLE=_asset("report.css"),
        LANGUAGES=languages,
        BODY=body,
        PROJECT_URL=PROJECT_URL,
        DATA=json.dumps(payload, ensure_ascii=False).replace("</", "<\\/"),
        SCRIPT=_asset("report.js"),
    )
