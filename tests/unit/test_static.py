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
    detect_models,
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
    workload, in_suite_only = detect_frameworks(tmp_path)
    assert set(workload) >= {"pytorch", "transformers"}
    assert in_suite_only == ()


def test_a_framework_written_into_a_fixture_is_not_a_framework(tmp_path: Path) -> None:
    # This is what a tool doing the naive thing gets wrong, and what it got wrong
    # on this very repository: a fixture writing "import torch" into a temporary
    # file made the audit report a project that trains models. It does not, and
    # the string inside the call is not an import anywhere.
    write(tmp_path, "app.py", "import flask\n")
    write(tmp_path, "tests/test_model.py", 'write("import torch\\n")\n')
    workload, in_suite_only = detect_frameworks(tmp_path)
    assert "pytorch" not in workload
    assert "pytorch" not in in_suite_only


def test_a_framework_the_suite_itself_imports_is_reported_apart(tmp_path: Path) -> None:
    # The suite really does import it, which is worth saying and is not evidence
    # that the workload does.
    write(tmp_path, "app.py", "import flask\n")
    write(tmp_path, "tests/test_model.py", "import torch\n")
    workload, in_suite_only = detect_frameworks(tmp_path)
    assert "pytorch" not in workload
    assert "pytorch" in in_suite_only


def test_a_framework_named_in_prose_is_not_detected(tmp_path: Path) -> None:
    write(tmp_path, "app.py", "# we could import torch here one day\nimport flask\n")
    workload, in_suite_only = detect_frameworks(tmp_path)
    assert workload == () and in_suite_only == ()


def test_a_framework_used_in_both_places_belongs_to_the_workload(tmp_path: Path) -> None:
    write(tmp_path, "train.py", "import torch\n")
    write(tmp_path, "tests/test_train.py", "import torch\n")
    workload, in_suite_only = detect_frameworks(tmp_path)
    assert "pytorch" in workload
    assert "pytorch" not in in_suite_only


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


# --- Model identifiers -------------------------------------------------------


def test_a_model_named_in_a_call_is_found_with_its_evidence(tmp_path) -> None:
    (tmp_path / "app.py").write_text(
        'reply = client.chat.completions.create(model="gpt-4o")\n', encoding="utf-8"
    )
    hits = detect_models(tmp_path)
    assert [hit.identifier for hit in hits] == ["gpt-4o"]
    assert hits[0].path == "app.py"
    assert hits[0].line_number == 1
    assert "gpt-4o" in hits[0].line


def test_the_other_spellings_of_naming_a_model_are_found_too(tmp_path) -> None:
    (tmp_path / "a.py").write_text('model_name = "claude-3-5-sonnet"\n', encoding="utf-8")
    (tmp_path / "b.py").write_text('{"model": "mistral-large-latest"}\n', encoding="utf-8")
    found = {hit.identifier for hit in detect_models(tmp_path)}
    assert found == {"claude-3-5-sonnet", "mistral-large-latest"}


def test_a_model_named_only_in_a_comment_is_not_a_model_the_code_calls(tmp_path) -> None:
    # The same rule the service detection keeps: prose about code is not code.
    (tmp_path / "app.py").write_text('# model="gpt-4o" is the expensive one\n', encoding="utf-8")
    assert detect_models(tmp_path) == ()


def test_a_model_held_in_a_variable_is_not_guessed_at(tmp_path) -> None:
    # Knowing what CHOSEN holds would mean running the program, and this pass
    # runs nothing.
    (tmp_path / "app.py").write_text("client.chat(model=CHOSEN)\n", encoding="utf-8")
    assert detect_models(tmp_path) == ()


def test_each_identifier_is_reported_once_however_often_it_appears(tmp_path) -> None:
    (tmp_path / "a.py").write_text('model="gpt-4o"\nmodel="gpt-4o"\n', encoding="utf-8")
    (tmp_path / "b.py").write_text('model="gpt-4o"\n', encoding="utf-8")
    assert len(detect_models(tmp_path)) == 1


