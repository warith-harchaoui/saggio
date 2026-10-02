"""
Checking that a derived number actually follows from the numbers it names.

Module summary
--------------
The central promise of a cost model here is that a derived value names its
inputs. The validator long checked that those names resolve, and that the value
does not claim to be better founded than the worst of them. It never checked the
one thing a reader assumes on seeing ``derived_from``: that the number *follows*
from those inputs.

It did not, and the gap had the worst possible shape. A number invented with no
derivation at all looks suspect. A number wrong by four orders of magnitude,
carrying a perfectly correct list of the inputs it supposedly came from, looks
better founded than anything else on the page.

How this works
--------------
Every unit is parsed into a scale and a set of base dimensions — joules, seconds,
grams of CO2 equivalent, litres, bytes, and whatever currency a model names.
``W`` is ``J/s``; ``kWh`` is 3.6 million joules; ``gCO2e/kWh`` is grams over
joules with the scale folded in.

Then the inputs are combined. Not only multiplied: a derivation may divide, which
is how the embodied-carbon formula amortises a footprint over a lifetime. So
every assignment of each input to numerator or denominator is tried, and the
answer depends on how many of them land on the stated unit:

- **exactly one** — the relationship is unambiguous, so the value is recomputed
  and a disagreement beyond a tolerance is an error;
- **more than one** — the units cannot tell which was meant, so nothing is said
  about the value;
- **none, and every unit is one this module knows** — no arrangement of these
  inputs can produce that unit, which is an error about the unit itself and
  needs no arithmetic at all;
- **none, and some unit is not known here** — somebody else's dimension, and
  none of this module's business.

That last case is the important one. A tool that invented a rule for a dimension
it had never heard of would be doing exactly what this package exists to refuse.

Usage example
-------------
>>> from saggio.model.derivation import combine, unreachable
>>> combine([(3600.0, "s"), (400.0, "W")], "kWh")
0.4
>>> unreachable([(1.0, "s"), (1.2, "ratio")], "gCO2e") is not None
True

Author
------
Warith Harchaoui
"""

from __future__ import annotations

import itertools
import re
from collections import Counter
from typing import Final

#: How far a stated value may sit from the recomputed one before it is wrong, as
#: a fraction. One percent is loose enough for a model whose numbers were rounded
#: on the way into YAML, and tight enough that the error this exists to catch — a
#: factor of ten thousand — cannot hide in it.
TOLERANCE: Final[float] = 0.01

#: Units that mean "a plain number" and carry no dimension at all.
DIMENSIONLESS: Final[frozenset[str]] = frozenset({"ratio", "", "1", "x", "factor", "percent"})

#: Every unit this module claims to understand, as a scale onto base dimensions.
#: The bases are joules, seconds, grams of CO2 equivalent, litres and bytes;
#: anything else a model writes is treated as an atom of its own and makes the
#: whole comparison fall silent, which is the intended behaviour for a dimension
#: this package has never heard of.
_UNITS: Final[dict[str, tuple[float, dict[str, int]]]] = {
    # Time.
    "s": (1.0, {"s": 1}),
    "sec": (1.0, {"s": 1}),
    "secs": (1.0, {"s": 1}),
    "second": (1.0, {"s": 1}),
    "seconds": (1.0, {"s": 1}),
    "min": (60.0, {"s": 1}),
    "mins": (60.0, {"s": 1}),
    "minute": (60.0, {"s": 1}),
    "minutes": (60.0, {"s": 1}),
    "h": (3600.0, {"s": 1}),
    "hr": (3600.0, {"s": 1}),
    "hour": (3600.0, {"s": 1}),
    "hours": (3600.0, {"s": 1}),
    "d": (86_400.0, {"s": 1}),
    "day": (86_400.0, {"s": 1}),
    "days": (86_400.0, {"s": 1}),
    # A year here is the Julian year the rest of the package amortises over.
    "y": (31_557_600.0, {"s": 1}),
    "yr": (31_557_600.0, {"s": 1}),
    "year": (31_557_600.0, {"s": 1}),
    "years": (31_557_600.0, {"s": 1}),
    # Energy and power. A watt is a joule per second, which is what lets seconds
    # times watts come out as energy without a special case for it.
    "J": (1.0, {"J": 1}),
    "kJ": (1_000.0, {"J": 1}),
    "MJ": (1_000_000.0, {"J": 1}),
    "Wh": (3_600.0, {"J": 1}),
    "kWh": (3_600_000.0, {"J": 1}),
    "MWh": (3_600_000_000.0, {"J": 1}),
    "GWh": (3_600_000_000_000.0, {"J": 1}),
    "W": (1.0, {"J": 1, "s": -1}),
    "kW": (1_000.0, {"J": 1, "s": -1}),
    "MW": (1_000_000.0, {"J": 1, "s": -1}),
    # Carbon dioxide equivalent.
    "gCO2e": (1.0, {"gCO2e": 1}),
    "kgCO2e": (1_000.0, {"gCO2e": 1}),
    "tCO2e": (1_000_000.0, {"gCO2e": 1}),
    # Water.
    "L": (1.0, {"L": 1}),
    "mL": (0.001, {"L": 1}),
    "m3": (1_000.0, {"L": 1}),
    # Data.
    "B": (1.0, {"B": 1}),
    "kB": (1_000.0, {"B": 1}),
    "MB": (1_000_000.0, {"B": 1}),
    "GB": (1_000_000_000.0, {"B": 1}),
    "TB": (1_000_000_000_000.0, {"B": 1}),
}

