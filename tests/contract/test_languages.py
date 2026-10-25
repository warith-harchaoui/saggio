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
import difflib
import re
from pathlib import Path
from typing import Final

import pytest

from saggio.analyze.llm import WORKLOAD_KINDS, _build_prompt
from saggio.api.app import AuditIn
from saggio.auditor.options import AuditOptions
from saggio.cli.app import build_cli
from saggio.i18n import (
    DEFAULT_LANGUAGE,
    decimal_separator,
    group_separator,
    labels,
    language,
    languages,
    messages,
    percent_space,
    prompts,
)
from saggio.model import CostModel
from saggio.report import render_html, render_markdown
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


def _asking_sentence(code: str) -> str:
    """Return the sentence that asks for a language, as the prompt will carry it.

    The key holds `{language}` and the name is filled from the Common Locale
    Data Repository's autonym, so the sentence a prompt carries is not the key
    verbatim and a test comparing the two has to fill it the same way.
    """
    from saggio.i18n import language_name

    return prompts()[code]["prompt.classify.language"].format(language=language_name(code))


@pytest.mark.parametrize("code", sorted(prompts()))
def test_a_prompt_carries_its_own_language_and_only_its_own(code: str) -> None:
    prompt = _build_prompt("a repository", language=code)
    assert _asking_sentence(code) in prompt
    for other in set(prompts()) - {code}:
        assert _asking_sentence(other) not in prompt


@pytest.mark.parametrize("code", sorted(prompts()))
def test_the_prompt_names_the_language_in_the_language(code: str) -> None:
    """A model is asked in the word its training data saw most.

    *Écris … en français*, not *en French*: the autonym is what a French corpus
    contains, and it is a thing the database knows so a translator does not have
    to. The sentence that asks is read in the language being asked for, so the
    name inside it has to be that language's name for itself.
    """
    from saggio.i18n import language_name

    assert language_name(code) in _build_prompt("a repository", language=code)


def test_no_prompt_states_a_number() -> None:
    """Locale data for numbers has no place in a prompt, and this says why.

    Adopting the database raised the question of telling a model how to write a
    figure. The prompt forbids it to write one at all — every number in this
    package comes from a measurement — so a decimal separator rule there would
    contradict an instruction three paragraphs below it. This pins the premise
    rather than the conclusion: if a prompt ever states a figure, the question
    reopens and this is where it is asked.
    """
    for code, entries in prompts().items():
        for key, wording in entries.items():
            assert not re.search(r"\d", wording), f"{code}/{key} states a figure: {wording!r}"


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


# --- What the docs claim about translation, recomputed ------------------------
#
# Three figures the pages quote, each measured here so it cannot go stale by
# itself. They had: four rounds of translation moved all three and nobody
# noticed, because a dated number is not a false one and nothing was watching.


#: What a string literal has to look like to be prose an audit would show a
#: reader and no translation reaches. Each exclusion is a rule rather than a
#: judgement, so somebody who disagrees with the count can see which rule to
#: argue with.
_MARKUP: Final[re.Pattern[str]] = re.compile(r"</?[a-zA-Z][^>]*>|^[<>&]|[{}]\s*$|^\s*[-*#|]")
_KEYISH: Final[re.Pattern[str]] = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z0-9_]+)+\.?$")
_PATHISH: Final[re.Pattern[str]] = re.compile(
    r"^[./~]|^[a-z]+://|\.(py|ya?ml|json|md|csv|html|js|css)$"
)


def is_prose(text: str) -> bool:
    """Return whether a literal is a sentence rather than markup, a key or a path."""
    stripped = text.strip()
    if len(stripped.split()) < 4:
        return False
    if _KEYISH.match(stripped) or _PATHISH.search(stripped):
        return False
    if _MARKUP.search(stripped):
        return False
    # A sentence has a letter, a space and a letter, and a lower-case run of
    # three. `python3 -c import yaml` has the first and not the second.
    return bool(re.search(r"[A-Za-z]\s+[A-Za-z]", stripped)) and bool(
        re.search(r"[a-z]{3}", stripped)
    )


