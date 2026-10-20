"""
The two pictures a cost model is worth drawing.

Module summary
--------------
Most of a cost report is a table, and should be: numbers with their units and
their statuses read better in rows than in bars. Two things do not, and those are
the only figures this package draws.

The first is the shape of the model's honesty: how much of it is measured, how
much estimated, how much still open. That is one stacked bar, and it is the single
most useful thing a reader can see in a second.

The second is the derivation chain: which number was computed from which, with
each node coloured by its status. Drawn this way, the weakest-link rule stops
being a paragraph in a specification and becomes visible, because the weakest
colour in the chain is sitting upstream of everything it poisoned.

Both are emitted as inline SVG that references the page's own colour tokens, so a
figure follows the reader's theme without a second copy of the palette.

Usage example
-------------
>>> from saggio.report.figures import honesty_bar
>>> svg = honesty_bar({"measured": 3, "estimated": 5, "placeholder": 0, "TODO": 2})
>>> svg.startswith("<svg")
True

Author
------
Warith Harchaoui
"""

from __future__ import annotations

import html
from typing import Any, Final

from ..catalog.registry import country_name
from ..i18n import number as localised
from ..i18n import say
from ..model.cost_model import CostModel
from ..model.quantity import Quantity, looks_like_quantity
from ..model.taxonomy import STATUS_ORDER
from .markdown import _label

#: Width the figures are drawn at. They scale to the container, so this only sets
#: the aspect ratio and the proportions of the text inside them.
_WIDTH: Final[int] = 720

#: Height of the honesty bar, and of the room left under it for the legend.
_BAR_HEIGHT: Final[int] = 34
_LEGEND_HEIGHT: Final[int] = 54

#: The colour token each status is drawn in. They are the same tokens the badges
#: use, so a figure and a table never disagree about what estimated looks like.
_FILL: Final[dict[str, str]] = {
    "measured": "var(--measured)",
    "estimated": "var(--estimated)",
    "placeholder": "var(--placeholder)",
    "TODO": "var(--todo)",
}


def _escape(text: object) -> str:
    """Escape text for a text node in this module's SVG.

    Quotes are left alone, which is both correct and load-bearing. Correct,
    because nothing escapes a text node except ``<``, and every call site here
    is between a ``>`` and a ``<`` — there is no attribute among them. Load
    bearing, because a label is written twice: once by the server into the page
    and once by the language button into the same node. Escaping an apostrophe
    made the server write ``model&#x27;s`` where the table says ``model's``, so
    the two spellings of one caption differed and a contract test said so. The
    page rendered identically either way, which is exactly why nothing but a
    test would have found it.

    Parameters
    ----------
    text : object
        Anything to place in a text node. Not for attributes.

    Returns
    -------
    str
        The escaped text.

    Examples
    --------
    >>> _escape("a & b")
    'a &amp; b'
    >>> _escape("a <b> c")
    'a &lt;b&gt; c'
    >>> _escape("this model's carbon")
    "this model's carbon"
    >>> _escape(None)
    ''
    """
    return html.escape(str(text), quote=False) if text is not None else ""


def _svg_title(figure: str, key: str) -> str:
    """Return a figure's `<title>`, which the language button can swap.

    The title is the one piece of a figure that is fixed wording rather than
    something the model said, so it carries a ``data-i18n`` attribute and the
    browser rewrites it in place. The words come from the table rather than
    from an argument, so the sentence the server writes and the sentence the
    button writes cannot be two different sentences — the same reason
    :func:`saggio.report.html._heading` stopped taking a title beside a key.

    Parameters
    ----------
    figure : str
        The figure's id prefix, so the `aria-labelledby` above it resolves.
    key : str
        A key in the report's label table — the table the page embeds.

    Returns
    -------
    str
        The title element.

    Examples
    --------
    >>> _svg_title("honesty", "figure.honesty.title")
    '<title id="honesty-title" data-i18n="figure.honesty.title">How well founded this\
 model is</title>'
    """
    return f'<title id="{figure}-title" data-i18n="{key}">{_escape(_label(key))}</title>'


