"""
Refreshing a catalogue from the source it cites, rather than from memory.

Module summary
--------------
A grid carbon intensity goes stale in a month, and until now the only way to
answer that was for a person to open a web page, read thirty-eight numbers and
type them back in. Nobody does that. What happens instead is that somebody
changes the ``retrieved_date`` and moves on, and a re-dated number nobody looked
at is precisely the thing this package exists to refuse.

So the refresh is mechanical, and it is bound by the same rules as everything
else here.

**It reads the source the catalogue cites.** The grid rows say Ember, so this
reads Ember — either the yearly dataset Ember publishes openly, which needs no
key and is what the rows cite, or the API at ``api.ember-energy.org``, which
needs one and is the same series. Which of the two answered is printed, never
inferred from how it went.

What is refused is the other kind of fallback, and the distinction is the whole
point: Our World in Data publishes an Ember-*derived* series through a stable
CSV, but it is *lifecycle* carbon intensity, and the field here is documented as
*operating* emissions. Swapping one for the other would change what every
committed model means, silently, and leave every number looking exactly as
trustworthy as before. Ember's own published dataset is not that swap — same
publisher, same measure, and checked against the API country by country rather
than assumed equivalent.

**It cites what a reader can open.** The API answers a machine; without a key it
answers a reader with HTTP 403 and no number, so it is named in prose and never
in a ``source_url``. :data:`ENDPOINTS_A_READER_CANNOT_FOLLOW` is that rule as
data, so the contract test checking it grows when a module does.

**It writes only what it read.** A country the source did not answer for is left
alone and named in the report. A value that does not parse is left alone and
named. Nothing is interpolated, carried over, or averaged.

**It touches one column.** The row's electricity price and its timezones come
from elsewhere and keep their own provenance; only the carbon intensity and the
dates that belong to it are rewritten.

What is where
-------------
One module per source, because they share nothing: no constant, no helper, no
record type. Each holds the same three things -- what the source said, how to ask
it, and how to write the answer into a catalogue -- and each carries the reason
it is that source rather than a more convenient one.

================================================ ============================
:mod:`~saggio.catalog.refresh.carbon`            Ember, operating emissions
:mod:`~saggio.catalog.refresh.tariffs`           the price, and its cross-check
:mod:`~saggio.catalog.refresh.timezones`         the IANA database
:mod:`~saggio.catalog.refresh.embodied`          processor footprints
================================================ ============================

This was one file of 1,213 lines, and it had been 424 that morning. The three
sources added over a single afternoon each went in without anyone looking at
what the file was becoming.

Usage example
-------------
>>> from saggio.catalog.refresh import GridRefresh
>>> GridRefresh(year=None, rows={}, skipped={}, source="").changed({})
{}

Author
------
Warith Harchaoui
"""

from __future__ import annotations

from typing import Final

from .carbon import (
    EMBER_API,
    EMBER_CITATION,
    EMBER_INTENSITY_COLUMN,
    EMBER_KEY_VARIABLE,
    EMBER_PUBLIC_CSV,
    EMBER_TOTAL_ROW,
    ISO3_OF_ISO2,
    OPERATING_EMISSIONS,
    GridRefresh,
    apply_grid,
    fetch_grid,
    fetch_grid_public,
    missing_key_message,
)
from .embodied import (
    EMBODIED_CPU_API,
    EMBODIED_METHOD_URL,
    EMBODIED_NAME_OF_KEY,
    EmbodiedRefresh,
    _asked_for_what_came_back,
    accelerators_refused,
    apply_embodied,
    fetch_embodied,
)
from .tariffs import (
    PRICE_CROSSCHECK,
    PRICE_CROSSCHECK_RATE,
    PRICE_NAME_OF_KEY,
    PRICE_SOURCE,
    PriceRefresh,
    apply_prices,
    fetch_prices,
)
from .timezones import (
    TIMEZONE_LINKS_SOURCE,
    TIMEZONE_SOURCE,
    TIMEZONE_VERSION_SOURCE,
    TimezoneCheck,
    apply_timezone_check,
    check_timezones,
)

#: The URLs here that answer a machine and show a reader nothing usable. A
#: catalogue row may name one in its *scope*, where it is provenance of method,
#: but never in a ``source_url``, which is an invitation to go and check. The
#: tuple exists so that contract is checked against what the modules declare
#: rather than against a list somebody has to remember to extend: Boavizta's
#: endpoint was caught and listed by hand, and Ember's -- which answers a reader
#: with HTTP 403 and no number at all -- then sat in thirty-eight rows for three
#: iterations, passing a test written for exactly that fault.
ENDPOINTS_A_READER_CANNOT_FOLLOW: Final[tuple[str, ...]] = (
    EMBER_API,
    EMBODIED_CPU_API,
)

__all__ = [
    "EMBER_API",
    "EMBER_CITATION",
    "EMBER_INTENSITY_COLUMN",
    "EMBER_KEY_VARIABLE",
    "EMBER_PUBLIC_CSV",
    "EMBER_TOTAL_ROW",
    "ENDPOINTS_A_READER_CANNOT_FOLLOW",
    "EMBODIED_CPU_API",
    "EMBODIED_METHOD_URL",
    "EMBODIED_NAME_OF_KEY",
    "EmbodiedRefresh",
    "accelerators_refused",
    "GridRefresh",
    "ISO3_OF_ISO2",
    "OPERATING_EMISSIONS",
    "PRICE_CROSSCHECK",
    "PRICE_CROSSCHECK_RATE",
    "PRICE_NAME_OF_KEY",
    "PRICE_SOURCE",
    "PriceRefresh",
    "TIMEZONE_LINKS_SOURCE",
    "TIMEZONE_SOURCE",
    "TIMEZONE_VERSION_SOURCE",
    "TimezoneCheck",
    "apply_embodied",
    "apply_grid",
    "apply_prices",
    "apply_timezone_check",
    "check_timezones",
    "fetch_embodied",
    "fetch_grid",
    "fetch_grid_public",
    "fetch_prices",
    "missing_key_message",
    "_asked_for_what_came_back",
]
