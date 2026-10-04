"""The documentation, checked against the code it documents.

Documentation rots by drifting away from the thing it describes, and the two ways
it drifts here are a command-line flag that was renamed and a claim about the
package that stopped being true. Both are checkable, so both are checked.
"""

from __future__ import annotations

import re
import shlex
from collections import Counter
from pathlib import Path

import pytest

from saggio import __version__
from saggio.cli.app import PROGRAM, build_parser

ROOT = Path(__file__).resolve().parents[2]

#: The documents that show commands a reader is expected to type.
DOCUMENTS = [
    "README.md",
    "LISEZMOI.md",
    "EXAMPLES.md",
    "EXEMPLES.md",
    "MEASURING.md",
    "MESURER.md",
    "TRIGGERS.md",
    "GALLERY.md",
    "GALERIE.md",
]

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


#: Every invocation the documentation shows, as ``(document, line, command)``.
#: It held :func:`pytest.param` objects while each one was its own test case;
#: once the check was collapsed into a single test those wrappers were just a
#: shape to unpack around, and unpacking them wrongly is how the collapse first
#: went in.
ALL_COMMANDS: list[tuple[str, int, str]] = [
    (document, number, command)
    for document in DOCUMENTS
    for number, command in commands_in(document)
]


def test_the_documents_actually_show_commands() -> None:
    # A guard on the extraction itself: if the regex stopped matching, every
    # parametrised check below would pass by finding nothing to check.
    assert len(ALL_COMMANDS) > 25


def test_every_documented_command_parses() -> None:
    """Every invocation the documentation shows is one the parser accepts.

    One claim over 152 commands. It was parametrised, which meant 152 cases
    saying the same sentence about a different line, and a run that stopped at
    whichever one pytest reached first. Collapsed, a failure lists every
    command that does not parse, which is what somebody fixing the docs needs.
    """
    parser = build_parser()
    rejected: list[str] = []
    for document, number, command in ALL_COMMANDS:
        # The prose pipes output into other tools and writes URLs with an
        # ellipsis in the middle; neither is the parser's business.
        head = command.split("|", 1)[0]
        argv = [
            "https://example.invalid" if part.startswith("http") else part
            for part in shlex.split(head, comments=True)
            if part not in {"...", "\u2026"}
        ]
        try:
            parser.parse_args(argv)
        except SystemExit as exit_info:  # argparse exits on a flag it does not know.
            rejected.append(f"{document}:{number} shows `{head.strip()}` ({exit_info})")
    assert not rejected, "the parser rejects these documented commands:\n" + "\n".join(rejected)


@pytest.mark.parametrize("document", DOCUMENTS)
def test_no_document_shows_a_flag_that_was_renamed(document: str) -> None:
    path = ROOT / document
    if not path.is_file():
        pytest.skip(f"{document} is not in this repository")
    text = path.read_text(encoding="utf-8")
    for gone in ("--target-gpu", "--source-gpu", "--no-run", "cost-running "):
        assert gone not in text, f"{document} still mentions {gone!r}"


@pytest.mark.parametrize("catalogue", ["hardware", "grid", "providers", "instances", "services"])
def test_no_bundled_catalogue_names_a_command_that_does_not_exist(catalogue: str) -> None:
    # The catalogue headers tell a contributor how to add a row, and two of them
    # went on naming `cost-running <verb>` long after the verb and the name were
    # both gone. A wrong instruction in a data file is read as often as one in a
    # document and is checked by nothing else.
    text = (ROOT / "saggio" / "data" / f"{catalogue}.yaml").read_text(encoding="utf-8")
    for gone in ("cost-running", "running-code-cost", "rcch "):
        assert gone not in text, f"{catalogue}.yaml still mentions {gone!r}"


def test_the_version_in_the_changelog_is_the_installed_one() -> None:
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert f"## {__version__}" in changelog


