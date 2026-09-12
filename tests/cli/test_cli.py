"""The command line: exit codes, output streams, and what it refuses."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import yaml

from running_code_cost_helper.cli import DECLINED, INVALID, OK, UNAVAILABLE, USAGE, main


def run(argv: list[str], capsys) -> tuple[int, str, str]:
    code = main(argv)
    captured = capsys.readouterr()
    return code, captured.out, captured.err


# --- The parser --------------------------------------------------------------


def test_no_verb_prints_help_and_says_it_was_a_usage_problem(capsys) -> None:
    code, out, _ = run([], capsys)
    assert code == USAGE
    assert "usage:" in out


def test_the_help_lists_the_exit_codes(capsys) -> None:
    _, out, _ = run([], capsys)
    assert "Exit codes:" in out


def test_the_version_is_the_packages(capsys) -> None:
    with pytest.raises(SystemExit) as exit_info:
        main(["--version"])
    assert exit_info.value.code == 0


# --- init --------------------------------------------------------------------


def test_init_writes_a_template(tmp_path: Path, capsys) -> None:
    target = tmp_path / "cost.yaml"
    code, _, _ = run(["init", "--template", "annotated", "-o", str(target)], capsys)
    assert code == OK
    assert yaml.safe_load(target.read_text(encoding="utf-8"))["schema_version"] == "2.0"


def test_init_writes_to_standard_output_when_no_file_is_named(capsys) -> None:
    code, out, _ = run(["init"], capsys)
    assert code == OK
    assert "unit_of_work" in out


def test_an_unknown_template_is_rejected_before_anything_is_written(capsys) -> None:
    with pytest.raises(SystemExit):
        main(["init", "--template", "fancy"])


# --- validate ----------------------------------------------------------------


def test_validate_passes_a_sound_model(tmp_path: Path, sound_model: dict[str, Any], capsys) -> None:
    target = tmp_path / "cost.yaml"
    target.write_text(yaml.safe_dump(sound_model), encoding="utf-8")
    code, out, _ = run(["validate", str(target)], capsys)
    assert code == OK
    assert "0 errors" in out


def test_validate_fails_a_model_that_breaks_a_rule(
    tmp_path: Path, sound_model: dict[str, Any], capsys
) -> None:
    sound_model["scenarios"][0]["costs"]["energy"]["status"] = "measured"
    target = tmp_path / "cost.yaml"
    target.write_text(yaml.safe_dump(sound_model), encoding="utf-8")
    code, out, _ = run(["validate", str(target)], capsys)
    assert code == INVALID
    assert "cannot outrank" in out


def test_validate_emits_json_on_request(
    tmp_path: Path, sound_model: dict[str, Any], capsys
) -> None:
    target = tmp_path / "cost.yaml"
    target.write_text(yaml.safe_dump(sound_model), encoding="utf-8")
    code, out, _ = run(["validate", str(target), "--json"], capsys)
    payload = json.loads(out)
    assert code == OK
    assert payload["ok"] is True
    assert payload["overall_status"] == "estimated"


def test_validating_a_file_that_is_not_there_is_a_usage_problem(tmp_path: Path, capsys) -> None:
    code, _, _ = run(["validate", str(tmp_path / "nope.yaml")], capsys)
    assert code == USAGE


def test_a_model_with_warnings_still_passes(
    tmp_path: Path, sound_model: dict[str, Any], capsys
) -> None:
    # An honest model that admits it is incomplete must not be punished for it.
    del sound_model["assumptions"]["power_draw"]["source_url"]
    target = tmp_path / "cost.yaml"
    target.write_text(yaml.safe_dump(sound_model), encoding="utf-8")
    code, out, _ = run(["validate", str(target)], capsys)
    assert code == OK
    assert "1 warning" in out


# --- render ------------------------------------------------------------------


@pytest.mark.parametrize(("fmt", "marker"), [("md", "# Cost of running"), ("html", "<!doctype")])
def test_render_writes_the_format_asked_for(
    tmp_path: Path, sound_model: dict[str, Any], fmt: str, marker: str, capsys
) -> None:
    source = tmp_path / "cost.yaml"
    source.write_text(yaml.safe_dump(sound_model), encoding="utf-8")
    out_file = tmp_path / f"report.{fmt}"
    code, _, _ = run(["render", str(source), "-f", fmt, "-o", str(out_file)], capsys)
    assert code == OK
    assert out_file.read_text(encoding="utf-8").startswith(marker)


def test_render_goes_to_standard_output_by_default(
    tmp_path: Path, sound_model: dict[str, Any], capsys
) -> None:
    source = tmp_path / "cost.yaml"
    source.write_text(yaml.safe_dump(sound_model), encoding="utf-8")
    code, out, _ = run(["render", str(source)], capsys)
    assert code == OK
    assert out.startswith("# Cost of running")


def test_a_binary_format_needs_a_destination(
    tmp_path: Path, sound_model: dict[str, Any], capsys
) -> None:
    source = tmp_path / "cost.yaml"
    source.write_text(yaml.safe_dump(sound_model), encoding="utf-8")
    code, _, _ = run(["render", str(source), "-f", "docx"], capsys)
    assert code == USAGE


def test_a_missing_toolchain_is_reported_as_unavailable_not_as_a_crash(
    tmp_path: Path, sound_model: dict[str, Any], monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    monkeypatch.setattr("running_code_cost_helper.report.office.md2star_available", lambda: False)
    source = tmp_path / "cost.yaml"
    source.write_text(yaml.safe_dump(sound_model), encoding="utf-8")
    code, _, _ = run(["render", str(source), "-f", "docx", "-o", str(tmp_path / "r.docx")], capsys)
    assert code == UNAVAILABLE


# --- diff --------------------------------------------------------------------


def test_diff_passes_when_nothing_moved(
    tmp_path: Path, sound_model: dict[str, Any], capsys
) -> None:
    for name in ("before.yaml", "after.yaml"):
        (tmp_path / name).write_text(yaml.safe_dump(sound_model), encoding="utf-8")
    code, out, _ = run(
        ["diff", str(tmp_path / "before.yaml"), str(tmp_path / "after.yaml")], capsys
    )
    assert code == OK
    assert "Nothing changed" in out


def test_diff_fails_on_drift(tmp_path: Path, sound_model: dict[str, Any], capsys) -> None:
    (tmp_path / "before.yaml").write_text(yaml.safe_dump(sound_model), encoding="utf-8")
    sound_model["scenarios"][0]["costs"]["energy"]["value"] = 1.0
    (tmp_path / "after.yaml").write_text(yaml.safe_dump(sound_model), encoding="utf-8")
    code, out, _ = run(
        ["diff", str(tmp_path / "before.yaml"), str(tmp_path / "after.yaml")], capsys
    )
    assert code == INVALID
    assert "energy" in out


# --- audit -------------------------------------------------------------------


def test_audit_writes_a_model_and_its_notes_to_different_streams(
    training_repository: Path, tmp_path: Path, capsys
) -> None:
    # Redirecting the model to a file must still show the reader what the audit
    # could not establish, so the notes go to standard error.
    target = tmp_path / "audited.yaml"
    code, _, err = run(
        ["audit", str(training_repository), "--no-llm", "--country", "FR", "-o", str(target)],
        capsys,
    )
    assert code == OK
    assert yaml.safe_load(target.read_text(encoding="utf-8"))["schema_version"] == "2.0"
    assert err == "" or "Read before trusting" in err


def test_audit_emits_json_on_request(training_repository: Path, capsys) -> None:
    code, out, _ = run(["audit", str(training_repository), "--no-llm", "--json"], capsys)
    payload = json.loads(out)
    assert code == OK
    assert payload["model"]["schema_version"] == "2.0"
    assert "validation" in payload


def test_auditing_something_that_is_not_a_directory_is_a_usage_problem(
    tmp_path: Path, capsys
) -> None:
    code, _, _ = run(["audit", str(tmp_path / "nope"), "--no-llm"], capsys)
    assert code == USAGE


# --- measure -----------------------------------------------------------------


def test_measure_needs_a_command(capsys) -> None:
    code, _, _ = run(["measure"], capsys)
    assert code == USAGE


def test_measure_runs_a_command_and_reports_it(python_command: list[str], capsys) -> None:
    code, out, _ = run(["measure", "--", *python_command], capsys)
    assert code == OK
    assert "Exit code: 0" in out


def test_measure_strips_the_argparse_separator(python_command: list[str], capsys) -> None:
    # argparse.REMAINDER hands back the "--" along with the command, and running
    # it would look for a program literally called "--".
    code, out, _ = run(["measure", "--json", "--", *python_command], capsys)
    payload = json.loads(out)
    assert code == OK
    assert payload["command"][0] != "--"


def test_a_command_that_fails_is_reported_faithfully(capsys) -> None:
    import sys

    code, out, _ = run(["measure", "--", sys.executable, "-c", "raise SystemExit(7)"], capsys)
    assert code == OK  # the measurement succeeded; it measured a failure
    assert "Exit code: 7" in out


# --- catalog -----------------------------------------------------------------


def test_catalog_list_prints_rows(capsys) -> None:
    code, out, _ = run(["catalog", "list", "gpu"], capsys)
    assert code == OK
    assert "A100" in out


def test_catalog_list_emits_json_on_request(capsys) -> None:
    code, out, _ = run(["catalog", "list", "country", "--json"], capsys)
    assert code == OK
    assert json.loads(out)["FR"]["name"] == "France"


def test_adding_a_row_without_provenance_is_impossible(capsys) -> None:
    with pytest.raises(SystemExit):
        main(["catalog", "add", "gpu", "X"])


def test_a_malformed_field_is_a_usage_problem(capsys) -> None:
    code, _, _ = run(
        [
            "catalog",
            "add",
            "gpu",
            "X",
            "--source-url",
            "https://example.invalid",
            "--retrieved-date",
            "2026-09-12",
            "--field",
            "nonsense",
        ],
        capsys,
    )
    assert code == USAGE


def test_catalog_without_an_action_shows_its_help(capsys) -> None:
    with pytest.raises(SystemExit):
        main(["catalog"])


def test_freshness_is_a_gate(capsys) -> None:
    code, _, _ = run(["catalog", "freshness"], capsys)
    assert code in {OK, INVALID}


# --- machine and consent -----------------------------------------------------


def test_machine_describes_this_one(capsys) -> None:
    code, out, _ = run(["machine"], capsys)
    assert code == OK
    assert "catalogue key" in out


def test_machine_emits_json_on_request(capsys) -> None:
    code, out, _ = run(["machine", "--json"], capsys)
    assert code == OK
    assert json.loads(out)["platform"]


def test_consent_records_a_decision_where_it_is_told_to(tmp_path: Path, capsys) -> None:
    target = tmp_path / "decision.json"
    assert run(["consent", "grant", "--path", str(target)], capsys)[0] == OK
    assert json.loads(target.read_text(encoding="utf-8"))["granted"] is True
    assert run(["consent", "revoke", "--path", str(target)], capsys)[0] == DECLINED
    assert json.loads(target.read_text(encoding="utf-8"))["granted"] is False
