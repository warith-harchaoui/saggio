"""Naming a command and a repository, in words a report can print.

Module summary
--------------
Small, pure, and used by everything else: what to call a repository taken from
a URL, how to render the command that was timed, and the sentence that says
what the audit found before any number is quoted.

Author
------
Warith Harchaoui
"""

from __future__ import annotations

from pathlib import Path

from ..analyze.static import (
    RepositoryReading,
)


def describe_command(command: tuple[str, ...]) -> str:
    """Render a command for a note, short enough to read and free of a home path.

    The full path of a Python interpreter is most of the line and none of the
    information, and a model that will be committed and shared should not carry
    somebody's home directory in it.

    Parameters
    ----------
    command : tuple of str
        The command as it was run.

    Returns
    -------
    str
        A readable one-line form.

    Examples
    --------
    >>> describe_command(("/opt/conda/bin/python", "/repo/train.py", "--max_iters", "600"))
    'python train.py --max_iters 600'
    >>> describe_command(())
    ''
    """
    if not command:
        return ""
    parts = [Path(command[0]).name]
    for part in command[1:]:
        # Only turn something that looks like a path into a basename; a flag or a
        # value would be unrecognisable without it.
        parts.append(Path(part).name if "/" in part or "\\" in part else part)
    return " ".join(parts)


def _repository_summary(reading: RepositoryReading) -> str:
    """Describe a repository for the local model, in prose and without numbers.

    Parameters
    ----------
    reading : RepositoryReading
        The static reading.

    Returns
    -------
    str
        A short description: languages, frameworks, entry point, tests.

    Examples
    --------
    >>> "Languages" in _repository_summary(RepositoryReading(root=Path(".")))
    True
    """
    lines = [
        f"Name: {reading.root.name}",
        f"Languages: {', '.join(reading.languages) or 'none detected'}",
        f"Frameworks: {', '.join(reading.frameworks) or 'none detected'}",
        f"Archetype from filenames: {reading.archetype}",
        f"Entry point: {reading.entrypoint or 'none found'}",
        f"Has a test suite: {reading.has_tests}",
    ]
    if reading.services:
        lines.append(f"Paid services called: {', '.join(hit.key for hit in reading.services)}")
    return "\n".join(lines)


def repository_name(url: str) -> str:
    """Return the repository's own name, as its clone URL spells it.

    Parameters
    ----------
    url : str
        A git URL, in any of the spellings git itself accepts.

    Returns
    -------
    str
        The last path segment without its ``.git`` suffix, or ``"repository"``
        when the URL carries nothing usable.

    Examples
    --------
    >>> repository_name("https://github.com/warith-harchaoui/saggio")
    'saggio'
    >>> repository_name("https://gitlab.com/gitlab-org/gitlab-runner.git")
    'gitlab-runner'
    >>> repository_name("git@github.com:someone/their-project.git")
    'their-project'
    >>> repository_name("https://example.invalid/")
    'repository'
    >>> repository_name("https://git.example.org/team/sub/group/thing.git/")
    'thing'
    """
    # Drop the scheme first, so the "//" in "https://" cannot be mistaken for a
    # path separator and leave an empty segment behind.
    without_scheme = url.split("://", 1)[-1]
    # A scp-style address (git@host:owner/name) puts a colon where a slash would
    # otherwise be, so it separates here exactly as a slash does.
    # "." and ".." are dropped along with empty segments: the result becomes a
    # directory name under a temp folder, and a ".." there would point the
    # clone target outside it.
    segments = [
        part for part in without_scheme.replace(":", "/").split("/") if part not in ("", ".", "..")
    ]
    # The first segment is the host. A URL that stops there names no repository,
    # and answering with the hostname would put "example.invalid" in the model
    # where a project name belongs.
    if len(segments) < 2:
        return "repository"
    last = segments[-1]
    if last.endswith(".git"):
        last = last[: -len(".git")]
    return last or "repository"
