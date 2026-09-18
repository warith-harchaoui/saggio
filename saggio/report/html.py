"""
The standalone HTML report.

Module summary
--------------
One file, opening offline, with no request to anybody: the stylesheet, the script,
the logo, and the catalogue data it needs are all inlined at render time. That
makes it something you can attach to an email, commit next to the code, or print
to PDF without the layout falling apart.

This module assembles; it does not author. The stylesheet is a stylesheet, the
script is a script, and the translations are a YAML file, all packaged as data and
read through :mod:`importlib.resources`. An earlier design kept all three inside
Python string literals, which cost it syntax highlighting, a linter exemption for
the whole module, a hand-maintained duplicate of the translation table, and one
outage where a French apostrophe closed a JavaScript string and silently disabled
every control on the page.

Usage example
-------------
>>> from saggio.report.html import render_html
>>> from saggio.templates import template_mapping
>>> page = render_html(template_mapping("annotated"))
>>> page.startswith("<!doctype html>")
True

Author
------
Warith Harchaoui
"""

from __future__ import annotations

import base64
import html
import json
import re
from functools import cache
from importlib import resources
from typing import Any, Final

import yaml

from ..catalog.registry import Catalog
from ..estimate.equivalences import GREEN_ALGORITHMS_SOURCE
from ..model.cost_model import CostModel
from ..model.dimensions import DimensionRegistry
from ..model.quantity import Quantity, looks_like_quantity
from ..model.taxonomy import STATUS_MEANING, STATUS_ORDER
from ..model.validate import overall_status
from .figures import (
    count_statuses,
    derivation_chain,
    honesty_bar,
    location_impact,
    scenario_energy,
)
from .markdown import NOT_KNOWN, ROUTE_LABEL, felt_size, format_number, format_quantity

#: Where the report's own assets live inside the package.
_ASSET_PACKAGE: Final[str] = "saggio.data.report"

#: The project's home, linked from the footer of every report.
PROJECT_URL: Final[str] = "https://github.com/warith-harchaoui/saggio"

#: The shape of a token in the report shell, as authored in ``reporting/report.html``.
_TOKEN_PATTERN: Final[re.Pattern[str]] = re.compile(r"\{\{([A-Z_]+)\}\}")


@cache
def _asset(name: str) -> str:
    """Return a packaged text asset.

    Parameters
    ----------
    name : str
        A filename inside the report asset package.

    Returns
    -------
    str
        The file's text. Cached, because a batch render reads the same stylesheet
        once per report otherwise.

    Examples
    --------
    >>> _asset("report.css").startswith("/*")
    True
    """
    return resources.files(_ASSET_PACKAGE).joinpath(name).read_text("utf-8")


def _fill(template: str, **values: str) -> str:
    """Substitute ``{{TOKEN}}`` placeholders in the report shell.

    Plain replacement rather than :meth:`str.format`, because the stylesheet and
    the script this fills in are full of braces of their own, and a format call
    would try to read them as fields.

    The substitution is a single pass, so a value is never scanned for tokens
    itself. Replacing token by token would mean a cost model whose notes happened
    to contain ``{{SCRIPT}}`` had that text replaced by the real script, which is
    a strange enough outcome to be worth one regular expression to rule out.

    Parameters
    ----------
    template : str
        The shell, as authored in ``reporting/report.html``.
    **values : str
        One value per token. Every token in the shell must be given one.

    Returns
    -------
    str
        The filled document.

    Raises
    ------
    KeyError
        If the shell holds a token nothing was given for. A report with a literal
        ``{{BODY}}`` in it would be worse than a failure here.

    Examples
    --------
    >>> _fill("<p>{{GREETING}}</p>", GREETING="hello")
    '<p>hello</p>'
    >>> _fill("{{A}}{{B}}", A="{{B}}", B="!")
    '{{B}}!'
    >>> _fill("<p>{{MISSING}}</p>")
    Traceback (most recent call last):
        ...
    KeyError: 'the report shell has unfilled tokens: MISSING'
    """
    missing: list[str] = []

    def substitute(match: re.Match[str]) -> str:
        token = match.group(1)
        if token not in values:
            missing.append(token)
            return match.group(0)
        return values[token]

    filled = _TOKEN_PATTERN.sub(substitute, template)
    if missing:
        raise KeyError(f"the report shell has unfilled tokens: {', '.join(sorted(set(missing)))}")
    return filled


