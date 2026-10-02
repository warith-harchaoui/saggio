"""What to run, how much of it, and how to cut it into a ladder.

Module summary
--------------
Finding the entry point, capping it to a slice small enough to time without
paying for the whole run, and laying out the sizes a scaling series needs. The
cap is a fraction of the stated work size, so a repository that does not say how
much work a run performs gets no slice rather than a guessed one.

Author
------
Warith Harchaoui
"""

from __future__ import annotations

import sys
from pathlib import Path

from .findings import RepositoryReading
from .tables import (
    _RUNS_ITSELF,
    DEFAULT_CAP_FRACTION,
    DEFAULT_SCALING_GROWTH,
    DEFAULT_SCALING_STEPS,
    ENTRYPOINT_NAMES,
)
from .walking import _iter_source_files, _read_head


def detect_tests(root: Path) -> tuple[bool, tuple[str, ...]]:
    """Return whether the repository has a test suite, and how to run a slice of it.

    A repository's own tests are the safest representative thing to execute: they
    were written to be run, they exercise the real code paths, and they are
    expected to terminate.

    Parameters
    ----------
    root : pathlib.Path
        The repository root.

    Returns
    -------
    tuple
        Whether tests were found, and a bounded command, empty when they were not.

    Examples
    --------
    >>> from pathlib import Path
    >>> found, command = detect_tests(Path("."))
    >>> found and command[1:3] == ("-m", "pytest")
    True
    """
    has_tests = (root / "tests").is_dir() or (root / "test").is_dir()
    if not has_tests:
        # Via the filtered walk, so a test file inside .venv or node_modules does
        # not make the tool run somebody else's suite as if it were this one's.
        has_tests = any(
            path.name.startswith("test_")
            for path in _iter_source_files(root)
            if path.suffix == ".py"
        )
    if not has_tests:
        return False, ()
    # sys.executable is the interpreter actually running, which is the only
    # spelling that is correct on macOS, Linux, and Windows alike. `-x` stops at
    # the first failure so a broken suite does not become a long slice.
    return True, (sys.executable, "-m", "pytest", "-q", "-x")


def find_entrypoint(root: Path) -> str | None:
    r"""Return the script a capped slice of the real workload would run.

    Parameters
    ----------
    root : pathlib.Path
        The repository root.

    Returns
    -------
    str or None
        A repository-relative filename, or ``None`` when none of the well-known
        entry points is present at the root.

    Examples
    --------
    >>> from pathlib import Path
    >>> import tempfile
    >>> with tempfile.TemporaryDirectory() as folder:
    ...     _ = (Path(folder) / "main.py").write_text("pass", encoding="utf-8")
    ...     find_entrypoint(Path(folder))
    'main.py'

    A repository with no conventionally named script but exactly one that runs
    itself has an unambiguous entry point anyway:

    >>> with tempfile.TemporaryDirectory() as folder:
    ...     _ = (Path(folder) / "config.py").write_text("size = 10", encoding="utf-8")
    ...     _ = (Path(folder) / "predict.py").write_text(
    ...         'if __name__ == "__main__":\n    pass\n', encoding="utf-8")
    ...     find_entrypoint(Path(folder))
    'predict.py'

    Two of them is not unambiguous, so neither is chosen:

    >>> with tempfile.TemporaryDirectory() as folder:
    ...     for name in ("first.py", "second.py"):
    ...         _ = (Path(folder) / name).write_text(
    ...             'if __name__ == "__main__":\n    pass\n', encoding="utf-8")
    ...     find_entrypoint(Path(folder)) is None
    True
    """
    for name in ENTRYPOINT_NAMES:
        if (root / name).is_file():
            return name
    # Nothing conventionally named. A repository can still have one obvious
    # script: exactly one file at the root that runs itself. Picking it when
    # there is one is not a guess, and refusing when there are two is not
    # timidity — a slice of the wrong script measures the wrong thing, and the
    # reader would have no way to tell from the number.
    runnable = sorted(
        path.name
        for path in root.glob("*.py")
        if path.is_file() and _RUNS_ITSELF.search(_read_head(path))
    )
    return runnable[0] if len(runnable) == 1 else None