#: An ISO 4217 code, which a model writes as a money unit. Treated as a base
#: dimension of its own: dollars are not convertible into euros by multiplying.
_CURRENCY: Final[re.Pattern[str]] = re.compile(r"^[A-Z]{3}$")

#: A unit written as "something per something", which is how every intensity in
#: this package is spelled: gCO2e/kWh, USD/kWh, L/kWh.
_PER: Final[re.Pattern[str]] = re.compile(r"^([^/]+)/([^/]+)$")


def _tidy(dimensions: Counter[str]) -> Counter[str]:
    """Return the dimensions with the zero exponents dropped and the rest kept.

    Not ``+counter``: unary plus on a :class:`~collections.Counter` drops every
    non-positive entry, which silently deletes a denominator. ``gCO2e/kWh``
    parsed that way comes out as grams of CO2 equivalent, and an intensity that
    has lost its denominator compares equal to a mass.

    Parameters
    ----------
    dimensions : collections.Counter
        Base dimensions with their exponents.

    Returns
    -------
    collections.Counter
        The same, without the exponents that cancelled to zero.

    Examples
    --------
    >>> sorted(_tidy(Counter({"gCO2e": 1, "J": -1, "s": 0})).items())
    [('J', -1), ('gCO2e', 1)]
    """
    return Counter({base: exponent for base, exponent in dimensions.items() if exponent})


def parse_unit(unit: str | None) -> tuple[float, Counter[str]] | None:
    """Return a unit as a scale onto base dimensions, or ``None`` if unknown.

    Parameters
    ----------
    unit : str or None
        As written in the model.

    Returns
    -------
    tuple or None
        ``(scale, dimensions)`` where multiplying a value by ``scale`` expresses
        it in the base units counted by ``dimensions``. ``None`` when any part of
        the unit is not one this module knows.

    Examples
    --------
    >>> scale, dimensions = parse_unit("kWh")
    >>> scale, dict(dimensions)
    (3600000.0, {'J': 1})
    >>> scale, dimensions = parse_unit("W")
    >>> scale, sorted(dimensions.items())
    (1.0, [('J', 1), ('s', -1)])
    >>> scale, dimensions = parse_unit("gCO2e/kWh")
    >>> round(scale, 12), sorted(dimensions.items())
    (2.77778e-07, [('J', -1), ('gCO2e', 1)])
    >>> parse_unit("ratio")
    (1.0, Counter())
    >>> parse_unit("furlong") is None
    True
    """
    name = (unit or "").strip()
    if name in DIMENSIONLESS:
        return 1.0, Counter()
    per = _PER.match(name)
    if per:
        numerator = parse_unit(per.group(1))
        denominator = parse_unit(per.group(2))
        if numerator is None or denominator is None or denominator[0] == 0.0:
            return None
        dimensions = Counter(numerator[1])
        dimensions.subtract(denominator[1])
        return numerator[0] / denominator[0], _tidy(dimensions)
    if name in _UNITS:
        scale, dimensions = _UNITS[name]
        return scale, Counter(dimensions)
    if _CURRENCY.match(name):
        return 1.0, Counter({name: 1})
    return None


