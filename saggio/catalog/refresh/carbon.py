"""The grid's operating emissions, from Ember.

Module summary
--------------
What a kilowatt-hour emits in a country, read from the one source that answers a
machine. It needs a free key, and it substitutes nothing when there is none: the
open series that looks equivalent measures lifecycle rather than operating
emissions, and swapping one for the other would change what every committed
model means without changing how trustworthy any of them looks.

Author
------
Warith Harchaoui
"""

from __future__ import annotations

import csv
import io
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Final

#: Where a machine reads the figures. Not what a row cites: asked without a key
#: it answers ``{"detail": "No API key set"}`` and HTTP 403, so a reader who
#: followed it from a catalogue row would be shown no number at all -- the same
#: failure as :data:`~saggio.catalog.refresh.embodied.EMBODIED_CPU_API`, which
#: answers a reader with the wrong number and is kept out of citations for it.
EMBER_API: Final[str] = "https://api.ember-energy.org/v1/carbon-intensity/yearly"


#: What a row cites, and what a reader can actually open. Ember publishes the
#: same series here as a CC-BY-4.0 download, so this is not a page that merely
#: discusses the figure: it is where the figure is published. Checked rather
#: than assumed -- the file behind it agrees with the API on 36 of the 38
#: countries on file to better than half a percent, thirty of them to better
#: than a tenth, several to three decimal places. The two that disagreed said
#: something worth knowing, and both are recorded in `CHANGELOG.md`.
EMBER_CITATION: Final[str] = "https://ember-energy.org/data/yearly-electricity-data/"


#: The file that page offers, which is what :func:`fetch_grid_public` reads. No
#: key, which is the point: a catalogue whose most important column can only be
#: re-read by whoever holds a credential is a catalogue that stops being re-read.
EMBER_PUBLIC_CSV: Final[str] = (
    "https://files.ember-energy.org/public-downloads/generation/outputs/"
    "release_generation_yearly_global.csv"
)


#: The row of that file that carries the whole grid, rather than one fuel. The
#: column holds an intensity per source as well, and reading the wrong row would
#: put the carbon intensity of a country's coal fleet under its name.
EMBER_TOTAL_ROW: Final[str] = "Total generation"


