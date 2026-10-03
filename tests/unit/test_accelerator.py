"""The NVIDIA counters, on a machine with no NVIDIA card in it.

Why this file exists
--------------------
Two readers here shell out to ``nvidia-smi``: one asks it a question and reads
the answer, the other leaves it logging into a file for the length of a run and
averages what it wrote. Neither runs on a developer's Mac and neither runs on
the cloud runner continuous integration uses, so the parsing, the averaging and
every refusal in between were the least exercised code in the package after the
power split.

Nothing here mocks the readers. A stand-in ``nvidia-smi`` is written -- a real
executable that prints what the real one prints, in the same format, for the
same flags -- and the module is pointed at it. The subprocess is real, the log
file is real, and the arithmetic is the shipped arithmetic.

Author
------
Warith Harchaoui
"""

from __future__ import annotations

import os
import stat
import sys
from pathlib import Path

import pytest

#: What `nvidia-smi --query-gpu=... --format=csv,noheader,nounits` prints: one
#: line per board, one value per line, no header and no units.
STAND_IN = """\
#!{python}
import sys, time
argv = sys.argv[1:]
if any(a.startswith("-lms") for a in argv):
    # The logging mode: keep printing until somebody terminates this. The lines
    # may differ from the one-shot answer, which is what a real driver does when
    # a board drops out of a stream it was answering a moment ago.
    while True:
        for line in {logged!r}:
            print(line, flush=True)
        time.sleep({interval})
else:
    for line in {lines!r}:
        print(line)
sys.exit({code})
"""


