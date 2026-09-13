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

from ..model.cost_model import CostModel
from ..model.quantity import Quantity, looks_like_quantity
from ..model.taxonomy import STATUS_ORDER

#: Width the figures are drawn at. They scale to the container, so this only sets
#: the aspect ratio and the proportions of the text inside them.
_WIDTH: Final[int] = 720

#: What the honesty bar is described as when the model states no numbers.
_NOTHING_STATED: Final[str] = "This model states no numbers yet."

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
    """Escape text for inclusion in SVG.

    Parameters
    ----------
    text : object
        Anything to place in a text node or attribute.

    Returns
    -------
    str
        The escaped text.

    Examples
    --------
    >>> _escape("a & b")
    'a &amp; b'
    >>> _escape(None)
    ''
    """
    return html.escape(str(text)) if text is not None else ""


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
        '<title id="honesty-title">How well founded this model is</title>',
        f'<desc id="honesty-desc">{_escape(described or _NOTHING_STATED)}</desc>',
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
        '<title id="chain-title">How each number was derived</title>',
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
            f'fill="{fill}">{_escape(status or "no status")}</text></g>'
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
        status = quantities[node].status if node in quantities else "no status"
        sentences.append(f"{node} is {status} and comes from {', '.join(inputs)}.")
    return " ".join(sentences) or "Nothing in this model derives from anything else."


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