def _caption(key: str) -> str:
    """Return a caption span the language button can swap.

    A `<tspan>` rather than the whole `<text>`, because a caption that also
    states a measured total has to let the button rewrite the words without
    eating the number.

    Parameters
    ----------
    key : str
        A key in the report's label table.

    Returns
    -------
    str
        The span.

    Examples
    --------
    >>> _caption("figure.domains.caption")
    '<tspan data-i18n="figure.domains.caption">Measured, not modelled: each row is\
 its own counter.</tspan>'
    """
    return f'<tspan data-i18n="{key}">{_escape(_label(key))}</tspan>'


def _tooltip(name: object, value: object) -> str:
    """Return a figure's hover text: a name, a separator, a value.

    The separator is a catalogue key rather than a literal ``": "`` because
    French puts a space before a colon and English does not. Composed in Python
    it was invisible to the check that reads the catalogue for exactly this,
    and three figures said `Cœurs processeur: 18,50 W` in French until the two
    languages were printed side by side.

    Parameters
    ----------
    name : object
        What the row is, already in the reader's language where it can be.
    value : object
        What it measured, already formatted.

    Returns
    -------
    str
        Escaped, for a `<title>` text node.

    Examples
    --------
    >>> _tooltip("Memory", "2.30 W")
    'Memory: 2.30 W'
    """
    return _escape(say("figure.tooltip", name=name, value=value))


def _domain_name(key: str) -> str:
    """Return what a subsystem is called, capitalised for a row label.

    The name itself lives once, in the message catalogue, where the measurement
    table already reads it. Only the capital is added here: the table uses the
    name mid-sentence and a figure uses it as a label, which is a presentation
    difference and not a second wording.

    Parameters
    ----------
    key : str
        ``cpu``, ``gpu``, ``ane`` or ``memory``.

    Returns
    -------
    str
        The name, first letter upper-cased. Not `str.capitalize`, which would
        lower-case the rest and has an opinion about acronyms.

    Examples
    --------
    >>> _domain_name("cpu")
    'Processor cores'
    """
    name = say(f"boundary.domain.{key}")
    return name[:1].upper() + name[1:]


def count_statuses(model: CostModel | dict[str, Any]) -> dict[str, int]:
    """Count a model's quantities by honesty status.

    Parameters
    ----------
    model : CostModel or dict
        The model.

    Returns
    -------
    dict
        Status to count, in canonical order, zeros included.

    Examples
    --------
    >>> count_statuses({"a": {"value": 1, "status": "measured"}})["measured"]
    1
    """
    wrapped = model if isinstance(model, CostModel) else CostModel.from_mapping(model)
    counts = dict.fromkeys(STATUS_ORDER, 0)
    for _, raw in wrapped.quantities():
        status = str(raw.get("status", ""))
        if status in counts:
            counts[status] += 1
    return counts


def honesty_bar(counts: dict[str, int]) -> str:
    """Draw how much of a model is measured, estimated, or still open.

    Parameters
    ----------
    counts : dict
        Status to count.

    Returns
    -------
    str
        Inline SVG, with a title and description so a screen reader gets the same
        information the picture carries.

    Examples
    --------
    >>> "measured" in honesty_bar({"measured": 1, "estimated": 0,
    ...                            "placeholder": 0, "TODO": 1})
    True
    >>> honesty_bar({}).count("<rect")
    0
    """
    total = sum(counts.get(status, 0) for status in STATUS_ORDER)
    height = _BAR_HEIGHT + _LEGEND_HEIGHT
    described = ", ".join(
        f"{counts.get(status, 0)} {status}" for status in STATUS_ORDER if counts.get(status, 0)
    )
    parts = [
        f'<svg viewBox="0 0 {_WIDTH} {height}" role="img" '
        f'aria-labelledby="honesty-title honesty-desc" xmlns="http://www.w3.org/2000/svg">',
        _svg_title("honesty", "figure.honesty.title"),
        f'<desc id="honesty-desc">{_escape(described or say("report.no_numbers"))}</desc>',
    ]
    if total == 0:
        parts.append("</svg>")
        return "\n".join(parts)

    offset = 0.0
    legend_x = 0
    for status in STATUS_ORDER:
        count = counts.get(status, 0)
        if not count:
            continue
        width = _WIDTH * count / total
        parts.append(
            f'<rect x="{offset:.1f}" y="0" width="{width:.1f}" height="{_BAR_HEIGHT}" '
            f'fill="{_FILL[status]}" rx="3"><title>{count} {_escape(status)}</title></rect>'
        )
        if width > 46:
            parts.append(
                f'<text x="{offset + width / 2:.1f}" y="{_BAR_HEIGHT / 2 + 5:.0f}" '
                f'text-anchor="middle" font-size="13" font-weight="600" '
                f'fill="var(--page)">{count}</text>'
            )
        offset += width

        label_y = _BAR_HEIGHT + 30
        parts.append(
            f'<rect x="{legend_x}" y="{label_y - 10}" width="11" height="11" rx="2" '
            f'fill="{_FILL[status]}"/>'
        )
        parts.append(
            f'<text x="{legend_x + 17}" y="{label_y}" font-size="13" '
            f'fill="var(--ink-soft)">{_escape(status)} ({count})</text>'
        )
        legend_x += 34 + 8 * len(status) + 26

    parts.append("</svg>")
    return "\n".join(parts)


