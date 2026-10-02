"""What a kilowatt-hour costs, and the check on that figure.

Module summary
--------------
A residential price per kilowatt-hour -- power, distribution, transmission and
all taxes -- for every country in one table and one currency. The table is
written by a script rather than served, so it is rendered in a headless browser;
with no browser installed this says so and stops rather than guessing.

Eurostat is the more authoritative body for Europe and is cited here as a
*check*, not as the source: it publishes in euros and for Europe only, so taking
it would have meant a second source for the exchange rate, a conversion going
stale daily, and eighteen rows that could not be compared with the other twenty.

Author
------
Warith Harchaoui
"""

from __future__ import annotations

import re
import shutil
import subprocess
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Final

#: Where the electricity tariffs come from. One page, one method, one unit: the
#: residential price including the cost of power, distribution, transmission and
#: all taxes, in US dollars per kilowatt-hour, for every country at once. The
#: alternative was Eurostat, which is the more authoritative body but publishes
#: in euros and for Europe only: taking it would have meant a second source for
#: the exchange rate, a conversion going stale daily, and eighteen rows that
#: could not be compared with the other twenty. See :func:`fetch_prices` for the
#: cross-check that was run against it anyway.
PRICE_SOURCE: Final[str] = "https://www.globalpetrolprices.com/electricity_prices/"


#: Eurostat's household electricity price series, cited as the check on the
#: tariffs rather than as their source. A deterministic URL that answers with
#: the number, which is what makes it worth citing at all.
PRICE_CROSSCHECK: Final[str] = (
    "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/nrg_pc_204"
    "?format=JSON&lang=EN&nrg_cons=KWH2500-4999&tax=I_TAX&currency=EUR&unit=KWH"
    "&lastTimePeriod=1"
)


#: The European Central Bank's euro reference rates, which is what the
#: cross-check above had to be converted through to be comparable at all.
PRICE_CROSSCHECK_RATE: Final[str] = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml"


#: The names that page uses where they are not the country's ordinary English
#: name. Everything else matches the name already in the catalogue.
PRICE_NAME_OF_KEY: Final[dict[str, str]] = {
    "AE": "UAE",
    "CZ": "Czech Republic",
    "GB": "UK",
    "KR": "South Korea",
    "TR": "Turkey",
    "US": "USA",
}


#: Where a headless browser might be. That page writes its table with a script
#: rather than serving it, so reading the bytes off the wire returns a table
#: with no numbers in it.
_BROWSERS: Final[tuple[str, ...]] = (
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "google-chrome",
    "chromium",
    "chromium-browser",
)


_PRICE_ROW: Final[re.Pattern[str]] = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S)


_PRICE_CELL: Final[re.Pattern[str]] = re.compile(r"<t[dh][^>]*>(.*?)</t[dh]>", re.S)


_TAG: Final[re.Pattern[str]] = re.compile(r"<[^>]+>")


#: How the tariff page dates its figures. The comparison table heads itself with
#: a quarter ("Q3 2026 update"); the per-country pages say which month the prices
#: were collected in. Either is the period the number describes, which is not the
#: day it was read, and the row records both.
_COLLECTED: Final[re.Pattern[str]] = re.compile(r"(Q[1-4] \d{4}) update|collected in (\w+ \d{4})")


@dataclass(frozen=True)
class PriceRefresh:
    """What the tariff source said, and what it had nothing to say about.

    Parameters
    ----------
    rows : dict
        ISO 3166-1 alpha-2 key to price in US dollars per kilowatt-hour.
    skipped : dict
        Key to the reason this refresh has nothing to say about it.
    source : str
        The URL that answered.
    collected : str or None
        When the source says it collected the prices, which is not when they
        were read: a figure read today out of a March release is a March figure,
        and the row records both.
    retrieved : str
        The day this was read.

    Examples
    --------
    >>> PriceRefresh(rows={"FR": 0.276}, skipped={}, source="x").rows["FR"]
    0.276
    """

    rows: dict[str, float]
    skipped: dict[str, str]
    source: str
    collected: str | None = None
    retrieved: str = field(default_factory=lambda: date.today().isoformat())

    def changed(self, current: dict[str, Any], *, tolerance: float = 0.005) -> dict[str, tuple]:
        """Return the rows whose tariff moved by more than the tolerance.

        Parameters
        ----------
        current : dict
            The catalogue as it stands, keyed the same way.
        tolerance : float, optional
            Movement below this is the catalogue's own rounding, not news.

        Returns
        -------
        dict
            Key to ``(was, now)``.

        Examples
        --------
        >>> refresh = PriceRefresh(rows={"FR": 0.276}, skipped={}, source="x")
        >>> refresh.changed({"FR": {"price_usd_per_kwh": 0.24}})
        {'FR': (0.24, 0.276)}
        >>> refresh.changed({"FR": {"price_usd_per_kwh": 0.2761}})
        {}
        """
        moved: dict[str, tuple] = {}
        for key, now in self.rows.items():
            row = current.get(key)
            was = row.get("price_usd_per_kwh") if isinstance(row, dict) else None
            if was is None or abs(float(was) - now) > tolerance:
                moved[key] = (was, now)
        return moved


