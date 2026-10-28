"""Draw the three figures the README and the LISEZMOI explain the tool with.

Module summary
--------------
The two front pages are long, and the three things a newcomer has to hold in
their head at once are the three hardest to carry in prose: where a figure comes
from, why a derived figure may not outrank the numbers it was computed from, and
why the same engine answers through five different surfaces. Each gets one
drawing here, in English and in French, from one source.

Both languages come out of this file for the reason the gallery's figure does:
two hand-edited SVGs drift the first time a row changes, and a figure that
disagrees with its translation leaves nobody able to tell which one is right.

Two things are read rather than restated, because a figure that contradicts the
package is worse than no figure. The palette comes from ``reporting/report.css``,
so the colour this draws ``estimated`` in is the colour the reader will meet
again in their own report. The numbers in the second figure come from the model
``saggio init --template annotated`` writes, so the chain cannot quietly stop
matching the template it claims to be drawing.

Usage example
-------------
>>> svg = draw("weakest-link", "fr")
>>> svg.startswith("<svg")
True
>>> "0,1" in svg               # the figures write numbers the language's way
True

Author
------
Warith Harchaoui
"""

from __future__ import annotations

import pathlib
import re
from typing import Final

import yaml

from saggio.i18n import language, number

#: Repository root, from this file rather than from the working directory, so
#: the generator can be run from anywhere.
ROOT: Final[pathlib.Path] = pathlib.Path(__file__).resolve().parents[1]

#: The report's stylesheet, which owns the palette, and the template whose
#: numbers the derivation figure draws. Both are read, never copied.
STYLESHEET: Final[pathlib.Path] = ROOT / "reporting" / "report.css"
TEMPLATE: Final[pathlib.Path] = ROOT / "saggio" / "data" / "templates" / "annotated.yaml"

#: Canvas width shared by the three figures: wide enough for three columns of
#: prose at a readable size, and the width the gallery's figure already uses, so
#: two figures on the same page scale to the same thing.
WIDTH: Final[int] = 1180

#: Breathing room at the four edges.
MARGIN: Final[int] = 44

#: The report's own font stacks, so a figure sitting above a report looks like
#: the same document rather than a neighbour.
SANS: Final[str] = (
    "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif"
)
MONO: Final[str] = "ui-monospace, 'SF Mono', 'JetBrains Mono', Menlo, Consolas, monospace"

#: Advance width of a glyph as a fraction of the font size. Measured off Inter
#: and rounded up: the wrapper that uses this must never under-estimate, because
#: a line it thinks fits and does not is a line of text running off a card.
_NARROW: Final[str] = "iljItf.,;:!|'()[]/ "
_WIDE: Final[str] = "mwMW@—"
_ADVANCE_NARROW: Final[float] = 0.31
_ADVANCE_WIDE: Final[float] = 0.90
_ADVANCE_UPPER: Final[float] = 0.68
_ADVANCE_DIGIT: Final[float] = 0.57
_ADVANCE_OTHER: Final[float] = 0.54

#: Monospace advances do not vary by glyph; this is the ratio for the stacks
#: above, taken from the widest of them.
_ADVANCE_MONO: Final[float] = 0.61

#: Every pixel width this file computes is multiplied by this, so that a font
#: slightly wider than Inter -- which is what a reader without Inter installed
#: will get -- still leaves the text inside its card.
_SAFETY: Final[float] = 1.03

#: Line heights, as a multiple of the font size.
_LEADING: Final[float] = 1.42


def _escape(text: str) -> str:
    """Return text safe to drop between SVG tags.

    Examples
    --------
    >>> _escape("a & b < c")
    'a &amp; b &lt; c'
    """
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _advance(character: str, size: float, *, mono: bool = False) -> float:
    """Return the width one glyph takes, in pixels.

    Parameters
    ----------
    character : str
        A single character.
    size : float
        Font size in pixels.
    mono : bool, optional
        Whether the glyph is set in the monospace stack.

    Returns
    -------
    float
        Its advance width.

    Examples
    --------
    >>> _advance("i", 10) < _advance("m", 10)
    True
    >>> _advance("i", 10, mono=True) == _advance("m", 10, mono=True)
    True
    """
    if mono:
        return size * _ADVANCE_MONO
    if character in _NARROW:
        return size * _ADVANCE_NARROW
    if character in _WIDE:
        return size * _ADVANCE_WIDE
    if character.isdigit():
        return size * _ADVANCE_DIGIT
    if character.isupper():
        return size * _ADVANCE_UPPER
    return size * _ADVANCE_OTHER


def measure(text: str, size: float, *, mono: bool = False) -> float:
    """Return how wide a string will be set, in pixels.

    Examples
    --------
    >>> measure("", 14)
    0.0
    >>> measure("mmmm", 14) > measure("iiii", 14)
    True
    """
    return sum(_advance(character, size, mono=mono) for character in text) * _SAFETY


def wrap(text: str, width: float, size: float, *, mono: bool = False) -> list[str]:
    """Break a string into lines that fit a given width.

    Words longer than the width are left alone rather than hyphenated: in this
    repository those are command names and file paths, and a broken one is worse
    than a line that runs a little wide.

    Parameters
    ----------
    text : str
        The string to break.
    width : float
        The width to fit, in pixels.
    size : float
        Font size in pixels.
    mono : bool, optional
        Whether the text is set in the monospace stack.

    Returns
    -------
    list of str
        One entry per line.

    Examples
    --------
    >>> wrap("one two three", 1000, 14)
    ['one two three']
    >>> len(wrap("one two three four five six seven", 60, 14)) > 1
    True
    >>> wrap("", 100, 14)
    ['']
    """
    words = text.split()
    if not words:
        return [""]
    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        candidate = f"{current} {word}"
        if measure(candidate, size, mono=mono) <= width:
            current = candidate
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def tokens() -> dict[str, dict[str, str]]:
    """Return the report's palette, light and dark.

    Reading the stylesheet rather than copying the hexadecimals is the whole
    point: a figure and the report it introduces may not disagree about what
    ``estimated`` looks like, and the only way to guarantee that is for one of
    them to ask the other.

    Returns
    -------
    dict
        ``{"light": {...}, "dark": {...}}``, token name without the leading
        dashes to hexadecimal.

    Examples
    --------
    >>> palette = tokens()
    >>> palette["light"]["measured"] != palette["dark"]["measured"]
    True
    >>> palette["light"]["ink"].startswith("#")
    True
    """
    css = STYLESHEET.read_text(encoding="utf-8")
    out: dict[str, dict[str, str]] = {}
    for key, opener in (("light", ":root {"), ("dark", ':root[data-theme="dark"] {')):
        start = css.index(opener) + len(opener)
        block = css[start : css.index("}", start)]
        out[key] = dict(re.findall(r"--([a-z0-9-]+):\s*(#[0-9a-fA-F]{3,8})\s*;", block))
    return out