@cache
def _logo_data_uri() -> str:
    """Return the project logo as a data URI.

    Returns
    -------
    str
        A ``data:image/png;base64,...`` string, so the page carries its own logo
        and opens identically with no network.

    Examples
    --------
    >>> _logo_data_uri().startswith("data:image/png;base64,")
    True
    """
    raw = resources.files(_ASSET_PACKAGE).joinpath("logo.png").read_bytes()
    return "data:image/png;base64," + base64.b64encode(raw).decode("ascii")


@cache
def translations() -> dict[str, dict[str, str]]:
    """Return the report's translation table.

    Returns
    -------
    dict
        Language code to key-value mapping. Packaged with the wheel, so there is
        exactly one copy and no fallback that can drift out of step with it.

    Examples
    --------
    >>> sorted(translations())
    ['en', 'fr']
    """
    loaded = yaml.safe_load(_asset("i18n.yaml")) or {}
    return {
        str(code): {str(key): str(value) for key, value in table.items()}
        for code, table in loaded.items()
        if isinstance(table, dict)
    }


def _escape(text: object) -> str:
    """Escape a value for HTML.

    Parameters
    ----------
    text : object
        Anything destined for the page.

    Returns
    -------
    str
        The escaped text, empty for ``None``.

    Examples
    --------
    >>> _escape("<b>")
    '&lt;b&gt;'
    >>> _escape(None)
    ''
    """
    return html.escape(str(text)) if text is not None else ""


def _badge(status: object) -> str:
    """Render an honesty status as a badge.

    Parameters
    ----------
    status : object
        A status label.

    Returns
    -------
    str
        The badge markup, empty when there is no status.

    Examples
    --------
    >>> _badge("measured")
    '<span class="badge badge-measured" title="Recorded from an actual run on the\
 target system.">measured</span>'
    >>> _badge(None)
    ''
    """
    if status is None:
        return ""
    label = str(status)
    known = label if label in STATUS_ORDER else ""
    meaning = STATUS_MEANING.get(label, "")
    classes = f"badge badge-{known}" if known else "badge"
    title = f' title="{_escape(meaning)}"' if meaning else ""
    return f'<span class="{classes}"{title}>{_escape(label)}</span>'


def _quantity_cell(quantity: Quantity) -> str:
    """Render a quantity as a table cell.

    Parameters
    ----------
    quantity : Quantity
        The quantity.

    Returns
    -------
    str
        A ``<td>`` marked as unknown when there is no number, so the missing
        values read as missing rather than as something a reader might skim past.

    Examples
    --------
    >>> _quantity_cell(Quantity(status="TODO"))
    '<td class="number unknown">not known</td>'
    """
    if not quantity.is_known():
        return f'<td class="number unknown">{NOT_KNOWN}</td>'
    return f'<td class="number">{_escape(format_quantity(quantity))}</td>'


def _table(
    headers: list[str],
    rows: list[str],
    *,
    i18n_keys: list[str] | None = None,
    widths: list[int] | None = None,
) -> str:
    """Wrap rows in a horizontally scrollable table.

    Parameters
    ----------
    headers : list of str
        Column headings.
    rows : list of str
        Pre-rendered ``<tr>`` markup.
    i18n_keys : list of str or None, optional
        Translation keys for the headings, one per column.
    widths : list of int or None, optional
        Column widths as percentages. Given these, the table lays out in them
        rather than in whatever its widest cell asks for; a column of dotted
        derivation paths otherwise takes the width it wants and pushes the notes
        off the right of the page.

    Returns
    -------
    str
        The table, or an empty string when there is nothing to show.

    Examples
    --------
    >>> _table(["a"], [])
    ''
    >>> "<colgroup>" in _table(["a"], ["<tr><td>1</td></tr>"], widths=[100])
    True
    """
    if not rows:
        return ""
    cells = []
    for index, heading in enumerate(headers):
        key = i18n_keys[index] if i18n_keys and index < len(i18n_keys) else None
        attribute = f' data-i18n="{key}"' if key else ""
        cells.append(f"<th{attribute}>{_escape(heading)}</th>")
    if widths:
        colgroup = (
            "<colgroup>"
            + "".join(f'<col style="width:{width}%">' for width in widths)
            + "</colgroup>"
        )
        opening = '<table class="sized">' + colgroup
    else:
        opening = "<table>"
    return (
        '<div class="scroller">'
        + opening
        + "<thead><tr>"
        + "".join(cells)
        + "</tr></thead><tbody>"
        + "".join(rows)
        + "</tbody></table></div>"
    )


