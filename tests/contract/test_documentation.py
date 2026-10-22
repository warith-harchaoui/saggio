"""The documentation, checked against the code it documents.

Documentation rots by drifting away from the thing it describes, and the two ways
it drifts here are a command-line flag that was renamed and a claim about the
package that stopped being true. Both are checkable, so both are checked.
"""

from __future__ import annotations

import re
import shlex
from collections import Counter
from functools import cache
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
    "DECLENCHEURS.md",
    "ANNEX-XI.md",
    "ANNEXE-XI.md",
    "BOUNDARIES.md",
    "FRONTIERES.md",
    "GALLERY.md",
    "GALERIE.md",
    "USING.md",
    "UTILISER.md",
]

#: Both spellings of the console script.
_INVOCATION = re.compile(rf"^\s*(?:\$ )?(?:{re.escape(PROGRAM)}|saggio)\s+(.*)$")

#: A line ending in a backslash is continued on the next one.
_CONTINUED = re.compile(r"\\\s*$")


def commands_in(document: str) -> list[tuple[int, str]]:
    """Return every command-line invocation the document shows, with its line.

    Only inside a fenced code block. A command shown to a reader is in a fence:
    of the 213 lines that matched the invocation pattern across every page, 212
    were fenced and the one that was not was a French sentence whose wrapping
    happened to put the word *saggio* at the start of a line. Reading prose for
    commands means any re-wrap can invent one, and the invented one then fails
    to parse.
    """
    path = ROOT / document
    if not path.is_file():
        return []
    found: list[tuple[int, str]] = []
    pending: str | None = None
    pending_line = 0
    fenced = False
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if line.lstrip().startswith("```"):
            fenced = not fenced
            continue
        if not fenced:
            continue
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


#: How many of a thing the documents spell out in words, in both languages. Only
#: as far as the catalogue could plausibly reach; a count past this is a count
#: somebody should have written in digits.
_SPELLED_OUT = {
    # English. "six" is spelled the same in French and is not repeated below.
    "zero": 0,
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    # French.
    "aucune": 0,
    "une": 1,
    "deux": 2,
    "trois": 3,
    "quatre": 4,
    "cinq": 5,
    "sept": 7,
    "huit": 8,
    "neuf": 9,
    "dix": 10,
    "onze": 11,
    "douze": 12,
}

#: The sentence six pages make about the embodied catalogue, in either language.
#: Whitespace is collapsed before matching because every one of them wraps the
#: claim across a line break, in a different place.
_FOOTPRINT_CLAIM = re.compile(
    r"(\w+) (?:accelerators out of|accélérateurs sur) (\d+)\s*(?:rows|lignes)"
    r"[,.]?\s*(?:and\s+|et\s+)?(\w+) (?:processors out of|processeurs sur) (\d+)",
    re.IGNORECASE,
)


