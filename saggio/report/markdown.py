"""
The Markdown report: the one that gets read in a pull request.

Module summary
--------------
The report a team actually reads is the one that renders in a code review, so this
is the primary output and the others are derived from it. It is written to be
skimmed top to bottom: the verdict first, then what one unit of work is, then what
it costs, then everything the numbers rest on, then what is deliberately not
counted.

Two rules shape every table here. A number is never shown without its status
beside it, because a figure without its provenance is the thing this package
exists to stop. And a value that does not exist is shown as the word that says so,
never as a zero or a dash, because a blank invites the reader to fill it in
themselves with something optimistic.

Usage example
-------------
>>> from saggio.report.markdown import render_markdown
>>> from saggio.templates import template_mapping
>>> "Honesty" in render_markdown(template_mapping("annotated"))
True

Author
------
Warith Harchaoui
"""

from __future__ import annotations

from typing import Any, Final

from ..model.cost_model import CostModel
from ..model.dimensions import DimensionRegistry
from ..model.quantity import Quantity, looks_like_quantity
from ..model.taxonomy import STATUS_MEANING, STATUS_ORDER
from ..model.validate import overall_status

#: Shown in place of a number that does not exist, so a reader never mistakes an
#: open field for a zero.
NOT_KNOWN: Final[str] = "not known"

#: What each status means for the reader of a report, rather than for the
#: validator. Slightly shorter than the canonical definitions, because a legend is
#: read in passing.
_LEGEND: Final[dict[str, str]] = dict(STATUS_MEANING)

#: How many significant figures a number is shown to. Beyond this the digits are
#: noise: nothing in this chain is known to seven places.
_SIGNIFICANT_FIGURES: Final[int] = 4


def format_number(value: float | int | None) -> str:
    """Render a number for a report, without pretending to precision it lacks.

    Parameters
    ----------
    value : float or int or None
        The number, or ``None``.

    Returns
    -------
    str
        A readable figure, in scientific notation when a plain one would be a row
        of zeros, or :data:`NOT_KNOWN`.

    Examples
    --------
    >>> format_number(1234.5678)
    '1235'
    >>> format_number(2.5e-05)
    '2.5e-05'
    >>> format_number(0)
    '0'
    >>> format_number(None)
    'not known'
    """
    if value is None:
        return NOT_KNOWN
    number = float(value)
    if number == 0.0:
        return "0"
    # The general format picks a plain figure or scientific notation for us, and
    # drops trailing zeros either way. Energy per request is routinely a hundred
    # thousandth of a kilowatt-hour, so scientific notation is the common case,
    # not the exception.
    return f"{number:.{_SIGNIFICANT_FIGURES}g}"


def format_quantity(quantity: Quantity) -> str:
    """Render a quantity as a number with its unit.

    Parameters
    ----------
    quantity : Quantity
        The quantity.

    Returns
    -------
    str
        The number and unit, or :data:`NOT_KNOWN`.

    Examples
    --------
    >>> format_quantity(Quantity(value=1.5, unit="kWh", status="measured"))
    '1.5 kWh'
    >>> format_quantity(Quantity(value=2.0, currency="EUR", status="measured"))
    '2 EUR'
    >>> format_quantity(Quantity(status="TODO"))
    'not known'
    """
    if not quantity.is_known():
        return NOT_KNOWN
    number = format_number(quantity.value)
    unit = quantity.currency or quantity.unit
    return f"{number} {unit}" if unit and unit != "currency" else number


def _escape(text: object) -> str:
    r"""Escape a value so it cannot break out of a Markdown table cell.

    Parameters
    ----------
    text : object
        Anything to put in a cell.

    Returns
    -------
    str
        The text with pipes and newlines neutralised.

    Examples
    --------
    >>> _escape("a | b")
    'a \\| b'
    >>> _escape(None)
    ''
    """
    if text is None:
        return ""
    return str(text).replace("|", "\\|").replace("\n", " ").strip()


def _table(headers: list[str], rows: list[list[str]]) -> str:
    """Render a Markdown table, or nothing when there are no rows.

    Parameters
    ----------
    headers : list of str
        Column headings.
    rows : list of list of str
        Cell values, already escaped.

    Returns
    -------
    str
        The table, or an empty string.

    Examples
    --------
    >>> _table(["a"], [])
    ''
    >>> _table(["a"], [["1"]]).splitlines()[0]
    '| a |'
    """
    if not rows:
        return ""
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join(["---"] * len(headers)) + "|"]
    lines.extend("| " + " | ".join(row) + " |" for row in rows)
    return "\n".join(lines)


