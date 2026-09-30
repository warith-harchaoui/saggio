"""Projections: what they will do, and what they refuse to do."""

from __future__ import annotations

import pytest

from saggio.catalog.registry import Catalog
from saggio.estimate.extrapolate import (
    Projection,
    project_to_completion,
    project_to_machine,
    project_to_processor,
)
from saggio.model import Quantity


def measured(value: float, unit: str = "kWh") -> Quantity:
    return Quantity(value=value, unit=unit, status="measured")


# --- Slice to whole run ------------------------------------------------------


def test_a_quarter_of_a_run_projects_to_four_times_the_cost() -> None:
    assert project_to_completion(measured(2.0), fraction=0.25).quantity.value == pytest.approx(8.0)


def test_a_projection_is_never_stronger_than_estimated() -> None:
    # A measurement of a slice is not a measurement of the whole run.
    assert project_to_completion(measured(2.0), fraction=0.5).quantity.status == "estimated"


def test_a_projection_from_a_smuggled_value_stays_open() -> None:
    # A placeholder that carries a number is an invalid model. Projecting it
    # would launder the smuggled value into a result the validator can no
    # longer see, so the projection stays open and carries no number.
    weak = Quantity(value=2.0, unit="kWh", status="placeholder")
    projected = project_to_completion(weak, fraction=0.5)
    assert projected.quantity.status == "TODO"
    assert projected.quantity.value is None


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


def test_a_workload_read_as_compute_bound_gains_the_arithmetic_ratio() -> None:
    projected = project_to_machine(
        runtime=measured(1000.0, "s"), source_key="A100", target_key="H100", compute_bound=True
    )
    assert projected.quantity.value == pytest.approx(1000.0 * 312 / 989, rel=1e-6)


def test_a_workload_read_as_memory_bound_gains_only_the_bandwidth_ratio() -> None:
    # The H100 has 3.2x the arithmetic of an A100 and 2.2x the bandwidth. Single
    # stream generation moves weights and waits, so it gets the 2.2x, and a model
    # that promised the 3.2x would understate the bill by a third.
    projected = project_to_machine(
        runtime=measured(1000.0, "s"), source_key="A100", target_key="H100", compute_bound=False
    )
    assert projected.quantity.value == pytest.approx(1000.0 * 1555 / 3350, rel=1e-6)


def test_when_nobody_knows_which_limit_applies_the_slower_ratio_is_reported() -> None:
    # The slower ratio is the longer run, the larger bill, and the number a reader
    # is not harmed by having believed. The faster one is still on the record.
    projected = project_to_machine(
        runtime=measured(1000.0, "s"), source_key="A100", target_key="H100"
    )
    assert projected.quantity.value == pytest.approx(1000.0 * 1555 / 3350, rel=1e-6)
    assert projected.bounds is not None
    fastest, slowest = projected.bounds
    assert fastest.value == pytest.approx(1000.0 * 312 / 989, rel=1e-6)
    assert slowest.value == pytest.approx(projected.quantity.value, rel=1e-6)


def test_the_bracket_is_serialised_as_two_quantities() -> None:
    # Two quantities, not two bare numbers: everything with a number in this
    # package carries its own status, and a bound is no exception.
    mapping = project_to_machine(
        runtime=measured(1000.0, "s"), source_key="A100", target_key="H100"
    ).to_mapping()
    assert set(mapping["bounds"]) == {"fastest", "slowest"}
    for bound in mapping["bounds"].values():
        assert bound["status"] == "estimated"
        assert isinstance(bound["value"], float)