def _arrangements(
    parsed: list[tuple[float, Counter[str]]], target: tuple[float, Counter[str]]
) -> list[float]:
    """Return the value each way of combining the inputs would give.

    Each input is tried as a multiplier and as a divisor, because a derivation
    may divide — amortising a footprint over a lifetime is a division, and the
    model names the lifetime among its inputs just the same.

    Parameters
    ----------
    parsed : list of tuple
        Each input as ``(value times its scale, dimensions)``.
    target : tuple
        The claimed unit, parsed the same way.

    Returns
    -------
    list of float
        The distinct values, in the claimed unit, of every arrangement whose
        dimensions match the target. Empty when none match.

    Examples
    --------
    >>> seconds = (3600.0, Counter({"s": 1}))
    >>> watts = (400.0, Counter({"J": 1, "s": -1}))
    >>> _arrangements([seconds, watts], (3_600_000.0, Counter({"J": 1})))
    [0.4]
    """
    target_scale, target_dimensions = target

    # The product comes first, and when it lands on the claimed unit it is the
    # reading: a derivation multiplies unless it cannot. Without this, every
    # dimensionless input would be ambiguous — energy times a facility overhead
    # could as well be energy divided by it — and the most common derivation in
    # this package would stop being checked exactly.
    product: Counter[str] = Counter()
    straight = 1.0
    for magnitude, dims in parsed:
        straight *= magnitude
        product.update(dims)
    if _tidy(product) == _tidy(target_dimensions):
        return [straight / target_scale]

    matches: list[float] = []
    for signs in itertools.product((1, -1), repeat=len(parsed)):
        dimensions: Counter[str] = Counter()
        value = 1.0
        ok = True
        for (magnitude, dims), sign in zip(parsed, signs, strict=True):
            if sign == -1 and magnitude == 0.0:
                ok = False
                break
            value *= magnitude if sign == 1 else 1.0 / magnitude
            for base, exponent in dims.items():
                dimensions[base] += exponent * sign
        if not ok:
            continue
        if _tidy(dimensions) == _tidy(target_dimensions):
            matches.append(value / target_scale)
    # Arrangements that differ only in a dimensionless input's placement give the
    # same number; those are not an ambiguity, they are the same answer twice.
    distinct: list[float] = []
    for value in matches:
        if not any(abs(value - seen) <= abs(seen) * 1e-9 for seen in distinct):
            distinct.append(value)
    return distinct


def candidates(inputs: list[tuple[float, str | None]], unit: str | None) -> list[float] | None:
    """Return every value the inputs could give in the claimed unit.

    The general form, and the one the validator uses. Where exactly one
    arrangement produces the claimed unit the answer is a single value; where
    several do, all of them are returned, because a stated value matching *none*
    of them is wrong under every reading of the derivation, and that is worth
    saying even when the units cannot tell which reading was meant.

    Parameters
    ----------
    inputs : list of (float, str or None)
        Each input's value and unit.
    unit : str or None
        The unit the derived value claims.

    Returns
    -------
    list of float, or None
        The candidate values; an **empty list** when no arrangement produces the
        claimed unit at all; ``None`` when some unit here is not one this module
        knows, which is somebody else's dimension and not its business.

    Examples
    --------
    >>> candidates([(3600.0, "s"), (400.0, "W")], "kWh")
    [0.4]

    Amortising a footprint over a lifetime: the units cannot say whether the
    lifetime multiplies or divides, so both readings come back. Neither is
    anywhere near a number that is wrong by five orders of magnitude.

    >>> values = candidates([(164.0, "kgCO2e"), (4.0, "years"), (1.0, "h")], "gCO2e")
    >>> len(values), round(min(values), 3)
    (2, 4.677)

    >>> candidates([(1.0, "s"), (1.2, "ratio")], "gCO2e")
    []
    >>> candidates([(1.0, "furlong")], "gCO2e") is None
    True
    """
    target = parse_unit(unit)
    if target is None or not inputs:
        return None
    parsed: list[tuple[float, Counter[str]]] = []
    for value, raw in inputs:
        got = parse_unit(raw)
        if got is None:
            return None
        scale, dimensions = got
        parsed.append((float(value) * scale, dimensions))
    return _arrangements(parsed, target)


