"""
The catalogues: sourced facts about hardware, grids, providers, and services.

Module summary
--------------
Some of what a cost model needs is not about your code at all. What a GPU draws,
what a kilowatt-hour emits in Poland, what overhead a datacenter adds, where a
given API publishes its prices: these are facts about the world, they go out of
date, and none of them should be a literal buried in a renderer. They live here
instead, in provenance-carrying YAML.

Two copies of every catalogue exist. The **bundled** one ships inside the
package and is the same for everyone. The **overlay** lives in the user's config
directory and holds rows they or an agent added locally, which take precedence by
key. A row added to the overlay works immediately and can later be offered to the
public catalogue as a pull request; :func:`add_row` is what writes it, and
``saggio catalog add`` is the same thing from a terminal.

Two rules keep the catalogues worth trusting. A row cannot be added without a
``source_url`` and a ``retrieved_date``, so nothing enters as folklore. And every
row goes stale on a schedule that matches how fast the world moves: a datasheet
power figure holds for a year, an electricity price for a month.

Usage example
-------------
>>> from saggio.catalog.registry import Catalog
>>> gpus = Catalog.bundled("hardware").rows("gpus")
>>> gpus["A100"]["tdp_w"]
400

Author
------
Warith Harchaoui
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from importlib import resources
from pathlib import Path
from typing import Any, Final

import os_helper as osh
import platformdirs
import yaml

#: The catalogue files that ship with the package, by name.
BUNDLED_CATALOGS: Final[tuple[str, ...]] = (
    "hardware",
    "grid",
    "providers",
    "instances",
    "services",
)

#: Which section of which catalogue each row kind lives in. The kind is what a
#: user names on the command line, so it is short and singular.
SECTION_OF_KIND: Final[dict[str, tuple[str, str]]] = {
    "gpu": ("hardware", "gpus"),
    "cpu": ("hardware", "cpus"),
    "country": ("grid", "countries"),
    "provider": ("providers", "providers"),
    "instance": ("instances", "instances"),
    "service": ("services", "services"),
}

#: How long a row of each kind stays believable, in days. Hardware datasheets do
#: not move; tariffs and grid mixes do. A single global threshold would either
#: nag about a GPU's TDP or let last year's electricity price through unremarked.
STALE_AFTER_DAYS: Final[dict[str, int]] = {
    "gpu": 365,
    "cpu": 365,
    "instance": 365,
    "country": 31,
    "provider": 365,
    "service": 31,
}

#: Fallback when a kind has no explicit threshold.
DEFAULT_STALE_AFTER_DAYS: Final[int] = 31

#: The ``source_url`` reserved for a figure this package chose itself, such as a
#: generic fallback. It is honest about being an internal default rather than
#: pretending to a citation.
INTERNAL_DEFAULT_SOURCE: Final[str] = "internal-default"

#: Application name used to find the per-user config directory.
_APP_NAME: Final[str] = "saggio"


def overlay_directory() -> Path:
    """Return the per-user directory holding local catalogue additions.

    Returns
    -------
    pathlib.Path
        A platform-appropriate config directory. It is created if missing, so
        callers may write into it without checking first.

    Examples
    --------
    >>> overlay_directory().name
    'saggio'
    """
    folder = Path(platformdirs.user_config_dir(_APP_NAME))
    osh.make_directory(str(folder))
    return folder


def _read_yaml(path: Path) -> dict[str, Any]:
    """Read a YAML mapping from disk, returning an empty mapping when absent.

    Parameters
    ----------
    path : pathlib.Path
        The file to read.

    Returns
    -------
    dict
        The parsed mapping, or ``{}`` when the file is missing, empty, or holds
        something other than a mapping. A broken overlay must never stop the tool
        from running with its bundled data.

    Examples
    --------
    >>> _read_yaml(Path("/nonexistent/none.yaml"))
    {}
    """
    if not osh.file_exists(str(path), check_empty=True):
        return {}
    try:
        parsed = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        osh.warning(f"Ignoring unreadable catalogue {path}: {exc}")
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _bundled_text(name: str) -> str:
    """Return the text of a bundled catalogue file.

    Parameters
    ----------
    name : str
        A catalogue name from :data:`BUNDLED_CATALOGS`.

    Returns
    -------
    str
        The YAML text as shipped inside the package.

    Raises
    ------
    FileNotFoundError
        If the package was built without the catalogue, which means the wheel is
        broken rather than the user's setup.

    Examples
    --------
    >>> "gpus:" in _bundled_text("hardware")
    True
    """
    return resources.files("saggio.data").joinpath(f"{name}.yaml").read_text("utf-8")


def days_since(retrieved_date: object, *, today: date | None = None) -> int | None:
    """Return how many days old a provenance date is.

    Parameters
    ----------
    retrieved_date : object
        An ISO ``YYYY-MM-DD`` string, or anything else.
    today : datetime.date or None, optional
        The day to measure from; defaults to the real today. Injectable so tests
        do not drift as the calendar moves.

    Returns
    -------
    int or None
        The age in days, or ``None`` when the value is not a calendar date.

    Examples
    --------
    >>> from datetime import date
    >>> days_since("2026-01-01", today=date(2026, 3, 2))
    60
    >>> days_since(date(2026, 1, 1), today=date(2026, 3, 2))
    60
    >>> days_since(None) is None
    True
    """
    # A hand-edited overlay with an unquoted date parses straight to a
    # datetime.date, which is at least as good as the string form; rejecting
    # it made perfectly fresh rows read as stale.
    if isinstance(retrieved_date, datetime):
        then = retrieved_date.date()
    elif isinstance(retrieved_date, date):
        then = retrieved_date
    elif isinstance(retrieved_date, str):
        try:
            then = date.fromisoformat(retrieved_date)
        except ValueError:
            return None
    else:
        return None
    return ((today or date.today()) - then).days


def stale_after_days(kind: str) -> int:
    """Return how long a row of this kind stays believable.

    Parameters
    ----------
    kind : str
        A row kind such as ``gpu`` or ``country``.

    Returns
    -------
    int
        The threshold in days.

    Examples
    --------
    >>> stale_after_days("gpu") > stale_after_days("country")
    True
    >>> stale_after_days("invented")
    31
    """
    return STALE_AFTER_DAYS.get(kind, DEFAULT_STALE_AFTER_DAYS)


def carries_numbers(row: dict[str, Any]) -> bool:
    """Return whether a catalogue row asserts any number of its own.

    The distinction matters for staleness. A hardware row asserts a wattage and
    can therefore be out of date. A service row asserts nothing numeric: it says
    what the service is, how to spot it in code, and which page publishes its
    prices. A pointer to a price cannot go stale; the price a user copied out of
    it can, and that lives in their model where the validator watches it.

    Parameters
    ----------
    row : dict
        The catalogue row.

    Returns
    -------
    bool
        ``True`` when any field holds a number, booleans excluded.

    Examples
    --------
    >>> carries_numbers({"key": "A100", "tdp_w": 400})
    True
    >>> carries_numbers({"key": "openai", "pricing_source_url": "https://example.invalid"})
    False
    """
    return any(
        isinstance(value, (int, float)) and not isinstance(value, bool) for value in row.values()
    )


def is_stale(row: dict[str, Any], kind: str, *, today: date | None = None) -> bool:
    """Return whether a catalogue row is past its refresh date.

    Parameters
    ----------
    row : dict
        The row, expected to carry ``retrieved_date`` when it asserts a number.
    kind : str
        The row kind, which sets the threshold.
    today : datetime.date or None, optional
        The day to measure from.

    Returns
    -------
    bool
        ``True`` when the row asserts a number and that number is older than the
        threshold for its kind, or carries no usable date at all. A row asserting
        no number never goes stale; see :func:`carries_numbers`.

    Examples
    --------
    >>> from datetime import date
    >>> is_stale({"tdp_w": 1, "retrieved_date": "2026-01-01"}, "country", today=date(2026, 6, 1))
    True
    >>> is_stale({"tdp_w": 1, "retrieved_date": "2026-01-01"}, "gpu", today=date(2026, 6, 1))
    False
    >>> is_stale({"tdp_w": 1}, "gpu")
    True
    >>> is_stale({"pricing_source_url": "https://example.invalid"}, "service")
    False
    >>> is_stale({"tdp_w": 1, "retrieved_date": "2030-01-01"}, "gpu", today=date(2026, 1, 1))
    True
    """
    if not carries_numbers(row):
        return False
    age = days_since(row.get("retrieved_date"), today=today)
    if age is None or age < 0:
        # A future date is a typo, not extra freshness; a typo'd year must not
        # buy the row years of unearned trust.
        return True
    return age > stale_after_days(kind)


def require_provenance(row: dict[str, Any]) -> None:
    """Refuse a catalogue row that does not say where its numbers came from.

    Parameters
    ----------
    row : dict
        The candidate row.

    Raises
    ------
    ValueError
        If ``key`` is missing; or, for a row that asserts numbers, if
        ``source_url`` or ``retrieved_date`` is missing or the date is not a
        calendar date. A row asserting no number — a service pointer, say —
        needs no provenance, because it states nothing that could be sourced;
        the bundled service rows are shaped exactly this way, and the
        sanctioned ``saggio catalog add`` flow has to be able to produce their
        like.

    Examples
    --------
    >>> require_provenance({"key": "X", "source_url": "u", "retrieved_date": "2026-01-01"})
    >>> require_provenance({"key": "svc", "pricing_source_url": "https://x.invalid"})
    >>> require_provenance({"key": "X", "tdp_w": 400})
    Traceback (most recent call last):
        ...
    ValueError: A catalogue row needs a source_url saying where its numbers came from.
    """
    if not str(row.get("key") or "").strip():
        raise ValueError("A catalogue row needs a key.")
    if not carries_numbers(row):
        return
    if not str(row.get("source_url") or "").strip():
        raise ValueError("A catalogue row needs a source_url saying where its numbers came from.")
    retrieved = row.get("retrieved_date")
    if days_since(retrieved) is None:
        raise ValueError(
            f"A catalogue row needs a retrieved_date as YYYY-MM-DD, got {retrieved!r}."
        )


@dataclass(slots=True)
class Catalog:
    """One catalogue: its bundled rows, overlaid with the user's own.

    Parameters
    ----------
    name : str
        The catalogue name, one of :data:`BUNDLED_CATALOGS`.
    data : dict
        The merged mapping of section name to list of rows.
    overlay_path : pathlib.Path or None
        Where local additions are written, or ``None`` for a catalogue loaded
        without an overlay.

    Examples
    --------
    >>> Catalog.bundled("providers").row("providers", "gcp")["pue"]
    1.09
    """

    name: str
    data: dict[str, Any] = field(default_factory=dict)
    overlay_path: Path | None = None

    @classmethod
    def load(cls, name: str, *, overlay: Path | None = None) -> Catalog:
        """Load a catalogue, merging the user's overlay over the bundled rows.

        Parameters
        ----------
        name : str
            The catalogue name.
        overlay : pathlib.Path or None, optional
            Directory holding the overlay files. Defaults to
            :func:`overlay_directory`. Pass an explicit directory in tests so a
            developer's own additions never change the result.

        Returns
        -------
        Catalog
            The merged catalogue.

        Raises
        ------
        ValueError
            If ``name`` is not a bundled catalogue.

        Examples
        --------
        >>> Catalog.load("grid").name
        'grid'
        """
        if name not in BUNDLED_CATALOGS:
            known = ", ".join(BUNDLED_CATALOGS)
            raise ValueError(f"Unknown catalogue {name!r}. Known catalogues: {known}.")
        bundled = yaml.safe_load(_bundled_text(name)) or {}
        folder = overlay if overlay is not None else overlay_directory()
        overlay_file = folder / f"{name}.yaml"
        local = _read_yaml(overlay_file)

        merged: dict[str, Any] = {}
        for section in set(bundled) | set(local):
            base = bundled.get(section)
            extra = local.get(section)
            if isinstance(base, list) or isinstance(extra, list):
                merged[section] = _merge_rows(
                    base if isinstance(base, list) else [],
                    extra if isinstance(extra, list) else [],
                )
            else:
                merged[section] = extra if extra is not None else base
        return cls(name=name, data=merged, overlay_path=overlay_file)

    @classmethod
    def bundled(cls, name: str) -> Catalog:
        """Return a catalogue exactly as shipped, ignoring any overlay.

        The doctests in this module run on developer machines, where a local
        ``saggio catalog add`` may have overlaid the very row a doctest asserts
        on; documentation that fails because the reader once used the tool is
        documentation lying about the tool. Anything that needs the user's own
        rows should call :meth:`load`.

        Parameters
        ----------
        name : str
            The catalogue name.

        Returns
        -------
        Catalog
            The bundled rows only, with no overlay path to write back to.

        Examples
        --------
        >>> Catalog.bundled("hardware").row("gpus", "A100")["tdp_w"]
        400
        """
        catalog = cls.load(name, overlay=Path("/nonexistent-overlay"))
        catalog.overlay_path = None
        return catalog

    def sections(self) -> tuple[str, ...]:
        """Return the row sections this catalogue holds.

        Returns
        -------
        tuple of str
            Section names, sorted, excluding scalar metadata such as the schema
            version.

        Examples
        --------
        >>> Catalog.bundled("hardware").sections()
        ('cpus', 'gpus')
        """
        return tuple(sorted(key for key, value in self.data.items() if isinstance(value, list)))

    def rows(self, section: str) -> dict[str, dict[str, Any]]:
        """Return one section's rows, keyed by their ``key``.

        Parameters
        ----------
        section : str
            The section name, for example ``gpus``.

        Returns
        -------
        dict
            Mapping of row key to row. Empty when the section is absent, so a
            caller can iterate without guarding.

        Examples
        --------
        >>> "A100" in Catalog.bundled("hardware").rows("gpus")
        True
        >>> Catalog.bundled("hardware").rows("nonexistent")
        {}
        """
        entries = self.data.get(section)
        if not isinstance(entries, list):
            return {}
        return {
            str(row["key"]): row
            for row in entries
            if isinstance(row, dict) and str(row.get("key") or "").strip()
        }

    def row(self, section: str, key: str) -> dict[str, Any] | None:
        """Return one row, or ``None`` when the catalogue does not know it.

        Parameters
        ----------
        section : str
            The section name.
        key : str
            The row key.

        Returns
        -------
        dict or None
            The row, or ``None``. A miss is a normal outcome: it is how the tool
            knows to go and look the fact up.

        Examples
        --------
        >>> Catalog.bundled("grid").row("countries", "FR")["name"]
        'France'
        >>> Catalog.bundled("grid").row("countries", "ZZ") is None
        True
        """
        return self.rows(section).get(key)

    def keys(self, section: str) -> tuple[str, ...]:
        """Return the keys in a section, in catalogue order.

        Parameters
        ----------
        section : str
            The section name.

        Returns
        -------
        tuple of str
            The row keys.

        Examples
        --------
        >>> "on-prem" in Catalog.bundled("providers").keys("providers")
        True
        """
        return tuple(self.rows(section))


def _merge_rows(bundled: list[Any], overlay: list[Any]) -> list[dict[str, Any]]:
    """Merge overlay rows over bundled rows, matching on ``key``.

    Parameters
    ----------
    bundled : list
        Rows shipped with the package.
    overlay : list
        Rows the user or an agent added locally.

    Returns
    -------
    list of dict
        Bundled rows in their original order, each updated column by column by
        the overlay row of the same key when there is one, followed by the
        overlay's new keys. The order matters because it is the order reports
        and dropdowns read in.

    Examples
    --------
    >>> _merge_rows([{"key": "a", "v": 1, "w": 9}], [{"key": "a", "v": 2}, {"key": "b"}])
    [{'key': 'a', 'v': 2, 'w': 9}, {'key': 'b'}]
    """
    local: dict[str, dict[str, Any]] = {}
    for row in overlay:
        if not isinstance(row, dict):
            continue
        key = row.get("key")
        if isinstance(key, bool) or not str(key or "").strip():
            # YAML 1.1 reads an unquoted NO as the boolean false, at which
            # point the user's Norway override would vanish without a trace.
            # Dropping the row is right; dropping it silently is not.
            osh.warning(
                f"An overlay row's key reads as {key!r} rather than text; YAML "
                'turns unquoted NO/YES/ON/OFF into booleans. Quote the key ("NO") '
                "and the row will load."
            )
            continue
        local[str(key)] = row
    merged: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in bundled:
        if not isinstance(row, dict):
            continue
        key = str(row.get("key") or "")
        seen.add(key)
        override = local.get(key)
        if override is None:
            merged.append(row)
        else:
            # Column-level, not row-level: an overlay that refreshes France's
            # electricity price must not silently erase its carbon intensity
            # and timezones because it did not restate them.
            merged.append({**row, **override})
    for key, row in local.items():
        if key not in seen:
            merged.append(row)
    return merged


def add_row(kind: str, row: dict[str, Any], *, overlay: Path | None = None) -> Path:
    """Add a row to the user's overlay, refusing one with no provenance.

    This is what an agent calls when a lookup misses: search the web once, find
    the datasheet or the tariff page, and record the row with the URL it came
    from. The row is usable immediately and can be offered upstream later.

    Parameters
    ----------
    kind : str
        A row kind from :data:`SECTION_OF_KIND`.
    row : dict
        The row, carrying at least ``key``, ``source_url``, and ``retrieved_date``.
    overlay : pathlib.Path or None, optional
        Directory to write into; defaults to :func:`overlay_directory`.

    Returns
    -------
    pathlib.Path
        The overlay file written.

    Raises
    ------
    ValueError
        If the kind is unknown, or the row has no provenance.

    Examples
    --------
    >>> import tempfile, pathlib
    >>> with tempfile.TemporaryDirectory() as folder:
    ...     written = add_row(
    ...         "gpu",
    ...         {"key": "TEST-1", "tdp_w": 1, "source_url": "https://example.invalid",
    ...          "retrieved_date": "2026-09-12"},
    ...         overlay=pathlib.Path(folder),
    ...     )
    ...     written.name
    'hardware.yaml'
    """
    if kind not in SECTION_OF_KIND:
        known = ", ".join(sorted(SECTION_OF_KIND))
        raise ValueError(f"Unknown catalogue kind {kind!r}. Known kinds: {known}.")
    require_provenance(row)
    catalog_name, section = SECTION_OF_KIND[kind]
    folder = overlay if overlay is not None else overlay_directory()
    osh.make_directory(str(folder))
    target = folder / f"{catalog_name}.yaml"

    current = _read_yaml(target)
    entries = current.get(section)
    entries = entries if isinstance(entries, list) else []
    # Replace in place when the key already exists, so re-adding a row after a
    # refresh updates it instead of leaving two rows that disagree.
    replaced = False
    for index, existing in enumerate(entries):
        if isinstance(existing, dict) and str(existing.get("key")) == str(row["key"]):
            entries[index] = row
            replaced = True
            break
    if not replaced:
        entries.append(row)
    current[section] = entries
    target.write_text(
        yaml.safe_dump(current, sort_keys=False, allow_unicode=True, width=100),
        encoding="utf-8",
    )
    return target


#: How soon a row has to be from expiring before this says so. A week is enough
#: notice to re-read a source without it becoming noise every build.
EXPIRING_WITHIN_DAYS: Final[int] = 7


def expiring_report(
    *, overlay: Path | None = None, today: date | None = None, within: int = EXPIRING_WITHIN_DAYS
) -> dict[str, list[tuple[str, int]]]:
    """Return the rows that are still fresh but about to stop being.

    A gate that turns red overnight with no warning gets the number re-dated in a
    hurry rather than re-read, which is the one outcome this whole mechanism
    exists to prevent. So a row inside its window but near the end of it is
    reported separately: nothing fails, and somebody has a week to go and look at
    the source properly.

    Parameters
    ----------
    overlay : pathlib.Path or None, optional
        Overlay directory to include.
    today : datetime.date or None, optional
        The day to measure from.
    within : int, optional
        How many days ahead to look.

    Returns
    -------
    dict
        Mapping of row kind to ``(key, days left)`` pairs, soonest first. Kinds
        with nothing expiring are omitted. A row that is already stale is not
        here: it is in :func:`stale_report`, and reporting it twice would make
        the warning compete with the failure.

    Examples
    --------
    >>> from datetime import date
    >>> report = expiring_report(today=date(2020, 1, 1))
    >>> isinstance(report, dict)
    True
    """
    soon: dict[str, list[tuple[str, int]]] = {}
    for kind, (catalog_name, section) in SECTION_OF_KIND.items():
        limit = STALE_AFTER_DAYS.get(kind, DEFAULT_STALE_AFTER_DAYS)
        catalog = Catalog.load(catalog_name, overlay=overlay)
        rows: list[tuple[str, int]] = []
        for key, row in catalog.rows(section).items():
            if row.get("source_url") == INTERNAL_DEFAULT_SOURCE:
                continue
            age = days_since(row.get("retrieved_date"), today=today)
            if age is None or age < 0 or age > limit:
                continue
            left = limit - age
            if left <= within:
                rows.append((key, left))
        if rows:
            soon[kind] = sorted(rows, key=lambda row: (row[1], row[0]))
    return soon


def stale_report(*, overlay: Path | None = None, today: date | None = None) -> dict[str, list[str]]:
    """Return the keys of every catalogue row that is past its refresh date.

    Used as a continuous-integration gate: a build that ships numbers nobody has
    looked at for a year is shipping folklore.

    Parameters
    ----------
    overlay : pathlib.Path or None, optional
        Overlay directory to include.
    today : datetime.date or None, optional
        The day to measure from.

    Returns
    -------
    dict
        Mapping of row kind to the sorted keys that are stale. Kinds with nothing
        stale are omitted, so an empty mapping means everything is fresh.

    Examples
    --------
    >>> import tempfile, pathlib
    >>> from datetime import date
    >>> with tempfile.TemporaryDirectory() as folder:
    ...     report = stale_report(overlay=pathlib.Path(folder), today=date(2020, 1, 1))
    >>> "gpu" in report  # a retrieved_date after `today` is a typo, not freshness
    True
    """
    stale: dict[str, list[str]] = {}
    for kind, (catalog_name, section) in SECTION_OF_KIND.items():
        catalog = Catalog.load(catalog_name, overlay=overlay)
        keys = [
            key
            for key, row in catalog.rows(section).items()
            if row.get("source_url") != INTERNAL_DEFAULT_SOURCE and is_stale(row, kind, today=today)
        ]
        if keys:
            stale[kind] = sorted(keys)
    return stale
