"""The quantity: what it round-trips, and what it refuses to call a number."""

from __future__ import annotations

import pytest

from running_code_cost_helper.model.quantity import (
    QUANTITY_KEYS,
    Quantity,
    looks_like_quantity,
)


def test_a_full_quantity_round_trips_without_loss() -> None:
    mapping = {
        "value": 0.24,
        "unit": "USD/kWh",
        "currency": "USD",
        "status": "estimated",
        "source_url": "https://example.invalid",
        "retrieved_date": "2026-09-12",
        "derived_from": ["a", "b"],
        "notes": "a note",
    }
    assert Quantity.from_mapping(mapping).to_mapping() == mapping


def test_a_minimal_quantity_does_not_sprout_empty_keys() -> None:
    assert Quantity(value=1.0, status="measured").to_mapping() == {
        "value": 1.0,
        "status": "measured",
    }


def test_a_single_derivation_path_is_accepted_as_written() -> None:
    # A hand-edited model often writes one path as a string rather than a list;
    # iterating its characters would produce a derivation from "a", "." and "b".
    assert Quantity.from_mapping({"value": 1, "derived_from": "a.b"}).derived_from == ("a.b",)


def test_a_missing_status_defaults_to_the_weakest() -> None:
    assert Quantity.from_mapping({"value": 1}).status == "TODO"


@pytest.mark.parametrize("value", [True, False])
def test_a_boolean_is_not_a_measurement(value: bool) -> None:
    assert not Quantity(value=value, status="measured").is_known()


def test_zero_is_a_number() -> None:
    assert Quantity(value=0.0, status="measured").is_known()


def test_a_placeholder_does_not_promise_a_value() -> None:
    assert not Quantity(status="placeholder").expects_a_value()
    assert not Quantity(status="TODO").expects_a_value()
    assert Quantity(value=1, status="estimated").expects_a_value()


def test_withdrawing_a_value_keeps_the_shape() -> None:
    withdrawn = Quantity(value=3.0, unit="kWh", currency=None, status="estimated").unknown(
        reason="the source went away"
    )
    assert withdrawn.status == "TODO"
    assert withdrawn.unit == "kWh"
    assert withdrawn.value is None
    assert "source" in str(withdrawn.notes)


def test_adding_a_derivation_changes_nothing_else() -> None:
    original = Quantity(value=2.0, unit="kWh", status="estimated", notes="n")
    derived = original.with_derivation("x", "y")
    assert derived.derived_from == ("x", "y")
    assert (derived.value, derived.unit, derived.status, derived.notes) == (
        original.value,
        original.unit,
        original.status,
        original.notes,
    )


def test_a_quantity_is_recognised_by_shape_not_by_position() -> None:
    assert looks_like_quantity({"value": 1})
    assert not looks_like_quantity({"name": "default"})
    assert not looks_like_quantity([1, 2])
    assert not looks_like_quantity(3.14)


def test_every_serialised_key_is_a_declared_quantity_key() -> None:
    full = Quantity(
        value=1,
        unit="s",
        currency="USD",
        status="measured",
        source_url="u",
        retrieved_date="2026-01-01",
        derived_from=("a",),
        notes="n",
    )
    assert set(full.to_mapping()) <= QUANTITY_KEYS