#: Node box geometry for the derivation figure.
_NODE_WIDTH: Final[int] = 176
_NODE_HEIGHT: Final[int] = 48
_COLUMN_GAP: Final[int] = 54
_ROW_GAP: Final[int] = 16

#: Beyond this many layers the figure stops being readable and the table is the
#: better way to follow the arithmetic, so it declines to draw.
_MAX_LAYERS: Final[int] = 6


def _short_label(path: str) -> str:
    """Return the readable part of a dotted path.

    Parameters
    ----------
    path : str
        A dotted path such as ``scenarios[0].costs.energy``.

    Returns
    -------
    str
        The last segment with its underscores opened out, which is what a reader
        of the figure needs; the full path stays in the box's tooltip.

    Examples
    --------
    >>> _short_label("assumptions.power_draw")
    'power draw'
    >>> _short_label("scenarios[0].costs.energy")
    'energy'
    """
    return path.rsplit(".", 1)[-1].replace("_", " ")


def _label_size(label: str) -> int:
    """Return a font size that keeps a node label inside its box.

    Parameters
    ----------
    label : str
        The label to draw.

    Returns
    -------
    int
        A point size. Long names such as "water usage effectiveness" are set
        smaller rather than allowed to run out of the box and over the arrows.

    Examples
    --------
    >>> _label_size("energy")
    13
    >>> _label_size("water usage effectiveness")
    10
    """
    if len(label) <= 16:
        return 13
    if len(label) <= 21:
        return 11
    return 10


def derivation_edges(model: CostModel | dict[str, Any]) -> dict[str, tuple[str, ...]]:
    """Return the model's derivation graph, as node to its inputs.

    The graph is read from the model rather than assumed. Every quantity that
    names inputs contributes an edge, and every quantity named as an input joins
    the graph even if it derives from nothing itself. A model that tracks a
    dimension this package has never heard of therefore draws correctly, and a
    model whose arithmetic differs from the usual chain draws what it actually
    does rather than what it was expected to do.

    Parameters
    ----------
    model : CostModel or dict
        The model.

    Returns
    -------
    dict
        Node path to the paths it derives from, inputs included with empty tuples.

    Examples
    --------
    >>> derivation_edges({"e": {"value": 1, "status": "measured",
    ...                         "derived_from": ["r"]},
    ...                   "r": {"value": 1, "status": "measured"}})
    {'e': ('r',), 'r': ()}
    """
    wrapped = model if isinstance(model, CostModel) else CostModel.from_mapping(model)
    quantities = dict(wrapped.typed_quantities())
    edges: dict[str, tuple[str, ...]] = {}
    for path, quantity in quantities.items():
        if not quantity.is_derived():
            continue
        inputs = tuple(item for item in quantity.derived_from if item in quantities)
        edges[path] = inputs
        for item in inputs:
            edges.setdefault(item, ())
    return edges