#: Every page this repository writes twice, English first. The French half is not
#: a courtesy translation, it is the other half of the documentation, and the way
#: it rots is that an English section lands on Tuesday and its twin never does.
BILINGUAL_PAIRS: list[tuple[str, str]] = [
    ("README.md", "LISEZMOI.md"),
    ("EXAMPLES.md", "EXEMPLES.md"),
    ("MEASURING.md", "MESURER.md"),
    ("GALLERY.md", "GALERIE.md"),
    ("CONTRIBUTING.md", "CONTRIBUER.md"),
    ("LANDSCAPE.md", "PAYSAGE.md"),
    ("ANALYSIS.md", "ANALYSE.md"),
    ("STANDARDS.md", "NORMES.md"),
    ("docs/README.md", "docs/LISEZMOI.md"),
]

#: Pages written once on purpose, each with the reason, so that adding a new page
#: is a decision about both languages rather than an oversight in one.
MONOLINGUAL_ON_PURPOSE: dict[str, str] = {
    "CHANGELOG.md": "a log of releases, read by the person who wrote the release",
    "CODING.md": "the house rules for source code, which is written in English",
    "TRIGGERS.md": "addressed to agents, whose working language here is English",
    "docs/api.md": "generated from the docstrings, which are written in English",
}


def _command_shape(command: str) -> tuple[str, tuple[str, ...]]:
    """Reduce an invocation to the verbs and flags it uses.

    The two languages localise the words around a command, its file names, and
    the comment at the end of the line, and none of that is a difference in what
    the reader is being taught. What has to match is which verb is being shown
    and which flags it is being shown with.

    >>> _command_shape("audit . --country FR -o /tmp/now.yaml  # go")
    ('audit', ('--country',))
    >>> _command_shape("catalog add gpu H300 --source-url https://x --field tdp_w=800")
    ('catalog add gpu H300', ('--field', '--source-url'))
    """
    without_comment = re.sub(r"\s+#.*$", "", command)
    tokens = shlex.split(without_comment, posix=False)
    verbs: list[str] = []
    for token in tokens:
        if token.startswith("-") or any(character in token for character in "/.:="):
            break
        verbs.append(token)
    flags = tuple(sorted({token.split("=")[0] for token in tokens if token.startswith("--")}))
    return " ".join(verbs), flags


@pytest.mark.parametrize(("english", "french"), BILINGUAL_PAIRS)
def test_both_halves_of_a_bilingual_page_are_there(english: str, french: str) -> None:
    for document in (english, french):
        path = ROOT / document
        assert path.is_file(), f"{document} is promised by its twin and is not there"
        assert len(path.read_text(encoding="utf-8").split()) > 200, (
            f"{document} is a stub standing in for a page that was written once"
        )


@pytest.mark.parametrize(("english", "french"), BILINGUAL_PAIRS)
def test_each_half_of_a_bilingual_page_points_at_the_other(english: str, french: str) -> None:
    # A reader who lands on the wrong half has to be able to leave, and the link
    # is also what tells a contributor that the other half exists to be updated.
    english_text = (ROOT / english).read_text(encoding="utf-8")
    french_text = (ROOT / french).read_text(encoding="utf-8")
    assert Path(french).name in english_text, f"{english} never links to {french}"
    assert Path(english).name in french_text, f"{french} never links to {english}"


@pytest.mark.parametrize(("english", "french"), BILINGUAL_PAIRS)
def test_the_two_languages_show_the_same_commands(english: str, french: str) -> None:
    # Not a translation check, a coverage check: a command shown in one language
    # and not the other means one audience is being told about a feature the
    # other is not, which is the ordinary way a second language falls behind.
    in_english = Counter(_command_shape(command) for _, command in commands_in(english))
    in_french = Counter(_command_shape(command) for _, command in commands_in(french))
    assert in_english == in_french, (
        f"only in {english}: {sorted((in_english - in_french).elements())}; "
        f"only in {french}: {sorted((in_french - in_english).elements())}"
    )