#: The four statuses, in the order the taxonomy ranks them, with the token each
#: one is drawn in.
STATUSES: Final[tuple[str, ...]] = ("measured", "estimated", "placeholder", "TODO")


def _token(status: str) -> str:
    """Return the stylesheet token name for a status.

    Examples
    --------
    >>> _token("TODO")
    'todo'
    """
    return status.lower()


def style() -> str:
    """Return the ``<style>`` block every figure carries.

    One block, built from the report's tokens, with only the tokens that differ
    redefined for dark. A figure sitting in a README is read in whichever theme
    the reader set, and an SVG loaded as an image still honours the media query.

    Returns
    -------
    str
        The style element.

    Examples
    --------
    >>> "prefers-color-scheme" in style()
    True
    """
    palette = tokens()

    def rules(scheme: str) -> str:
        colour = palette[scheme]
        parts = [
            f".paper{{fill:{colour['page']}}}",
            f".surface{{fill:{colour['surface']}}}",
            f".sunken{{fill:{colour['surface-sunken']}}}",
            f".ink{{fill:{colour['ink']}}}",
            f".soft{{fill:{colour['ink-soft']}}}",
            f".faint{{fill:{colour['ink-faint']}}}",
            f".edge{{stroke:{colour['line']}}}",
            f".strong{{stroke:{colour['line-strong']}}}",
            f".strong-fill{{fill:{colour['line-strong']}}}",
            f".accent{{fill:{colour['accent']}}}",
            f".accent-soft{{fill:{colour['accent-soft']}}}",
        ]
        for status in STATUSES:
            name = _token(status)
            parts.append(f".{name}{{fill:{colour[name]}}}")
            parts.append(f".{name}-bg{{fill:{colour[f'{name}-soft']}}}")
            parts.append(f".{name}-edge{{stroke:{colour[name]}}}")
        return "".join(parts)

    return (
        "<style>"
        f"{rules('light')}"
        ".card{stroke-width:1}"
        ".t{font-size:26px;font-weight:700;letter-spacing:-.01em}"
        ".s{font-size:15px}"
        ".k{font-size:11.5px;font-weight:700;letter-spacing:.09em}"
        ".h{font-size:15.5px;font-weight:650}"
        ".b{font-size:13px}"
        ".n{font-size:12.5px}"
        ".c{font-size:12.5px}"
        ".v{font-size:17px;font-weight:650}"
        "@media (prefers-color-scheme: dark){"
        f"{rules('dark')}"
        "}"
        "</style>"
    )


def head(figure: str, title: str, description: str, height: int) -> list[str]:
    """Return the opening of a figure: the element, its labels, its background.

    Parameters
    ----------
    figure : str
        Short name, used to make the label identifiers unique.
    title : str
        The figure's title, which is also its accessible name.
    description : str
        A sentence saying what the figure shows, for a reader who cannot see it.
    height : int
        Canvas height.

    Returns
    -------
    list of str
        The lines to start the document with.

    Examples
    --------
    >>> head("x", "T", "D", 100)[0].startswith("<svg")
    True
    """
    identifier = re.sub(r"[^a-z]+", "-", figure.lower())
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{height}" '
        f'viewBox="0 0 {WIDTH} {height}" role="img" '
        f'aria-labelledby="{identifier}-title {identifier}-desc" font-family="{SANS}">',
        f'<title id="{identifier}-title">{_escape(title)}</title>',
        f'<desc id="{identifier}-desc">{_escape(description)}</desc>',
        style(),
        f'<rect class="paper" width="{WIDTH}" height="{height}"/>',
        "<defs>"
        + "".join(
            f'<marker id="arrow-{name}" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="5.5" '
            f'markerHeight="5.5" orient="auto"><path d="M0,0 L8,4 L0,8 z" class="{fill}"/></marker>'
            for name, fill in [("line", "strong-fill")]
            + [(_token(status), _token(status)) for status in STATUSES]
        )
        + "</defs>",
    ]


def text(
    x: float,
    y: float,
    classes: str,
    content: str,
    *,
    mono: bool = False,
    anchor: str | None = None,
    preserve: bool = False,
) -> str:
    """Return one line of text.

    Parameters
    ----------
    x, y : float
        Anchor point. ``y`` is the baseline, as SVG counts it.
    classes : str
        Space-separated class names, which carry the size and the colour.
    content : str
        The line, escaped here rather than by the caller.
    mono : bool, optional
        Set it in the monospace stack.
    anchor : str, optional
        ``"middle"`` or ``"end"`` to change the alignment.
    preserve : bool, optional
        Keep leading and repeated spaces. SVG collapses them like HTML does,
        which silently unindents a YAML block and turns a nested key into a
        top-level one -- a figure claiming a file shape the file does not have.

    Returns
    -------
    str
        A ``<text>`` element.

    Examples
    --------
    >>> text(0, 0, "ink b", "x & y")
    '<text class="ink b" x="0" y="0">x &amp; y</text>'
    >>> 'xml:space="preserve"' in text(0, 0, "c", "  indented", preserve=True)
    True
    """
    attributes = f'class="{classes}" x="{x:g}" y="{y:g}"'
    if mono:
        attributes += f' font-family="{MONO}"'
    if anchor:
        attributes += f' text-anchor="{anchor}"'
    if preserve:
        attributes += ' xml:space="preserve"'
    return f"<text {attributes}>{_escape(content)}</text>"


def chip(x: float, y: float, label: str, status: str | None) -> tuple[str, float]:
    """Return a status pill, and how wide it came out.

    A pill rather than a word so that the status reads as a label on the box
    rather than as part of the sentence, which is how the report badges it too.

    Parameters
    ----------
    x, y : float
        Top-left corner.
    label : str
        The text inside, usually the status itself.
    status : str or None
        Which palette entry to colour it with. ``None`` draws it in the faint
        ink, for a pill that is not a status.

    Returns
    -------
    tuple
        The elements, and the pill's width.

    Examples
    --------
    >>> _, width = chip(0, 0, "measured", "measured")
    >>> width > 0
    True
    """
    size = 11.5
    inner = 9.0
    width = measure(label, size, mono=True) + 2 * inner
    background = f"{_token(status)}-bg" if status else "sunken"
    ink = _token(status) if status else "faint"
    parts = (
        f'<rect class="{background}" x="{x:g}" y="{y:g}" width="{width:.1f}" height="20" rx="6"/>'
        + text(x + inner, y + 14.2, f"{ink} k", label, mono=True)
    )
    return parts, width


