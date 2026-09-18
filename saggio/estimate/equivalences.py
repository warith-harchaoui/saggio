"""
Equivalences: carbon restated in terms a reader already has a feel for.

Module summary
--------------
A figure in grams of CO2 equivalent is exact and means nothing to most readers.
The Green Algorithms paper (Lannelongue, Grealey, and Inouye, Advanced Science,
2021) contextualises it three ways, and this module implements all three with the
paper's own coefficients: months of carbon sequestration by a mature tree,
kilometres driven in an average passenger car, and the fraction of a reference
flight, per passenger, in economy.

An equivalence is a restatement, not a new measurement, so it obeys the same
honesty rules as everything else here. Each result carries the weakest-link
status of the carbon it restates, capped at ``estimated`` because the conversion
factor is itself a published average, and a carbon figure that is still ``TODO``
gives an equivalence that is still ``TODO``. Nothing becomes more convincing by
being turned into trees.

Usage example
-------------
>>> from saggio.estimate.equivalences import tree_months, car_km, flight_fraction
>>> from saggio.model import Quantity
>>> carbon = Quantity(value=50_000.0, unit="gCO2e", status="estimated")
>>> round(tree_months(carbon).value, 1)
54.5
>>> round(car_km(carbon).value, 0)
286.0
>>> round(flight_fraction(carbon, "paris-london").value, 1)
1.0

Author
------
Warith Harchaoui
"""

from __future__ import annotations

from typing import Final

from ..model.quantity import Quantity
from ..model.taxonomy import ESTIMATED, TODO, weakest

#: The published source for every coefficient in this module.
GREEN_ALGORITHMS_SOURCE: Final[str] = "https://doi.org/10.1002/advs.202100707"

#: Grams of CO2 a mature tree sequesters in one month. The paper estimates a
#: mature tree at roughly 11 kg of CO2 per year, giving a tree-month a value
#: close to 1 kg (11000 / 12 ~ 917 g). Species, age, and climate move this a
#: lot; it is an order-of-magnitude anchor, not a forestry model.
TREE_MONTH_GCO2: Final[float] = 11_000.0 / 12.0

#: Grams of CO2 equivalent per kilometre for an average passenger car, by
#: region: 175 gCO2e/km in Europe, 251 gCO2e/km in the United States.
CAR_GCO2_PER_KM: Final[dict[str, float]] = {"EU": 175.0, "US": 251.0}

#: Reference flights from the paper, per passenger in economy class:
#: total gCO2e for the trip. Jet aircraft emit 139-244 gCO2e per passenger
#: kilometre depending on the length of the flight, which these totals bake in.
FLIGHT_GCO2: Final[dict[str, float]] = {
    "paris-london": 50_000.0,
    "new-york-san-francisco": 570_000.0,
    "new-york-melbourne": 2_310_000.0,
}


def _restated(carbon: Quantity, factor_status: str = ESTIMATED) -> str:
    """Return the status an equivalence of this carbon figure may claim.

    Parameters
    ----------
    carbon : Quantity
        The carbon being restated.
    factor_status : str, optional
        The status of the conversion factor; published averages are
        ``estimated``.

    Returns
    -------
    str
        The weakest of the two, so a measured carbon figure still yields an
        ``estimated`` equivalence: the tree is an average tree.
    """
    return weakest(carbon.status, factor_status) or ESTIMATED


def _open(unit: str, why: str) -> Quantity:
    """Return a ``TODO`` equivalence naming what is missing."""
    return Quantity(unit=unit, status=TODO, notes=why)


def tree_months(carbon: Quantity) -> Quantity:
    """Restate a carbon figure as months of sequestration by one mature tree.

    Parameters
    ----------
    carbon : Quantity
        Grams of CO2 equivalent.

    Returns
    -------
    Quantity
        Tree-months, ``estimated`` at best, or a ``TODO`` when the carbon
        figure itself is still open.

    Examples
    --------
    >>> tree_months(Quantity(value=11_000.0, unit="gCO2e", status="measured")).value
    12.0
    >>> tree_months(Quantity(unit="gCO2e", status="TODO")).status
    'TODO'
    """
    if not carbon.is_known():
        return _open("tree-months", "The carbon figure is still open, so its restatement is too.")
    return Quantity(
        value=float(carbon.value) / TREE_MONTH_GCO2,
        unit="tree-months",
        status=_restated(carbon),
        source_url=GREEN_ALGORITHMS_SOURCE,
        notes=f"Carbon / {TREE_MONTH_GCO2:.0f} g per tree-month: a mature tree "
        "sequesters roughly 11 kg of CO2 a year.",
    )


