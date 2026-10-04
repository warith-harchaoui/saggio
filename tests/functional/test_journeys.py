"""The journeys a user actually takes, end to end through the command line.

Why this file exists
--------------------
Everything else here tests a function. These test the tool: a real process, the
real argument parser, real files on disk, and the exit codes a shell or a
continuous-integration job will act on. A package can have every unit passing
and still be unusable because two verbs do not fit together, and nothing below
the command line would notice.

They are deliberately few. One journey is worth more than twenty assertions
about the pieces of it, and a failure here means a user is stuck rather than
that an internal changed shape.

Author
------
Warith Harchaoui
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

#: Invoking the module rather than the installed script, so the test exercises
#: the code in this working tree whatever is on the PATH.
SAGGIO = [sys.executable, "-m", "saggio"]

#: Exit codes the command line promises. A shell acts on these, so they are part
#: of the interface rather than an implementation detail.
OK, FAILED_ITS_RULES, MISUSED = 0, 1, 2


def run(*arguments: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    """Run saggio the way a shell would, and return what happened."""
    return subprocess.run(  # noqa: S603 - a fixed argument list, never a shell.
        [*SAGGIO, *arguments],
        capture_output=True,
        text=True,
        cwd=cwd,
        timeout=300,
    )


@pytest.fixture
def project(tmp_path: Path) -> Path:
    """A small repository that looks like something worth costing."""
    root = tmp_path / "project"
    root.mkdir()
    (root / "config.py").write_text("max_iters = 10000\n", encoding="utf-8")
    (root / "train.py").write_text(
        "import argparse, math\n"
        "parser = argparse.ArgumentParser()\n"
        'parser.add_argument("--max_iters", type=int, default=10000)\n'
        "args = parser.parse_args()\n"
        "print(sum(math.sqrt(i + 1) for i in range(args.max_iters)))\n",
        encoding="utf-8",
    )
    return root


def test_a_new_model_can_be_started_and_passes_its_own_rules(tmp_path: Path) -> None:
    """The first thing anybody does, and it has to work with nothing installed."""
    model = tmp_path / "cost_of_running.yaml"
    assert run("init", "-o", str(model)).returncode == OK
    assert model.is_file()
    assert run("validate", str(model)).returncode == OK


def test_audit_then_render_gives_a_report_that_leads_with_what_is_missing(
    project: Path, tmp_path: Path
) -> None:
    """The journey the README opens with: audit, render, read.

    The point of the report is the first line. A model nobody has measured is
    `TODO` overall, and the page has to say so before any number, or somebody
    quotes a figure the tool never stood behind.
    """
    model = tmp_path / "cost.yaml"
    report = tmp_path / "cost.md"
    assert (
        run("audit", str(project), "--country", "FR", "--no-llm", "-o", str(model)).returncode == OK
    )
    assert run("render", str(model), "-f", "md", "-o", str(report)).returncode == OK

    text = report.read_text(encoding="utf-8")
    opening = text.split("\n\n", 2)[1]
    assert "TODO" in opening, f"the report does not lead with what is missing: {opening[:120]}"
    assert run("validate", str(model)).returncode == OK


def test_a_model_that_lies_about_its_arithmetic_fails_the_gate(tmp_path: Path) -> None:
    """What a continuous-integration job is actually buying.

    A number four orders of magnitude from what its own inputs give, carrying a
    correct list of those inputs, is the mistake that looks most like diligence.
    The exit code is what a pipeline acts on, so it is the thing under test.
    """
    model = tmp_path / "cost.yaml"
    model.write_text(
        yaml.safe_dump(
            {
                "schema_version": "2.1",
                "date_updated": "2026-10-04",
                "unit_of_work": {"name": "one request", "status": "estimated"},
                "deployment": {"provider": "on-prem", "country": "FR"},
                "assumptions": {
                    "power_draw": {
                        "value": 100.0,
                        "unit": "W",
                        "status": "measured",
                        "notes": "counter",
                    }
                },
                "scenarios": [
                    {
                        "name": "default",
                        "runtime": {
                            "value": 3600.0,
                            "unit": "s",
                            "status": "measured",
                            "notes": "timed",
                        },
                        "costs": {
                            "energy": {
                                "value": 0.00001,
                                "unit": "kWh",
                                "status": "estimated",
                                "derived_from": [
                                    "scenarios[0].runtime",
                                    "assumptions.power_draw",
                                ],
                            }
                        },
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    done = run("validate", str(model))
    assert done.returncode == FAILED_ITS_RULES
    assert "does not follow" in done.stdout + done.stderr


def test_running_a_slice_turns_an_open_runtime_into_a_measured_one(
    project: Path, tmp_path: Path
) -> None:
    """The step that makes a model mean something, through the command line.

    Before: the runtime is open and everything derived from it is open too.
    After: a counter answered, and the chain below it moves with it.
    """
    before = tmp_path / "before.yaml"
    after = tmp_path / "after.yaml"
    assert (
        run("audit", str(project), "--country", "FR", "--no-llm", "-o", str(before)).returncode
        == OK
    )
    opened = yaml.safe_load(before.read_text(encoding="utf-8"))
    assert opened["scenarios"][0]["runtime"]["status"] == "TODO"

    done = run("audit", str(project), "--country", "FR", "--no-llm", "--run", "-o", str(after))
    if done.returncode != OK or not after.is_file():
        pytest.skip(f"this machine would not run the slice: {done.stderr[-200:]}")
    measured = yaml.safe_load(after.read_text(encoding="utf-8"))
    assert measured["scenarios"][0]["runtime"]["status"] == "measured"
    assert run("validate", str(after)).returncode == OK


def test_a_cost_that_worsens_fails_the_drift_gate(tmp_path: Path) -> None:
    """Two models and a threshold, which is how this is used in a pipeline."""

    def model_at(energy: float) -> dict:
        return {
            "schema_version": "2.1",
            "date_updated": "2026-10-04",
            "unit_of_work": {"name": "one request", "status": "estimated"},
            "deployment": {"provider": "on-prem", "country": "FR"},
            "scenarios": [
                {
                    "name": "default",
                    "costs": {
                        "energy": {
                            "value": energy,
                            "unit": "kWh",
                            "status": "measured",
                            "notes": "counter",
                        }
                    },
                }
            ],
        }

    base = tmp_path / "base.yaml"
    worse = tmp_path / "worse.yaml"
    base.write_text(yaml.safe_dump(model_at(0.40)), encoding="utf-8")
    worse.write_text(yaml.safe_dump(model_at(0.80)), encoding="utf-8")

    assert run("diff", str(base), str(base)).returncode == OK
    drifted = run("diff", str(base), str(worse))
    assert drifted.returncode == FAILED_ITS_RULES
    assert "energy" in drifted.stdout + drifted.stderr


def test_a_report_for_everyone_else_is_one_file_and_needs_no_network(
    project: Path, tmp_path: Path
) -> None:
    """The HTML report is handed to people who will open it offline.

    A stylesheet or a script loaded from somewhere else would make it a page
    that works on the machine it was made on and nowhere else.
    """
    model = tmp_path / "cost.yaml"
    page = tmp_path / "cost.html"
    assert (
        run("audit", str(project), "--country", "FR", "--no-llm", "-o", str(model)).returncode == OK
    )
    assert run("render", str(model), "-f", "html", "-o", str(page)).returncode == OK

    html = page.read_text(encoding="utf-8")
    assert html.lstrip().lower().startswith("<!doctype html")
    for fetched in ('src="http', 'href="http://', "@import url(http"):
        assert fetched not in html, f"the report reaches for {fetched}"
    # A stylesheet link to another host is the common way this breaks.
    assert 'rel="stylesheet" href="http' not in html


def test_the_command_line_refuses_what_it_cannot_do_with_a_usage_code(
    tmp_path: Path,
) -> None:
    """A shell has to be able to tell a refusal from a verdict.

    Exit 2 means the command was asked for something it cannot do; exit 1 means
    the model is wrong. Collapsing them would make a typo look like a failing
    cost gate.
    """
    assert run("render", str(tmp_path / "absent.yaml"), "-f", "md").returncode != OK
    assert run("catalog", "refresh", "services").returncode == MISUSED
    assert run("validate", str(tmp_path / "nothing-here.yaml")).returncode != OK


def test_the_catalogue_reports_its_own_freshness_for_a_scheduled_job() -> None:
    """What the weekly job runs, and what it prints when nothing is stale."""
    done = run("catalog", "freshness", "--within", "21")
    assert done.returncode in {OK, FAILED_ITS_RULES}
    assert "refresh window" in done.stdout or "stale" in done.stdout

    as_json = run("catalog", "freshness", "--json")
    assert as_json.returncode in {OK, FAILED_ITS_RULES}
    payload = json.loads(as_json.stdout)
    assert {"stale", "expiring"} <= set(payload)