def prose_literals(tree_root: Path) -> dict[str, int]:
    """Return how many prose literals each module under a tree still holds."""
    per_module: dict[str, int] = {}
    for path in sorted((tree_root / "saggio").rglob("*.py")):
        parsed = ast.parse(path.read_text(encoding="utf-8"))
        docs = set()
        for node in ast.walk(parsed):
            if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                found = ast.get_docstring(node, clean=False)
                if found:
                    docs.add(found)
        count = sum(
            1
            for node in ast.walk(parsed)
            if isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and node.value not in docs
            and is_prose(node.value)
        )
        if count:
            per_module[path.relative_to(tree_root).as_posix()] = count
    return per_module


def flattened(text: str) -> str:
    """Return text with its whitespace collapsed, for comparing one run to another."""
    return re.sub(r"\s+", " ", text).strip()


def _example_model() -> CostModel:
    import yaml

    return CostModel.from_mapping(
        yaml.safe_load((ROOT / "examples" / "render.yaml").read_text(encoding="utf-8"))
    )


def _quoted(page: str, pattern: str) -> float:
    """Return the one number a page quotes for a claim, or fail saying it is gone."""
    written = re.sub(r"\s+", " ", (ROOT / page).read_text(encoding="utf-8"))
    found = re.search(pattern, written)
    assert found is not None, f"{page} no longer states this claim"
    return float(found.group(1))


def test_where_an_audit_prose_lives_is_what_the_docs_count() -> None:
    """How many prose literals are left, and in how many modules.

    The claim this serves: the button moves the page's structure and not its
    substance, because the substance is composed where the measurement happens.
    That is only worth saying with a number beside it.

    The definition above is not the one that produced the 709 first quoted
    here — run against the tree that quoted it, this counts 801 — so the two
    are not a trend. The trend is this definition on both trees, which is the
    only comparison a reader can check.
    """
    per_module = prose_literals(ROOT)
    total = sum(per_module.values())
    under_report = sum(v for key, v in per_module.items() if key.startswith("saggio/report/"))
    assert total == _quoted("USING.md", r"\*\*(\d+) prose literals of four words or more"), (
        f"USING.md counts a different number of prose literals; there are {total}"
    )
    assert len(per_module) == _quoted("USING.md", r"or more across (\d+) modules"), (
        f"USING.md counts a different number of modules; there are {len(per_module)}"
    )
    share = round(100 * under_report / total)
    assert share == _quoted("USING.md", r"modules\*\*[^.]*?only (\d+)% of"), (
        f"USING.md states a different share under report/; it is {share}%"
    )


def test_the_share_a_model_file_writes_is_the_share_the_docs_quote() -> None:
    """How much of a static report is the model's own sentences.

    Every string in the model, longest first so a note containing a shorter one
    is not counted twice, and matched once so a sentence the report repeats is
    credited once: the question is how much of the page the file wrote, not how
    often it appears. Measured on the Markdown report, which is what this
    project means by a static one.
    """
    model = _example_model()
    with language(DEFAULT_LANGUAGE):
        seen = flattened(render_markdown(model))
    total_visible = len(seen)
    strings: list[str] = []

    def walk(node: object) -> None:
        if isinstance(node, str):
            if len(node.split()) >= 3:
                strings.append(node)
        elif isinstance(node, dict):
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(model.data)
    written = 0
    for text in sorted(set(strings), key=len, reverse=True):
        flat = flattened(text)
        if flat and flat in seen:
            written += len(flat)
            seen = seen.replace(flat, " " * len(flat), 1)
    share = round(100 * written / total_visible)
    assert share == _quoted("README.md", r"\*\*(\d+)% of a static report's text\*\*"), (
        f"README.md states a different share from the model file; it is {share}%"
    )


