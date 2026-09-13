"""Reading a repository: what it establishes, and what it refuses to settle."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from saggio.analyze.static import (
    CONFIG_FILE_PRECEDENCE,
    _is_prose_line,
    capped_entrypoint_command,
    detect_archetype,
    detect_frameworks,
    detect_languages,
    detect_services,
    detect_tests,
    find_entrypoint,
    find_work_size,
    read_repository,
)


def write(root: Path, name: str, text: str) -> Path:
    target = root / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")
    return target


# --- Languages ---------------------------------------------------------------


def test_languages_are_counted_and_ordered(tmp_path: Path) -> None:
    write(tmp_path, "a.py", "")
    write(tmp_path, "b.py", "")
    write(tmp_path, "c.rs", "")
    assert list(detect_languages(tmp_path)) == ["Python", "Rust"]


def test_vendored_trees_are_not_the_code_under_study(tmp_path: Path) -> None:
    write(tmp_path, "app.py", "")
    write(tmp_path, "node_modules/pkg/index.js", "")
    write(tmp_path, ".venv/lib/thing.py", "")
    assert detect_languages(tmp_path) == {"Python": 1}


# --- Archetype ---------------------------------------------------------------


@pytest.mark.parametrize(
    ("filename", "expected"),
    [
        ("train.py", "training"),
        ("predict.py", "inference"),
        ("etl.py", "batch-pipeline"),
        ("server.py", "service"),
        ("cli.py", "command-line-tool"),
    ],
)
def test_a_filename_suggests_a_shape(tmp_path: Path, filename: str, expected: str) -> None:
    write(tmp_path, filename, "pass")
    assert detect_archetype(tmp_path, {"Python": 1}) == expected


def test_training_outranks_a_generic_entry_point(tmp_path: Path) -> None:
    write(tmp_path, "train.py", "pass")
    write(tmp_path, "main.py", "pass")
    assert detect_archetype(tmp_path, {"Python": 2}) == "training"


def test_an_unremarkable_repository_is_unknown(tmp_path: Path) -> None:
    write(tmp_path, "helpers.py", "pass")
    assert detect_archetype(tmp_path, {"Python": 1}) == "unknown"


# --- Frameworks --------------------------------------------------------------


def test_frameworks_are_found_by_import_fingerprint(tmp_path: Path) -> None:
    write(tmp_path, "model.py", "import torch\nfrom transformers import AutoModel\n")
    assert set(detect_frameworks(tmp_path)) >= {"pytorch", "transformers"}


# --- Work size, and the disagreement it refuses to settle quietly ------------


def test_a_stated_size_is_read_verbatim(tmp_path: Path) -> None:
    write(tmp_path, "config.py", "max_iters = 600_000\n")
    chosen, _, conflicts = find_work_size(tmp_path)
    assert chosen is not None
    assert chosen.value == 600000.0
    assert chosen.source == "config.py::max_iters"
    assert not conflicts


def test_a_configuration_file_outranks_a_training_script(tmp_path: Path) -> None:
    write(tmp_path, "config.py", "max_iters = 600000\n")
    write(tmp_path, "train.py", "max_iters = 300\n")
    chosen, every, conflicts = find_work_size(tmp_path)
    assert chosen is not None
    assert chosen.value == 600000.0
    assert len(every) == 2
    assert conflicts


def test_a_disagreement_is_reported_rather_than_settled(tmp_path: Path) -> None:
    # Capping a measured slice against 300 when a real run does 600000 is off by a
    # factor of two thousand, and it used to happen in silence.
    write(tmp_path, "config.py", "max_iters = 600000\n")
    write(tmp_path, "train.py", "max_iters = 300\n")
    _, _, conflicts = find_work_size(tmp_path)
    assert "600000" in conflicts[0] and "300" in conflicts[0]


def test_agreeing_statements_are_not_a_disagreement(tmp_path: Path) -> None:
    write(tmp_path, "config.py", "epochs = 10\n")
    write(tmp_path, "train.py", "epochs = 10\n")
    assert not find_work_size(tmp_path)[2]


def test_a_more_precise_key_outranks_a_vaguer_one(tmp_path: Path) -> None:
    write(tmp_path, "config.py", "epochs = 10\nmax_iters = 5000\n")
    chosen, _, _ = find_work_size(tmp_path)
    assert chosen is not None
    assert chosen.key == "max_iters"


def test_a_repository_that_states_no_size_says_so(tmp_path: Path) -> None:
    write(tmp_path, "app.py", "print('hello')\n")
    assert find_work_size(tmp_path)[0] is None


def test_a_zero_size_is_not_a_size(tmp_path: Path) -> None:
    write(tmp_path, "config.py", "max_iters = 0\n")
    assert find_work_size(tmp_path)[0] is None


def test_the_precedence_is_written_down_and_used() -> None:
    assert CONFIG_FILE_PRECEDENCE.index("config.py") < CONFIG_FILE_PRECEDENCE.index("train.py")


# --- Services ----------------------------------------------------------------


def test_a_service_call_is_found_with_the_line_that_proves_it(tmp_path: Path) -> None:
    write(tmp_path, "app.py", "import os\nfrom openai import OpenAI\n")
    hits = detect_services(tmp_path)
    assert len(hits) == 1
    assert hits[0].key == "openai"
    assert hits[0].line_number == 2
    assert hits[0].pricing_source_url


def test_writing_about_a_service_is_not_calling_one(tmp_path: Path) -> None:
    write(tmp_path, "notes.py", "# we could use: from openai import OpenAI\n")
    assert detect_services(tmp_path) == ()


def test_a_docstring_example_is_not_a_service_call(tmp_path: Path) -> None:
    write(tmp_path, "doc.py", '"""Example.\n\n    >>> import openai\n    """\n')
    assert detect_services(tmp_path) == ()


@pytest.mark.parametrize(
    "line", ["# import openai", "// import openai", "  >>> import openai", "* import openai"]
)
def test_prose_lines_are_recognised(line: str) -> None:
    assert _is_prose_line(line)


def test_real_code_is_not_prose() -> None:
    assert not _is_prose_line("from openai import OpenAI")


# --- Tests and entry points --------------------------------------------------


def test_a_test_directory_makes_a_slice_available(tmp_path: Path) -> None:
    write(tmp_path, "tests/test_thing.py", "def test_it():\n    assert True\n")
    found, command = detect_tests(tmp_path)
    assert found
    assert command[0] == sys.executable
    assert "pytest" in command


def test_a_repository_with_no_tests_offers_no_command(tmp_path: Path) -> None:
    write(tmp_path, "app.py", "pass")
    assert detect_tests(tmp_path) == (False, ())


def test_the_entry_point_is_the_first_well_known_name(tmp_path: Path) -> None:
    write(tmp_path, "main.py", "pass")
    write(tmp_path, "train.py", "pass")
    assert find_entrypoint(tmp_path) == "train.py"


def test_no_entry_point_is_a_normal_answer(tmp_path: Path) -> None:
    assert find_entrypoint(tmp_path) is None


# --- The capped slice --------------------------------------------------------


def test_a_capped_command_covers_a_share_read_from_a_file(tmp_path: Path) -> None:
    write(tmp_path, "config.py", "max_iters = 600000\n")
    write(tmp_path, "train.py", "pass")
    reading = read_repository(tmp_path)
    command, fraction = capped_entrypoint_command(reading, cap_fraction=0.001)
    assert command is not None
    assert command[-2:] == ("--max_iters", "600")
    assert fraction == pytest.approx(0.001)


def test_a_tiny_run_never_claims_to_be_more_than_all_of_itself(tmp_path: Path) -> None:
    write(tmp_path, "config.py", "max_iters = 3\n")
    write(tmp_path, "train.py", "pass")
    command, fraction = capped_entrypoint_command(read_repository(tmp_path), cap_fraction=0.001)
    assert command is not None
    assert 0.0 < fraction <= 1.0


def test_without_a_size_or_an_entry_point_there_is_no_capped_slice(tmp_path: Path) -> None:
    write(tmp_path, "app.py", "pass")
    assert capped_entrypoint_command(read_repository(tmp_path)) == (None, None)


# --- The whole reading -------------------------------------------------------


def test_reading_a_repository_gathers_everything(training_repository: Path) -> None:
    reading = read_repository(training_repository)
    assert reading.archetype == "training"
    assert reading.work_size is not None
    assert reading.entrypoint == "train.py"
    assert [hit.key for hit in reading.services] == ["openai"]
    assert reading.dominant_language() == "Python"


def test_a_deep_learning_training_repository_reads_as_compute_bound(tmp_path: Path) -> None:
    write(tmp_path, "train.py", "import torch\n")
    assert read_repository(tmp_path).is_compute_bound() is True


def test_anything_else_declines_to_guess(tmp_path: Path) -> None:
    write(tmp_path, "server.py", "import flask\n")
    assert read_repository(tmp_path).is_compute_bound() is None


def test_reading_something_that_is_not_a_directory_is_refused(tmp_path: Path) -> None:
    with pytest.raises(AssertionError, match="Not a directory"):
        read_repository(tmp_path / "nope")


def test_the_reading_serialises_as_prose_and_counts(training_repository: Path) -> None:
    mapping = read_repository(training_repository).to_mapping()
    assert mapping["evidence_source"] == "static"
    assert mapping["total_work"]["source"].endswith("::max_iters")
