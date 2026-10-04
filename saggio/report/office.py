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

#: What to tell a caller who does not have the toolchain installed.
_MISSING_MESSAGE: Final[str] = (
    "Word and PDF output needs md2star, which is not on the PATH. Install it with "
    "`pip install md2star` and make sure Pandoc is available, or render Markdown or "
    "HTML instead, which need nothing extra."
)


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
        Path(scratch).write_text(render_markdown(model), encoding="utf-8")
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
