"""Consent, and running a bounded slice of somebody else's code."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from saggio.analyze.power import PowerReading
from saggio.analyze.run import (
    CONSENT_WORD,
    SliceResult,
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


# --- Holes the second audit found, kept closed ----------------------------------


def test_the_timeout_ends_the_whole_process_tree(tmp_path) -> None:
    # A workload that forks workers must not leave them running as the user
    # after the "slice was stopped" warning claims otherwise.
    marker = tmp_path / "grandchild-was-here"
    script = tmp_path / "spawner.py"
    script.write_text(
        "import subprocess, sys, time\n"
        "subprocess.Popen([sys.executable, '-c',\n"
        "                  'import sys, time; time.sleep(3); "
        'open(sys.argv[1], "w").write("x")\',\n'
        "                  sys.argv[1]])\n"
        "time.sleep(60)\n",
        encoding="utf-8",
    )
    import time

    result = run_slice(
        [sys.executable, str(script), str(marker)], timeout_seconds=1.0, profile=False
    )
    assert result.truncated
    time.sleep(3.5)
    assert not marker.exists()


def test_child_processor_time_is_recorded_where_the_platform_reports_it() -> None:
    result = run_slice([sys.executable, "-c", "sum(range(2_000_000))"], profile=False)
    if result.cpu_seconds is not None:
        assert result.cpu_seconds >= 0.0
        assert "cpu_seconds" in result.to_mapping()


# --- The floor a measurement is read against ---------------------------------
#
# A counter measures the machine, not the program. On a laptop with a browser
# open, most of what it reports was never the slice's, and a tool that quoted
# the total as the slice's cost would be wrong by whatever else happened to be
# running. So the machine is watched before the slice starts, and the difference
# is what the slice added — with every way that subtraction can go wrong named.


def _result(total: float | None, idle: float | None, **extra: object) -> SliceResult:
    """A finished slice with the two power figures set, and nothing else real."""
    return SliceResult(
        command=("x",),
        exit_code=0,
        wall_seconds=1.0,
        power=PowerReading(total, total, "during the run"),
        baseline=None if idle is None else PowerReading(idle, idle, "before it"),
        **extra,  # type: ignore[arg-type]
    )


def test_the_slices_own_draw_is_the_difference() -> None:
    assert _result(120.0, 20.0).marginal_watts() == pytest.approx(100.0)


def test_a_machine_that_grew_quieter_yields_no_marginal_figure() -> None:
    # Whatever else was busy stopped. Subtracting that would credit the slice
    # for somebody else's work ending.
    assert _result(20.0, 120.0).marginal_watts() is None


def test_without_a_baseline_there_is_no_difference_to_take() -> None:
    assert _result(120.0, None).marginal_watts() is None


def test_without_a_measurement_there_is_no_difference_either() -> None:
    assert _result(None, 20.0).marginal_watts() is None


def test_the_floor_is_recorded_in_the_model_with_its_caveat() -> None:
    mapping = _result(120.0, 20.0).to_mapping()
    assert mapping["idle_watts"] == pytest.approx(20.0)
    assert "100.0 W as the slice's own draw" in mapping["power_note"]
    # The subtraction assumes the rest of the machine kept doing what it did.
    # Nobody checked that, so the assumption travels with the number.
    assert "only if the rest of the machine did the same thing" in mapping["power_note"]


def test_no_baseline_means_no_floor_in_the_model() -> None:
    assert "idle_watts" not in _result(120.0, None).to_mapping()


class _FixedMeter:
    """A meter that reports a wattage decided by the test."""

    watts = 0.0

    @classmethod
    def start(cls) -> _FixedMeter:
        return cls()

    def stop(self, *, seconds: float) -> PowerReading:
        return PowerReading(self.watts, self.watts * seconds, "during the run")


def _with_power(monkeypatch: pytest.MonkeyPatch, *, idle: float, during: float) -> None:
    """Pin both power figures so the arithmetic between them can be tested."""
    monkeypatch.setattr(
        "saggio.analyze.run.measure_for",
        lambda seconds: PowerReading(idle, idle * seconds, "before it"),
    )
    _FixedMeter.watts = during
    monkeypatch.setattr("saggio.analyze.run.PowerMeter", _FixedMeter)


def test_a_busy_machine_is_called_out(monkeypatch: pytest.MonkeyPatch) -> None:
    # Above half, the total has stopped being a figure about the slice and
    # started being a figure about the machine it was measured on.
    _with_power(monkeypatch, idle=60.0, during=100.0)
    result = run_slice([sys.executable, "-c", "pass"], profile=False, baseline_seconds=0.01)
    joined = " ".join(result.warnings)
    assert "already drawing 60.0 W" in joined
    assert "40.0 W, is what the slice added" in joined
    assert result.marginal_watts() == pytest.approx(40.0)


def test_a_quiet_machine_earns_no_warning(monkeypatch: pytest.MonkeyPatch) -> None:
    _with_power(monkeypatch, idle=5.0, during=100.0)
    result = run_slice([sys.executable, "-c", "pass"], profile=False, baseline_seconds=0.01)
    assert not any("already drawing" in warning for warning in result.warnings)
    assert result.marginal_watts() == pytest.approx(95.0)


def test_a_machine_that_went_quiet_says_so_rather_than_subtracting(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _with_power(monkeypatch, idle=120.0, during=20.0)
    result = run_slice([sys.executable, "-c", "pass"], profile=False, baseline_seconds=0.01)
    joined = " ".join(result.warnings)
    assert "grew quieter while the slice ran" in joined
    assert result.marginal_watts() is None


def test_the_baseline_can_be_skipped() -> None:
    # An audit on a machine known to be quiet should not pay a second for a
    # figure it does not need.
    result = run_slice([sys.executable, "-c", "pass"], profile=False, baseline_seconds=0.0)
    assert result.baseline is None
    assert "idle_watts" not in result.to_mapping()


def test_the_baseline_is_taken_when_asked_for() -> None:
    result = run_slice([sys.executable, "-c", "pass"], profile=False, baseline_seconds=0.05)
    assert result.baseline is not None
