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
asks Ember, through the open API at ``api.ember-energy.org``. That API wants a
key — free, issued on request — and this module refuses rather than quietly
falling back to some other dataset that happens to be reachable. There is one
tempting fallback and it is wrong: Our World in Data publishes an Ember-derived
series through a stable CSV, but it is *lifecycle* carbon intensity, and the
field here is documented as *operating* emissions. Swapping one for the other
would change what every committed model means, silently, and leave every number
looking exactly as trustworthy as before.

**It writes only what it read.** A country the source did not answer for is left
alone and named in the report. A value that does not parse is left alone and
named. Nothing is interpolated, carried over, or averaged.

**It touches one column.** The row's electricity price and its timezones come
from elsewhere and keep their own provenance; only the carbon intensity and the
dates that belong to it are rewritten.

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

import json
import os
import re
import shutil
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Final

#: Where the figures the grid catalogue cites actually live, machine-readable.
EMBER_API: Final[str] = "https://api.ember-energy.org/v1/carbon-intensity/yearly"

#: The environment variable this reads a key from, so a key never has to appear
#: in a shell history or a command somebody pastes into an issue.
EMBER_KEY_VARIABLE: Final[str] = "EMBER_API_KEY"

#: What the catalogue column means, and therefore what the source must mean too.
#: Written here because it is the one fact that decides whether a dataset may be
#: used at all, and it is easy to lose between a column name and an API field.
OPERATING_EMISSIONS: Final[str] = (
    "annual average operating emissions of the national grid, in gCO2e per kWh — "
    "not lifecycle, which includes building the generating plant and is a larger "
    "number for every low-carbon grid"
)

#: The series that is reachable without a key and must not be used. Named so the
#: next person to look for a shortcut finds the reason rather than the shortcut.
_REFUSED_FALLBACK: Final[str] = (
    "Our World in Data's carbon-intensity-electricity series is reachable without "
    "a key and is Ember-derived, but its own metadata calls it lifecycle carbon "
    "intensity. This column is operating emissions. Substituting one for the "
    "other would change what every committed model means without changing how "
    "trustworthy any of them looks."
)

#: ISO 3166-1 alpha-2 to alpha-3, for the countries the bundled catalogue holds.
#: Explicit rather than a dependency: thirty-eight rows do not justify a library,
#: and a key with no entry here is reported rather than guessed at.
ISO3_OF_ISO2: Final[dict[str, str]] = {
    "AE": "ARE",
    "AR": "ARG",
    "AT": "AUT",
    "AU": "AUS",
    "BE": "BEL",
    "BR": "BRA",
    "CA": "CAN",
    "CH": "CHE",
    "CL": "CHL",
    "CN": "CHN",
    "CZ": "CZE",
    "DE": "DEU",
    "DK": "DNK",
    "EG": "EGY",
    "ES": "ESP",
    "FI": "FIN",
    "FR": "FRA",
    "GB": "GBR",
    "ID": "IDN",
    "IE": "IRL",
    "IL": "ISR",
    "IN": "IND",
    "IT": "ITA",
    "JP": "JPN",
    "KR": "KOR",
    "MX": "MEX",
    "MY": "MYS",
    "NL": "NLD",
    "NO": "NOR",
    "NZ": "NZL",
    "PL": "POL",
    "PT": "PRT",
    "RO": "ROU",
    "RU": "RUS",
    "SA": "SAU",
    "SE": "SWE",
    "SG": "SGP",
    "SK": "SVK",
    "TR": "TUR",
    "TW": "TWN",
    "UA": "UKR",
    "US": "USA",
    "ZA": "ZAF",
}