def _heading(level: int, text: str, key: str | None = None) -> str:
    """Render a translatable heading.

    Parameters
    ----------
    level : int
        Heading level.
    text : str
        The English text, which is what a reader sees before the script runs.
    key : str or None, optional
        Translation key.

    Returns
    -------
    str
        The heading markup.

    Examples
    --------
    >>> _heading(2, "Honesty", "section.honesty")
    '<h2 data-i18n="section.honesty">Honesty</h2>'
    """
    attribute = f' data-i18n="{key}"' if key else ""
    return f"<h{level}{attribute}>{_escape(text)}</h{level}>"


def _verdict(model: CostModel) -> str:
    """Render the banner that states how far the whole model can be trusted.

    Parameters
    ----------
    model : CostModel
        The model.

    Returns
    -------
    str
        The banner markup, empty when the model states no numbers.

    Examples
    --------
    >>> _verdict(CostModel.from_mapping({}))
    ''
    """
    weakest = overall_status(model)
    if weakest is None:
        return ""
    return (
        f'<div class="verdict" data-status="{_escape(weakest)}">{_badge(weakest)}'
        f"<p>This model is only as good as its weakest number, which is "
        f"<code>{_escape(weakest)}</code>. {_escape(STATUS_MEANING.get(weakest, ''))}</p></div>"
    )


#: What each lead of the felt-size sentence says in English, keyed by (what one
#: table entry is, what the numbers restate). The i18n key follows the same pair.
_FELT_SIZE_LEADS: Final[dict[tuple[str, str], str]] = {
    ("unit", "one"): "One unit emits about",
    ("unit", "million"): "A million units emit about",
    ("run", "one"): "One run emits about",
    ("run", "million"): "A million runs emit about",
}


def _felt_size_paragraph(costs: object, *, per: str = "unit") -> str:
    """Render the felt-size restatement of a costs block's carbon, or nothing.

    The numbers are baked into the markup and only the labels around them carry
    ``data-i18n`` attributes, so the language picker changes the words without
    recomputing anything.

    Parameters
    ----------
    costs : object
        A scenario's or projection's ``costs`` mapping.
    per : str, optional
        What one entry of the table is: ``"unit"`` or ``"run"``.

    Returns
    -------
    str
        A paragraph of markup, empty when there is nothing worth restating.

    Examples
    --------
    >>> markup = _felt_size_paragraph({"carbon": {"value": 1.4, "unit": "gCO2e",
    ...                                           "status": "estimated"}})
    >>> 'data-i18n="equivalence.trees"' in markup
    True
    >>> _felt_size_paragraph({"carbon": {"status": "TODO"}})
    ''
    """
    sized = felt_size(costs)
    if sized is None:
        return ""
    scale, named = sized
    if not (named["tree_months"].is_known() and named["car_km"].is_known()):
        return ""
    parts = [
        f"{format_number(named['tree_months'].value)} "
        '<span data-i18n="equivalence.trees">tree-months</span>',
        f"{format_number(named['car_km'].value)} "
        '<span data-i18n="equivalence.car">km by car (EU average)</span>',
    ]
    flight = named["flight"]
    if flight.is_known():
        route = (flight.unit or "").removeprefix("flights ").strip()
        label = ROUTE_LABEL.get(route)
        fraction = float(flight.value)
        if label and fraction >= 1.0:
            parts.append(
                f"{format_number(fraction)} "
                f'<span data-i18n="equivalence.flights.{route}">{label} flights</span>'
            )
        elif label and fraction >= 0.005:
            parts.append(
                f"{fraction:.0%} "
                f'<span data-i18n="equivalence.flight.{route}">of a {label} flight</span>'
            )
    lead = _FELT_SIZE_LEADS[(per, scale)]
    return (
        f'<p class="muted equivalences"><span data-i18n="equivalence.{per}.{scale}">{lead}</span> '
        + " · ".join(parts)
        + f' — <a href="{GREEN_ALGORITHMS_SOURCE}" data-i18n="equivalence.note">'
        "estimated restatements, Green Algorithms coefficients</a>.</p>"
    )


