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


#: Initialisms the skill's body uses without writing out, each because it sits
#: inside a phrase a *user* types. The description's whole job is to be matched
#: against what somebody asks for, and the body quotes those same askings; an
#: expansion inside a quotation changes what the person said, which is the one
#: thing this repository's own rule forbids.
QUOTED_BY_A_USER: dict[str, str] = {
    "API": 'in "carbon footprint of our API", a phrase a user types',
    "CSRD": 'in "we need a figure for CSRD", a phrase a user types',
    "ESRS": 'in "ESRS E1", the name of the standard as a filer says it',
    "GPU": 'in "which GPU should we buy", a phrase a user types',
}


#: Per reference file, the initialisms it uses without writing out, and why.
#: Each sits inside a question a user asks or the name of a platform, and the
#: repository's rule is that neither gets rewritten.
QUOTED_IN_REFERENCES: dict[str, dict[str, str]] = {
    "inventory.md": {
        "AWS": "a column of platform names: AWS, GCP, Azure",
        "GCP": "a column of platform names: AWS, GCP, Azure",
        "GPU": 'the phrase "a GPU cloud" in that same column of platforms',
    },
    "landscape.md": {
        "AWS": 'inside "Why was our AWS bill so high last month?", a user\'s question',
        "GCP": "the product name GCP Billing",
        "GPU": 'inside "Which GPU should we buy?", a user\'s question',
    },
}


def _declared_initialisms() -> dict[str, str]:
    """The glossary, as the pages are held to it."""
    declared: dict[str, str] = {}
    for line in (ROOT / "GLOSSARY.md").read_text(encoding="utf-8").splitlines():
        found = re.match(r"\|\s*\*\*([A-Z][A-Z0-9]*)\*\*\s*\|\s*([^|]*?)\s*\|", line)
        if found and found.group(2) not in {"", "—"}:
            declared[found.group(1)] = found.group(2)
    return declared


def _prose_of(text: str) -> str:
    """Prose only: no fenced blocks, no inline code."""
    without = re.sub(r"```.*?```", " ", text, flags=re.S)
    return re.sub(r"`[^`]*`", " ", without)


@pytest.mark.parametrize(
    "reference", sorted(path.name for path in (SKILL_DIR / "references").glob("*.md"))
)
def test_each_reference_writes_out_the_initialisms_it_uses(reference: str) -> None:
    """The same rule, reaching the files the skill loads on demand.

    A reference is read by whoever followed the link to it, which is the
    definition of a reader landing on one page without having read another.
    "Per kilowatt-hour of IT load" is the one that settles the argument: in
    English prose those two letters are as likely to be read as a pronoun.
    """
    prose = _prose_of((SKILL_DIR / "references" / reference).read_text(encoding="utf-8"))
    exempt = QUOTED_IN_REFERENCES.get(reference, {})
    unexplained = sorted(
        acronym
        for acronym, written in _declared_initialisms().items()
        if acronym not in exempt
        and re.search(rf"(?<![A-Za-z0-9]){acronym}(?![A-Za-z0-9])", prose)
        and written.lower() not in prose.lower()
    )
    assert not unexplained, (
        f"references/{reference} uses these without writing them out: "
        f"{unexplained}. If one is inside a question a user asks or a platform's "
        f"name, declare it in QUOTED_IN_REFERENCES with the reason."
    )


def test_every_reference_exemption_is_still_needed() -> None:
    """An exemption for a file that no longer uses the word is dead weight."""
    idle: list[str] = []
    for reference, acronyms in QUOTED_IN_REFERENCES.items():
        text = (SKILL_DIR / "references" / reference).read_text(encoding="utf-8")
        idle += [
            f"{reference}:{acronym}"
            for acronym in acronyms
            if not re.search(rf"(?<![A-Za-z0-9]){acronym}(?![A-Za-z0-9])", text)
        ]
    assert not idle, f"QUOTED_IN_REFERENCES names what is no longer used: {sorted(idle)}"


def test_the_skill_writes_out_the_initialisms_it_uses() -> None:
    """The rule every page here obeys, reaching the skill's body as well.

    Thirty documentation pages are held to "nowhere an acronym that is not
    spelled out before it is used", and the skill -- which is prose a reader
    and an agent both read -- was held to nothing. It used eleven and expanded
    none.

    The frontmatter is deliberately not checked. Its description is matched
    against what a user asks for, so the acronyms in it are search terms
    rather than prose, and expanding them would make the skill harder to find
    while making nothing clearer.
    """
    body = SKILL.read_text(encoding="utf-8").split("---", 2)[2]
    prose = re.sub(r"```.*?```", " ", body, flags=re.S)
    prose = re.sub(r"`[^`]*`", " ", prose)

    glossary = ROOT / "GLOSSARY.md"
    declared: dict[str, str] = {}
    for line in glossary.read_text(encoding="utf-8").splitlines():
        found = re.match(r"\|\s*\*\*([A-Z][A-Z0-9]*)\*\*\s*\|\s*([^|]*?)\s*\|", line)
        if found and found.group(2) not in {"", "—"}:
            declared[found.group(1)] = found.group(2)

    unexplained = sorted(
        acronym
        for acronym, written in declared.items()
        if acronym not in QUOTED_BY_A_USER
        and re.search(rf"(?<![A-Za-z0-9]){acronym}(?![A-Za-z0-9])", prose)
        and written.lower() not in prose.lower()
    )
    assert not unexplained, (
        f"SKILL.md uses these without writing them out: {unexplained}. The "
        f"written-out form is in {glossary.name}. If one is inside a phrase a "
        f"user types, declare it in QUOTED_BY_A_USER with the reason."
    )


def test_every_exemption_is_still_quoted_in_the_skill() -> None:
    """An exemption nobody needs is one that stops being read."""
    body = SKILL.read_text(encoding="utf-8").split("---", 2)[2]
    idle = sorted(
        acronym
        for acronym in QUOTED_BY_A_USER
        if not re.search(rf"(?<![A-Za-z0-9]){acronym}(?![A-Za-z0-9])", body)
    )
    assert not idle, f"QUOTED_BY_A_USER names acronyms the skill no longer uses: {idle}"


def test_every_command_the_skill_shows_parses() -> None:
    import shlex

    from saggio.cli.app import build_parser

    parser = build_parser()
    text = SKILL.read_text(encoding="utf-8").replace("\\\n", " ")
    # Fenced blocks only. A command shown to a reader is in a fence -- all
    # eight here are -- and reading prose for commands means any rewrap can
    # invent one by landing the word "saggio" at the start of a line, which is
    # exactly how this check's twin in test_documentation.py came to fail on a
    # French sentence.
    fenced = False
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            fenced = not fenced
            continue
        if not fenced:
            continue
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
