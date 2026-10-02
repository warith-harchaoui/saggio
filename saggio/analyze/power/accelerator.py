"""What an NVIDIA accelerator drew, by counter or by sampling.

Module summary
--------------
The total energy counter where the driver keeps one, and a sampling thread
where it does not. A mean of readings across a run is an honest figure for a
card that publishes instantaneous draw; it is not the same quantity as a
counter, and the scope sentence says which one was read.

Author
------
Warith Harchaoui
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from .tables import (
    _MINIMUM_SAMPLES,
    _QUERY_TIMEOUT_SECONDS,
    _SAMPLE_INTERVAL_MS,
    NVIDIA_SMI,
)


def _query_nvidia_smi(field_name: str) -> list[str] | None:
    """Ask the NVIDIA driver one question about every board, or return ``None``.

    Parameters
    ----------
    field_name : str
        The query field, as ``nvidia-smi --help-query-gpu`` spells it.

    Returns
    -------
    list of str or None
        One raw answer per board, or ``None`` when there is no driver to ask,
        the driver did not answer, or a board answered that it does not know.

    Examples
    --------
    >>> answers = _query_nvidia_smi("power.draw")
    >>> answers is None or all(isinstance(answer, str) for answer in answers)
    True
    """
    if shutil.which(NVIDIA_SMI) is None:
        return None
    try:
        completed = subprocess.run(  # noqa: S603 - a fixed argument list, never a shell.
            [
                NVIDIA_SMI,
                f"--query-gpu={field_name}",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=_QUERY_TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if completed.returncode != 0:
        return None
    answers = [line.strip() for line in completed.stdout.splitlines() if line.strip()]
    if not answers:
        return None
    # A board that does not implement the field answers "[N/A]" rather than
    # failing. Half an answer across two boards is not an answer about the
    # machine, so one unsupported board voids the query.
    if any(answer.startswith("[") for answer in answers):
        return None
    return answers


def read_accelerator_energy_millijoules() -> int | None:
    """Return the accelerators' accumulated energy, or ``None``.

    Every board present is summed, so a machine with eight of them is counted
    whole. The counter runs from the moment the driver loaded, which makes it the
    accelerator's exact equivalent of the processor package counter: two readings
    and a duration give an average that owes nothing to sampling.

    Returns
    -------
    int or None
        Millijoules since the driver loaded, or ``None`` when no board reports
        the counter.

    Examples
    --------
    >>> value = read_accelerator_energy_millijoules()
    >>> value is None or value >= 0
    True
    """
    answers = _query_nvidia_smi("total_energy_consumption")
    if answers is None:
        return None
    try:
        return sum(int(float(answer)) for answer in answers)
    except ValueError:
        return None


@dataclass(slots=True)
class AcceleratorSampler:
    """A driver process logging board power for the length of a run.

    Older drivers and most consumer boards publish what they are drawing right
    now and keep no running total. The honest answer there is a mean of readings
    taken across the run, which is what this collects: the driver does its own
    timing in its own process, writing to a file rather than a pipe so that a run
    long enough to matter cannot fill a buffer and stall behind it.

    Parameters
    ----------
    process : subprocess.Popen
        The logging process, running until the measured run is over.
    log_path : pathlib.Path
        Where it is writing its readings.

    Examples
    --------
    >>> AcceleratorSampler.start() is None or True
    True
    """

    process: subprocess.Popen[str]
    log_path: Path = field(default_factory=Path)
    #: How many boards answer each tick. The log holds one line per board per
    #: tick, so the machine's draw is the per-reading mean times this count;
    #: averaging the raw lines alone would report an eight-board node at the
    #: wattage of one board.
    board_count: int = 1

    @classmethod
    def start(cls) -> AcceleratorSampler | None:
        """Begin logging, or return ``None`` when there is nothing to log.

        Returns
        -------
        AcceleratorSampler or None
            A running sampler, or ``None`` when no driver answered.

        Examples
        --------
        >>> sampler = AcceleratorSampler.start()
        >>> sampler is None or sampler.stop() is not None
        True
        """
        answers = _query_nvidia_smi("power.draw")
        if answers is None:
            return None
        handle = tempfile.NamedTemporaryFile(
            mode="w", suffix=".watts", prefix="saggio-", delete=False, encoding="utf-8"
        )
        log_path = Path(handle.name)
        try:
            process = subprocess.Popen(  # noqa: S603 - a fixed argument list, never a shell.
                [
                    NVIDIA_SMI,
                    "--query-gpu=power.draw",
                    "--format=csv,noheader,nounits",
                    f"-lms={_SAMPLE_INTERVAL_MS}",
                ],
                stdout=handle,
                stderr=subprocess.DEVNULL,
                text=True,
            )
        except (OSError, subprocess.SubprocessError):
            handle.close()
            log_path.unlink(missing_ok=True)
            return None
        return cls(process=process, log_path=log_path, board_count=max(len(answers), 1))

    def stop(self) -> tuple[float, int] | None:
        """Stop logging and return the mean board power and how many readings it is.

        Returns
        -------
        tuple of (float, int), or None
            Mean watts across every board and every reading, with the number of
            readings it was averaged over, or ``None`` when too few arrived to
            average. The count travels with the mean because a mean of four
            readings and a mean of four thousand deserve different trust, and the
            reader cannot tell them apart from the number alone.

        Examples
        --------
        >>> sampler = AcceleratorSampler.start()
        >>> sampler is None or sampler.stop() is None or True
        True
        """
        try:
            self.process.terminate()
            self.process.wait(timeout=_QUERY_TIMEOUT_SECONDS)
        except (OSError, subprocess.SubprocessError):
            self.process.kill()
        try:
            lines = self.log_path.read_text(encoding="utf-8").splitlines()
        except OSError:
            lines = []
        finally:
            self.log_path.unlink(missing_ok=True)
        readings: list[float] = []
        for line in lines:
            for cell in line.split(","):
                try:
                    readings.append(float(cell.strip()))
                except ValueError:
                    # "[N/A]" and the driver's own noise. A line that is not a
                    # number is not a reading, and pretending otherwise would
                    # drag the mean towards a figure nobody measured.
                    continue
        if len(readings) < _MINIMUM_SAMPLES:
            return None
        # One line per board per tick, so the per-reading mean is one board's
        # draw; the machine draws that times the boards answering each tick.
        return sum(readings) / len(readings) * self.board_count, len(readings)