def _costs_section(model: CostModel, registry: DimensionRegistry) -> str:
    """Render one table per scenario, one row per dimension.

    Parameters
    ----------
    model : CostModel
        The model.
    registry : DimensionRegistry
        The dimensions to report.

    Returns
    -------
    str
        The section markup, empty when there are no scenarios.

    Examples
    --------
    >>> _costs_section(CostModel.from_mapping({"scenarios": []}), DimensionRegistry())
    ''
    """
    scenarios = model.scenarios()
    if not scenarios:
        return ""
    blocks = [_heading(2, "What one unit costs", "section.costs")]
    for scenario in scenarios:
        blocks.append(_heading(3, str(scenario.get("name") or "scenario")))
        if scenario.get("description"):
            blocks.append(f'<p class="lede">{_escape(scenario["description"])}</p>')
        costs = scenario.get("costs")
        costs = costs if isinstance(costs, dict) else {}
        rows: list[str] = []
        for dimension in registry:
            raw = costs.get(dimension.key)
            if not looks_like_quantity(raw):
                continue
            quantity = Quantity.from_mapping(raw)
            derived = (
                ", ".join(f"<code>{_escape(path)}</code>" for path in quantity.derived_from)
                if quantity.is_derived()
                else "—"
            )
            rows.append(
                f'<tr><td title="{_escape(dimension.description)}">{_escape(dimension.label)}</td>'
                f"{_quantity_cell(quantity)}"
                f"<td>{_badge(quantity.status)}</td>"
                f'<td class="paths">{derived}</td>'
                f'<td class="muted">{_escape(quantity.notes)}</td></tr>'
            )
        blocks.append(
            _table(
                ["Dimension", "Per unit", "Status", "Derived from", "Notes"],
                rows,
                i18n_keys=[
                    "column.dimension",
                    "column.value",
                    "column.status",
                    "column.derived",
                    "column.notes",
                ],
                widths=[13, 16, 11, 30, 30],
            )
            or '<p class="muted">This scenario states no costs yet.</p>'
        )
        blocks.append(_felt_size_paragraph(costs, per="unit"))
    return "".join(blocks)


def _projections_section(model: CostModel) -> str:
    """Render what the run would cost elsewhere, and what that answer rests on.

    The page carried no projections at all until now, while the translations
    already had a heading waiting for them. A figure that only exists in the YAML
    is a figure most readers never see, and "what would this cost on an H100" is
    the question the people who never open a terminal are asking.

    Parameters
    ----------
    model : CostModel
        The model.

    Returns
    -------
    str
        The section markup, empty when nothing was projected.

    Examples
    --------
    >>> _projections_section(CostModel.from_mapping({}))
    ''
    """
    projections = model.data.get("projections")
    if not isinstance(projections, dict) or not projections:
        return ""
    blocks = [_heading(2, "Projections", "section.projections")]
    for name, block in projections.items():
        if not isinstance(block, dict):
            continue
        blocks.append(_heading(3, str(name).replace("_", " ")))
        if block.get("description"):
            blocks.append(f'<p class="lede">{_escape(block["description"])}</p>')
        rows: list[str] = []
        for key, value in block.items():
            if key in {"description", "costs", "held_constant", "costs_note"}:
                continue
            rows += _projection_rows(key, value)
        costs = block.get("costs")
        if isinstance(costs, dict):
            for key, value in costs.items():
                rows += _projection_rows(key, value)
        blocks.append(
            _table(
                ["", "Value", "Status", "How it was obtained"],
                rows,
                i18n_keys=["column.dimension", "column.value", "column.status", "column.method"],
                widths=[18, 20, 11, 51],
            )
        )
        blocks.append(_felt_size_paragraph(block.get("costs"), per="run"))
        for sentence in (block.get("costs_note"), block.get("held_constant")):
            if sentence:
                blocks.append(f'<p class="muted">{_escape(sentence)}</p>')
    return "".join(blocks)


def _projection_rows(key: str, value: object) -> list[str]:
    """Render one entry of a projections block as table rows.

    Parameters
    ----------
    key : str
        The entry's name in the block.
    value : object
        A projection mapping, a quantity mapping, or a plain scalar.

    Returns
    -------
    list of str
        ``<tr>`` markup, empty when the entry is not something to show.

    Examples
    --------
    >>> _projection_rows("target", "H100")[0][:32]
    '<tr><td>target</td><td>H100</td>'
    """
    if isinstance(value, dict) and looks_like_quantity(value.get("result")):
        quantity = Quantity.from_mapping(value["result"])
        rows = [
            f"<tr><td>{_escape(key)}</td>{_quantity_cell(quantity)}"
            f"<td>{_badge(quantity.status)}</td>"
            f'<td class="muted">{_escape(value.get("method"))}</td></tr>'
        ]
        bounds = value.get("bounds")
        if isinstance(bounds, dict):
            fastest, slowest = bounds.get("fastest"), bounds.get("slowest")
            if looks_like_quantity(fastest) and looks_like_quantity(slowest):
                low, high = Quantity.from_mapping(fastest), Quantity.from_mapping(slowest)
                rows.append(
                    f"<tr><td>{_escape(key)} &mdash; range</td>"
                    f'<td class="number">{_escape(format_quantity(low))} to '
                    f"{_escape(format_quantity(high))}</td>"
                    f"<td>{_badge(high.status)}</td>"
                    '<td class="muted">The fastest and the slowest the evidence '
                    "supports.</td></tr>"
                )
        return rows
    if looks_like_quantity(value):
        quantity = Quantity.from_mapping(value)
        return [
            f"<tr><td>{_escape(key)}</td>{_quantity_cell(quantity)}"
            f"<td>{_badge(quantity.status)}</td>"
            f'<td class="muted">{_escape(quantity.notes)}</td></tr>'
        ]
    if not isinstance(value, (dict, list)):
        return [
            f"<tr><td>{_escape(key)}</td><td>{_escape(value)}</td>"
            '<td>&mdash;</td><td class="muted">&mdash;</td></tr>'
        ]
    return []


