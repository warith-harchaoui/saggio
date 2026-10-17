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

The other half of scope 2
-------------------------
The grid intensities this package carries are grid averages, which is the
*location-based* method by definition. The GHG Protocol requires scope 2 to be
reported both ways wherever contractual instruments exist, and the market-based
number is a different one: a supplier-specific factor, the instruments the
organisation holds, or its market's residual mix.

**None of the three is derivable from a grid average, so this package will never
compute one from what it knows.** What it does instead is carry the second
figure as a dimension of its own, ``carbon_market_based``, computed from a
factor the organisation states — the one fact only it has. State the factor and
both halves are reported, each labelled with the method that produced it; state
nothing and the placement prints the shopping list rather than a plausible
number. A market-based figure is a claim about contracts, so the validator asks
for the document it rests on in a way it does not ask of a grid average: nobody
else can check this one, and nothing in this package can refresh it.

**It does not place water.** Water is not a greenhouse gas and has no scope. It
is reported, under the European standards, somewhere else entirely.

Usage example
-------------
>>> from saggio.estimate.ghg import placement
>>> placement("carbon", "on-prem").label
'Scope 2 (location-based)'
>>> placement("carbon_market_based", "on-prem").label
'Scope 2 (market-based)'
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

from collections import Counter
from dataclasses import dataclass
from typing import Any, Final

from ..catalog.registry import Catalog
from ..model.cost_model import CostModel

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

#: What the market-based figure is, in the same shape as the line above, for the
#: half of the pair that comes from a contract rather than from a grid.
MARKET_BASED: Final[str] = (
    "market-based: the emission factor of the electricity this organisation "
    "contracted for, rather than the average of the grid it drew from"
)

#: Where a market-based factor may honestly come from, in the order the Scope 2
#: Guidance puts them. Printed when the figure is missing, so the sentence is a
#: shopping list rather than a refusal, and kept in one place because the report,
#: the command and the model's own notes all say it.
MARKET_BASED_SOURCES: Final[str] = (
    "It is built from your supplier's own emission factor, from the contractual "
    "instruments you hold — guarantees of origin, RECs, a PPA — or, failing both, "
    "from your market's residual mix, which exists precisely so that unclaimed "
    "electricity is not counted as clean by default."
)

#: Why the other half of the required pair is absent, and what it would take.
#: A sustainability team reads this as a shopping list rather than as a refusal.
MARKET_BASED_MISSING: Final[str] = (
    "The market-based figure is a different number and is not here. "
    + MARKET_BASED_SOURCES
    + " None of the three can be derived from a grid average, so this package "
    "reports neither a market-based figure nor a zero. Record the factor as "
    "`assumptions.market_carbon_intensity` and the figure is computed and placed "
    "beside this one. Where contractual instruments exist in your market, the GHG "
    "Protocol requires both numbers, each labelled with the method that produced it."
)