# --- Model identifiers: three things that look alike ------------------------


def test_a_type_annotation_is_not_a_model_being_called(tmp_path: Path) -> None:
    # Auditing Whisper reported a model called Whisper, from the line
    # `model: "Whisper", mel: Tensor` in a function signature. Python has no
    # unquoted mapping keys, so a colon after a bare name is an annotation.
    write(tmp_path, "decoding.py", 'def decode(model: "Whisper", mel: Tensor) -> str:\n    ...\n')
    assert detect_models(tmp_path) == ()


def test_a_quoted_key_in_python_is_a_mapping_and_still_counts(tmp_path: Path) -> None:
    write(tmp_path, "call.py", 'reply = post({"model": "gpt-4o"})\n')
    assert [hit.identifier for hit in detect_models(tmp_path)] == ["gpt-4o"]


def test_an_unquoted_key_outside_python_is_a_mapping(tmp_path: Path) -> None:
    # JavaScript, TypeScript and Go all write object keys without quotes, and
    # there the same line really is a model being chosen.
    write(tmp_path, "client.ts", 'const body = { model: "gpt-4o" };\n')
    assert [hit.identifier for hit in detect_models(tmp_path)] == ["gpt-4o"]


def test_a_string_being_built_is_not_a_model(tmp_path: Path) -> None:
    # Auditing FastAPI reported a model called Body_, from
    # `model_name = "Body_" + name` in its own internals.
    write(tmp_path, "utils.py", 'model_name = "Body_" + name\n')
    assert detect_models(tmp_path) == ()


def test_a_string_being_formatted_is_not_a_model(tmp_path: Path) -> None:
    write(tmp_path, "utils.py", 'model = "gpt-{}".format(version)\n')
    assert detect_models(tmp_path) == ()


def test_a_fragment_appended_to_something_else_is_not_a_model(tmp_path: Path) -> None:
    write(tmp_path, "utils.py", 'model = prefix + "-turbo"\n')
    assert detect_models(tmp_path) == ()


def test_the_ordinary_ways_of_naming_a_model_all_still_work(tmp_path: Path) -> None:
    write(
        tmp_path,
        "app.py",
        'a = chat(model="gpt-4o")\n'
        "b = chat(model_name='claude-3-5-sonnet')\n"
        'c = post({"model": "mistral-large-latest"})\n',
    )
    found = {hit.identifier for hit in detect_models(tmp_path)}
    assert found == {"gpt-4o", "claude-3-5-sonnet", "mistral-large-latest"}


# --- Which file states the length of a run ----------------------------------


def test_a_training_config_outranks_an_evaluation_one(tmp_path: Path) -> None:
    # Auditing DINOv2 took its epoch count from configs/eval/, because the rule
    # was alphabetical within a rank and "eval" sorts before "train".
    write(tmp_path, "configs/eval/linear.yaml", "epochs: 10\n")
    write(tmp_path, "configs/train/vitg14.yaml", "epochs: 500\n")
    chosen, every, conflicts = find_work_size(tmp_path)
    assert chosen is not None
    assert chosen.value == 500.0
    assert "train" in chosen.source
    # Both are still on the record, and the disagreement is still reported.
    assert len(every) == 2
    assert conflicts


def test_a_neutral_directory_outranks_an_evaluation_one(tmp_path: Path) -> None:
    write(tmp_path, "configs/benchmarks/speed.yaml", "epochs: 3\n")
    write(tmp_path, "configs/default.yaml", "epochs: 100\n")
    chosen, _, _ = find_work_size(tmp_path)
    assert chosen is not None and chosen.value == 100.0


def test_a_named_config_file_still_beats_a_training_directory(tmp_path: Path) -> None:
    # The file-name table is the stronger statement of the two: a repository that
    # has a config.py is telling you where its configuration lives.
    write(tmp_path, "config.py", "epochs = 42\n")
    write(tmp_path, "train/other.yaml", "epochs: 7\n")
    chosen, _, _ = find_work_size(tmp_path)
    assert chosen is not None and chosen.value == 42.0
