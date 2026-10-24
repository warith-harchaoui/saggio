"""The command line: exit codes, output streams, and what it refuses."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pytest
import yaml

from saggio.cli import DECLINED, INVALID, OK, UNAVAILABLE, USAGE, main
from saggio.model import SCHEMA_VERSION


def run(argv: list[str], capsys) -> tuple[int, str, str]:
    code = main(argv)
    captured = capsys.readouterr()
    return code, captured.out, captured.err


# --- Streams that cannot carry the typography ---------------------------------


@pytest.mark.parametrize("encoding", ["ascii", "latin-1"])
@pytest.mark.parametrize("language", ["fr", "en"])
def test_a_stream_that_cannot_encode_the_prose_still_gets_the_report(
    encoding: str, language: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A narrow output encoding must cost a character, never the command.

    The prose uses the em dash in both languages and accents plus the ``oe``
    ligature in French. On a stream that cannot encode them -- a container with
    no language set, a wrapper exporting ``PYTHONIOENCODING=ascii`` -- the write
    raised `UnicodeEncodeError` and the command printed nothing at all.
    """
    import io

    raw = io.BytesIO()
    monkeypatch.setattr(sys, "stdout", io.TextIOWrapper(raw, encoding=encoding, errors="strict"))
    code = main(["--language", language, "machine"])
    sys.stdout.flush()
    assert code == OK
    assert raw.getvalue(), "the report did not arrive"
    # Decodable as what the stream claimed to be, which is the point: the
    # declared encoding is honoured rather than quietly replaced by UTF-8.
    raw.getvalue().decode(encoding)