def card(
    x: float,
    y: float,
    width: float,
    *,
    heading: str | None = None,
    heading_mono: bool = False,
    heading_class: str = "ink h",
    lines: tuple[str, ...] = (),
    line_class: str = "soft b",
    line_size: float = 13.0,
    code: tuple[str, ...] = (),
    code_size: float = 12.5,
    notes: tuple[str, ...] = (),
    pills: tuple[tuple[str, str | None], ...] = (),
    accent: str | None = None,
    surface: str = "surface",
    pad: float = 16.0,
) -> tuple[str, float]:
    """Return a card, and the height it needed.

    The height is computed from the wrapped content rather than fixed, which is
    what keeps the French figure honest: the same sentence is reliably longer in
    French, and a card sized for the English one would cut it off.

    Parameters
    ----------
    x, y : float
        Top-left corner.
    width : float
        Card width.
    heading : str, optional
        The bold first line.
    heading_mono : bool, optional
        Set the heading in the monospace stack, for a command or a file name.
    heading_class : str, optional
        Classes for the heading.
    lines : tuple of str, optional
        Body paragraphs, each wrapped to the card's inner width.
    line_class, line_size : str, float, optional
        Classes and size for the body.
    code : tuple of str, optional
        Monospace lines, set verbatim and never wrapped: they are file content,
        and a wrapped YAML line is not that file any more.
    code_size : float, optional
        Their size. The caller lowers it rather than letting a long path run out
        of its block, since the path cannot be shortened without being wrong.
    notes : tuple of str, optional
        Smaller trailing lines, in the faint ink.
    pills : tuple, optional
        ``(label, status)`` pairs for the bottom row.
    accent : str, optional
        Class for a coloured bar down the left edge.
    surface : str, optional
        Which surface class to fill the card with.
    pad : float, optional
        Inner padding.

    Returns
    -------
    tuple
        The elements, and the card's height.

    Examples
    --------
    >>> body, height = card(0, 0, 200, heading="Title", lines=("a sentence",))
    >>> height > 0 and body.startswith("<g>")
    True
    """
    inner = width - 2 * pad - (6 if accent else 0)
    left = x + pad + (6 if accent else 0)
    parts: list[str] = []
    cursor = y + pad + 2

    if heading is not None:
        size = 15.5
        for line in wrap(heading, inner, size, mono=heading_mono):
            cursor += size * 1.02
            parts.append(text(left, cursor, heading_class, line, mono=heading_mono))
            cursor += size * (_LEADING - 1.02)
        cursor += 3

    for index, paragraph in enumerate(lines):
        # A list of rules set as one block reads as one rule with a long tail.
        cursor += 5 if index else 0
        for line in wrap(paragraph, inner, line_size):
            cursor += line_size * 1.02
            parts.append(text(left, cursor, line_class, line))
            cursor += line_size * (_LEADING - 1.02)

    if code:
        cursor += 6
        size = code_size
        block_top = cursor - 4
        for line in code:
            cursor += size * 1.02
            parts.append(text(left + 10, cursor, "soft c", line, mono=True, preserve=True))
            cursor += size * (_LEADING - 1.02)
        parts.insert(
            0,
            f'<rect class="sunken" x="{left:g}" y="{block_top:.1f}" width="{inner:.1f}" '
            f'height="{cursor - block_top + 4:.1f}" rx="7"/>',
        )
        cursor += 4

    for note in notes:
        cursor += 3
        for line in wrap(note, inner, 12.5):
            cursor += 12.5 * 1.02
            parts.append(text(left, cursor, "faint n", line))
            cursor += 12.5 * (_LEADING - 1.02)

    if pills:
        cursor += 12
        offset = left
        for label, status in pills:
            body, pill_width = chip(offset, cursor, label, status)
            parts.append(body)
            offset += pill_width + 8
        cursor += 20

    height = cursor - y + pad
    # The accent is a second rounded rectangle peeking out from behind the card
    # rather than a clipped bar: the card's own border then draws uninterrupted,
    # which a bar sitting inside it would break at two corners.
    frame = ""
    if accent:
        frame += (
            f'<rect class="{accent}" x="{x:g}" y="{y:g}" width="16" height="{height:.1f}" rx="10"/>'
        )
    body_x = x + 6 if accent else x
    frame += (
        f'<rect class="{surface} edge card" x="{body_x:g}" y="{y:g}" '
        f'width="{width - (6 if accent else 0):g}" height="{height:.1f}" rx="10"/>'
    )
    return "<g>" + frame + "".join(parts) + "</g>", height


def connector(
    x1: float, y1: float, x2: float, y2: float, status: str | None = None, *, curved: bool = True
) -> str:
    """Return one arrow from a box to a box.

    Parameters
    ----------
    x1, y1 : float
        Where it leaves.
    x2, y2 : float
        Where it arrives, tip included.
    status : str, optional
        Colour it by a status, so the weakest colour in a chain is visible
        sitting upstream of everything it weakened.
    curved : bool, optional
        A cubic between columns that are far apart; a straight line between
        neighbours, which is what the report's own chain figure draws.

    Returns
    -------
    str
        A ``<path>``.

    Examples
    --------
    >>> connector(0, 0, 10, 10).startswith("<path")
    True
    """
    name = _token(status) if status else "line"
    stroke = f"{name}-edge" if status else "strong"
    if curved:
        middle = (x1 + x2) / 2
        shape = f"M{x1:.1f},{y1:.1f} C{middle:.1f},{y1:.1f} {middle:.1f},{y2:.1f} {x2:.1f},{y2:.1f}"
    else:
        shape = f"M{x1:.1f},{y1:.1f} L{x2:.1f},{y2:.1f}"
    return (
        f'<path class="{stroke}" d="{shape}" fill="none" stroke-width="1.4" '
        f'marker-end="url(#arrow-{name})"/>'
    )


def title_block(words: dict[str, str], parts: list[str]) -> float:
    """Write a figure's title and subtitle, and return where the body may start.

    Parameters
    ----------
    words : dict
        Needs ``title`` and ``subtitle``.
    parts : list of str
        Accumulator the elements are appended to.

    Returns
    -------
    float
        The y the first row of content may use.

    Examples
    --------
    >>> body: list[str] = []
    >>> title_block({"title": "T", "subtitle": "S"}, body) > 0
    True
    """
    parts.append(text(MARGIN, 58, "ink t", words["title"]))
    cursor = 72.0
    for line in wrap(words["subtitle"], WIDTH - 2 * MARGIN, 15):
        cursor += 15 * 1.05
        parts.append(text(MARGIN, cursor, "soft s", line))
        cursor += 15 * (_LEADING - 1.05)
    return cursor + 22


def column_head(x: float, y: float, label: str) -> str:
    """Return a column's small capital heading.

    Examples
    --------
    >>> column_head(0, 0, "WHERE").startswith("<text")
    True
    """
    return text(x, y, "faint k", label)