def car_km(carbon: Quantity, region: str = "EU") -> Quantity:
    """Restate a carbon figure as kilometres driven in an average passenger car.

    Parameters
    ----------
    carbon : Quantity
        Grams of CO2 equivalent.
    region : str, optional
        ``"EU"`` (175 gCO2e/km) or ``"US"`` (251 gCO2e/km). The fleet differs
        enough that quoting one number for both would be wrong for each.

    Returns
    -------
    Quantity
        Kilometres, ``estimated`` at best, or a ``TODO`` when the carbon figure
        is still open.

    Raises
    ------
    ValueError
        If ``region`` is not one this module carries a factor for. A silent
        fallback would restate the carbon against the wrong fleet.

    Examples
    --------
    >>> car_km(Quantity(value=175.0, unit="gCO2e", status="estimated")).value
    1.0
    >>> round(car_km(Quantity(value=251.0, unit="gCO2e", status="estimated"), "US").value, 3)
    1.0
    """
    if region not in CAR_GCO2_PER_KM:
        known = ", ".join(sorted(CAR_GCO2_PER_KM))
        raise ValueError(f"No car emission factor for region {region!r}; have {known}.")
    if not carbon.is_known():
        return _open("km", "The carbon figure is still open, so its restatement is too.")
    factor = CAR_GCO2_PER_KM[region]
    return Quantity(
        value=float(carbon.value) / factor,
        unit="km",
        status=_restated(carbon),
        source_url=GREEN_ALGORITHMS_SOURCE,
        notes=f"Carbon / {factor:g} gCO2e per km, average passenger car, {region}.",
    )


def flight_fraction(carbon: Quantity, route: str = "paris-london") -> Quantity:
    """Restate a carbon figure as a fraction of a reference flight.

    The fraction is per passenger in economy class, and can exceed 1: a
    computation that emits three Paris-London flights reads as 3.0.

    Parameters
    ----------
    carbon : Quantity
        Grams of CO2 equivalent.
    route : str, optional
        One of ``"paris-london"``, ``"new-york-san-francisco"``,
        ``"new-york-melbourne"``, ordered short to long so a report can pick
        the one whose fraction lands nearest 1.

    Returns
    -------
    Quantity
        A dimensionless fraction of the named flight, ``estimated`` at best, or
        a ``TODO`` when the carbon figure is still open.

    Raises
    ------
    ValueError
        If ``route`` is not one of the reference flights.

    Examples
    --------
    >>> flight_fraction(Quantity(value=25_000.0, unit="gCO2e", status="estimated")).value
    0.5
    >>> flight_fraction(Quantity(value=570_000.0, unit="gCO2e", status="measured"),
    ...                 "new-york-san-francisco").value
    1.0
    """
    if route not in FLIGHT_GCO2:
        known = ", ".join(sorted(FLIGHT_GCO2))
        raise ValueError(f"No reference flight named {route!r}; have {known}.")
    if not carbon.is_known():
        return _open(
            f"flights {route}", "The carbon figure is still open, so its restatement is too."
        )
    total = FLIGHT_GCO2[route]
    return Quantity(
        value=float(carbon.value) / total,
        unit=f"flights {route}",
        status=_restated(carbon),
        source_url=GREEN_ALGORITHMS_SOURCE,
        notes=f"Carbon / {total:g} gCO2e for one passenger, economy, {route}.",
    )


def equivalences(carbon: Quantity) -> dict[str, Quantity]:
    """Return the full set of restatements for one carbon figure.

    The convenience a report wants: every equivalence at once, keyed by name,
    with the flight chosen as the shortest reference route whose fraction stays
    below one thousand percent, so the sentence stays readable.

    Parameters
    ----------
    carbon : Quantity
        Grams of CO2 equivalent.

    Returns
    -------
    dict of str to Quantity
        ``tree_months``, ``car_km``, and ``flight`` restatements. When the
        carbon is open they are all ``TODO``, so the report shows the gap
        instead of hiding the row.

    Examples
    --------
    >>> keys = sorted(equivalences(Quantity(value=1e6, unit="gCO2e", status="estimated")))
    >>> keys
    ['car_km', 'flight', 'tree_months']
    """
    chosen = "new-york-melbourne"
    for route in ("paris-london", "new-york-san-francisco", "new-york-melbourne"):
        if not carbon.is_known() or float(carbon.value) / FLIGHT_GCO2[route] <= 10.0:
            chosen = route
            break
    return {
        "tree_months": tree_months(carbon),
        "car_km": car_km(carbon),
        "flight": flight_fraction(carbon, chosen),
    }