def _status_counts(model: CostModel) -> dict[str, int]:
    """Count the model's quantities by honesty status.

    Parameters
    ----------
    model : CostModel
        The model.

    Returns
    -------
    dict
        Status to count, in canonical order, including zeros so the shape of the
        table does not change between models.

    Examples
    --------
    >>> _status_counts(CostModel.from_mapping(
    ...     {"a": {"value": 1, "status": "measured"}}))["measured"]
    1
    """
    counts = dict.fromkeys(STATUS_ORDER, 0)
    for _, raw in model.quantities():
        status = str(raw.get("status", ""))
        if status in counts:
            counts[status] += 1
    return counts


def _source_cell(quantity: Quantity) -> str:
    """Render a quantity's provenance as one cell.

    Parameters
    ----------
    quantity : Quantity
        The quantity.

    Returns
    -------
    str
        A Markdown link with the date it was read, or an em dash when the value
        was not sourced from anywhere.

    Examples
    --------
    >>> _source_cell(Quantity(source_url="https://x.invalid", retrieved_date="2026-01-01"))
    '[source](https://x.invalid), read 2026-01-01'
    >>> _source_cell(Quantity())
    '—'
    """
    if not quantity.source_url:
        return "—"
    link = f"[source]({quantity.source_url})"
    if quantity.retrieved_date:
        return f"{link}, read {quantity.retrieved_date}"
    return link


def _header(model: CostModel) -> list[str]:
    """Render the title and the one-line verdict.

    Parameters
    ----------
    model : CostModel
        The model.

    Returns
    -------
    list of str
        Markdown lines.

    Examples
    --------
    >>> _header(CostModel.from_mapping({"project": {"name": "x"}}))[0]
    '# Cost of running x'
    """
    project = model.data.get("project")
    name = project.get("name") if isinstance(project, dict) else None
    lines = [f"# Cost of running {name}" if name else "# Cost of running this code", ""]

    weakest = overall_status(model)
    if weakest:
        lines += [
            f"**This model is only as good as its weakest number, which is `{weakest}`.** "
            f"{_LEGEND.get(weakest, '')}",
            "",
        ]
    updated = model.data.get("date_updated")
    if updated:
        lines += [f"Last updated {updated}. Schema {model.schema_version}.", ""]
    return lines


def _honesty_section(model: CostModel) -> list[str]:
    r"""Render the count of quantities by status, with the legend.

    Parameters
    ----------
    model : CostModel
        The model.

    Returns
    -------
    list of str
        Markdown lines.

    Examples
    --------
    >>> "## Honesty" in "\\n".join(_honesty_section(CostModel.from_mapping({})))
    True
    """
    counts = _status_counts(model)
    rows = [
        [f"`{status}`", str(counts[status]), _LEGEND.get(status, "")]
        for status in STATUS_ORDER
        if counts[status]
    ]
    if not rows:
        rows = [["—", "0", "This model states no numbers yet."]]
    return ["## Honesty", "", _table(["Status", "Count", "Meaning"], rows), ""]


def _unit_section(model: CostModel) -> list[str]:
    """Render what one unit of work is.

    Parameters
    ----------
    model : CostModel
        The model.

    Returns
    -------
    list of str
        Markdown lines, empty when the model does not say.

    Examples
    --------
    >>> _unit_section(CostModel.from_mapping({}))
    []
    """
    unit = model.data.get("unit_of_work")
    if not isinstance(unit, dict):
        return []
    lines = ["## One unit of work", "", f"**{_escape(unit.get('name'))}**", ""]
    if unit.get("description"):
        lines += [str(unit["description"]).strip(), ""]
    excluded = unit.get("out_of_scope")
    if isinstance(excluded, list) and excluded:
        lines += ["Not part of a unit:", ""]
        lines += [f"- {_escape(item)}" for item in excluded]
        lines += [""]
    return lines


def _deployment_section(model: CostModel) -> list[str]:
    """Render where the code runs.

    Parameters
    ----------
    model : CostModel
        The model.

    Returns
    -------
    list of str
        Markdown lines, empty when the model does not say.

    Examples
    --------
    >>> _deployment_section(CostModel.from_mapping({}))
    []
    """
    deployment = model.data.get("deployment")
    if not isinstance(deployment, dict) or not deployment:
        return []
    rows = [[_escape(key.replace("_", " ")), _escape(value)] for key, value in deployment.items()]
    return ["## Where it runs", "", _table(["", ""], rows), ""]