def stack(
    x: float, width: float, items: tuple[dict[str, object], ...], gap: float, top: float
) -> tuple[str, float, list[tuple[float, float]]]:
    """Lay a column of cards out from a top edge.

    Parameters
    ----------
    x, width : float
        Where the column sits and how wide it is.
    items : tuple of dict
        One dictionary of :func:`card` keyword arguments per card.
    gap : float
        Space between cards.
    top : float
        The y the first card starts at.

    Returns
    -------
    tuple
        The elements, the column's total height, and the ``(y, height)`` of each
        card, which is what the connectors need to find their anchors.

    Examples
    --------
    >>> body, total, boxes = stack(0, 200, ({"heading": "A"}, {"heading": "B"}), 10, 0)
    >>> len(boxes) == 2 and total > 0
    True
    """
    parts: list[str] = []
    boxes: list[tuple[float, float]] = []
    cursor = top
    for item in items:
        body, height = card(x, cursor, width, **item)  # type: ignore[arg-type]
        parts.append(body)
        boxes.append((cursor, height))
        cursor += height + gap
    return "".join(parts), cursor - gap - top, boxes


def column_height(
    x: float, width: float, items: tuple[dict[str, object], ...], gap: float
) -> float:
    """Return how tall a column will be, without placing it.

    Examples
    --------
    >>> column_height(0, 200, ({"heading": "A"},), 10) > 0
    True
    """
    return stack(x, width, items, gap, 0.0)[1]


def footer(parts: list[str], y: float, notes: tuple[str, ...]) -> float:
    """Write the closing note under a figure, and return the bottom of it.

    Parameters
    ----------
    parts : list of str
        Accumulator.
    y : float
        Where the rule above the note goes.
    notes : tuple of str
        One or more paragraphs.

    Returns
    -------
    float
        The y of the last baseline.

    Examples
    --------
    >>> body: list[str] = []
    >>> footer(body, 10, ("a note",)) > 10
    True
    """
    parts.append(
        f'<line class="edge" x1="{MARGIN}" y1="{y:.1f}" x2="{WIDTH - MARGIN}" y2="{y:.1f}" '
        'stroke-width="1"/>'
    )
    cursor = y + 8
    for index, note in enumerate(notes):
        cursor += 7 if index else 0
        for line in wrap(note, WIDTH - 2 * MARGIN, 12.5):
            cursor += 12.5 * 1.05
            parts.append(text(MARGIN, cursor, "faint n", line))
            cursor += 12.5 * (_LEADING - 1.05)
    return cursor


#: Everything the first figure says, per language. The two versions are written
#: rather than translated: a French card is a French sentence, not an English
#: one with the words changed, and the layout gives each of them the room it
#: needs rather than the room the English one needed.
PIPELINE: Final[dict[str, dict[str, object]]] = {
    "en": {
        "title": "From your repository to a figure somebody can quote",
        "subtitle": "Three sources of fact write one file. Everything anybody reads is rendered "
        "from that file, and nothing in it may state a number without saying where it came from.",
        "heads": ("WHERE THE FACTS COME FROM", "WHAT GETS COMMITTED", "WHAT PEOPLE READ"),
        "sources": (
            {
                "heading": "Reading the repository",
                "line": "Languages, frameworks, how much work one full run performs, which paid "
                "interfaces you call and the line that calls them.",
                "note": "Deterministic, and every finding quotes its evidence.",
                "pills": (),
                "accent": "strong-fill",
            },
            {
                "heading": "Running a capped slice of it",
                "line": "With --run, and only once you have agreed: seconds off the clock, joules "
                "off whatever counters this machine publishes to an ordinary user.",
                "note": "The slice covers a share your own configuration states, so projecting "
                "to a whole run is arithmetic.",
                "pills": (("measured", "measured"),),
                "accent": "measured",
            },
            {
                "heading": "Sourced catalogues",
                "line": "Wattages, grid carbon intensities, tariffs, the building's overhead, "
                "published manufacturing footprints.",
                "note": "Every row carries the page it came from and the date somebody read it. "
                "No row for your part is a normal outcome, and it is named.",
                "pills": (("estimated", "estimated"), ("TODO", "TODO")),
                "accent": "estimated",
            },
        ),
        "file": {
            "heading": "cost_of_running.yaml",
            "line": "Committed next to the code, and reviewed in a pull request like the "
            "rest of it.",
        },
        "rules": {
            "heading": "What the validator enforces",
            "lines": (
                "Every number lives inside a quantity, so an extra block cannot smuggle a figure "
                "past the rules.",
                "Every derived value is recomputed from the inputs it names, units parsed down to "
                "their base dimensions.",
                "Nothing claims to be better founded than the weakest input it came from.",
            ),
        },
        "readers": (
            {
                "heading": "Markdown",
                "line": "Straight into the pull request, next to the diff that moved the number.",
            },
            {
                "heading": "One self-contained web page",
                "line": "Offline, light and dark, and it recomputes for another country in the "
                "browser.",
            },
            {
                "heading": "Word and PDF",
                "line": "For whoever needs a document, with a title block saying what produced it "
                "and when.",
            },
            {
                "heading": "saggio dashboard",
                "mono": True,
                "line": "Every committed model on one page, led by how much of each is measured.",
            },
            {
                "heading": "saggio diff",
                "mono": True,
                "line": "Fails the build when a cost worsened, a status weakened, or a quantity "
                "quietly disappeared.",
            },
        ),
        "foot": (
            "Nothing on the right may say anything the file does not. What nobody can supply "
            "stays TODO the whole way through — never a zero, never a plausible number.",
        ),
        "alt": "Three sources of fact — reading the repository, running a capped slice once you "
        "have agreed, and sourced catalogues — write one committed YAML model. The validator "
        "checks it, and the Markdown report, the self-contained web page, the Word and PDF "
        "documents, the team dashboard and the drift gate are all rendered from that one file.",
    },
    "fr": {
        "title": "De votre dépôt à un chiffre qu'on peut citer",
        "subtitle": "Trois sources de faits écrivent un seul fichier. Tout ce que quiconque lit "
        "est rendu depuis ce fichier, et rien n'y a le droit d'avancer un chiffre sans dire d'où "
        "il vient.",
        "heads": ("D'OÙ VIENNENT LES FAITS", "CE QUI EST VERSIONNÉ", "CE QUE LES GENS LISENT"),
        "sources": (
            {
                "heading": "Lire le dépôt",
                "line": "Les langages, les frameworks, la quantité de travail d'une exécution "
                "complète, les interfaces payantes appelées et la ligne qui les appelle.",
                "note": "Tout est déterministe, et chaque constat cite sa preuve.",
                "pills": (),
                "accent": "strong-fill",
            },
            {
                "heading": "En exécuter une tranche plafonnée",
                "line": "Avec --run, et seulement une fois votre accord donné : les secondes à "
                "l'horloge, les joules aux compteurs que la machine publie à un utilisateur "
                "ordinaire.",
                "note": "La tranche couvre une part que votre propre configuration énonce : "
                "projeter sur une exécution entière relève du calcul.",
                "pills": (("measured", "measured"),),
                "accent": "measured",
            },
            {
                "heading": "Les catalogues sourcés",
                "line": "Puissances, intensités carbone du réseau, tarifs, surcoût du bâtiment, "
                "empreintes de fabrication publiées.",
                "note": "Chaque ligne porte la page d'où elle vient et la date où quelqu'un l'a "
                "lue. N'avoir aucune ligne pour votre composant est ordinaire, et c'est dit.",
                "pills": (("estimated", "estimated"), ("TODO", "TODO")),
                "accent": "estimated",
            },
        ),
        "file": {
            "heading": "cost_of_running.yaml",
            "line": "Versionné à côté du code, et relu dans une pull request comme le reste.",
        },
        "rules": {
            "heading": "Ce que le validateur impose",
            "lines": (
                "Tout nombre vit dans une quantité : un bloc ajouté ne peut pas faire passer un "
                "chiffre sous la règle.",
                "Toute valeur dérivée est recalculée depuis les apports qu'elle nomme, unités "
                "décomposées en dimensions de base.",
                "Rien ne se prétend mieux fondé que le plus faible des apports dont il vient.",
            ),
        },
        "readers": (
            {
                "heading": "Markdown",
                "line": "Directement dans la pull request, à côté du diff qui a bougé le chiffre.",
            },
            {
                "heading": "Une page web autonome",
                "line": "Hors ligne, claire et sombre, et elle recalcule pour un autre pays dans "
                "le navigateur.",
            },
            {
                "heading": "Word et PDF",
                "line": "Pour qui veut un document, avec un pavé de titre disant ce qui l'a "
                "produit et quand.",
            },
            {
                "heading": "saggio dashboard",
                "mono": True,
                "line": "Tous les modèles versionnés sur une page, menés par la part mesurée de "
                "chacun.",
            },
            {
                "heading": "saggio diff",
                "mono": True,
                "line": "Fait échouer le build quand un coût empire, qu'un statut faiblit ou "
                "qu'une quantité disparaît sans bruit.",
            },
        ),
        "foot": (
            "Rien, à droite, n'a le droit de dire ce que le fichier ne dit pas. Ce que personne "
            "ne peut fournir reste TODO de bout en bout — jamais un zéro, jamais un chiffre "
            "plausible.",
        ),
        "alt": "Trois sources de faits — lire le dépôt, en exécuter une tranche plafonnée une "
        "fois l'accord donné, et les catalogues sourcés — écrivent un seul modèle YAML versionné. "
        "Le validateur le vérifie, et le rapport Markdown, la page web autonome, les documents "
        "Word et PDF, le tableau de bord d'équipe et le garde-fou de dérive en sont tous rendus.",
    },
}