def test_the_share_that_comes_out_french_is_the_share_the_docs_quote() -> None:
    """How much of a static report is French when the report is asked for in French.

    Word by word rather than character by character. A character diff matches
    stray substrings between unrelated sentences — it reports 18% where a word
    diff reports 30% — and what is being measured is how much of the text
    changed, not how many letters two texts happen to share.
    """
    model = _example_model()
    with language(DEFAULT_LANGUAGE):
        english = flattened(render_markdown(model)).split(" ")
    with language("fr"):
        french = flattened(render_markdown(model)).split(" ")
    matcher = difflib.SequenceMatcher(None, english, french, autojunk=False)
    shared = sum(
        sum(len(word) + 1 for word in french[block.b : block.b + block.size])
        for block in matcher.get_matching_blocks()
    )
    total = sum(len(word) + 1 for word in french)
    share = round(100 * (total - shared) / total, 1)
    assert share == _quoted("README.md", r"and \*\*([\d.]+)%\*\* of it comes out French"), (
        f"README.md states a different French share; it is {share}%"
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


def _language_parameter(command):
    """Return a command's ``--language`` parameter, or None. Public API only."""
    return next((p for p in command.params if p.name == "language"), None)


def test_the_command_line_offers_exactly_the_languages_that_exist() -> None:
    """Every verb offers the language, and offers the ones that exist.

    Read off `Command.params`, which click publishes. The argparse version of
    this walked `parser._actions` and `action.choices`, and ended by asserting
    that each verb's default was the `argparse.SUPPRESS` constant -- a test
    about how one library avoids overwriting a parent's value, not about
    anything a caller can see. What a caller can see is pinned by the test
    below instead.
    """
    import click

    group = build_cli()
    overall = _language_parameter(group)
    assert overall is not None, "the group offers no --language"
    assert tuple(overall.type.choices) == languages()
    assert overall.default == DEFAULT_LANGUAGE, "the global spelling carries the default"

    def walk(command, prefix=""):
        for name, verb in command.commands.items():
            if isinstance(verb, click.Group):
                walk(verb, prefix=f"{prefix}{name} ")
                continue
            where = f"{prefix}{name}"
            parameter = _language_parameter(verb)
            assert parameter is not None, f"{where} offers no --language"
            assert tuple(parameter.type.choices) == languages(), where
            # None, not a language: a default here would be indistinguishable
            # from the caller asking for English and would win over the group's
            # `--language`. The merge is in `_verb`, and the test below holds it.
            assert parameter.default is None, where

    walk(group)


def test_the_global_spelling_and_the_verb_spelling_agree(monkeypatch) -> None:
    """Either position reaches the verb, and the nearer word wins.

    Checked on what the verb is handed rather than on a parsed namespace: under
    click the two spellings are merged in `_verb`, which is the behaviour a
    caller sees, and a test reading a namespace attribute could have passed
    with the merge missing entirely.
    """
    from saggio.cli import app

    seen: list[str] = []

    def record(args):
        seen.append(args.language)
        return 0

    monkeypatch.setitem(app._HANDLERS, "validate", record)

    for argv, expected in (
        (["validate", "m.yaml"], DEFAULT_LANGUAGE),
        (["--language", "fr", "validate", "m.yaml"], "fr"),
        (["validate", "m.yaml", "--language", "fr"], "fr"),
        # The verb wins when both are given, which is the way round a reader
        # expects: the nearer word to the thing it describes.
        (["--language", "en", "validate", "m.yaml", "--language", "fr"], "fr"),
    ):
        seen.clear()
        assert app.main(argv) == 0, argv
        assert seen == [expected], argv


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


#: What a key prefix looks like, for recognising the literal a module leaves
#: behind when it builds a family of keys. Matched rather than counted: the rule
#: used to ask for two dots, which let `boundary.field.` through and kept
#: `country.` out — a one-segment family is still a family, and thirty-eight
#: country names were unreachable by a test that was right about everything
#: except how many dots a prefix has.
_KEY_PREFIX: Final[re.Pattern[str]] = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z0-9_]+)*\.$")


