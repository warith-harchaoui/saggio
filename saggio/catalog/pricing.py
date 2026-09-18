"""
What a third-party API charges, and how close the figure is to whoever sets it.

Module summary
--------------
A cost model that names the APIs a repository calls but leaves every price open
is honest and half useful. This module closes the other half, without doing the
thing that would make it dishonest.

The rule the rest of the package keeps is that a number comes from a file you can
open or a counter you can read. A price on a vendor's marketing page is neither,
and parsing one is the worst kind of automation: it fails *silently and wrongly*.
A layout change does not raise, it returns the struck-through old figure, or the
enterprise tier, or the cached-input rate instead of the input rate. ``gpt-4o``
alone publishes eight plausible numbers; picking the wrong one is the nominal
case, not the edge case. So nothing here parses HTML, and nothing here asks a
language model what a page says.

What it does instead is walk a ladder, the same shape as the country ladder in
:mod:`saggio.estimate.context`, where each rung produces a different provenance:

1. a human stated the price, which is an assertion, so ``measured`` / ``stated``;
2. the vendor publishes a machine-readable price, so ``estimated`` /
   ``first-party``;
3. a structured aggregator publishes somebody's transcription of that, so
   ``estimated`` / ``aggregator``, and the note says to confirm it against the
   vendor's own page;
4. nothing does, so ``TODO`` carrying the page where the number lives.

Rung three is where the large language-model vendors sit today, because none of
them publishes a price API. That is stated rather than dressed up: the model
records ``source_kind: aggregator`` and the report shows it.

A fetched rate is a *rate*, never a cost. How many tokens one unit of work spends
is not something reading a repository can establish, so it stays ``TODO`` and the
model ends up saying exactly which half is missing.

Usage example
-------------
>>> from saggio.catalog.pricing import rate_table, LITELLM_SOURCE
>>> table = rate_table("gpt-4o", fetch=lambda _u, _t: {
...     "gpt-4o": {"input_cost_per_token": 2.5e-06, "litellm_provider": "openai"}})
>>> table.source_kind
'aggregator'
>>> table.rates["input_cost_per_token"].value
2.5e-06

Author
------
Warith Harchaoui
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Final

import os_helper as osh

from ..model.quantity import AGGREGATOR, Quantity
from ..model.taxonomy import ESTIMATED, TODO

#: Where the structured aggregator publishes its table. A file in a public
#: repository, fetched as a file: no HTML, no parsing, no guessing.
LITELLM_URL: Final[str] = (
    "https://raw.githubusercontent.com/BerriAI/litellm/main/model_prices_and_context_window.json"
)

#: What the model records as the source of a rate read from it. The vendor's own
#: pricing page is a better citation for a human, and the note carries that too,
#: but this is the URL the number was actually read from and so it is the one the
#: provenance names.
LITELLM_SOURCE: Final[str] = "https://github.com/BerriAI/litellm"

#: Seconds to wait for the table. It is a couple of megabytes of JSON over a CDN;
#: a fetch that has not finished in this long is not going to improve the audit.
FETCH_TIMEOUT_SECONDS: Final[float] = 30.0

#: The currency the aggregator quotes. It states this in its documentation rather
#: than in the file, so it is an assumption about the source, and every rate says
#: so in its notes rather than letting the currency pass as read.
AGGREGATOR_CURRENCY: Final[str] = "USD"

#: Keys in an aggregator row that are not rates. Everything else whose name says
#: it is a cost is treated as one, so a unit the source adds next month arrives
#: without a change here.
_NOT_A_RATE: Final[frozenset[str]] = frozenset(
    {"litellm_provider", "mode", "supported_endpoints", "deprecation_date"}
)

#: Readable units for the handful of rate keys a reader meets most often. A key
#: that is not here keeps its own spelling, because inventing a normalisation
#: across seventy-odd keys would be a silent transformation of somebody else's
#: data, which is the habit this package exists to break.
_UNIT_BY_KEY: Final[dict[str, str]] = {
    "input_cost_per_token": "USD per input token",
    "output_cost_per_token": "USD per output token",
    "cache_read_input_token_cost": "USD per cached input token",
    "cache_creation_input_token_cost": "USD per cache-write input token",
    "input_cost_per_token_batches": "USD per input token, batch tier",
    "output_cost_per_token_batches": "USD per output token, batch tier",
    "input_cost_per_image": "USD per input image",
    "output_cost_per_image": "USD per output image",
    "input_cost_per_audio_token": "USD per input audio token",
    "output_cost_per_second": "USD per output second",
    "input_cost_per_second": "USD per input second",
}


def unit_for(key: str) -> str:
    """Return a readable unit for an aggregator rate key.

    Parameters
    ----------
    key : str
        The key as the source spells it, for example ``input_cost_per_token``.

    Returns
    -------
    str
        A readable unit, or the key itself when this build has no better name for
        it. Keeping the source's own spelling is deliberate: a reader can match
        the row back to the file it came from.

    Examples
    --------
    >>> unit_for("output_cost_per_token")
    'USD per output token'
    >>> unit_for("input_cost_per_token_above_200k_tokens")
    'input_cost_per_token_above_200k_tokens'
    """
    return _UNIT_BY_KEY.get(key, key)


def looks_like_a_rate(key: str, value: object) -> bool:
    """Return whether a field of an aggregator row states a price.

    Parameters
    ----------
    key : str
        The field name.
    value : object
        The field value.

    Returns
    -------
    bool
        ``True`` when the name says it is a cost and the value is a real number.
        Booleans are rejected even though Python calls them integers: ``True`` is
        not a price.

    Examples
    --------
    >>> looks_like_a_rate("input_cost_per_token", 2.5e-06)
    True
    >>> looks_like_a_rate("max_input_tokens", 128000)
    False
    >>> looks_like_a_rate("supports_vision", True)
    False
    """
    if key in _NOT_A_RATE:
        return False
    if not ("cost" in key or "price" in key):
        return False
    return isinstance(value, (int, float)) and not isinstance(value, bool)


@dataclass(frozen=True, slots=True)
class RateTable:
    """Every rate one model is charged at, with where the figures came from.

    Parameters
    ----------
    model : str
        The model identifier the rates belong to, as the source spells it.
    rates : dict
        Rate key to :class:`~saggio.model.quantity.Quantity`. A model may be
        charged on several axes at once; ``gpt-4o`` publishes eight.
    source_kind : str
        How close the figures are to whoever sets them.
    source_url : str
        Where they were read.
    provider : str or None
        The vendor the source attributes the model to, when it says.
    note : str
        One sentence on where these figures came from and what to do about it.
        It sits on the table rather than on each rate because it is the same
        sentence for all of them, and a model that repeats forty words eight
        times is a model nobody finishes reading.

    Examples
    --------
    >>> RateTable("m", {}, "aggregator", "https://x.invalid").is_empty()
    True
    """

    model: str
    rates: dict[str, Quantity] = field(default_factory=dict)
    source_kind: str = AGGREGATOR
    source_url: str = LITELLM_SOURCE
    provider: str | None = None
    note: str = ""

    def is_empty(self) -> bool:
        """Return whether the table states no rate at all.

        Returns
        -------
        bool
            ``True`` when nothing was found, which is how a caller knows to leave
            the price open rather than write an empty block.

        Examples
        --------
        >>> RateTable("m", {"input_cost_per_token": Quantity(value=1.0)}).is_empty()
        False
        """
        return not self.rates

    def to_mapping(self) -> dict[str, Any]:
        """Serialise the table for a model's external-services block.

        Returns
        -------
        dict
            A mapping of rate key to serialised quantity. The provenance travels
            on each quantity rather than once on the table, because a later hand
            edit may replace one rate with a stated figure and leave the rest.

        Examples
        --------
        >>> RateTable("m", {}).to_mapping()
        {}

        """
        return {key: quantity.to_mapping() for key, quantity in self.rates.items()}


def _fetch_json(url: str, timeout: float) -> Any | None:
    """Fetch a URL and parse it as JSON, returning ``None`` on any failure.

    An absent or slow source is an ordinary outcome, not an error: an audit that
    cannot reach the network must produce the same model it produces offline,
    with the prices left open.

    Parameters
    ----------
    url : str
        What to fetch.
    timeout : float
        Seconds to wait.

    Returns
    -------
    Any or None
        The decoded document, or ``None``.

    Examples
    --------
    >>> _fetch_json("http://127.0.0.1:1/nothing", timeout=0.01) is None
    True
    """
    try:
        request = urllib.request.Request(  # noqa: S310 - https, and the caller's own URL.
            url, headers={"Accept": "application/json", "User-Agent": "saggio"}
        )
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
            return json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
        osh.warning(f"Could not read published prices from {url}: {exc}")
        return None


#: Signature of a fetcher, so a test can supply the table without a network.
Fetcher = Callable[[str, float], Any]


def rate_table(
    model: str,
    *,
    timeout: float = FETCH_TIMEOUT_SECONDS,
    fetch: Fetcher | None = None,
    today: date | None = None,
) -> RateTable:
    """Return every published rate for one model, or an empty table.

    Parameters
    ----------
    model : str
        A model identifier as the vendor spells it, for example ``gpt-4o``.
    timeout : float, optional
        Seconds to wait for the source.
    fetch : callable or None, optional
        Injected fetcher taking ``(url, timeout)``; the real one when not given,
        so a test never reaches the network.
    today : datetime.date or None, optional
        The date recorded as when the figures were read. Injectable so a test
        does not drift as the calendar moves.

    Returns
    -------
    RateTable
        The rates, each carrying its unit, its currency, its provenance and the
        date it was read. Empty when the source could not be reached or does not
        know the model, which leaves the price open rather than inventing one.

    Examples
    --------
    >>> from datetime import date
    >>> rows = {"claude-3-5-sonnet-20241022": {
    ...     "input_cost_per_token": 3e-06, "output_cost_per_token": 1.5e-05,
    ...     "max_input_tokens": 200000, "litellm_provider": "anthropic"}}
    >>> table = rate_table("claude-3-5-sonnet-20241022",
    ...                    fetch=lambda _u, _t: rows, today=date(2026, 9, 13))
    >>> sorted(table.rates)
    ['input_cost_per_token', 'output_cost_per_token']
    >>> rate = table.rates["output_cost_per_token"]
    >>> rate.value, rate.unit, rate.currency, rate.status, rate.source_kind
    (1.5e-05, 'USD per output token', 'USD', 'estimated', 'aggregator')
    >>> rate.retrieved_date
    '2026-09-13'
    >>> rate.notes is None      # the explanation sits once on the table
    True
    >>> "Confirm against the vendor" in table.note
    True
    >>> rate_table("not-a-model", fetch=lambda _u, _t: rows).is_empty()
    True
    >>> rate_table("gpt-4o", fetch=lambda _u, _t: None).is_empty()
    True
    """
    reader = fetch if fetch is not None else _fetch_json
    document = reader(LITELLM_URL, timeout)
    if not isinstance(document, dict):
        return RateTable(model=model)

    row = document.get(model)
    if not isinstance(row, dict):
        return RateTable(model=model)

    stamped = (today or date.today()).isoformat()
    provider = row.get("litellm_provider")
    note = (
        f"Rates for {model}, read from a community table rather than from "
        f"{provider or 'the vendor'} directly, because no vendor price API publishes them. "
        "Confirm against the vendor's own pricing page before quoting. The source quotes "
        f"{AGGREGATOR_CURRENCY} in its documentation rather than in the file, so the "
        "currency is an assumption about the source."
    )
    rates = {
        key: Quantity(
            value=float(value),
            unit=unit_for(key),
            currency=AGGREGATOR_CURRENCY,
            status=ESTIMATED,
            source_kind=AGGREGATOR,
            source_url=LITELLM_SOURCE,
            retrieved_date=stamped,
        )
        for key, value in sorted(row.items())
        if looks_like_a_rate(key, value)
    }
    return RateTable(
        model=model,
        rates=rates,
        source_kind=AGGREGATOR,
        source_url=LITELLM_SOURCE,
        provider=str(provider) if provider else None,
        note=note,
    )


def open_price(pricing_source_url: str | None, reason: str) -> Quantity:
    """Return the quantity a price gets when nothing could establish it.

    Parameters
    ----------
    pricing_source_url : str or None
        The vendor page where the current number lives, carried so a reader has
        somewhere to go.
    reason : str
        Why it is open, phrased as something to act on.

    Returns
    -------
    Quantity
        A ``TODO`` with no number.

    Examples
    --------
    >>> open_price("https://openai.com/api/pricing/", "No model named.").status
    'TODO'
    """
    return Quantity(status=TODO, source_url=pricing_source_url or None, notes=reason)
