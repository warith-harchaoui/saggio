"""The second way of telling a run apart from the machine it ran on."""

from __future__ import annotations

import pytest

from saggio.analyze.cpu import (
    MINIMUM_MACHINE_SECONDS,
    CpuShare,
    CpuShareMeter,
    machine_cpu_seconds,
    unavailable_reason,
)
from saggio.analyze.power import PowerReading
from saggio.analyze.run import SliceResult

# --- Reading the machine's own total -----------------------------------------


def test_the_machine_reports_a_positive_total_or_says_it_cannot() -> None:
    total = machine_cpu_seconds()
    assert total is None or total > 0.0


def test_the_total_only_goes_forwards() -> None:
    first = machine_cpu_seconds()
    if first is None:
        pytest.skip("this platform publishes no machine-wide processor time")
    for _ in range(200_000):
        pass
    assert machine_cpu_seconds() >= first


def test_a_platform_that_cannot_answer_says_why() -> None:
    assert "processor time" in unavailable_reason() or "does not publish" in unavailable_reason()


# --- The share ---------------------------------------------------------------


def test_a_meter_with_no_opening_reading_refuses() -> None:
    share = CpuShareMeter(started_at=None).stop(run_cpu_seconds=1.0)
    assert not share.known()
    assert share.reason


def test_an_unknown_run_time_refuses() -> None:
    share = CpuShareMeter(started_at=100.0).stop(run_cpu_seconds=None)
    assert not share.known()
    assert "processor time is unknown" in str(share.reason)


def test_a_window_too_short_for_the_counter_refuses_with_the_number(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import saggio.analyze.cpu as cpu

    monkeypatch.setattr(cpu, "machine_cpu_seconds", lambda: 100.1)
    share = CpuShareMeter(started_at=100.0).stop(run_cpu_seconds=0.05)
    assert not share.known()
    assert f"{MINIMUM_MACHINE_SECONDS:g}" in str(share.reason)


def test_a_part_larger_than_the_whole_is_refused_rather_than_clamped(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Clamping to 1.0 would turn a sign that one counter is wrong into a
    # confident number.
    import saggio.analyze.cpu as cpu

    monkeypatch.setattr(cpu, "machine_cpu_seconds", lambda: 102.0)
    share = CpuShareMeter(started_at=100.0).stop(run_cpu_seconds=5.0)
    assert not share.known()
    assert "cannot both be right" in str(share.reason)


def test_a_counter_that_went_backwards_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    import saggio.analyze.cpu as cpu

    monkeypatch.setattr(cpu, "machine_cpu_seconds", lambda: 99.0)
    assert not CpuShareMeter(started_at=100.0).stop(run_cpu_seconds=1.0).known()


def test_a_sound_window_gives_the_ratio(monkeypatch: pytest.MonkeyPatch) -> None:
    import saggio.analyze.cpu as cpu

    monkeypatch.setattr(cpu, "machine_cpu_seconds", lambda: 104.0)
    share = CpuShareMeter(started_at=100.0).stop(run_cpu_seconds=1.0)
    assert share.share == pytest.approx(0.25)
    assert share.machine_seconds == pytest.approx(4.0)


def test_the_share_serialises_its_evidence_not_just_its_answer() -> None:
    mapping = CpuShare(share=0.25, run_seconds=1.0, machine_seconds=4.0).to_mapping()
    assert mapping == {"share": 0.25, "run_cpu_seconds": 1.0, "machine_cpu_seconds": 4.0}


def test_a_refusal_serialises_the_reason() -> None:
    assert "unknown_because" in CpuShare(reason="no counter here").to_mapping()


# --- What the share may price ------------------------------------------------


def half() -> CpuShare:
    return CpuShare(share=0.5, run_seconds=1.0, machine_seconds=2.0)


def test_a_split_reading_is_attributed_on_the_processors_own_figure() -> None:
    reading = PowerReading(60.0, 60.0, "soc", by_domain={"cpu": 40.0, "gpu": 20.0})
    result = SliceResult(("x",), 0, 1.0, reading, cpu_share=half())
    assert result.attributed_watts() == pytest.approx(20.0)
    assert "processor cores alone" in str(result.attributed_scope())


def test_a_processor_only_reading_is_attributed_whole() -> None:
    reading = PowerReading(60.0, 60.0, "processor package")
    assert SliceResult(("x",), 0, 1.0, reading, cpu_share=half()).attributed_watts() == 30.0


def test_one_number_covering_an_accelerator_is_refused() -> None:
    # A run that keeps a GPU busy on almost no processor time would be
    # attributed almost none of a draw that was mostly the GPU's.
    reading = PowerReading(60.0, 60.0, "processor package and accelerator board")
    result = SliceResult(("x",), 0, 1.0, reading, cpu_share=half())
    assert result.attributed_watts() is None
    assert result.attributed_scope() is None


def test_no_share_means_no_attribution() -> None:
    reading = PowerReading(60.0, 60.0, "processor package")
    assert SliceResult(("x",), 0, 1.0, reading).attributed_watts() is None


def test_the_two_answers_are_both_reported_when_both_exist() -> None:
    reading = PowerReading(60.0, 60.0, "processor package", by_domain={"cpu": 60.0})
    result = SliceResult(
        ("x",), 0, 1.0, reading, baseline=PowerReading(10.0, 10.0, "idle"), cpu_share=half()
    )
    mapping = result.to_mapping()
    assert mapping["idle_watts"] == 10.0
    assert mapping["attributed_watts"] == 30.0
    assert "attributed_scope" in mapping


def test_the_measured_split_reaches_the_model() -> None:
    reading = PowerReading(20.0, 20.0, "soc", by_domain={"cpu": 18.0, "memory": 2.0})
    mapping = SliceResult(("x",), 0, 1.0, reading).to_mapping()
    assert mapping["power_by_domain"] == {"cpu": 18.0, "memory": 2.0}


def test_the_split_is_structural_context_not_a_cost() -> None:
    from saggio.model.schema import is_bare_number_exempt

    assert is_bare_number_exempt("measurement.power_by_domain.cpu")
    assert is_bare_number_exempt("measurement.cpu_share.share")
    assert is_bare_number_exempt("measurement.attributed_watts")


# --- The figure --------------------------------------------------------------


def test_the_figure_draws_a_row_per_subsystem() -> None:
    from saggio.report.figures import power_by_domain

    svg = power_by_domain({"cpu": 18.5, "gpu": 0.1, "memory": 2.3})
    assert svg.count("<rect") == 3
    assert "Processor cores" in svg
    assert "Measured, not modelled" in svg


def test_a_chip_with_nothing_split_apart_gets_no_figure() -> None:
    from saggio.report.figures import power_by_domain

    assert power_by_domain({}) == ""
    assert power_by_domain({"cpu": 0.0}) == ""
