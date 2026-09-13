"""The documentation, checked against the code it documents.

Documentation rots by drifting away from the thing it describes, and the two ways
it drifts here are a command-line flag that was renamed and a claim about the
package that stopped being true. Both are checkable, so both are checked.
"""

from __future__ import annotations

import re
import shlex
from pathlib import Path

import pytest

from saggio import __version__
from saggio.cli.app import PROGRAM, build_parser

ROOT = Path(__file__).resolve().parents[2]

#: The documents that show commands a reader is expected to type.
DOCUMENTS = ["README.md", "LISEZMOI.md", "EXAMPLES.md", "EXEMPLES.md", "TRIGGERS.md"]

#: Both spellings of the console script.
_INVOCATION = re.compile(rf"^\s*(?:\$ )?(?:{re.escape(PROGRAM)}|saggio)\s+(.*)$")

#: A line ending in a backslash is continued on the next one.
_CONTINUED = re.compile(r"\\\s*$")


def commands_in(document: str) -> list[tuple[int, str]]:
    """Return every command-line invocation the document shows, with its line."""
    path = ROOT / document
    if not path.is_file():
        return []
    found: list[tuple[int, str]] = []
    pending: str | None = None
    pending_line = 0
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if pending is not None:
            pending += " " + line.strip()
            if not _CONTINUED.search(line):
                found.append((pending_line, pending.replace("\\", " ")))
                pending = None
            continue
        match = _INVOCATION.match(line)
        if not match:
            continue
        if _CONTINUED.search(line):
            pending, pending_line = match.group(1), number
            continue
        found.append((number, match.group(1)))
    return found


ALL_COMMANDS = [
    pytest.param(document, number, command, id=f"{document}:{number}")
    for document in DOCUMENTS
    for number, command in commands_in(document)
]


def test_the_documents_actually_show_commands() -> None:
    # A guard on the extraction itself: if the regex stopped matching, every
    # parametrised check below would pass by finding nothing to check.
    assert len(ALL_COMMANDS) > 25


@pytest.mark.parametrize(("document", "number", "command"), ALL_COMMANDS)
def test_every_documented_command_parses(document: str, number: int, command: str) -> None:
    parser = build_parser()
    # The prose pipes output into other tools and writes URLs with an ellipsis in
    # the middle; neither is the parser's business.
    command = command.split("|", 1)[0]
    argv = [
        "https://example.invalid" if part.startswith("http") else part
        for part in shlex.split(command, comments=True)
        if part not in {"...", "…"}
    ]
    try:
        parser.parse_args(argv)
    except SystemExit as exit_info:  # argparse exits on a flag it does not know.
        pytest.fail(
            f"{document}:{number} shows `{command}`, which the parser rejects ({exit_info})"
        )


@pytest.mark.parametrize("document", DOCUMENTS)
def test_no_document_shows_a_flag_that_was_renamed(document: str) -> None:
    path = ROOT / document
    if not path.is_file():
        pytest.skip(f"{document} is not in this repository")
    text = path.read_text(encoding="utf-8")
    for gone in ("--target-gpu", "--source-gpu", "--no-run", "cost-running "):
        assert gone not in text, f"{document} still mentions {gone!r}"


def test_the_version_in_the_changelog_is_the_installed_one() -> None:
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert f"## {__version__}" in changelog


def test_the_readme_and_the_french_one_cover_the_same_ground() -> None:
    english = (ROOT / "README.md").read_text(encoding="utf-8")
    french = (ROOT / "LISEZMOI.md").read_text(encoding="utf-8")
    # Not a translation check, a coverage check: both have to show the same
    # commands, or one audience is being told about a feature the other is not.
    for command in ("audit", "validate", "render", "diff", "measure", "consent", "catalog"):
        assert command in english and command in french


def test_the_arithmetic_the_examples_promise_is_the_arithmetic_they_get() -> None:
    # This is the snippet EXAMPLES.md prints the output of, run for real.
    from saggio import Quantity, carbon_from_energy, energy_from_runtime

    runtime = Quantity(value=3600.0, unit="s", status="measured")
    power = Quantity(value=400.0, unit="W", status="estimated")
    overhead = Quantity(value=1.2, unit="ratio", status="estimated")

    energy = energy_from_runtime(runtime, power, overhead)
    carbon = carbon_from_energy(energy, Quantity(value=56, unit="gCO2e/kWh", status="estimated"))

    assert (energy.value, energy.status) == (pytest.approx(0.48), "estimated")
    assert (carbon.value, carbon.status) == (pytest.approx(26.88), "estimated")


def test_the_exit_code_table_in_the_examples_matches_the_code() -> None:
    from saggio.cli.exit_codes import MEANINGS

    text = (ROOT / "EXAMPLES.md").read_text(encoding="utf-8")
    for code in MEANINGS:
        assert f"| `{code}` |" in text, f"exit code {code} is not documented"