def stand_in_smi(
    tmp_path: Path,
    lines: list[str],
    *,
    logged: list[str] | None = None,
    code: int = 0,
    interval: float = 0.01,
) -> str:
    """Write an executable that answers the way nvidia-smi answers.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Where to write it.
    lines : list of str
        One line per board, exactly as the real tool would print them, in
        answer to a one-shot query.
    logged : list of str or None, optional
        What it prints while logging, when that differs. A real driver can
        answer a query cleanly and then emit `[N/A]` into the stream a moment
        later, which is the case worth testing separately.
    code : int, optional
        The exit status. A driver that is present but unhappy exits non-zero.
    interval : float, optional
        Seconds between ticks in logging mode.

    Returns
    -------
    str
        The path to the executable, for ``NVIDIA_SMI``.
    """
    script = tmp_path / "nvidia-smi"
    script.write_text(
        STAND_IN.format(
            python=sys.executable,
            lines=lines,
            logged=lines if logged is None else logged,
            code=code,
            interval=interval,
        ),
        encoding="utf-8",
    )
    script.chmod(script.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    return str(script)


def point_at(monkeypatch: pytest.MonkeyPatch, path: str) -> None:
    """Point the accelerator readers at this tool."""
    from saggio.analyze.power import accelerator

    monkeypatch.setattr(accelerator, "NVIDIA_SMI", path)


# --- Asking the driver a question ----------------------------------------------


def test_one_board_answering_is_read(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from saggio.analyze.power.accelerator import _query_nvidia_smi

    point_at(monkeypatch, stand_in_smi(tmp_path, ["412.75"]))
    assert _query_nvidia_smi("power.draw") == ["412.75"]


def test_every_board_answers_on_its_own_line(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from saggio.analyze.power.accelerator import _query_nvidia_smi

    point_at(monkeypatch, stand_in_smi(tmp_path, ["400.1", "398.6", "401.0", "399.9"]))
    assert _query_nvidia_smi("power.draw") == ["400.1", "398.6", "401.0", "399.9"]


def test_a_board_that_does_not_implement_the_field_voids_the_whole_query(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Half an answer across two boards is not an answer about the machine.

    The driver answers ``[N/A]`` rather than failing, so a reader that kept the
    numbers it did get would report one board's draw as the machine's.
    """
    from saggio.analyze.power.accelerator import _query_nvidia_smi

    point_at(monkeypatch, stand_in_smi(tmp_path, ["400.1", "[N/A]"]))
    assert _query_nvidia_smi("power.draw") is None


def test_a_driver_that_exits_unhappy_is_no_answer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from saggio.analyze.power.accelerator import _query_nvidia_smi

    point_at(monkeypatch, stand_in_smi(tmp_path, ["400.1"], code=1))
    assert _query_nvidia_smi("power.draw") is None


def test_no_tool_at_all_is_no_answer(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from saggio.analyze.power.accelerator import _query_nvidia_smi

    point_at(monkeypatch, str(tmp_path / "there-is-no-nvidia-smi-here"))
    assert _query_nvidia_smi("power.draw") is None


def test_a_tool_that_prints_nothing_is_no_answer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from saggio.analyze.power.accelerator import _query_nvidia_smi

    point_at(monkeypatch, stand_in_smi(tmp_path, []))
    assert _query_nvidia_smi("power.draw") is None


def test_the_energy_counter_is_converted_from_millijoules(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from saggio.analyze.power.accelerator import read_accelerator_energy_millijoules

    point_at(monkeypatch, stand_in_smi(tmp_path, ["1500000", "2500000"]))
    assert read_accelerator_energy_millijoules() == 4_000_000


# --- Leaving it logging for the length of a run --------------------------------


def wait_for_lines(path: Path, at_least: int, seconds: float = 5.0) -> bool:
    """Wait until the log holds this many lines.

    Polling rather than sleeping a fixed amount: a loaded machine is slower, and
    a test tuned to one machine's speed fails on another for no reason anybody
    can act on.
    """
    import time

    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        try:
            if len(path.read_text(encoding="utf-8").splitlines()) >= at_least:
                return True
        except OSError:
            pass
        time.sleep(0.01)
    return False


def test_no_driver_means_no_sampler(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from saggio.analyze.power.accelerator import AcceleratorSampler

    point_at(monkeypatch, str(tmp_path / "absent"))
    assert AcceleratorSampler.start() is None


def test_a_sampled_run_reports_a_mean_and_how_many_readings_it_is(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The count travels with the mean, and that is the point.

    A mean of four readings and a mean of four thousand deserve different
    trust, and a reader cannot tell them apart from the number alone.
    """
    from saggio.analyze.power.accelerator import AcceleratorSampler

    point_at(monkeypatch, stand_in_smi(tmp_path, ["300.0"]))
    sampler = AcceleratorSampler.start()
    assert sampler is not None
    assert wait_for_lines(sampler.log_path, 4), "the tool never logged anything"
    result = sampler.stop()
    assert result is not None
    watts, count = result
    assert watts == pytest.approx(300.0)
    assert count >= 4
    assert not sampler.log_path.exists(), "the sampler left its log behind"


def test_two_boards_are_counted_as_two(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """One line per board per tick, so the machine draws the mean times the boards.

    Reporting one board's draw for a two-board node would halve the figure, and
    nothing downstream could tell.
    """
    from saggio.analyze.power.accelerator import AcceleratorSampler

    point_at(monkeypatch, stand_in_smi(tmp_path, ["250.0", "250.0"]))
    sampler = AcceleratorSampler.start()
    assert sampler is not None
    assert sampler.board_count == 2
    assert wait_for_lines(sampler.log_path, 6)
    result = sampler.stop()
    assert result is not None
    watts, _count = result
    assert watts == pytest.approx(500.0), "a two-board node reported one board's draw"


def test_noise_in_the_log_is_skipped_rather_than_averaged_in(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A line that is not a number is not a reading.

    The driver writes ``[N/A]`` and its own warnings into the same stream.
    Treating one as a zero would drag the mean towards a figure nobody measured.
    """
    from saggio.analyze.power.accelerator import AcceleratorSampler

    # The query answers cleanly for both boards; one of them drops out of the
    # stream afterwards, which `start` cannot foresee and `stop` must survive.
    point_at(monkeypatch, stand_in_smi(tmp_path, ["200.0", "200.0"], logged=["200.0", "[N/A]"]))
    sampler = AcceleratorSampler.start()
    assert sampler is not None
    assert wait_for_lines(sampler.log_path, 6)
    result = sampler.stop()
    assert result is not None
    watts, _count = result
    # Two lines per tick, one of them unreadable: the mean is of the readable
    # one, times the two boards the query said were there.
    assert watts == pytest.approx(400.0)


def test_too_few_readings_is_no_figure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from saggio.analyze.power import accelerator
    from saggio.analyze.power.accelerator import AcceleratorSampler

    point_at(monkeypatch, stand_in_smi(tmp_path, ["300.0"], interval=10.0))
    monkeypatch.setattr(accelerator, "_MINIMUM_SAMPLES", 10_000)
    sampler = AcceleratorSampler.start()
    assert sampler is not None
    assert sampler.stop() is None
    assert not sampler.log_path.exists()


def test_a_tool_that_cannot_be_launched_leaves_no_file_behind(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The failure path has to clean up after itself.

    It opens the log before it launches, so a launch that fails would otherwise
    leave a stray file in the temporary directory on every attempt.
    """
    from saggio.analyze.power import accelerator
    from saggio.analyze.power.accelerator import AcceleratorSampler

    # The query succeeds, so the sampler gets as far as launching; the launch
    # itself is what fails.
    point_at(monkeypatch, stand_in_smi(tmp_path, ["300.0"]))
    before = set(os.listdir(tmp_path))

    def refuse(*_a: object, **_k: object) -> None:
        raise OSError("cannot launch")

    monkeypatch.setattr(accelerator.subprocess, "Popen", refuse)
    assert AcceleratorSampler.start() is None
    assert set(os.listdir(tmp_path)) == before, "a log file was left behind"
