"""The three figures the front pages explain the tool with, checked against it.

A figure is a claim, drawn large, on the page a stranger reads first. The way it
rots is quieter than prose: the template changes a number, the stylesheet changes
a colour, a public function is renamed, and the drawing goes on saying the old
thing with no words in it for a reviewer to catch. These tests hold the figures
to the files they are drawn from -- the starter model, the report's stylesheet,
the package's own exports -- and to each other, so that the French figure and the
English one stay the same figure.
"""

from __future__ import annotations

import doctest
import html
import re
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

import saggio

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "assets"

sys.path.insert(0, str(ASSETS))

import make_readme_figures as figures  # noqa: E402

#: Each figure, the page that shows it in each language, and the dictionary of
#: words it is drawn from.
PAGES: dict[str, tuple[str, str]] = {"en": ("README.md", ""), "fr": ("LISEZMOI.md", "fr.")}

WORDS = {
    "pipeline": figures.PIPELINE,
    "weakest-link": figures.WEAKEST,
    "surfaces": figures.SURFACES,
}


def _figure(name: str, lang: str) -> Path:
    """Return the committed file for one figure in one language."""
    suffix = PAGES[lang][1]
    return ASSETS / f"readme-{name}.{suffix}svg"


@pytest.mark.parametrize("name", sorted(WORDS))
@pytest.mark.parametrize("lang", sorted(PAGES))
def test_every_figure_is_shown_on_its_own_language_s_front_page(name: str, lang: str) -> None:
    """Each language's page shows its own figure.

    An English figure on the French page is the one gap a reader cannot work
    around: they can see that something was meant to be readable, and is not.
    """
    path = _figure(name, lang)
    assert path.is_file(), f"{path.name} is missing"
    page = (ROOT / PAGES[lang][0]).read_text(encoding="utf-8")
    assert path.name in page, f"{PAGES[lang][0]} does not show {path.name}"


@pytest.mark.parametrize("name", sorted(WORDS))
@pytest.mark.parametrize("lang", sorted(PAGES))
def test_the_alt_text_is_the_figure_s_own_description(name: str, lang: str) -> None:
    """The page's alt text is the figure's description, word for word.

    They are one sentence, so neither can be improved while the other goes
    stale.
    """
    page = (ROOT / PAGES[lang][0]).read_text(encoding="utf-8")
    block = next(
        match for match in re.findall(r"<img[^>]*>", page) if _figure(name, lang).name in match
    )
    alt = html.unescape(re.search(r'alt="([^"]*)"', block).group(1))
    described = html.unescape(
        re.search(r"<desc[^>]*>(.*?)</desc>", _figure(name, lang).read_text(encoding="utf-8"), re.S)
        .group(1)
        .strip()
    )
    assert len(alt) > 60, f"{name} ({lang}) needs alt text that says what it shows"
    assert alt == described, f"the alt text for {name} ({lang}) is not the figure's own description"


def test_the_committed_figures_are_what_the_generator_writes() -> None:
    """Hand-edited is the failure every other check here would pass.

    One generator, six files: the moment one of them is touched by hand it stops
    being reproducible, and the next regeneration silently throws the edit away.
    """
    committed = {
        _figure(name, lang): _figure(name, lang).read_bytes() for name in WORDS for lang in PAGES
    }
    subprocess.run(  # noqa: S603 - a fixed argument list, in this repository.
        [sys.executable, str(ASSETS / "make_readme_figures.py")], check=True, capture_output=True
    )
    for path, body in committed.items():
        assert path.read_bytes() == body, (
            f"{path.name} is not what its generator produces. Run "
            "`python assets/make_readme_figures.py` and commit the result"
        )


@pytest.mark.parametrize("name", sorted(WORDS))
def test_both_languages_get_the_same_figure(name: str) -> None:
    """Same boxes, same arrows, different words.

    A translation that quietly dropped a box would be a different explanation
    wearing the same title, and nobody reading one language could tell.
    """
    counts = []
    for lang in PAGES:
        body = _figure(name, lang).read_text(encoding="utf-8")
        counts.append((body.count("<g>"), body.count("marker-end")))
    assert counts[0] == counts[1], f"{name} is drawn differently in the two languages"


