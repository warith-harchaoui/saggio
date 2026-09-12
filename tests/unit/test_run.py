"""Consent, and running a bounded slice of somebody else's code."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from running_code_cost_helper.analyze.run import (
    CONSENT_WORD,
    _can_profile,
    _is_python_command,
    _read_profile,
    consent_path,
    has_consent,
    record_consent,
    require_consent,
    run_slice,
)

# --- Consent -----------------------------------------------------------------


def test_nothing_recorded_means_no_consent(consent_file: Path) -> None:
    assert not has_consent(consent_file)


def test_a_decision_is_recorded_and_read_back(consent_file: Path) -> None:
    record_consent(True, consent_file)
    assert has_consent(consent_file)
    record_consent(False, consent_file)
    assert not has_consent(consent_file)


def test_an_unreadable_record_counts_as_no(consent_file: Path) -> None:
    # Consent has to be positively established, never inferred from a file nobody
    # could parse.
    consent_path(consent_file).write_text("{not json", encoding="utf-8")
    assert not has_consent(consent_file)


def test_only_the_exact_word_grants_it(consent_file: Path, capsys) -> None:
    assert not require_consent(lambda _: "y", path=consent_file, interactive=True)
    assert not require_consent(lambda _: "sure", path=consent_file, interactive=True)
    assert require_consent(lambda _: CONSENT_WORD, path=consent_file, interactive=True)


def test_it_is_asked_once_and_remembered(consent_file: Path, capsys) -> None:
    require_consent(lambda _: CONSENT_WORD, path=consent_file, interactive=True)

    def refuse_to_be_asked(_: str) -> str:
        raise AssertionError("consent was asked for a second time")

    assert require_consent(refuse_to_be_asked, path=consent_file, interactive=True)


def test_with_no_terminal_it_is_refused_rather_than_defaulted(consent_file: Path) -> None:
    # A build server must never be able to agree on a person's behalf.
    assert not require_consent(path=consent_file, interactive=False)
    assert not consent_path(consent_file).exists()


def test_the_prompt_says_what_is_being_agreed_to(consent_file: Path, capsys) -> None:
    require_consent(lambda _: "no", path=consent_file, interactive=True)
    shown = capsys.readouterr().out
    assert "no sandbox" in shown.lower()
    assert "permissions" in shown


# --- What can be profiled ----------------------------------------------------


def test_an_interpreter_is_recognised() -> None:
    assert _is_python_command([sys.executable, "-c", "pass"])
    assert not _is_python_command(["make", "test"])
    assert not _is_python_command([])


@pytest.mark.parametrize(
    ("command", "expected"),
    [
        ([sys.executable, "-m", "pytest", "-q"], True),
        ([sys.executable, "train.py"], True),
        ([sys.executable, "-c", "print(1)"], False),
        ([sys.executable, "-"], False),
        ([sys.executable, "-m"], False),
        ([sys.executable], False),
        (["make", "test"], False),
    ],
)
def test_the_profiler_only_wraps_what_it_can(command: list[str], expected: bool) -> None:
    # cProfile has no -c, so wrapping `python -c "..."` turns a working command
    # into a usage error from a tool the user never asked for.
    assert _can_profile(command) is expected


def test_an_absent_profile_file_yields_nothing() -> None:
    assert _read_profile(Path("/nonexistent.prof")) == ()


def test_an_empty_profile_file_yields_nothing(tmp_path: Path) -> None:
    # The normal outcome when the child crashed before the profiler could flush.
    empty = tmp_path / "empty.prof"
    empty.write_bytes(b"")
    assert _read_profile(empty) == ()


def test_a_corrupt_profile_file_yields_nothing(tmp_path: Path) -> None:
    corrupt = tmp_path / "corrupt.prof"
    corrupt.write_bytes(b"not a marshalled profile")
    assert _read_profile(corrupt) == ()


# --- Running -----------------------------------------------------------------


def test_a_clean_run_reports_a_clean_run(python_command: list[str]) -> None:
    result = run_slice(python_command, profile=False)
    assert result.exit_code == 0
    assert result.succeeded()
    assert result.wall_seconds >= 0.0


def test_a_failing_run_is_reported_faithfully() -> None:
    result = run_slice([sys.executable, "-c", "raise SystemExit(3)"], profile=False)
    assert result.exit_code == 3
    assert not result.succeeded()
    assert any("exited 3" in warning for warning in result.warnings)


def test_a_failing_run_licenses_no_projection() -> None:
    result = run_slice(
        [sys.executable, "-c", "raise SystemExit(1)"], fraction_completed=0.01, profile=False
    )
    assert result.fraction_completed is None
    assert not result.may_project()


def test_a_failing_capped_run_explains_why_nothing_was_projected() -> None:
    # This used to happen in silence: the entry point did not accept the flag, the
    # run failed, and the model simply had no projection with no hint as to why.
    result = run_slice(
        [sys.executable, "-c", "raise SystemExit(2)"], fraction_completed=0.01, profile=False
    )
    assert any("entry point" in warning for warning in result.warnings)


def test_a_run_that_hits_the_limit_is_marked_truncated() -> None:
    result = run_slice(
        [sys.executable, "-c", "import time; time.sleep(30)"], timeout_seconds=0.6, profile=False
    )
    assert result.truncated
    assert not result.succeeded()
    assert any("limit" in warning for warning in result.warnings)


def test_a_truncated_run_licenses_no_projection() -> None:
    result = run_slice(
        [sys.executable, "-c", "import time; time.sleep(30)"],
        timeout_seconds=0.6,
        fraction_completed=0.5,
        profile=False,
    )
    assert result.fraction_completed is None


def test_a_clean_capped_run_may_be_projected(python_command: list[str]) -> None:
    result = run_slice(python_command, fraction_completed=0.01, profile=False)
    assert result.may_project()


def test_a_script_is_profiled(tmp_path: Path) -> None:
    script = tmp_path / "work.py"
    script.write_text("total = sum(i * i for i in range(200000))\n", encoding="utf-8")
    result = run_slice([sys.executable, str(script)], profile=True)
    assert result.exit_code == 0
    assert result.hot_path
    assert result.hot_path[0].cumulative_seconds >= 0.0


def test_a_command_that_cannot_be_profiled_says_so(python_command: list[str]) -> None:
    result = run_slice(python_command, profile=True)
    assert any("profile" in warning for warning in result.warnings)


def test_the_working_directory_is_honoured(tmp_path: Path) -> None:
    script = tmp_path / "where.py"
    script.write_text("import pathlib, sys\nsys.exit(0)\n", encoding="utf-8")
    assert run_slice([sys.executable, str(script)], working_directory=tmp_path).exit_code == 0


def test_a_command_whose_program_does_not_exist_raises() -> None:
    with pytest.raises(FileNotFoundError):
        run_slice(["definitely-not-a-real-program-xyz"], profile=False)


def test_the_result_serialises_what_a_reader_needs(python_command: list[str]) -> None:
    mapping = run_slice(python_command, profile=False).to_mapping()
    assert mapping["exit_code"] == 0
    assert mapping["power_scope"]


def test_the_recorded_command_does_not_carry_a_home_directory(
    python_command: list[str],
) -> None:
    # A cost model is committed and shared; spelling out /Users/somebody in it
    # tells every reader of the repository where the author's home is.
    mapping = run_slice(python_command, profile=False).to_mapping()
    assert not any(part.startswith(str(Path.home())) for part in mapping["command"])