def _assumptions_section(model: CostModel) -> str:
    """Render the numbers everything else rests on, with their sources.

    Parameters
    ----------
    model : CostModel
        The model.

    Returns
    -------
    str
        The section markup, empty when the model assumes nothing.

    Examples
    --------
    >>> _assumptions_section(CostModel.from_mapping({}))
    ''
    """
    assumptions = model.data.get("assumptions")
    if not isinstance(assumptions, dict):
        return ""
    rows: list[str] = []
    for key, raw in assumptions.items():
        if not looks_like_quantity(raw):
            continue
        quantity = Quantity.from_mapping(raw)
        source = (
            f'<a href="{_escape(quantity.source_url)}" rel="noopener">source</a>'
            + (f", read {_escape(quantity.retrieved_date)}" if quantity.retrieved_date else "")
            if quantity.source_url
            else "—"
        )
        rows.append(
            f"<tr><td><code>{_escape(key)}</code></td>"
            f"{_quantity_cell(quantity)}"
            f"<td>{_badge(quantity.status)}</td>"
            f'<td class="muted">{source}</td>'
            f'<td class="muted">{_escape(quantity.notes)}</td></tr>'
        )
    if not rows:
        return ""
    return _heading(2, "What the numbers rest on", "section.assumptions") + _table(
        ["Assumption", "Value", "Status", "Provenance", "Notes"],
        rows,
        widths=[20, 14, 11, 18, 37],
    )


def _services_section(model: CostModel) -> str:
    """Render the paid services the code calls, with the evidence.

    Parameters
    ----------
    model : CostModel
        The model.

    Returns
    -------
    str
        The section markup, empty when none were detected.

    Examples
    --------
    >>> _services_section(CostModel.from_mapping({}))
    ''
    """
    services = model.data.get("external_services")
    if not isinstance(services, list) or not services:
        return ""
    rows: list[str] = []
    for entry in services:
        if not isinstance(entry, dict):
            continue
        price = entry.get("price_per_unit") or entry.get("price")
        quantity = Quantity.from_mapping(price) if looks_like_quantity(price) else Quantity()
        pricing = entry.get("pricing_source_url")
        rows.append(
            f"<tr><td>{_escape(entry.get('name') or entry.get('key'))}</td>"
            f"<td><code>{_escape(entry.get('detected_at'))}</code></td>"
            f"<td><code>{_escape(entry.get('evidence'))}</code></td>"
            f"{_quantity_cell(quantity)}"
            + (
                f'<td><a href="{_escape(pricing)}" rel="noopener">prices</a></td>'
                if pricing
                else "<td>—</td>"
            )
            + "</tr>"
        )
    return (
        _heading(2, "Services this code pays for", "section.services")
        + '<p class="lede">Prices are not copied into this model. An API price copied today '
        "is wrong by next quarter, so the report says where the current one lives and "
        "leaves the figure open until somebody reads it.</p>"
        + _table(
            ["Service", "Found at", "Evidence", "Per unit", "Where to price it"],
            rows,
            widths=[16, 20, 32, 17, 15],
        )
    )


