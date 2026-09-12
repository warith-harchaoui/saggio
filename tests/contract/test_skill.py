"""The agent skill, checked against the repository it describes."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
SKILL_DIR = ROOT / "skills" / "running-code-cost-helper"
SKILL = SKILL_DIR / "SKILL.md"


def frontmatter() -> dict:
    text = SKILL.read_text(encoding="utf-8")
    assert text.startswith("---\n")
    return yaml.safe_load(text.split("---", 2)[1])


def body() -> str:
    return SKILL.read_text(encoding="utf-8").split("---", 2)[2]


def test_the_skill_exists_and_has_frontmatter() -> None:
    assert SKILL.is_file()
    assert frontmatter()["name"] == "running-code-cost-helper"


@pytest.mark.parametrize("field", ["name", "description", "license", "compatibility", "metadata"])
def test_the_frontmatter_is_complete(field: str) -> None:
    assert frontmatter()[field]


def test_the_description_says_when_not_to_fire() -> None:
    # A skill that only says when it applies fires on everything adjacent to it.
    assert "Do not use" in frontmatter()["description"]


def test_the_skill_version_matches_the_package() -> None:
    from running_code_cost_helper import __version__

    assert str(frontmatter()["metadata"]["version"]) == __version__


@pytest.mark.parametrize(
    "reference",
    ["honesty-taxonomy.md", "schema.md", "green-algorithms.md", "landscape.md"],
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


def test_the_evals_are_valid_json_and_cover_the_refusals() -> None:
    cases = json.loads((SKILL_DIR / "evals" / "evals.json").read_text(encoding="utf-8"))["cases"]
    ids = {case["id"] for case in cases}
    for required in {
        "never-guesses-the-country",
        "never-writes-a-remembered-number",
        "asks-before-running-code",
        "does-not-invent-water",
        "respects-a-refusal",
    }:
        assert required in ids
    for case in cases:
        assert case["prompt"] and case["expect"]


def test_every_command_the_skill_shows_parses() -> None:
    import shlex

    from running_code_cost_helper.cli.app import build_parser

    parser = build_parser()
    text = SKILL.read_text(encoding="utf-8").replace("\\\n", " ")
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("running-code-cost-helper "):
            continue
        argv = [
            "https://example.invalid" if part.startswith("http") else part
            for part in shlex.split(stripped.removeprefix("running-code-cost-helper "))
            if part not in {"...", "…"}
        ]
        try:
            parser.parse_args(argv)
        except SystemExit as exit_info:
            pytest.fail(f"SKILL.md shows `{stripped}`, which the parser rejects ({exit_info})")