#: The quantity the first figure shows, kept short enough to sit in its card and
#: still be the file's own notation. It is the same quantity the two front pages
#: quote in prose a few lines above the figure.
_QUANTITY: Final[tuple[str, ...]] = (
    "carbon:",
    "  value: 0.0014",
    '  unit: "gCO2e"',
    '  status: "estimated"',
    "  derived_from:",
    "    - scenarios[0].costs.energy",
    "    - assumptions.grid_carbon_intensity",
)


def pipeline(lang: str) -> str:
    """Draw the first figure: where a number comes from and who reads it.

    Parameters
    ----------
    lang : str
        ``"en"`` or ``"fr"``.

    Returns
    -------
    str
        A standalone SVG.

    Examples
    --------
    >>> svg = pipeline("en")
    >>> "cost_of_running.yaml" in svg
    True
    """
    words = PIPELINE[lang]
    heads: tuple[str, str, str] = words["heads"]  # type: ignore[assignment]
    parts: list[str] = []
    top = title_block(words, parts)  # type: ignore[arg-type]

    left_x, left_w = MARGIN, 312.0
    mid_x, mid_w = 416.0, 348.0
    right_x, right_w = 824.0, 312.0

    sources = tuple(
        {
            "heading": item["heading"],
            "lines": (item["line"],),
            "notes": (item["note"],),
            "pills": item["pills"],
            "accent": item["accent"],
        }
        for item in words["sources"]  # type: ignore[attr-defined]
    )
    centre = (
        {
            "heading": words["file"]["heading"],  # type: ignore[index]
            "heading_mono": True,
            "lines": (words["file"]["line"],),  # type: ignore[index]
            "code": _QUANTITY,
            "code_size": 11.5,
        },
        {
            "heading": words["rules"]["heading"],  # type: ignore[index]
            "heading_class": "ink h",
            "lines": words["rules"]["lines"],  # type: ignore[index]
            "line_class": "soft b",
            "surface": "surface",
            "accent": "accent",
        },
    )
    readers = tuple(
        {
            "heading": item["heading"],
            "heading_mono": bool(item.get("mono")),
            "lines": (item["line"],),
        }
        for item in words["readers"]  # type: ignore[attr-defined]
    )

    parts.append(column_head(left_x, top, heads[0]))
    parts.append(column_head(mid_x, top, heads[1]))
    parts.append(column_head(right_x, top, heads[2]))
    body_top = top + 24

    columns = (
        (left_x, left_w, sources, 18.0),
        (mid_x, mid_w, centre, 18.0),
        (right_x, right_w, readers, 14.0),
    )
    tallest = max(column_height(x, w, items, gap) for x, w, items, gap in columns)

    placed: list[list[tuple[float, float]]] = []
    bodies: list[str] = []
    for x, w, items, gap in columns:
        height = column_height(x, w, items, gap)
        body, _, boxes = stack(x, w, items, gap, body_top + (tallest - height) / 2)
        bodies.append(body)
        placed.append(boxes)

    file_top, file_height = placed[1][0]
    file_middle = file_top + file_height / 2
    for (y, height), item in zip(placed[0], words["sources"], strict=True):  # type: ignore[arg-type]
        parts.append(
            connector(left_x + left_w, y + height / 2, mid_x - 7, file_middle, _arrow_status(item))
        )
    for y, height in placed[2]:
        parts.append(connector(mid_x + mid_w, file_middle, right_x - 7, y + height / 2))
    parts.extend(bodies)

    bottom = footer(parts, body_top + tallest + 30, words["foot"])  # type: ignore[arg-type]
    height = int(bottom + MARGIN)
    return (
        "\n".join(
            head("pipeline", words["title"], words["alt"], height) + parts + ["</svg>"]  # type: ignore[arg-type]
        )
        + "\n"
    )


def _arrow_status(source: dict[str, object]) -> str | None:
    """Return the status an arrow out of a source card should be drawn in.

    A source that can only ever hand over an estimate is drawn in the estimated
    colour, so the reader sees what each path is worth before reading a word.

    Examples
    --------
    >>> _arrow_status({"pills": (("measured", "measured"),)})
    'measured'
    >>> _arrow_status({"pills": ()}) is None
    True
    """
    pills: tuple[tuple[str, str | None], ...] = source.get("pills", ())  # type: ignore[assignment]
    return pills[0][1] if pills else None