def test_the_embodied_counts_the_documents_quote_are_the_catalogue_s_own() -> None:
    """Six pages state how much of the catalogue carries a footprint. Nothing checked.

    "Three accelerators out of 25 rows and four processors out of 12" is a claim
    about a data file, written out in prose in two languages across six
    documents, and a row added to `hardware.yaml` falsifies all six at once
    without touching a test. It is the same shape as the defect that opened the
    previous iteration -- a preface saying "twenty-one entries" above
    twenty-three -- and the same shape as the citations that worked everywhere
    except where they were read: a statement the repository makes about itself
    on a surface nobody re-reads.

    `CHANGELOG.md` and its French half `JOURNAL.md` are deliberately not
    scanned. Their old entries say "seven footprints" and should go on saying
    it: they describe a release where that was true, and a history rewritten to
    agree with today is not a history.
    """
    import yaml

    catalogue = yaml.safe_load((ROOT / "saggio" / "data" / "hardware.yaml").read_text("utf-8"))
    truth = {
        section: (
            sum("embodied_kgco2e" in row for row in catalogue[section]),
            len(catalogue[section]),
        )
        for section in ("gpus", "cpus")
    }
    (with_gpu, gpus), (with_cpu, cpus) = truth["gpus"], truth["cpus"]

    pages = sorted(
        path
        for path in ROOT.glob("*.md")
        if path.name not in {"CHANGELOG.md", "JOURNAL.md"}
        and _FOOTPRINT_CLAIM.search(" ".join(path.read_text("utf-8").split()))
    )
    assert len(pages) >= 6, (
        "the pages that quote the embodied counts have moved or been renamed, so "
        f"this is checking {len(pages)} of them rather than six"
    )
    for page in pages:
        collapsed = " ".join(page.read_text(encoding="utf-8").split())
        for said_gpu, said_gpus, said_cpu, said_cpus in _FOOTPRINT_CLAIM.findall(collapsed):
            where = page.name
            assert _SPELLED_OUT.get(said_gpu.lower()) == with_gpu, (
                f"{where} says {said_gpu} accelerators carry a footprint; "
                f"the catalogue has {with_gpu}"
            )
            assert int(said_gpus) == gpus, (
                f"{where} says {said_gpus} accelerator rows; the catalogue has {gpus}"
            )
            assert _SPELLED_OUT.get(said_cpu.lower()) == with_cpu, (
                f"{where} says {said_cpu} processors carry a footprint; "
                f"the catalogue has {with_cpu}"
            )
            assert int(said_cpus) == cpus, (
                f"{where} says {said_cpus} processor rows; the catalogue has {cpus}"
            )
            # And the total the same sentence leads with, where it leads with one.
            total = _SPELLED_OUT.get(
                next(
                    (
                        word
                        for word in re.findall(
                            r"(\w+) (?:footprints|empreintes)", collapsed, re.IGNORECASE
                        )
                    ),
                    "",
                ).lower()
            )
            if total is not None:
                assert total == with_gpu + with_cpu, (
                    f"{where} leads with {total} footprints and then accounts for "
                    f"{with_gpu + with_cpu}"
                )


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
    ("INVENTORY.md", "INVENTAIRE.md"),
    ("ANNEX-XI.md", "ANNEXE-XI.md"),
    ("BOUNDARIES.md", "FRONTIERES.md"),
    ("CHANGELOG.md", "JOURNAL.md"),
    ("TRIGGERS.md", "DECLENCHEURS.md"),
    ("USING.md", "UTILISER.md"),
    ("GLOSSARY.md", "GLOSSAIRE.md"),
    ("docs/README.md", "docs/LISEZMOI.md"),
]

#: Where the repository's vocabulary is declared, English half first. Read by the
#: gate below rather than listed in it, so a contributor adds an initialism in
#: the place a reader looks it up.
GLOSSARIES: dict[str, str] = {"en": "GLOSSARY.md", "fr": "GLOSSAIRE.md"}

#: The two files where "expand it at its first use" is the wrong rule, and the
#: reason. They are append-only and read newest-first, so the first use of an
#: initialism sits in the oldest entry at the bottom — the one place a reader
#: starting at the top will never reach. They carry a link to the glossary in
#: their first lines instead, which the gate below checks.
HISTORIES: dict[str, str] = {
    "CHANGELOG.md": "append-only and read newest-first; links the glossary instead",
    "JOURNAL.md": "the French half of the same, and the same reason",
}


#: Phrases that contain an initialism without being a use of it, each with the
#: reason it is here. Declared rather than discovered, because a gate written
#: without this list signals the whole repository and teaches everyone to ignore
#: it -- and because the remedy it would otherwise demand is to edit somebody
#: else's proper noun, or, in the first entry below, to assert something untrue.
#:
#: Being on this list is not an exemption from the rule. It is a statement that
#: the rule does not apply, because no reader meets an undecoded initialism
#: here: they meet a name.
NOT_A_USE: dict[str, str] = {
    "Resource Aware ML": (
        "RaML's own name. Its ML is the functional-language family OCaml belongs "
        "to, not machine learning -- the row beside it says 'first-order "
        "functional programs'. Expanding it to the glossary's sense would make "
        "the page state something false."
    ),
    "Static Analysis of Energy Consumption for LLVM IR Programs": (
        "a cited paper's title. A title is a quotation, and this page does not "
        "get to rewrite somebody else's."
    ),
    "Mistral AI": (
        "the company's registered name, in a list of the providers EcoLogits "
        "instruments. A proper noun is not a use of the initialism inside it, "
        "and writing out somebody's company name for them would be wrong on "
        "the page before it was wrong about the acronym."
    ),
}


