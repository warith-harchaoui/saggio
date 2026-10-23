"""
Word and PDF, for the reader who did not choose the format.

Module summary
--------------
Sometimes the report has to go into a document nobody would have picked: a
compliance annexe, a client deliverable, a slide deck's appendix. This module
hands the Markdown report to ``md2star``, which wraps Pandoc with branded
templates, and gets back a ``.docx`` or a ``.pdf``.

The dependency is deliberately external and deliberately optional. Pandoc and a
LaTeX toolchain are large, they are not needed by anybody using the library or the
command line, and a package that installed them to render a table would be
mis-weighted. When ``md2star`` is absent, this says so in a sentence that names
what to install, rather than raising something a caller has to decode.

Usage example
-------------
>>> from saggio.report.office import md2star_available
>>> isinstance(md2star_available(), bool)
True

Author
------
Warith Harchaoui
"""

from __future__ import annotations

import shutil
import subprocess
from datetime import date
from pathlib import Path
from typing import Any, Final

import os_helper as osh

from ..model.cost_model import CostModel
from .markdown import render_markdown

#: The formats this module can produce, and the wrapper command for each.
OFFICE_FORMATS: Final[dict[str, str]] = {"docx": "md2docx", "pdf": "md2pdf"}

#: The command that must be on the path for any of this to work.
MD2STAR_COMMAND: Final[str] = "md2star"

#: How long a conversion may take. Pandoc with a LaTeX engine is slow on a first
#: run because it builds font caches, so the limit is generous.
_CONVERSION_TIMEOUT_SECONDS: Final[float] = 600.0

#: Who the document says produced it. A cost model is written by a person and
#: argued over in review; the Word file and the PDF are produced by this program
#: from that model, and the title block should say which of the two the reader
#: is holding.
DEFAULT_AUTHOR: Final[str] = "saggio"

#: Passed to ``md2star`` when a caller asks for no network. Since its 2.5.0 the
#: wrapper fetches a branded template over HTTP whenever no reference document
#: is given, which is a pleasant default and a surprising one: a render can fail
#: on a train, and two renders of one model can differ because a template moved.
#: Neither is a defect, but neither should be undeclared.
_OFFLINE_ARGUMENTS: Final[tuple[str, ...]] = ("--offline", "--no-remote-templates")

#: How much wider than every other column put together a cell has to be before
#: its column is lifted out of the table. Three times is deliberately far past
#: the point where the layout hurts: the shipped report's cost table had a notes
#: column at 79% against a dimension column at 3%, a ratio near twenty, and the
#: tables that read fine sit under two. Nothing in between is touched.
_PROSE_COLUMN_RATIO: Final[float] = 3.0

#: A column of one-word cells is never prose, however lopsided the table.
_PROSE_MINIMUM_CHARACTERS: Final[int] = 60


#: What to tell a caller who does not have the toolchain installed.
_MISSING_MESSAGE: Final[str] = (
    "Word and PDF output needs md2star, which is not on the PATH. Install it with "
    "`pip install md2star` and make sure Pandoc is available, or render Markdown or "
    "HTML instead, which need nothing extra."
)


def _lift_prose_columns(markdown: str) -> str:
    """Move a table's column of sentences out from underneath it.

    The converter sizes a table's columns by how much text each one holds, so
    one cell carrying three sentences squeezes every other column to about a
    character's width. In the shipped report that was not a cosmetic loss: the
    cost table's own figures came out as vertical stacks of single letters, so
    ``5.585e-08 USD`` was unreadable in both the Word file and the Portable
    Document Format one. Measured on that table, the notes column took 79% of
    the width and the dimension column 3%.

    The dashes a pipe table can carry to request relative widths do not help:
    the same table converts to the same widths whether they are proportional or
    all equal, because the converter computes its own. So the fix is on this
    side, and it is the one the content wanted anyway -- a column of sentences
    is a list wearing a table.

    Only the office path calls this. The Markdown a reader opens on a forge
    renders that column perfectly well, and the HTML report has its own
    renderer, so neither is touched.

    Parameters
    ----------
    markdown : str
        The report, as :func:`~saggio.report.markdown.render_markdown` wrote it.

    Returns
    -------
    str
        The same report, with any prose column emitted as labelled lines under
        its table rather than inside it.

    Examples
    --------
    >>> table = chr(10).join([
    ...     "| Dimension | Per unit | Notes |",
    ...     "|---|---|---|",
    ...     "| Money | 5.6e-08 USD | " + "Facility energy times the price. " * 3 + "|",
    ... ])
    >>> lifted = _lift_prose_columns(table)
    >>> "| Dimension | Per unit |" in lifted
    True
    >>> "**Money** — Facility energy" in lifted
    True

    A table whose columns are all short keeps every one of them:

    >>> short = chr(10).join(["| a | b |", "|---|---|", "| 1 | 2 |"])
    >>> _lift_prose_columns(short) == short
    True
    """
    out: list[str] = []
    block: list[str] = []

    def flush() -> None:
        out.extend(_rewrite_table(block) if len(block) >= 2 else block)
        block.clear()

    fenced = False
    for line in markdown.split("\n"):
        if line.startswith("```"):
            fenced = not fenced
        if not fenced and line.startswith("|") and line.endswith("|"):
            block.append(line)
            continue
        flush()
        out.append(line)
    flush()
    return "\n".join(out)


def _cells(row: str) -> list[str]:
    """Split one pipe-table row into its cells."""
    return [cell.strip() for cell in row.strip().strip("|").split("|")]