@pytest.mark.parametrize("page", sorted(MONOLINGUAL_ON_PURPOSE))
def test_a_page_written_once_is_written_once_on_purpose(page: str) -> None:
    assert (ROOT / page).is_file(), f"{page} is listed as monolingual and is not there"
    assert MONOLINGUAL_ON_PURPOSE[page].strip(), f"{page} has no reason recorded"


def test_no_page_escapes_the_language_decision() -> None:
    # The failure this catches is a new English page landing with no French twin
    # and nobody noticing for a month. Every markdown page at the top level and
    # in docs/ is either half of a pair or listed above with its reason.
    accounted = {name for pair in BILINGUAL_PAIRS for name in pair} | set(MONOLINGUAL_ON_PURPOSE)
    found = {path.name for path in ROOT.glob("*.md")}
    found |= {f"docs/{path.name}" for path in (ROOT / "docs").glob("*.md")}
    assert found <= accounted, (
        f"{sorted(found - accounted)} is neither half of a bilingual pair nor "
        f"listed in MONOLINGUAL_ON_PURPOSE with a reason"
    )


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


def test_the_conda_environment_installs_the_package_and_not_just_its_dependencies() -> None:
    # An environment that installs only the dependencies leaves the reader with
    # no `saggio` command, which is not what the README promises them.
    environment = (ROOT / "environment.yaml").read_text(encoding="utf-8")
    assert re.search(r"^\s*-\s*(--editable\s+)?\.(\[[a-z,]+\])?\s*$", environment, re.MULTILINE), (
        "environment.yaml installs dependencies but never the package itself"
    )


def test_the_requirements_files_still_match_pyproject() -> None:
    # They exist for tools that expect that shape and are kept in step by hand,
    # which is exactly the arrangement that drifts without a test watching it.
    tomllib = pytest.importorskip("tomllib", reason="tomllib arrived in Python 3.11")
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    def named(lines: list[str]) -> set[str]:
        return {
            line.strip()
            for line in lines
            if line.strip() and not line.lstrip().startswith(("#", "-r "))
        }

    runtime = named((ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines())
    assert runtime == set(pyproject["project"]["dependencies"])

    development = named((ROOT / "requirements-dev.txt").read_text(encoding="utf-8").splitlines())
    assert development == set(pyproject["project"]["optional-dependencies"]["dev"])


def test_the_api_page_matches_the_docstrings_it_was_generated_from() -> None:
    # docs/api.md is derived, so an edited docstring must regenerate it or the
    # reference starts describing a package that no longer exists.
    import importlib.util

    spec = importlib.util.spec_from_file_location("docs_sync_api", ROOT / "docs" / "sync_api.py")
    assert spec is not None and spec.loader is not None
    sync_api = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(sync_api)

    assert not sync_api.out_of_date(), (
        "docs/api.md no longer matches the docstrings. Run `python docs/sync_api.py`."
    )


DOCUMENTATION_PAGES = sorted(path.name for path in (ROOT / "docs").glob("*.md"))


@pytest.mark.parametrize("page", DOCUMENTATION_PAGES)
def test_every_link_in_the_documentation_map_resolves(page: str) -> None:
    # The map exists to route a reader somewhere. A link that goes nowhere is
    # worse than no map, because the reader trusted it.
    path = ROOT / "docs" / page
    for target in re.findall(r"\]\((?!https?:)([^)#]+)\)", path.read_text(encoding="utf-8")):
        assert (path.parent / target).resolve().exists(), (
            f"{page} links to {target}, which is not there"
        )


#: Every markdown page this repository ships, wherever it lives. The link checks
#: below run over all of them rather than over ``docs/`` alone: a dead link in
#: the README is exactly as broken as a dead link in the map, and the reader who
#: followed it trusted it just as much.
MARKDOWN_PAGES = sorted(
    str(path.relative_to(ROOT)) for path in [*ROOT.glob("*.md"), *(ROOT / "docs").glob("*.md")]
)

#: A markdown link that points somewhere in this repository rather than out on
#: the web. ``mailto:`` and the two URL schemes are somebody else's to keep alive.
_RELATIVE_LINK = re.compile(r"\]\((?!https?:|mailto:)([^)]+)\)")

#: A setext- or atx-style heading, which is what an anchor is derived from.
_HEADING = re.compile(r"^#{1,6}\s+(.*)$", re.MULTILINE)


def _anchor_of(heading: str) -> str:
    """Return the fragment a heading can be linked by.

    Follows the rule the forges use: drop the inline markup, lowercase, drop
    punctuation but keep letters in every alphabet, and hyphenate the spaces.
    Accented letters survive, which is why the French half's anchors work.

    >>> _anchor_of("## The four states")
    'the-four-states'
    >>> _anchor_of("Du compteur au coût")
    'du-compteur-au-coût'
    >>> _anchor_of("`saggio power`, and what it says")
    'saggio-power-and-what-it-says'
    """
    text = re.sub(r"^#+\s*", "", heading.strip())
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"[`*_]", "", text).strip().lower()
    text = re.sub(r"[^\w\s-]", "", text, flags=re.UNICODE)
    return re.sub(r"\s+", "-", text)