def _prose_of(page: str) -> str:
    """Return a page's prose: no code, no link targets, no web addresses.

    An initialism inside a command is not prose a reader decodes, and neither
    is one inside the path of a link they click, nor one inside a name or a
    cited title -- see :data:`NOT_A_USE`.
    """
    text = (ROOT / page).read_text(encoding="utf-8")
    text = re.sub(r"```.*?```", " ", text, flags=re.S)
    text = re.sub(r"`[^`]*`", " ", text)
    text = re.sub(r"\]\([^)]*\)", "] ", text)
    text = re.sub(r"https?://\S+", " ", text)
    for phrase in NOT_A_USE:
        text = text.replace(phrase, " ")
    return text


def test_every_declared_name_is_actually_on_a_page() -> None:
    """A list of exemptions nobody needs is a list that stops being read.

    Each entry here was put there to let one real page through. When the phrase
    leaves the documentation, the entry has to leave this list with it, or the
    next reader cannot tell which entries are load-bearing.
    """
    pages = sorted({page for pair in BILINGUAL_PAIRS for page in pair} | set(HISTORIES))
    everything = " ".join((ROOT / page).read_text(encoding="utf-8") for page in pages)
    idle = sorted(phrase for phrase in NOT_A_USE if phrase not in everything)
    assert not idle, f"NOT_A_USE declares phrases no page contains: {idle}"


def test_every_declared_name_says_why() -> None:
    # An exemption without a reason is indistinguishable from an oversight, and
    # the whole point of declaring these is that somebody can disagree with one.
    unexplained = sorted(phrase for phrase, why in NOT_A_USE.items() if len(why.split()) < 8)
    assert not unexplained, f"these are exempted without a reason anybody can weigh: {unexplained}"


@cache
def declared_initialisms(code: str) -> dict[str, str]:
    """Return the initialisms a glossary declares, with how it writes each out.

    Parsed from the page rather than listed here: the page is what a reader
    opens, and two copies of a vocabulary is the defect this repository keeps
    finding in its own prose.
    """
    declared: dict[str, str] = {}
    for line in (ROOT / GLOSSARIES[code]).read_text(encoding="utf-8").splitlines():
        found = re.match(r"\|\s*\*\*([A-Z][A-Z0-9]*)\*\*\s*\|\s*([^|]*?)\s*\|", line)
        if found and found.group(2) not in {"", "—"}:
            declared[found.group(1)] = found.group(2)
    return declared


@pytest.mark.parametrize("page", sorted({page for pair in BILINGUAL_PAIRS for page in pair}))
def test_every_initialism_is_written_out_before_it_is_used(page: str) -> None:
    """A reader meets a word they can decode, or they meet an explanation.

    The rule in one line: nowhere an initialism that is not spelled out and
    explained before it is used. Each page stands alone for it, because a
    reader landing on one has not read the others.

    What counts as spelled out: the written-out form appears no later than the
    end of the sentence that first uses the initialism. That accepts both
    shapes — *Common Locale Data Repository (CLDR)* and *CLDR (Common Locale
    Data Repository)* — and a glossary row, where the two sit side by side.

    The unit is the sentence rather than the source line on purpose. Markdown
    soft-wraps, so a line break inside a paragraph is invisible to the reader:
    judging the rule by where the file happens to wrap failed pages whose
    expansion a reader saw perfectly well, and turned every re-wrap of a
    paragraph into a chance to break a page that had not changed meaning.
    """
    if page in HISTORIES:
        pytest.skip(HISTORIES[page])
    code = "fr" if page in {french for _, french in BILINGUAL_PAIRS} else "en"
    declared = declared_initialisms(code)
    prose = _prose_of(page)
    unexplained = []
    for acronym, written in declared.items():
        first = re.search(rf"(?<![A-Za-z0-9]){re.escape(acronym)}(?![A-Za-z0-9])", prose)
        if first is None:
            continue
        sentence_end = re.search(r"(?<=[.!?:])\s|\n\n", prose[first.end() :])
        cut = first.end() + (sentence_end.end() if sentence_end else len(prose))
        if written.lower() not in re.sub(r"\s+", " ", prose[:cut]).lower():
            unexplained.append(acronym)
    assert not unexplained, (
        f"{page} uses these without writing them out first: {sorted(unexplained)}. "
        f"The written-out form is in {GLOSSARIES[code]}."
    )