def _models_section(model: CostModel) -> str:
    """Render the models the code calls, and what each is charged at.

    Parameters
    ----------
    model : CostModel
        The model.

    Returns
    -------
    str
        The section markup, empty when the code names no model.

    Examples
    --------
    >>> _models_section(CostModel.from_mapping({}))
    ''
    """
    called = model.data.get("models_called")
    if not isinstance(called, list) or not called:
        return ""
    blocks = [
        _heading(2, "Models this code calls", "section.models"),
        '<p class="lede">A rate is not a cost. These are what the vendor charges per '
        "unit; how many of those units one unit of work spends is the open half, and "
        "reading the code cannot establish it.</p>",
    ]
    for entry in called:
        if not isinstance(entry, dict):
            continue
        where = entry.get("detected_at")
        blocks.append(
            _heading(3, str(entry.get("model") or "model"))
            + (f'<p class="muted"><code>{_escape(where)}</code></p>' if where else "")
        )
        rates = entry.get("rates")
        rows: list[str] = []
        if isinstance(rates, dict):
            for key, raw in rates.items():
                if not looks_like_quantity(raw):
                    continue
                quantity = Quantity.from_mapping(raw)
                source = (
                    f'<a href="{_escape(quantity.source_url)}" rel="noopener">source</a>'
                    + (
                        f", read {_escape(quantity.retrieved_date)}"
                        if quantity.retrieved_date
                        else ""
                    )
                    if quantity.source_url
                    else "—"
                )
                rows.append(
                    f"<tr><td><code>{_escape(key)}</code></td>"
                    f"{_quantity_cell(quantity)}"
                    f"<td>{_badge(quantity.status)}</td>"
                    f"<td><code>{_escape(quantity.source_kind or '—')}</code></td>"
                    f'<td class="muted">{source}</td></tr>'
                )
        blocks.append(
            _table(
                ["Rate", "Value", "Status", "Provenance", "Source"],
                rows,
                widths=[28, 18, 12, 16, 26],
            )
            or '<p class="muted">No published rate was found for this model.</p>'
        )
        if entry.get("rates_provenance"):
            blocks.append(f'<p class="muted">{_escape(entry["rates_provenance"])}</p>')
    return "".join(blocks)


def _measurement_section(model: CostModel) -> str:
    """Render how a measurement was taken, and what to distrust about it.

    The Markdown report has carried this section from the start; the HTML page
    silently dropped it, so the reader most likely to be sent the page — the
    one who never opens a terminal — was the one who never saw the command,
    the hot path, or the warnings that qualify every number above.

    Parameters
    ----------
    model : CostModel
        The model.

    Returns
    -------
    str
        The section markup, empty when nothing was run.

    Examples
    --------
    >>> _measurement_section(CostModel.from_mapping({}))
    ''
    >>> markup = _measurement_section(CostModel.from_mapping(
    ...     {"measurement": {"command": ["python", "train.py"],
    ...                      "warnings": ["read this"]}}))
    >>> "train.py" in markup and "read this" in markup
    True
    """
    measurement = model.data.get("measurement")
    if not isinstance(measurement, dict) or not measurement:
        return ""
    blocks = [_heading(2, "How it was measured", "section.measurement")]
    command = measurement.get("command")
    if isinstance(command, list):
        blocks.append(
            "<pre><code>" + _escape(" ".join(str(part) for part in command)) + "</code></pre>"
        )
    rows = [
        f"<tr><td>{_escape(str(key).replace('_', ' '))}</td><td>{_escape(value)}</td></tr>"
        for key, value in measurement.items()
        if key not in {"command", "hot_path", "warnings"} and not isinstance(value, (dict, list))
    ]
    if rows:
        blocks.append(_table(["", ""], rows, widths=[30, 70]))
    hot_path = measurement.get("hot_path")
    if isinstance(hot_path, list) and hot_path:
        entries = [
            f"<tr><td><code>{_escape(entry.get('function'))}</code></td>"
            f"<td>{_escape(entry.get('cumulative_seconds'))}</td>"
            f"<td>{_escape(entry.get('calls'))}</td></tr>"
            for entry in hot_path
            if isinstance(entry, dict)
        ]
        blocks.append(_table(["Function", "Cumulative seconds", "Calls"], entries))
    warnings = measurement.get("warnings")
    if isinstance(warnings, list) and warnings:
        bullets = "".join(f"<li>{_escape(item)}</li>" for item in warnings)
        blocks.append(f'<ul class="plain">{bullets}</ul>')
    return "".join(blocks)


