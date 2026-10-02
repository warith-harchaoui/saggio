"""Checking the timezone names against the database that defines them.

Module summary
--------------
This verifies rather than replaces. The database says which zones exist, not
which of them a country uses in the way this catalogue means it, and the
catalogue deliberately carries compatibility names like ``Europe/Kiev`` because
those are what a real machine reports. A zone published under no name at all
fails the check rather than being corrected: that is a question, not a fix.

Author
------
Warith Harchaoui
"""

from __future__ import annotations

import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Final

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