@pytest.mark.parametrize("page", sorted({page for pair in BILINGUAL_PAIRS for page in pair}))
def test_no_link_target_is_broken_across_a_line(page: str) -> None:
    """A Markdown link destination cannot contain a newline.

    Re-wrapping a paragraph is how these appear: a long address, or a word with
    a hyphen in it, lands at the wrap point and the destination is cut in two.
    The link renders as literal text and goes nowhere. Twelve of them were
    written across seven pages in one session and the relative-link check saw
    one, because the other eleven were absolute addresses it does not resolve.

    This looks at the shape instead of the destination, so it covers both.
    """
    text = (ROOT / page).read_text(encoding="utf-8")
    broken = [
        match.group(0).replace("\n", "\\n")[:80]
        for match in re.finditer(r"\]\([^)\s]*\n[^)\s]*\)", text)
    ]
    assert not broken, (
        f"{page} has a link target split across a line break: {broken}. "
        "A destination has to sit on one line, even past eighty columns."
    )


#: Phrases that look like the debris of a spliced clause and are not. Each is
#: correct writing that one of the rules below cannot tell from a defect, and
#: each carries the reason, because an exemption nobody can weigh is
#: indistinguishable from an oversight.
READS_AS_WRITTEN: dict[str, str] = {
    "quoi que ce soit soit": (
        "'anything be analysed' in French. The subjunctive of etre follows the "
        "pronoun that ends 'quoi que ce soit', so the repetition is the "
        "sentence working rather than a verb left behind."
    ),
    "cette phrase ce paquet": (
        "an inversion -- 'which part of this sentence this package handles'. "
        "Two determiners either side of a noun is the shape of a spliced "
        "clause, and here it is the shape of a subordinate question."
    ),
}

#: What a sentence that stopped being a sentence looks like, mechanically.
NOT_A_SENTENCE: dict[str, str] = {
    r"\b(?!CODE|LINK)([A-Za-zÀ-ÿ]{3,})\s+\1\b": "a word written twice in a row",
    r"\b(?:ce|cet|cette|ces)\s+(?!que|qu'|qui|dont|quoi|où)\w+\s+(?:ce|cet|cette|ces)\s+\w":
        "two French determiners either side of one word",
    r"(?:,\s*[,.]|;\s*;|\(\s*\))": "punctuation left over from a rewrite",
}


def _readable(page: str) -> str:
    """A page's prose, with code and addresses reduced to one placeholder word.

    Removing them outright invents punctuation -- "`a`, `b`," collapses to
    ", ," -- so each becomes a word instead.
    """
    text = (ROOT / page).read_text(encoding="utf-8")
    text = re.sub(r"```.*?```", " CODE ", text, flags=re.S)
    text = re.sub(r"`[^`]*`", "CODE", text)
    text = re.sub(r"\]\([^)]*\)", "]", text)
    text = re.sub(r"https?://\S+", "LINK", text)
    for phrase in READS_AS_WRITTEN:
        text = text.replace(phrase, " ")
    return re.sub(r"\s+", " ", text)


