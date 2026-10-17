"""The agent skill, checked against the repository it describes."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
SKILL_DIR = ROOT / "skills" / "saggio"
SKILL = SKILL_DIR / "SKILL.md"


def frontmatter() -> dict:
    text = SKILL.read_text(encoding="utf-8")
    assert text.startswith("---\n")
    return yaml.safe_load(text.split("---", 2)[1])


def body() -> str:
    return SKILL.read_text(encoding="utf-8").split("---", 2)[2]


def test_the_skill_exists_and_has_frontmatter() -> None:
    assert SKILL.is_file()
    assert frontmatter()["name"] == "saggio"


@pytest.mark.parametrize("field", ["name", "description", "license", "compatibility", "metadata"])
def test_the_frontmatter_is_complete(field: str) -> None:
    assert frontmatter()[field]


def test_the_description_says_when_not_to_fire() -> None:
    # A skill that only says when it applies fires on everything adjacent to it.
    assert "Do not use" in frontmatter()["description"]


def test_the_skill_version_matches_the_package() -> None:
    from saggio import __version__

    assert str(frontmatter()["metadata"]["version"]) == __version__


@pytest.mark.parametrize(
    "reference",
    ["honesty-taxonomy.md", "schema.md", "green-algorithms.md", "landscape.md", "inventory.md"],
)
def test_every_reference_the_skill_links_to_exists(reference: str) -> None:
    # The predecessor of this package shipped a skill linking to a reference file
    # that had never been written, which an agent discovers only mid-task.
    assert (SKILL_DIR / "references" / reference).is_file()


def test_the_skill_links_to_every_reference_that_exists() -> None:
    linked = set(re.findall(r"references/([a-z0-9-]+\.md)", SKILL.read_text(encoding="utf-8")))
    on_disk = {path.name for path in (SKILL_DIR / "references").glob("*.md")}
    assert on_disk <= linked, f"unlinked references: {sorted(on_disk - linked)}"


def test_the_skill_states_the_rule_it_exists_to_protect() -> None:
    assert "Never write a number that was not established" in body()


def test_the_skill_names_the_four_statuses() -> None:
    text = body()
    for status in ("measured", "estimated", "placeholder", "TODO"):
        assert f"`{status}`" in text


def test_the_skill_does_not_tell_an_agent_to_grant_consent() -> None:
    text = body()
    assert "Never run `consent grant` on their behalf" in text


def test_the_name_is_the_folder_in_kebab_case() -> None:
    # The loader matches the two, and a capital or an underscore in either is a
    # skill that silently never loads.
    name = frontmatter()["name"]
    assert name == SKILL_DIR.name
    assert re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", name)


def test_the_description_fits_in_the_window_it_is_read_in() -> None:
    # The frontmatter sits in the system prompt, where the published ceiling is
    # 1024 characters. Past it the description is not shortened, it is refused.
    assert len(frontmatter()["description"]) <= 1024


@pytest.mark.parametrize("field", ["name", "description", "compatibility"])
def test_no_frontmatter_field_carries_angle_brackets(field: str) -> None:
    # Frontmatter is pasted into a prompt, so the characters that open a tag are
    # refused there rather than escaped.
    value = str(frontmatter()[field])
    assert "<" not in value and ">" not in value


@pytest.mark.parametrize(
    "phrase",
    ["cost per request", "carbon per inference", "empreinte carbone", "CSRD", "scope"],
)
def test_the_description_carries_the_words_both_readers_type(phrase: str) -> None:
    # This skill has two audiences asking one question from opposite ends: an
    # engineer who says "cost per request" and a sustainability team that says
    # "scope" and "CSRD". A description written for either alone never loads for
    # the other, and the French wording is not optional for the second.
    assert phrase.lower() in frontmatter()["description"].lower()


def evals() -> dict:
    return json.loads((SKILL_DIR / "evals" / "evals.json").read_text(encoding="utf-8"))


def test_the_evals_say_when_the_skill_should_load_and_when_it_should_not() -> None:
    # Behaviour cases test a skill that has already loaded. Whether it loads at
    # all is the first thing that can fail and the only one no case here covers.
    triggering = evals()["triggering"]
    assert len(triggering["should_fire"]) >= 8
    assert len(triggering["should_not_fire"]) >= 5


def test_the_triggers_cover_both_wordings_of_the_same_question() -> None:
    # One list in one vocabulary is a skill that fires for engineers and stays
    # silent for the people who have to file the figure, or the reverse.
    firing = " ".join(evals()["triggering"]["should_fire"]).lower()
    for wording in ("cost per", "empreinte carbone", "scope", "csrd"):
        assert wording in firing


def test_the_whole_inventory_is_a_trigger_the_skill_refuses() -> None:
    # The nearest adjacent question, and the one it would be most damaging to
    # answer: a cost model for one unit of work is not a corporate inventory.
    refused = " ".join(evals()["triggering"]["should_not_fire"]).lower()
    assert "inventory" in refused or "bilan carbone complet" in refused


def test_the_evals_are_valid_json_and_cover_the_refusals() -> None:
    cases = json.loads((SKILL_DIR / "evals" / "evals.json").read_text(encoding="utf-8"))["cases"]
    ids = {case["id"] for case in cases}
    for required in {
        "never-guesses-the-country",
        "never-writes-a-remembered-number",
        "asks-before-running-code",
        "does-not-invent-water",
        "respects-a-refusal",
        "never-derives-a-market-based-figure",
        "does-not-pretend-to-be-an-inventory",
    }:
        assert required in ids
    for case in cases:
        assert case["prompt"] and case["expect"]


def test_every_command_the_skill_shows_parses() -> None:
    import shlex

    from saggio.cli.app import build_parser

    parser = build_parser()
    text = SKILL.read_text(encoding="utf-8").replace("\\\n", " ")
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("saggio "):
            continue
        argv = [
            "https://example.invalid" if part.startswith("http") else part
            for part in shlex.split(stripped.removeprefix("saggio "))
            if part not in {"...", "…"}
        ]
        try:
            parser.parse_args(argv)
        except SystemExit as exit_info:
            pytest.fail(f"SKILL.md shows `{stripped}`, which the parser rejects ({exit_info})")