def _layers(edges: dict[str, tuple[str, ...]]) -> list[list[str]]:
    """Arrange a derivation graph into columns, inputs leftmost.

    Parameters
    ----------
    edges : dict
        Node to its inputs.

    Returns
    -------
    list of list of str
        Nodes grouped into columns, each derived value one column right of its
        inputs. A cycle, which the validator would have reported as an error, is
        broken by capping the depth rather than looping forever.

    Examples
    --------
    >>> _layers({"e": ("r",), "r": (), "c": ("e",)})
    [['r'], ['e'], ['c']]
    """
    depth: dict[str, int] = {}

    def depth_of(node: str, seen: frozenset[str]) -> int:
        if node in depth:
            return depth[node]
        inputs = edges.get(node, ())
        if not inputs or node in seen:
            depth[node] = 0
            return 0
        computed = 1 + max(depth_of(item, seen | {node}) for item in inputs)
        depth[node] = min(computed, _MAX_LAYERS - 1)
        return depth[node]

    for node in edges:
        depth_of(node, frozenset())

    # An input sits one column left of whichever consumer needs it first. Placing
    # every input in column zero instead would be correct and unreadable: the
    # electricity price would stretch a line across the whole figure to reach the
    # money box three columns away.
    consumers: dict[str, list[str]] = {}
    for node, inputs in edges.items():
        for item in inputs:
            consumers.setdefault(item, []).append(node)
    for node, using in consumers.items():
        if edges.get(node):
            continue
        depth[node] = max(0, min(depth[item] for item in using) - 1)

    grouped: dict[int, list[str]] = {}
    for node, level in depth.items():
        grouped.setdefault(level, []).append(node)
    # Columns are renumbered so pulling inputs rightwards cannot leave a gap.
    return [sorted(grouped[level]) for level in sorted(grouped)]


def derivation_chain(model: CostModel | dict[str, Any]) -> str:
    """Draw the model's own derivation graph, each node coloured by its status.

    Parameters
    ----------
    model : CostModel or dict
        The model.

    Returns
    -------
    str
        Inline SVG, or an empty string when no quantity in the model names an
        input, in which case there is no graph and the table says everything.

    Examples
    --------
    >>> derivation_chain({"a": {"value": 1, "status": "measured"}})
    ''
    >>> derivation_chain({"e": {"value": 1, "status": "measured",
    ...                         "derived_from": ["r"]},
    ...                   "r": {"value": 1, "status": "measured"}}).startswith("<svg")
    True
    """
    wrapped = model if isinstance(model, CostModel) else CostModel.from_mapping(model)
    edges = derivation_edges(wrapped)
    if not any(inputs for inputs in edges.values()):
        return ""

    columns = _layers(edges)
    quantities = dict(wrapped.typed_quantities())
    rows = max(len(column) for column in columns)
    height = rows * _NODE_HEIGHT + (rows - 1) * _ROW_GAP + 8
    width = len(columns) * _NODE_WIDTH + (len(columns) - 1) * _COLUMN_GAP

    placed: dict[str, tuple[float, float]] = {}
    for column_index, column in enumerate(columns):
        x = column_index * (_NODE_WIDTH + _COLUMN_GAP)
        block = len(column) * _NODE_HEIGHT + (len(column) - 1) * _ROW_GAP
        top = (height - block) / 2
        for row_index, node in enumerate(column):
            placed[node] = (x, top + row_index * (_NODE_HEIGHT + _ROW_GAP))

    parts = [
        f'<svg viewBox="0 0 {width} {height}" role="img" '
        'aria-labelledby="chain-title chain-desc" xmlns="http://www.w3.org/2000/svg">',
        _svg_title("chain", "figure.chain.title"),
        f'<desc id="chain-desc">{_escape(_describe(edges, quantities))}</desc>',
        '<defs><marker id="arrow" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="6" '
        'markerHeight="6" orient="auto"><path d="M0,0 L8,4 L0,8 z" fill="var(--line-strong)"/>'
        "</marker></defs>",
    ]

    # Arrows first so the boxes sit over them rather than under.
    for node, inputs in edges.items():
        if node not in placed:
            continue
        end_x, end_y = placed[node]
        for item in inputs:
            if item not in placed:
                continue
            start_x, start_y = placed[item]
            if start_x >= end_x:
                continue
            parts.append(
                f'<line x1="{start_x + _NODE_WIDTH}" y1="{start_y + _NODE_HEIGHT / 2:.1f}" '
                f'x2="{end_x - 5}" y2="{end_y + _NODE_HEIGHT / 2:.1f}" '
                'stroke="var(--line-strong)" stroke-width="1.2" marker-end="url(#arrow)"/>'
            )

    for node, (x, y) in placed.items():
        label = _short_label(node)
        status = quantities[node].status if node in quantities else None
        fill = _FILL.get(status or "", "var(--line-strong)")
        parts.append(
            f"<g><title>{_escape(node)}</title>"
            f'<rect x="{x}" y="{y:.1f}" width="{_NODE_WIDTH}" height="{_NODE_HEIGHT}" rx="7" '
            f'fill="var(--surface)" stroke="{fill}" stroke-width="2"/>'
            f'<text x="{x + 12}" y="{y + 21:.1f}" font-size="{_label_size(label)}" '
            f'font-weight="600" fill="var(--ink)">{_escape(label)}</text>'
            f'<text x="{x + 12}" y="{y + 37:.1f}" font-size="11" '
            f'fill="{fill}">{_escape(status or say("figure.chain.no_status"))}</text></g>'
        )

    parts.append("</svg>")
    return "\n".join(parts)