def _rendered(url: str, *, timeout: int) -> str:
    """Return a page's document after its scripts have run.

    Parameters
    ----------
    url : str
        The page to render.
    timeout : int
        Seconds to allow.

    Returns
    -------
    str
        The document, or an empty string when no browser is installed. Saying
        nothing is the honest answer to "I could not look".
    """
    for browser in _BROWSERS:
        if not Path(browser).exists() and shutil.which(browser) is None:
            continue
        try:
            done = subprocess.run(  # noqa: S603 - a fixed argument list.
                [
                    browser,
                    "--headless",
                    "--disable-gpu",
                    "--dump-dom",
                    "--virtual-time-budget=9000",
                    url,
                ],
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
        except (subprocess.TimeoutExpired, OSError):
            continue
        if done.stdout:
            return done.stdout
    return ""


def fetch_prices(
    keys: list[str] | tuple[str, ...],
    *,
    names: dict[str, str] | None = None,
    timeout: int = 90,
) -> PriceRefresh:
    """Return today's residential electricity tariff for each country asked for.

    One page carries every country in one unit, which is why it is read whole
    rather than country by country.

    Eurostat was read as well, as a check rather than as a source. Converted
    through the European Central Bank's reference rate, the two agree to a
    median of 7% over the eighteen countries both cover, and disagree by more
    than 15% for six of them: Finland, Romania, Poland, Norway, Sweden, Italy.
    That is a difference of method rather than an error in either -- Eurostat
    averages a half-year by consumption band, this is one collection -- and both
    URLs are on file, in :data:`PRICE_CROSSCHECK` and
    :data:`PRICE_CROSSCHECK_RATE`, so a reader can run the comparison again.

    Parameters
    ----------
    keys : list of str
        ISO 3166-1 alpha-2 codes to look for.
    names : dict, optional
        Country name per key, as the catalogue spells it. The source's own
        spellings, in :data:`PRICE_NAME_OF_KEY`, win where they differ.
    timeout : int, optional
        Seconds to allow the page.

    Returns
    -------
    PriceRefresh
        What was found, and why anything missing was missed.

    Raises
    ------
    RuntimeError
        When no headless browser is installed, since the page's table is
        written by a script rather than served.

    Examples
    --------
    >>> fetch_prices([]).rows
    {}
    """
    wanted = {key: (names or {}).get(key, "") for key in keys}
    if not wanted:
        return PriceRefresh(rows={}, skipped={}, source=PRICE_SOURCE)
    document = _rendered(PRICE_SOURCE, timeout=timeout)
    if not document:
        raise RuntimeError(
            "No headless browser answered, and that page writes its table with a "
            "script rather than serving it. Install Chrome or Chromium; nothing "
            "here will guess at a tariff."
        )
    table: dict[str, float] = {}
    for block in _PRICE_ROW.findall(document):
        cells = [_TAG.sub("", cell).strip() for cell in _PRICE_CELL.findall(block)]
        cells = [cell for cell in cells if cell]
        if len(cells) >= 2:
            try:
                table[cells[0]] = float(cells[1])
            except ValueError:
                continue
    found = _COLLECTED.search(_TAG.sub(" ", document))
    collected = next((part for part in (found.groups() if found else ()) if part), None)
    rows: dict[str, float] = {}
    skipped: dict[str, str] = {}
    for key, name in wanted.items():
        label = PRICE_NAME_OF_KEY.get(key, name)
        if label in table:
            rows[key] = table[label]
        else:
            skipped[key] = "the source published no tariff under that name."
    return PriceRefresh(
        rows=rows,
        skipped=skipped,
        source=PRICE_SOURCE,
        collected=collected,
    )


def apply_prices(path: Path, refresh: PriceRefresh) -> int:
    r"""Write a tariff refresh into a catalogue file, line by line.

    Edited rather than re-serialised, for the same reason as the carbon column:
    a round trip through a YAML writer loses every comment in the file, and the
    comments are where the reasons live.

    Parameters
    ----------
    path : pathlib.Path
        The catalogue to edit. It must already exist.
    refresh : PriceRefresh
        What to write.

    Returns
    -------
    int
        How many rows were rewritten.

    Raises
    ------
    FileNotFoundError
        When the path is not there.

    Examples
    --------
    >>> import tempfile, pathlib
    >>> text = 'countries:\n  - key: "FR"\n    price_usd_per_kwh: 0.24\n'
    >>> with tempfile.TemporaryDirectory() as folder:
    ...     target = pathlib.Path(folder) / "grid.yaml"
    ...     _ = target.write_text(text, encoding="utf-8")
    ...     written = apply_prices(
    ...         target, PriceRefresh({"FR": 0.276}, {}, "gpp", "March 2026"))
    ...     body = target.read_text(encoding="utf-8")
    >>> written
    1
    >>> "price_usd_per_kwh: 0.276" in body
    True
    >>> 'price_collected: "March 2026"' in body
    True
    """
    if not path.is_file():
        raise FileNotFoundError(
            f"{path} is not there. This edits a catalogue; it does not create one."
        )
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    written = 0
    current: str | None = None
    out: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("- key:"):
            current = stripped.split(":", 1)[1].strip().strip('"').strip("'")
        if current in refresh.rows and stripped.startswith("price_usd_per_kwh:"):
            indent = line[: len(line) - len(line.lstrip())]
            out.append(f"{indent}price_usd_per_kwh: {refresh.rows[current]}\n")
            out.append(f'{indent}price_source_url: "{refresh.source}"\n')
            out.append(f'{indent}price_retrieved_date: "{refresh.retrieved}"\n')
            if refresh.collected:
                out.append(f'{indent}price_collected: "{refresh.collected}"\n')
            written += 1
            continue
        if current in refresh.rows and stripped.startswith(
            ("price_source_url:", "price_retrieved_date:", "price_collected:")
        ):
            continue
        out.append(line)
    path.write_text("".join(out), encoding="utf-8")
    return written