def _scenario_section(
    model: CostModel, scenario: dict[str, Any], registry: DimensionRegistry
) -> list[str]:
    """Render one scenario's costs, one row per dimension.

    Parameters
    ----------
    model : CostModel
        The whole model, to resolve derivations against.
    scenario : dict
        The scenario.
    registry : DimensionRegistry
        The dimensions to report, in order.

    Returns
    -------
    list of str
        Markdown lines.

    Examples
    --------
    >>> model = CostModel.from_mapping({})
    >>> lines = _scenario_section(model, {"name": "d", "costs": {}}, DimensionRegistry())
    >>> lines[0]
    '### d'
    """
    lines = [f"### {_escape(scenario.get('name') or 'scenario')}", ""]
    if scenario.get("description"):
        lines += [str(scenario["description"]).strip(), ""]

    costs = scenario.get("costs")
    costs = costs if isinstance(costs, dict) else {}
    rows: list[list[str]] = []
    for dimension in registry:
        raw = costs.get(dimension.key)
        if not looks_like_quantity(raw):
            continue
        quantity = Quantity.from_mapping(raw)
        derived = (
            ", ".join(f"`{path}`" for path in quantity.derived_from)
            if quantity.is_derived()
            else "—"
        )
        rows.append(
            [
                dimension.label,
                format_quantity(quantity),
                f"`{quantity.status}`",
                derived,
                _escape(quantity.notes),
            ]
        )
    lines += [
        _table(["Dimension", "Per unit", "Status", "Derived from", "Notes"], rows)
        or "_This scenario states no costs yet._",
        "",
    ]
    return lines


def _assumptions_section(model: CostModel) -> list[str]:
    """Render the numbers everything else rests on.

    Parameters
    ----------
    model : CostModel
        The model.

    Returns
    -------
    list of str
        Markdown lines, empty when the model assumes nothing.

    Examples
    --------
    >>> _assumptions_section(CostModel.from_mapping({}))
    []
    """
    assumptions = model.data.get("assumptions")
    if not isinstance(assumptions, dict) or not assumptions:
        return []
    rows: list[list[str]] = []
    for key, raw in assumptions.items():
        if not looks_like_quantity(raw):
            continue
        quantity = Quantity.from_mapping(raw)
        rows.append(
            [
                f"`{key}`",
                format_quantity(quantity),
                f"`{quantity.status}`",
                _source_cell(quantity),
                _escape(quantity.notes),
            ]
        )
    if not rows:
        return []
    return [
        "## What the numbers rest on",
        "",
        _table(["Assumption", "Value", "Status", "Provenance", "Notes"], rows),
        "",
    ]


def _services_section(model: CostModel) -> list[str]:
    """Render the paid services the code calls.

    Parameters
    ----------
    model : CostModel
        The model.

    Returns
    -------
    list of str
        Markdown lines, empty when none were detected.

    Examples
    --------
    >>> _services_section(CostModel.from_mapping({}))
    []
    """
    services = model.data.get("external_services")
    if not isinstance(services, list) or not services:
        return []
    rows: list[list[str]] = []
    for entry in services:
        if not isinstance(entry, dict):
            continue
        price = entry.get("price_per_unit") or entry.get("price")
        quantity = Quantity.from_mapping(price) if looks_like_quantity(price) else Quantity()
        pricing = entry.get("pricing_source_url")
        rows.append(
            [
                _escape(entry.get("name") or entry.get("key")),
                f"`{_escape(entry.get('detected_at'))}`" if entry.get("detected_at") else "—",
                f"`{_escape(entry.get('evidence'))}`" if entry.get("evidence") else "—",
                format_quantity(quantity),
                f"[prices]({pricing})" if pricing else "—",
            ]
        )
    return [
        "## Services this code pays for",
        "",
        "Prices are not copied into this model. An API price copied today is wrong "
        "by next quarter, so the report says where the current one lives and leaves "
        "the figure open until somebody reads it.",
        "",
        _table(["Service", "Found at", "Evidence", "Per unit", "Where to price it"], rows),
        "",
    ]


