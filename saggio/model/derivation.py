"""
Checking that a derived number actually follows from the numbers it names.

Module summary
--------------
The central promise of a cost model here is that a derived value names its
inputs. Until now the validator checked that those names resolve, and that the
value does not claim to be better founded than the worst of them. It never
checked the one thing a reader assumes on seeing ``derived_from``: that the
number *follows* from those inputs.

It did not, and the gap was the worst shape a gap can take. A number invented
with no derivation at all looks suspect. A number that is wrong by four orders of
magnitude, carrying a perfectly correct list of the inputs it supposedly came
from, looks better founded than anything else on the page.

So this module multiplies the inputs back together and compares. It can only do
that where it recognises the relationship, and it recognises it **by units**
rather than by field name, because a project that registers a dimension of its
own gets the same checking as carbon rather than a special case:

- seconds times watts give kilowatt-hours, over 3 600 000;
- kilowatt-hours times a dimensionless ratio give kilowatt-hours;
- kilowatt-hours times anything *per* kilowatt-hour give that anything.

Where the units do combine, the value is recomputed and a disagreement beyond a
tolerance is an error. Where they cannot possibly combine to the unit that was
written — seconds times a ratio can never be grams of CO2 — that is an error too,
and a cheaper one to be sure of. And where the relationship is simply not one of
these, this says **nothing at all**. A dimension somebody registered this morning
must not become an error because this module has not heard of it.

Usage example
-------------
>>> from saggio.model.derivation import combine
>>> combine([(3600.0, "s"), (400.0, "W")], "kWh")
0.4
>>> combine([(1.0, "s"), (1.2, "ratio")], "gCO2e") is None
True

Author
------
Warith Harchaoui
"""

from __future__ import annotations

import re
from typing import Final

#: How far a stated value may sit from the recomputed one before it is wrong, as
#: a fraction. One percent is loose enough for a model whose numbers were rounded
#: on the way into YAML, and tight enough that the error this exists to catch —
#: a factor of ten thousand — cannot hide in it.
TOLERANCE: Final[float] = 0.01

#: Seconds times watts give joules; this is joules per kilowatt-hour.
_JOULES_PER_KWH: Final[float] = 3_600_000.0

#: Units that mean "a plain number", and therefore multiply without changing the
#: unit of whatever they multiply.
_DIMENSIONLESS: Final[frozenset[str]] = frozenset({"ratio", "", "1", "x", "factor"})

#: A unit written as "something per something", which is how every intensity in
#: this package is spelled: gCO2e/kWh, USD/kWh, L/kWh.
_PER: Final[re.Pattern[str]] = re.compile(r"^(?P<numerator>[^/]+)/(?P<denominator>[^/]+)$")


def _normalise(unit: str | None) -> str:
    """Return a unit in the one spelling this module compares against.

    Parameters
    ----------
    unit : str or None
        As written in the model.

    Returns
    -------
    str
        Stripped, with the case left alone — ``W`` and ``Wh`` differ by case in
        the second letter and lowercasing them would make them the same.

    Examples
    --------
    >>> _normalise("  kWh ")
    'kWh'
    >>> _normalise(None)
    ''
    """
    return (unit or "").strip()


#: What kind of quantity a unit measures. Only the ones this package deals in,
#: and only where the answer is not in doubt. Two units of *different* kinds can
#: never be turned into one another by multiplying by a plain number, which is
#: the one impossibility worth asserting; two units of the *same* kind might be,
#: by a conversion this module does not do, so it stays quiet about those.
KIND_OF_UNIT: dict[str, str] = {
    "s": "time",
    "sec": "time",
    "min": "time",
    "h": "time",
    "d": "time",
    "years": "time",
    "W": "power",
    "kW": "power",
    "J": "energy",
    "Wh": "energy",
    "kWh": "energy",
    "MWh": "energy",
    "gCO2e": "carbon",
    "kgCO2e": "carbon",
    "tCO2e": "carbon",
    "L": "volume",
    "m3": "volume",
    "B": "data",
    "GB": "data",
    "TB": "data",
}


