"""Word and PDF output, on a machine where the converter is a stand-in.

Why this file exists
--------------------
Everything in this module that is not a one-line guard happens around a
subprocess: a Markdown file written to a scratch path, ``md2star`` invoked on
it, and whatever it says afterwards turned into either a file or an error a
person can act on. None of that runs unless md2star and Pandoc are installed,
so on most machines -- and on the cloud runner continuous integration uses --
the whole conversion was never executed.

Nothing here mocks `subprocess`. A stand-in ``md2star`` is written: a real
executable, taking the real flags, writing a real file or failing the way the
real one fails. What is being tested is what this module does with the answer,
which is the half that can be wrong.

Author
------
Warith Harchaoui
"""

from __future__ import annotations

import stat
import sys
from datetime import date
from pathlib import Path

import pytest

from saggio.model import CostModel
from saggio.report.markdown import render_markdown
from saggio.report.office import DEFAULT_AUTHOR, _lift_prose_columns, render_office

#: A model small enough to read and complete enough to render.
MODEL = CostModel.from_mapping(
    {
        "schema_version": "2.0",
        "date_updated": "2026-10-03",
        "unit_of_work": {"name": "one request", "status": "estimated"},
        "deployment": {"provider": "on-prem", "country": "FR"},
    }
)

#: A converter that behaves the way md2star behaves: it takes a format, an input
#: path and `--output`, writes something there, and says so on its way out.
STAND_IN = """\
#!{python}
import pathlib, sys, time
argv = sys.argv[1:]
time.sleep({delay})
if {code} == 0:
    target = argv[argv.index("--output") + 1]
    pathlib.Path(target).write_bytes({payload!r})
    # The real one records what it was asked to do, including the reference
    # document when one was given, which is how the test below sees the flag.
    pathlib.Path(target + ".argv").write_text("\\n".join(argv), encoding="utf-8")
    # And a copy of the Markdown it was handed, because the scratch file is
    # deleted on the way out and what is *in* it is half of this module's job.
    pathlib.Path(target + ".md").write_text(
        pathlib.Path(argv[1]).read_text(encoding="utf-8"), encoding="utf-8"
    )
sys.stderr.write({stderr!r})
sys.exit({code})
"""


