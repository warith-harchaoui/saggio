"""How much work one whole run performs, and which file said so.

Module summary
--------------
The most contested number a static read produces, because a repository usually
states it more than once and the statements usually disagree. This ranks the
candidates by what the file is for -- a training directory outranks a neutral
one, which outranks an evaluation or benchmark one -- then names the file it
used and the ones it did not, reporting the disagreement rather than settling it
silently.

Author
------
Warith Harchaoui
"""

from __future__ import annotations

import re
from pathlib import Path

from .findings import WorkSizeCandidate
from .tables import (
    _CONFIG_READ_BYTES,
    CONFIG_FILE_PRECEDENCE,
    SIDE_ERRAND_DIRECTORIES,
    TRAINING_DIRECTORIES,
    WORK_SIZE_KEYS,
)
from .walking import _is_prose_line, _iter_source_files, is_test_path


def _purpose_rank(relative_path: str) -> int:
    """Return how far a file's directory is trusted to state the length of a run.

    Only directory names are read, never the file's own name: a repository that
    separates ``configs/train`` from ``configs/eval`` is saying which of the two a
    real run reads, and that statement is worth more than any guess from a stem.

    Parameters
    ----------
    relative_path : str
        Repository-relative path.

    Returns
    -------
    int
        ``0`` under a training directory, ``2`` under an evaluation, benchmark or
        example one, ``1`` everywhere else. Smaller means more trusted.

    Examples
    --------
    >>> _purpose_rank("configs/train/vitg14.yaml")
    0
    >>> _purpose_rank("configs/ssl_default.yaml")
    1
    >>> _purpose_rank("configs/eval/linear.yaml")
    2
    """
    directories = {part.lower() for part in Path(relative_path).parts[:-1]}
    if directories & TRAINING_DIRECTORIES:
        return 0
    if directories & SIDE_ERRAND_DIRECTORIES:
        return 2
    return 1


def _config_rank(relative_path: str) -> int:
    """Return how far a file is trusted to state the size of a run.

    Parameters
    ----------
    relative_path : str
        Repository-relative path.

    Returns
    -------
    int
        A smaller number means more trusted. Files not named in
        :data:`CONFIG_FILE_PRECEDENCE` rank after all of them.

    Examples
    --------
    >>> _config_rank("config.py") < _config_rank("train.py")
    True
    >>> _config_rank("some/other.py") == len(CONFIG_FILE_PRECEDENCE)
    True
    >>> _config_rank("tests/conftest.py") > _config_rank("some/other.py")
    True
    """
    lowered = relative_path.lower()
    # A suite states a size so that a test finishes quickly, which is the opposite
    # of what a real run does. It ranks below every file the workload owns, so it
    # only ever wins when the workload states no size at all.
    penalty = len(CONFIG_FILE_PRECEDENCE) + 1 if is_test_path(Path(relative_path)) else 0
    for rank, name in enumerate(CONFIG_FILE_PRECEDENCE):
        if lowered == name or lowered.endswith(f"/{name}") or f"/{name}/" in f"/{lowered}/":
            return rank + penalty
    return len(CONFIG_FILE_PRECEDENCE) + penalty


def find_work_size(
    root: Path,
) -> tuple[WorkSizeCandidate | None, tuple[WorkSizeCandidate, ...], tuple[str, ...]]:
    """Find every statement of how much work a whole run performs.

    Precedence is documented and applied in this order: the file's rank in
    :data:`CONFIG_FILE_PRECEDENCE` first, then the key's rank in
    :data:`WORK_SIZE_KEYS`, then the path alphabetically so the result does not
    depend on filesystem ordering. When two files state different sizes for the
    same key, that disagreement is returned rather than settled, because capping a
    measured slice against the wrong one is off by however much they differ.

    Parameters
    ----------
    root : pathlib.Path
        The repository root.

    Returns
    -------
    tuple
        The chosen candidate or ``None``, every candidate in precedence order, and
        a sentence for each disagreement found.

    Examples
    --------
    >>> import tempfile
    >>> with tempfile.TemporaryDirectory() as folder:
    ...     here = Path(folder)
    ...     _ = (here / "config.py").write_text("max_iters = 600000", encoding="utf-8")
    ...     _ = (here / "train.py").write_text("max_iters = 300", encoding="utf-8")
    ...     chosen, every, conflicts = find_work_size(here)
    ...     chosen.value, len(every), len(conflicts)
    (600000.0, 2, 1)
    """
    candidates: list[WorkSizeCandidate] = []
    for path in _iter_source_files(root):
        if path.suffix.lower() not in {".py", ".yaml", ".yml", ".json", ".toml", ".cfg", ".ini"}:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")[:_CONFIG_READ_BYTES]
        except OSError:
            continue
        relative = str(path.relative_to(root))
        lines = text.splitlines()
        for key in WORK_SIZE_KEYS:
            # The number may be written 600000, 600_000, or 6e5; stopping at the
            # mantissa would read 6e5 as six and cap the run at a millionth of
            # its size while still calling the figure file-sourced.
            pattern = re.compile(
                rf'(?<![\w.]){re.escape(key)}["\']?\s*[=:]\s*'
                r"([0-9][0-9_]*(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?)",
                re.IGNORECASE,
            )
            for line in lines:
                if _is_prose_line(line):
                    # A commented-out size is prose about the code. Letting it
                    # win the precedence contest is exactly the silent-cap
                    # failure this pass exists to prevent.
                    continue
                match = pattern.search(line)
                if not match:
                    continue
                value = float(match.group(1).replace("_", ""))
                if value > 0:
                    candidates.append(WorkSizeCandidate(key, value, f"{relative}::{key}"))
                break

    candidates.sort(
        key=lambda item: (
            _config_rank(item.source.split("::", 1)[0]),
            _purpose_rank(item.source.split("::", 1)[0]),
            WORK_SIZE_KEYS.index(item.key) if item.key in WORK_SIZE_KEYS else len(WORK_SIZE_KEYS),
            item.source,
        )
    )

    chosen = candidates[0] if candidates else None
    conflicts: list[str] = []
    # A suite states a small size so that a test finishes, and the workload states
    # the real one. That is not a disagreement, it is the two files doing their
    # jobs, and reporting it as one buries the disagreements that matter.
    from_workload = [
        candidate
        for candidate in candidates
        if not is_test_path(Path(candidate.source.split("::", 1)[0]))
    ]
    considered = from_workload or candidates
    by_key: dict[str, list[WorkSizeCandidate]] = {}
    for candidate in considered:
        by_key.setdefault(candidate.key, []).append(candidate)
    for key, group in by_key.items():
        values = {candidate.value for candidate in group}
        if len(values) > 1:
            listed = "; ".join(f"{item.source} says {item.value:g}" for item in group)
            # Only one candidate in the whole repository is actually used, and it
            # may well belong to another key. Saying "was used" of each key's own
            # front-runner would name a figure nothing read.
            if chosen is not None and chosen.key == key:
                outcome = f"{chosen.source} was used; check it is the one a real run reads."
            elif chosen is not None:
                outcome = (
                    f"{group[0].source} takes precedence among them, but none of them "
                    f"was used: the size this read went with is {chosen.source} "
                    f"({chosen.value:g})."
                )
            else:
                outcome = f"{group[0].source} takes precedence among them."
            conflicts.append(
                f"{key} is stated more than once and the statements disagree ({listed}). {outcome}"
            )

    return chosen, tuple(candidates), tuple(conflicts)