@pytest.mark.parametrize("page", sorted({page for pair in BILINGUAL_PAIRS for page in pair}))
def test_every_sentence_still_reads_as_one(page: str) -> None:
    """A rewritten sentence has to still be a sentence.

    Every prose probe in this repository looks for an *absence* -- an
    initialism nobody expanded, a language with no twin, a key one table has
    and the other does not. None of them asks whether what was written reads.
    So a mechanical pass over prose could ship "qu'aucun de ces trois cet outil
    ne modélise", which is not a sentence, and stay green; it did, and the page
    carried it until somebody read the line.

    What this catches is the debris such a pass leaves: a word written twice, a
    French determiner on both sides of one word, punctuation from a clause that
    was spliced in. What it does **not** catch is a repetition that changes
    form -- "read by a contract test reads it" slipped past this check and was
    found by reading. Naming that limit is the point: this is a net under one
    class of mistake, not a proofreader.
    """
    text = _readable(page)
    found = [
        f"{why}: {match.group(0).strip()!r}"
        for pattern, why in NOT_A_SENTENCE.items()
        for match in re.finditer(pattern, text)
    ]
    assert not found, (
        f"{page} has prose that stopped being a sentence: {found}. "
        f"If one of these is correct writing, declare it in READS_AS_WRITTEN "
        f"with the reason."
    )


def test_every_exemption_from_reading_is_still_needed() -> None:
    """An exemption nobody needs is one that stops being read."""
    pages = sorted({page for pair in BILINGUAL_PAIRS for page in pair} | set(HISTORIES))
    everything = " ".join(
        re.sub(r"\s+", " ", (ROOT / page).read_text(encoding="utf-8")) for page in pages
    )
    idle = sorted(phrase for phrase in READS_AS_WRITTEN if phrase not in everything)
    assert not idle, f"READS_AS_WRITTEN declares phrases no page contains: {idle}"


@pytest.mark.parametrize("page", sorted(HISTORIES))
def test_a_history_points_at_the_glossary_instead(page: str) -> None:
    # Expanding at first use is the wrong rule for a file read newest-first:
    # the first use is at the bottom, in the entry nobody scrolls to. A link in
    # the opening lines is the rule that serves the reader here.
    opening = "\n".join((ROOT / page).read_text(encoding="utf-8").splitlines()[:12])
    code = "fr" if page == "JOURNAL.md" else "en"
    assert GLOSSARIES[code] in opening, (
        f"{page} is exempt from expanding at first use and has to link {GLOSSARIES[code]}"
    )


def test_the_glossary_declares_nothing_nobody_uses() -> None:
    # The other direction, and the one that rots: a vocabulary page grows
    # entries for words the repository stopped using, and a reader trusts it
    # less for every one of them.
    pages = sorted({page for pair in BILINGUAL_PAIRS for page in pair} | set(HISTORIES))
    for code, glossary in GLOSSARIES.items():
        used = set()
        for page in pages:
            if (page in {french for _, french in BILINGUAL_PAIRS}) != (code == "fr"):
                continue
            prose = _prose_of(page)
            used |= {
                acronym
                for acronym in declared_initialisms(code)
                if re.search(rf"(?<![A-Za-z0-9]){re.escape(acronym)}(?![A-Za-z0-9])", prose)
            }
        idle = sorted(set(declared_initialisms(code)) - used)
        assert not idle, f"{glossary} declares what no {code} page uses: {idle}"