def _template() -> dict[str, object]:
    """Return the annotated starter model, parsed.

    Examples
    --------
    >>> "assumptions" in _template()
    True
    """
    return yaml.safe_load(TEMPLATE.read_text(encoding="utf-8"))


def _at(data: object, path: str) -> dict[str, object]:
    """Return the quantity a dotted path points at, indices included.

    The paths are the model's own, the ones a ``derived_from`` list is written
    with, so the figure names its sources exactly as the file does.

    Examples
    --------
    >>> _at({"a": [{"b": {"value": 1}}]}, "a[0].b")
    {'value': 1}
    """
    node: object = data
    for step in path.split("."):
        match = re.fullmatch(r"([a-z_]+)\[(\d+)\]", step)
        if match:
            node = node[match.group(1)][int(match.group(2))]  # type: ignore[index]
        else:
            node = node[step]  # type: ignore[index]
    return node  # type: ignore[return-value]


def reading(path: str, lang: str) -> str:
    """Return a quantity from the template, written the way a language writes it.

    Three significant figures, because this is a figure in a README rather than
    a report: the file keeps the precision, and the drawing keeps the point.

    Parameters
    ----------
    path : str
        A dotted path into the template.
    lang : str
        ``"en"`` or ``"fr"``.

    Returns
    -------
    str
        The value and its unit, or an em dash where the template holds the field
        open, which is a state this figure exists to show.

    Examples
    --------
    >>> reading("assumptions.power_draw", "en")
    '600 W'
    >>> reading("assumptions.water_usage_effectiveness", "en")
    '—'
    >>> reading("scenarios[0].runtime", "fr")
    '0,1 s'
    """
    quantity = _at(_template(), path)
    value = quantity.get("value")
    if value is None:
        return "—"
    with language(lang):
        figure = number(f"{float(value):.3g}")
    unit = quantity.get("unit")
    # A ratio has no unit worth printing: "1.5 ratio" reads as a mistake, and
    # the note under the box already says what the one-and-a-half is of.
    return figure if unit in (None, "ratio") else f"{figure} {unit}"


#: The chain the second figure draws: identifier, which column it sits in, the
#: status it carries in this figure's scenario, and where its number is read
#: from in the template. The columns follow the rule the report's own chain
#: figure uses -- an input sits one column left of whichever value needs it --
#: which is what keeps every arrow here between neighbours and uncrossed.
CHAIN: Final[tuple[tuple[str, int, str, str], ...]] = (
    ("runtime", 0, "measured", "scenarios[0].runtime"),
    ("power", 0, "measured", "assumptions.power_draw"),
    ("effectiveness", 1, "estimated", "assumptions.pue"),
    ("machine_energy", 1, "measured", "assumptions.machine_energy"),
    ("water_effectiveness", 1, "TODO", "assumptions.water_usage_effectiveness"),
    ("energy", 2, "estimated", "scenarios[0].costs.energy"),
    ("grid", 2, "estimated", "assumptions.grid_carbon_intensity"),
    ("water", 2, "TODO", "scenarios[0].costs.water"),
    ("carbon", 3, "estimated", "scenarios[0].costs.carbon"),
)

#: Which value was computed from which. Same direction as the model's
#: ``derived_from`` lists, read the other way round.
LINKS: Final[tuple[tuple[str, str], ...]] = (
    ("runtime", "machine_energy"),
    ("power", "machine_energy"),
    ("machine_energy", "energy"),
    ("effectiveness", "energy"),
    ("machine_energy", "water"),
    ("water_effectiveness", "water"),
    ("energy", "carbon"),
    ("grid", "carbon"),
)

#: Label and provenance for every box, per language.
WEAKEST: Final[dict[str, dict[str, object]]] = {
    "en": {
        "title": "Where one figure comes from, and why it cannot outrank its inputs",
        "subtitle": "One inference on a median-sized request, with the numbers from the starter "
        "model this package ships. Follow the colour down the left edge of each box: a computed "
        "value can be no better founded than the weakest box upstream of it.",
        "boxes": {
            "runtime": ("runtime", "off the clock, over the slice that ran"),
            "power": ("power draw", "off this machine's own counters"),
            "effectiveness": (
                "power usage effectiveness",
                "a catalogue row, with its source and its date",
            ),
            "machine_energy": ("the machine's energy", "runtime × power draw"),
            "water_effectiveness": (
                "water usage effectiveness",
                "no row: a self-run room publishes none",
            ),
            "energy": ("the building's energy", "the machine's energy × the overhead above"),
            "grid": ("grid carbon intensity", "a catalogue row for the country you stated"),
            "water": ("water", "the machine's energy × an effectiveness nobody has"),
            "carbon": ("carbon", "the building's energy × the intensity above"),
        },
        "foot": (
            "Take the counters away and the two measured boxes read estimated — a wattage from "
            "the catalogue instead of a reading — and every box downstream of them follows. "
            "Nothing else in the file changes, and nothing has to be edited for it to happen.",
            "The water branch is the rule at its least convenient and its most useful. A "
            "self-run room publishes no water usage effectiveness, so the figure stays TODO: an "
            "invented water number in a sustainability report is the worst kind of number there "
            "is.",
        ),
        "alt": "A derivation chain for one inference: runtime and power draw, both measured, give "
        "the machine's energy; multiplied by an estimated power usage effectiveness it gives the "
        "building's energy, which is therefore only estimated; multiplied by an estimated grid "
        "carbon intensity it gives the carbon figure. The water branch ends in TODO because no "
        "water usage effectiveness is published for a self-run room.",
    },
    "fr": {
        "title": "D'où vient un chiffre, et pourquoi il ne peut pas dépasser ses apports",
        "subtitle": "Une inférence sur une requête de taille médiane, avec les chiffres du "
        "modèle de départ que livre ce paquet. Suivez la couleur au bord gauche de chaque "
        "case : une valeur calculée ne peut pas être mieux fondée que la plus faible des cases en "
        "amont.",
        "boxes": {
            "runtime": ("durée d'exécution", "à l'horloge, sur la tranche exécutée"),
            "power": ("puissance appelée", "aux compteurs de cette machine"),
            "effectiveness": (
                "efficacité énergétique du site",
                "une ligne de catalogue, avec sa source et sa date",
            ),
            "machine_energy": ("énergie de la machine", "durée × puissance"),
            "water_effectiveness": (
                "efficacité d'usage de l'eau",
                "aucune ligne : une salle en propre n'en publie pas",
            ),
            "energy": ("énergie du bâtiment", "énergie de la machine × le surcoût ci-dessus"),
            "grid": (
                "intensité carbone du réseau",
                "une ligne de catalogue pour le pays que vous avez énoncé",
            ),
            "water": ("eau", "énergie de la machine × une efficacité que personne n'a"),
            "carbon": ("carbone", "énergie du bâtiment × l'intensité ci-dessus"),
        },
        "foot": (
            "Retirez les compteurs : les deux cases measured passent à estimated — une puissance "
            "du catalogue plutôt qu'un relevé — et toutes les cases en aval suivent. Rien d'autre "
            "ne change dans le fichier, et il n'y a rien à éditer pour que cela arrive.",
            "La branche de l'eau, c'est la règle au plus gênant et au plus utile. Une salle "
            "exploitée en propre ne publie aucune efficacité d'usage de l'eau, donc le chiffre "
            "reste TODO : un chiffre d'eau inventé dans un rapport de durabilité est le pire des "
            "chiffres qui soient.",
        ),
        "alt": "Une chaîne de dérivation pour une inférence : la durée et la puissance, toutes "
        "deux mesurées, donnent l'énergie de la machine ; multipliée par une efficacité "
        "énergétique du site estimée, elle donne l'énergie du bâtiment, qui n'est donc "
        "qu'estimée ; multipliée par une intensité carbone estimée, elle donne le chiffre du "
        "carbone. La branche de l'eau finit en TODO, faute d'efficacité d'usage de l'eau publiée "
        "pour une salle exploitée en propre.",
    },
}

