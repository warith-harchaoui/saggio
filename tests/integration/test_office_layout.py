"""The Word file a reader opens, measured rather than assumed.

Every other gate in this repository reads a *source*: the Markdown, the YAML,
the docstrings, the report's JavaScript. None of them opens the document the
converter produced, and that is how the cost table came to be unreadable in
both office formats for as long as those formats have existed.

The failure was not subtle once seen. The converter sizes a table's columns by
how much text each one holds, so a notes column carrying three sentences took
79% of the width and left the dimension column 3%. At that width the figures
came out one character per line: ``5.585e-08 USD`` ran down the page. Two of
the report's eight tables were in that state, and nothing noticed, because
nothing had ever looked at the file.

A ``.docx`` is a zip of XML, and the column widths are in it as plain
integers. So this is fifteen lines of stdlib rather than a rendering
comparison, and it runs wherever the converter does.

What this cannot see: whether a value wraps *inside* a column that is wide
enough for the table but narrow for that value. The converter sizes some
columns below their own longest word, which is a defect in md2star rather than
here; the residual is recorded in the office module rather than silently
tolerated.
"""

from __future__ import annotations

import re
import zipfile
from pathlib import Path

import pytest

from saggio.model import CostModel
from saggio.report.office import md2star_available, render_office

ROOT = Path(__file__).resolve().parents[2]

#: The share of a table's width below which a column has stopped being
#: readable. At 3% the report's dimension column was rendering one letter per
#: line; at 6% the tables that read fine were comfortable. Five sits between
#: them, close enough to the failure to catch a return of it and far enough
#: from the healthy tables not to fire on one.
_COLLAPSED_SHARE: float = 0.05

#: A model with the shape that caused the defect: several rows of short
#: figures, and one column carrying the long provenance sentences a real audit
#: writes. Built here rather than read from ``examples/`` so that tidying an
#: example cannot quietly disarm this -- but it has to be *as wordy as a real
#: report*, which the first version of it was not: at three short sentences the
#: table reached 9% and never collapsed, so the gate passed either way. The
#: companion test below measures that, rather than trusting this comment.
_NOTE = (
    "Facility energy times the price per kilowatt-hour, with hardware and "
    "staff excluded from the figure. Timed with saggio measure over fifty "
    "units of work inside one interpreter, so that Python's start-up, which "
    "is not the work, is not charged to it. Across five runs the figure "
    "ranged by four per cent of its median, and a range from five runs is not "
    "a bound: the next run lands outside it about one time in three."
)
_WORDY = CostModel.from_mapping(
    {
        "schema_version": "2.0",
        "date_updated": "2026-10-03",
        "unit_of_work": {"name": "one request served", "status": "estimated"},
        "deployment": {"provider": "on-prem", "country": "FR"},
        "scenarios": [
            {
                "name": "as-audited",
                "costs": {
                    "money": {
                        "value": 5.585e-08,
                        "unit": "USD",
                        "status": "estimated",
                        "notes": _NOTE,
                    },
                    "carbon": {
                        "value": 8.337e-06,
                        "unit": "gCO2e",
                        "status": "estimated",
                        "notes": "Facility energy times the grid carbon "
                        "intensity, operating emissions only. " + _NOTE,
                    },
                    "energy": {
                        "value": 2.024e-07,
                        "unit": "kWh",
                        "status": "estimated",
                        "notes": "Machine energy times power usage "
                        "effectiveness: what the building draws. " + _NOTE,
                    },
                    "time": {
                        "value": 27.18,
                        "unit": "ms",
                        "status": "measured",
                        "notes": _NOTE,
                    },
                },
            }
        ],
    }
)


def _column_shares(document: Path) -> list[tuple[int, list[float]]]:
    """Return each table's column widths, as shares of that table's width."""
    xml = zipfile.ZipFile(document).read("word/document.xml").decode("utf-8")
    tables = []
    for index, grid in enumerate(re.findall(r"<w:tblGrid>(.*?)</w:tblGrid>", xml, re.S)):
        widths = [int(value) for value in re.findall(r'w:w="(\d+)"', grid)]
        total = sum(widths)
        if total:
            tables.append((index, [width / total for width in widths]))
    return tables


@pytest.mark.skipif(
    not md2star_available(),
    reason="md2star is not installed, so no document is produced to measure",
)
def test_no_column_of_the_word_file_is_squeezed_out_of_readability(tmp_path: Path) -> None:
    """Open the file a reader opens, and measure what they would see.

    This is the only check in the repository that reads a produced document
    rather than a source. It exists because the defect it guards against was
    visible from the first day to anybody who opened the PDF, and nobody had.
    """
    document = tmp_path / "cost.docx"
    render_office(_WORDY, document, output_format="docx")

    collapsed = [
        f"table {index}: {[round(share * 100) for share in shares]}%"
        for index, shares in _column_shares(document)
        if len(shares) > 1 and min(shares) < _COLLAPSED_SHARE
    ]
    assert not collapsed, (
        f"a column of the Word file is under {_COLLAPSED_SHARE:.0%} of its "
        f"table and will render a character at a time: {collapsed}. The "
        "converter sizes columns by their content, so one cell of prose "
        "squeezes the figures beside it; saggio.report.office lifts such a "
        "column out, and this says it stopped."
    )


def test_this_file_s_own_model_would_still_collapse_without_the_fix() -> None:
    """The gate above is only worth running if its model can still fail it.

    The first version of this model was three short sentences per note, and
    the table it produced reached 9% at its narrowest -- comfortably above the
    threshold, so the gate passed whether or not the fix was in place. That is
    a test that looks like a test. This one measures the Markdown instead of
    the document, so it costs nothing and needs no converter: if lifting is a
    no-op on this model, the gate has gone vacuous and says so.
    """
    from saggio.report.markdown import render_markdown
    from saggio.report.office import _lift_prose_columns

    rendered = render_markdown(_WORDY)
    assert _lift_prose_columns(rendered) != rendered, (
        "this file's model no longer has a column long enough to lift, so the "
        "layout gate would pass with or without the fix. Make the notes wordier."
    )


@pytest.mark.skipif(
    not md2star_available(),
    reason="md2star is not installed, so no document is produced to measure",
)
def test_the_lifted_prose_is_in_the_document_rather_than_dropped(tmp_path: Path) -> None:
    """Moving a column out must not lose it.

    A fix for the layout that quietly deleted the provenance would be worse
    than the layout, and both look fine in a column-width measurement.
    """
    document = tmp_path / "cost.docx"
    render_office(_WORDY, document, output_format="docx")
    xml = zipfile.ZipFile(document).read("word/document.xml").decode("utf-8")
    text = re.sub(r"<[^>]+>", "", xml)

    for sentence in ("hardware and staff excluded", "operating emissions only"):
        assert sentence in text, (
            f"{sentence!r} is in the model's notes and not in the document. "
            "Lifting a prose column has to move it, never drop it."
        )