#: Pages written once on purpose, each with the reason, so that adding a new page
#: is a decision about both languages rather than an oversight in one.
MONOLINGUAL_ON_PURPOSE: dict[str, str] = {
    "CODING.md": "the house rules for source code, which is written in English",
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


#: How each language groups thousands and marks tenths. English groups with a
#: comma and France with a space, so `1,312` and `1 312` are one figure written
#: twice and `19,337` and `19 337` are another. Without this the comparison
#: below reports three pairs in disagreement and all three are its own doing.
_THOUSANDS: dict[str, re.Pattern[str]] = {
    "en": re.compile(r"(?<=\d),(?=\d)"),
    "fr": re.compile(r"(?<=\d)[\s\u00a0\u202f](?=\d)"),
}


def _bold_figures(page: str, code: str) -> Counter[str]:
    """Return every measurement a bold run on a page claims, normalised.

    A number inside a code span is not one of them. The entry about the decimal
    separator reads **`17.4 W` in English, `17,4 W` in French** in both halves,
    which is one sentence showing two notations rather than two measurements —
    and the only thing the first version of this check reported, because it read
    the French notation in the English page as a thousands-grouped integer.

    Nor is a digit inside a word. The second version reported one figure, from
    **The structural a11y gate finds nothing** — a numeronym, which is a way of
    spelling *accessibility* and not a count of eleven.
    """
    text = (ROOT / page).read_text(encoding="utf-8")
    found: Counter[str] = Counter()
    for bold in re.findall(r"\*\*([^*]+)\*\*", text):
        shown = re.sub(r"`[^`]*`", " ", bold)
        plain = _THOUSANDS[code].sub("", shown)
        for raw in re.findall(r"(?<![A-Za-z\d])\d+(?:[.,]\d+)?\s*%?(?![A-Za-z\d])", plain):
            found[re.sub(r"\s+", "", raw).replace(",", ".")] += 1
    return found


@pytest.mark.parametrize(("english", "french"), BILINGUAL_PAIRS)
def test_the_two_languages_quote_the_same_figures(english: str, french: str) -> None:
    """A measurement stated in bold must be the same measurement in both halves.

    Not a translation check, a staleness check, and the sibling of the commands
    one above: a figure remeasured in English and not in French leaves one
    audience reading last month's number with this month's confidence. That is
    how three figures in these pages went four rounds of work out of date — the
    English was corrected, or was not, and nothing compared the halves.
    """
    in_english = _bold_figures(english, "en")
    in_french = _bold_figures(french, "fr")
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
PAGES_THAT_LIST_THEIR_SOURCES: tuple[str, ...] = (
    "STANDARDS.md",
    "NORMES.md",
    "INVENTORY.md",
    "INVENTAIRE.md",
)

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


def test_every_verb_is_shown_in_both_cookbooks() -> None:
    """A verb nobody documents is a verb nobody finds.

    `scopes` shipped, answered the question this package added it for, and
    appeared in neither cookbook for two releases. The pages promise every
    command a reader is expected to type, and nothing was comparing that promise
    against the parser that defines them.
    """
    parser = build_parser()
    verbs: set[str] = set()
    # argparse offers no public reader for its subparsers, and the alternative
    # is a second hand-maintained list of verbs, which is the thing this test
    # exists to stop existing.
    for action in parser._subparsers._group_actions:
        verbs |= set(getattr(action, "choices", {}) or {})
    assert verbs, "the parser stopped exposing its verbs, so this check is blind"

    for cookbook in ("EXAMPLES.md", "EXEMPLES.md"):
        shown = {command.split()[0] for _, command in commands_in(cookbook) if command.split()}
        missing = sorted(verbs - shown)
        assert not missing, f"{cookbook} never shows: {', '.join(missing)}"


def test_no_document_quotes_a_version_the_package_is_not() -> None:
    """A version printed in prose is a claim, and claims here are checked.

    `python -m saggio --version` is shown in the module's own docstring with the
    answer beside it. That answer was right when it was written and goes stale
    on the next release, silently, in the one place a reader checks to find out
    which version they have.
    """
    quoted = re.compile(rf"{re.escape(PROGRAM)}\s+([0-9]+\.[0-9]+\.[0-9]+)")
    history = {"CHANGELOG.md", "JOURNAL.md"}
    offenders: list[str] = []
    # The package itself, not a wheel build left in the tree: `build/lib/` holds
    # a copy of every module from whenever somebody last built, and failing on
    # a stale artefact teaches people to delete the test rather than the copy.
    for path in [
        *ROOT.glob("*.md"),
        *(ROOT / "docs").glob("*.md"),
        *(ROOT / "saggio").rglob("*.py"),
    ]:
        if path.name in history:
            continue
        for found in quoted.findall(path.read_text(encoding="utf-8")):
            if found != __version__:
                offenders.append(f"{path.relative_to(ROOT)} says {found}")
    assert not offenders, f"the installed version is {__version__}; " + "; ".join(offenders)


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