def stand_in_md2star(
    tmp_path: Path,
    *,
    code: int = 0,
    stderr: str = "",
    delay: float = 0.0,
    payload: bytes = b"PK\\x03\\x04 a document",
) -> str:
    """Write an executable that converts the way md2star converts.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Where to write it.
    code : int, optional
        Exit status. Non-zero is a conversion that failed.
    stderr : str, optional
        What it complains about on the way out.
    delay : float, optional
        Seconds to take, for the timeout.
    payload : bytes, optional
        What it writes to the output path.

    Returns
    -------
    str
        The path to the executable.
    """
    script = tmp_path / "md2star"
    script.write_text(
        STAND_IN.format(
            python=sys.executable, code=code, stderr=stderr, delay=delay, payload=payload
        ),
        encoding="utf-8",
    )
    script.chmod(script.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    return str(script)


def point_at(monkeypatch: pytest.MonkeyPatch, path: str) -> None:
    """Point the converter at this tool, and make it findable."""
    import saggio.report.office as office

    monkeypatch.setattr(office, "MD2STAR_COMMAND", path)
    monkeypatch.setattr(office.shutil, "which", lambda _name: path)


# --- The two guards before anything is launched --------------------------------


def test_a_format_this_module_does_not_produce_is_refused() -> None:
    with pytest.raises(ValueError, match="Unknown output format"):
        render_office(MODEL, "out.odt", output_format="odt")


def test_without_the_converter_the_error_says_how_to_get_it(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A missing dependency is not a bug report, it is an instruction.

    The message has to name the thing, the way to install it, and the two
    formats that need nothing extra -- otherwise somebody without Pandoc is
    simply stuck.
    """
    import saggio.report.office as office

    monkeypatch.setattr(office.shutil, "which", lambda _name: None)
    with pytest.raises(RuntimeError) as raised:
        render_office(MODEL, tmp_path / "out.docx", output_format="docx")
    message = str(raised.value)
    assert "md2star" in message
    assert "pip install md2star" in message
    assert "Markdown or HTML" in message


# --- The conversion itself ------------------------------------------------------


@pytest.mark.parametrize("output_format", ["docx", "pdf"])
def test_a_conversion_that_works_leaves_the_file_where_it_was_asked_to(
    output_format: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    point_at(monkeypatch, stand_in_md2star(tmp_path))
    target = tmp_path / "reports" / f"cost.{output_format}"
    written = render_office(MODEL, target, output_format=output_format)
    assert written == target
    assert target.is_file()
    assert target.read_bytes().startswith(b"PK")


def test_the_directory_is_made_rather_than_demanded(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Asking somebody to mkdir before a render would be a worse tool.
    point_at(monkeypatch, stand_in_md2star(tmp_path))
    target = tmp_path / "a" / "b" / "c" / "cost.docx"
    render_office(MODEL, target, output_format="docx")
    assert target.is_file()


def test_the_converter_is_given_the_rendered_markdown_not_the_model(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The scratch file is the report, and it is cleaned up afterwards."""
    point_at(monkeypatch, stand_in_md2star(tmp_path))
    target = tmp_path / "cost.docx"
    render_office(MODEL, target, output_format="docx")
    argv = (tmp_path / "cost.docx.argv").read_text(encoding="utf-8").splitlines()
    assert argv[0] == "docx"
    scratch = Path(argv[1])
    assert scratch.suffix == ".md"
    assert not scratch.exists(), "the scratch Markdown was left behind"


def test_a_column_of_sentences_does_not_squeeze_the_figures_out_of_a_table() -> None:
    """The defect that made both office formats unreadable, pinned.

    The converter sizes a table's columns by how much text each holds, so a
    notes column carrying three sentences per row took 79% of the width and
    left the dimension column 3%. At that width the figures came out one
    character per line: "5.585e-08 USD" ran down the page. Nothing caught it
    because nothing had ever rendered the Word file and looked at it.
    """
    prose = "Facility energy times the price per kilowatt-hour, staff excluded. " * 2
    table = "\n".join(
        [
            "| Dimension | Per unit | Status | Notes |",
            "|---|---|---|---|",
            f"| Money | 5.585e-08 USD | estimated | {prose} |",
            f"| Carbon | 8.337e-06 gCO2e | estimated | {prose} |",
        ]
    )
    lifted = _lift_prose_columns(table)

    header = next(line for line in lifted.splitlines() if line.startswith("| Dimension"))
    assert "Notes" not in header, "the prose column is still inside the table"
    assert "Per unit" in header and "Status" in header, "a short column was lifted by mistake"
    assert "**Money** — Facility energy" in lifted, "the prose was dropped rather than moved"
    assert "**Carbon** — Facility energy" in lifted


def test_the_markdown_handed_over_has_had_its_prose_columns_lifted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Through ``render_office``, not through the helper on its own.

    Testing the helper proves the helper works. It does not prove this module
    calls it, and the defect being guarded against is precisely a report going
    to the converter unlifted -- which is what shipped. Removing the call has
    to turn this red.
    """
    # A model whose notes are long enough to collapse the table, because the
    # bare fixture's are not and the comparison would be vacuous: lifting is a
    # no-op on a report with no prose column, so an unlifted hand-over would
    # look identical to a lifted one.
    wordy = CostModel.from_mapping(
        {
            "schema_version": "2.0",
            "date_updated": "2026-10-03",
            "unit_of_work": {"name": "one request", "status": "estimated"},
            "deployment": {"provider": "on-prem", "country": "FR"},
            "scenarios": [
                {
                    "name": "as-audited",
                    "costs": {
                        "money": {
                            "value": 5.585e-08,
                            "unit": "USD",
                            "status": "estimated",
                            "notes": "Facility energy times the price per kilowatt-hour. "
                            "Hardware and staff are not included in this figure. "
                            "The tariff is the one the catalogue holds for the country.",
                        }
                    },
                }
            ],
        }
    )
    rendered = render_markdown(wordy)
    assert _lift_prose_columns(rendered) != rendered, (
        "this test's own model no longer has a column worth lifting, so it "
        "cannot tell a lifted hand-over from an unlifted one"
    )

    point_at(monkeypatch, stand_in_md2star(tmp_path))
    target = tmp_path / "cost.docx"
    render_office(wordy, target, output_format="docx")
    handed = (tmp_path / "cost.docx.md").read_text(encoding="utf-8")

    assert handed == _lift_prose_columns(rendered), (
        "the converter was handed the report unlifted; a notes column will "
        "squeeze the figures in the table down to one character per line"
    )


def test_a_table_whose_columns_are_all_short_is_left_alone() -> None:
    """The other direction, which is the one that would quietly ruin a report.

    A rule that lifts a long column is one threshold away from dismantling
    every table in the document, and the result would still render.
    """
    table = "\n".join(
        [
            "| provider | country | cores |",
            "|---|---|---|",
            "| on-prem | FR | 12 |",
        ]
    )
    assert _lift_prose_columns(table) == table


def test_text_that_is_not_a_table_passes_through_untouched() -> None:
    """Prose, headings and fenced code are not tables and must not be read as one."""
    document = "\n".join(
        [
            "# Heading",
            "",
            "A paragraph mentioning | a pipe | in passing.",
            "",
            "```",
            "| this | is | code |",
            "|---|---|---|",
            "```",
        ]
    )
    assert _lift_prose_columns(document) == document


def test_a_reference_document_is_passed_through_when_given(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The house template, which is the whole reason this takes a Word path."""
    point_at(monkeypatch, stand_in_md2star(tmp_path))
    template = tmp_path / "template.docx"
    template.write_bytes(b"PK\x03\x04")
    target = tmp_path / "cost.docx"
    render_office(MODEL, target, output_format="docx", reference_document=template)
    argv = (tmp_path / "cost.docx.argv").read_text(encoding="utf-8").splitlines()
    assert "--reference-doc" in argv
    assert argv[argv.index("--reference-doc") + 1] == str(template)


def test_no_reference_document_means_no_flag(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    point_at(monkeypatch, stand_in_md2star(tmp_path))
    render_office(MODEL, tmp_path / "cost.docx", output_format="docx")
    argv = (tmp_path / "cost.docx.argv").read_text(encoding="utf-8").splitlines()
    assert "--reference-doc" not in argv


def test_the_document_says_what_produced_it_and_when(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A reader holding the PDF should be able to tell it was generated."""
    point_at(monkeypatch, stand_in_md2star(tmp_path))
    render_office(MODEL, tmp_path / "cost.docx", output_format="docx")
    argv = (tmp_path / "cost.docx.argv").read_text(encoding="utf-8").splitlines()
    assert argv[argv.index("--author") + 1] == DEFAULT_AUTHOR
    assert argv[argv.index("--date") + 1] == date.today().isoformat()


def test_the_author_line_can_be_left_out(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Somebody producing a client deliverable may not want our name on it."""
    point_at(monkeypatch, stand_in_md2star(tmp_path))
    render_office(MODEL, tmp_path / "cost.docx", output_format="docx", author=None)
    argv = (tmp_path / "cost.docx.argv").read_text(encoding="utf-8").splitlines()
    assert "--author" not in argv
    assert "--date" in argv, "dropping the author must not drop the date with it"


def test_the_date_the_document_was_made_is_not_the_date_the_model_changed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Two different facts, and conflating them is how a stale figure looks fresh.

    *Last updated* in the body says when somebody last changed a number. The
    date in the title block says when this file was made. A document produced
    today from a model nobody has touched since June has to say both.
    """
    point_at(monkeypatch, stand_in_md2star(tmp_path))
    render_office(MODEL, tmp_path / "cost.docx", output_format="docx", generated=date(2026, 6, 21))
    argv = (tmp_path / "cost.docx.argv").read_text(encoding="utf-8").splitlines()
    assert argv[argv.index("--date") + 1] == "2026-06-21"
    body = render_markdown(MODEL)
    assert "2026-06-21" not in body, "stamping the document rewrote the model's own dates"


def test_a_date_that_is_not_a_date_is_passed_through_untouched(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`2026-Q2` and `submitted 14 March` are what some documents actually say."""
    point_at(monkeypatch, stand_in_md2star(tmp_path))
    render_office(MODEL, tmp_path / "cost.docx", output_format="docx", generated="2026-Q2")
    argv = (tmp_path / "cost.docx.argv").read_text(encoding="utf-8").splitlines()
    assert argv[argv.index("--date") + 1] == "2026-Q2"


def test_the_network_can_be_refused_and_is_not_refused_by_default(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The converter fetches a template over HTTP unless told not to.

    That is a pleasant default and a surprising one: a render fails on a train,
    and two renders of one model differ when the template moves. Neither is a
    defect, but a caller who needs determinism has to be able to say so.
    """
    point_at(monkeypatch, stand_in_md2star(tmp_path))
    render_office(MODEL, tmp_path / "plain.docx", output_format="docx")
    relaxed = (tmp_path / "plain.docx.argv").read_text(encoding="utf-8").splitlines()
    assert "--offline" not in relaxed

    render_office(MODEL, tmp_path / "sealed.docx", output_format="docx", offline=True)
    sealed = (tmp_path / "sealed.docx.argv").read_text(encoding="utf-8").splitlines()
    assert "--offline" in sealed
    assert "--no-remote-templates" in sealed


# --- When it goes wrong ---------------------------------------------------------


def test_a_failed_conversion_carries_the_reason_out(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The last line of the converter's complaint, which is the useful one.

    Pandoc's errors end with the sentence that names the problem; everything
    above it is the stack that got there.
    """
    point_at(
        monkeypatch,
        stand_in_md2star(
            tmp_path, code=1, stderr="pandoc: some noise\nmore noise\npdflatex not found in PATH\n"
        ),
    )
    with pytest.raises(RuntimeError) as raised:
        render_office(MODEL, tmp_path / "cost.pdf", output_format="pdf")
    assert "pdflatex not found in PATH" in str(raised.value)


def test_a_failure_that_says_nothing_still_produces_a_message(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The failure message must not itself be able to fail.

    Whitespace-only output strips to nothing, and taking the last line of an
    empty list raised an IndexError out of the error handler -- the messenger
    crashing instead of delivering the message.
    """
    point_at(monkeypatch, stand_in_md2star(tmp_path, code=3, stderr="   \n  \n"))
    with pytest.raises(RuntimeError) as raised:
        render_office(MODEL, tmp_path / "cost.docx", output_format="docx")
    assert "no output" in str(raised.value)


def test_a_conversion_that_never_finishes_is_given_up_on(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A hung converter must not hang the render that called it."""
    import saggio.report.office as office

    monkeypatch.setattr(office, "_CONVERSION_TIMEOUT_SECONDS", 0.2)
    point_at(monkeypatch, stand_in_md2star(tmp_path, delay=10.0))
    with pytest.raises(RuntimeError) as raised:
        render_office(MODEL, tmp_path / "cost.pdf", output_format="pdf")
    message = str(raised.value)
    assert "did not produce the pdf" in message
    assert "0.2 seconds" in message
