"""Which languages a repository is written in.

Module summary
--------------
Counted by file, and broad on purpose: a mixed repository should be described as
mixed rather than reduced to whatever it has most of.

Author
------
Warith Harchaoui
"""

from __future__ import annotations

from pathlib import Path

from .tables import LANGUAGE_BY_EXTENSION
from .walking import _iter_source_files


def detect_languages(root: Path) -> dict[str, int]:
    """Count source files per language, most files first.

    Parameters
    ----------
    root : pathlib.Path
        The repository root.

    Returns
    -------
    dict
        Language name to file count, in descending order of count.

    Examples
    --------
    >>> "Python" in detect_languages(Path("."))
    True
    """
    counts: dict[str, int] = {}
    for path in _iter_source_files(root):
        language = LANGUAGE_BY_EXTENSION.get(path.suffix.lower())
        if language:
            counts[language] = counts.get(language, 0) + 1
    return dict(sorted(counts.items(), key=lambda item: (-item[1], item[0])))
