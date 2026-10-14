"""
Which line of a corporate GHG inventory a cost belongs on.

Module summary
--------------
A cost model answers *what one unit of work costs*. A greenhouse-gas inventory
asks a different question about the same number: **whose emission is it, and
under which scope does the reporting organisation declare it?** The two are not
interchangeable, and the gap between them is where a perfectly good figure gets
filed under the wrong heading — or, more often, gets handed to a sustainability
team that has no way to place it and quietly leaves it out.

The placement is not a judgement call. The GHG Protocol settles it with one
fact: **who buys the electricity and owns the machine.** Run the code on
hardware the organisation owns and it bought the kilowatt-hour, so the
electricity is its scope 2 and the hardware its scope 3 category 2. Run it on
somebody's cloud and it bought a *service*; the same two emissions are that
vendor's scope 2 and 3.2, and reach the organisation as scope 3 category 1.
Nothing about the code changes, and the inventory line changes completely.

That fact lives in the providers catalogue as ``operated_by``, so the rule is
data rather than code, and a provider somebody registers this morning is placed
by the same rule as ``aws``. A provider that does not state it gets **no scope**
rather than a guessed one: the two answers differ by which company reports the
emission, and that is not something to infer from a name.

What this module will not do
----------------------------
**It does not produce a market-based scope 2 figure.** The grid intensities this
package carries are grid averages, which is the *location-based* method by
definition. The GHG Protocol requires dual reporting wherever contractual
instruments exist, and the market-based number is a different one, built from a
supplier-specific factor, the instruments the organisation holds, or its
market's residual mix. None of the three is derivable from anything here, so
the placement says so in words and reports no figure, which is the only honest
answer and is also the one a reviewer can act on.

**It does not place water.** Water is not a greenhouse gas and has no scope. It
is reported, under the European standards, somewhere else entirely.

Usage example
-------------
>>> from saggio.estimate.ghg import placement
>>> placement("carbon", "on-prem").label
'Scope 2'
>>> placement("carbon", "aws").label
'Scope 3, category 1 — purchased goods and services'
>>> placement("embodied_carbon", "on-prem").label
'Scope 3, category 2 — capital goods'
>>> placement("carbon", "a-provider-nobody-classified").scope is None
True

Author
------
Warith Harchaoui
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Final

from ..catalog.registry import Catalog

#: The standard that defines the three scopes and the two kinds of indirect
#: emission. Cited by every placement that names a scope at all.
GHG_PROTOCOL_CORPORATE: Final[str] = "https://ghgprotocol.org/corporate-standard"

#: The standard that defines the fifteen scope 3 categories, including the two
#: this package can land in: category 1 and category 2.
GHG_PROTOCOL_SCOPE3: Final[str] = "https://ghgprotocol.org/corporate-value-chain-scope-3-standard"

#: The guidance that requires scope 2 to be reported twice — once location-based,
#: once market-based — wherever contractual instruments are available. It is the
#: reason a location-based figure alone is an incomplete disclosure rather than a
#: wrong one.
GHG_PROTOCOL_SCOPE2: Final[str] = "https://ghgprotocol.org/scope-2-guidance"

#: What `operated_by` may say, and what each value means for an inventory.
OPERATED_BY_SELF: Final[str] = "self"
OPERATED_BY_VENDOR: Final[str] = "vendor"

#: What the carbon figure in this package is, in the words the guidance uses.
#: Written here rather than in a report, because it is a property of the
#: catalogue's method and not of any one rendering of it.
LOCATION_BASED: Final[str] = (
    "location-based: a grid-average emission factor for the country, carrying no "
    "adjustment for any contractual instrument"
)

#: Why the other half of the required pair is absent, and what it would take.
#: A sustainability team reads this as a shopping list rather than as a refusal.
MARKET_BASED_MISSING: Final[str] = (
    "The market-based figure is a different number and is not here. It is built "
    "from your supplier's own emission factor, from the contractual instruments "
    "you hold — guarantees of origin, RECs, a PPA — or, failing both, from your "
    "market's residual mix. None of the three can be derived from a grid average, "
    "so this package reports neither a market-based figure nor a zero. Where "
    "contractual instruments exist in your market, the GHG Protocol requires both "
    "numbers, each labelled with the method that produced it."
)


@dataclass(frozen=True, slots=True)
class Placement:
    """Where one cost goes in a greenhouse-gas inventory, or why it cannot be said.

    Parameters
    ----------
    dimension : str
        The cost dimension this places.
    scope : str or None
        ``"1"``, ``"2"``, ``"3"``, or ``None`` when the inputs do not settle it.
        ``None`` is a real answer here, in the way a ``TODO`` quantity is: it
        says a human has to supply something before an inventory line exists.
    category : int or None
        The scope 3 category, where the scope is 3 and the category is known.
    label : str
        The heading a reader would write on the inventory line.
    why : str
        The sentence that justifies it, naming the fact it turned on.
    source_url : str
        The standard that settles it. Empty when nothing is being claimed.
    dual_reporting : str
        For a scope 2 placement, what the second required figure is and why it is
        not here. Empty for everything else.

    Examples
    --------
    >>> Placement("carbon", "2", None, "Scope 2", "because", "x", "").scope
    '2'
    """

    dimension: str
    scope: str | None
    category: int | None
    label: str
    why: str
    source_url: str
    dual_reporting: str = ""

    @property
    def is_open(self) -> bool:
        """Return whether this is a placement nobody can make yet.

        Examples
        --------
        >>> Placement("carbon", None, None, "", "", "").is_open
        True
        """
        return self.scope is None


#: The dimensions that are greenhouse-gas emissions at all. Money and time are
#: costs and not emissions; water is an emission of nothing and belongs to a
#: different standard. Listing them here rather than guessing from a unit keeps a
#: registered dimension in grams of something from being filed as carbon.
_EMISSIONS: Final[tuple[str, ...]] = ("carbon", "embodied_carbon")


#: Why a dimension that is not an emission has no scope. One sentence each,
#: because "not applicable" in a report reads as an omission rather than a fact.
_NOT_AN_EMISSION: Final[dict[str, str]] = {
    "money": "Money is a cost, not an emission. No scope applies.",
    "time": "Time is a cost, not an emission. No scope applies.",
    "energy": (
        "Energy is the activity datum the scope 2 or scope 3 figure is computed "
        "from, not an emission itself. Under the European standards it is "
        "disclosed on its own, as energy consumption, beside the emissions it "
        "produced."
    ),
    "water": (
        "Water is not a greenhouse gas and has no scope. The European standards "
        "disclose it under water and marine resources, not under climate change."
    ),
}


def _operated_by(provider: str | None, *, overlay: Any = None) -> str | None:
    """Return who runs the machines for a provider, or None when nobody said.

    Parameters
    ----------
    provider : str or None
        A providers-catalogue key.
    overlay : optional
        A user catalogue overlay, as the rest of the package passes one.

    Returns
    -------
    str or None
        ``"self"``, ``"vendor"``, or ``None`` when the row is absent or silent.

    Examples
    --------
    >>> _operated_by("gcp")
    'vendor'
    >>> _operated_by("not-a-provider") is None
    True
    >>> _operated_by(None) is None
    True
    """
    if not provider:
        return None
    try:
        row = Catalog.load("providers", overlay=overlay).row("providers", provider)
    except (KeyError, FileNotFoundError, ValueError):
        return None
    if not isinstance(row, dict):
        return None
    said = row.get("operated_by")
    return said if said in (OPERATED_BY_SELF, OPERATED_BY_VENDOR) else None


def placement(dimension: str, provider: str | None, *, overlay: Any = None) -> Placement:
    """Return where one dimension's figure goes in a GHG inventory.

    Parameters
    ----------
    dimension : str
        A cost dimension's key.
    provider : str or None
        The deployment's provider, as the model states it.
    overlay : optional
        A user catalogue overlay.

    Returns
    -------
    Placement
        A scope, or an open placement saying what is missing.

    Examples
    --------
    >>> placement("energy", "aws").scope is None
    True
    >>> placement("energy", "aws").why.startswith("Energy is the activity datum")
    True
    >>> placement("embodied_carbon", "gcp").category
    1
    >>> "residual mix" in placement("carbon", "on-prem").dual_reporting
    True
    """
    if dimension in _NOT_AN_EMISSION:
        return Placement(dimension, None, None, "No scope", _NOT_AN_EMISSION[dimension], "")
    if dimension not in _EMISSIONS:
        return Placement(
            dimension,
            None,
            None,
            "No scope",
            (
                f"{dimension!r} is a dimension this project registered. Whether it "
                "is a greenhouse gas, and under which scope, is a question about "
                "your dimension rather than about this package, which will not "
                "guess at it from a unit."
            ),
            "",
        )

    runs_on = _operated_by(provider, overlay=overlay)
    if runs_on is None:
        return Placement(
            dimension,
            None,
            None,
            "No scope",
            (
                "The provider does not say who operates the machine, and that is "
                "the fact the scope turns on: the same emission is scope 2 on "
                "hardware you own and scope 3 category 1 on hardware you rent. "
                "Set `operated_by` on the provider's catalogue row — `self` or "
                "`vendor` — rather than letting this be inferred."
                if provider
                else "The model states no provider, and the scope turns on who "
                "operates the machine. Name one in `deployment.provider`."
            ),
            "",
        )

    if runs_on == OPERATED_BY_VENDOR:
        # Everything bought as a service lands in one category, whether it is the
        # electricity the vendor burned or the hardware it built: the
        # organisation did not buy either of them, it bought compute.
        return Placement(
            dimension,
            "3",
            1,
            "Scope 3, category 1 — purchased goods and services",
            (
                "The machine is operated by a vendor, so the organisation bought a "
                "service rather than electricity or hardware. This is the vendor's "
                "own scope 2 and scope 3 category 2; it reaches the organisation "
                "as the purchased service."
                + (
                    " Most providers publish no per-customer figure for the "
                    "hardware share, so a vendor invoice will rarely contain this "
                    "number: it is the one the model beside it computes."
                    if dimension == "embodied_carbon"
                    else ""
                )
            ),
            GHG_PROTOCOL_SCOPE3,
        )

    if dimension == "embodied_carbon":
        return Placement(
            dimension,
            "3",
            2,
            "Scope 3, category 2 — capital goods",
            (
                "The organisation operates the machine, so it bought the hardware. "
                "Capital goods rather than purchased goods and services, because "
                "the asset's useful life is longer than a year — which is the "
                "distinction the standard draws between the two categories, and "
                "also the reason this figure is amortised rather than counted once."
            ),
            GHG_PROTOCOL_SCOPE3,
        )

    return Placement(
        dimension,
        "2",
        None,
        "Scope 2",
        (
            "The organisation operates the machine, so it bought the electricity. "
            f"The figure here is {LOCATION_BASED}."
        ),
        GHG_PROTOCOL_SCOPE2,
        MARKET_BASED_MISSING,
    )


def placements(
    dimensions: list[str] | tuple[str, ...],
    provider: str | None,
    *,
    overlay: Any = None,
) -> dict[str, Placement]:
    """Place every dimension of a model at once, in the order given.

    Parameters
    ----------
    dimensions : list or tuple of str
        The dimension keys the model reports.
    provider : str or None
        The deployment's provider.
    overlay : optional
        A user catalogue overlay.

    Returns
    -------
    dict
        Dimension key to its placement.

    Examples
    --------
    >>> found = placements(["carbon", "embodied_carbon", "water"], "on-prem")
    >>> [found[key].label for key in found]
    ['Scope 2', 'Scope 3, category 2 — capital goods', 'No scope']
    """
    return {key: placement(key, provider, overlay=overlay) for key in dimensions}
