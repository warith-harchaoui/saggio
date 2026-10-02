"""Reading a repository once, and holding what was found.

Module summary
--------------
The orchestration: every detector in turn, into one record that says what was
established and what it rests on.

Author
------
Warith Harchaoui
"""

from __future__ import annotations

from pathlib import Path

import os_helper as osh

from .archetype import detect_archetype, detect_frameworks
from .calls import detect_models, detect_services
from .findings import RepositoryReading
from .languages import detect_languages
from .running import detect_tests, find_entrypoint
from .tables import _TRAINING_KEYS
from .worksize import find_work_size


def read_repository(path: str | Path, *, overlay: Path | None = None) -> RepositoryReading:
    """Read a repository and return everything the static pass established.

    Parameters
    ----------
    path : str or pathlib.Path
        The repository root.
    overlay : pathlib.Path or None, optional
        Catalogue overlay directory, for service detection.

    Returns
    -------
    RepositoryReading
        What was found.

    Raises
    ------
    AssertionError
        If the path is not a directory, reported through ``os_helper.check``.

    Examples
    --------
    >>> read_repository(".").source_files > 0
    True
    """
    root = Path(path).resolve()
    osh.check(osh.dir_exists(str(root)), f"Not a directory: {root}")

    languages = detect_languages(root)
    chosen, candidates, conflicts = find_work_size(root)
    has_tests, test_command = detect_tests(root)
    archetype = detect_archetype(root, languages)
    if archetype == "unknown" and chosen is not None and chosen.key in _TRAINING_KEYS:
        archetype = "training"

    for sentence in conflicts:
        osh.warning(sentence)

    frameworks, frameworks_in_suite_only = detect_frameworks(root)

    return RepositoryReading(
        root=root,
        languages=languages,
        archetype=archetype,
        frameworks=frameworks,
        frameworks_in_suite_only=frameworks_in_suite_only,
        work_size=chosen,
        work_size_candidates=candidates,
        work_size_conflicts=conflicts,
        services=detect_services(root, overlay=overlay),
        models=detect_models(root),
        has_tests=has_tests,
        test_command=test_command,
        entrypoint=find_entrypoint(root),
        source_files=sum(languages.values()),
    )