#: The column that holds the figure, spelled as the file spells it. Named rather
#: than found by position: the file has gained columns before, and a refresh that
#: reads the wrong one would write plausible numbers under the right names.
EMBER_INTENSITY_COLUMN: Final[str] = "Emissions intensity (gCO2e/kWh)"


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
        The newest data year anything in this refresh describes. Not today's
        date: a number read today from a 2025 release is a 2025 number, and the
        row records both. It is a headline, not a per-row fact -- see `years`.
    rows : dict
        ISO 3166-1 alpha-2 key to carbon intensity in gCO2e per kWh.
    years : dict
        Key to the data year *that country's own figure* describes. Separate
        from `year` because the source does not publish every country up to the
        same year, and collapsing the two is how the catalogue came to carry
        Ukraine's 2022 figure stamped 2025: every other country had a 2025
        reading, the newest year won, and one row was left claiming a currency
        it did not have. A reader cannot see that from the number -- 250.5 is a
        perfectly ordinary intensity -- so only the stamp could have said it.
    skipped : dict
        Key to the reason this refresh has nothing to say about it.
    source : str
        The URL that answered.
    citation : str
        The URL a refreshed row should cite, which is not always the one that
        answered. An endpoint that needs a key answers a machine and shows a
        reader an error; the page that publishes the same series shows them the
        figure. Rows cite the second.

    Examples
    --------
    >>> GridRefresh(year=2025, rows={"FR": 41.0}, skipped={}, source="x").year
    2025
    >>> GridRefresh(2025, {"UA": 250.5}, {}, "x", years={"UA": 2022}).years["UA"]
    2022
    """

    year: int | None
    rows: dict[str, float]
    skipped: dict[str, str]
    source: str
    retrieved: str = field(default_factory=lambda: date.today().isoformat())
    years: dict[str, int] = field(default_factory=dict)
    citation: str = EMBER_CITATION

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

    # One year per country, not one year for the refresh. Ember does not publish
    # every country up to the same year -- Ukraine's series stops in 2022 while
    # the rest reach 2025 -- and the newest of them is nobody's year but its own.
    found_years = {code: found for code, (found, _) in latest.items()}
    return GridRefresh(
        year=max(found_years.values()) if found_years else year,
        rows={code: value for code, (_, value) in latest.items()},
        skipped=skipped,
        source=EMBER_API,
        years=found_years,
    )


def fetch_grid_public(
    keys: list[str] | tuple[str, ...],
    *,
    year: int | None = None,
    timeout: float = 120.0,
) -> GridRefresh:
    """Read the same figures from the dataset Ember publishes openly.

    The API in :func:`fetch_grid` is Ember's machine interface and needs a key.
    This reads Ember's published yearly dataset, which needs none, carries the
    same series, and is the file behind the page every refreshed row cites. That
    matters beyond convenience: a column that only a credential-holder can
    re-read is a column that stops being re-read, and the alternative to
    re-reading is re-dating.

    It is not the substitution this module refuses. The refused one is a
    *different measure* -- lifecycle rather than operating emissions -- wearing
    the same units. This is the same publisher, the same series, and it was
    checked against the API country by country rather than assumed: see
    :data:`EMBER_CITATION`.

    Parameters
    ----------
    keys : list or tuple of str
        ISO 3166-1 alpha-2 country codes, as the catalogue keys them.
    year : int or None, optional
        Data year. ``None`` takes the most recent each country has, which is not
        the same year for every country. A year given is taken literally: a
        country the file does not publish for that year is named as skipped
        rather than quietly served its nearest.
    timeout : float, optional
        Seconds to wait on the network. Generous by default: this is a download
        of some tens of megabytes rather than a query.

    Returns
    -------
    GridRefresh
        What the file said, each country with its own data year, and what it
        had nothing to say about.

    Raises
    ------
    RuntimeError
        When the file could not be read, or when its header no longer carries a
        column this needs. The second is the one worth raising for: a renamed
        column would otherwise yield an empty refresh, and an empty refresh
        prints as "nothing moved", which reads exactly like a clean bill of
        health.

    Examples
    --------
    >>> fetch_grid_public([]).rows
    {}
    """
    if not keys:
        return GridRefresh(year=year, rows={}, skipped={}, source=EMBER_PUBLIC_CSV)

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
        return GridRefresh(year=year, rows={}, skipped=skipped, source=EMBER_PUBLIC_CSV)

    request = urllib.request.Request(EMBER_PUBLIC_CSV, headers={"Accept": "text/csv"})
    latest: dict[str, tuple[int, float]] = {}
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
            stream = io.TextIOWrapper(response, encoding="utf-8", newline="")
            reader = csv.DictReader(stream)
            columns = set(reader.fieldnames or ())
            needed = {"ISO 3 code", "Year", "Electricity source", EMBER_INTENSITY_COLUMN}
            absent = sorted(needed - columns)
            if absent:
                raise RuntimeError(
                    f"Ember's published dataset no longer has {', '.join(absent)}. "
                    "The catalogue is untouched: a refresh that silently found "
                    "nothing would print as a refresh that found nothing to change."
                )
            for record in reader:
                if record.get("Electricity source") != EMBER_TOTAL_ROW:
                    continue
                code = wanted.get(str(record.get("ISO 3 code") or "").upper())
                if code is None:
                    continue
                stamp = str(record.get("Year") or "")[:4]
                raw = record.get(EMBER_INTENSITY_COLUMN) or ""
                if not stamp.isdigit() or not raw:
                    continue
                try:
                    value = float(raw)
                except ValueError:
                    continue
                found_year = int(stamp)
                if year is not None and found_year != year:
                    continue
                if code not in latest or found_year > latest[code][0]:
                    latest[code] = (found_year, value)
    except (urllib.error.URLError, TimeoutError, UnicodeDecodeError, csv.Error) as exc:
        raise RuntimeError(f"Ember's published dataset did not read: {exc}") from exc

    for code in wanted.values():
        if code not in latest:
            skipped[code] = (
                f"the published dataset carries no intensity for this country in {year}."
                if year is not None
                else "the published dataset carries no intensity for this country."
            )

    found_years = {code: found for code, (found, _) in latest.items()}
    return GridRefresh(
        year=max(found_years.values()) if found_years else year,
        rows={code: value for code, (_, value) in latest.items()},
        skipped=skipped,
        source=EMBER_PUBLIC_CSV,
        years=found_years,
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

    Two things it writes are deliberately not the obvious ones. The row cites
    ``refresh.citation`` rather than ``refresh.source``, because the URL that
    answers a machine and the URL that shows a reader the figure are not the
    same URL here. And each row is stamped with its *own* data year from
    ``refresh.years``, falling back to the refresh's newest only where the
    source did not say -- stamping every row with the newest is what left
    Ukraine's 2022 reading claiming to be a 2025 one.

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

    A row whose own year is older than the refresh's newest keeps its own:

    >>> with tempfile.TemporaryDirectory() as folder:
    ...     target = pathlib.Path(folder) / "grid.yaml"
    ...     _ = target.write_text(text.replace('"FR"', '"UA"'), encoding="utf-8")
    ...     lagging = GridRefresh(2025, {"UA": 250.5}, {}, "ember", years={"UA": 2022})
    ...     _ = apply_grid(target, lagging)
    ...     body = target.read_text(encoding="utf-8")
    >>> "carbon_data_year: 2022" in body
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
            # This row's own data year, falling back to the refresh's newest only
            # when the source did not say. Writing `refresh.year` on every row is
            # what put a 2022 figure under a 2025 stamp.
            stamp = refresh.years.get(current, refresh.year)
            out.append(f"{indent}carbon_gco2e_per_kwh: {value:.1f}\n")
            out.append(f'{indent}carbon_source_url: "{refresh.citation}"\n')
            out.append(f'{indent}carbon_retrieved_date: "{refresh.retrieved}"\n')
            out.append(f"{indent}carbon_data_year: {stamp}\n")
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