def _rewrite_table(block: list[str]) -> list[str]:
    """Return one table, with its prose column lifted out if it has one."""
    header = _cells(block[0])
    rows = [_cells(row) for row in block[2:]]
    if len(header) < 3 or not rows or any(len(row) != len(header) for row in rows):
        return list(block)

    widths = [max(len(row[column]) for row in rows) for column in range(len(header))]
    widest = max(range(len(widths)), key=lambda column: widths[column])
    others = sum(widths) - widths[widest]
    if widths[widest] < _PROSE_MINIMUM_CHARACTERS:
        return list(block)
    if others and widths[widest] < _PROSE_COLUMN_RATIO * others:
        return list(block)

    keep = [column for column in range(len(header)) if column != widest]
    kept = ["| " + " | ".join(header[column] for column in keep) + " |"]
    kept.append("|" + "|".join(["---"] * len(keep)) + "|")
    kept.extend("| " + " | ".join(row[column] for column in keep) + " |" for row in rows)

    # The lifted text keeps its row's first cell as a label, so a reader can
    # still tell which line of the table each sentence belongs to.
    lifted = [""]
    for row in rows:
        if row[widest]:
            lifted.append(f"**{row[0]}** — {row[widest]}")
            lifted.append("")
    return kept + lifted[:-1] if len(lifted) > 1 else list(block)


def md2star_available() -> bool:
    """Return whether the conversion toolchain is installed.

    Returns
    -------
    bool
        ``True`` when ``md2star`` is on the path.

    Examples
    --------
    >>> isinstance(md2star_available(), bool)
    True
    """
    return shutil.which(MD2STAR_COMMAND) is not None


def _stamp(generated: date | str | None) -> str:
    """Return the date the document says it was produced on.

    The body of the report already carries *Last updated*, which is a fact about
    the **model**: when somebody last changed a number in it. This is a fact
    about the **document**: when this particular file was made. A PDF produced
    today from a model nobody has touched since June should say both, and saying
    only one of them is how a stale figure acquires a fresh-looking date.

    Parameters
    ----------
    generated : datetime.date or str or None
        The date to stamp. A string is passed through untouched, so a caller who
        wants ``2026-Q2`` or ``submitted 14 March`` gets exactly that. ``None``
        stamps today.

    Returns
    -------
    str
        What to hand to the converter.

    Examples
    --------
    >>> import datetime
    >>> _stamp(datetime.date(2026, 6, 21))
    '2026-06-21'
    >>> _stamp("submitted 14 March")
    'submitted 14 March'
    >>> _stamp(None) == datetime.date.today().isoformat()
    True
    """
    if generated is None:
        return date.today().isoformat()
    if isinstance(generated, str):
        return generated
    return generated.isoformat()


def render_office(
    model: CostModel | dict[str, Any],
    output: str | Path,
    *,
    output_format: str = "docx",
    reference_document: str | Path | None = None,
    author: str | None = DEFAULT_AUTHOR,
    generated: date | str | None = None,
    offline: bool = False,
) -> Path:
    """Render a cost model to Word or PDF.

    Parameters
    ----------
    model : CostModel or dict
        The model.
    output : str or pathlib.Path
        Where to write the document.
    output_format : str, optional
        ``docx`` or ``pdf``.
    reference_document : str or pathlib.Path or None, optional
        A ``.docx`` whose styles the output should follow.
    author : str or None, optional
        Who the title block names as having produced the document. Defaults to
        the program, because the program is what produced it: a reader holding
        the PDF should be able to tell it was generated rather than written.
        Pass ``None`` to leave the line out.
    generated : datetime.date or str or None, optional
        The date the document states it was made on, which is **not** the date
        the model was last changed -- see :func:`_stamp`. Defaults to today.
    offline : bool, optional
        Refuse every network-touching step of the conversion. The converter
        otherwise fetches a branded template over HTTP when no reference
        document is given, which makes a render fail without a connection and
        lets two renders of one model differ.

    Returns
    -------
    pathlib.Path
        The document written.

    Raises
    ------
    ValueError
        If the format is not one this module produces.
    RuntimeError
        If ``md2star`` is not installed, or the conversion fails, with the reason.

    Examples
    --------
    >>> render_office({}, "out.odt", output_format="odt")
    Traceback (most recent call last):
        ...
    ValueError: Unknown output format 'odt'. Available: docx, pdf.
    """
    if output_format not in OFFICE_FORMATS:
        available = ", ".join(sorted(OFFICE_FORMATS))
        raise ValueError(f"Unknown output format {output_format!r}. Available: {available}.")
    if not md2star_available():
        raise RuntimeError(_MISSING_MESSAGE)

    target = Path(output)
    osh.make_directory(str(target.parent))

    with osh.temporary_filename(suffix=".md", delete=True) as scratch:
        Path(scratch).write_text(_lift_prose_columns(render_markdown(model)), encoding="utf-8")
        command = [MD2STAR_COMMAND, output_format, scratch, "--output", str(target)]
        if author:
            command += ["--author", author]
        command += ["--date", _stamp(generated)]
        if reference_document is not None:
            command += ["--reference-doc", str(reference_document)]
        if offline:
            command += list(_OFFLINE_ARGUMENTS)
        try:
            completed = subprocess.run(  # noqa: S603 - a list, never a shell.
                command,
                capture_output=True,
                text=True,
                timeout=_CONVERSION_TIMEOUT_SECONDS,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(
                f"md2star did not produce the {output_format} within "
                f"{_CONVERSION_TIMEOUT_SECONDS:g} seconds."
            ) from exc
    if completed.returncode != 0:
        # The failure message must not be able to fail: whitespace-only output
        # strips to nothing, and indexing an empty tail crashed the messenger.
        tail = (completed.stderr or completed.stdout or "").strip().splitlines()[-1:]
        detail = tail[0] if tail else "no output"
        raise RuntimeError(f"md2star could not produce the {output_format}: {detail}")
    return target
