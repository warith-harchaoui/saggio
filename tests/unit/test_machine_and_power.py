"""The machine, and whether it will tell us what it draws."""

from __future__ import annotations

from pathlib import Path

import pytest

from saggio.analyze.power import (
    AcceleratorSampler,
    PowerMeter,
    PowerReading,
    _query_nvidia_smi,
    read_package_energy_microjoules,
    unavailable_reason,
)
from saggio.estimate.machine import (
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
    monkeypatch.setattr("saggio.analyze.power.read_package_energy_microjoules", lambda: 5)
    reading = PowerMeter(started_at=1_000_000).stop(seconds=1.0)
    assert reading.watts is None
    assert "wrapped or reset" in reading.scope


def test_a_real_reading_divides_energy_by_time(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "saggio.analyze.power.read_package_energy_microjoules",
        lambda: 2_000_000,
    )
    reading = PowerMeter(started_at=0).stop(seconds=2.0)
    assert reading.measured()
    assert reading.watts == pytest.approx(1.0)
    assert reading.joules == pytest.approx(2.0)


def test_the_scope_of_a_reading_is_stated() -> None:
    assert "package" in PowerReading(1.0, 1.0, "Intel RAPL counts the package").scope


class _StubProcess:
    """A logging process that is already over, for the parsing tests."""

    def terminate(self) -> None:
        return None

    def wait(self, timeout: float | None = None) -> int:
        return 0

    def kill(self) -> None:
        return None


def _sampler_over(readings: str, tmp_path: Path) -> AcceleratorSampler:
    log = tmp_path / "watts.log"
    log.write_text(readings, encoding="utf-8")
    return AcceleratorSampler(process=_StubProcess(), log_path=log)  # type: ignore[arg-type]


def test_a_board_that_does_not_know_voids_the_query(monkeypatch: pytest.MonkeyPatch) -> None:
    # Two boards where one answers "[N/A]" is not an answer about the machine,
    # and half a machine's power presented as the machine's would be wrong.
    monkeypatch.setattr("saggio.analyze.power.shutil.which", lambda _: "/usr/bin/nvidia-smi")

    class _Completed:
        returncode = 0
        stdout = "250.4\n[N/A]\n"

    monkeypatch.setattr("saggio.analyze.power.subprocess.run", lambda *a, **k: _Completed())
    assert _query_nvidia_smi("power.draw") is None


def test_no_driver_means_no_answer(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("saggio.analyze.power.shutil.which", lambda _: None)
    assert _query_nvidia_smi("power.draw") is None


def test_a_single_sample_is_not_an_average(tmp_path: Path) -> None:
    # One reading taken at an arbitrary instant is not a mean over a run, and a
    # training run's power varies by hundreds of watts between steps.
    assert _sampler_over("300.0\n", tmp_path).stop() is None


def test_the_mean_comes_with_the_number_of_readings_it_is(tmp_path: Path) -> None:
    sampled = _sampler_over("100.0\n200.0\n300.0\n", tmp_path)
    result = sampled.stop()
    assert result is not None
    mean_watts, count = result
    assert mean_watts == pytest.approx(200.0)
    assert count == 3


def test_noise_in_the_log_is_not_counted_as_a_reading(tmp_path: Path) -> None:
    result = _sampler_over("100.0\n[N/A]\n300.0\n", tmp_path).stop()
    assert result is not None
    assert result == (pytest.approx(200.0), 2)


def test_the_accelerator_counter_is_added_to_the_package(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # A processor drawing 50 W beside a board drawing 300 W is a 350 W machine,
    # and reporting only the 50 W is the failure this whole path exists to fix.
    monkeypatch.setattr("saggio.analyze.power.read_package_energy_microjoules", lambda: 100_000_000)
    monkeypatch.setattr("saggio.analyze.power.read_accelerator_energy_millijoules", lambda: 600_000)
    reading = PowerMeter(started_at=0, accelerator_started_at=0).stop(seconds=2.0)
    assert reading.measured()
    assert reading.watts == pytest.approx(50.0 + 300.0)
    assert reading.sources == ("processor package", "accelerator")
    assert "added" in reading.scope


def test_a_machine_with_only_a_board_says_the_processor_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Windows and Apple Silicon have no package counter. An accelerator figure
    # there is worth having, and worth labelling as the accelerator alone.
    monkeypatch.setattr("saggio.analyze.power.read_package_energy_microjoules", lambda: None)
    monkeypatch.setattr("saggio.analyze.power.read_accelerator_energy_millijoules", lambda: 600_000)
    reading = PowerMeter(started_at=None, accelerator_started_at=0).stop(seconds=2.0)
    assert reading.watts == pytest.approx(300.0)
    assert reading.sources == ("accelerator",)
    assert "not included" in reading.scope


def test_a_package_alone_still_says_what_it_misses(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("saggio.analyze.power.read_package_energy_microjoules", lambda: 2_000_000)
    monkeypatch.setattr("saggio.analyze.power.read_accelerator_energy_millijoules", lambda: None)
    reading = PowerMeter(started_at=0).stop(seconds=2.0)
    assert reading.sources == ("processor package",)
    assert "accelerator" in reading.scope


def test_an_accelerator_counter_that_went_backwards_is_not_a_measurement(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("saggio.analyze.power.read_package_energy_microjoules", lambda: 2_000_000)
    monkeypatch.setattr("saggio.analyze.power.read_accelerator_energy_millijoules", lambda: 5)
    reading = PowerMeter(started_at=0, accelerator_started_at=600_000).stop(seconds=2.0)
    assert reading.sources == ("processor package",)


def test_the_sampled_figure_says_how_many_readings_it_averaged(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr("saggio.analyze.power.read_package_energy_microjoules", lambda: None)
    meter = PowerMeter(started_at=None, sampler=_sampler_over("100.0\n300.0\n", tmp_path))
    reading = meter.stop(seconds=4.0)
    assert reading.watts == pytest.approx(200.0)
    assert "2 readings" in reading.scope
    assert reading.joules == pytest.approx(800.0)


def test_a_run_too_short_to_average_still_stops_the_sampler(tmp_path: Path) -> None:
    # The logging process outlives nothing: a meter stopped at zero seconds must
    # not leave a driver writing to a temporary file nobody will read.
    sampler = _sampler_over("100.0\n300.0\n", tmp_path)
    assert PowerMeter(started_at=None, sampler=sampler).stop(seconds=0.0).watts is None
    assert not (tmp_path / "watts.log").exists()
