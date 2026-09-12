"""
The command line, as a thin adapter over the library.

Module summary
--------------
Everything the command line can do, the library can do, because the command line
does nothing but parse arguments, call the library, and print. The split is kept
honest by putting the parser in :mod:`app` and the verbs in :mod:`commands`, with
no business logic in either.

Usage example
-------------
>>> from running_code_cost_helper.cli import build_parser
>>> build_parser().parse_args(["render", "cost.yaml", "-f", "html"]).format
'html'

Author
------
Warith Harchaoui
"""

from __future__ import annotations

from .app import PROGRAM, build_parser, main, run
from .exit_codes import DECLINED, INVALID, MEANINGS, OK, UNAVAILABLE, USAGE

__all__ = [
    "DECLINED",
    "INVALID",
    "MEANINGS",
    "OK",
    "PROGRAM",
    "UNAVAILABLE",
    "USAGE",
    "build_parser",
    "main",
    "run",
]
