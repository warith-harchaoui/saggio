"""
Write the library reference from the docstrings it documents.

Module summary
--------------
``docs/api.md`` is the one page a library caller reads to find out what
:mod:`saggio` exposes and what each name is for. Writing it by hand would mean
maintaining a second copy of every summary line, and a second copy is a copy that
drifts, so this script derives the page from the package itself: the names come
from ``__all__``, the headings come from the comments that already group
``__all__`` in ``saggio/__init__.py``, the signatures come from
:mod:`inspect`, and each one-line summary is the first line of the object's own
docstring.

``--check`` reports drift without writing anything, which is what the contract
test and continuous integration call, so a docstring edited without regenerating
the page fails the build instead of silently shipping a stale reference.

Usage example
-------------
>>> from docs.sync_api import render      # doctest: +SKIP
>>> render().startswith("# The library")  # doctest: +SKIP
True

Author
------
Warith Harchaoui
"""

from __future__ import annotations

import argparse
import inspect
import re
import sys
from pathlib import Path
from typing import Any, Final

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# The path insertion above is what makes this importable from a checkout.
import saggio

#: Where the generated page lives.
PAGE: Final[Path] = Path(__file__).resolve().parent / "api.md"

#: The heading each ``__all__`` group gets, keyed by the comment that opens it in
#: ``saggio/__init__.py``. A group whose comment is not listed here keeps the
#: comment itself as its heading, so adding a group does not need a change here.
_HEADINGS: Final[dict[str, str]] = {
    "The model and its rules.": "The model and its rules",
    "Facts about the world.": "Facts about the world",
    "Estimation.": "Estimation",
    "Reading and running a repository.": "Reading and running a repository",
    "The whole job.": "The whole job",
    "Reports.": "Reports",
}

#: The dunder names at the top of ``__all__``, which are metadata rather than API.
_METADATA: Final[tuple[str, ...]] = ("__version__", "__author__", "__email__")

#: What the page says before the tables.
_PREAMBLE: Final[str] = """# The library

Everything `import saggio` gives you, grouped the way `__all__` groups it. This
page is in English only, because it is the docstrings and the docstrings are in
English. [`LISEZMOI.md`](LISEZMOI.md) is the French map of the documentation.

**This page is generated.** The names come from `__all__`, the summaries are the
first line of each object's own docstring, and `docs/sync_api.py --check` fails
the build when the two have drifted. Edit the docstring, then run
`python docs/sync_api.py`.

The command line reaches nothing the library does not, so anything the `saggio`
command can do is reachable from here. [`../EXAMPLES.md`](../EXAMPLES.md) shows
these in use; the full parameter documentation is in the docstrings themselves,
which `help()` will show you.
"""


def groups() -> list[tuple[str, list[str]]]:
    """Return the public names, grouped as ``saggio/__init__.py`` groups them.

    The grouping is read from the source rather than restated, because the
    comments in ``__all__`` are already the author's own division of the surface
    and a second division would be one more thing to keep in step.

    Returns
    -------
    list of (str, list of str)
        A heading and its names, in the order ``__all__`` lists them. The
        metadata dunders are dropped.

    Examples
    --------
    >>> [heading for heading, _ in groups()][0]
    'The model and its rules'
    """
    source = Path(saggio.__file__).read_text(encoding="utf-8")
    block = source.split("__all__ = [", 1)[1].split("\n]", 1)[0]

    collected: list[tuple[str, list[str]]] = []
    heading = "Everything else"
    for line in block.splitlines():
        stripped = line.strip()
        comment = re.fullmatch(r"#\s*(.+)", stripped)
        if comment:
            heading = _HEADINGS.get(comment.group(1), comment.group(1).rstrip("."))
            continue
        name = re.fullmatch(r'"([^"]+)",', stripped)
        if not name or name.group(1) in _METADATA:
            continue
        if not collected or collected[-1][0] != heading:
            collected.append((heading, []))
        collected[-1][1].append(name.group(1))
    return collected