def _whatif_section(model: CostModel, *, overlay: Any = None) -> str:
    """Render the panel that recomputes the model somewhere else.

    Parameters
    ----------
    model : CostModel
        The model, whose machine energy is what gets rescaled.
    overlay : pathlib.Path or None, optional
        Catalogue overlay directory.

    Returns
    -------
    str
        The panel markup, empty when the model states no machine energy to
        rescale. There is deliberately no panel without one: a what-if built on
        an invented baseline would be the worst number on the page.

    Examples
    --------
    >>> _whatif_section(CostModel.from_mapping({}))
    ''
    """
    if not scenario_energy(model).is_known():
        return ""

    countries = Catalog.load("grid", overlay=overlay).rows("countries")
    providers = Catalog.load("providers", overlay=overlay).rows("providers")
    current_country = str(model.get("deployment.country") or "")
    current_provider = str(model.get("deployment.provider") or "on-prem")

    country_options = "".join(
        f'<option value="{_escape(key)}"'
        + (" selected" if key == current_country else "")
        + f">{_escape(row.get('name') or key)}</option>"
        for key, row in sorted(
            countries.items(), key=lambda item: str(item[1].get("name") or item[0])
        )
    )
    provider_options = "".join(
        f'<option value="{_escape(key)}"'
        + (" selected" if key == current_provider else "")
        + f">{_escape(row.get('name') or key)}</option>"
        for key, row in providers.items()
    )
    panel = location_impact(countries, current_country or None)

    return (
        # S608 reads the words "What if" as the start of a SQL clause. There is no
        # database anywhere in this package.
        _heading(2, "What if it ran somewhere else", "section.whatif")  # noqa: S608
        + '<div class="card whatif-card"><div class="whatif">'
        + '<div><label for="whatif-country" data-i18n="whatif.country">Country</label>'
        f'<select id="whatif-country">{country_options}</select></div>'
        + '<div><label for="whatif-provider" data-i18n="whatif.provider">Provider</label>'
        f'<select id="whatif-provider">{provider_options}</select></div>'
        + "</div>"
        + '<dl class="readout">'
        + '<div><dt data-i18n="whatif.energy">Energy</dt><dd id="whatif-energy">—</dd></div>'
        + '<div><dt data-i18n="whatif.carbon">Carbon</dt><dd id="whatif-carbon">—</dd></div>'
        + '<div><dt data-i18n="whatif.money">Electricity</dt><dd id="whatif-money">—</dd></div>'
        + '<div><dt data-i18n="whatif.water">Water</dt><dd id="whatif-water">—</dd></div>'
        + "</dl>"
        + '<p class="muted" data-i18n="whatif.note">Recomputed in your browser from the '
        "energy this model already states. Nothing is sent anywhere.</p>"
        + (f"<figure>{panel}</figure>" if panel else "")
        + "</div>"
    )


def _mapping_section(title: str, key: str, mapping: object) -> str:
    """Render a flat mapping as a two-column table.

    Parameters
    ----------
    title : str
        The heading.
    key : str
        Translation key for the heading.
    mapping : object
        Expected to be a mapping of label to scalar.

    Returns
    -------
    str
        The section markup, empty when there is nothing to show.

    Examples
    --------
    >>> _mapping_section("Where it runs", "section.deployment", {})
    ''
    """
    if not isinstance(mapping, dict) or not mapping:
        return ""
    rows = [
        f"<tr><td>{_escape(str(name).replace('_', ' '))}</td><td>{_escape(value)}</td></tr>"
        for name, value in mapping.items()
        if not isinstance(value, (dict, list))
    ]
    if not rows:
        return ""
    return _heading(2, title, key) + _table(["", ""], rows)


def _list_section(title: str, key: str, items: object) -> str:
    """Render a titled bullet list.

    Parameters
    ----------
    title : str
        The heading.
    key : str
        Translation key for the heading.
    items : object
        Expected to be a list of strings.

    Returns
    -------
    str
        The section markup, empty when there is nothing to show.

    Examples
    --------
    >>> _list_section("Not counted", "section.exclusions", [])
    ''
    """
    if not isinstance(items, list) or not items:
        return ""
    bullets = "".join(f"<li>{_escape(item)}</li>" for item in items)
    return _heading(2, title, key) + f'<ul class="plain">{bullets}</ul>'