def test_no_sentence_is_dead() -> None:
    # Reachable means spelled somewhere, or inside a family some module builds
    # keys for: `say(f"boundary.field.{key}")` leaves the literal
    # "boundary.field." in the source, which is how a family of twelve row
    # labels is reached without any of them being written out. A key that is
    # neither spelled nor inside such a family is wording nobody can see.
    spelled = literals_in_the_package()
    families = {text for text in spelled if _KEY_PREFIX.match(text)}
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
    # Not in this repository any more: how a language writes a figure comes from
    # the Common Locale Data Repository, and the page carries what it says so the
    # browser can write a figure the way the renderer did. This checks the page's
    # copy against the database, which is the only way the two can disagree.
    from saggio.report.html import translations

    carried = translations()[code]
    for key, answer in (
        ("number.decimal", decimal_separator(code)),
        ("number.group", group_separator(code)),
        ("number.percent", percent_space(code)),
    ):
        assert key in carried, f"the page does not carry {key} for {code}"
        assert carried[key] == answer, f"the page and the database disagree about {key}"
    assert decimal_separator(code), f"{code} writes a number with no decimal separator"


@pytest.mark.parametrize("code", sorted(labels()))
def test_the_number_rules_are_not_kept_by_hand(code: str) -> None:
    """The three symbols are read, not written here, and the file says so.

    One of them was wrong for as long as it was hand-kept: the space before a
    per-cent sign in French is U+00A0, the no-break space, and this had U+202F,
    the narrow one. Invisible in a report, and nothing could have caught it.
    """
    assert "number.decimal" not in labels()[code], (
        "the decimal separator is back in the hand-kept table"
    )
    assert "number.group" not in labels()[code], "the grouping separator is back"
    assert "number.percent" not in labels()[code], "the per-cent spacing is back"


def test_the_per_cent_space_is_the_one_the_database_gives() -> None:
    # The hand-written value was the narrow no-break space and the database says
    # the no-break space. Pinned by code point, because the two are a width
    # apart and a test that read as `" " == " "` would teach nobody anything.
    assert percent_space("en") == ""
    assert percent_space("fr") == "\u00a0", "French spaces a per-cent sign with U+00A0"


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


#: Every key that says how a language writes a figure. The what-if panel
#: recomputes in the browser, so each of these is read twice — once by the
#: renderer and once by the script — and a rule one of them has and the other
#: does not is two halves of a page writing one number differently.
NUMBER_RULES: Final[tuple[str, ...]] = ("number.decimal", "number.group")


@pytest.mark.parametrize("key", NUMBER_RULES)
def test_the_browser_and_the_renderer_write_a_number_the_same_way(key: str) -> None:
    # Two formatters mean two chances to disagree; this pins that the script
    # reads the keys the page carries, and the test above pins that what the
    # page carries is what the database says. `number.percent` is not among
    # them because the panel states no percentages — when it does, it joins
    # this list.
    from saggio.report.html import translations

    script = (ROOT / "reporting" / "report.js").read_text(encoding="utf-8")
    assert f'translated("{key}"' in script, f"the script invents its own {key}"
    assert key in translations()[DEFAULT_LANGUAGE]


def test_a_figure_is_grouped_the_way_each_language_groups_it() -> None:
    """The whole part, in threes, and nothing else.

    What must not move is the list: tenths are not grouped however many there
    are, an exponent is not a quantity, and a run of three digits is not long
    enough to group. Each was a way to break a report by rewriting a number
    that was already right.
    """
    from saggio.i18n import group_separator, language, number

    assert number("1234567.89") == "1,234,567.89"
    assert number("999") == "999"
    with language("fr"):
        space = group_separator()
        assert number("10870.6 s") == f"10{space}870,6 s"
        assert number("1000") == f"1{space}000"
        # Already grouped, and not grouped twice.
        assert number(f"1{space}000") == f"1{space}000"
        # Tenths, an exponent, and a figure too short to group.
        assert number("0.12345") == "0,12345"
        assert number("1.906e+04") == "1,906e+04"
        assert number("999") == "999"


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
        # "source" is the same word in French.
        "report.link.source",
        # Four of the thirty-eight countries, and only four: Singapore is
        # Singapour and Israel is Israël, so a fifth identical entry here would
        # mean somebody pasted the English column rather than translating it.
        "country.CA",
        "country.FR",
        "country.PT",
        "country.UA",
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

    The per-cent sign obeys the same rule and is not checked here, because no
    catalogue entry writes one: a figure reaches a sentence already formatted,
    and :func:`saggio.i18n.number` is where the spacing is applied. The test
    below is the gate for that.
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


