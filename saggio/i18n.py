"""The languages this package speaks, and the one place a phrase comes from.

Module summary
--------------
Two kinds of text here are written for a reader rather than for a machine: the
labels of the HTML report, and the instruction sent to a local model. Both have
to exist in every language the package offers, because a page whose furniture
is French and whose generated sentence is English is one deliverable in two
languages, which is worse than either.

**What this does not cover, measured rather than guessed.** Pressing the
report's language button exchanges **6.9%** of the visible text on a rendered
report. The other 93% is the notes, the methods, the caveats and the refusals,
and none of it is written here: an audit's prose is composed where the
measurement happens, and that is **209 prose literals of four words or more
across 35 modules**, only 4% of them under ``report/``. So this file translates
the page's structure, not its substance, and saying otherwise would be the kind
of claim this package refuses about numbers.

Every figure in that paragraph is recomputed by a contract test from the report
it describes. They are quoted in ``USING.md`` and ``README.md`` rather than
here, so there is one place a reader checks and one place a gate reads.

So there is one loader and two tables, and :func:`languages` answers for the
package as a whole: a language appears there only when **both** tables have it.
A contract test refuses a table that speaks a language the other does not, so a
half-added language is a failing test rather than a page with English holes.

They are two files rather than two sections of one file, and the easy argument
for that is wrong: the prompt table is **375 bytes, 0.30% of a rendered page**,
so what keeps them apart is not size. It is that the two texts are edited by
different people against different rules. A label is free text; a translator
may word ``bar.print`` however reads best in their language. The prompt
sentence is load-bearing — it has to go on naming the JSON fields literally and
must not translate the closed set of workload kinds, or the model's answer is
discarded on the way back in — and sitting it among the interface strings
invites exactly the edit that breaks it. The report's table is also *published*:
it is embedded in every page the renderer writes, so that a report opens with no
network, and an instruction to a model has no business inside a document someone
reads.

What is *not* translated, deliberately: the closed set of workload kinds the
model chooses from. Those values are matched against
:data:`saggio.analyze.llm.WORKLOAD_KINDS` on the way back in, so a translated
``training`` would be thrown away as an unrecognised answer, and the model
would have been asked a question whose right answer this package rejects.

Usage example
-------------
>>> languages()
('en', 'fr')
>>> resolve("FR-fr")
'fr'
>>> phrase("prompt.classify.language", language="fr").startswith("Écris")
True

Author
------
Warith Harchaoui
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from functools import cache
from importlib import resources
from typing import Final

import yaml

#: The language everything falls back to, and the one the package is authored in.
DEFAULT_LANGUAGE: Final[str] = "en"

#: Where the two tables live. The report's one is packaged beside the stylesheet
#: and the script it goes with, because ``reporting/sync.py`` keeps that whole
#: folder in step with the authored copies; the prompt's one is a catalogue like
#: any other and is never sent to a browser.
_LABEL_PACKAGE: Final[str] = "saggio.data.report"
_LABEL_FILE: Final[str] = "i18n.yaml"
_PROMPT_PACKAGE: Final[str] = "saggio.data"
_PROMPT_FILE: Final[str] = "prompts.yaml"

#: Where the engine's own sentences live: one file per language, because there
#: are hundreds of them and a translator should be able to read their diff.
#: Reached through the data package rather than as a package of its own, so it
#: needs no ``__init__.py`` and ships as package data like every catalogue.
_MESSAGE_FOLDER: Final[str] = "messages"

#: The language the current piece of work is being done in. A context variable
#: rather than a parameter on every function that composes a sentence: the prose
#: of an audit is written where the measurement happens, across dozens of
#: modules, and threading a tag through all of them would be a larger change
#: with more places to forget it. Set once at the edge — a command, a request, a
#: library call — and read where a sentence is built.
_CURRENT: ContextVar[str] = ContextVar("saggio_language", default=DEFAULT_LANGUAGE)

#: What to say when a caller asks for a language nothing here is written in.
#: Named here so the CLI, the API and the audit notes word it identically.
UNKNOWN_LANGUAGE: Final[str] = (
    "Nothing in this package is written in {asked!r}, so {used!r} was used "
    "instead. Languages available: {offered}. Adding one means adding a "
    "top-level code to both translation files, and nothing else."
)


def _load(package: str, name: str) -> dict[str, dict[str, str]]:
    """Return a translation file as language code to key-value mapping.

    Parameters
    ----------
    package : str
        The package the file ships inside.
    name : str
        The filename.

    Returns
    -------
    dict
        Every top-level mapping, coerced to strings. A top-level entry that is
        not a mapping is dropped rather than raised on: a file is read at
        render time and a broken one should cost a missing phrase, not a
        traceback in the middle of somebody's audit.

    Examples
    --------
    >>> sorted(_load(_LABEL_PACKAGE, _LABEL_FILE))
    ['en', 'fr']
    """
    loaded = yaml.safe_load(resources.files(package).joinpath(name).read_text("utf-8")) or {}
    return {
        str(code): {str(key): str(value) for key, value in table.items()}
        for code, table in loaded.items()
        if isinstance(table, dict)
    }


@cache
def labels() -> dict[str, dict[str, str]]:
    """Return the report's translation table.

    Returns
    -------
    dict
        Language code to key-value mapping, for the keys the renderer writes as
        ``data-i18n`` attributes.

    Examples
    --------
    >>> labels()["fr"]["bar.print"]
    'Enregistrer en PDF'
    """
    return _load(_LABEL_PACKAGE, _LABEL_FILE)


@cache
def prompts() -> dict[str, dict[str, str]]:
    """Return the table of instructions sent to a local model.

    Returns
    -------
    dict
        Language code to key-value mapping. Never embedded in a page.

    Examples
    --------
    >>> sorted(prompts())
    ['en', 'fr']
    """
    return _load(_PROMPT_PACKAGE, _PROMPT_FILE)


@cache
def languages() -> tuple[str, ...]:
    """Return the languages this package can answer in, in a stable order.

    Returns
    -------
    tuple of str
        Codes present in **all three** tables — the page's labels, what the
        package asks, and what it says. A language only some of them have is
        left out here and reported by a contract test: offering a reader a
        language the package can only half write is the defect this guards
        against, and silently serving them English for the other half is how it
        would show.

    Examples
    --------
    >>> languages()
    ('en', 'fr')
    """
    return tuple(sorted(set(labels()) & set(prompts()) & set(messages())))


@cache
def messages() -> dict[str, dict[str, str]]:
    """Return the engine's own sentences, by language.

    The prose an audit composes while it measures: the notes, the methods, the
    caveats and the refusals. One file per language under
    ``saggio/data/messages/``, because there are hundreds of them and a
    translator should be able to read the diff of their own language.

    Returns
    -------
    dict
        Language code to key-value mapping.

    Examples
    --------
    >>> "en" in messages()
    True
    """
    folder = resources.files(_PROMPT_PACKAGE).joinpath(_MESSAGE_FOLDER)
    found: dict[str, dict[str, str]] = {}
    for entry in folder.iterdir():
        name = entry.name
        if not name.endswith(".yaml"):
            continue
        loaded = yaml.safe_load(entry.read_text("utf-8")) or {}
        if isinstance(loaded, dict):
            found[name[: -len(".yaml")]] = {str(key): str(value) for key, value in loaded.items()}
    return found


def current_language() -> str:
    """Return the language the work in hand is being done in.

    Returns
    -------
    str
        A code :func:`languages` contains.

    Examples
    --------
    >>> current_language()
    'en'
    """
    return _CURRENT.get()


@contextmanager
def language(code: str | None) -> Iterator[str]:
    """Do a piece of work in a language, and put the previous one back after.

    Parameters
    ----------
    code : str or None
        A language tag. ``None`` and anything unwritten mean English.

    Yields
    ------
    str
        The code actually in force, after :func:`resolve`.

    Examples
    --------
    >>> with language("fr") as code:
    ...     code, current_language()
    ('fr', 'fr')
    >>> current_language()
    'en'
    """
    chosen = resolve(code)
    token = _CURRENT.set(chosen)
    try:
        yield chosen
    finally:
        _CURRENT.reset(token)


def decimal_separator(code: str | None = None) -> str:
    """Return the character this language writes between units and tenths.

    Parameters
    ----------
    code : str or None, optional
        A language tag; the one in force when omitted.

    Returns
    -------
    str
        ``"."`` or ``","``. It is kept with the page's labels rather than with
        the engine's sentences because both halves need it: the renderer writes
        a figure server-side, and the what-if panel recomputes in the browser
        from the table the page carries.

    Examples
    --------
    >>> decimal_separator("en"), decimal_separator("fr")
    ('.', ',')
    """
    return phrase("number.decimal", language=code or current_language(), table="label") or "."


def percent_space(code: str | None = None) -> str:
    """Return what this language puts between a figure and its per-cent sign.

    English puts nothing. French puts a space, and the one typographers use is
    the narrow no-break one, which also stops a line breaking between the
    figure and the sign. Nine call sites wrote ``f"{share:.0%}"`` and a French
    report said `21,9%`, which is the decimal separator applied and the spacing
    rule not — a rule nothing had written down.

    Parameters
    ----------
    code : str or None, optional
        A language tag; the one in force when omitted.

    Returns
    -------
    str
        The spacing, possibly empty.

    Examples
    --------
    >>> percent_space("en") == ""
    True
    >>> percent_space("fr") == "\u202f"
    True
    """
    return phrase("number.percent", language=code or current_language(), table="label") or ""


def group_separator(code: str | None = None) -> str:
    """Return what this language puts between groups of three digits.

    A comma in English, a narrow no-break space in French. Both languages group
    and this package did neither, so a French report read `10870,6 s` and
    `400000 num_samples` — the decimal separator applied and the grouping rule
    not, which is the same omission the per-cent sign had.

    Parameters
    ----------
    code : str or None, optional
        A language tag; the one in force when omitted.

    Returns
    -------
    str
        The separator, empty for a language that does not group.

    Examples
    --------
    >>> group_separator("en")
    ','
    >>> group_separator("fr") == "\u202f"
    True
    """
    return phrase("number.group", language=code or current_language(), table="label") or ""


#: A run of four digits or more that is the whole part of a figure, and
#: therefore the part that groups. Not preceded by a digit, a decimal separator
#: or an exponent marker: `0.12345` has five digits after its point and they are
#: tenths, and `1.906e+04` has an exponent that is not a quantity.
_WHOLE_PART: Final[re.Pattern[str]] = re.compile(r"(?<![\d.,])(?<![eE][+-])\d{4,}(?![\d])")


def number(text: str) -> str:
    """Return a formatted number written the way the language in force writes it.

    Takes the output of a format specification rather than a value, so that
    every caller keeps the precision it chose — significant figures, a fixed
    number of decimals, scientific notation — and only the separator moves.

    Three things move: the decimal separator, the space before a per-cent sign,
    and the grouping of the whole part. Nothing else is touched. A blanket
    substitution over a report would have rewritten dates, schema versions,
    dotted field paths and URLs; this is called on the digits and on nothing
    else — audited call site by call site before the grouping was added, because
    a year grouped as `2 025` is the exact failure that docstring warns about,
    and no caller passes one.

    Parameters
    ----------
    text : str
        An already-formatted number, in the authored notation.

    Returns
    -------
    str
        The same figure, written this language's way.

    Examples
    --------
    >>> number("17.4")
    '17.4'
    >>> number("21.9%")
    '21.9%'
    >>> with language("fr"):
    ...     number("17.4"), number("1.087e+04"), number("not known")
    ('17,4', '1,087e+04', 'not known')
    >>> with language("fr"):
    ...     number("21.9%") == "21,9\u202f%"
    True
    >>> number("1234567.89")
    '1,234,567.89'
    >>> with language("fr"):
    ...     number("10870.6 s") == "10\u202f870,6 s"
    True
    >>> number("0.12345"), number("1.906e+04"), number("2.5e-06")
    ('0.12345', '1.906e+04', '2.5e-06')
    """
    if not text:
        return text
    separator = decimal_separator()
    if separator != ".":
        # Only between digits: `2.5e-05` has one, `example.invalid` has none,
        # and a thousands group would be a different decision in a different
        # sentence.
        text = re.sub(r"(?<=\d)\.(?=\d)", separator, text)
    spacing = percent_space()
    if spacing:
        # Only a sign that follows a figure. A per-cent sign is the one unit
        # English sets tight against its number and French does not.
        text = re.sub(rf"(?<=\d)(?<!{re.escape(spacing)})%", spacing + "%", text)
    grouping = group_separator()
    if grouping:
        text = _WHOLE_PART.sub(lambda found: _grouped(found.group(0), grouping), text)
    return text


def _grouped(digits: str, separator: str) -> str:
    """Return a run of digits with a separator every three, counting from the right."""
    out = []
    for index, digit in enumerate(reversed(digits)):
        if index and index % 3 == 0:
            out.append(separator)
        out.append(digit)
    return "".join(reversed(out))


def sort_key(text: str) -> str:
    """Return a key that orders words the way a reader expects to find them.

    Python sorts by code point, which puts `Égypte` after `Ukraine` and `Suisse`
    before `Suède` — a French dropdown with three countries exiled past Z and
    two in the wrong order. An accent is a mark on a letter, not a different
    letter, so the mark comes off for the comparison and stays on the word.

    Not full Unicode collation: that is a table per language and a dependency,
    and this orders Latin script for the two languages this package writes. A
    language whose order is not its alphabet's would need more than this, and
    should say so rather than inherit it.

    Parameters
    ----------
    text : str
        What a reader sees.

    Returns
    -------
    str
        Fold-cased, with combining marks removed.

    Examples
    --------
    >>> sorted(["Ukraine", "Égypte", "Suisse", "Suède"], key=sort_key)
    ['Égypte', 'Suède', 'Suisse', 'Ukraine']
    >>> sort_key("États-Unis")
    'etats-unis'
    """
    decomposed = unicodedata.normalize("NFD", text)
    return "".join(mark for mark in decomposed if not unicodedata.combining(mark)).casefold()


def plural(count: int, one: str, many: str) -> str:
    """Return the form this language uses for a count, and the count with it.

    English and French disagree about zero: *0 errors* is plural, *0 erreur* is
    singular. One is not a rule the code can hold, because it is a property of
    the language; it is a key, like every other wording here.

    Parameters
    ----------
    count : int
        How many.
    one : str
        The wording for a single thing, with no count in it.
    many : str
        The wording for several.

    Returns
    -------
    str
        The count and the right form, separated by a space.

    Examples
    --------
    >>> plural(1, "error", "errors"), plural(0, "error", "errors")
    ('1 error', '0 errors')
    >>> with language("fr"):
    ...     plural(0, "erreur", "erreurs"), plural(2, "erreur", "erreurs")
    ('0 erreur', '2 erreurs')
    """
    if count == 1:
        return f"{count} {one}"
    if count == 0:
        zero = phrase("number.plural.zero", language=current_language(), table="label") or "many"
        return f"{count} {one if zero == 'one' else many}"
    return f"{count} {many}"


def say(key: str, /, **arguments: object) -> str:
    """Return one of the engine's sentences, in the language in force.

    Parameters
    ----------
    key : str
        The sentence's key in the message catalogue.
    **arguments
        What the sentence names in braces. Formatted with :meth:`str.format`,
        so a sentence may use its arguments in whatever order its own language
        needs — which is the point of a catalogue rather than a concatenation.

    Returns
    -------
    str
        The sentence. A key the language has no wording for falls back to
        English, and a key nothing has is returned bracketed so it shows up in
        a page instead of vanishing — a missing sentence is a defect, and a
        contract test fails for it, but it must not take an audit down.

    Examples
    --------
    >>> say("ghg.label.scope2_location")
    'Scope 2 (location-based)'
    >>> with language("fr"):
    ...     say("ghg.not_an_emission.money")
    "L'argent est un coût, pas une émission. Aucun scope ne s'applique."
    >>> say("nothing.has.this.key")
    '[nothing.has.this.key]'
    """
    table = messages()
    for candidate in (current_language(), DEFAULT_LANGUAGE):
        wording = table.get(candidate, {}).get(key)
        if wording:
            try:
                return wording.format(**arguments) if arguments else wording
            except (IndexError, KeyError) as error:
                # A translation naming an argument the caller does not pass is a
                # defect in the catalogue, caught by a contract test. Here it
                # must not take an audit down, and it must not pretend either.
                return f"[{key}: {error}]"
    return f"[{key}]"


def resolve(language: str | None) -> str:
    """Return the code this package will answer in for what a caller asked.

    An agent passes what the person in front of it typed: ``fr``, ``FR``,
    ``fr-FR``, ``fr_CA``. All four mean the same table here, and anything with
    no table falls back to English — loudly, through
    :data:`UNKNOWN_LANGUAGE`, rather than by quietly answering in a language
    nobody asked for.

    Parameters
    ----------
    language : str or None
        A language tag, or ``None`` for the default.

    Returns
    -------
    str
        A code :func:`languages` contains.

    Examples
    --------
    >>> resolve(None), resolve("fr_CA"), resolve("klingon")
    ('en', 'fr', 'en')
    """
    if not language:
        return DEFAULT_LANGUAGE
    code = str(language).strip().lower().replace("_", "-").split("-")[0]
    return code if code in languages() else DEFAULT_LANGUAGE


def unknown_language_note(language: str | None) -> str | None:
    """Return what to tell a caller who asked for a language nothing is written in.

    Falling back to English is the right behaviour — an audit must not fail over
    a language tag — but doing it silently would leave somebody holding a report
    in a language they did not ask for with nothing saying why. So the fallback
    is a note, in the same place every other missing catalogue row goes.

    Parameters
    ----------
    language : str or None
        What the caller asked for.

    Returns
    -------
    str or None
        The note, or ``None`` when the language is one this package speaks.

    Examples
    --------
    >>> unknown_language_note("fr_CA") is None
    True
    >>> "klingon" in unknown_language_note("klingon")
    True
    """
    if not language:
        return None
    asked = str(language).strip().lower().replace("_", "-").split("-")[0]
    used = resolve(language)
    if asked == used:
        return None
    return UNKNOWN_LANGUAGE.format(asked=language, used=used, offered=", ".join(languages()))


def phrase(key: str, *, language: str = DEFAULT_LANGUAGE, table: str = "prompt") -> str:
    """Return one translated phrase.

    Parameters
    ----------
    key : str
        The phrase's key.
    language : str, optional
        A language tag, resolved by :func:`resolve`.
    table : {'prompt', 'label', 'message'}, optional
        Which table to read: what the package asks, what a page labels, or what
        the engine says. ``say`` is the way to read the last of these in the
        language in force; this is the way to read one language in particular,
        which the recognisers of already-written prose need.

    Returns
    -------
    str
        The phrase, or its English wording when the language has no entry for
        that key, or an empty string when nothing does. An empty string is the
        right answer for a missing key in a prompt: a sentence of English
        inserted into a French instruction is worse than a sentence less.

    Examples
    --------
    >>> phrase("prompt.classify.language", language="en").startswith("Write")
    True
    >>> phrase("boundary.idle_prefix", language="fr", table="message")
    'La capacité au repos'
    >>> phrase("nothing.has.this.key")
    ''
    """
    tables = {"prompt": prompts, "label": labels, "message": messages}[table]()
    code = resolve(language)
    for candidate in (code, DEFAULT_LANGUAGE):
        found = tables.get(candidate, {}).get(key)
        if found:
            return found
    return ""