def test_a_part_with_no_bandwidth_figure_says_the_number_is_an_upper_bound() -> None:
    # Without both bandwidths there is no bracket, and the compute ratio alone is
    # the optimistic end. Saying so is the difference between an estimate and a
    # claim.
    catalog = Catalog(
        name="hardware",
        data={
            "gpus": [
                {
                    "key": "SOURCE",
                    "peak_bf16_tflops": 100,
                    "source_url": "https://example.invalid/source",
                    "retrieved_date": "2026-09-14",
                },
                {
                    "key": "TARGET",
                    "peak_bf16_tflops": 400,
                    "source_url": "https://example.invalid/target",
                    "retrieved_date": "2026-09-14",
                },
            ]
        },
    )
    projected = project_to_machine(
        runtime=measured(1000.0, "s"),
        source_key="SOURCE",
        target_key="TARGET",
        overlay_catalog=catalog,
    )
    assert not projected.refused
    assert projected.bounds is None
    assert projected.quantity.value == pytest.approx(250.0)
    assert any("upper bound" in limit for limit in projected.limits)


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
    assert "peak_bf16_tflops" in str(projection.quantity.notes)
    assert "T4" in str(projection.quantity.notes)


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
    assert ("312" in method and "989" in method) or ("1555" in method and "3350" in method)
    assert "/" in method


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


def test_a_smaller_target_board_is_said_before_the_number_is_used() -> None:
    # 80 GB of measured work does not fit on a 24 GB card. Nothing here knows how
    # much of the board the run actually used, so this is a warning rather than a
    # refusal, and it has to come before anybody acts on the duration.
    projection = project_to_machine(
        runtime=measured(100.0, "s"), source_key="A100-80GB", target_key="RTX-4090"
    )
    assert not projection.refused
    assert any("may" in limit and "not start" in limit for limit in projection.limits)
    assert projection.limits[0].startswith("RTX-4090 has 24 GB")


def test_a_larger_target_board_says_nothing_about_memory() -> None:
    projection = project_to_machine(
        runtime=measured(100.0, "s"), source_key="RTX-4090", target_key="H100"
    )
    assert not any("not start" in limit for limit in projection.limits)


# --- Onto another processor --------------------------------------------------
#
# A processor has two speeds and they do not move together: one thread on one
# core, and every core busy at once. A part with many slow cores wins the second
# and loses the first, so "the faster chip" is not a question with one answer.
# Which speed a workload follows is measurable — processor-seconds over
# wall-clock seconds — and these tests are about that measurement deciding.

_BENCHMARK = "SPEC CPU 2017 rate base, per socket"


def _cpus(**overrides: object) -> Catalog:
    """A two-row processor catalogue: few fast cores against many slow ones."""
    rows = {
        "cpus": [
            {
                "key": "few-fast",
                "single_thread_score": 100.0,
                "throughput_score": 400.0,
                "benchmark": _BENCHMARK,
                "cores": 8,
            },
            {
                "key": "many-slow",
                "single_thread_score": 80.0,
                "throughput_score": 1600.0,
                "benchmark": _BENCHMARK,
                "cores": 64,
            },
        ]
    }
    for key, value in overrides.items():
        for row in rows["cpus"]:
            if value is None:
                row.pop(key, None)
            else:
                row[key] = value
    return Catalog("hardware", rows)


def _project(**kwargs: object) -> object:
    return project_to_processor(
        runtime=Quantity(value=100.0, unit="s", status="measured"),
        source_key="few-fast",
        target_key="many-slow",
        overlay_catalog=_cpus(),
        **kwargs,  # type: ignore[arg-type]
    )


def test_a_single_threaded_run_follows_the_single_threaded_score() -> None:
    # The target's cores are slower one at a time. A run using one of them gets
    # *worse*, and the projection says so rather than promising the 4x the
    # throughput score would suggest.
    projected = _project(parallelism=1.0)
    assert projected.quantity.value == pytest.approx(125.0)
    assert "single-threaded score ratio" in projected.method


def test_a_run_that_saturates_the_chip_follows_the_throughput_score() -> None:
    projected = _project(parallelism=7.0)
    assert projected.quantity.value == pytest.approx(25.0)
    assert "all-core throughput" in projected.method


def test_an_unmeasured_parallelism_takes_the_slower_end() -> None:
    # The slower ratio is the longer run and the larger bill: the number a
    # reader is not harmed by having believed.
    projected = _project()
    assert projected.quantity.value == pytest.approx(125.0)
    assert "nothing having measured" in projected.method