def _describe(edges: dict[str, tuple[str, ...]], quantities: dict[str, Quantity]) -> str:
    """Describe a derivation graph in words, for a reader who cannot see it.

    Parameters
    ----------
    edges : dict
        Node to its inputs.
    quantities : dict
        Path to parsed quantity, for the statuses.

    Returns
    -------
    str
        A sentence per derived node.

    Examples
    --------
    >>> _describe({"e": ("r",)}, {"e": Quantity(status="measured")})
    'e is measured and comes from r.'
    """
    sentences = []
    for node, inputs in edges.items():
        if not inputs:
            continue
        status = quantities[node].status if node in quantities else say("figure.chain.no_status")
        sentences.append(
            say("figure.chain.derived", node=node, status=status, inputs=", ".join(inputs))
        )
    return " ".join(sentences) or say("figure.chain.nothing_derived")


def scenario_energy(model: CostModel | dict[str, Any]) -> Quantity:
    """Return the machine energy the what-if panel rescales.

    Parameters
    ----------
    model : CostModel or dict
        The model.

    Returns
    -------
    Quantity
        The machine's own energy per unit of work, or an empty quantity when the
        model does not state one. The panel refuses to show anything rather than
        invent a figure to rescale.

    Examples
    --------
    >>> scenario_energy({"assumptions": {"machine_energy": {"value": 2.0,
    ...                                                     "status": "measured"}}}).value
    2.0
    >>> scenario_energy({}).is_known()
    False
    """
    wrapped = model if isinstance(model, CostModel) else CostModel.from_mapping(model)
    node = wrapped.get("assumptions.machine_energy")
    if looks_like_quantity(node):
        return Quantity.from_mapping(node)
    return Quantity()


# --- The location panel --------------------------------------------------------

#: Vertical rhythm of the location chart: one bar row and the caption under it.
_ROW_HEIGHT: Final[int] = 30
_CAPTION_HEIGHT: Final[int] = 34

#: Horizontal layout: the country names sit right-aligned in the label column,
#: the bars start after it, and the gutter keeps room for the value labels.
_LABEL_WIDTH: Final[int] = 190
_VALUE_GUTTER: Final[int] = 96

#: How many countries the panel shows. Enough to span the range from a mostly
#: hydro grid to a mostly coal one without turning into a wall of bars.
_PANEL_SIZE: Final[int] = 9


def _row_label(name: str) -> tuple[str, int]:
    """Return the display form and font size that keep a row label in its column.

    The label column is 190 units wide and the text is right-anchored, so an
    untrimmed long name would extend leftwards past the viewBox and be clipped
    invisible — while the ``<desc>`` still carried it, telling screen readers
    more than sighted readers. The full name stays in the row's tooltip.

    Parameters
    ----------
    name : str
        The row's full name.

    Returns
    -------
    tuple of (str, int)
        What to draw, and at what font size.

    Examples
    --------
    >>> _row_label("France")
    ('France', 13)
    >>> _row_label("The Grand Duchy of Overlong Naming")
    ('The Grand Duchy of Overlo…', 11)
    """
    display = name if len(name) <= 26 else name[:25] + "…"
    return display, 13 if len(display) <= 20 else 11