#: Geometry of the chain: four columns, each wide enough for a label that does
#: not wrap in either language, inside the shared canvas.
_NODE_WIDTH: Final[float] = 228.0
_NODE_GAP: Final[float] = 60.0
_ROW_GAP: Final[float] = 20.0


def weakest_link(lang: str) -> str:
    """Draw the second figure: one derivation chain, coloured by status.

    Parameters
    ----------
    lang : str
        ``"en"`` or ``"fr"``.

    Returns
    -------
    str
        A standalone SVG.

    Examples
    --------
    >>> "600" in weakest_link("en")
    True
    """
    words = WEAKEST[lang]
    boxes: dict[str, tuple[str, str]] = words["boxes"]  # type: ignore[assignment]
    parts: list[str] = []
    body_top = title_block(words, parts)  # type: ignore[arg-type]

    columns: dict[int, list[tuple[str, str, str]]] = {}
    for key, column, status, path in CHAIN:
        columns.setdefault(column, []).append((key, status, path))

    heights: dict[int, float] = {}
    items: dict[int, tuple[dict[str, object], ...]] = {}
    for column, entries in columns.items():
        items[column] = tuple(
            {
                "heading": boxes[key][0],
                "lines": (reading(path, lang),),
                "line_class": "ink v",
                "line_size": 17.0,
                "notes": (boxes[key][1],),
                "pills": ((status, status),),
                "accent": _token(status),
            }
            for key, status, path in entries
        )
        heights[column] = column_height(0, _NODE_WIDTH, items[column], _ROW_GAP)
    tallest = max(heights.values())

    placed: dict[str, tuple[float, float, float]] = {}
    bodies: list[str] = []
    for column, entries in columns.items():
        x = MARGIN + column * (_NODE_WIDTH + _NODE_GAP)
        body, _, laid = stack(
            x, _NODE_WIDTH, items[column], _ROW_GAP, body_top + (tallest - heights[column]) / 2
        )
        bodies.append(body)
        for (key, _, _), (y, height) in zip(entries, laid, strict=True):
            placed[key] = (x, y, height)

    status_of = {key: status for key, _, status, _ in CHAIN}
    for source, target in LINKS:
        x1, y1, h1 = placed[source]
        x2, y2, h2 = placed[target]
        parts.append(
            connector(
                x1 + _NODE_WIDTH,
                y1 + h1 / 2,
                x2 - 7,
                y2 + h2 / 2,
                status_of[source],
                curved=False,
            )
        )
    parts.extend(bodies)

    bottom = footer(parts, body_top + tallest + 30, words["foot"])  # type: ignore[arg-type]
    height = int(bottom + MARGIN)
    return (
        "\n".join(
            head("chain", words["title"], words["alt"], height) + parts + ["</svg>"]  # type: ignore[arg-type]
        )
        + "\n"
    )


#: Everything the third figure says. The five rows are the five surfaces of the
#: table it sits under, in the same order, because a figure that reordered them
#: would make the reader check which one was wrong.
SURFACES: Final[dict[str, dict[str, object]]] = {
    "en": {
        "title": "One engine, five surfaces",
        "subtitle": "The person who produces a figure is rarely the person who has to file it, "
        "and most readers will never install a Python package. So the same engine answers five "
        "ways — and every one of them is an adapter over the same public functions, which is a "
        "rule tests enforce rather than a habit.",
        "heads": ("HOW YOU REACH IT", "WHAT ACTUALLY RUNS", "WHAT COMES BACK"),
        "rows": (
            ("Library", "A script, a notebook, another package.", "import saggio"),
            ("Command line", "A terminal, and continuous integration.", "saggio audit ."),
            (
                "HTTP API",
                "A browser, an internal service, a reporting pipeline.",
                "uvicorn saggio.api.app:app",
            ),
            (
                "Agent protocol",
                "Asking in your own words, in your own language.",
                "uvicorn saggio.api.mcp:app",
            ),
            ("Skill", "Claude, and any agent that reads Agent Skills.", "skills/saggio/"),
        ),
        "engine": {
            "heading": "The same public functions",
            "note": "A surface adds argument parsing and printing. Nothing else, and nothing of "
            "its own.",
        },
        "answers": (
            {
                "heading": "The same answer",
                "line": "One model, one set of rules, one report. A figure produced through one "
                "surface is the figure the others produce, because it is the same function that "
                "produced it.",
                "accent": "accent",
            },
            {
                "heading": "And the two limits that follow",
                "line": "No surface may do what the library cannot: a capability only one of them "
                "had would be locked away from every other caller. And the HTTP surface runs "
                "nobody's code — over a network there is nobody to ask for consent — cloning a "
                "repository only where the operator allowed it.",
                "accent": "todo",
            },
        ),
        "foot": (
            "A sixth surface is another adapter over the same functions, and USING.md says what "
            "it may and may not do.",
        ),
        "alt": "Five surfaces — a Python library, the command line, an HTTP API, an agent "
        "protocol and an Agent Skill — all call the same public functions, so each returns the "
        "same model, the same rules and the same report; no surface may do what the library "
        "cannot, and the HTTP surface runs nobody's code.",
    },
    "fr": {
        "title": "Un seul moteur, cinq surfaces",
        "subtitle": "La personne qui produit un chiffre est rarement celle qui doit le déclarer, "
        "et la plupart des lecteurs n'installeront jamais un paquet Python. Le même moteur répond "
        "donc de cinq façons — et chacune est un adaptateur au-dessus des mêmes fonctions "
        "publiques, règle imposée par des tests plutôt qu'habitude.",
        "heads": ("PAR OÙ ON L'ATTEINT", "CE QUI S'EXÉCUTE VRAIMENT", "CE QUI REVIENT"),
        "rows": (
            ("Bibliothèque", "Un script, un notebook, un autre paquet.", "import saggio"),
            ("Ligne de commande", "Un terminal, et l'intégration continue.", "saggio audit ."),
            (
                "API HTTP",
                "Un navigateur, un service interne, une chaîne de reporting.",
                "uvicorn saggio.api.app:app",
            ),
            (
                "Protocole d'agent",
                "Poser la question avec ses mots, dans sa langue.",
                "uvicorn saggio.api.mcp:app",
            ),
            ("Skill", "Claude, et tout agent qui lit les Agent Skills.", "skills/saggio/"),
        ),
        "engine": {
            "heading": "Les mêmes fonctions publiques",
            "note": "Une surface ajoute l'analyse des arguments et l'affichage. Rien d'autre, et "
            "rien qui lui soit propre.",
        },
        "answers": (
            {
                "heading": "La même réponse",
                "line": "Un modèle, un jeu de règles, un rapport. Un chiffre produit par une "
                "surface est celui que produisent les autres, puisque c'est la même fonction qui "
                "l'a produit.",
                "accent": "accent",
            },
            {
                "heading": "Et les deux limites qui s'ensuivent",
                "line": "Aucune surface ne peut ce que la bibliothèque ne peut pas : une "
                "capacité réservée à l'une serait interdite à tous les autres appelants. Et la "
                "surface HTTP n'exécute le code de personne — à travers un réseau, il n'y a "
                "personne à qui demander un consentement — et ne clone un dépôt que là où "
                "l'exploitant l'a permis.",
                "accent": "todo",
            },
        ),
        "foot": (
            "Une sixième surface est un adaptateur de plus au-dessus des mêmes fonctions, et "
            "UTILISER.md dit ce qu'elle a et n'a pas le droit de faire.",
        ),
        "alt": "Cinq surfaces — une bibliothèque Python, la ligne de commande, une API HTTP, un "
        "protocole d'agent et une Agent Skill — appellent toutes les mêmes fonctions publiques, "
        "si bien que chacune rend le même modèle, les mêmes règles et le même rapport ; aucune ne "
        "peut ce que la bibliothèque ne peut pas, et la surface HTTP n'exécute le code de "
        "personne.",
    },
}