@pytest.mark.parametrize("name", sorted(WORDS))
@pytest.mark.parametrize("lang", sorted(PAGES))
def test_the_figures_are_drawn_in_the_report_s_own_colours(name: str, lang: str) -> None:
    """The palette is the report's, read from its stylesheet.

    A figure and the report it introduces may not disagree about what
    ``estimated`` looks like: the reader meets the same colour twice and would
    have to work out which one means what.
    """
    palette = figures.tokens()
    body = _figure(name, lang).read_text(encoding="utf-8")
    for scheme in ("light", "dark"):
        for status in figures.STATUSES:
            colour = palette[scheme][status.lower()]
            assert colour in body, f"{name} ({lang}) does not use the report's {status} colour"


@pytest.mark.parametrize("name", sorted(WORDS))
@pytest.mark.parametrize("lang", sorted(PAGES))
def test_every_figure_follows_the_reader_s_theme_and_says_what_it_shows(
    name: str, lang: str
) -> None:
    body = _figure(name, lang).read_text(encoding="utf-8")
    assert "prefers-color-scheme" in body, f"{name} ({lang}) is drawn for one theme only"
    assert 'role="img"' in body and "<title" in body and "<desc" in body


def test_the_chain_figure_draws_the_derivation_the_template_actually_states() -> None:
    """The second figure is only worth drawing if it is the shipped model's chain.

    Every arrow is checked against the ``derived_from`` list of the quantity it
    points at, in both directions: an arrow the template does not state would be
    an invented derivation, and a missing arrow would show a value as resting on
    less than it does, which is the flattering half of the same mistake.
    """
    template = yaml.safe_load(figures.TEMPLATE.read_text(encoding="utf-8"))
    path_of = {key: path for key, _, _, path in figures.CHAIN}
    drawn: dict[str, set[str]] = {}
    for source, target in figures.LINKS:
        drawn.setdefault(target, set()).add(path_of[source])
    for target, inputs in drawn.items():
        stated = set(figures._at(template, path_of[target]).get("derived_from", []))
        assert inputs == stated, (
            f"the figure draws {target} as coming from {sorted(inputs)}, the template says "
            f"{sorted(stated)}"
        )


@pytest.mark.parametrize("lang", sorted(PAGES))
def test_the_chain_figure_shows_the_template_s_own_numbers(lang: str) -> None:
    body = _figure("weakest-link", lang).read_text(encoding="utf-8")
    for _, _, _, path in figures.CHAIN:
        value = figures.reading(path, lang)
        assert value in body, f"the chain figure ({lang}) does not show {path} as {value}"


def test_each_language_writes_the_numbers_its_own_way() -> None:
    """Each language writes the figures its own way.

    The drawings are part of the pages, so they obey the pages' own rule: a
    number is written the way the language writes it, decimal mark included.
    """
    english = _figure("weakest-link", "en").read_text(encoding="utf-8")
    french = _figure("weakest-link", "fr").read_text(encoding="utf-8")
    assert "0.1 s" in english and "0.0014" in english
    assert "0,1 s" in french and "0,0014" in french


def test_the_surfaces_figure_names_functions_the_package_exports() -> None:
    """The engine card lists names ``import saggio`` really gives you.

    A figure listing a function nobody can call would be the worst kind of
    documentation: it reads as a promise and fails at the import line.
    """
    for name in figures.ENGINE:
        assert name.endswith("()")
        assert name[:-2] in saggio.__all__, f"{name} is drawn but not exported"


@pytest.mark.parametrize("lang", sorted(PAGES))
def test_the_surfaces_figure_lists_the_five_surfaces_its_page_lists(lang: str) -> None:
    page = (ROOT / PAGES[lang][0]).read_text(encoding="utf-8")
    rows = figures.SURFACES[lang]["rows"]
    assert len(rows) == 5, "there are five surfaces, and the figure draws all of them"
    for surface, _, invocation in rows:
        assert surface in page, f"{PAGES[lang][0]} does not name the surface {surface!r}"
        assert invocation in page or invocation.rstrip("/") in page, (
            f"{PAGES[lang][0]} does not show how to reach {surface!r}"
        )


def test_the_generator_s_own_examples_run() -> None:
    """The generator's examples run, though it lives outside the package.

    The suite's doctest sweep covers ``tests`` and ``saggio``; this file is in
    neither, and its examples are documentation all the same.
    """
    results = doctest.testmod(figures, verbose=False)
    assert results.failed == 0, f"{results.failed} example(s) in the generator fail"
    assert results.attempted > 0