def test_what_a_narrow_stream_loses_is_named_rather_than_dropped(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An unencodable character arrives as the escape naming it, not as `?`.

    `?` would lose which character it stood for; the escape stays reversible,
    so a French report read off an ASCII pipe is still unambiguous.
    """
    import io

    raw = io.BytesIO()
    monkeypatch.setattr(sys, "stdout", io.TextIOWrapper(raw, encoding="ascii", errors="strict"))
    assert main(["--language", "fr", "machine"]) == OK
    sys.stdout.flush()
    written = raw.getvalue().decode("ascii")
    # "Memoire" carries an acute accent in the French output.
    assert "\\xe9" in written
    assert "?" not in written


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
    assert yaml.safe_load(target.read_text(encoding="utf-8"))["schema_version"] == SCHEMA_VERSION


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
    monkeypatch.setattr("saggio.report.office.md2star_available", lambda: False)
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
    assert yaml.safe_load(target.read_text(encoding="utf-8"))["schema_version"] == SCHEMA_VERSION
    assert err == "" or "Read before trusting" in err


def test_audit_emits_json_on_request(training_repository: Path, capsys) -> None:
    code, out, _ = run(["audit", str(training_repository), "--no-llm", "--json"], capsys)
    payload = json.loads(out)
    assert code == OK
    assert payload["model"]["schema_version"] == SCHEMA_VERSION
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


def test_a_row_whose_value_is_a_sentence_is_not_joined_by_commas(capsys) -> None:
    """The separator must not be a character the values contain.

    `embodied_scope` is prose: "One AMD EPYC 7742 package, cradle-to-gate,
    computed from its die of 1600 mm2 by https://... Excludes the use phase
    and, per the source, end of life." Joining the fields of that row with
    ", " made a 391-character line in which a reader could not tell a field
    boundary from a comma inside the sentence.

    A row that does not fit goes one field to a line, where the separator is
    the line break and nothing in a value can be mistaken for it.
    """
    code, out, _ = run(["catalog", "list", "cpu"], capsys)
    assert code == OK

    lines = out.split("\n")
    scope = [line for line in lines if "embodied_scope=" in line]
    assert scope, "no row in this catalogue carries a prose field any more"
    for line in scope:
        assert ", embodied_source_url=" not in line, (
            "a field that is a sentence is still being comma-joined to the "
            "next field, so the two cannot be told apart"
        )


def test_no_catalogue_line_breaks_a_url(capsys) -> None:
    """A URL is printed to be copied, and half of one cannot be.

    Wrapping is allowed to run a line past the margin rather than split a
    single long token, which is the whole reason a source URL is in the
    listing.
    """
    from saggio.catalog import Catalog

    code, out, _ = run(["catalog", "list", "gpu"], capsys)
    assert code == OK

    # Against the catalogue rather than against the output's own shape. The
    # first version of this searched the printed text for `https?://\S+` and
    # asserted the match held no newline -- which `\S` cannot match, so the
    # assertion could not fail and a split URL sailed through it.
    lines = out.split("\n")
    # Only the fields the listing prints. `source_url` and `retrieved_date`
    # are held back from it on purpose, and asserting one of those appears is
    # how the first version of this failed -- against the product, over a URL
    # the product never claimed to show.
    withheld = {"key", "source_url", "retrieved_date", "notes", "detect"}
    urls = {
        str(value)
        for row in Catalog.load("hardware").rows("gpus").values()
        for field, value in row.items()
        if field not in withheld and str(value).startswith("http")
    }
    assert urls, "no GPU row carries a source URL any more"
    for url in urls:
        assert any(url in line for line in lines), (
            f"{url} is in the catalogue and on no single line of the listing, "
            "so wrapping has split it and a reader cannot copy it"
        )


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


def test_catalog_without_an_action_is_a_usage_error_not_a_success(capsys) -> None:
    # The old behavior raised SystemExit(0) via argparse's help action, so a CI
    # script checking the exit code saw success for a usage error.
    assert main(["catalog"]) == 2


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


def test_granting_shows_the_terms_before_recording_them(tmp_path: Path, capsys) -> None:
    # The defect: this verb wrote `granted: true` without ever displaying what
    # was being agreed to, and the cookbook recommends it as the first step of
    # measuring somebody else's repository. The confirmation was an info log,
    # invisible at the default verbosity, so the whole command printed nothing.
    target = tmp_path / "decision.json"
    code, out, _ = run(["consent", "grant", "--path", str(target)], capsys)
    assert code == OK
    assert "no sandbox" in out.lower(), "the terms were not shown"
    assert "permissions" in out
    assert str(target) in out, "nobody was told where the decision went"


def test_granting_shows_the_terms_in_the_language_asked_for(tmp_path: Path, capsys) -> None:
    target = tmp_path / "decision.json"
    code, out, _ = run(["consent", "grant", "--path", str(target), "--language", "fr"], capsys)
    assert code == OK
    assert "bac à sable" in out
    assert json.loads(target.read_text(encoding="utf-8"))["language"] == "fr"


def test_revoking_says_where_the_decision_went_without_restating_the_terms(
    tmp_path: Path, capsys
) -> None:
    # Nobody needs to read the terms to say no to them, and deleting the record
    # is how consent is revoked, so the path is the one thing that must appear.
    target = tmp_path / "decision.json"
    code, out, _ = run(["consent", "revoke", "--path", str(target)], capsys)
    assert code == DECLINED
    assert str(target) in out
    assert "no sandbox" not in out.lower()


# --- measure --into ----------------------------------------------------------


def test_measuring_into_a_model_that_is_not_there_says_so(tmp_path: Path) -> None:
    code = main(
        ["measure", "--no-profile", "--into", str(tmp_path / "nope.yaml"), "--", "python", "-c", ""]
    )
    assert code != 0


def test_a_failed_command_is_not_folded_into_a_model(tmp_path: Path) -> None:
    # A command that exited non-zero measured a failure, and a failure has no
    # cost per unit of work because it produced no units.
    model = tmp_path / "cost.yaml"
    main(["init", "-o", str(model), "--template", "annotated"])
    before = model.read_text(encoding="utf-8")
    code = main(
        [
            "measure",
            "--no-profile",
            "--into",
            str(model),
            "--",
            sys.executable,
            "-c",
            "raise SystemExit(3)",
        ]
    )
    assert code != 0
    assert model.read_text(encoding="utf-8") == before