def _models_section(model: CostModel) -> list[str]:
    """Render the models the code calls, and what each is charged at.

    Parameters
    ----------
    model : CostModel
        The model.

    Returns
    -------
    list of str
        Markdown lines, empty when the code names no model.

    Examples
    --------
    >>> _models_section(CostModel.from_mapping({}))
    []
    """
    called = model.data.get("models_called")
    if not isinstance(called, list) or not called:
        return []
    lines = [
        "## Models this code calls",
        "",
        "A rate is not a cost. These are what the vendor charges per unit; how many "
        "of those units one unit of work spends is the open half, and reading the "
        "code cannot establish it.",
        "",
    ]
    for entry in called:
        if not isinstance(entry, dict):
            continue
        name = _escape(entry.get("model"))
        where = entry.get("detected_at")
        heading = f"### `{name}`" + (f" — found at `{_escape(where)}`" if where else "")
        lines += [heading, ""]
        if entry.get("provider"):
            lines += [f"Vendor: {_escape(entry['provider'])}.", ""]
        rates = entry.get("rates")
        rows: list[list[str]] = []
        if isinstance(rates, dict):
            for key, raw in rates.items():
                if not looks_like_quantity(raw):
                    continue
                quantity = Quantity.from_mapping(raw)
                rows.append(
                    [
                        f"`{_escape(key)}`",
                        format_quantity(quantity),
                        f"`{quantity.status}`",
                        f"`{_escape(quantity.source_kind)}`" if quantity.source_kind else "—",
                        _source_cell(quantity),
                    ]
                )
        lines += [
            _table(["Rate", "Value", "Status", "Provenance", "Source"], rows)
            or "_No published rate was found for this model._",
            "",
        ]
        if entry.get("rates_provenance"):
            lines += [str(entry["rates_provenance"]).strip(), ""]
    return lines


def _projections_section(model: CostModel) -> list[str]:
    """Render the projections, each with what it assumed.

    Parameters
    ----------
    model : CostModel
        The model.

    Returns
    -------
    list of str
        Markdown lines, empty when nothing was projected.

    Examples
    --------
    >>> _projections_section(CostModel.from_mapping({}))
    []
    """
    projections = model.data.get("projections")
    if not isinstance(projections, dict) or not projections:
        return []
    lines = [
        "## Projections",
        "",
        "A projection is not a measurement of the thing it projects to.",
        "",
    ]
    for name, block in projections.items():
        if not isinstance(block, dict):
            continue
        lines += [f"### {_escape(name.replace('_', ' '))}", ""]
        if block.get("description"):
            lines += [str(block["description"]).strip(), ""]
        rows: list[list[str]] = []
        for key, value in block.items():
            if key in {"description", "costs"}:
                continue
            rows += _projection_rows(key, value)
        costs = block.get("costs")
        if isinstance(costs, dict):
            for key, value in costs.items():
                rows += _projection_rows(key, value)
        lines += [_table(["", "Value", "Status", "Method"], rows), ""]
        held = block.get("held_constant")
        if held:
            lines += [f"*{_escape(held)}*", ""]
    return lines


def _projection_rows(key: str, value: object) -> list[list[str]]:
    """Render one entry of a projections block, whatever shape it arrived in.

    A projection nests its number under ``result`` and carries a method. A figure
    derived from one, such as what the run would cost on the target accelerator,
    is an ordinary quantity. Both belong in the table, and a renderer that knew
    only the first shape dropped every projected cost on the floor without
    saying so.

    Parameters
    ----------
    key : str
        The entry's name in the block.
    value : object
        A projection mapping, a quantity mapping, or a plain scalar.

    Returns
    -------
    list of list of str
        Table rows, empty when the entry is not something to show.

    Examples
    --------
    >>> _projection_rows("target", "H100")
    [['target', 'H100', '—', '—']]
    >>> _projection_rows("costs", {"nested": {}})
    []
    """
    if isinstance(value, dict) and looks_like_quantity(value.get("result")):
        quantity = Quantity.from_mapping(value["result"])
        rows = [
            [
                _escape(key),
                format_quantity(quantity),
                f"`{quantity.status}`",
                _escape(value.get("method")),
            ]
        ]
        bounds = value.get("bounds")
        if isinstance(bounds, dict):
            fastest, slowest = bounds.get("fastest"), bounds.get("slowest")
            if looks_like_quantity(fastest) and looks_like_quantity(slowest):
                # The bracket is the honest part of the answer. A reader who sees
                # only the point estimate has been told less than is known.
                rows.append(
                    [
                        f"{_escape(key)}, bracketed",
                        f"{format_quantity(Quantity.from_mapping(fastest))} to "
                        f"{format_quantity(Quantity.from_mapping(slowest))}",
                        f"`{Quantity.from_mapping(slowest).status}`",
                        "Fastest and slowest the evidence supports.",
                    ]
                )
        return rows
    if looks_like_quantity(value):
        quantity = Quantity.from_mapping(value)
        return [
            [
                _escape(key),
                format_quantity(quantity),
                f"`{quantity.status}`",
                _escape(quantity.notes),
            ]
        ]
    if not isinstance(value, (dict, list)):
        return [[_escape(key), _escape(value), "—", "—"]]
    return []


