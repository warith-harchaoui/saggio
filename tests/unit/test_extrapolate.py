"""Projections: what they will do, and what they refuse to do."""

from __future__ import annotations

import pytest

from running_code_cost_helper.estimate.extrapolate import (
    Projection,
    project_to_completion,
    project_to_machine,
)
from running_code_cost_helper.model import Quantity


def measured(value: float, unit: str = "kWh") -> Quantity:
    return Quantity(value=value, unit=unit, status="measured")


# --- Slice to whole run ------------------------------------------------------


def test_a_quarter_of_a_run_projects_to_four_times_the_cost() -> None:
    assert project_to_completion(measured(2.0), fraction=0.25).quantity.value == pytest.approx(8.0)


def test_a_projection_is_never_stronger_than_estimated() -> None:
    # A measurement of a slice is not a measurement of the whole run.
    assert project_to_completion(measured(2.0), fraction=0.5).quantity.status == "estimated"


def test_a_projection_from_something_weak_stays_weak() -> None:
    weak = Quantity(value=2.0, unit="kWh", status="placeholder")
    assert project_to_completion(weak, fraction=0.5).quantity.status == "placeholder"


@pytest.mark.parametrize("fraction", [0.0, -0.1, 1.5, 2.0])
def test_a_fraction_outside_the_interval_is_refused(fraction: float) -> None:
    projection = project_to_completion(measured(1.0), fraction=fraction)
    assert projection.refused
    assert "(0, 1]" in str(projection.quantity.notes)


def test_a_whole_slice_is_allowed() -> None:
    assert not project_to_completion(measured(1.0), fraction=1.0).refused


def test_a_slice_with_no_number_projects_to_nothing() -> None:
    assert project_to_completion(Quantity(status="TODO"), fraction=0.5).refused


def test_a_projection_keeps_the_unit_and_currency() -> None:
    money = Quantity(value=1.0, unit="USD", currency="USD", status="measured")
    projected = project_to_completion(money, fraction=0.5).quantity
    assert (projected.unit, projected.currency) == ("USD", "USD")


def test_a_projection_states_what_it_assumed_and_where_it_stops() -> None:
    projection = project_to_completion(measured(1.0), fraction=0.01)
    assert projection.assumptions
    assert projection.limits
    assert "0.001" not in projection.method


# --- One machine to another --------------------------------------------------


def test_a_faster_accelerator_finishes_sooner_in_proportion() -> None:
    projected = project_to_machine(
        runtime=measured(1000.0, "s"), source_key="A100", target_key="H100"
    )
    assert projected.quantity.value == pytest.approx(1000.0 * 312 / 989, rel=1e-6)


def test_the_same_accelerator_changes_nothing() -> None:
    projected = project_to_machine(
        runtime=measured(100.0, "s"), source_key="A100", target_key="A100"
    )
    assert projected.quantity.value == pytest.approx(100.0)


@pytest.mark.parametrize("precision", ["fp32", "int8", "fp8", "tf32"])
def test_a_precision_the_catalogue_cannot_speak_to_is_refused(precision: str) -> None:
    # Two chips do not keep the same ratio across precisions: scaling FP32 work
    # by a BF16 figure would overstate the faster one, sometimes by a lot.
    projection = project_to_machine(
        runtime=measured(1.0, "s"), source_key="A100", target_key="H100", precision=precision
    )
    assert projection.refused
    assert precision in str(projection.quantity.notes)


@pytest.mark.parametrize("precision", ["bf16", "BF16", "fp16", "bfloat16"])
def test_the_precisions_it_can_speak_to_are_accepted(precision: str) -> None:
    assert not project_to_machine(
        runtime=measured(1.0, "s"), source_key="A100", target_key="H100", precision=precision
    ).refused


def test_an_unknown_accelerator_is_refused_and_named() -> None:
    projection = project_to_machine(
        runtime=measured(1.0, "s"), source_key="A100", target_key="NOT-A-GPU"
    )
    assert projection.refused
    assert "NOT-A-GPU" in str(projection.quantity.notes)


def test_an_accelerator_with_no_throughput_figure_is_refused() -> None:
    # T4 is in the catalogue with a wattage but no peak throughput, so there is
    # no ratio to scale by and saying so beats inventing one.
    projection = project_to_machine(runtime=measured(1.0, "s"), source_key="T4", target_key="H100")
    assert projection.refused
    assert "peak throughput" in str(projection.quantity.notes)


def test_a_consumer_card_can_be_the_source() -> None:
    # This is the case that makes the feature usable at all: most people write a
    # cost model on a laptop or a workstation, not on a datacenter node.
    assert not project_to_machine(
        runtime=measured(600.0, "s"), source_key="RTX-4090", target_key="H100"
    ).refused


def test_a_runtime_with_no_number_projects_to_nothing() -> None:
    assert project_to_machine(
        runtime=Quantity(status="TODO"), source_key="A100", target_key="H100"
    ).refused


def test_the_method_can_be_redone_by_hand() -> None:
    method = project_to_machine(
        runtime=measured(1.0, "s"), source_key="A100", target_key="H100"
    ).method
    assert "312" in method and "989" in method


# --- Serialisation -----------------------------------------------------------


def test_a_projection_nests_its_quantity_under_result_not_value() -> None:
    # A mapping with a value key is a quantity everywhere else in this package, so
    # a projection using that key would be read as a quantity with four invented
    # fields, and the validator would warn about every one of them.
    mapping = project_to_completion(measured(1.0), fraction=0.5).to_mapping()
    assert "result" in mapping
    assert "value" not in mapping


def test_a_refusal_serialises_as_a_refusal() -> None:
    mapping = project_to_completion(measured(1.0), fraction=0.0).to_mapping()
    assert mapping["refused"] is True


def test_an_empty_projection_carries_no_empty_lists() -> None:
    assert set(Projection(Quantity(status="TODO"), "m").to_mapping()) == {"method", "result"}