def _page_data(model: CostModel, *, overlay: Any = None) -> str:
    """Build the JSON blob the page's script reads.

    Everything the script needs arrives this way, serialised with
    :func:`json.dumps`, so no value is ever pasted into a JavaScript literal by
    hand and an apostrophe in a French sentence cannot break the page.

    Parameters
    ----------
    model : CostModel
        The model.
    overlay : pathlib.Path or None, optional
        Catalogue overlay directory.

    Returns
    -------
    str
        A JSON document.

    Examples
    --------
    >>> json.loads(_page_data(CostModel.from_mapping({})))["machine_energy_kwh"] is None
    True
    """
    countries = Catalog.load("grid", overlay=overlay).rows("countries")
    providers = Catalog.load("providers", overlay=overlay).rows("providers")
    energy = scenario_energy(model)
    payload = {
        "i18n": translations(),
        "machine_energy_kwh": float(energy.value) if energy.is_known() else None,
        "countries": {
            key: {
                "name": row.get("name"),
                "carbon": row.get("carbon_gco2e_per_kwh"),
                "price": row.get("price_usd_per_kwh"),
            }
            for key, row in countries.items()
        },
        "providers": {
            key: {
                "name": row.get("name"),
                "pue": row.get("pue"),
                "wue": row.get("wue_l_per_kwh"),
            }
            for key, row in providers.items()
        },
    }
    # The closing tag has to be broken up: a JSON string containing it verbatim
    # would end the <script> element early, whatever the type attribute says.
    return json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")


def render_html(model: CostModel | dict[str, Any], *, overlay: Any = None) -> str:
    """Render a cost model as one self-contained HTML page.

    Parameters
    ----------
    model : CostModel or dict
        The model.
    overlay : pathlib.Path or None, optional
        Catalogue overlay directory, used for the what-if panel's data.

    Returns
    -------
    str
        A complete document, with the stylesheet, script, logo, and catalogue data
        inlined, so it opens offline and makes no request to anybody.

    Examples
    --------
    >>> page = render_html({"project": {"name": "demo"}, "scenarios": []})
    >>> "<title>" in page and "demo" in page
    True
    """
    wrapped = model if isinstance(model, CostModel) else CostModel.from_mapping(model)
    registry = wrapped.registry
    project = wrapped.data.get("project")
    name = project.get("name") if isinstance(project, dict) else None
    title = f"Cost of running {name}" if name else "Cost of running this code"

    languages = "".join(
        f'<option value="{_escape(code)}">{_escape(code.upper())}</option>'
        for code in sorted(translations())
    )

    updated = wrapped.data.get("date_updated")
    subtitle = (
        f"Last updated {_escape(updated)}. Schema {_escape(wrapped.schema_version)}."
        if updated
        else f"Schema {_escape(wrapped.schema_version)}."
    )

    unit = wrapped.data.get("unit_of_work")
    unit_block = ""
    if isinstance(unit, dict):
        unit_block = (
            _heading(2, "One unit of work", "section.unit")
            + f'<div class="card"><p><strong>{_escape(unit.get("name"))}</strong> '
            f"{_badge(unit.get('status'))}</p>"
            + (f"<p>{_escape(unit.get('description'))}</p>" if unit.get("description") else "")
            + (
                '<ul class="plain">'
                + "".join(f"<li>{_escape(item)}</li>" for item in unit["out_of_scope"])
                + "</ul>"
                if isinstance(unit.get("out_of_scope"), list) and unit["out_of_scope"]
                else ""
            )
            + "</div>"
        )

    chain = derivation_chain(wrapped)
    chain_block = (
        f"<figure>{chain}<figcaption>Each box is coloured by how well founded that "
        "number is. A weak colour upstream caps everything downstream of it: that is "
        "the weakest-link rule, drawn.</figcaption></figure>"
        if chain
        else ""
    )

    body = "".join(
        [
            f"<h1>{_escape(title)}</h1>",
            f'<p class="muted">{subtitle}</p>',
            _verdict(wrapped),
            _heading(2, "Honesty", "section.honesty"),
            f"<figure>{honesty_bar(count_statuses(wrapped))}</figure>",
            chain_block,
            unit_block,
            _mapping_section("Where it runs", "section.deployment", wrapped.data.get("deployment")),
            _costs_section(wrapped, registry),
            _projections_section(wrapped),
            _whatif_section(wrapped, overlay=overlay),
            _assumptions_section(wrapped),
            _services_section(wrapped),
            _models_section(wrapped),
            _measurement_section(wrapped),
            _list_section("Not counted", "section.exclusions", wrapped.data.get("exclusions")),
            _list_section(
                "Rules this model follows", "section.rules", wrapped.data.get("provenance_rules")
            ),
        ]
    )

    return _fill(
        _asset("report.html"),
        LANG="en",
        TITLE=_escape(title),
        LOGO=_logo_data_uri(),
        STYLE=_asset("report.css"),
        LANGUAGES=languages,
        BODY=body,
        PROJECT_URL=PROJECT_URL,
        DATA=_page_data(wrapped, overlay=overlay),
        SCRIPT=_asset("report.js"),
    )