def capped_entrypoint_command(
    reading: RepositoryReading,
    *,
    cap_fraction: float = DEFAULT_CAP_FRACTION,
) -> tuple[tuple[str, ...], float] | tuple[None, None]:
    """Build a command that runs a known share of the real workload.

    The size comes from the repository's own configuration, so the fraction is a
    fact read from a file rather than a guess. The command passes the size key as
    a flag, which assumes the entry point parses flags in the usual way; when it
    does not, the run exits non-zero and the caller must say so in the model
    rather than quietly projecting from whatever did happen.

    Parameters
    ----------
    reading : RepositoryReading
        The static reading, which must carry a work size and an entry point.
    cap_fraction : float, optional
        The share of the whole run to aim for.

    Returns
    -------
    tuple
        The command and the exact fraction it covers, or ``(None, None)`` when
        there is no entry point or no stated size to cap against.

    Examples
    --------
    >>> from saggio.analyze.static.findings import RepositoryReading
    >>> from saggio.analyze.static.findings import WorkSizeCandidate
    >>> from pathlib import Path
    >>> reading = RepositoryReading(
    ...     root=Path("."), entrypoint="train.py",
    ...     work_size=WorkSizeCandidate("max_iters", 600000.0, "config.py::max_iters"))
    >>> command, fraction = capped_entrypoint_command(reading)
    >>> command[-2:], round(fraction, 6)
    (('--max_iters', '600'), 0.001)
    """
    if reading.entrypoint is None or reading.work_size is None:
        return None, None
    total = reading.work_size.value
    capped = max(1, int(total * cap_fraction))
    fraction = min(capped / total, 1.0)
    command = (
        sys.executable,
        str(reading.root / reading.entrypoint),
        f"--{reading.work_size.key}",
        str(capped),
    )
    return command, fraction


def scaling_ladder(
    reading: RepositoryReading,
    *,
    cap_fraction: float = DEFAULT_CAP_FRACTION,
    steps: int = DEFAULT_SCALING_STEPS,
    growth: float = DEFAULT_SCALING_GROWTH,
) -> tuple[tuple[tuple[str, ...], float, float], ...]:
    """Build several capped commands of increasing size, to measure the scaling.

    The top rung is the slice that would have been run anyway, so nothing about
    the cost figures changes by asking for a ladder: the rungs below it exist
    only to establish how the work grows, and they are small by construction.

    Sizes are integers because they are passed to somebody else's flag, so two
    rungs can collide after rounding on a repository whose stated size is small.
    Colliding rungs are dropped rather than run twice, which means a short ladder
    is a possible answer and the caller has to be ready for one: fewer than three
    distinct sizes licenses no exponent.

    Parameters
    ----------
    reading : RepositoryReading
        The static reading, which must carry a work size and an entry point.
    cap_fraction : float, optional
        The share of the whole run the largest rung aims for.
    steps : int, optional
        How many rungs to build, before collisions are dropped.
    growth : float, optional
        The factor between one rung and the next.

    Returns
    -------
    tuple
        One ``(command, fraction, size)`` triple per rung, smallest first, or an
        empty tuple when there is no entry point or no stated size to cap
        against.

    Examples
    --------
    >>> from saggio.analyze.static.findings import RepositoryReading
    >>> from saggio.analyze.static.findings import WorkSizeCandidate
    >>> from pathlib import Path
    >>> reading = RepositoryReading(
    ...     root=Path("."), entrypoint="train.py",
    ...     work_size=WorkSizeCandidate("max_iters", 600000.0, "config.py::max_iters"))
    >>> ladder = scaling_ladder(reading)
    >>> [size for _, _, size in ladder]
    [37.0, 150.0, 600.0]
    >>> ladder[-1][0][-2:]
    ('--max_iters', '600')

    A repository whose whole run is tiny cannot be cut three ways, and says so
    by returning fewer rungs than were asked for:

    >>> tiny = RepositoryReading(
    ...     root=Path("."), entrypoint="train.py",
    ...     work_size=WorkSizeCandidate("epochs", 2.0, "config.yaml::epochs"))
    >>> [size for _, _, size in scaling_ladder(tiny)]
    [1.0]

    >>> scaling_ladder(RepositoryReading(root=Path(".")))
    ()
    """
    if reading.entrypoint is None or reading.work_size is None:
        return ()
    if steps < 1 or growth <= 1.0:
        return ()

    total = reading.work_size.value
    rungs: dict[int, tuple[tuple[str, ...], float, float]] = {}
    for step in reversed(range(steps)):
        share = cap_fraction / (growth**step)
        capped = max(1, int(total * share))
        if capped in rungs:
            continue
        rungs[capped] = (
            (
                sys.executable,
                str(reading.root / reading.entrypoint),
                f"--{reading.work_size.key}",
                str(capped),
            ),
            min(capped / total, 1.0),
            float(capped),
        )
    return tuple(rungs[size] for size in sorted(rungs))
