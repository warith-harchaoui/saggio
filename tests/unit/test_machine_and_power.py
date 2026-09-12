"""The machine, and whether it will tell us what it draws."""

from __future__ import annotations

from pathlib import Path

import pytest

from running_code_cost_helper.analyze.power import (
    PowerMeter,
    PowerReading,
    read_package_energy_microjoules,
    unavailable_reason,
)
from running_code_cost_helper.estimate.machine import (
    _GPU_PATTERNS,
    MachineProfile,
    _match_key,
    detect_machine,
)

# --- Matching the machine against the catalogue ------------------------------


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("NVIDIA A100-SXM4-80GB", "A100-80GB"),
        ("NVIDIA A100-PCIE-40GB", "A100-40GB"),
        ("NVIDIA H100 80GB HBM3", "H100"),
        ("NVIDIA GeForce RTX 4090", "RTX-4090"),
        ("Tesla T4", "T4"),
        ("AMD Instinct MI300X", "MI300X"),
    ],
)
def test_an_accelerator_is_matched_to_its_catalogue_key(name: str, expected: str) -> None:
    assert _match_key(name, _GPU_PATTERNS) == expected


def test_an_unreleased_chip_matches_nothing() -> None:
    assert _match_key("Some Unreleased Accelerator", _GPU_PATTERNS) is None


def test_this_machine_is_detected_without_raising(overlay: Path) -> None:
    # Hardware probing must never abort an audit: an unreadable machine gives a
    # profile full of nothing, which is an honest answer.
    profile = detect_machine(overlay=overlay)
    assert profile.platform in {"darwin", "linux", "windows"}
    assert profile.physical_cores >= 1
    assert profile.logical_cores >= 1


def test_a_machine_describes_itself_in_one_line() -> None:
    described = MachineProfile(
        "linux",
        cpu_model="EPYC 7742",
        physical_cores=64,
        gpu_names=("NVIDIA A100",),
        accelerator_count=1,
    ).describe()
    assert "EPYC 7742" in described and "A100" in described


def test_apple_silicon_is_not_counted_twice() -> None:
    # The GPU is part of the package the CPU figure already covers.
    assert not MachineProfile("darwin", apple_chip="Apple M2 Max").has_accelerator()


def test_the_profile_serialises_only_facts_about_the_machine() -> None:
    mapping = MachineProfile("linux", cpu_model="X", physical_cores=4, logical_cores=8).to_mapping()
    assert mapping["logical_cores"] == 8
    assert "catalog_misses" not in mapping


def test_an_unknown_device_names_itself_so_somebody_can_add_it() -> None:
    profile = MachineProfile("linux", catalog_misses=("GPU 'Future-1' is not in the catalogue",))
    assert "Future-1" in profile.catalog_misses[0]


# --- Power -------------------------------------------------------------------


def test_reading_the_counter_gives_a_number_or_nothing() -> None:
    value = read_package_energy_microjoules()
    assert value is None or value >= 0


def test_the_reason_names_the_platform_limitation() -> None:
    assert len(unavailable_reason()) > 40


def test_a_machine_with_no_counter_measures_nothing() -> None:
    assert not PowerMeter(started_at=None).stop(seconds=1.0).measured()


def test_a_run_too_short_to_divide_by_measures_nothing() -> None:
    assert PowerMeter(started_at=0).stop(seconds=0.0).watts is None


def test_a_counter_that_went_backwards_is_not_a_measurement(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # A wrapped or reset counter gives a difference that is not energy, and
    # reporting it as one would be worse than admitting there is none.
    monkeypatch.setattr(
        "running_code_cost_helper.analyze.power.read_package_energy_microjoules", lambda: 5
    )
    reading = PowerMeter(started_at=1_000_000).stop(seconds=1.0)
    assert reading.watts is None
    assert "wrapped or reset" in reading.scope


def test_a_real_reading_divides_energy_by_time(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "running_code_cost_helper.analyze.power.read_package_energy_microjoules",
        lambda: 2_000_000,
    )
    reading = PowerMeter(started_at=0).stop(seconds=2.0)
    assert reading.measured()
    assert reading.watts == pytest.approx(1.0)
    assert reading.joules == pytest.approx(2.0)


def test_the_scope_of_a_reading_is_stated() -> None:
    assert "package" in PowerReading(1.0, 1.0, "Intel RAPL counts the package").scope