def _anchors_in(path: Path) -> set[str]:
    """Return every fragment a page offers to be linked by."""
    return {_anchor_of(heading) for heading in _HEADING.findall(path.read_text(encoding="utf-8"))}


@pytest.mark.parametrize("page", MARKDOWN_PAGES)
def test_every_relative_link_in_every_page_resolves(page: str) -> None:
    # A link that goes nowhere is worse than no link, because the reader trusted
    # it. This covers the pages a reader actually lands on first, not only the
    # map that sends them there.
    path = ROOT / page
    for target in _RELATIVE_LINK.findall(path.read_text(encoding="utf-8")):
        destination = target.partition("#")[0]
        if not destination:
            continue
        assert (path.parent / destination).resolve().exists(), (
            f"{page} links to {destination}, which is not there"
        )


@pytest.mark.parametrize("page", MARKDOWN_PAGES)
def test_every_link_to_a_section_lands_on_a_heading(page: str) -> None:
    # The way a table of contents rots is that a heading gets reworded and the
    # entry above it keeps the old wording. The link still looks like a link.
    path = ROOT / page
    for target in _RELATIVE_LINK.findall(path.read_text(encoding="utf-8")):
        destination, _, anchor = target.partition("#")
        if not anchor:
            continue
        landing = (path.parent / destination).resolve() if destination else path
        if landing.suffix != ".md" or not landing.exists():
            continue
        assert anchor.lower() in _anchors_in(landing), (
            f"{page} links to #{anchor} in {landing.name}, which has no such heading"
        )


#: Pages whose `Sources` section is a promise: everything the body cites is
#: listed there, so a reader has one place to find what the page rests on.
PAGES_THAT_LIST_THEIR_SOURCES: tuple[str, ...] = ("STANDARDS.md", "NORMES.md")

#: Two addresses for one thing. The SCI specification answers at both, and
#: neither redirects to the other, so citing one in the body and the other in
#: the list is not an omission. Stated rather than inferred, because a rule that
#: guessed which URLs are "the same" would hide real omissions behind a
#: heuristic.
SAME_SOURCE: tuple[frozenset[str], ...] = (
    frozenset(
        {
            "https://sci.greensoftware.foundation/",
            "https://greensoftware.foundation/standards/sci/",
        }
    ),
)


@pytest.mark.parametrize("page", PAGES_THAT_LIST_THEIR_SOURCES)
def test_everything_a_page_cites_is_in_the_sources_it_lists(page: str) -> None:
    """A Sources section that is merely most of the sources is worse than none.

    A reader who checks the list and finds nothing about, say, the processor
    footprints concludes they rest on nothing. This caught three real omissions
    the day it was written: the parametric-model paper, its dataset, and the
    method the four processor rows cite -- all added to the body of the page
    over two days without anybody going back to the list.
    """
    import re

    text = (ROOT / page).read_text(encoding="utf-8")
    heading = "## Sources"
    assert heading in text, f"{page} has no Sources section"
    body, listed = text.split(heading, 1)

    def addresses(block: str) -> set[str]:
        return {u.rstrip(".,;)") for u in re.findall(r"https?://[^)\s\"]+", block)}

    def canonical(url: str) -> str:
        for group in SAME_SOURCE:
            if url in group:
                return min(group)
        return url

    cited = {canonical(u) for u in addresses(body)}
    in_list = {canonical(u) for u in addresses(listed)}
    missing = sorted(cited - in_list)
    assert not missing, (
        f"{page} cites these in its body and does not list them under Sources: {missing}"
    )