def _measurement_section(model: CostModel) -> list[str]:
    """Render how a measurement was taken, and what to distrust about it.

    Parameters
    ----------
    model : CostModel
        The model.

    Returns
    -------
    list of str
        Markdown lines, empty when nothing was run.

    Examples
    --------
    >>> _measurement_section(CostModel.from_mapping({}))
    []
    """
    measurement = model.data.get("measurement")
    if not isinstance(measurement, dict) or not measurement:
        return []
    lines = ["## How it was measured", ""]
    command = measurement.get("command")
    if isinstance(command, list):
        lines += ["```", " ".join(str(part) for part in command), "```", ""]
    rows = [
        [_escape(key.replace("_", " ")), _escape(value)]
        for key, value in measurement.items()
        if key not in {"command", "hot_path", "warnings"} and not isinstance(value, (dict, list))
    ]
    if rows:
        lines += [_table(["", ""], rows), ""]

    hot_path = measurement.get("hot_path")
    if isinstance(hot_path, list) and hot_path:
        lines += [
            "Where the time went:",
            "",
            _table(
                ["Function", "Cumulative seconds", "Calls"],
                [
                    [
                        f"`{_escape(entry.get('function'))}`",
                        _escape(entry.get("cumulative_seconds")),
                        _escape(entry.get("calls")),
                    ]
                    for entry in hot_path
                    if isinstance(entry, dict)
                ],
            ),
            "",
        ]
    warnings = measurement.get("warnings")
    if isinstance(warnings, list) and warnings:
        lines += ["Read these before trusting the numbers above:", ""]
        lines += [f"- {_escape(item)}" for item in warnings]
        lines += [""]
    return lines


def _list_section(title: str, items: object) -> list[str]:
    """Render a titled bullet list, or nothing when there is none.

    Parameters
    ----------
    title : str
        The heading.
    items : object
        Expected to be a list of strings.

    Returns
    -------
    list of str
        Markdown lines.

    Examples
    --------
    >>> _list_section("Excluded", ["hardware"])[0]
    '## Excluded'
    >>> _list_section("Excluded", None)
    []
    """
    if not isinstance(items, list) or not items:
        return []
    return [f"## {title}", "", *[f"- {_escape(item)}" for item in items], ""]


def render_markdown(model: CostModel | dict[str, Any]) -> str:
    """Render a cost model as a Markdown report.

    Parameters
    ----------
    model : CostModel or dict
        The model.

    Returns
    -------
    str
        The report, ending in a newline.

    Examples
    --------
    >>> report = render_markdown({"project": {"name": "demo"}, "scenarios": []})
    >>> report.startswith("# Cost of running demo")
    True
    """
    wrapped = model if isinstance(model, CostModel) else CostModel.from_mapping(model)
    registry = wrapped.registry

    lines = _header(wrapped)
    lines += _honesty_section(wrapped)
    lines += _unit_section(wrapped)
    lines += _deployment_section(wrapped)

    scenarios = wrapped.scenarios()
    if scenarios:
        lines += ["## What one unit costs", ""]
        for scenario in scenarios:
            lines += _scenario_section(wrapped, scenario, registry)

    lines += _assumptions_section(wrapped)
    lines += _services_section(wrapped)
    lines += _models_section(wrapped)
    lines += _measurement_section(wrapped)
    lines += _projections_section(wrapped)
    lines += _list_section("Not counted", wrapped.data.get("exclusions"))
    lines += _list_section("Rules this model follows", wrapped.data.get("provenance_rules"))
    lines += [
        "---",
        "",
        "Generated by [saggio](https://github.com/warith-harchaoui/saggio).",
        "",
    ]
    # Collapse the runs of blank lines that section joining leaves behind, so the
    # rendered file looks hand-written rather than assembled.
    text = "\n".join(lines)
    while "\n\n\n" in text:
        text = text.replace("\n\n\n", "\n\n")
    return text.rstrip("\n") + "\n"