@dataclass(frozen=True, slots=True)
class GridRefresh:
    """What a source said when it was asked, and what it did not say.

    Parameters
    ----------
    year : int or None
        The data year the figures describe. Not today's date: a number read
        today from a 2025 release is a 2025 number, and the row records both.
    rows : dict
        ISO 3166-1 alpha-2 key to carbon intensity in gCO2e per kWh.
    skipped : dict
        Key to the reason this refresh has nothing to say about it.
    source : str
        The URL that answered.

    Examples
    --------
    >>> GridRefresh(year=2025, rows={"FR": 41.0}, skipped={}, source="x").year
    2025
    """

    year: int | None
    rows: dict[str, float]
    skipped: dict[str, str]
    source: str
    retrieved: str = field(default_factory=lambda: date.today().isoformat())

    def changed(self, current: dict[str, Any], *, tolerance: float = 0.5) -> dict[str, tuple]:
        """Return the rows whose value actually moved, with both figures.

        A refresh that rewrites thirty-eight identical numbers and bumps
        thirty-eight dates is indistinguishable, in a diff, from a refresh
        nobody did. Only the ones that moved are interesting, and the ones that
        did not still get their date, because somebody genuinely looked.

        Parameters
        ----------
        current : dict
            The catalogue as it stands: key to row mapping.
        tolerance : float, optional
            How many gCO2e per kWh of difference counts as unchanged. Ember
            restates figures to more decimal places than this catalogue carries.

        Returns
        -------
        dict
            Key to ``(was, now)``, for the rows that moved.

        Examples
        --------
        >>> refresh = GridRefresh(2025, {"FR": 41.4}, {}, "x")
        >>> refresh.changed({"FR": {"carbon_gco2e_per_kwh": 56}})
        {'FR': (56, 41.4)}
        >>> refresh.changed({"FR": {"carbon_gco2e_per_kwh": 41.5}})
        {}
        """
        moved: dict[str, tuple] = {}
        for key, value in self.rows.items():
            row = current.get(key)
            if not isinstance(row, dict):
                continue
            was = row.get("carbon_gco2e_per_kwh")
            if not isinstance(was, (int, float)):
                moved[key] = (was, value)
            elif abs(float(was) - value) > tolerance:
                moved[key] = (was, value)
        return moved


def _api_key(explicit: str | None = None) -> str | None:
    """Return the Ember API key, from the argument or the environment."""
    return explicit or os.environ.get(EMBER_KEY_VARIABLE) or None


def missing_key_message() -> str:
    """Return what to do when there is no key, including what not to do.

    Returns
    -------
    str
        One paragraph: where to get a key, how to pass it, and why the
        key-less dataset that looks equivalent is not.

    Examples
    --------
    >>> "lifecycle" in missing_key_message()
    True
    """
    return (
        f"No Ember API key. Set {EMBER_KEY_VARIABLE}, or pass --api-key. Ember issues "
        "one free at https://ember-energy.org/data/ — this package will not refresh "
        f"from anywhere else. {_REFUSED_FALLBACK}"
    )


