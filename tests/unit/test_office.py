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
from pathlib import Path

import pytest

from saggio.model import CostModel
from saggio.report.office import render_office

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
