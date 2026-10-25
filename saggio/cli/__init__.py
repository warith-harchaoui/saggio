"""
The command line, as a thin adapter over the library.

Module summary
--------------
Everything the command line can do, the library can do, because the command line
does nothing but parse arguments, call the library, and print. The split is kept
honest by putting the command declarations in :mod:`app` and the verbs in
:mod:`commands`, with no business logic in either. Both are built on click, and
only on click.

Usage example
-------------
>>> from saggio.cli import build_cli
>>> sorted(build_cli().commands)[:2]
['audit', 'catalog']

Author
------
Warith Harchaoui
"""

from __future__ import annotations

from .app import PROGRAM, accepts, build_cli, main, run
from .exit_codes import DECLINED, INVALID, MEANINGS, OK, UNAVAILABLE, USAGE

__all__ = [
    "DECLINED",
    "INVALID",
    "MEANINGS",
    "OK",
    "PROGRAM",
    "UNAVAILABLE",
    "USAGE",
    "accepts",
    "build_cli",
    "main",
    "run",
]