#: The same slot, once the companion figure is actually in the model. It says
#: what the pair is for, because the commonest misuse of a market-based number
#: is to publish it alone — which is the one thing the guidance forbids.
MARKET_BASED_PRESENT: Final[str] = (
    "The market-based figure required beside this one is in the model, as "
    "`carbon_market_based`. Both are disclosed: the market-based number does not "
    "replace this one, and a contract does not change which electrons the grid "
    "delivered. Check that what you recorded meets the Scope 2 Guidance's quality "
    "criteria for a contractual instrument — this package cannot, and does not "
    "pretend to."
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
#: registered dimension in grams of something from being filed as carbon. Public
#: because the two reports pick their inventory rows from it, and a report that
#: kept its own copy would be a second list to forget to extend.
GHG_EMISSIONS: Final[tuple[str, ...]] = ("carbon", "carbon_market_based", "embodied_carbon")

#: The dimension that carries the market-based half of scope 2. Named once
#: because three things read it: the placement below, the sentence a
#: location-based placement prints about its companion, and the fold.
MARKET_BASED_DIMENSION: Final[str] = "carbon_market_based"


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


def operated_by(provider: str | None, *, overlay: Any = None) -> str | None:
    """Return who runs the machines for a provider, or None when nobody said.

    Public because the rule has a second reader: an audit decides whether to
    write a market-based row at all from the same fact, and two copies of a
    catalogue lookup would be two chances to disagree about a provider.

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
    >>> operated_by("gcp")
    'vendor'
    >>> operated_by("not-a-provider") is None
    True
    >>> operated_by(None) is None
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


def placement(
    dimension: str,
    provider: str | None,
    *,
    overlay: Any = None,
    market_based_reported: bool = False,
) -> Placement:
    """Return where one dimension's figure goes in a GHG inventory.

    Parameters
    ----------
    dimension : str
        A cost dimension's key.
    provider : str or None
        The deployment's provider, as the model states it.
    overlay : optional
        A user catalogue overlay.
    market_based_reported : bool, optional
        Whether the model also carries ``carbon_market_based``. It changes what a
        location-based scope 2 placement says about its companion: a shopping
        list when the pair is half there, a warning against publishing one
        without the other when it is whole. :func:`placements` works it out from
        the dimension list, so a caller placing a whole model never passes it.

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
    >>> placement("carbon", "on-prem", market_based_reported=True).dual_reporting[:3]
    'The'
    >>> placement("carbon_market_based", "on-prem").label
    'Scope 2 (market-based)'
    >>> placement("carbon_market_based", "aws").scope is None
    True
    """
    if dimension in _NOT_AN_EMISSION:
        return Placement(dimension, None, None, "No scope", _NOT_AN_EMISSION[dimension], "")
    if dimension not in GHG_EMISSIONS:
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

    runs_on = operated_by(provider, overlay=overlay)
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

    if runs_on == OPERATED_BY_VENDOR and dimension == MARKET_BASED_DIMENSION:
        # The pair exists inside scope 2 and nowhere else. Filing a market-based
        # figure here would be the mirror of filing cloud electricity as scope 2:
        # a number that looks like a disclosure and belongs to another company.
        return Placement(
            dimension,
            None,
            None,
            "No scope",
            (
                "The machine is operated by a vendor, so there is no scope 2 of "
                "yours here to report either way. The electricity is the vendor's "
                "scope 2, and the location-based / market-based pair is its "
                "disclosure to make. What reaches you is one purchased service, in "
                "scope 3 category 1, where the standard draws no such pair — so a "
                "market-based figure on rented hardware is not a more precise "
                "answer, it is an answer to somebody else's question."
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

    if dimension == MARKET_BASED_DIMENSION:
        return Placement(
            dimension,
            "2",
            None,
            "Scope 2 (market-based)",
            (
                "The organisation operates the machine, so it bought the electricity, "
                "and it bought it under a contract. The figure here is "
                f"{MARKET_BASED}. It rests on a factor you stated, which is the one "
                "fact about this number nobody else holds — this package neither "
                "derived it nor can refresh it."
            ),
            GHG_PROTOCOL_SCOPE2,
            (
                "This is one half of the pair. The location-based figure beside it, "
                "`carbon`, is the other, and both are disclosed: a contract changes "
                "what you are accountable for, not what the grid emitted."
            ),
        )

    return Placement(
        dimension,
        "2",
        None,
        "Scope 2 (location-based)",
        (
            "The organisation operates the machine, so it bought the electricity. "
            f"The figure here is {LOCATION_BASED}."
        ),
        GHG_PROTOCOL_SCOPE2,
        MARKET_BASED_PRESENT if market_based_reported else MARKET_BASED_MISSING,
    )


def placements(
    dimensions: list[str] | tuple[str, ...],
    provider: str | None,
    *,
    overlay: Any = None,
    market_based_reported: bool = False,
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
    market_based_reported : bool, optional
        Whether the model carries an actual market-based figure, which
        :func:`market_based_figure_exists` answers from the costs. Defaults to
        false, so a caller that does not know prints the shopping list rather
        than claiming a disclosure is whole.

    Returns
    -------
    dict
        Dimension key to its placement.

    Examples
    --------
    >>> found = placements(["carbon", "embodied_carbon", "water"], "on-prem")
    >>> [found[key].label for key in found]
    ['Scope 2 (location-based)', 'Scope 3, category 2 — capital goods', 'No scope']
    >>> whole = placements(["carbon"], "on-prem", market_based_reported=True)
    >>> "`carbon_market_based`" in whole["carbon"].dual_reporting
    True
    """
    return {
        key: placement(key, provider, overlay=overlay, market_based_reported=market_based_reported)
        for key in dimensions
    }


def market_based_figure_exists(costs: Any) -> bool:
    """Return whether a model carries a market-based number, not just the row.

    The distinction the sentence above rests on, and it is not pedantry: an
    empty ``carbon_market_based`` is the shopping list, and a report that read
    the key alone would tell a sustainability team the pair was complete while
    the second number was a ``TODO``. That is the exact failure this package
    exists to prevent, committed by the function that explains it.

    Parameters
    ----------
    costs : any
        A scenario's ``costs`` mapping, as it comes out of the document.

    Returns
    -------
    bool
        True only when the market-based row is there and holds a value.

    Examples
    --------
    >>> market_based_figure_exists({"carbon_market_based": {"value": 12.0}})
    True
    >>> market_based_figure_exists({"carbon_market_based": {"status": "TODO"}})
    False
    >>> market_based_figure_exists({"carbon": {"value": 12.0}})
    False
    """
    if not isinstance(costs, dict):
        return False
    row = costs.get(MARKET_BASED_DIMENSION)
    return isinstance(row, dict) and row.get("value") is not None


def placed_model(
    model: CostModel | dict[str, Any],
    *,
    scenario: str | None = None,
    overlay: Any = None,
) -> dict[str, Any]:
    """Return one scenario's costs, each with the inventory line it belongs on.

    The whole-model answer, assembled once. Three surfaces ask for it in the same
    shape — the command line, the HTTP API, and the agent tool built on that API —
    and the first version of this lived inside the command, where the other two
    could only have reached it by copying. A placement that differed between two
    of them by a field would be the package disagreeing with itself about which
    line a figure goes on, which is the one thing it exists to settle.

    It computes no figure. Every number here is already in the model; what is
    added is the scope, the sentence justifying it, and the count of how well
    founded the placed figures are, which a filer is asked to disclose.

    Parameters
    ----------
    model : CostModel or dict
        The model to place.
    scenario : str or None, optional
        Which scenario's costs to place. The first one when omitted.
    overlay : optional
        A user catalogue overlay, as the rest of the package passes one.

    Returns
    -------
    dict
        ``unit_of_work``, ``provider``, ``scenario``, a ``placements`` list in
        the model's own dimension order, ``by_status`` counting the placed
        figures, and the ``standards`` that settle them.

    Raises
    ------
    ValueError
        When a scenario was named and the model has no scenario by that name.
        Reporting the wrong scenario's costs under the right name is worse than
        refusing, because nothing downstream could detect it.

    Examples
    --------
    >>> placed = placed_model({
    ...     "unit_of_work": {"name": "one inference"},
    ...     "deployment": {"provider": "on-prem"},
    ...     "scenarios": [{"name": "cold", "costs": {
    ...         "carbon": {"value": 1.4, "unit": "gCO2e", "status": "estimated"},
    ...         "water": {"value": None, "unit": "L", "status": "TODO"},
    ...     }}],
    ... })
    >>> [row["label"] for row in placed["placements"]]
    ['Scope 2 (location-based)', 'No scope']
    >>> placed["by_status"]
    {'estimated': 1}
    >>> try:
    ...     placed_model({"scenarios": [{"name": "cold"}]}, scenario="warm")
    ... except ValueError as exc:
    ...     print(exc)
    No scenario named 'warm'. The model has: cold
    """
    wrapped = model if isinstance(model, CostModel) else CostModel.from_mapping(model)

    deployment = wrapped.get("deployment") if isinstance(wrapped.get("deployment"), dict) else {}
    provider = deployment.get("provider")
    rows_in = wrapped.get("scenarios") if isinstance(wrapped.get("scenarios"), list) else []
    usable = [row for row in rows_in if isinstance(row, dict)]

    if scenario is None:
        chosen = usable[0] if usable else {}
    else:
        found = next((row for row in usable if str(row.get("name")) == scenario), None)
        if found is None:
            named = ", ".join(str(row.get("name", "?")) for row in usable)
            raise ValueError(f"No scenario named {scenario!r}. The model has: {named}")
        chosen = found

    costs = chosen.get("costs") if isinstance(chosen.get("costs"), dict) else {}
    placed = placements(
        list(costs),
        provider,
        overlay=overlay,
        market_based_reported=market_based_figure_exists(costs),
    )

    rows: list[dict[str, Any]] = []
    for key, cost in costs.items():
        where = placed[key]
        quantity = cost if isinstance(cost, dict) else {}
        rows.append(
            {
                "dimension": key,
                "value": quantity.get("value"),
                "unit": quantity.get("unit"),
                "status": quantity.get("status"),
                "scope": where.scope,
                "category": where.category,
                "label": where.label,
                "why": where.why,
                "source_url": where.source_url,
                "dual_reporting": where.dual_reporting,
            }
        )

    # The share of the inventory that rests on an estimate rather than a reading.
    # Not decoration: the European standards require a filer to disclose it, and
    # a model that already labels every number can answer without being asked.
    counted = Counter(
        str(row["status"]) for row in rows if row["scope"] is not None and row["status"]
    )

    unit = wrapped.get("unit_of_work") if isinstance(wrapped.get("unit_of_work"), dict) else {}
    return {
        "unit_of_work": unit.get("name"),
        "provider": provider,
        "scenario": chosen.get("name"),
        "placements": rows,
        "by_status": dict(sorted(counted.items())),
        "standards": {
            "corporate": GHG_PROTOCOL_CORPORATE,
            "scope_2_guidance": GHG_PROTOCOL_SCOPE2,
            "scope_3_standard": GHG_PROTOCOL_SCOPE3,
        },
    }