def test_the_version_the_package_reports_is_the_version_it_ships_as() -> None:
    """`__version__` and the packaging metadata have to be the same number.

    They are written in two files and nothing connected them. If they drift, a
    user runs `saggio --version`, reads one number, reports a bug against it,
    and the maintainer looks at a different release — which is a particularly
    tiring way to waste two people's afternoon.

    Found while cutting 1.4.0: the skill's frontmatter and the changelog
    heading were both checked against `__version__`, and `pyproject.toml`, the
    one that decides what `pip install` actually delivers, was not.
    """
    import re

    # `tomllib` arrived in 3.11 and this package supports 3.10, which is the
    # version continuous integration runs precisely because it is the one most
    # likely to refuse something. It refused this, on the commit that added it.
    #
    # A narrow read instead: the first `version = "..."` inside the `[project]`
    # table, and nowhere else, so a version pinned for a dependency further down
    # the file cannot be mistaken for the package's own.
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    project = re.search(r"^\[project\]$(.*?)^\[", text, re.M | re.S)
    assert project, "pyproject.toml has no [project] table"
    found = re.search(r'^version\s*=\s*"([^"]+)"', project.group(1), re.M)
    assert found, "[project] declares no version"
    shipped = found.group(1)
    assert shipped == __version__, (
        f"pyproject.toml ships {shipped!r} and the package reports {__version__!r}"
    )


def test_the_readme_links_still_work_once_it_leaves_the_repository() -> None:
    """README.md is republished elsewhere, so nothing in it can be relative.

    It is the long description: whatever a package index is given, it renders
    on its own domain. A relative reference resolves against that domain rather
    than against the repository, so `](EXAMPLES.md)` becomes a link to a page
    that was never there.

    Nothing catches this locally, because every such reference works in a
    checkout and works on the forge. It only breaks on the one surface the
    maintainer does not look at.

    The first version of this looked only at Markdown link syntax, and so
    walked straight past the header logo, which is an HTML `<img>` tag. The
    lesson is that the defect is "a reference that is not absolute", not "a
    Markdown link that is not absolute" -- so every form a reference can take
    is checked here, including the two attribute spellings.

    Images have a second trap this cannot check: on the forge, `blob/` serves
    an HTML page and only the raw host serves the bytes, so an image pointed at
    `blob/` is absolute and still broken.

    The other documents keep their relative references on purpose: they are
    read where they live, and a relative link is the one that survives a fork.
    """
    text = (ROOT / "README.md").read_text(encoding="utf-8")

    def is_absolute(target: str) -> bool:
        return target.startswith(("http://", "https://", "#", "mailto:"))

    offenders: list[str] = []
    for _, target in re.findall(r"\[([^\]]*)\]\(([^)\s]+)\)", text):
        if not is_absolute(target):
            offenders.append(f"markdown link -> {target}")
    for attribute, target in re.findall(r'\b(src|href)\s*=\s*"([^"]+)"', text):
        if not is_absolute(target):
            offenders.append(f"html {attribute} -> {target}")
    for label, target in re.findall(r"^\[([^\]]+)\]:\s*(\S+)", text, re.M):
        if not is_absolute(target):
            offenders.append(f"reference link [{label}] -> {target}")

    assert not offenders, (
        "README.md is shipped as the package's long description, where these "
        f"resolve against the index's own domain: {sorted(set(offenders))}"
    )
