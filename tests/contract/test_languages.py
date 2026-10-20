"""One language everywhere, or nowhere.

The defect these exist to prevent: the package offers a reader a language, and
then half of it answers in English anyway. It has two halves — the labels of
the report and the instruction sent to a local model — and nothing but a test
keeps them in step, because adding a language to one file is a complete,
plausible, self-consistent change.

And one defect already committed: the report's language control became a button
reading a comma-separated attribute, while the dashboard went on filling the
same shell with `<option>` markup. Two renderers, one template, one of them
updated.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Final

import pytest

from saggio.analyze.llm import WORKLOAD_KINDS, _build_prompt
from saggio.api.app import AuditIn
from saggio.auditor.options import AuditOptions
from saggio.cli.app import build_parser
from saggio.i18n import DEFAULT_LANGUAGE, labels, languages, messages, prompts
from saggio.model import CostModel
from saggio.report import render_html
from saggio.report.dashboard import render_dashboard

ROOT = Path(__file__).resolve().parents[2]

MODEL = CostModel.from_mapping(
    {
        "schema_version": "2.1",
        "project": {"name": "demo"},
        "unit_of_work": {"name": "one request"},
        "scenarios": [{"name": "as-audited", "costs": {}}],
    }
)


# --- The two tables agree ----------------------------------------------------


def test_both_translation_files_speak_the_same_languages() -> None:
    # The invariant the rest of this file rests on. A language in only one file
    # is not half a language: it is a reader handed a French page with an
    # English sentence generated inside it, or a French sentence in a model
    # whose report has no French to render.
    assert sorted(labels()) == sorted(prompts()), (
        "report/i18n.yaml and prompts.yaml must offer the same languages; "
        f"labels={sorted(labels())} prompts={sorted(prompts())}"
    )


def test_the_languages_the_package_offers_are_those_two_files() -> None:
    assert languages() == tuple(sorted(labels()))
    assert DEFAULT_LANGUAGE in languages()


@pytest.mark.parametrize("code", sorted(labels()))
def test_no_language_is_missing_a_label(code: str) -> None:
    # A missing key falls back to English in the page, which is how a
    # half-translated language looks like a working one.
    missing = sorted(set(labels()[DEFAULT_LANGUAGE]) - set(labels()[code]))
    assert not missing, f"{code} is missing {missing}"


@pytest.mark.parametrize("code", sorted(prompts()))
def test_no_language_is_missing_a_prompt(code: str) -> None:
    missing = sorted(set(prompts()[DEFAULT_LANGUAGE]) - set(prompts()[code]))
    assert not missing, f"{code} is missing {missing}"


def test_the_two_tables_share_no_key() -> None:
    # They are read for different purposes and only one of them is published in
    # the page; a key in both would mean two wordings of one string, free to
    # drift, and no way to tell which one a reader saw.
    for code in languages():
        assert not set(labels()[code]) & set(prompts()[code])


# --- What a prompt must keep saying -----------------------------------------


@pytest.mark.parametrize("code", sorted(prompts()))
def test_every_language_asks_for_prose_without_renaming_the_fields(code: str) -> None:
    # `_coerce` matches these names literally. An instruction that translated
    # them would get a well-formed answer under keys nothing reads, which is
    # indistinguishable from a model that ignored the request.
    asked = prompts()[code]["prompt.classify.language"]
    for field in ("dominant_operation", "reasoning", "workload_kind"):
        assert field in asked, f"{code} does not name {field}"


@pytest.mark.parametrize("code", sorted(prompts()))
def test_no_language_translates_the_closed_set(code: str) -> None:
    # The kinds are matched against WORKLOAD_KINDS on the way back in, so the
    # one thing the instruction must not do is invite a translated `training`.
    prompt = _build_prompt("a repository", language=code)
    offered = re.search(r'"workload_kind": one of \[([^\]]+)\]', prompt)
    assert offered is not None, "the prompt no longer offers the closed set"
    assert tuple(part.strip() for part in offered.group(1).split(",")) == WORKLOAD_KINDS


@pytest.mark.parametrize("code", sorted(prompts()))
def test_a_prompt_carries_its_own_language_and_only_its_own(code: str) -> None:
    prompt = _build_prompt("a repository", language=code)
    assert prompts()[code]["prompt.classify.language"] in prompt
    for other in set(prompts()) - {code}:
        assert prompts()[other]["prompt.classify.language"] not in prompt


# --- What the language button actually switches ------------------------------


def test_the_share_of_a_report_the_button_switches_is_the_share_the_docs_quote() -> None:
    """The claim `USING.md` makes, recomputed from the page it is about.

    The point of pinning it: the button switches the page's furniture, and
    saying "the report is bilingual" would be a claim nobody established. If
    somebody translates more of it the figure improves and this fails, which is
    the pleasant direction for a gate to fail in — and if the page grows more
    English, it fails in the direction that matters.
    """
    import yaml

    from saggio.i18n import labels

    model = CostModel.from_mapping(
        yaml.safe_load((ROOT / "examples" / "render.yaml").read_text(encoding="utf-8"))
    )
    page = render_html(model)
    body = re.sub(r"<script.*?</script>|<style.*?</style>", "", page, flags=re.S)
    swapped = 0
    for found in re.finditer(r'data-i18n="([^"]+)"[^>]*>(.*?)<', body, re.S):
        key, shown = found.group(1), re.sub(r"<[^>]+>", "", found.group(2))
        swapped += len(labels()["fr"].get(key, shown).strip())
    visible = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", body)).strip()
    visible = re.sub(r"[A-Za-z0-9+/]{200,}=*", "", visible)
    share = 100 * swapped / len(visible)

    # Read from the flattened text, because the claim is prose: it gets rewrapped
    # whenever a sentence around it is edited, and a test that fails for a line
    # break teaches a contributor to distrust it.
    written = re.sub(r"\s+", " ", (ROOT / "USING.md").read_text(encoding="utf-8"))
    quoted = re.search(
        r"It exchanges \*\*([\d.]+)%\*\* of the visible text on a rendered report",
        written,
    )
    assert quoted is not None, "USING.md no longer states what the button switches"
    # The share alone. It used to pin the two character counts as well, which
    # churned on every edit anywhere in the report and sent me chasing a figure
    # my own changes kept moving — three numbers to keep true where one says the
    # thing. The share is what the claim is about.
    assert round(share, 1) == float(quoted.group(1)), (
        f"USING.md says {quoted.group(1)}% of a report switches language, it is {share:.1f}%"
    )


# --- The consent wording, which is the most load-bearing prose here ----------


@pytest.mark.parametrize("code", sorted(prompts()))
def test_the_terms_keep_every_paragraph_in_every_language(code: str) -> None:
    # A translation that quietly drops the paragraph about there being no
    # sandbox would pass every other check in this file. Counting paragraphs is
    # not reading them, but it catches a truncation, which is the failure a
    # hurried translation actually has.
    english = prompts()[DEFAULT_LANGUAGE]["prompt.consent.terms"].strip().split("\n\n")
    translated = prompts()[code]["prompt.consent.terms"].strip().split("\n\n")
    assert len(translated) == len(english), (
        f"{code} states the terms in {len(translated)} paragraphs, English in {len(english)}"
    )


@pytest.mark.parametrize("code", sorted(prompts()))
def test_the_word_that_grants_consent_is_one_word(code: str) -> None:
    word = prompts()[code]["prompt.consent.word"]
    assert word == word.strip().lower(), f"{code}: {word!r} is not already lowercase and trimmed"
    assert " " not in word, f"{code}: {word!r} is more than one word"


@pytest.mark.parametrize("code", sorted(prompts()))
def test_the_question_names_the_word_rather_than_spelling_it_twice(code: str) -> None:
    # The word lives in one key. A translation that wrote it into the question
    # as well would have two copies of it, free to drift, and the one a reader
    # is told to type is the one that would be wrong.
    asked = prompts()[code]["prompt.consent.ask"]
    assert "{word}" in asked, f"{code} does not name {{word}}"
    assert asked.format(word=repr(prompts()[code]["prompt.consent.word"]))


@pytest.mark.parametrize("code", sorted(prompts()))
@pytest.mark.parametrize(
    "key",
    [
        "prompt.consent.granted",
        "prompt.consent.revoked",
        "prompt.consent.changed",
        "prompt.consent.unversioned",
    ],
)
def test_every_sentence_about_the_record_names_the_file(code: str, key: str) -> None:
    # A confirmation that does not say where the decision went leaves nobody
    # able to delete it, and deleting it is how consent is revoked.
    assert "{path}" in prompts()[code][key], f"{code}/{key} does not name {{path}}"
    assert prompts()[code][key].format(path="a-recorded-decision.json")


# --- The surfaces offer what the files hold ----------------------------------


def test_the_command_line_offers_exactly_the_languages_that_exist() -> None:
    import argparse

    parser = build_parser()
    overall = next(a for a in parser._actions if a.dest == "language")
    assert tuple(overall.choices) == languages()
    assert overall.default == DEFAULT_LANGUAGE, "the global spelling carries the default"

    action = next(a for a in parser._actions if a.dest == "verb")
    for name, verb in action.choices.items():
        language = next((a for a in verb._actions if a.dest == "language"), None)
        assert language is not None, f"{name} offers no --language"
        assert tuple(language.choices) == languages(), name
        # SUPPRESS, so that `saggio --language fr audit .` is not overwritten by
        # the verb's own default on its way through the sub-parser. A default
        # here is the argparse trap that makes a global option look ignored.
        assert language.default is argparse.SUPPRESS, name


def test_the_global_spelling_and_the_verb_spelling_agree() -> None:
    parser = build_parser()
    assert parser.parse_args(["validate", "m.yaml"]).language == DEFAULT_LANGUAGE
    assert parser.parse_args(["--language", "fr", "validate", "m.yaml"]).language == "fr"
    assert parser.parse_args(["validate", "m.yaml", "--language", "fr"]).language == "fr"
    # The verb wins when both are given, which is the way round a reader expects:
    # the nearer word to the thing it describes.
    both = parser.parse_args(["--language", "en", "validate", "m.yaml", "--language", "fr"])
    assert both.language == "fr"


def test_the_library_the_http_surface_and_the_agent_tool_share_one_default() -> None:
    assert AuditOptions().language == DEFAULT_LANGUAGE
    assert AuditIn(git_url="https://example.invalid/x.git").language == DEFAULT_LANGUAGE


def test_the_agent_tool_takes_a_language() -> None:
    # The tools are generated from the HTTP routes, so a field that exists in
    # the request model is an argument an agent can pass; this pins that the
    # route an agent reaches is the one carrying it.
    from saggio.api.app import create_app
    from saggio.api.mcp import attach_mcp

    tool = next(
        tool
        for tool in attach_mcp(create_app(allow_clone=True)).tools
        if tool.name == "audit_repository"
    )
    assert "language" in tool.inputSchema["properties"]


# --- Both pages switch language the same way ---------------------------------


@pytest.mark.parametrize(
    "page",
    [
        pytest.param(lambda: render_html(MODEL), id="report"),
        pytest.param(lambda: render_dashboard([MODEL]), id="dashboard"),
    ],
)
def test_every_page_lists_the_languages_the_same_way(page) -> None:
    rendered = page()
    found = re.findall(r'data-languages="([^"]*)"', rendered)
    assert found == [",".join(languages())], f"data-languages={found}"


@pytest.mark.parametrize(
    "page",
    [
        pytest.param(lambda: render_html(MODEL), id="report"),
        pytest.param(lambda: render_dashboard([MODEL]), id="dashboard"),
    ],
)
def test_every_label_on_a_page_has_something_to_switch_to(page) -> None:
    # What clicking the language button actually does: the script walks every
    # `data-i18n` node and replaces its text from the table. A key with no entry
    # is not an error anywhere — the node simply keeps the English it was
    # rendered with, so the page half-switches and looks like it worked. This is
    # the static half of pressing the button, and it is the half a test can hold.
    rendered = page()
    used = sorted(set(re.findall(r'data-i18n="([^"]+)"', rendered)))
    assert used, "the page writes no translatable labels at all"
    for code in languages():
        missing = [key for key in used if key not in labels()[code]]
        assert not missing, f"{code} has no wording for {missing}"


@pytest.mark.parametrize(
    "page",
    [
        pytest.param(lambda: render_html(MODEL), id="report"),
        pytest.param(lambda: render_dashboard([MODEL]), id="dashboard"),
    ],
)
def test_no_page_ships_the_model_instructions_to_a_browser(page) -> None:
    rendered = page()
    for code in languages():
        for key, value in prompts()[code].items():
            assert key not in rendered, f"the key {key} reached the page"
            # The longest run of the text with no double quote in it. A whole
            # sentence would not match even when the table was embedded: the
            # text quotes JSON field names, and a page embeds its data as JSON,
            # where those quotes come out backslashed. A sabotage probe put the
            # table in the blob and an earlier version of this test passed,
            # which is how that is known rather than supposed. Values too short
            # to be distinctive — the word that grants consent is three letters
            # — are left to the key check above.
            longest = max(value.split('"'), key=len)
            if len(longest) >= 25:
                assert longest not in rendered, f"{key} reached the page"


# --- The engine's own sentences -----------------------------------------------


def keys_the_code_asks_for() -> dict[str, list[str]]:
    """Return every key passed literally to `say`, with where it was asked for."""
    asked: dict[str, list[str]] = {}
    for path in sorted((ROOT / "saggio").rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "say"
                and node.args
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)
            ):
                where = f"{path.relative_to(ROOT).as_posix()}:{node.lineno}"
                asked.setdefault(node.args[0].value, []).append(where)
    return asked


def literals_in_the_package() -> set[str]:
    """Return every string literal in the package, for finding dead wording.

    By literal rather than by `say` call, because a key is often held in a
    mapping — the dimensions that are not emissions, the scope labels — and
    read from there. A key spelled nowhere is wording nobody can reach.
    """
    found: set[str] = set()
    for path in sorted((ROOT / "saggio").rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                found.add(node.value)
    return found


def test_every_sentence_the_code_asks_for_is_written() -> None:
    # The defect this prevents is quiet: `say` on a missing key returns the key
    # in brackets, which shows up in a report rather than crashing, and a report
    # nobody reads that day ships with `[ghg.capital_goods]` in it.
    english = messages()[DEFAULT_LANGUAGE]
    missing = {key: where for key, where in keys_the_code_asks_for().items() if key not in english}
    assert not missing, f"no wording for: {missing}"


@pytest.mark.parametrize("code", sorted(messages()))
def test_no_language_is_missing_a_sentence(code: str) -> None:
    missing = sorted(set(messages()[DEFAULT_LANGUAGE]) - set(messages()[code]))
    assert not missing, f"{code} is missing {len(missing)} sentences: {missing[:5]}"


@pytest.mark.parametrize("code", sorted(messages()))
def test_no_language_invents_a_sentence(code: str) -> None:
    # A key only one language has is wording the code never asks for in any
    # other, which means nobody will ever see it.
    extra = sorted(set(messages()[code]) - set(messages()[DEFAULT_LANGUAGE]))
    assert not extra, f"{code} has {len(extra)} sentences nothing asks for: {extra[:5]}"


def test_no_sentence_is_dead() -> None:
    # Reachable means spelled somewhere, or inside a family some module builds
    # keys for: `say(f"boundary.field.{key}")` leaves the literal
    # "boundary.field." in the source, which is how a family of twelve row
    # labels is reached without any of them being written out. A key that is
    # neither spelled nor inside such a family is wording nobody can see.
    spelled = literals_in_the_package()
    families = {text for text in spelled if text.endswith(".") and text.count(".") >= 2}
    orphans = sorted(
        key
        for key in messages()[DEFAULT_LANGUAGE]
        if key not in spelled and not any(key.startswith(family) for family in families)
    )
    assert not orphans, f"wording nothing reaches: {orphans}"


@pytest.mark.parametrize("code", sorted(messages()))
def test_every_language_names_the_same_arguments(code: str) -> None:
    # A translation that renamed `{pue}` gets a bracketed error in place of a
    # sentence; one that dropped it silently loses the figure the sentence is
    # about. Both are caught here rather than by a reader.
    english = messages()[DEFAULT_LANGUAGE]
    for key, wording in messages()[code].items():
        mine = set(re.findall(r"\{(\w+)\}", wording))
        theirs = set(re.findall(r"\{(\w+)\}", english.get(key, "")))
        assert mine == theirs, f"{code}/{key} names {sorted(mine)}, English names {sorted(theirs)}"


@pytest.mark.parametrize("code", sorted(messages()))
def test_every_sentence_formats_with_the_arguments_it_names(code: str) -> None:
    for key, wording in messages()[code].items():
        named = re.findall(r"\{(\w+)\}", wording)
        assert wording.format(**dict.fromkeys(named, "x")), key


def test_every_label_the_button_swaps_says_what_the_server_wrote() -> None:
    """A key on a node must mean the words that are in that node.

    The defect this found: the projections table carried
    ``i18n_keys=["column.dimension", "column.value", ...]`` while the server
    wrote ``["", "Value", ...]``. Pressing the language button wrote
    "Dimension" into a deliberately blank header and relabelled a whole-run
    figure "Per unit", which is the one thing a column header must not do. The
    page looked right until somebody pressed the button, which nothing tested.
    """
    import yaml

    model = CostModel.from_mapping(
        yaml.safe_load((ROOT / "examples" / "render.yaml").read_text(encoding="utf-8"))
    )
    table = labels()[DEFAULT_LANGUAGE]
    wrong = []
    for page in (render_html(model), render_dashboard([model])):
        for found in re.finditer(r'data-i18n="([^"]+)"[^>]*>(.*?)<', page, re.S):
            key = found.group(1)
            shown = re.sub(r"<[^>]+>", "", found.group(2)).strip()
            if table.get(key) != shown:
                wrong.append((key, table.get(key), shown))
    assert not wrong, f"keys that would change the words: {wrong}"


# --- How a figure is written ---------------------------------------------------


@pytest.mark.parametrize("code", sorted(labels()))
def test_every_language_says_how_it_writes_a_number(code: str) -> None:
    # Warith's call: 17.4 W in English, 17,4 W in French. A language with no
    # separator of its own would silently take the authored one, which is the
    # kind of default this package does not keep.
    separator = labels()[code].get("number.decimal")
    assert separator in {".", ","}, f"{code} writes a number with {separator!r}"


def test_the_separator_moves_between_digits_and_nowhere_else() -> None:
    """Dates, schema versions and dotted paths must come through untouched.

    The reason this is a function on a formatted figure rather than a pass over
    a rendered page: `2026-10-18` is not a number, `schema 2.1` is a version,
    and `example.invalid` is a host.
    """
    from saggio.i18n import language, number

    with language("fr"):
        assert number("17.4") == "17,4"
        assert number("2.5e-05") == "2,5e-05"
        assert number("not known") == "not known"
    assert number("17.4") == "17.4", "the authored language is left alone"


def test_the_browser_and_the_renderer_write_a_number_the_same_way() -> None:
    # The what-if panel recomputes in the browser, so it formats figures itself.
    # Two formatters mean two chances to disagree; this pins that the script
    # reads the same key the renderer reads.
    script = (ROOT / "reporting" / "report.js").read_text(encoding="utf-8")
    assert 'translated("number.decimal"' in script, "the script invents its own separator"
    assert "number.decimal" in labels()[DEFAULT_LANGUAGE]


# --- What a machine can check in a translation --------------------------------
#
# Not quality: no test reads a sentence and judges it, and a human reviewer is
# still owed one. These are the three defects a machine *can* find, measured
# before they became gates — over ~520 entries they found exactly one real
# fault, a dropped clause in `cli.help.scopes.scenario` where the French said
# "which scenario to place" and the English said "which scenario's *costs*".

#: Entries that are the same in both languages on purpose: a word French spells
#: the same way, a term of art kept in the standard's own wording, or a label
#: deliberately written in the language it offers. Anything else identical is a
#: translation somebody forgot, which is the likeliest translation defect there
#: is and the one hardest to see by reading.
SAME_IN_BOTH: frozenset[str] = frozenset(
    {
        "bar.language.en",
        "bar.language.fr",
        "section.projections",
        "whatif.machine",
        "column.dimension",
        "column.notes",
        "column.provenance",
        "column.source",
        "column.protocol",
        "column.service",
        "ghg.label.scope2_location",
        "ghg.label.scope2_market",
        # "Total" is the same word in French, and the rest is a number and a unit.
        "figure.domains.total",
    }
)


def every_table() -> dict[str, dict[str, dict[str, str]]]:
    """Return the three tables by name, so a check can say which one it found."""
    return {"label": labels(), "prompt": prompts(), "message": messages()}


@pytest.mark.parametrize("name", ["label", "prompt", "message"])
def test_no_translation_lost_a_clause(name: str) -> None:
    """A translation much shorter than its source has usually dropped something.

    French runs some fifteen to twenty per cent longer than English, so a French
    entry under four fifths of the English length is a sentence to look at. The
    threshold is loose on purpose: it is a hint for a reader, and it found a real
    one — a help line that said which scenario to place where the English said
    which scenario's *costs*.
    """
    table = every_table()[name]
    english = table[DEFAULT_LANGUAGE]
    for code, entries in table.items():
        if code == DEFAULT_LANGUAGE:
            continue
        for key, source in english.items():
            target = entries.get(key, "")
            if not target or len(source) < 60:
                continue
            assert len(target) >= len(source) * 0.8, (
                f"{code}/{key} is {100 * len(target) / len(source):.0f}% of the "
                f"English length — a clause may be missing:\n  en: {source}\n  {code}: {target}"
            )


@pytest.mark.parametrize("name", ["label", "prompt", "message"])
def test_nothing_is_identical_without_saying_why(name: str) -> None:
    table = every_table()[name]
    english = table[DEFAULT_LANGUAGE]
    for code, entries in table.items():
        if code == DEFAULT_LANGUAGE:
            continue
        for key, source in english.items():
            target = entries.get(key, "")
            if key in SAME_IN_BOTH or len(source.strip()) <= 3:
                continue
            assert source.strip() != target.strip(), (
                f"{code}/{key} is word for word the English. If that is right, add it "
                f"to SAME_IN_BOTH with the reason; if not, it was never translated: {source!r}"
            )


#: The three characters that count as a space before French punctuation: a plain
#: one, a no-break one, and the narrow no-break one typographers prefer. Written
#: by code point because a line holding all three is a line nobody can proofread.
SPACES: Final[str] = " " + "\u00a0" + "\u202f"


def test_the_french_spaces_its_punctuation_the_way_french_does() -> None:
    """A space before `:` `;` `!` `?`, every time or not at all.

    French typography puts one there and English does not. Either convention
    reads; mixing them inside one page is what a reader notices.
    """
    offenders: list[str] = []
    for name, table in every_table().items():
        for key, wording in table.get("fr", {}).items():
            # A URL's own colon is not punctuation, and neither is a time or a
            # ratio: the guard is what the first version of this check lacked,
            # and `https:` was its one and only finding.
            text = re.sub(r"\w+://\S+", "", wording)
            text = re.sub(r"\{\w+\}", "", text)
            for mark in (":", ";", "!", "?"):
                for match in re.finditer(rf"(.)\{mark}", text):
                    if match.group(1) not in SPACES:
                        offenders.append(
                            f"{name}/{key}: …{text[max(0, match.start() - 24) : match.start() + 2]}"
                        )
                        break
    assert not offenders, "French wants a space before these marks:\n  " + "\n  ".join(offenders)
