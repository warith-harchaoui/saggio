"""An arithmetic written in prose must be an arithmetic that works.

Three places in this repository spell out a calculation in words and put its
answer beside it. Nothing checked that the words give the answer:

- a nameplate power note — *"12 cores x 4.0 W + 96 GB x 0.3725 W/GB"* — against
  the ``power_draw`` it is the note of;
- a projection's method — *"Whole run = measured slice / 2.5e-06."* — against
  the projected figure and the slice it was projected from. **This is the only
  place that divisor appears as a number at all**: the model holds
  ``analysis.total_work.stated_as`` as the string ``'400000'`` and the fraction
  nowhere, so the one quantity every projected cost turns on is prose. Until it
  becomes a field, this test is what reads it;
- a comparison table on a page — ``| 0.198 × 15.18 W | **3.01 W** |``.

The check needs no pool of numbers to match against and no knowledge of what the
figures mean. It asks only whether the sentence is self-consistent, which is a
different question from the one the other prose sondes ask — and it catches both
a stale figure and an invented one, in either language.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
MODELS = sorted(path.relative_to(ROOT).as_posix() for path in (ROOT / "examples").rglob("*.yaml"))

#: Pages whose tables spell out a calculation.
PAGES = ["MEASURING.md", "MESURER.md", "GALLERY.md", "GALERIE.md"]

#: How close two floats have to be. A page rounds its operands to the digits a
#: reader can hold, so the product of the rounded operands is not the product of
#: the exact ones; one per cent is tight enough to catch a wrong figure and
#: loose enough to allow honest rounding.
TOLERANCE = 0.01

#: Everything a restricted expression can be made of. ``NUMBER`` comes first so
#: that the ``e`` of ``2.5e-06`` is part of the number rather than the start of
#: a unit, and a compound unit such as ``W/GB`` is one word rather than a
#: division nobody wrote.
TOKEN = re.compile(
    r"(?P<number>\d+(?:\.\d+)?(?:[eE][-+]?\d+)?)"
    r"|(?P<op>[-+*/()^])"
    r"|(?P<word>[A-Za-z]+(?:/[A-Za-z]+)*)"
    r"|(?P<space>\s+)"
)

#: The nameplate sum, as :func:`saggio.estimate.energy.node_power` writes it.
NAMEPLATE = re.compile(r"Nameplate sum[^:]*:\s*(?P<sum>[^.]+?)\s*$")

#: A projection's method, with or without a measured scaling exponent.
PROJECTION = re.compile(
    r"Whole run = measured slice / (?P<fraction>\d+(?:\.\d+)?(?:[eE][-+]?\d+)?)"
    r"(?:\^(?P<exponent>\d+(?:\.\d+)?))?\.\s*(?P<rest>.*)$"
)


def _normalise(text: str) -> str:
    """Return prose arithmetic with its typography turned into operators.

    Parameters
    ----------
    text : str
        A cell or a clause, in either language.

    Returns
    -------
    str
        The same text with the multiplication sign, the true minus sign and the
        French decimal comma replaced by what a parser can read.

    Examples
    --------
    >>> _normalise("0,198 × (17,44 − 13,83) W")
    '0.198 * (17.44 - 13.83) W'
    """
    for before, after in (("×", "*"), ("−", "-"), (" ", " "), (" ", " ")):
        text = text.replace(before, after)
    # The decimal comma, only between digits: a comma listing two figures is not
    # a decimal point, and turning it into one would silently glue them.
    return re.sub(r"(?<=\d),(?=\d)", ".", text)


def _tokens(text: str) -> list[str] | None:
    """Return an expression as tokens, or ``None`` when it is not one.

    Unit words are dropped — they say what the numbers are, not what to do with
    them — except a bare ``x``, which is how the nameplate note spells
    multiplication.

    Parameters
    ----------
    text : str
        Normalised text.

    Returns
    -------
    list of str or None
        Numbers and operators, or ``None`` when fewer than two numbers survive
        and there is therefore no calculation to check.

    Examples
    --------
    >>> _tokens("12 cores x 4.0 W + 96 GB x 0.3725 W/GB")
    ['12', '*', '4.0', '+', '96', '*', '0.3725']
    >>> _tokens("3.01 W") is None
    True
    """
    found: list[str] = []
    position = 0
    while position < len(text):
        match = TOKEN.match(text, position)
        if match is None:
            return None
        position = match.end()
        if match.group("number"):
            found.append(match.group("number"))
        elif match.group("op"):
            found.append(match.group("op"))
        elif match.group("word") == "x":
            found.append("*")
    if sum(1 for token in found if token not in "+-*/()^") < 2:
        return None
    return found


class _Reader:
    """A cursor over a token list, for the three rules below it."""

    def __init__(self, tokens: list[str]) -> None:
        self.tokens, self.at = tokens, 0

    def peek(self) -> str | None:
        """Return the next token without consuming it."""
        return self.tokens[self.at] if self.at < len(self.tokens) else None

    def take(self) -> str:
        """Consume the next token and return it."""
        token = self.tokens[self.at]
        self.at += 1
        return token


def _atom(reader: _Reader) -> float:
    """Read a number or a parenthesised expression."""
    token = reader.take()
    if token == "(":
        value = _sum(reader)
        if reader.peek() == ")":
            reader.take()
        return value
    if token == "-":
        return -_atom(reader)
    return float(token)


def _product(reader: _Reader) -> float:
    """Read a run of multiplications, divisions and powers."""
    value = _atom(reader)
    while reader.peek() in {"*", "/", "^"}:
        operator = reader.take()
        other = _atom(reader)
        if operator == "*":
            value *= other
        elif operator == "/":
            value /= other
        else:
            value **= other
    return value


def _sum(reader: _Reader) -> float:
    """Read a run of additions and subtractions."""
    value = _product(reader)
    while reader.peek() in {"+", "-"}:
        operator = reader.take()
        other = _product(reader)
        value = value + other if operator == "+" else value - other
    return value


def evaluate(text: str) -> float | None:
    """Return what a prose arithmetic comes to, or ``None``.

    Parameters
    ----------
    text : str
        A cell or a clause.

    Returns
    -------
    float or None
        The value, or ``None`` when the text holds no calculation or does not
        parse. ``None`` means *not checked*, never *correct*.

    Examples
    --------
    >>> evaluate("12 cores x 4.0 W + 96 GB x 0.3725 W/GB")
    83.75999999999999
    >>> round(evaluate("0,198 × (17,44 − 13,83) W"), 4)
    0.7148
    >>> evaluate("a sentence") is None
    True
    """
    tokens = _tokens(_normalise(text))
    if tokens is None:
        return None
    try:
        reader = _Reader(tokens)
        value = _sum(reader)
    except (ValueError, IndexError, ZeroDivisionError):
        return None
    return value if reader.at == len(tokens) else None


def _close(left: float, right: float) -> bool:
    """Return whether two figures agree to within the tolerance.

    Examples
    --------
    >>> _close(83.76, 83.75999999999999)
    True
    >>> _close(3.01, 0.72)
    False
    """
    if right == 0.0:
        return abs(left) < TOLERANCE
    return abs(left - right) / abs(right) <= TOLERANCE


@pytest.mark.parametrize("model", MODELS)
def test_a_nameplate_sum_adds_up_to_the_figure_it_explains(model: str) -> None:
    data = yaml.safe_load((ROOT / model).read_text(encoding="utf-8"))
    power = (data.get("assumptions") or {}).get("power_draw") or {}
    found = NAMEPLATE.search(str(power.get("notes") or ""))
    if found is None or not isinstance(power.get("value"), (int, float)):
        return
    total = evaluate(found.group("sum"))
    assert total is not None, f"{model}: the nameplate sum does not parse"
    assert _close(total, float(power["value"])), (
        f"{model}: the note adds to {total}, the model states {power['value']}"
    )


@pytest.mark.parametrize("model", MODELS)
def test_a_projection_divides_by_the_fraction_it_says_it_does(model: str) -> None:
    # The only place the divisor appears as a number: the model holds the run
    # size as a string and the fraction nowhere.
    data = yaml.safe_load((ROOT / model).read_text(encoding="utf-8"))
    scenario = (data.get("scenarios") or [{}])[0]
    costs = scenario.get("costs") or {}
    slices = {key: (value or {}).get("value") for key, value in costs.items()}
    # Collected rather than asserted one at a time: the first version stopped at
    # the first bad dimension and reported `money` on two models whose `carbon`
    # was wrong too. A sonde that hides half of what it found is half a sonde.
    offenders: list[str] = []
    for block, body in (data.get("projections") or {}).items():
        for dimension, projection in (body.get("costs") or {}).items():
            found = PROJECTION.match(str(projection.get("method") or ""))
            result = (projection.get("result") or {}).get("value")
            measured = slices.get(dimension)
            if found is None or not isinstance(result, (int, float)):
                continue
            if not isinstance(measured, (int, float)):
                offenders.append(f"{block}.{dimension} projects from a slice with no figure")
                continue
            divisor = float(found.group("fraction"))
            if found.group("exponent"):
                divisor **= float(found.group("exponent"))
            if _close(float(measured) / divisor, float(result)):
                continue
            offenders.append(
                f"{block}.{dimension} says slice / {found.group('fraction')}"
                f"{'^' + found.group('exponent') if found.group('exponent') else ''}, "
                f"which gives {float(measured) / divisor:.6g} and not {result:.6g} "
                f"(the model is out by {float(measured) / divisor / float(result):.4g}x)"
            )
    assert not offenders, f"{model}: " + "; ".join(offenders)


@pytest.mark.parametrize("page", PAGES)
def test_a_calculation_written_in_a_table_gives_the_answer_beside_it(page: str) -> None:
    offenders: list[str] = []
    for number, line in enumerate((ROOT / page).read_text(encoding="utf-8").splitlines(), 1):
        if not line.startswith("|") or set(line) <= set("|- "):
            continue
        cells = [cell.strip().strip("*") for cell in line.strip("|").split("|")]
        computed = [(index, evaluate(cell)) for index, cell in enumerate(cells)]
        stated = [
            (index, value)
            for index, cell in enumerate(cells)
            if (value := _single(cell)) is not None
        ]
        for index, total in computed:
            if total is None:
                continue
            answers = [value for position, value in stated if position > index]
            if not answers:
                continue
            if any(_close(total, value) for value in answers):
                continue
            offenders.append(
                f"{page}:{number}: {cells[index]!r} comes to {total:.6g}, "
                f"and the cell beside it says {answers[0]:.6g}"
            )
    assert not offenders, "\n".join(offenders)


def _single(cell: str) -> float | None:
    """Return a cell holding exactly one number, or ``None``.

    Parameters
    ----------
    cell : str
        One table cell, already stripped of emphasis.

    Returns
    -------
    float or None
        The number, or ``None`` when the cell holds none or holds several.

    Examples
    --------
    >>> _single("3.01 W")
    3.01
    >>> _single("0.198 x 15.18 W") is None
    True
    """
    numbers = re.findall(r"\d+(?:\.\d+)?(?:[eE][-+]?\d+)?", _normalise(cell))
    return float(numbers[0]) if len(numbers) == 1 else None
