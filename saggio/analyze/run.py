"""
Running someone else's code, once they have said you may.

Module summary
--------------
The most useful number a cost model can carry is a measured one, and getting it
means executing the repository under study. There is no sandbox here and none is
pretended: the code runs as the user, with the user's permissions, on the user's
machine. That is a real decision with real consequences, so it is the user's to
make, explicitly, once, and it is recorded where they can see and revoke it.

What gets run is chosen to be as safe and as representative as the repository
allows. First choice is a capped slice of the real entry point, because the size
it covers is read from the repository's own configuration and so the fraction is a
fact. Second choice is the repository's own test suite, which was written to be
run and to terminate, but which covers an unknown share of a real workload, so no
completion projection follows from it.

Three failures used to happen quietly and now do not. A capped run that exits
non-zero, usually because the entry point does not take the flag, produces a
warning that says so, and no projection. A run that hits the time limit is
recorded as truncated, with the share of the limit it used, rather than being
presented as a completed slice. And a run taken with the profiler attached says
so, because cProfile charges per call and the inflated wall time it produces is
what every downstream energy, carbon, and money figure gets multiplied by.

Usage example
-------------
>>> from saggio.analyze.run import has_consent
>>> isinstance(has_consent(), bool)
True

Author
------
Warith Harchaoui
"""

from __future__ import annotations

import cProfile  # noqa: F401 - imported for the -m form used in the child command.
import json
import os
import pstats
import signal
import subprocess
import sys
import tempfile
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Final

import os_helper as osh
import platformdirs

try:  # Windows has no resource module; the child CPU time is simply unknown there.
    import resource
except ImportError:  # pragma: no cover - POSIX-only dependency.
    resource = None  # type: ignore[assignment]

from .power import PowerMeter, PowerReading

#: Application name used to locate the consent record.
_APP_NAME: Final[str] = "saggio"

#: File the consent decision is written to, so the user can find and delete it.
CONSENT_FILENAME: Final[str] = "run-consent.json"

#: What the user is agreeing to. Shown verbatim, because a consent prompt that
#: paraphrases what it is asking for is not consent.
CONSENT_PROMPT: Final[str] = (
    "To measure what this code costs to run, it has to be run.\n"
    "\n"
    "That means executing a third party's program on this machine, with your\n"
    "permissions and your network access. There is no sandbox. Anything the\n"
    "program can do, it will be able to do.\n"
    "\n"
    "This tool will run a short, capped slice, and will stop it at the time\n"
    "limit. It will not run anything else without asking again.\n"
    "\n"
    "Read the code first if you have not. This decision is recorded so you are\n"
    "not asked every time; delete the record to revoke it.\n"
)

#: The exact word required to grant consent. Anything else is a refusal, so a
#: stray keypress cannot become a yes.
CONSENT_WORD: Final[str] = "yes"

#: Default ceiling on a slice, in seconds. Long enough to get past import and
#: warm-up, short enough that nobody's afternoon is spent on it.
DEFAULT_TIMEOUT_SECONDS: Final[float] = 300.0

#: How many functions of the profile to keep. Enough to see where the time goes,
#: few enough to read.
PROFILE_TOP_N: Final[int] = 8


def consent_path(path: str | Path | None = None) -> Path:
    """Return the file a consent decision is recorded in.

    Parameters
    ----------
    path : str or pathlib.Path or None, optional
        An explicit file to use instead of the per-user one. Every function that
        touches the decision takes this, so a test can point the whole mechanism
        at a temporary directory. Without it, a test that exercised consent would
        silently change what the person running the test had agreed to.

    Returns
    -------
    pathlib.Path
        The file, with its directory created.

    Examples
    --------
    >>> consent_path().name
    'run-consent.json'
    >>> import tempfile
    >>> with tempfile.TemporaryDirectory() as folder:
    ...     consent_path(Path(folder) / "decision.json").name
    'decision.json'
    """
    if path is not None:
        target = Path(path)
        osh.make_directory(str(target.parent))
        return target
    folder = Path(platformdirs.user_config_dir(_APP_NAME))
    osh.make_directory(str(folder))
    return folder / CONSENT_FILENAME


def has_consent(path: str | Path | None = None) -> bool:
    """Return whether running downloaded code has already been agreed to.

    Parameters
    ----------
    path : str or pathlib.Path or None, optional
        Where the decision is recorded.

    Returns
    -------
    bool
        ``True`` only when a record exists and says yes. An unreadable or
        malformed record counts as no: consent has to be positively established,
        never inferred from a file nobody could parse.

    Examples
    --------
    >>> import tempfile
    >>> with tempfile.TemporaryDirectory() as folder:
    ...     has_consent(Path(folder) / "decision.json")
    False
    """
    target = consent_path(path)
    if not osh.file_exists(str(target), check_empty=True):
        return False
    try:
        record = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    return bool(record.get("granted"))


