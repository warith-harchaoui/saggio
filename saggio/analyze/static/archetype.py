"""What kind of thing this repository is, and what it is built on.

Module summary
--------------
Whether it reads as training, inference, a service, a pipeline, a command-line
tool or a library, and which frameworks a real run would load. Both are read
from the files a workload would use, never from the suite beside them.

Author
------
Warith Harchaoui
"""

from __future__ import annotations

from pathlib import Path

from .tables import (
    _MAX_SCANNED_BYTES,
    _SCANNED_EXTENSIONS,
    ARCHETYPE_FILES,
    FRAMEWORK_PATTERNS,
)
from .walking import _iter_source_files, _iter_workload_files, is_test_path


def _filename_weight_at_depth(depth: int) -> float:
    """Return how much a file name counts as evidence at that depth.

    A file at the root is what the repository is about; the same name three
    directories down is a detail of how it is built. An ``app.py`` inside
    ``src/cli/`` is not a web service, and weighing it as one is how a
    command-line tool gets reported as a server.

    Parameters
    ----------
    depth : int
        How many directories separate the file from the root.

    Returns
    -------
    float
        One at the root, falling away below it.

    Examples
    --------
    >>> _filename_weight_at_depth(0) > _filename_weight_at_depth(2)
    True
    """
    return 1.0 / (1.0 + depth)


def declares_console_script(root: Path) -> bool:
    r"""Return whether the packaging metadata installs a command.

    Parameters
    ----------
    root : pathlib.Path
        The repository root.

    Returns
    -------
    bool
        ``True`` when ``pyproject.toml``, ``setup.py`` or ``package.json`` says
        the project installs an executable.

    Examples
    --------
    >>> import tempfile
    >>> with tempfile.TemporaryDirectory() as folder:
    ...     _ = (Path(folder) / "pyproject.toml").write_text(
    ...         '[project.scripts]\\nthing = "thing:run"\\n', encoding="utf-8")
    ...     declares_console_script(Path(folder))
    True
    """
    pyproject = root / "pyproject.toml"
    if pyproject.is_file():
        try:
            if "[project.scripts]" in pyproject.read_text(encoding="utf-8", errors="replace"):
                return True
        except OSError:
            pass
    setup = root / "setup.py"
    if setup.is_file():
        try:
            if "console_scripts" in setup.read_text(encoding="utf-8", errors="replace"):
                return True
        except OSError:
            pass
    package = root / "package.json"
    if package.is_file():
        try:
            return '"bin"' in package.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return False
    return False


def detect_archetype(root: Path, languages: dict[str, int]) -> str:
    """Return a coarse label for the shape of work the repository does.

    Parameters
    ----------
    root : pathlib.Path
        The repository root.
    languages : dict
        The language counts, used only as a last resort.

    Returns
    -------
    str
        One of the archetype labels, or ``unknown``.

    Examples
    --------
    >>> import tempfile
    >>> with tempfile.TemporaryDirectory() as folder:
    ...     _ = (Path(folder) / "train.py").write_text("pass", encoding="utf-8")
    ...     detect_archetype(Path(folder), {"Python": 1})
    'training'
    """
    scores: dict[str, float] = {}
    present: set[str] = set()
    for path in _iter_workload_files(root):
        present.add(path.name.lower())
        relative = path.relative_to(root) if path.is_relative_to(root) else path
        for label, names in ARCHETYPE_FILES:
            if path.name.lower() in names:
                scores[label] = scores.get(label, 0.0) + _filename_weight_at_depth(
                    len(relative.parts) - 1
                )

    if declares_console_script(root):
        # Packaging metadata is a statement about what the thing is, where a file
        # name is an inference about it. A repository that installs a command is
        # a command, whatever a file three directories down happens to be called.
        scores["command-line-tool"] = scores.get("command-line-tool", 0.0) + 1.0

    if scores:
        order = [label for label, _ in ARCHETYPE_FILES]
        # Ties go to the earlier label, which is how a project that both trains
        # and serves is reported as the expensive one it is.
        return max(scores, key=lambda label: (scores[label], -order.index(label)))
    if "Python" in languages and ("setup.py" in present or "pyproject.toml" in present):
        return "library"
    return "unknown"


def detect_frameworks(root: Path) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Return the frameworks the workload imports, and those only its suite names.

    A suite writes fixtures, and a fixture that writes ``import torch`` into a
    temporary file is not a repository that trains anything. Reading both at once
    is how a tool ends up reporting a dozen frameworks to a project that uses
    none, so the two are read apart and reported apart.

    Parameters
    ----------
    root : pathlib.Path
        The repository root.

    Returns
    -------
    tuple of (tuple of str, tuple of str)
        Frameworks the workload imports, then frameworks that appear only in the
        code that tests it. Both in catalogue order.

    Examples
    --------
    >>> workload, in_suite_only = detect_frameworks(Path("."))
    >>> isinstance(workload, tuple) and isinstance(in_suite_only, tuple)
    True
    """
    workload_blobs: list[str] = []
    suite_blobs: list[str] = []
    for path in _iter_source_files(root):
        if path.suffix.lower() not in _SCANNED_EXTENSIONS:
            continue
        try:
            if path.stat().st_size > _MAX_SCANNED_BYTES:
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        relative = path.relative_to(root) if path.is_relative_to(root) else path
        (suite_blobs if is_test_path(relative) else workload_blobs).append(text)

    workload = "\n".join(workload_blobs)
    suite = "\n".join(suite_blobs)
    found: list[str] = []
    in_suite_only: list[str] = []
    for name, pattern in FRAMEWORK_PATTERNS.items():
        if pattern.search(workload):
            found.append(name)
        elif pattern.search(suite):
            in_suite_only.append(name)
    return tuple(found), tuple(in_suite_only)
