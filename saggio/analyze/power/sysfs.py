"""Reading a number out of the kernel, or admitting it could not.

Module summary
--------------
Two readers, each returning ``None`` rather than a zero when the file is absent
or unreadable. A zero would be a measurement saying the machine drew nothing,
which is exactly the invented number this package exists to refuse.

Author
------
Warith Harchaoui
"""

from __future__ import annotations

from pathlib import Path


def _read_integer(path: Path) -> int | None:
    """Return the integer a sysfs file holds, or ``None``.

    Parameters
    ----------
    path : pathlib.Path
        The file to read.

    Returns
    -------
    int or None
        Its contents as an integer, or ``None`` when it is absent, unreadable,
        or not a number.

    Examples
    --------
    >>> _read_integer(Path("/nonexistent/energy_uj")) is None
    True
    """
    try:
        return int(path.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return None


def _read_text(path: Path) -> str | None:
    """Return a sysfs file's contents, stripped, or ``None``.

    Parameters
    ----------
    path : pathlib.Path
        The file to read.

    Returns
    -------
    str or None
        Its contents without surrounding whitespace, or ``None`` when it is
        absent or unreadable.

    Examples
    --------
    >>> _read_text(Path("/nonexistent/name")) is None
    True
    """
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError:
        return None
