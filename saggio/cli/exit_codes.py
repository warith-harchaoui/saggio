"""
What the command line returns, and what each number means.

Module summary
--------------
A command-line tool is something other programs run, so its exit codes are part
of its interface and are documented here rather than scattered as literals. The
distinction that matters is between *the model is wrong* and *you asked wrongly*:
a continuous-integration job wants to fail on the first and stop on the second,
and it cannot tell them apart from a shared code of one.

Usage example
-------------
>>> from saggio.cli.exit_codes import OK, INVALID
>>> OK == 0 and INVALID == 1
True

Author
------
Warith Harchaoui
"""

from __future__ import annotations

from typing import Final

#: Everything worked.
OK: Final[int] = 0

#: The model, the catalogue, or the comparison failed its own rules. The command
#: ran correctly; the thing it looked at is not sound.
INVALID: Final[int] = 1

#: The command was asked for something it cannot do: an unknown template, a file
#: that is not there, a format it does not produce.
USAGE: Final[int] = 2

#: The user declined something the command needed, such as consent to run
#: downloaded code. Not an error, and deliberately not zero.
DECLINED: Final[int] = 3

#: A dependency outside this package is missing or failed: git, Pandoc, a network.
UNAVAILABLE: Final[int] = 4

#: What each code means, for the help text and for anyone reading a CI log.
MEANINGS: Final[dict[int, str]] = {
    OK: "Everything worked.",
    INVALID: "The model or catalogue failed its own rules.",
    USAGE: "The command was asked for something it cannot do.",
    DECLINED: "Consent was declined for something the command needed.",
    UNAVAILABLE: "An external dependency is missing or failed.",
}
