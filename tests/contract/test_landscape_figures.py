"""The landscape pages' two visuals, held to the table they are drawn from.

The star table in ``LANDSCAPE.md`` and ``PAYSAGE.md`` feeds two pictures: a
hand-authored figure of the four links of the question, and a positioning map
drawn by ``standpoint`` from a numeric table. Both rot the same quiet way. A row
is added to the table, the committed comma-separated-values file still says
fourteen tools, and the map goes on placing a cohort that no longer exists --
with no words on it for a reviewer to catch.

These hold each visual to its source: the numeric tables to the stars they were
counted from, the figures to their generator, each language's figure to the
other, and both to the page that shows them.
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

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "assets"

sys.path.insert(0, str(ASSETS))

import make_landscape_figure as figure  # noqa: E402
import make_landscape_map as numbers  # noqa: E402

#: Each language: the page that carries it, and the suffix its files take.
PAGES: dict[str, tuple[str, str]] = {"en": ("LANDSCAPE.md", ""), "fr": ("PAYSAGE.md", "fr.")}


def _figure(lang: str) -> Path:
    """Return the committed figure for one language."""
    return ASSETS / f"landscape-links.{PAGES[lang][1]}svg"


# --------------------------------------------------------------------------- #
# the numeric tables, and the map drawn from them
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(("page", "stem"), sorted(numbers.PAGES.items()))
def test_the_numeric_table_is_the_page_s_own_stars(page: str, stem: str) -> None:
    """The comma-separated-values file is counted from the page, not kept beside it.

    Two copies of one fact is the defect this repository keeps finding in its
    own prose, and a positioning map is the worst place for it: a map drawn
    from a stale table is wrong in a way that looks like an opinion.
    """
    committed = (ASSETS / f"{stem}.csv").read_text(encoding="utf-8")
    assert committed == numbers.comma_separated(page), (
        f"assets/{stem}.csv is not what {page}'s table says. Run "
        "`python assets/make_landscape_map.py` and redraw the map"
    )


@pytest.mark.parametrize(("page", "stem"), sorted(numbers.PAGES.items()))
def test_the_map_was_drawn_from_the_table_it_is_shown_beside(page: str, stem: str) -> None:
    """Every tool in the table is on the map, and nothing else is.

    ``standpoint`` writes a coordinate file beside the picture, which is the
    only part of its output a test can read. A row added to the page and never
    redrawn shows up here as a name the map has never heard of.
    """
    name = "landscape.yaml" if stem.endswith(".en") else "landscape.fr.yaml"
    drawn = yaml.safe_load((ASSETS / name).read_text(encoding="utf-8"))
    ratings, criteria = numbers.read(page)
    assert drawn["meta"]["attributes"] == criteria, (
        f"{name} was drawn against different criteria than {page} now lists"
    )
    placed = {
        entry["name"]: [int(entry["attributes"][column]) for column in criteria]
        for entry in drawn["approaches"]
    }
    assert placed == ratings, (
        f"{name} places a different cohort than {page} rates. Redraw the map: "
        f"`standpoint assets/{stem}.csv -r {numbers.REFERENCE} -o assets "
        f"--stem {name[: -len('.yaml')]} --model qwen3:8b`"
    )
    assert drawn["meta"]["reference"] == numbers.REFERENCE


def test_the_map_s_own_generator_runs() -> None:
    """Its examples are run, because a usage example nobody runs is a comment."""
    assert doctest.testmod(numbers, verbose=False).failed == 0


# --------------------------------------------------------------------------- #
# the hand-authored figure
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("lang", sorted(PAGES))
def test_the_figure_is_shown_on_its_own_language_s_page(lang: str) -> None:
    """An English figure on the French page is the gap a reader cannot work around."""
    path = _figure(lang)
    assert path.is_file(), f"{path.name} is missing"
    assert path.name in (ROOT / PAGES[lang][0]).read_text(encoding="utf-8")


@pytest.mark.parametrize("lang", sorted(PAGES))
def test_the_alt_text_is_the_figure_s_own_description(lang: str) -> None:
    """One sentence, written once, so neither copy can go stale alone."""
    page = (ROOT / PAGES[lang][0]).read_text(encoding="utf-8")
    block = next(match for match in re.findall(r"<img[^>]*>", page) if _figure(lang).name in match)
    alt = html.unescape(re.search(r'alt="([^"]*)"', block).group(1))
    described = html.unescape(
        re.search(r"<desc[^>]*>(.*?)</desc>", _figure(lang).read_text(encoding="utf-8"), re.S)
        .group(1)
        .strip()
    )
    assert len(alt) > 60, f"the {lang} figure needs alt text that says what it shows"
    assert alt == described


def test_the_committed_figures_are_what_the_generator_writes() -> None:
    """Hand-edited is the failure every other check here would pass."""
    committed = {_figure(lang): _figure(lang).read_bytes() for lang in PAGES}
    subprocess.run(  # noqa: S603 - a fixed argument list, in this repository.
        [sys.executable, str(ASSETS / "make_landscape_figure.py")], check=True, capture_output=True
    )
    for path, body in committed.items():
        assert path.read_bytes() == body, (
            f"{path.name} is not what its generator produces. Run "
            "`python assets/make_landscape_figure.py` and commit the result"
        )


def test_both_languages_get_the_same_figure() -> None:
    """Same boxes, same arrows, different words."""
    shapes = [
        (body.count("<g>"), body.count("marker-end"))
        for body in (_figure(lang).read_text(encoding="utf-8") for lang in PAGES)
    ]
    assert shapes[0] == shapes[1], "the figure is drawn differently in the two languages"


@pytest.mark.parametrize("lang", sorted(PAGES))
def test_the_figure_follows_the_reader_s_theme_and_says_what_it_shows(lang: str) -> None:
    """A figure in a README is read in whichever theme the reader set."""
    body = _figure(lang).read_text(encoding="utf-8")
    assert "prefers-color-scheme" in body
    assert 'role="img"' in body and "<desc" in body


@pytest.mark.parametrize("lang", sorted(PAGES))
def test_every_status_the_figure_shows_is_a_status_the_package_has(lang: str) -> None:
    """The pills are this package's own vocabulary, used on itself.

    A fifth word on the figure would be a status the validator has never heard
    of, which is the one mistake that would make the drawing look more rigorous
    than the tool.
    """
    import make_readme_figures as style

    shown = {row["status"] for row in figure.LINKS[lang]["rows"]}  # type: ignore[attr-defined]
    assert shown <= set(style.STATUSES), f"the {lang} figure shows a status that does not exist"


@pytest.mark.parametrize("lang", sorted(PAGES))
def test_every_tool_the_figure_names_is_a_tool_the_page_rates(lang: str) -> None:
    """A figure may not introduce a tool the page never scored.

    The second band names who answers each link best. Each of those names has
    to be one a reader can then look up in the table, or the figure is sending
    them somewhere the page does not go.
    """
    rated = set(numbers.read(PAGES[lang][0])[0])
    known = {part.strip() for name in rated for part in name.split("/")}
    for row in figure.LINKS[lang]["rows"]:  # type: ignore[attr-defined]
        for candidate in re.findall(r"[A-Z][A-Za-z0-9.\-]+(?: [A-Z][A-Za-z0-9.\-]+)*", row["who"]):
            if candidate in known or candidate.split()[0] in known:
                continue
            assert not candidate.isupper() or len(candidate) < 4, (
                f"the {lang} figure names {candidate!r}, which the table does not rate"
            )


def test_the_figure_s_own_examples_run() -> None:
    """Its usage example is run, so the module cannot document a call it refuses."""
    assert doctest.testmod(figure, verbose=False).failed == 0