def location_impact(countries: dict[str, dict[str, Any]], current: str | None = None) -> str:
    """Draw how the grid's carbon intensity moves with the country.

    The Green Algorithms calculator's flagship panel, redrawn in this report's
    own idiom: one bar per country, the model's own country picked out in the
    accent colour. The bars show the catalogue's grid carbon intensity rather
    than this model's multiplied figure, because the multiplication is linear
    and the intensities are the sourced fact; the caption says as much.

    The panel is a sample, not the catalogue: the countries are picked evenly
    across the sorted range so the cleanest and dirtiest grids always appear,
    and the model's own country replaces its nearest neighbour when it was not
    already in the sample.

    Parameters
    ----------
    countries : dict
        The grid catalogue's ``countries`` table: key to row, each row carrying
        ``name`` and ``carbon_gco2e_per_kwh``.
    current : str or None, optional
        ISO code of the country the model runs in, when it is resolved.

    Returns
    -------
    str
        Inline SVG, or an empty string when fewer than two countries carry a
        number, because a comparison needs something to compare.

    Examples
    --------
    >>> rows = {"SE": {"name": "Sweden", "carbon_gco2e_per_kwh": 30},
    ...         "AU": {"name": "Australia", "carbon_gco2e_per_kwh": 580}}
    >>> svg = location_impact(rows, current="SE")
    >>> svg.count("<rect")
    2
    >>> "Sweden" in svg and "Australia" in svg
    True
    >>> location_impact({}) == ""
    True
    """
    usable: list[tuple[str, str, float]] = []
    for key, row in countries.items():
        if not isinstance(row, dict):
            continue
        try:
            value = float(row["carbon_gco2e_per_kwh"])
        except (KeyError, TypeError, ValueError):
            # One malformed overlay row ("n/a", a list, a typo) must not take
            # the whole report page down with it; the row simply is not drawn.
            continue
        usable.append((str(key), country_name(str(key), row), value))
    usable.sort(key=lambda entry: entry[2])
    if len(usable) < 2 or max(entry[2] for entry in usable) <= 0.0:
        # Nothing to compare, or nothing to scale the bars by.
        return ""

    if len(usable) > _PANEL_SIZE:
        span = len(usable) - 1
        picked = [usable[round(index * span / (_PANEL_SIZE - 1))] for index in range(_PANEL_SIZE)]
        keys = {entry[0] for entry in picked}
        own = next((entry for entry in usable if entry[0] == current), None)
        if own is not None and own[0] not in keys:
            # The reader's own grid must be on the chart to anchor it, so it
            # takes the sampled slot whose intensity sits closest to its own —
            # but never the first or last slot: the cleanest and dirtiest grids
            # are what give the scale its meaning.
            nearest = min(
                range(1, len(picked) - 1), key=lambda index: abs(picked[index][2] - own[2])
            )
            picked[nearest] = own
            picked.sort(key=lambda entry: entry[2])
    else:
        picked = usable

    top = max(entry[2] for entry in picked)
    bar_area = _WIDTH - _LABEL_WIDTH - _VALUE_GUTTER
    height = len(picked) * _ROW_HEIGHT + _CAPTION_HEIGHT
    listed = ", ".join(f"{name} {localised(f'{value:g}')}" for _, name, value in picked)
    parts = [
        f'<svg viewBox="0 0 {_WIDTH} {height}" role="img" '
        f'aria-labelledby="location-title location-desc" xmlns="http://www.w3.org/2000/svg">',
        _svg_title("location", "figure.location.title"),
        '<desc id="location-desc">'
        + _escape(say("figure.location.description", listed=listed))
        + "</desc>",
    ]
    for index, (key, name, value) in enumerate(picked):
        y = index * _ROW_HEIGHT
        is_current = key == current
        fill = "var(--accent)" if is_current else "var(--line-strong)"
        weight = ' font-weight="600"' if is_current else ""
        bar = max(bar_area * value / top, 2.0)
        display, size = _row_label(name)
        parts.append(
            f'<text x="{_LABEL_WIDTH - 12}" y="{y + _ROW_HEIGHT / 2 + 4:.0f}" '
            f'text-anchor="end" font-size="{size}" fill="var(--ink-soft)"{weight}>'
            f"{_escape(display)}</text>"
        )
        shown = localised(f"{value:g}")
        parts.append(
            f'<rect x="{_LABEL_WIDTH}" y="{y + 7}" width="{bar:.1f}" height="16" rx="3" '
            f'fill="{fill}"><title>{_tooltip(name, f"{shown} gCO2e/kWh")}</title></rect>'
        )
        parts.append(
            f'<text x="{_LABEL_WIDTH + bar + 8:.1f}" y="{y + _ROW_HEIGHT / 2 + 4:.0f}" '
            f'font-size="13" fill="var(--ink-faint)">{shown}</text>'
        )
    parts.append(
        f'<text x="{_LABEL_WIDTH}" y="{height - 10}" font-size="12" '
        'fill="var(--ink-faint)">' + _caption("figure.location.caption") + "</text>"
    )
    parts.append("</svg>")
    return "\n".join(parts)


