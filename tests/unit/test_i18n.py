"""The language a caller asked for, and what happens when nothing is written in it.

Measured on 2026-10-19, which is why the prompt table holds one sentence per
language rather than a whole prompt per language. Two local models
(`qwen3-vl:8b`, `gemma3:12b`), two seeds each, on this repository's summary:

    english prompt + the sentence     french prose 4/4
    prompt translated, no sentence     french prose 0/4
    french prompt + the sentence       french prose 4/4

A translated prompt on its own changes nothing. Asking is what works, and it
works whichever language the asking is written in.
"""

from __future__ import annotations

import pytest

from saggio import i18n
from saggio.i18n import (
    DEFAULT_LANGUAGE,
    labels,
    languages,
    phrase,
    prompts,
    resolve,
    unknown_language_note,
)

# --- What a caller may write --------------------------------------------------


@pytest.mark.parametrize(
    ("asked", "expected"),
    [
        (None, "en"),
        ("", "en"),
        ("en", "en"),
        ("fr", "fr"),
        ("FR", "fr"),
        ("fr-FR", "fr"),
        ("fr_CA", "fr"),
        ("  fr  ", "fr"),
        ("en-GB", "en"),
        ("klingon", "en"),
        ("français", "en"),
    ],
)
def test_a_language_tag_resolves_to_a_table_or_to_english(asked, expected) -> None:
    # An agent passes what the person in front of it typed, which is a tag, a
    # region, a capital, or a word. Only the first subtag decides.
    assert resolve(asked) == expected


def test_the_fallback_is_announced_rather_than_silent() -> None:
    note = unknown_language_note("klingon")
    assert note is not None
    assert "klingon" in note and "en" in note
    assert "en, fr" in note, "the note says what there is, not only what there is not"


@pytest.mark.parametrize("known", [None, "", "en", "fr", "fr-CA", "FR"])
def test_a_language_that_exists_produces_no_note(known) -> None:
    assert unknown_language_note(known) is None


# --- What a phrase is ---------------------------------------------------------


def test_a_prompt_phrase_comes_back_in_the_language_asked() -> None:
    assert phrase("prompt.classify.language", language="fr").startswith("Écris")
    assert phrase("prompt.classify.language", language="en").startswith("Write")


def test_a_label_comes_from_the_other_table() -> None:
    assert phrase("bar.print", language="fr", table="label") == "Enregistrer en PDF"


def test_a_key_in_neither_table_is_empty_rather_than_its_own_name() -> None:
    # A key echoed back would be rendered: `bar.nothing` on a page, or a line of
    # dotted identifier inside a prompt. An empty string is one sentence less,
    # which is the smaller harm.
    assert phrase("nothing.has.this", language="fr") == ""
    assert phrase("nothing.has.this", table="label") == ""


def test_a_language_with_no_entry_for_a_key_falls_back_to_english() -> None:
    # Not to silence: a report with a hole in it reads as a rendering bug, and
    # the fallback is what the contract test exists to make unnecessary.
    assert phrase("prompt.classify.language", language="klingon").startswith("Write")


# --- What the package offers ---------------------------------------------------


def test_the_two_tables_are_read_from_the_wheel_not_from_a_checkout() -> None:
    # Both go through importlib.resources, so an installed copy and a checkout
    # answer identically; this is the assertion that would fail if one of them
    # were read by path.
    assert labels()["en"]["bar.print"]
    assert prompts()["en"]["prompt.classify.language"]


def test_a_language_only_half_the_package_speaks_is_not_offered(monkeypatch) -> None:
    # The contract test refuses this state; this one says what the runtime does
    # while somebody is in the middle of creating it. German labels with no
    # German prompt must not put `de` in front of a reader.
    monkeypatch.setattr(i18n, "labels", lambda: {**labels(), "de": {"bar.print": "Als PDF"}})
    i18n.languages.cache_clear()
    try:
        assert "de" not in i18n.languages()
        assert i18n.resolve("de") == DEFAULT_LANGUAGE
    finally:
        i18n.languages.cache_clear()
    assert "fr" in languages(), "the real table is back"