def test_a_half_busy_chip_settles_nothing_and_says_so() -> None:
    projected = _project(parallelism=4.0)
    assert projected.quantity.value == pytest.approx(125.0)
    assert "neither one core nor most of them" in projected.method


def test_the_bracket_holds_both_ends() -> None:
    projected = _project(parallelism=1.0)
    assert projected.bounds is not None
    fastest, slowest = projected.bounds
    assert fastest.value == pytest.approx(25.0)
    assert slowest.value == pytest.approx(125.0)


def test_a_processor_projection_is_never_stronger_than_estimated() -> None:
    assert _project(parallelism=1.0).quantity.status == "estimated"


def test_two_different_benchmarks_are_refused_rather_than_divided() -> None:
    # A SPEC score over a Geekbench score is a number with no meaning, and it
    # would look exactly like a number with one.
    catalog = _cpus()
    catalog.data["cpus"][1]["benchmark"] = "Geekbench 6 multi-core"
    projected = project_to_processor(
        runtime=Quantity(value=100.0, unit="s", status="measured"),
        source_key="few-fast",
        target_key="many-slow",
        overlay_catalog=catalog,
    )
    assert projected.refused
    assert "scores of the same benchmark" in str(projected.quantity.notes)


def test_no_scores_at_all_is_refused_with_the_recipe_for_fixing_it() -> None:
    catalog = _cpus(single_thread_score=None, throughput_score=None)
    projected = project_to_processor(
        runtime=Quantity(value=100.0, unit="s", status="measured"),
        source_key="few-fast",
        target_key="many-slow",
        overlay_catalog=catalog,
    )
    assert projected.refused
    notes = str(projected.quantity.notes)
    assert "clock speed and core count do not give one" in notes
    assert "spec.org" in notes
    assert "divide it by the number of sockets" in notes


def test_one_score_projects_but_admits_it_brackets_nothing() -> None:
    catalog = _cpus(throughput_score=None)
    projected = project_to_processor(
        runtime=Quantity(value=100.0, unit="s", status="measured"),
        source_key="few-fast",
        target_key="many-slow",
        overlay_catalog=catalog,
    )
    assert not projected.refused
    assert projected.bounds is None
    assert any("brackets this" in limit for limit in projected.limits)


def test_half_a_ratio_is_not_a_ratio() -> None:
    # The source has a score and the target does not. Dividing by the one that
    # exists would be scaling by nothing.
    catalog = _cpus()
    catalog.data["cpus"][1].pop("single_thread_score")
    catalog.data["cpus"][1].pop("throughput_score")
    projected = project_to_processor(
        runtime=Quantity(value=100.0, unit="s", status="measured"),
        source_key="few-fast",
        target_key="many-slow",
        overlay_catalog=catalog,
    )
    assert projected.refused


def test_an_unknown_processor_names_the_ones_that_are_known() -> None:
    projected = project_to_processor(
        runtime=Quantity(value=100.0, unit="s", status="measured"),
        source_key="few-fast",
        target_key="not-a-cpu",
        overlay_catalog=_cpus(),
    )
    assert projected.refused
    assert "'not-a-cpu'" in str(projected.quantity.notes)
    assert "few-fast" in str(projected.quantity.notes)


def test_a_runtime_with_no_number_projects_onto_no_processor_either() -> None:
    projected = project_to_processor(
        runtime=Quantity(status="TODO"),
        source_key="few-fast",
        target_key="many-slow",
        overlay_catalog=_cpus(),
    )
    assert projected.refused


def test_the_bundled_catalogue_carries_core_counts_where_it_states_them() -> None:
    # The projection reads `cores` to decide whether a measured parallelism
    # means "most of the chip". A row whose own notes state the count should
    # carry it as a field rather than as prose.
    rows = Catalog.bundled("hardware").rows("cpus")
    assert rows["epyc-9654"]["cores"] == 96
    assert rows["xeon-gold-6248"]["cores"] == 20