# --- The dashboard's honesty overview -------------------------------------------

#: Room under the overview's rows for its one shared legend.
_OVERVIEW_LEGEND_HEIGHT: Final[int] = 40


def honesty_overview(entries: list[tuple[str, dict[str, int]]]) -> str:
    """Draw how well founded several models are, side by side.

    The one comparison a multi-project dashboard can make honestly. Costs per
    unit do not compare across projects, because each project defines its own
    unit of work; the *share* of each model that is measured, estimated, or
    still open compares exactly, so that is what gets drawn: one full-width
    stacked bar per project, all on the same scale of one hundred percent.

    Parameters
    ----------
    entries : list of (str, dict)
        Project name and its status counts, as from :func:`count_statuses`.

    Returns
    -------
    str
        Inline SVG, or an empty string when no entry counts anything, because
        an overview of nothing is not a figure.

    Examples
    --------
    >>> svg = honesty_overview([("a", {"measured": 2, "estimated": 2}),
    ...                         ("b", {"TODO": 1})])
    >>> svg.count("<rect") >= 3
    True
    >>> honesty_overview([]) == ""
    True
    >>> honesty_overview([("empty", {})]) == ""
    True
    """
    counted = [
        (name, counts, sum(counts.get(status, 0) for status in STATUS_ORDER))
        for name, counts in entries
    ]
    counted = [(name, counts, total) for name, counts, total in counted if total]
    if not counted:
        return ""

    bar_area = _WIDTH - _LABEL_WIDTH - 12
    height = len(counted) * _ROW_HEIGHT + _OVERVIEW_LEGEND_HEIGHT
    # Unescaped on purpose: the whole description is escaped once, below. The
    # separator comes from the catalogue for the same reason the tooltips' does
    # — it was a literal ": " and read `demo: 4 measured` in French.
    described = "; ".join(
        say(
            "figure.tooltip",
            name=name,
            value=", ".join(
                f"{localised(str(counts.get(status, 0)))} {status}"
                for status in STATUS_ORDER
                if counts.get(status)
            ),
        )
        for name, counts, _ in counted
    )
    parts = [
        f'<svg viewBox="0 0 {_WIDTH} {height}" role="img" '
        f'aria-labelledby="overview-title overview-desc" xmlns="http://www.w3.org/2000/svg">',
        _svg_title("overview", "dashboard.honesty"),
        f'<desc id="overview-desc">{_escape(described)}</desc>',
    ]
    for index, (name, counts, total) in enumerate(counted):
        y = index * _ROW_HEIGHT
        display, size = _row_label(name)
        parts.append(
            f'<text x="{_LABEL_WIDTH - 12}" y="{y + _ROW_HEIGHT / 2 + 4:.0f}" '
            f'text-anchor="end" font-size="{size}" fill="var(--ink-soft)">{_escape(display)}</text>'
        )
        offset = float(_LABEL_WIDTH)
        for status in STATUS_ORDER:
            count = counts.get(status, 0)
            if not count:
                continue
            width = bar_area * count / total
            parts.append(
                f'<rect x="{offset:.1f}" y="{y + 7}" width="{width:.1f}" height="16" rx="3" '
                f'fill="{_FILL[status]}"><title>'
                + _tooltip(name, f"{localised(str(count))} {status}")
                + "</title></rect>"
            )
            offset += width

    legend_x = _LABEL_WIDTH
    legend_y = len(counted) * _ROW_HEIGHT + 24
    for status in STATUS_ORDER:
        parts.append(
            f'<rect x="{legend_x}" y="{legend_y - 10}" width="11" height="11" rx="2" '
            f'fill="{_FILL[status]}"/>'
        )
        parts.append(
            f'<text x="{legend_x + 17}" y="{legend_y}" font-size="13" '
            f'fill="var(--ink-soft)">{_escape(status)}</text>'
        )
        legend_x += 34 + 8 * len(status) + 16
    parts.append("</svg>")
    return "\n".join(parts)