def record_consent(granted: bool, path: str | Path | None = None) -> Path:
    """Write a consent decision so the question is not asked again.

    Parameters
    ----------
    granted : bool
        What was decided.
    path : str or pathlib.Path or None, optional
        Where to record it.

    Returns
    -------
    pathlib.Path
        The file written.

    Examples
    --------
    >>> import tempfile
    >>> with tempfile.TemporaryDirectory() as folder:
    ...     written = record_consent(True, Path(folder) / "decision.json")
    ...     has_consent(written)
    True
    """
    target = consent_path(path)
    target.write_text(
        json.dumps(
            {"granted": granted, "decided_on": date.today().isoformat(), "tool": _APP_NAME},
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return target


def require_consent(
    prompt: Callable[[str], str] = input,
    *,
    path: str | Path | None = None,
    interactive: bool | None = None,
) -> bool:
    """Ask for consent once, record the answer, and return it.

    Parameters
    ----------
    prompt : callable, optional
        Reads the answer; injectable so a test never blocks on a terminal.
    path : str or pathlib.Path or None, optional
        Where the decision is recorded.
    interactive : bool or None, optional
        Whether there is a terminal to ask on. Detected when not given.

    Returns
    -------
    bool
        Whether running downloaded code is permitted. A session with no terminal
        is refused rather than defaulted: consent cannot be inferred from silence,
        and a build server must never be able to agree on a person's behalf.

    Examples
    --------
    >>> import contextlib, io, tempfile
    >>> with tempfile.TemporaryDirectory() as folder, contextlib.redirect_stdout(io.StringIO()):
    ...     decision = Path(folder) / "decision.json"
    ...     refused = require_consent(lambda _: "no", path=decision, interactive=True)
    ...     granted = require_consent(lambda _: "yes", path=decision, interactive=True)
    >>> refused, granted
    (False, True)
    >>> with tempfile.TemporaryDirectory() as folder:
    ...     silent = require_consent(path=Path(folder) / "d.json", interactive=False)
    >>> silent
    False
    """
    if has_consent(path):
        return True
    at_a_terminal = (
        interactive if interactive is not None else bool(sys.stdin and sys.stdin.isatty())
    )
    if not at_a_terminal:
        osh.error(
            "Running downloaded code needs explicit consent and there is no terminal "
            "to ask on. Run the command once interactively, or grant it with "
            "`saggio consent grant`."
        )
        return False
    print(CONSENT_PROMPT)
    answer = (
        prompt(f"Type {CONSENT_WORD!r} to allow it, anything else to decline: ").strip().lower()
    )
    granted = answer == CONSENT_WORD
    record_consent(granted, path)
    if not granted:
        osh.info("Declined. The audit will continue without running anything.")
    return granted


@dataclass(frozen=True, slots=True)
class ProfileEntry:
    """One function the profiler found time in.

    Parameters
    ----------
    function : str
        ``file:line(name)`` as the profiler spells it.
    cumulative_seconds : float
        Time spent in the function and everything it called.
    calls : int
        How many times it was called.

    Examples
    --------
    >>> ProfileEntry("m.py:1(f)", 0.5, 3).calls
    3
    """

    function: str
    cumulative_seconds: float
    calls: int

    def to_mapping(self) -> dict[str, Any]:
        """Serialise the entry for the model's measurement block.

        Returns
        -------
        dict
            A mapping with the function, its cumulative seconds, and its calls.

        Examples
        --------
        >>> sorted(ProfileEntry("f", 1.0, 1).to_mapping())
        ['calls', 'cumulative_seconds', 'function']
        """
        return {
            "function": self.function,
            "cumulative_seconds": round(self.cumulative_seconds, 4),
            "calls": self.calls,
        }


@dataclass(slots=True)
class SliceResult:
    """What happened when a slice of the repository was run.

    Parameters
    ----------
    command : tuple of str
        Exactly what was executed.
    exit_code : int
        What it returned. Non-zero means the numbers describe a failed run, and
        nothing may be projected from them.
    wall_seconds : float
        How long it took.
    cpu_seconds : float or None
        Processor time this side of the fence, where the platform reports it.
    power : PowerReading
        What the machine drew, measured or not.
    truncated : bool
        Whether the time limit stopped it.
    fraction_completed : float or None
        The share of a whole run it covered, when that is known from the
        repository's own configuration. ``None`` for a test-suite slice, which
        covers an unknown share and therefore licenses no projection.
    hot_path : tuple of ProfileEntry
        Where the time went.
    warnings : tuple of str
        Everything a reader needs to know to interpret the numbers above.

    Examples
    --------
    >>> SliceResult(command=("true",), exit_code=0, wall_seconds=0.1,
    ...             power=PowerReading(None, None, "n/a")).succeeded()
    True
    """

    command: tuple[str, ...]
    exit_code: int
    wall_seconds: float
    power: PowerReading
    cpu_seconds: float | None = None
    truncated: bool = False
    fraction_completed: float | None = None
    hot_path: tuple[ProfileEntry, ...] = field(default_factory=tuple)
    warnings: tuple[str, ...] = field(default_factory=tuple)

    def succeeded(self) -> bool:
        """Return whether the slice ran to a clean finish.

        Returns
        -------
        bool
            ``True`` when it exited zero and was not cut short.

        Examples
        --------
        >>> SliceResult(("x",), 1, 1.0, PowerReading(None, None, "")).succeeded()
        False
        """
        return self.exit_code == 0 and not self.truncated

    def may_project(self) -> bool:
        """Return whether a whole-run projection may be made from this slice.

        Returns
        -------
        bool
            ``True`` only when the run finished cleanly and covered a share of the
            work that was read from a file rather than guessed.

        Examples
        --------
        >>> SliceResult(("x",), 0, 1.0, PowerReading(None, None, ""),
        ...             fraction_completed=0.01).may_project()
        True
        """
        return self.succeeded() and self.fraction_completed is not None

    def to_mapping(self) -> dict[str, Any]:
        """Serialise the result for the model's measurement block.

        Returns
        -------
        dict
            Plain values and prose. The costs themselves become quantities
            elsewhere; this block records how they were obtained.

        Examples
        --------
        >>> "command" in SliceResult(("x",), 0, 1.0, PowerReading(None, None, "")).to_mapping()
        True
        """
        mapping: dict[str, Any] = {
            # A cost model is committed and shared, so the recorded command names
            # the user's home as ~ rather than spelling it out.
            "command": [osh.path_without_home(part) for part in self.command],
            "exit_code": self.exit_code,
            "measured_on": date.today().isoformat(),
            "power_scope": self.power.scope,
        }
        if self.power.sources:
            # Which counters answered, so a reader comparing two models can see
            # whether they are comparing the same hardware boundary.
            mapping["power_sources"] = list(self.power.sources)
        if self.cpu_seconds is not None:
            mapping["cpu_seconds"] = round(self.cpu_seconds, 4)
        if self.truncated:
            mapping["truncated"] = True
        if self.hot_path:
            mapping["hot_path"] = [entry.to_mapping() for entry in self.hot_path]
        if self.warnings:
            mapping["warnings"] = list(self.warnings)
        return mapping


def _children_cpu_seconds() -> float | None:
    """Return the processor time all reaped children have used so far.

    Returns
    -------
    float or None
        User plus system seconds from ``RUSAGE_CHILDREN``, or ``None`` where
        the platform does not report it. Two readings bracket one child's run
        because the counter only advances when a child is reaped.

    Examples
    --------
    >>> value = _children_cpu_seconds()
    >>> value is None or value >= 0.0
    True
    """
    if resource is None:
        return None
    usage = resource.getrusage(resource.RUSAGE_CHILDREN)
    return float(usage.ru_utime + usage.ru_stime)


def _end_process_tree(child: subprocess.Popen[Any], grouped: bool) -> None:
    """Stop a timed-out slice and everything it spawned.

    ``subprocess``'s own timeout kills one PID. A training script that forked
    dataloader workers, or a server the entry point started, would survive the
    "slice was stopped" warning and keep running as the user indefinitely.

    Parameters
    ----------
    child : subprocess.Popen
        The direct child.
    grouped : bool
        Whether the child was started as its own session, in which case the
        whole process group is signalled; otherwise only the child can be.
    """
    if grouped:
        try:
            os.killpg(child.pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError):  # pragma: no cover - races with exit.
            child.kill()
    else:  # pragma: no cover - non-POSIX fallback.
        child.kill()
    try:
        child.wait(timeout=5)
    except subprocess.TimeoutExpired:  # pragma: no cover - kernel refused the kill.
        pass


def _stderr_tail(sink: Any, lines: int = 3) -> list[str]:
    """Return the last few lines of a spooled stderr file.

    Parameters
    ----------
    sink : file object
        The temporary file the child's stderr was written to.
    lines : int, optional
        How many lines to keep.

    Returns
    -------
    list of str
        The tail, decoded leniently. Only the last few kilobytes are read, so a
        workload that logged gigabytes costs nothing here.
    """
    sink.flush()
    size = sink.seek(0, os.SEEK_END)
    sink.seek(max(0, size - 8192))
    text = sink.read().decode("utf-8", errors="replace")
    return text.strip().splitlines()[-lines:]


def _is_python_command(command: Sequence[str]) -> bool:
    """Return whether a command runs a Python interpreter.

    Parameters
    ----------
    command : sequence of str
        The command to inspect.

    Returns
    -------
    bool
        ``True`` when the first word is a Python interpreter.

    Examples
    --------
    >>> _is_python_command([sys.executable, "-m", "pytest"])
    True
    >>> _is_python_command(["make", "test"])
    False
    """
    return bool(command) and Path(command[0]).name.lower().startswith("python")


def _can_profile(command: Sequence[str]) -> bool:
    """Return whether the profiler can wrap this command.

    ``cProfile`` run as a module takes a script path or ``-m module``, and nothing
    else. It has no ``-c``, so wrapping ``python -c "..."`` turns a working
    command into a usage error from a tool the user never asked for, and the
    measurement describes a failure that this package caused.

    Parameters
    ----------
    command : sequence of str
        The command to inspect.

    Returns
    -------
    bool
        ``True`` when the command is a Python script or module invocation.

    Examples
    --------
    >>> _can_profile([sys.executable, "-m", "pytest", "-q"])
    True
    >>> _can_profile([sys.executable, "train.py"])
    True
    >>> _can_profile([sys.executable, "-c", "print(1)"])
    False
    >>> _can_profile([sys.executable])
    False
    >>> _can_profile(["make", "test"])
    False
    """
    if not _is_python_command(command) or len(command) < 2:
        return False
    first = command[1]
    if first == "-m":
        return len(command) > 2
    # An interpreter flag other than -m leaves nothing for cProfile to open:
    # -c takes source on the command line, - reads standard input, and the rest
    # (-i, -O, -u) change how the interpreter runs rather than what it runs.
    return not first.startswith("-")


def _profiled_command(command: Sequence[str], profile_path: Path) -> list[str]:
    """Rewrite a Python command so the profiler wraps it.

    Parameters
    ----------
    command : sequence of str
        The original command, known to start with this interpreter.
    profile_path : pathlib.Path
        Where the profiler should write its statistics.

    Returns
    -------
    list of str
        The rewritten command.

    Examples
    --------
    >>> _profiled_command([sys.executable, "-m", "pytest"], Path("/tmp/p.prof"))[1:4]
    ['-m', 'cProfile', '-o']
    """
    return [command[0], "-m", "cProfile", "-o", str(profile_path), *command[1:]]


def _read_profile(profile_path: Path, *, top: int = PROFILE_TOP_N) -> tuple[ProfileEntry, ...]:
    """Read the profiler's output and return where the time went.

    Parameters
    ----------
    profile_path : pathlib.Path
        The statistics file the child wrote.
    top : int, optional
        How many functions to keep.

    Returns
    -------
    tuple of ProfileEntry
        The heaviest functions by cumulative time, or an empty tuple when the
        file is missing, empty, or unreadable. An empty file is the normal outcome
        when the child crashed before the profiler could flush, so it is not
        treated as an error: the run's own numbers are still good.

    Examples
    --------
    >>> _read_profile(Path("/nonexistent.prof"))
    ()
    """
    if not osh.file_exists(str(profile_path), check_empty=True):
        return ()
    try:
        stats = pstats.Stats(str(profile_path))
    except (OSError, ValueError, EOFError, TypeError):
        return ()
    entries: list[ProfileEntry] = []
    for function, record in stats.stats.items():  # type: ignore[attr-defined]
        calls, _, _, cumulative = record[0], record[1], record[2], record[3]
        filename, line, name = function
        entries.append(
            ProfileEntry(
                function=f"{Path(str(filename)).name}:{line}({name})",
                cumulative_seconds=float(cumulative),
                calls=int(calls),
            )
        )
    entries.sort(key=lambda entry: entry.cumulative_seconds, reverse=True)
    return tuple(entries[:top])


def run_slice(
    command: Sequence[str],
    *,
    working_directory: str | Path | None = None,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    fraction_completed: float | None = None,
    profile: bool = True,
) -> SliceResult:
    """Run a command, time it, measure what it drew, and see where the time went.

    Parameters
    ----------
    command : sequence of str
        What to run. Passed as a list, never through a shell.
    working_directory : str or pathlib.Path or None, optional
        Where to run it; defaults to the current directory.
    timeout_seconds : float, optional
        How long to allow before stopping it.
    fraction_completed : float or None, optional
        The share of a whole run this covers, when it is known from the
        repository's own configuration.
    profile : bool, optional
        Whether to wrap a Python command in the profiler.

    Returns
    -------
    SliceResult
        Everything the run established, including why any of it should be
        distrusted.

    Raises
    ------
    FileNotFoundError
        If the command's program does not exist, which is a caller error rather
        than a property of the run.

    Examples
    --------
    >>> result = run_slice([sys.executable, "-c", "pass"], profile=False)
    >>> result.exit_code, result.succeeded()
    (0, True)
    """
    warnings: list[str] = []
    command = tuple(str(part) for part in command)
    workdir = str(working_directory) if working_directory is not None else None

    with osh.temporary_filename(suffix=".prof", delete=True) as profile_file:
        profile_path = Path(profile_file)
        wrap = profile and _can_profile(command)
        to_run = _profiled_command(command, profile_path) if wrap else list(command)
        if profile and not wrap:
            warnings.append(
                "No function-level profile was taken: the profiler can only wrap a "
                "Python script or a `-m module` invocation. The totals below are "
                "unaffected."
            )

        if wrap:
            # The wall-clock time below is of the *profiled* process. cProfile
            # charges per function call, which roughly doubles a call-heavy
            # workload, and that runtime is what every energy, carbon, and money
            # figure downstream is multiplied by. Saying so is the difference
            # between a measurement and an overstatement nobody can see.
            warnings.append(
                "The runtime below was measured with the function-level profiler "
                "attached. cProfile charges per call, so a call-heavy workload can "
                "take close to twice as long under it, and every cost derived from "
                "this runtime inherits that. Treat it as an upper bound, and measure "
                "again with --no-profile for the figure a cost model should carry."
            )

        meter = PowerMeter.start()
        truncated = False
        # The child runs as its own session on POSIX so a timeout can end the
        # whole tree it may have forked, not just the direct child. Its stdout
        # is discarded (nothing reads it, and buffering a chatty training loop
        # in this process's memory could OOM the auditor); stderr spools to
        # disk, of which only the tail is kept.
        grouped = os.name == "posix"
        cpu_before = _children_cpu_seconds()
        with tempfile.TemporaryFile() as err_sink, osh.wall_timer() as wall:
            child = subprocess.Popen(  # noqa: S603 - the command is a list, never a shell.
                to_run,
                cwd=workdir,
                stdout=subprocess.DEVNULL,
                stderr=err_sink,
                start_new_session=grouped,
            )
            try:
                child.wait(timeout=timeout_seconds)
                exit_code = child.returncode
                stderr_tail = _stderr_tail(err_sink)
            except subprocess.TimeoutExpired:
                truncated = True
                exit_code = -1
                stderr_tail = []
                _end_process_tree(child, grouped)
        seconds = float(wall["seconds"])
        cpu_after = _children_cpu_seconds()
        cpu_seconds = (
            cpu_after - cpu_before if cpu_before is not None and cpu_after is not None else None
        )
        reading = meter.stop(seconds=seconds)
        hot_path = _read_profile(profile_path) if wrap else ()

    if truncated:
        warnings.append(
            f"The slice hit the {timeout_seconds:g}-second limit and was stopped. "
            "The numbers describe the part that ran, not a completed slice, so no "
            "whole-run projection follows from them."
        )
    elif exit_code != 0:
        detail = f" Last output: {' / '.join(stderr_tail)}" if stderr_tail else ""
        warnings.append(
            f"The slice exited {exit_code}. The numbers describe a failed run and "
            f"must not be projected.{detail}"
        )
        if fraction_completed is not None:
            warnings.append(
                "A completed fraction was known for this command, but the run failed, "
                "so no whole-run projection was made. The usual cause is an entry "
                "point that does not accept the flag the slice was capped with; run "
                "the command by hand to see."
            )

    if not reading.measured():
        warnings.append(reading.scope)

    return SliceResult(
        command=command,
        exit_code=exit_code,
        wall_seconds=seconds,
        power=reading,
        cpu_seconds=cpu_seconds,
        truncated=truncated,
        fraction_completed=fraction_completed if exit_code == 0 and not truncated else None,
        hot_path=hot_path,
        warnings=tuple(warnings),
    )
