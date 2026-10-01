"""Dimensions: the registry that the schema actually uses."""

from __future__ import annotations

import pytest

from saggio.model.dimensions import (
    CANONICAL_DIMENSIONS,
    Dimension,
    DimensionRegistry,
    registry_for,
)


def test_the_canonical_five_are_registered_in_report_order() -> None:
    assert DimensionRegistry().keys() == tuple(d.key for d in CANONICAL_DIMENSIONS)


def test_money_is_the_only_canonical_money_dimension() -> None:
    money = [d.key for d in CANONICAL_DIMENSIONS if d.is_money]
    assert money == ["money"]


def test_every_canonical_dimension_says_what_it_counts() -> None:
    for dimension in CANONICAL_DIMENSIONS:
        assert dimension.description.endswith(".")
        assert dimension.unit


def test_registering_a_duplicate_is_refused() -> None:
    registry = DimensionRegistry()
    with pytest.raises(ValueError, match="already registered"):
        registry.register(Dimension("energy", "Energy", "J", "Again."))


def test_an_empty_key_is_refused() -> None:
    with pytest.raises(ValueError, match="non-empty key"):
        DimensionRegistry(()).register(Dimension("", "X", "u", "d."))


def test_a_reserved_key_is_refused() -> None:
    with pytest.raises(ValueError, match="reserved"):
        DimensionRegistry(()).register(Dimension("_secret", "X", "u", "d."))


def test_a_dimension_round_trips() -> None:
    dimension = Dimension("egress", "Egress", "GB", "Bytes out.", higher_is_worse=False)
    assert Dimension.from_mapping(dimension.to_mapping()) == dimension


def test_a_half_filled_declaration_still_renders() -> None:
    assert Dimension.from_mapping({"key": "egress"}).label == "egress"


def test_building_a_registry_from_a_model_adds_the_declared_ones() -> None:
    registry = registry_for([{"key": "egress", "unit": "GB"}])
    assert registry.keys()[-1] == "egress"


@pytest.mark.parametrize(
    "declared", [None, "not a list", [{"no": "key"}], ["not a mapping"], [{"key": "energy"}]]
)
def test_a_malformed_declaration_never_breaks_the_registry(declared: object) -> None:
    # The validator reports the fault with a path; building the registry must
    # still produce something usable, or the report itself could not be rendered.
    assert len(registry_for(declared)) == len(CANONICAL_DIMENSIONS)


def test_a_registry_is_iterable_sized_and_searchable() -> None:
    registry = DimensionRegistry()
    assert len(registry) == 6
    assert "carbon" in registry
    assert next(iter(registry)).key == "money"
    with pytest.raises(KeyError):
        registry.get("nope")
