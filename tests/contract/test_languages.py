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

import re

import pytest

from saggio.analyze.llm import WORKLOAD_KINDS, _build_prompt
from saggio.api.app import AuditIn
from saggio.auditor.options import AuditOptions
from saggio.cli.app import build_parser
from saggio.i18n import DEFAULT_LANGUAGE, labels, languages, prompts
from saggio.model import CostModel
from saggio.report import render_html
from saggio.report.dashboard import render_dashboard

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
    parser = build_parser()
    action = next(action for action in parser._actions if action.dest == "verb")
    audit = action.choices["audit"]
    language = next(a for a in audit._actions if a.dest == "language")
    assert tuple(language.choices) == languages()
    assert language.default == DEFAULT_LANGUAGE


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
