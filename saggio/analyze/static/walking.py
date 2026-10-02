"""Walking the tree, and deciding what is worth reading.

Module summary
--------------
Which files are the code under study, which belong to the suite that tests it,
and which line is prose about code rather than code. The distinction between a
workload and its suite decides whether a framework named in a fixture counts as
evidence about what this thing costs to run, which is why it lives here rather
than separately inside each detector.

Author
------
Warith Harchaoui
"""

from __future__ import annotations

from pathlib import Path

from .tables import (
    _CONFIG_READ_BYTES,
    PROSE_MARKERS,
    SKIPPED_DIRECTORIES,
    TEST_DIRECTORIES,
)


def is_test_path(path: Path) -> bool:
    """Return whether a file is part of the suite rather than the workload.

    Parameters
    ----------
    path : pathlib.Path
        Any file inside the repository.

    Returns
    -------
    bool
        ``True`` when the file tests the repository rather than running it.

    Examples
    --------
    >>> is_test_path(Path("tests/unit/test_static.py"))
    True
    >>> is_test_path(Path("src/app.py"))
    False
    """
    if any(part.lower() in TEST_DIRECTORIES for part in path.parts):
        return True
    name = path.name.lower()
    return (
        name == "conftest.py"
        or name.startswith("test_")
        or name.endswith(("_test.py", ".test.ts", ".test.js", ".spec.ts", ".spec.js"))
    )


def _iter_source_files(root: Path):
    """Yield the repository's own source files, skipping vendored trees.

    The workload's own code comes first and the suite that tests it comes last.
    Every detector below keeps the first place it saw a thing, so that ordering
    is what makes a service called from ``app.py`` outrank the same service named
    in a fixture, and what makes a hit whose evidence line is a test file mean
    that the suite is the only place it appears.

    Parameters
    ----------
    root : pathlib.Path
        The repository root.

    Yields
    ------
    pathlib.Path
        Files that are part of the code under study, workload before suite.

    Examples
    --------
    >>> any(p.suffix == ".py" for p in _iter_source_files(Path(".")))
    True
    """
    deferred: list[Path] = []
    for path in root.rglob("*"):
        # Only the path *inside* the repository decides the skip: a repository
        # legitimately cloned under ~/build or /tmp/dist must not read as empty
        # because an ancestor directory happens to share a vendored-tree name.
        inside = path.relative_to(root) if path.is_relative_to(root) else path
        if any(part in SKIPPED_DIRECTORIES for part in inside.parts):
            continue
        if not path.is_file():
            continue
        if is_test_path(path.relative_to(root) if path.is_relative_to(root) else path):
            deferred.append(path)
            continue
        yield path
    yield from deferred


def _iter_workload_files(root: Path):
    """Yield only the files the repository runs, leaving out the suite.

    Parameters
    ----------
    root : pathlib.Path
        The repository root.

    Yields
    ------
    pathlib.Path
        Files that are part of the workload.

    Examples
    --------
    >>> all(not is_test_path(p) for p in _iter_workload_files(Path("saggio")))
    True
    """
    for path in _iter_source_files(root):
        if is_test_path(path.relative_to(root) if path.is_relative_to(root) else path):
            return
        yield path


def _is_prose_line(line: str) -> bool:
    """Return whether a line is a comment or documentation rather than code.

    Service detection reads source files line by line, and a line that merely
    talks about a service is not a line that calls one. Skipping comments and
    documentation markers is what stops this package's own description of the
    services catalogue from being reported as a repository full of paid APIs.

    Parameters
    ----------
    line : str
        One line of source.

    Returns
    -------
    bool
        ``True`` when the line opens with a comment or documentation marker.

    Examples
    --------
    >>> _is_prose_line("    # from openai import OpenAI")
    True
    >>> _is_prose_line("from openai import OpenAI")
    False
    >>> _is_prose_line("    >>> import openai")
    True
    """
    stripped = line.lstrip()
    return stripped.startswith(PROSE_MARKERS)


def _read_head(path: Path, limit: int = _CONFIG_READ_BYTES) -> str:
    """Return the first bytes of a file as text, or an empty string.

    Parameters
    ----------
    path : pathlib.Path
        The file to look at.
    limit : int, optional
        How much to read. A main guard is at the end of a script, but scripts
        this reads are small; a file larger than the cap is read up to it and
        the guard is simply not found, which errs towards refusing rather than
        towards picking the wrong script.

    Returns
    -------
    str
        The text, or ``""`` when it cannot be read.

    Examples
    --------
    >>> _read_head(Path("/nonexistent/file.py"))
    ''
    """
    try:
        return path.read_text(encoding="utf-8", errors="replace")[:limit]
    except OSError:
        return ""
