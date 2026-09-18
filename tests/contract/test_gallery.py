"""The gallery, checked against the tool that produced it.

A worked example is a claim about what this package does, committed where a
stranger will read it. The way that claim rots is that the code changes, nobody
regenerates the files, and the gallery goes on showing an answer the tool no
longer gives. These tests cannot stop the files ageing, but they can stop them
being wrong about their own rules: every model validates, every model has its
report beside it, and the page that introduces them names them all.
"""

from __future__ import annotations

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