def combine(inputs: list[tuple[float, str | None]], unit: str | None) -> float | None:
    """Return what the inputs give in the claimed unit, when that is unambiguous.

    Parameters
    ----------
    inputs : list of (float, str or None)
        Each input's value and unit, in the order the model names them.
    unit : str or None
        The unit the derived value claims.

    Returns
    -------
    float or None
        The value, or ``None`` when this cannot tell — because a unit is not one
        it knows, because no arrangement produces the claimed unit, or because
        more than one does and the units cannot say which was meant.

    Examples
    --------
    An hour at four hundred watts, which needs no special case: a watt is a
    joule per second, so seconds times watts are joules.

    >>> combine([(3600.0, "s"), (400.0, "W")], "kWh")
    0.4

    A facility multiplier, an intensity, and a price:

    >>> combine([(0.4, "kWh"), (1.2, "ratio")], "kWh")
    0.48
    >>> round(combine([(0.48, "kWh"), (56.0, "gCO2e/kWh")], "gCO2e"), 4)
    26.88
    >>> round(combine([(0.48, "kWh"), (0.24, "USD/kWh")], "USD"), 4)
    0.1152

    A division, which is how an embodied footprint is amortised, is where the
    units stop being able to tell: an hour out of a four-year life divides, but
    nothing in ``years`` says so rather than multiplying. This says nothing, and
    :func:`candidates` is the one that still catches a wrong number there.

    >>> combine([(164.0, "kgCO2e"), (4.0, "years"), (1.0, "h")], "gCO2e") is None
    True
    >>> round(min(candidates([(164.0, "kgCO2e"), (4.0, "years"), (1.0, "h")], "gCO2e")), 3)
    4.677

    And the three ways of saying nothing:

    >>> combine([(1.0, "s"), (1.2, "ratio")], "gCO2e") is None
    True
    >>> combine([(1.0, "furlong")], "fortnight") is None
    True
    >>> combine([(2.0, "s"), (3.0, "s")], "s") is None   # ambiguous: x3 or /3
    True
    """
    target = parse_unit(unit)
    if target is None or not inputs:
        return None
    parsed: list[tuple[float, Counter[str]]] = []
    for value, raw in inputs:
        got = parse_unit(raw)
        if got is None:
            return None
        scale, dimensions = got
        parsed.append((float(value) * scale, dimensions))
    matches = _arrangements(parsed, target)
    return matches[0] if len(matches) == 1 else None


def unreachable(inputs: list[tuple[float, str | None]], unit: str | None) -> str | None:
    """Return why the claimed unit cannot come from these inputs, or ``None``.

    The half of the problem that needs no arithmetic. Recomputing a value needs
    the whole relationship; ruling one out needs only the dimensions, and it
    stays decidable however many inputs there are.

    Speaks only when every unit involved is one this module knows. An unknown
    unit is somebody else's dimension, and asserting an impossibility about it
    would be inventing a rule.

    Parameters
    ----------
    inputs : list of (float, str or None)
        Each input's value and unit.
    unit : str or None
        The unit the derived value claims.

    Returns
    -------
    str or None
        A sentence naming the impossibility, or ``None``.

    Examples
    --------
    >>> unreachable([(1.0, "s"), (1.2, "ratio")], "gCO2e")
    'no way of multiplying and dividing s and ratio gives gCO2e'
    >>> unreachable([(1.0, "kWh"), (56.0, "gCO2e/kWh")], "gCO2e") is None
    True
    >>> unreachable([(164.0, "kgCO2e"), (4.0, "years"), (1.0, "h")], "gCO2e") is None
    True
    >>> unreachable([(1.0, "furlong")], "gCO2e") is None
    True
    """
    target = parse_unit(unit)
    if target is None or not inputs:
        return None
    parsed: list[tuple[float, Counter[str]]] = []
    for value, raw in inputs:
        got = parse_unit(raw)
        if got is None:
            return None
        scale, dimensions = got
        parsed.append((float(value) * scale, dimensions))
    if _arrangements(parsed, target):
        return None
    written = " and ".join((raw or "").strip() or "no unit" for _, raw in inputs)
    return f"no way of multiplying and dividing {written} gives {(unit or '').strip()}"


def disagrees(stated: float, expected: float, *, tolerance: float = TOLERANCE) -> bool:
    """Return whether a stated value is too far from the recomputed one.

    Compared relatively, because these models span from microgrammes to
    megawatt-hours and an absolute tolerance would be meaningless at one end and
    useless at the other.

    Parameters
    ----------
    stated : float
        What the model says.
    expected : float
        What its own inputs give.
    tolerance : float, optional
        Allowed relative difference.

    Returns
    -------
    bool
        True when the two do not agree.

    Examples
    --------
    >>> disagrees(0.4, 0.4)
    False
    >>> disagrees(0.401, 0.4)
    False
    >>> disagrees(0.00004, 0.4)
    True
    >>> disagrees(0.0, 0.0)
    False
    """
    if expected == 0.0:
        return abs(stated) > tolerance
    return abs(stated - expected) / abs(expected) > tolerance
