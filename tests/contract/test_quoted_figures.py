"""A figure a page puts in bold beside a model must be that model's figure.

The repository refuses a bare number in a model and has refused one since the
first release. It has never refused anything to a *sentence*, and four Ralph
iterations running, the fault that mattered was in prose:

================ ====================================================== =============
 Iteration        The fault                                              Caught by
================ ====================================================== =============
 #5               an invented Legifrance identifier                      a human
 #6               "this is how Kepler splits a node between pods"        a human
 #7               "median of 5 runs" for a figure that is not one        a human
 #8               a ``derived_from`` that was not a derivation           the validator
================ ====================================================== =============

Only the one about a *number* was caught by a machine. This is the sonde for the
other kind, and it was written after finding that four committed pages had been
stale for two iterations: ``GALLERY.md`` said the render model drew **21.3 W**
three lines above a paragraph saying its floor was **13.8 W** and the figure it
carries **17.4 W**, and the Kepler comparison in ``MEASURING.md`` still quoted a
share, a total, a floor and a conclusion from a measurement that had been
replaced — its headline factor was wrong by 2.7x.

**The convention this enforces**: inside a section that names a committed model,
a figure written in **bold** is a claim that the model carries it. A figure that
is not the model's own — a nameplate rating, a threshold, a figure from a paper
— is written without bold. The rule is therefore declared in the page, by how it
is written, rather than in a list here that would go stale in the direction that
hides the fault.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]

#: Pages written under the convention. Adding a page opts it in; leaving one out
#: cannot hide a fault in a page that is in, which is why this list is safe to
#: keep here while a list of known-bad strings would not be.
PAGES = [
    "GALLERY.md",
    "GALERIE.md",
    "MEASURING.md",
    "MESURER.md",
    "BOUNDARIES.md",
    "FRONTIERES.md",
]

#: A bold figure: ``**21.3 W**``, ``**19.8% share**``, ``**1,01e-05 gCO2e**``.
#: The number must open the bold run, so ``**A factor of 1.58**`` is prose about
#: a figure rather than the figure itself and is left alone.
BOLD_FIGURE = re.compile(
    r"\*\*(?P<number>[0-9][0-9\s.,]*(?:e[-+]?\d+)?)\s*(?P<unit>%|[A-Za-z/]*)"
)

#: Which model a section is about.
MODEL_LINK = re.compile(r"examples/[\w/-]+\.yaml")

#: A heading, which is where one section ends and the next begins.
HEADING = re.compile(r"^#{1,6}\s")


def _as_float(text: str) -> tuple[float, str] | None:
    """Return a quoted figure as a number and the spelling it was written in.

    Parameters
    ----------
    text : str
        The digits as the page wrote them, in either decimal convention.

    Returns
    -------
    tuple or None
        ``(value, spelling)``, or ``None`` when it is not a number.

    Examples
    --------
    >>> _as_float("0,0276")[0]
    0.0276
    >>> _as_float("1,01e-05")[0]
    1.01e-05
    >>> _as_float("x") is None
    True
    """
    # French pages separate thousands with a narrow no-break space.
    cleaned = text.strip()
    for space in (" ", "\u00a0", "\u202f"):
        cleaned = cleaned.replace(space, "")
    # French pages write the decimal separator as a comma; English pages use it
    # as a thousands separator. Both are unambiguous here because no figure in
    # these pages has four digits before the point.
    cleaned = cleaned.replace(",", ".")
    try:
        return float(cleaned), cleaned
    except ValueError:
        return None


def _numbers(node: Any) -> list[float]:
    """Return every number anywhere inside a parsed model.

    Parameters
    ----------
    node : object
        A mapping, a list, or a leaf.

    Returns
    -------
    list of float
        Every numeric leaf, in no particular order.

    Examples
    --------
    >>> sorted(_numbers({"a": 1, "b": [2.0, {"c": 3}], "d": "four"}))
    [1.0, 2.0, 3.0]
    """
    if isinstance(node, bool):
        return []
    if isinstance(node, (int, float)):
        return [float(node)]
    if isinstance(node, dict):
        return [found for value in node.values() for found in _numbers(value)]
    if isinstance(node, list):
        return [found for value in node for found in _numbers(value)]
    return []


def _matches(quoted: float, spelling: str, candidate: float, *, percent: bool) -> bool:
    """Return whether a model's number, read at the page's precision, is the quote.

    Parameters
    ----------
    quoted : float
        What the page says.
    spelling : str
        How it says it, which is what fixes the precision to compare at.
    candidate : float
        One number out of the model.
    percent : bool
        Whether the page wrote it as a percentage, in which case the model holds
        a fraction and the comparison is against a hundred times it.

    Returns
    -------
    bool
        ``True`` when the model's figure rounds to the page's.

    Examples
    --------
    >>> _matches(17.4, "17.4", 17.442896, percent=False)
    True
    >>> _matches(19.8, "19.8", 0.198141, percent=True)
    True
    >>> _matches(21.3, "21.3", 17.442896, percent=False)
    False
    """
    value = candidate * 100.0 if percent else candidate
    if "e" in spelling:
        mantissa = spelling.split("e")[0]
        places = len(mantissa.split(".")[1]) if "." in mantissa else 0
        return f"{value:.{places}e}" == f"{quoted:.{places}e}"
    places = len(spelling.split(".")[1]) if "." in spelling else 0
    return round(value, places) == round(quoted, places)


def _sections(page: str) -> list[tuple[int, list[str], list[str]]]:
    """Return each section of a page with the models it names and its lines.

    Parameters
    ----------
    page : str
        A page filename at the repository root.

    Returns
    -------
    list of tuple
        ``(first_line_number, model_paths, lines)`` for each section that names
        at least one committed model.

    Examples
    --------
    >>> isinstance(_sections("GALLERY.md"), list)
    True
    """
    lines = (ROOT / page).read_text(encoding="utf-8").splitlines()
    sections: list[tuple[int, list[str], list[str]]] = []
    start, block = 0, []
    for number, line in enumerate(lines):
        if HEADING.match(line) and block:
            models = sorted({m for text in block for m in MODEL_LINK.findall(text)})
            if models:
                sections.append((start + 1, models, block))
            start, block = number, []
        block.append(line)
    models = sorted({m for text in block for m in MODEL_LINK.findall(text)})
    if models:
        sections.append((start + 1, models, block))
    return sections


@pytest.mark.parametrize("page", PAGES)
def test_a_bold_figure_beside_a_model_is_that_models_figure(page: str) -> None:
    offenders: list[str] = []
    for first_line, models, lines in _sections(page):
        pool: list[float] = []
        for model in models:
            path = ROOT / model
            if path.is_file():
                pool += _numbers(yaml.safe_load(path.read_text(encoding="utf-8")))
        if not pool:
            continue
        for offset, line in enumerate(lines):
            for found in BOLD_FIGURE.finditer(line):
                parsed = _as_float(found.group("number"))
                if parsed is None:
                    continue
                quoted, spelling = parsed
                percent = found.group("unit") == "%"
                if any(_matches(quoted, spelling, value, percent=percent) for value in pool):
                    continue
                offenders.append(
                    f"{page}:{first_line + offset}: **{found.group('number').strip()}"
                    f"{found.group('unit')}** is in none of {', '.join(models)}"
                )
    assert not offenders, "\n".join(offenders)


#: A table cell quoting one of a model's quantities: ``0.0276 s, measured``.
QUOTED_QUANTITY = re.compile(
    r"^(?P<number>[0-9][0-9\s.,]*(?:e[-+]?\d+)?)\s+(?P<unit>[^\s,]+),\s*(?P<status>\w+)$"
)

#: The status words the pages use, in both languages. Four entries, and a word
#: missing from here only ever makes the check skip a cell — never pass one it
#: should have failed.
STATUS_WORDS = {
    "measured": "measured",
    "mesuré": "measured",
    "estimated": "estimated",
    "estimé": "estimated",
}


def _quantities(model: str) -> list[tuple[float, str, str]]:
    """Return every quantity a model carries, as value, unit and status.

    Parameters
    ----------
    model : str
        A path such as ``examples/render.yaml``.

    Returns
    -------
    list of tuple
        ``(value, unit, status)`` for each quantity carrying a number.

    Examples
    --------
    >>> any(unit == "s" for _, unit, _ in _quantities("examples/render.yaml"))
    True
    """
    from saggio.model import CostModel

    data = yaml.safe_load((ROOT / model).read_text(encoding="utf-8"))
    found: list[tuple[float, str, str]] = []
    for _, quantity in CostModel.from_mapping(data).typed_quantities():
        if isinstance(quantity.value, (int, float)) and not isinstance(quantity.value, bool):
            found.append((float(quantity.value), str(quantity.unit or ""), str(quantity.status)))
    return found


@pytest.mark.parametrize("page", PAGES)
def test_a_table_row_about_a_model_quotes_that_models_quantities(page: str) -> None:
    # Stricter than the bold rule, and on the numbers a reader meets first: a
    # row that links one model must quote that model's value *at that unit and
    # that status*. The gallery's two rows were hand-edited on every iteration
    # that re-measured, and nothing compared them with the files they link to.
    offenders: list[str] = []
    for number, line in enumerate((ROOT / page).read_text(encoding="utf-8").splitlines(), 1):
        if not line.startswith("|"):
            continue
        models = sorted(set(MODEL_LINK.findall(line)))
        if len(models) != 1 or not (ROOT / models[0]).is_file():
            continue
        carried = _quantities(models[0])
        for cell in (part.strip() for part in line.strip("|").split("|")):
            quoted = QUOTED_QUANTITY.match(cell)
            if quoted is None:
                continue
            status = STATUS_WORDS.get(quoted.group("status").lower())
            if status is None:
                continue
            parsed = _as_float(quoted.group("number"))
            if parsed is None:
                continue
            value, spelling = parsed
            unit = quoted.group("unit")
            if any(
                _matches(value, spelling, carried_value, percent=False)
                and carried_unit == unit
                and carried_status == status
                for carried_value, carried_unit, carried_status in carried
            ):
                continue
            offenders.append(f"{page}:{number}: {cell!r} is not in {models[0]}")
    assert not offenders, "\n".join(offenders)
