"""Navigating a model: walking it, addressing it, and writing it back."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

from saggio.model.cost_model import (
    CostModel,
    resolve_path,
    status_at,
    walk_bare_numbers,
    walk_quantities,
)


def test_walking_finds_every_quantity_with_its_path(sound_model: dict[str, Any]) -> None:
    paths = [path for path, _ in walk_quantities(sound_model)]
    assert "assumptions.power_draw" in paths
    assert "scenarios[0].costs.money" in paths


def test_walking_stops_at_a_quantity() -> None:
    # A quantity is a leaf. Descending into it would treat its own fields as if
    # they were more model structure.
    paths = [path for path, _ in walk_quantities({"q": {"value": 1, "unit": "s", "notes": "n"}})]
    assert paths == ["q"]


def test_walking_reaches_inside_a_block_the_tool_does_not_know() -> None:
    paths = [path for path, _ in walk_quantities({"invented": {"deep": {"value": 1}}})]
    assert paths == ["invented.deep"]


def test_bare_numbers_are_the_ones_outside_a_quantity() -> None:
    found = dict(walk_bare_numbers({"a": 1, "b": {"value": 2, "status": "measured"}}))
    assert found == {"a": 1}


def test_booleans_are_not_bare_numbers() -> None:
    assert not list(walk_bare_numbers({"flag": True}))


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("a.b[1]", 20),
        ("a.b[0]", 10),
        ("a", {"b": [10, 20]}),
        ("", {"a": {"b": [10, 20]}}),
    ],
)
def test_resolving_a_path(path: str, expected: Any) -> None:
    assert resolve_path({"a": {"b": [10, 20]}}, path) == expected


@pytest.mark.parametrize("path", ["a.c", "a.b[9]", "a.b.c", "missing"])
def test_a_path_that_names_nothing_resolves_to_nothing(path: str) -> None:
    assert resolve_path({"a": {"b": [10, 20]}}, path) is None


def test_status_at_only_answers_for_quantities() -> None:
    model = {"q": {"value": 1, "status": "measured"}, "plain": 2}
    assert status_at(model, "q") == "measured"
    assert status_at(model, "plain") is None


def test_scenario_path_matches_the_spelling_the_model_used() -> None:
    assert CostModel.from_mapping({"scenario": {}}).scenario_path(0) == "scenario"
    assert CostModel.from_mapping({"scenarios": [{}]}).scenario_path(0) == "scenarios[0]"


def test_scenarios_flatten_whichever_spelling(sound_model: dict[str, Any]) -> None:
    single = CostModel.from_mapping({"scenario": {"name": "one"}})
    assert len(single.scenarios()) == 1
    assert len(CostModel.from_mapping(sound_model).scenarios()) == 1


def test_a_registry_picks_up_the_models_own_dimensions() -> None:
    model = CostModel.from_mapping({"dimensions": [{"key": "egress", "unit": "GB"}]})
    assert "egress" in model.registry
    assert len(model.registry) == 7


def test_a_dimension_that_duplicates_a_canonical_one_is_skipped_not_fatal() -> None:
    model = CostModel.from_mapping({"dimensions": [{"key": "energy", "unit": "J"}]})
    assert model.registry.get("energy").unit == "kWh"


def test_unknown_blocks_are_listed() -> None:
    assert CostModel.from_mapping({"invented": 1, "deployment": {}}).unknown_blocks() == (
        "invented",
    )


def test_writing_orders_the_blocks_the_way_a_reader_reads_them(
    sound_model: dict[str, Any],
) -> None:
    text = CostModel.from_mapping(sound_model).to_yaml()
    assert text.index("schema_version") < text.index("unit_of_work") < text.index("scenarios")


def test_an_unrecognised_block_is_carried_through_untouched(
    sound_model: dict[str, Any],
) -> None:
    sound_model["team_notes"] = ["keep this"]
    text = CostModel.from_mapping(sound_model).to_yaml()
    assert "keep this" in text


def test_a_model_round_trips_through_disk(tmp_path: Path, sound_model: dict[str, Any]) -> None:
    target = tmp_path / "nested" / "cost.yaml"
    CostModel.from_mapping(sound_model).save(target)
    assert CostModel.load(target).data == sound_model


def test_saving_without_a_path_is_refused(sound_model: dict[str, Any]) -> None:
    with pytest.raises(ValueError, match="no path"):
        CostModel.from_mapping(sound_model).save()


def test_loading_a_missing_file_says_so(tmp_path: Path) -> None:
    with pytest.raises(AssertionError, match="not found or empty"):
        CostModel.load(tmp_path / "nope.yaml")


def test_loading_broken_yaml_says_so(tmp_path: Path) -> None:
    target = tmp_path / "broken.yaml"
    target.write_text("a: [1, 2\n", encoding="utf-8")
    with pytest.raises(ValueError, match="not valid YAML"):
        CostModel.load(target)


def test_loading_something_that_is_not_a_mapping_says_so(tmp_path: Path) -> None:
    target = tmp_path / "list.yaml"
    target.write_text("- one\n- two\n", encoding="utf-8")
    with pytest.raises(ValueError, match="must contain a mapping"):
        CostModel.load(target)


def test_typed_quantities_parse_every_raw_one(sound_model: dict[str, Any]) -> None:
    model = CostModel.from_mapping(sound_model)
    assert len(model.typed_quantities()) == len(model.quantities())
    assert model.status_of("scenarios[0].runtime") == "measured"


def test_yaml_is_written_in_a_form_it_can_read_back(sound_model: dict[str, Any]) -> None:
    assert yaml.safe_load(CostModel.from_mapping(sound_model).to_yaml()) == sound_model