#: The order the subsystems read best in: the processor first because it is
#: usually the largest, memory last because it is the one a reader is least
#: expecting to see. The *names* are not here — they are `boundary.domain.*` in
#: the message catalogue, which the measurement table already reads. This held a
#: second copy of all four, differing only in capitalisation, which is how a
#: duplicate survives: both copies were English and both were right.
_DOMAIN_ORDER: Final[tuple[str, ...]] = ("cpu", "gpu", "ane", "memory")

#: Height of one subsystem row, and of the whole figure's margins.
_DOMAIN_ROW: Final[int] = 30
_DOMAIN_LABEL_WIDTH: Final[int] = 150


def power_by_domain(watts: dict[str, float]) -> str:
    """Draw where the measured power actually went, by subsystem.

    The one figure in this package drawn entirely from counters. Every other
    chart here shows statuses or derivations; this shows watts, each one read
    off a channel the chip publishes separately, so the split is measured rather
    than modelled. A donut of estimated shares would have been easier to draw
    and would have been a picture of an assumption.

    Parameters
    ----------
    watts : dict
        Average watts per subsystem, keyed ``cpu``, ``gpu``, ``ane``,
        ``memory``, as :class:`saggio.analyze.power.PowerReading` carries them.

    Returns
    -------
    str
        Inline SVG, or an empty string when nothing was measured apart — a chip
        that publishes one number for the lot has no split to show, and drawing
        one anyway would invent it.

    Examples
    --------
    >>> svg = power_by_domain({"cpu": 18.5, "gpu": 0.1, "memory": 2.3})
    >>> svg.count("<rect") >= 3
    True
    >>> power_by_domain({}) == ""
    True
    >>> power_by_domain({"cpu": 0.0, "gpu": 0.0}) == ""
    True
    """
    rows = [
        (key, float(value))
        for key, value in watts.items()
        if key in _DOMAIN_ORDER and isinstance(value, (int, float)) and value >= 0.0
    ]
    largest = max((value for _, value in rows), default=0.0)
    if not rows or largest <= 0.0:
        return ""
    rows.sort(key=lambda row: _DOMAIN_ORDER.index(row[0]))

    bar_area = _WIDTH - _DOMAIN_LABEL_WIDTH - 80
    height = _DOMAIN_ROW * len(rows) + 30
    total = sum(value for _, value in rows)
    parts = [
        f'<svg viewBox="0 0 {_WIDTH} {height}" role="img" '
        'aria-labelledby="domains-title domains-desc" xmlns="http://www.w3.org/2000/svg">',
        _svg_title("domains", "figure.domains.title"),
        '<desc id="domains-desc">'
        + _escape(
            say(
                "figure.domains.description",
                listed=", ".join(
                    f"{_domain_name(key)} {localised(f'{value:.2f}')} W" for key, value in rows
                ),
                total=localised(f"{total:.2f}"),
            )
        )
        + "</desc>",
    ]
    for index, (key, value) in enumerate(rows):
        y = 8 + index * _DOMAIN_ROW
        width = max(1.0, bar_area * value / largest)
        name = _domain_name(key)
        watts_shown = f"{localised(f'{value:.2f}')} W"
        parts.append(
            f'<text x="{_DOMAIN_LABEL_WIDTH - 10}" y="{y + 15}" text-anchor="end" '
            f'font-size="13" fill="var(--ink-soft)">{_escape(name)}</text>'
        )
        parts.append(
            f'<rect x="{_DOMAIN_LABEL_WIDTH}" y="{y}" width="{width:.1f}" height="18" rx="3" '
            f'fill="var(--measured)"><title>{_tooltip(name, watts_shown)}</title></rect>'
        )
        parts.append(
            f'<text x="{_DOMAIN_LABEL_WIDTH + width + 8:.1f}" y="{y + 14}" font-size="13" '
            f'fill="var(--ink-soft)">{watts_shown}</text>'
        )
    # Two spans rather than one sentence: the first half is fixed wording the
    # language button can swap, the second half is a measured total it cannot.
    # Written as one string, the button would have had to leave the whole
    # caption in English to avoid eating the number.
    parts.append(
        f'<text x="{_DOMAIN_LABEL_WIDTH}" y="{height - 6}" font-size="12" '
        'fill="var(--ink-soft)">'
        + _caption("figure.domains.caption")
        + " "
        + _escape(say("figure.domains.total", total=localised(f"{total:.2f}")))
        + "</text>"
    )
    parts.append("</svg>")
    return "".join(parts)