# --- What a country is called -------------------------------------------------


@pytest.mark.parametrize("code", sorted(messages()))
def test_every_country_on_file_has_a_name_in_every_language(code: str) -> None:
    """A grid row the database cannot name reads as its code to a reader.

    Thirty-eight rows, and the next one somebody adds is the one this is for.
    The Common Locale Data Repository covers every country there is, so a row
    this fails on is a row keyed by something that is not a country code.
    """
    from saggio.catalog.registry import Catalog
    from saggio.i18n import territory_name

    rows = Catalog.bundled("grid").rows("countries")
    missing = sorted(key for key in rows if not territory_name(key, within=code))
    assert not missing, f"the database cannot name these in {code}: {missing}"


def test_the_database_and_the_grid_row_agree_about_a_country_name() -> None:
    """The catalogue of numbers and the database of names, pinned together.

    The row's ``name`` could not be translated: thirty-two of the thirty-eight
    are matched to the tariff source by it. So the column keeps its job and the
    words come from the database — which leaves two spellings of one country,
    and two spellings with nothing watching them is the defect this file keeps
    finding.

    The exceptions are listed, not tolerated. Each is a row whose ``name`` is
    the tariff source's spelling and whose displayed name is the country's, and
    each is in `PRICE_NAME_OF_KEY` so the matching is stated rather than
    incidental.
    """
    from saggio.catalog.refresh.tariffs import PRICE_NAME_OF_KEY
    from saggio.catalog.registry import Catalog
    from saggio.i18n import territory_name

    rows = Catalog.bundled("grid").rows("countries")
    wrong = {}
    for key, row in rows.items():
        own, named = row.get("name"), territory_name(key, within=DEFAULT_LANGUAGE)
        if own and named != own and key not in PRICE_NAME_OF_KEY:
            wrong[key] = (named, own)
    assert not wrong, (
        "the database and the row disagree, as (database says, row says): "
        f"{wrong}. Either correct the row, or name it in PRICE_NAME_OF_KEY so "
        "the tariff refresh keeps matching on the source's spelling."
    )


def test_the_country_list_is_alphabetical_in_the_language_it_is_read_in() -> None:
    """A dropdown somebody has to find a country in, ordered as they would look.

    Code-point order put `Égypte` after `Ukraine` and `Suisse` before `Suède`:
    three countries past the end of the alphabet and two swapped, from one
    `sorted()` with no key. An accent is a mark on a letter, not a letter.
    """
    import yaml

    from saggio.i18n import language, sort_key

    model = CostModel.from_mapping(
        yaml.safe_load((ROOT / "examples" / "render.yaml").read_text(encoding="utf-8"))
    )
    for code in sorted(messages()):
        with language(code):
            page = render_html(model)
        options = re.search(r'<select id="whatif-country">(.*?)</select>', page, re.S)
        assert options is not None, "the what-if panel offers no countries"
        shown = re.findall(r'<option value="[A-Z]{2}"[^>]*>([^<]+)</option>', options.group(1))
        assert shown, f"{code} lists no countries"
        assert shown == sorted(shown, key=sort_key), (
            f"{code} lists them out of order, from {shown[0]!r} to {shown[-1]!r}"
        )


def test_the_per_cent_sign_is_spaced_the_way_each_language_spaces_it() -> None:
    """A formatted figure comes back spaced, and only where a figure precedes.

    `100%` is a figure and takes the rule. A literal per-cent sign with no
    digit before it is not a measurement and is left alone, the same discipline
    the decimal separator keeps.
    """
    from saggio.i18n import language, number, percent_space

    assert number("21.9%") == "21.9%", "English sets the sign tight against the figure"
    with language("fr"):
        spacing = percent_space()
        assert spacing == "\u00a0", "the database gives the no-break space, not the narrow one"
        assert number("21.9%") == f"21,9{spacing}%"
        assert number("49%") == f"49{spacing}%"
        # Already spaced, and not spaced twice.
        assert number(f"49{spacing}%") == f"49{spacing}%"
        # No figure before it, so nothing to space away from.
        assert number("%") == "%"
