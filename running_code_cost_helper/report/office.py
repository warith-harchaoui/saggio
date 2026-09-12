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
>>> from running_code_cost_helper.report.office import md2star_available
>>> isinstance(md2star_available(), bool)
True

Author
------
Warith Harchaoui
"""

from __future__ import annotations

import shutil
import subprocess
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


def render_office(
    model: CostModel | dict[str, Any],
    output: str | Path,
    *,
    output_format: str = "docx",
    reference_document: str | Path | None = None,
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
        if reference_document is not None:
            command += ["--reference-doc", str(reference_document)]
        completed = subprocess.run(  # noqa: S603 - a list, never a shell.
            command,
            capture_output=True,
            text=True,
            timeout=_CONVERSION_TIMEOUT_SECONDS,
            check=False,
        )
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "no output").strip().splitlines()[-1:]
        raise RuntimeError(f"md2star could not produce the {output_format}: {detail[0]}")
    return target
