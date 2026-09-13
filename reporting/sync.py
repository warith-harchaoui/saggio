"""
Copy the report's authored assets into the package that ships them.

Module summary
--------------
The report's stylesheet, script, translations, logo and document shell are
authored in ``reporting/``, where they are a stylesheet, a script, a YAML file, a
PNG and an HTML file rather than five strings quoted inside Python. The renderer
reads them through :mod:`importlib.resources`, which can only reach inside the
package, so a copy lives at ``saggio/data/report/`` and is what
the wheel ships.

This script keeps the two in step, in one direction only: ``reporting/`` is the
original and the package copy is the artefact. ``--check`` reports drift without
writing anything, which is what the contract test and continuous integration
call, so an edit made in the wrong copy fails the build instead of silently
shipping.

Usage example
-------------
>>> from reporting.sync import assets_out_of_date  # doctest: +SKIP
>>> assets_out_of_date()                           # doctest: +SKIP
[]

Author
------
Warith Harchaoui
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path
from typing import Final

#: Where the assets are authored.
SOURCE_DIR: Final[Path] = Path(__file__).resolve().parent

#: Where the package reads them from, and what the wheel ships.
PACKAGE_DIR: Final[Path] = SOURCE_DIR.parent / "saggio" / "data" / "report"

#: The assets themselves. Anything else in ``reporting/`` documents the template
#: rather than being part of it, and is not copied.
ASSETS: Final[tuple[str, ...]] = (
    "report.html",
    "report.css",
    "report.js",
    "i18n.yaml",
    "logo.png",
)


def assets_out_of_date() -> list[str]:
    """Return the names of the assets whose package copy differs from the original.

    Returns
    -------
    list of str
        Asset names, in the order of :data:`ASSETS`. Empty when the two
        directories agree. A missing package copy counts as differing, which is
        the state of a fresh checkout before this script has ever run.

    Examples
    --------
    >>> isinstance(assets_out_of_date(), list)
    True
    """
    stale: list[str] = []
    for name in ASSETS:
        source, packaged = SOURCE_DIR / name, PACKAGE_DIR / name
        if not packaged.exists() or packaged.read_bytes() != source.read_bytes():
            stale.append(name)
    return stale


def sync() -> list[str]:
    """Copy every asset into the package, and say which ones actually moved.

    Returns
    -------
    list of str
        The names that were written. Empty when everything already agreed, so a
        run on an unchanged tree touches no file and no timestamp.

    Examples
    --------
    >>> sync() if not assets_out_of_date() else []   # never copies from a doctest
    []
    """
    stale = assets_out_of_date()
    PACKAGE_DIR.mkdir(parents=True, exist_ok=True)
    for name in stale:
        shutil.copy2(SOURCE_DIR / name, PACKAGE_DIR / name)
    return stale


def main(argv: list[str] | None = None) -> int:
    """Run the script.

    Parameters
    ----------
    argv : list of str or None
        Arguments, without the program name. ``None`` reads :data:`sys.argv`.

    Returns
    -------
    int
        ``0`` when the copies agree, or were made to agree. ``1`` under
        ``--check`` when they do not, which is the signal a build wants.

    Examples
    --------
    >>> isinstance(main(["--check"]), int)
    True
    """
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    parser.add_argument(
        "--check",
        action="store_true",
        help="report drift and exit non-zero, without writing anything",
    )
    args = parser.parse_args(argv)

    stale = assets_out_of_date()
    if args.check:
        for name in stale:
            print(f"out of date: saggio/data/report/{name}", file=sys.stderr)
        if stale:
            print("run `python reporting/sync.py` to update the packaged copy", file=sys.stderr)
        return 1 if stale else 0

    for name in sync():
        print(f"copied {name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