#: The names the engine card lists. They are public names of the package, in the
#: order a job uses them, and `python -c "import saggio"` is enough to check
#: that every one of them is still there -- which a test does.
ENGINE: Final[tuple[str, ...]] = (
    "read_repository()",
    "run_slice()",
    "audit()",
    "validate()",
    "render_markdown()",
    "render_html()",
    "compare()",
)


def surfaces(lang: str) -> str:
    """Draw the third figure: five adapters over one set of functions.

    Parameters
    ----------
    lang : str
        ``"en"`` or ``"fr"``.

    Returns
    -------
    str
        A standalone SVG.

    Examples
    --------
    >>> "import saggio" in surfaces("fr")
    True
    """
    words = SURFACES[lang]
    heads: tuple[str, str, str] = words["heads"]  # type: ignore[assignment]
    parts: list[str] = []
    top = title_block(words, parts)  # type: ignore[arg-type]

    left_x, left_w = MARGIN, 392.0
    mid_x, mid_w = 486.0, 300.0
    right_x, right_w = 830.0, 306.0

    rows = tuple(
        {"heading": name, "lines": (who,), "notes": (), "code": (how,), "accent": "accent"}
        for name, who, how in words["rows"]  # type: ignore[attr-defined]
    )
    engine = (
        {
            "heading": words["engine"]["heading"],  # type: ignore[index]
            "code": ENGINE,
            "notes": (words["engine"]["note"],),  # type: ignore[index]
            "surface": "surface",
        },
    )
    answers = tuple(
        {"heading": item["heading"], "lines": (item["line"],), "accent": item["accent"]}
        for item in words["answers"]  # type: ignore[attr-defined]
    )

    parts.append(column_head(left_x, top, heads[0]))
    parts.append(column_head(mid_x, top, heads[1]))
    parts.append(column_head(right_x, top, heads[2]))
    body_top = top + 24

    columns = (
        (left_x, left_w, rows, 14.0),
        (mid_x, mid_w, engine, 0.0),
        (right_x, right_w, answers, 18.0),
    )
    tallest = max(column_height(x, w, items, gap) for x, w, items, gap in columns)

    placed: list[list[tuple[float, float]]] = []
    bodies: list[str] = []
    for x, w, items, gap in columns:
        height = column_height(x, w, items, gap)
        body, _, laid = stack(x, w, items, gap, body_top + (tallest - height) / 2)
        bodies.append(body)
        placed.append(laid)

    engine_top, engine_height = placed[1][0]
    engine_middle = engine_top + engine_height / 2
    for y, height in placed[0]:
        parts.append(connector(left_x + left_w, y + height / 2, mid_x - 7, engine_middle))
    for y, height in placed[2]:
        parts.append(connector(mid_x + mid_w, engine_middle, right_x - 7, y + height / 2))
    parts.extend(bodies)

    bottom = footer(parts, body_top + tallest + 30, words["foot"])  # type: ignore[arg-type]
    height = int(bottom + MARGIN)
    return (
        "\n".join(
            head("surfaces", words["title"], words["alt"], height) + parts + ["</svg>"]  # type: ignore[arg-type]
        )
        + "\n"
    )


#: The three figures, by the name their file carries.
FIGURES: Final[dict[str, object]] = {
    "pipeline": pipeline,
    "weakest-link": weakest_link,
    "surfaces": surfaces,
}


def draw(figure: str, lang: str) -> str:
    """Return one figure in one language.

    Parameters
    ----------
    figure : str
        ``"pipeline"``, ``"weakest-link"`` or ``"surfaces"``.
    lang : str
        ``"en"`` or ``"fr"``.

    Returns
    -------
    str
        A standalone SVG: the report's palette, light and dark aware through an
        embedded ``prefers-color-scheme`` block, and labelled for a reader who
        cannot see it.

    Examples
    --------
    >>> draw("surfaces", "en").startswith("<svg")
    True
    >>> "prefers-color-scheme" in draw("pipeline", "fr")
    True
    """
    return FIGURES[figure](lang)  # type: ignore[operator]


def main() -> None:
    """Write the six files next to this one."""
    here = pathlib.Path(__file__).resolve().parent
    for figure in FIGURES:
        for lang in ("en", "fr"):
            name = f"readme-{figure}.svg" if lang == "en" else f"readme-{figure}.{lang}.svg"
            (here / name).write_text(draw(figure, lang), encoding="utf-8")
            print(f"assets/{name}")


if __name__ == "__main__":
    main()
