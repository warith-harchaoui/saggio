"""The gallery, checked against the tool that produced it.

A worked example is a claim about what this package does, committed where a
stranger will read it. The way that claim rots is that the code changes, nobody
regenerates the files, and the gallery goes on showing an answer the tool no
longer gives. These tests cannot stop the files ageing, but they can stop them
being wrong about their own rules: every model validates, every model has its
report beside it, and the page that introduces them names them all.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

from saggio.model import CostModel, validate

ROOT = Path(__file__).resolve().parents[2]
EXAMPLES = ROOT / "examples"

#: Every committed model, the top-level gallery and the walkthrough alike.
MODELS = sorted(path.relative_to(ROOT).as_posix() for path in EXAMPLES.rglob("*.yaml"))


def test_the_gallery_is_not_empty() -> None:
    assert len(MODELS) >= 6, "the gallery is meant to hold more than a token example"


@pytest.mark.parametrize("model", MODELS)
def test_every_model_in_the_gallery_passes_its_own_rules(model: str) -> None:
    # These files are what the package produces. One of them failing its own
    # validator would mean the tool writes models it would then reject.
    data = yaml.safe_load((ROOT / model).read_text(encoding="utf-8"))
    verdict = validate(CostModel.from_mapping(data))
    assert verdict.ok, f"{model}: {[issue.message for issue in verdict.errors]}"


@pytest.mark.parametrize("model", MODELS)
def test_every_model_has_its_report_beside_it(model: str) -> None:
    # The point of the gallery is that somebody who will never open a terminal can
    # read it, which they cannot do from YAML.
    assert (ROOT / model).with_suffix(".md").is_file(), (
        f"{model} has no rendered report; run `saggio render {model} -f md`"
    )


@pytest.mark.parametrize("model", MODELS)
def test_every_model_says_what_one_unit_of_work_is(model: str) -> None:
    data = yaml.safe_load((ROOT / model).read_text(encoding="utf-8"))
    unit = data.get("unit_of_work") or {}
    assert unit.get("name"), f"{model} states no unit of work, so none of its numbers mean anything"


@pytest.mark.parametrize("page", ["GALLERY.md", "GALERIE.md"])
def test_the_gallery_page_names_every_model_it_ships(page: str) -> None:
    # A model nobody linked to is a file nobody reads and nobody maintains.
    text = (ROOT / page).read_text(encoding="utf-8")
    for model in MODELS:
        assert model in text, f"{page} never mentions {model}"


@pytest.mark.parametrize("page", ["GALLERY.md", "GALERIE.md"])
def test_the_gallery_says_these_are_not_cost_claims(page: str) -> None:
    # The one thing a gallery of scaffolds must never be read as.
    text = (ROOT / page).read_text(encoding="utf-8").lower()
    assert "cost claim" in text or "affirmation de coût" in text


def test_a_cloned_model_says_whose_machine_it_describes() -> None:
    # Every model here but the two local ones was read from a clone on a laptop,
    # and a reader taking that laptop for a training cluster would carry the
    # mistake into every energy figure below it.
    cloned = [
        model
        for model in MODELS
        if str(
            yaml.safe_load((ROOT / model).read_text(encoding="utf-8"))
            .get("project", {})
            .get("audited_from", "")
        ).startswith("http")
    ]
    assert cloned, "the gallery is meant to include repositories read from their URL"
    for model in cloned:
        data = yaml.safe_load((ROOT / model).read_text(encoding="utf-8"))
        assert "machine_provenance" in data["deployment"], model


def test_the_walkthrough_measured_stage_really_is_measured() -> None:
    # The point of the four stages is that one number changes status. If the
    # measured stage were committed with a TODO runtime, the walkthrough would be
    # teaching the opposite of what it says.
    measured = yaml.safe_load(
        (EXAMPLES / "walkthrough" / "3-measured.yaml").read_text(encoding="utf-8")
    )
    assert measured["scenarios"][0]["runtime"]["status"] == "measured"
    # And the weakest-link rule has to be visible in the same file: the energy is
    # that measured runtime times a power draw nobody measured.
    assert measured["scenarios"][0]["costs"]["energy"]["status"] == "estimated"


def test_the_walkthrough_first_stage_has_nothing_measured_yet() -> None:
    as_read = yaml.safe_load(
        (EXAMPLES / "walkthrough" / "1-as-read.yaml").read_text(encoding="utf-8")
    )
    assert as_read["scenarios"][0]["runtime"]["status"] == "TODO"


def test_the_walkthrough_diff_shows_the_status_moving() -> None:
    text = (EXAMPLES / "walkthrough" / "4-diff.txt").read_text(encoding="utf-8")
    assert "TODO -> measured" in text
    assert "TODO -> estimated" in text


# --- The comparison, and the page it is drawn from ----------------------------


COMPARED_TOOLS: tuple[str, ...] = (
    "codecarbon.io",
    "Eco2AI",
    "carbontracker",
    "scaphandre",
    "powerapi.org",
    "sustainable-computing.io",
    "green-algorithms.org",
    "infracost.io",
    "cloudcarbonfootprint.org",
    "opencost.io",
)


@pytest.mark.parametrize("page", ["GALLERY.md", "GALERIE.md"])
def test_every_tool_the_gallery_compares_is_one_the_landscape_researched(page: str) -> None:
    """A comparison may only name tools the sourced page already covers.

    The gallery makes claims about other people's projects. Those claims are
    somebody else's work to live with, so they are not written here: they are
    drawn from the landscape page, which has the reading behind it. A tool that
    appeared in the comparison and nowhere else would be a claim with no source,
    which is the one thing this package exists to object to -- and it would be
    about a stranger's project rather than our own numbers.
    """
    root = ROOT
    landscape = (root / ("LANDSCAPE.md" if page == "GALLERY.md" else "PAYSAGE.md")).read_text(
        encoding="utf-8"
    )
    text = (root / page).read_text(encoding="utf-8")
    for tool in COMPARED_TOOLS:
        if tool.lower() in text.lower():
            assert tool.lower() in landscape.lower(), (
                f"{page} compares against {tool}, which the landscape page does not "
                "cover. Research it there first, or drop it from the comparison"
            )


@pytest.mark.parametrize("page", ["GALLERY.md", "GALERIE.md"])
def test_the_comparison_refuses_to_rank_the_tools_by_their_numbers(page: str) -> None:
    """The one caveat the comparison may not lose.

    Outputs from these tools are per different units of work and do not sit on
    one scale -- the same rule the gallery already states about its own six
    models. A comparison that quietly dropped the caveat would invite exactly
    the arithmetic the package refuses everywhere else.
    """
    text = (ROOT / page).read_text(encoding="utf-8")
    said = (
        "do not line up" in text
        or "not on one scale" in text
        or "ne s'alignent pas" in text
        or "pas sur\nune même échelle" in text
        or "pas sur une même échelle" in text
    )
    assert said, f"{page} compares tools without saying their numbers do not compare"


@pytest.mark.parametrize("page", ["GALLERY.md", "GALERIE.md"])
def test_the_comparison_figure_is_there_and_carries_alt_text(page: str) -> None:
    root = ROOT
    text = (root / page).read_text(encoding="utf-8")
    # Each language shows its own: the French page points at the French figure.
    name = "gallery-families.svg" if page == "GALLERY.md" else "gallery-families.fr.svg"
    assert name in text, f"{page} does not show the comparison figure"
    assert (root / "assets" / name).is_file()
    for block in re.findall(r"<img[^>]*gallery-families[^>]*>", text):
        alt = re.search(r'alt="([^"]*)"', block)
        assert alt and len(alt.group(1)) > 60, (
            f"{page}: the comparison figure needs alt text that says what it shows"
        )


def test_the_landscape_does_not_still_say_there_is_no_embodied_carbon() -> None:
    """It said so until the day there was.

    A self-assessment that goes stale is worse than none: this page is the one
    the gallery's comparison is drawn from, so a false weakness there would
    propagate into a claim about where the tool stands against others.
    """
    root = ROOT
    for page in ("LANDSCAPE.md", "PAYSAGE.md"):
        text = (root / page).read_text(encoding="utf-8")
        assert "**No embodied carbon.**" not in text
        assert "**Pas de carbone incorporé.**" not in text


def test_both_languages_get_their_own_comparison_figure() -> None:
    """The figure is part of the page, so it is bilingual like the rest of it.

    An English figure on the French page is the one kind of untranslated thing a
    reader cannot work around: they can see that something was meant to be
    readable and is not. Both come out of one generator for the same reason the
    two Markdown pages are checked against each other -- two hand-edited SVGs
    would drift the first time a row changed, and a figure that disagrees with
    its translation leaves nobody able to tell which is right.
    """
    import subprocess
    import sys

    figures = {
        "GALLERY.md": ROOT / "assets" / "gallery-families.svg",
        "GALERIE.md": ROOT / "assets" / "gallery-families.fr.svg",
    }
    for page, svg in figures.items():
        assert svg.is_file(), f"{svg.name} is missing"
        assert svg.name in (ROOT / page).read_text(encoding="utf-8"), (
            f"{page} does not point at {svg.name}"
        )

    generator = ROOT / "assets" / "make_gallery_figure.py"
    assert generator.is_file(), "the figures have no generator, so they will drift"

    # Committed is what the generator writes today. A figure edited by hand
    # would pass every other check here and silently stop being reproducible.
    before = {path: path.read_bytes() for path in figures.values()}
    subprocess.run(  # noqa: S603 - a fixed argument list, in this repository.
        [sys.executable, str(generator)], check=True, capture_output=True
    )
    for path, body in before.items():
        assert path.read_bytes() == body, (
            f"{path.name} is not what its generator produces. Run "
            "`python assets/make_gallery_figure.py` and commit the result"
        )


def test_the_two_comparison_figures_have_the_same_shape() -> None:
    """Same rows, same columns, different words.

    A translation that quietly dropped a row would be a different comparison
    wearing the same name.
    """
    import sys

    sys.path.insert(0, str(ROOT / "assets"))
    try:
        import make_gallery_figure as figure
    finally:
        sys.path.pop(0)

    english, french = figure.ROWS["en"], figure.ROWS["fr"]
    assert len(english) == len(french)
    for (_, colour_en, *_), (_, colour_fr, *_) in zip(english, french, strict=True):
        assert colour_en == colour_fr, "a family changed colour between languages"
    assert sorted(figure.TEXT["en"]) == sorted(figure.TEXT["fr"]), (
        "one language's figure says something the other does not"
    )