def fetch_grid(
    keys: list[str] | tuple[str, ...],
    *,
    api_key: str | None = None,
    year: int | None = None,
    timeout: float = 60.0,
) -> GridRefresh:
    """Ask Ember what each country's grid emitted, for the countries given.

    Parameters
    ----------
    keys : list or tuple of str
        ISO 3166-1 alpha-2 country codes, as the catalogue keys them.
    api_key : str or None, optional
        Ember API key. Falls back to the environment.
    year : int or None, optional
        Data year. ``None`` asks for the most recent Ember publishes.
    timeout : float, optional
        Seconds to wait on the network.

    Returns
    -------
    GridRefresh
        What came back, and what did not.

    Raises
    ------
    RuntimeError
        When there is no key, or the API did not answer. Not a silent empty
        result: a refresh that quietly returned nothing would read, in a
        terminal, exactly like a refresh that found nothing to change.

    Examples
    --------
    >>> fetch_grid([], api_key="x").rows
    {}
    """
    key = _api_key(api_key)
    if not keys:
        return GridRefresh(year=year, rows={}, skipped={}, source=EMBER_API)
    if not key:
        raise RuntimeError(missing_key_message())

    wanted: dict[str, str] = {}
    skipped: dict[str, str] = {}
    for code in keys:
        iso3 = ISO3_OF_ISO2.get(code.upper())
        if iso3 is None:
            skipped[code] = (
                "no ISO 3166-1 alpha-3 code on file for this key, so the source "
                "cannot be asked about it. Add one to ISO3_OF_ISO2."
            )
        else:
            wanted[iso3] = code.upper()

    if not wanted:
        # Every key was unmappable. Asking the source about nothing would spend a
        # network round trip to be told nothing, and would report an API failure
        # where the real finding is in `skipped`.
        return GridRefresh(year=year, rows={}, skipped=skipped, source=EMBER_API)

    query = urllib.parse.urlencode(
        {
            "entity_code": ",".join(sorted(wanted)),
            # `is_aggregate_entity`, spelled exactly as the published schema
            # spells it. An earlier version sent `is_aggregate_series`, which is
            # not a parameter this API has: unknown query parameters are ignored
            # rather than refused, so the filter the code believed it was setting
            # was never set. Harmless here, because every entity_code asked for
            # is a country rather than a region, but a line that states an intent
            # it does not achieve is the kind of thing this package exists to
            # object to.
            "is_aggregate_entity": "false",
            "api_key": key,
            **({"start_date": str(year), "end_date": str(year)} if year else {}),
        }
    )
    request = urllib.request.Request(  # noqa: S310 - a fixed https endpoint.
        f"{EMBER_API}?{query}", headers={"Accept": "application/json"}
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
            payload = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        raise RuntimeError(f"Ember did not answer: {exc}") from exc

    records = payload.get("data") if isinstance(payload, dict) else payload
    if not isinstance(records, list):
        raise RuntimeError(
            "Ember answered in a shape this does not recognise. The catalogue is "
            "untouched; nothing here will guess at a response it cannot read."
        )

    latest: dict[str, tuple[int, float]] = {}
    for record in records:
        if not isinstance(record, dict):
            continue
        iso3 = str(record.get("entity_code") or record.get("entity") or "")
        code = wanted.get(iso3.upper())
        value = record.get("emissions_intensity_gco2_per_kwh", record.get("value"))
        stamp = str(record.get("date") or record.get("year") or "")[:4]
        if code is None or not isinstance(value, (int, float)) or not stamp.isdigit():
            continue
        found_year = int(stamp)
        if code not in latest or found_year > latest[code][0]:
            latest[code] = (found_year, float(value))

    for code in wanted.values():
        if code not in latest:
            skipped[code] = "the source returned no figure for this country."

    years = {found for found, _ in latest.values()}
    return GridRefresh(
        year=max(years) if years else year,
        rows={code: value for code, (_, value) in latest.items()},
        skipped=skipped,
        source=EMBER_API,
    )


def apply_grid(path: Path, refresh: GridRefresh) -> int:
    """Write the refreshed intensities into a grid catalogue file.

    Edited as text, line by line, rather than loaded and dumped. A round trip
    through a YAML parser would rewrite the whole file: it would lose the header
    that explains every column, the comment warning that ``NO`` unquoted is the
    boolean false and takes Norway out of the catalogue, and the blank lines that
    group the rows. A refresh is not a reformat.

    Only the carbon intensity is touched, and the provenance that belongs to it.
    The row's price and timezones came from elsewhere and keep the row's own
    ``source_url`` and ``retrieved_date``, which is why the new dates are written
    under their own names.

    Parameters
    ----------
    path : pathlib.Path
        The grid catalogue to edit in place.
    refresh : GridRefresh
        What the source said.

    Returns
    -------
    int
        How many rows were rewritten.

    Raises
    ------
    FileNotFoundError
        When the path is not there. Nothing is created: a refresh that invented
        a catalogue would be writing numbers into a file nobody had reviewed.

    Examples
    --------
    >>> import tempfile, pathlib
    >>> text = '''countries:
    ...   - key: "FR"
    ...     carbon_gco2e_per_kwh: 56
    ...     retrieved_date: "2026-09-12"
    ... '''
    >>> with tempfile.TemporaryDirectory() as folder:
    ...     target = pathlib.Path(folder) / "grid.yaml"
    ...     _ = target.write_text(text, encoding="utf-8")
    ...     written = apply_grid(target, GridRefresh(2025, {"FR": 41.4}, {}, "ember"))
    ...     body = target.read_text(encoding="utf-8")
    >>> written
    1
    >>> "carbon_gco2e_per_kwh: 41.4" in body
    True
    >>> "carbon_data_year: 2025" in body
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
        if (
            current in refresh.rows
            and stripped.startswith("carbon_gco2e_per_kwh:")
            and not stripped.startswith("carbon_gco2e_per_kwh_")
        ):
            indent = line[: len(line) - len(line.lstrip())]
            value = refresh.rows[current]
            out.append(f"{indent}carbon_gco2e_per_kwh: {value:.1f}\n")
            out.append(f'{indent}carbon_source_url: "{refresh.source}"\n')
            out.append(f'{indent}carbon_retrieved_date: "{refresh.retrieved}"\n')
            out.append(f"{indent}carbon_data_year: {refresh.year}\n")
            written += 1
            continue
        # A previous refresh's own fields are replaced, not stacked.
        if current in refresh.rows and stripped.startswith(
            ("carbon_source_url:", "carbon_retrieved_date:", "carbon_data_year:")
        ):
            continue
        out.append(line)
    path.write_text("".join(out), encoding="utf-8")
    return written


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


#: Where the timezone names come from. The IANA Time Zone Database is the
#: authority every operating system ships, it is in the public domain, and it is
#: versioned, so a row can say which release it was checked against rather than
#: only when somebody looked.
TIMEZONE_SOURCE: Final[str] = "https://data.iana.org/time-zones/tzdb/zone1970.tab"

#: The release identifier, as a line of text.
TIMEZONE_VERSION_SOURCE: Final[str] = "https://data.iana.org/time-zones/tzdb/version"

#: The compatibility links. ``zone1970.tab`` lists only canonical zones, so a
#: catalogue naming ``Europe/Oslo`` or ``Europe/Kiev`` -- both still correct, and
#: both what a real machine reports -- would look wrong without this file.
TIMEZONE_LINKS_SOURCE: Final[str] = "https://data.iana.org/time-zones/tzdb/backward"


@dataclass(frozen=True)
class TimezoneCheck:
    """Whether every zone the catalogue names is one IANA publishes.

    This verifies rather than replaces. The catalogue deliberately lists more
    zones than ``zone1970.tab`` does, because that file carries only canonical
    names while a machine may report a compatibility link, and a country the
    package cannot recognise from its own machine's timezone is a country the
    user has to type by hand.

    Parameters
    ----------
    version : str
        The tzdb release, such as ``2026e``.
    known : int
        How many catalogued zones IANA publishes.
    unknown : dict
        Country key to the zones IANA does not publish under any name.
    source : str
        The URL that answered.
    retrieved : str
        The day this was read.

    Examples
    --------
    >>> TimezoneCheck("2026e", 61, {}, "iana").ok
    True
    >>> TimezoneCheck("2026e", 60, {"ZZ": ["Mars/Olympus"]}, "iana").ok
    False
    """

    version: str
    known: int
    unknown: dict[str, list[str]]
    source: str = TIMEZONE_SOURCE
    retrieved: str = field(default_factory=lambda: date.today().isoformat())

    @property
    def ok(self) -> bool:
        """Return whether every catalogued zone is one IANA publishes."""
        return not self.unknown


def _iana_zones(timeout: int) -> tuple[set[str], str]:
    """Return every zone name IANA publishes, and the release they came from.

    Parameters
    ----------
    timeout : int
        Seconds to allow each request.

    Returns
    -------
    tuple
        The names, canonical and compatibility links together, and the version.

    Raises
    ------
    RuntimeError
        When the database does not answer. Nothing is assumed about a zone that
        could not be checked.
    """
    pages: dict[str, str] = {}
    for name, url in (
        ("zones", TIMEZONE_SOURCE),
        ("links", TIMEZONE_LINKS_SOURCE),
        ("version", TIMEZONE_VERSION_SOURCE),
    ):
        request = urllib.request.Request(url, headers={"Accept": "text/plain"})  # noqa: S310
        try:
            with urllib.request.urlopen(request, timeout=timeout) as answer:  # noqa: S310
                pages[name] = answer.read().decode("utf-8")
        except (urllib.error.URLError, TimeoutError, ValueError) as exc:
            raise RuntimeError(f"The timezone database did not answer: {exc}") from exc

    names: set[str] = set()
    for line in pages["zones"].splitlines():
        if line and not line.startswith("#"):
            columns = line.split("\t")
            if len(columns) >= 3:
                names.add(columns[2])
    for line in pages["links"].splitlines():
        columns = line.split()
        if len(columns) >= 3 and columns[0] == "Link":
            names.add(columns[2])
    return names, pages["version"].strip()


def check_timezones(rows: dict[str, Any], *, timeout: int = 30) -> TimezoneCheck:
    """Check the catalogue's timezone names against the database that defines them.

    Parameters
    ----------
    rows : dict
        The catalogue, keyed by ISO 3166-1 alpha-2 code.
    timeout : int, optional
        Seconds to allow each request.

    Returns
    -------
    TimezoneCheck
        What was checked and what did not check out.

    Examples
    --------
    >>> check_timezones({}).unknown
    {}
    """
    if not rows:
        return TimezoneCheck(version="", known=0, unknown={})
    names, version = _iana_zones(timeout)
    known = 0
    unknown: dict[str, list[str]] = {}
    for key, row in rows.items():
        strays = [zone for zone in (row.get("timezones") or []) if zone not in names]
        known += len(row.get("timezones") or []) - len(strays)
        if strays:
            unknown[key] = strays
    return TimezoneCheck(version=version, known=known, unknown=unknown)


def apply_timezone_check(path: Path, check: TimezoneCheck) -> int:
    r"""Stamp a verified timezone list with the release it was checked against.

    The list itself is not rewritten. The database says which zones exist, not
    which of them a country uses in the way this catalogue means it, and a
    refresh that replaced the list would throw away the compatibility names that
    are exactly what a real machine reports.

    Parameters
    ----------
    path : pathlib.Path
        The catalogue to edit. It must already exist.
    check : TimezoneCheck
        A check that passed. One that did not is refused: stamping a list as
        verified when it is not would be the whole mistake in miniature.

    Returns
    -------
    int
        How many rows were stamped.

    Raises
    ------
    FileNotFoundError
        When the path is not there.
    ValueError
        When the check found a zone IANA does not publish.

    Examples
    --------
    >>> import tempfile, pathlib
    >>> text = 'countries:\n  - key: "FR"\n    timezones: ["Europe/Paris"]\n'
    >>> with tempfile.TemporaryDirectory() as folder:
    ...     target = pathlib.Path(folder) / "grid.yaml"
    ...     _ = target.write_text(text, encoding="utf-8")
    ...     written = apply_timezone_check(target, TimezoneCheck("2026e", 1, {}))
    ...     body = target.read_text(encoding="utf-8")
    >>> written
    1
    >>> 'timezones_tzdb_version: "2026e"' in body
    True
    """
    if not path.is_file():
        raise FileNotFoundError(
            f"{path} is not there. This edits a catalogue; it does not create one."
        )
    if not check.ok:
        raise ValueError(
            f"{check.unknown} are not zones the database publishes. Nothing is "
            "stamped: marking a list as checked when it did not check out would be "
            "this package's own mistake, in miniature."
        )
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    written = 0
    out: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith(
            ("timezones_source_url:", "timezones_retrieved_date:", "timezones_tzdb_version:")
        ):
            continue
        out.append(line)
        if stripped.startswith("timezones:"):
            indent = line[: len(line) - len(line.lstrip())]
            out.append(f'{indent}timezones_source_url: "{check.source}"\n')
            out.append(f'{indent}timezones_retrieved_date: "{check.retrieved}"\n')
            out.append(f'{indent}timezones_tzdb_version: "{check.version}"\n')
            written += 1
    path.write_text("".join(out), encoding="utf-8")
    return written