def unreachable(inputs: list[tuple[float, str | None]], unit: str | None) -> str | None:
    """Return why the claimed unit cannot come from these inputs, or ``None``.

    The decidable half of the problem. Recomputing a value needs the whole
    relationship; ruling one out often needs only the units. A single quantity
    multiplied by dimensionless numbers keeps its kind, so a derivation from a
    duration alone can give a duration and never a mass of carbon dioxide.

    Deliberately narrow. It speaks only when exactly one input carries a unit,
    both kinds are known, and they differ. Two units of the same kind might be
    related by a conversion this does not perform; three or more inputs are a
    relationship it does not claim to understand; an unknown unit is somebody
    else's dimension and none of its business.

    Parameters
    ----------
    inputs : list of (float, str or None)
        Each input's value and unit.
    unit : str or None
        The unit the derived value claims.

    Returns
    -------
    str or None
        A sentence naming the impossibility, or ``None`` when there is none to
        assert.

    Examples
    --------
    >>> unreachable([(1.0, "s"), (1.2, "ratio")], "gCO2e")
    'time multiplied by a plain number gives time, never carbon'
    >>> unreachable([(1.0, "s")], "min") is None
    True
    >>> unreachable([(1.0, "kWh"), (56.0, "gCO2e/kWh")], "gCO2e") is None
    True
    >>> unreachable([(1.0, "furlong")], "fortnight") is None
    True
    """
    wanted = _normalise(unit)
    carrying = [
        (value, _normalise(raw)) for value, raw in inputs if _normalise(raw) not in _DIMENSIONLESS
    ]
    if len(carrying) != 1 or not wanted:
        return None
    source = carrying[0][1]
    if source == wanted:
        return None
    from_kind, to_kind = KIND_OF_UNIT.get(source), KIND_OF_UNIT.get(wanted)
    if from_kind is None or to_kind is None or from_kind == to_kind:
        return None
    return f"{from_kind} multiplied by a plain number gives {from_kind}, never {to_kind}"


def combine(inputs: list[tuple[float, str | None]], unit: str | None) -> float | None:
    """Return what the inputs multiply to, when their units allow it.

    Parameters
    ----------
    inputs : list of (float, str or None)
        Each input's value and unit, in the order the model names them.
    unit : str or None
        The unit the derived value claims.

    Returns
    -------
    float or None
        The product, or ``None`` when this does not recognise the combination —
        which is the ordinary answer, not a failure. Only a relationship this
        module is sure of gets checked; the rest is left to the humans who wrote
        it.

    Examples
    --------
    An hour at four hundred watts:

    >>> combine([(3600.0, "s"), (400.0, "W")], "kWh")
    0.4

    A facility multiplier leaves the unit alone:

    >>> combine([(0.4, "kWh"), (1.2, "ratio")], "kWh")
    0.48

    An intensity cancels the kilowatt-hours and leaves its numerator:

    >>> round(combine([(0.48, "kWh"), (56.0, "gCO2e/kWh")], "gCO2e"), 4)
    26.88

    Order does not matter:

    >>> round(combine([(56.0, "gCO2e/kWh"), (0.48, "kWh")], "gCO2e"), 4)
    26.88

    One input is an identity, which is how a cost restates a runtime:

    >>> combine([(3600.0, "s")], "s")
    3600.0

    And everything else is not this module's business:

    >>> combine([(1.0, "s"), (1.2, "ratio")], "gCO2e") is None
    True
    >>> combine([(1.0, "furlong")], "fortnight") is None
    True
    """
    wanted = _normalise(unit)
    if not inputs or not wanted:
        return None

    scalars = 1.0
    carrying: list[tuple[float, str]] = []
    for value, raw in inputs:
        name = _normalise(raw)
        if name in _DIMENSIONLESS:
            scalars *= float(value)
        else:
            carrying.append((float(value), name))

    if not carrying:
        return None

    if len(carrying) == 1:
        value, name = carrying[0]
        return value * scalars if name == wanted else None

    if len(carrying) != 2:
        # Three or more units is a relationship this does not claim to know.
        return None

    (first_value, first_unit), (second_value, second_unit) = carrying

    # Seconds times watts, in either order, give kilowatt-hours.
    for left, right in ((carrying[0], carrying[1]), (carrying[1], carrying[0])):
        if left[1] == "s" and right[1] == "W" and wanted == "kWh":
            return left[0] * right[0] / _JOULES_PER_KWH * scalars

    # Something times something-per-that-something leaves the numerator.
    for left, right in ((carrying[0], carrying[1]), (carrying[1], carrying[0])):
        match = _PER.match(right[1])
        if match and match.group("denominator").strip() == left[1]:
            if match.group("numerator").strip() == wanted:
                return left[0] * right[0] * scalars
            # The units do combine, but not to what was claimed. Saying nothing
            # here would let a kilowatt-hour times a price be labelled grams.
            return None

    return None


def disagrees(stated: float, expected: float, *, tolerance: float = TOLERANCE) -> bool:
    """Return whether a stated value is too far from the recomputed one.

    Compared relatively, because the values in these models span from
    microgrammes to megawatt-hours and an absolute tolerance would be meaningless
    at one end and useless at the other.

    Parameters
    ----------
    stated : float
        What the model says.
    expected : float
        What its own inputs multiply to.
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