def _summary(obj: Any) -> str:
    """Return the first line of an object's docstring.

    Parameters
    ----------
    obj : Any
        Anything with a docstring.

    Returns
    -------
    str
        The summary line, or an empty string when there is none.

    Examples
    --------
    >>> _summary(saggio.compare)
    'Compare two cost models quantity by quantity.'
    """
    documentation = inspect.getdoc(obj) or ""
    return documentation.splitlines()[0].strip() if documentation else ""


def _constant(obj: Any) -> str:
    """Describe a constant by its value rather than by its type's docstring.

    :func:`inspect.getdoc` on a plain string returns the documentation of
    :class:`str`, which tells a reader looking up ``MEASURED`` nothing at all.
    What they want is the value, and for a collection, what is in it.

    Parameters
    ----------
    obj : Any
        The constant.

    Returns
    -------
    str
        A short rendering of the value.

    Examples
    --------
    >>> _constant("measured")
    "`'measured'`"
    >>> _constant({"minimal": "a", "annotated": "b"})
    '`minimal`, `annotated`'
    """
    if isinstance(obj, dict):
        return ", ".join(f"`{key}`" for key in obj)
    if isinstance(obj, (tuple, list, frozenset, set)):
        members = [getattr(item, "key", item) for item in obj]
        return ", ".join(f"`{member}`" for member in members)
    return f"`{obj!r}`"


def _entry(name: str) -> tuple[str, str]:
    """Return how a public name is spelled on the page, and what it is for.

    Parameters
    ----------
    name : str
        A name from ``__all__``.

    Returns
    -------
    tuple of (str, str)
        The spelling, with a signature when the object is callable, and the
        summary line. A constant is described by its value, because a reader
        looking up ``MEASURED`` wants to see ``measured``.

    Examples
    --------
    >>> _entry("MEASURED")
    ('`MEASURED`', "`'measured'`")
    """
    obj = getattr(saggio, name)
    if inspect.isclass(obj):
        return f"`{name}`", _summary(obj)
    if inspect.isfunction(obj):
        try:
            signature = str(inspect.signature(obj))
        except (TypeError, ValueError):
            signature = "(...)"
        return f"`{name}{signature}`", _summary(obj)
    return f"`{name}`", _constant(obj)


def render() -> str:
    """Render the whole page.

    Returns
    -------
    str
        Markdown, ending in a newline.

    Examples
    --------
    >>> render().startswith("# The library")
    True
    """
    lines = [_PREAMBLE]
    for heading, names in groups():
        lines.append(f"\n## {heading}\n")
        lines.append("| Name | What it is for |")
        lines.append("|---|---|")
        for name in names:
            spelling, summary = _entry(name)
            lines.append(f"| {spelling.replace('|', chr(92) + '|')} | {summary} |")
        lines.append("")
    lines.append(
        "---\n\nGenerated from the docstrings by `docs/sync_api.py`. "
        f"saggio {saggio.__version__}.\n"
    )
    return "\n".join(lines)


def out_of_date() -> bool:
    """Return whether the page on disk differs from what the package would produce.

    Returns
    -------
    bool
        ``True`` when the page is missing or stale.

    Examples
    --------
    >>> isinstance(out_of_date(), bool)
    True
    """
    return not PAGE.exists() or PAGE.read_text(encoding="utf-8") != render()


def main(argv: list[str] | None = None) -> int:
    """Run the script.

    Parameters
    ----------
    argv : list of str or None
        Arguments, without the program name.

    Returns
    -------
    int
        ``0`` when the page agrees with the package, or was made to. ``1`` under
        ``--check`` when it does not.

    Examples
    --------
    >>> isinstance(main(["--check"]), int)
    True
    """
    parser = argparse.ArgumentParser(description="Write docs/api.md from the docstrings.")
    parser.add_argument(
        "--check",
        action="store_true",
        help="report drift and exit non-zero, without writing anything",
    )
    args = parser.parse_args(argv)

    if args.check:
        if out_of_date():
            print("docs/api.md is out of date; run `python docs/sync_api.py`", file=sys.stderr)
            return 1
        return 0

    if out_of_date():
        PAGE.write_text(render(), encoding="utf-8")
        print(f"wrote {PAGE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
