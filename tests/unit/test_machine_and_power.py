"""The machine, and whether it will tell us what it draws."""

from __future__ import annotations

from pathlib import Path

import pytest

from saggio.analyze import power
from saggio.analyze.power import (
    AcceleratorSampler,
    PowerMeter,
    PowerReading,
    _query_nvidia_smi,
    read_package_energy_microjoules,
    unavailable_reason,
)
from saggio.analyze.power import meter as power_meter
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
    assert profile.platform in {"darwin", "linux"}
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
    monkeypatch.setattr("saggio.analyze.power.meter.read_package_energy_microjoules", lambda: 5)
    reading = PowerMeter(started_at=1_000_000).stop(seconds=1.0)
    assert reading.watts is None
    assert "wrapped or reset" in reading.scope


def test_a_real_reading_divides_energy_by_time(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "saggio.analyze.power.meter.read_package_energy_microjoules",
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
    monkeypatch.setattr(
        "saggio.analyze.power.accelerator.shutil.which", lambda _: "/usr/bin/nvidia-smi"
    )

    class _Completed:
        returncode = 0
        stdout = "250.4\n[N/A]\n"

    monkeypatch.setattr(
        "saggio.analyze.power.accelerator.subprocess.run", lambda *a, **k: _Completed()
    )
    assert _query_nvidia_smi("power.draw") is None


def test_no_driver_means_no_answer(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("saggio.analyze.power.accelerator.shutil.which", lambda _: None)
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
    monkeypatch.setattr(
        "saggio.analyze.power.meter.read_package_energy_microjoules", lambda: 100_000_000
    )
    monkeypatch.setattr(
        "saggio.analyze.power.meter.read_accelerator_energy_millijoules", lambda: 600_000
    )
    reading = PowerMeter(started_at=0, accelerator_started_at=0).stop(seconds=2.0)
    assert reading.measured()
    assert reading.watts == pytest.approx(50.0 + 300.0)
    assert reading.sources == ("processor package", "accelerator")
    assert "added" in reading.scope


def test_a_machine_with_only_a_board_says_the_processor_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Apple Silicon has no package counter of the Intel kind. An accelerator figure
    # there is worth having, and worth labelling as the accelerator alone.
    monkeypatch.setattr("saggio.analyze.power.meter.read_package_energy_microjoules", lambda: None)
    monkeypatch.setattr(
        "saggio.analyze.power.meter.read_accelerator_energy_millijoules", lambda: 600_000
    )
    reading = PowerMeter(started_at=None, accelerator_started_at=0).stop(seconds=2.0)
    assert reading.watts == pytest.approx(300.0)
    assert reading.sources == ("accelerator",)
    assert "not included" in reading.scope


def test_a_package_alone_still_says_what_it_misses(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "saggio.analyze.power.meter.read_package_energy_microjoules", lambda: 2_000_000
    )
    monkeypatch.setattr(
        "saggio.analyze.power.meter.read_accelerator_energy_millijoules", lambda: None
    )
    reading = PowerMeter(started_at=0).stop(seconds=2.0)
    assert reading.sources == ("processor package",)
    assert "accelerator" in reading.scope


def test_an_accelerator_counter_that_went_backwards_is_not_a_measurement(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "saggio.analyze.power.meter.read_package_energy_microjoules", lambda: 2_000_000
    )
    monkeypatch.setattr("saggio.analyze.power.meter.read_accelerator_energy_millijoules", lambda: 5)
    reading = PowerMeter(started_at=0, accelerator_started_at=600_000).stop(seconds=2.0)
    assert reading.sources == ("processor package",)


def test_the_sampled_figure_says_how_many_readings_it_averaged(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr("saggio.analyze.power.meter.read_package_energy_microjoules", lambda: None)
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


# --- The sysfs layer, on a tree we control ------------------------------------
#
# None of this can be exercised on the machine the tests happen to run on: a Mac
# has no powercap tree and a laptop has no second socket. So the tree is built
# here, zone by zone, exactly as the kernel lays it out, and the readers are
# pointed at it. What is being tested is the reading of a *shape*, and the shape
# is documented in the kernel's own ABI.


def _zone(root: Path, directory: str, name: str, **files: str) -> Path:
    """Write one powercap zone the way the kernel publishes it."""
    path = root / directory
    path.mkdir(parents=True)
    (path / "name").write_text(name, encoding="utf-8")
    for filename, contents in files.items():
        (path / filename).write_text(contents, encoding="utf-8")
    return path


def _point_at(monkeypatch: pytest.MonkeyPatch, root: Path) -> None:
    monkeypatch.setattr("saggio.analyze.power.rapl.RAPL_ZONE_GLOB", f"{root}/[ai]*-rapl:*")


def test_two_sockets_are_counted_whole(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _zone(tmp_path, "intel-rapl:0", "package-0", energy_uj="1000")
    _zone(tmp_path, "intel-rapl:1", "package-1", energy_uj="2000")
    _point_at(monkeypatch, tmp_path)
    assert power.read_package_energy_microjoules() == 3000


def test_a_core_subzone_is_not_added_to_the_package_it_is_inside(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # core and uncore are already inside package-0. Adding them would report the
    # processor at up to twice what it drew.
    _zone(tmp_path, "intel-rapl:0", "package-0", energy_uj="1000")
    _zone(tmp_path, "intel-rapl:0:0", "core", energy_uj="900")
    _zone(tmp_path, "intel-rapl:0:1", "uncore", energy_uj="50")
    _point_at(monkeypatch, tmp_path)
    assert power.read_package_energy_microjoules() == 1000


def test_the_memory_zone_is_read_separately_because_it_is_outside_the_package(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # dram sits under package-0 in the tree but its energy is not in package-0's
    # figure, so a machine that publishes it has been under-reported until now.
    _zone(tmp_path, "intel-rapl:0", "package-0", energy_uj="1000")
    _zone(tmp_path, "intel-rapl:0:2", "dram", energy_uj="400")
    _point_at(monkeypatch, tmp_path)
    assert power.read_package_energy_microjoules() == 1000
    assert power.read_memory_energy_microjoules() == 400


def test_the_system_zone_replaces_the_packages_it_contains(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # psys covers the whole system-on-chip, packages included. Summing both
    # would count the processor twice.
    _zone(tmp_path, "intel-rapl:0", "package-0", energy_uj="1000")
    _zone(tmp_path, "intel-rapl:1", "psys", energy_uj="2500")
    _point_at(monkeypatch, tmp_path)
    assert power.read_package_energy_microjoules() == 2500


def test_an_amd_zone_is_read_like_an_intel_one(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _zone(tmp_path, "amd-rapl:0", "package-0", energy_uj="777")
    _point_at(monkeypatch, tmp_path)
    assert power.read_package_energy_microjoules() == 777


def test_a_zone_without_a_counter_is_not_a_zone(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _zone(tmp_path, "intel-rapl:0", "package-0")
    _point_at(monkeypatch, tmp_path)
    assert power.read_package_energy_microjoules() is None


def test_one_counter_wrap_is_recovered_and_says_what_it_assumed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # The counter ran from 900 of a 1000-unit range to 100: it passed the
    # ceiling once, and 200 units is the energy that means.
    monkeypatch.setattr("saggio.analyze.power.meter.read_package_energy_microjoules", lambda: 100)
    reading = PowerMeter(started_at=900, wrap_range=1_000_000).stop(seconds=1.0)
    assert reading.measured()
    assert reading.watts == pytest.approx((1_000_000 + 100 - 900) / 1_000_000)
    assert "passed its ceiling once" in reading.scope
    assert "1 W" in reading.scope


def test_a_counter_reset_is_refused_even_when_the_range_is_known(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Ending below the start by more than the range is not a wrap, it is a
    # machine that zeroed the counter; two unknowable totals make no difference.
    monkeypatch.setattr("saggio.analyze.power.meter.read_package_energy_microjoules", lambda: 10)
    reading = PowerMeter(started_at=5_000_000, wrap_range=1000).stop(seconds=1.0)
    assert reading.watts is None
    assert "reset" in reading.scope


def test_a_wrap_without_a_published_range_is_still_refused(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("saggio.analyze.power.meter.read_package_energy_microjoules", lambda: 5)
    reading = PowerMeter(started_at=1_000_000, wrap_range=None).stop(seconds=1.0)
    assert reading.watts is None


def test_measured_memory_is_added_and_announced(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "saggio.analyze.power.meter.read_package_energy_microjoules", lambda: 2_000_000
    )
    monkeypatch.setattr(
        "saggio.analyze.power.meter.read_memory_energy_microjoules", lambda: 1_000_000
    )
    reading = PowerMeter(started_at=0, memory_started_at=0).stop(seconds=2.0)
    assert reading.watts == pytest.approx(1.5)
    assert reading.sources == ("processor package", "memory")
    assert "Memory is measured rather than estimated" in reading.scope


# --- The graphics drivers Linux ships ----------------------------------------


def _graphics(root: Path, directory: str, name: str, **files: str) -> Path:
    path = root / directory
    path.mkdir(parents=True)
    (path / "name").write_text(name, encoding="utf-8")
    for filename, contents in files.items():
        (path / filename).write_text(contents, encoding="utf-8")
    return path


def test_an_intel_graphics_counter_is_read_exactly(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _graphics(tmp_path, "hwmon0", "xe", energy1_input="5000000")
    monkeypatch.setattr("saggio.analyze.power.graphics.GRAPHICS_HWMON_GLOB", f"{tmp_path}/hwmon*")
    assert power.read_graphics_energy_microjoules() == 5_000_000


def test_an_amd_board_publishes_watts_rather_than_a_total(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _graphics(tmp_path, "hwmon0", "amdgpu", power1_average="119095000")
    monkeypatch.setattr("saggio.analyze.power.graphics.GRAPHICS_HWMON_GLOB", f"{tmp_path}/hwmon*")
    assert power.read_graphics_energy_microjoules() is None
    assert power.read_graphics_watts() == pytest.approx(119.095)


def test_a_sensor_belonging_to_another_driver_is_left_alone(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # A hwmon node hanging off a graphics card can belong to something that is
    # not the graphics chip; only the three drivers that publish board power
    # are read.
    _graphics(tmp_path, "hwmon0", "nvme", energy1_input="42")
    monkeypatch.setattr("saggio.analyze.power.graphics.GRAPHICS_HWMON_GLOB", f"{tmp_path}/hwmon*")
    assert power.read_graphics_energy_microjoules() is None


def test_the_graphics_counter_is_used_when_no_nvidia_board_answered(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("saggio.analyze.power.meter.read_package_energy_microjoules", lambda: None)
    monkeypatch.setattr(
        "saggio.analyze.power.meter.read_graphics_energy_microjoules", lambda: 4_000_000
    )
    reading = PowerMeter(started_at=None, graphics_started_at=0).stop(seconds=2.0)
    assert reading.watts == pytest.approx(2.0)
    assert reading.sources == ("accelerator",)
    assert "needs neither a vendor tool nor administrator rights" in reading.scope


# --- A meter that reads nothing does not make you wait for it -----------------


def test_a_meter_with_no_counter_reads_nothing() -> None:
    from saggio.analyze.power import PowerMeter

    assert not PowerMeter(started_at=None).reads_anything()


@pytest.mark.parametrize(
    "field",
    [
        "started_at",
        "accelerator_started_at",
        "memory_started_at",
        "graphics_started_at",
    ],
)
def test_any_single_counter_answering_is_enough(field: str) -> None:
    from saggio.analyze.power import PowerMeter

    assert PowerMeter(**{"started_at": None, field: 1}).reads_anything()


def test_the_baseline_does_not_wait_when_nothing_can_measure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # The second bought a reading that says "not measured", which the meter can
    # say immediately. On a machine with no counters — a container, an ARM board —
    # every slice was paying it.
    import saggio.analyze.power as power

    monkeypatch.setattr(power.PowerMeter, "start", classmethod(lambda cls: cls(started_at=None)))
    slept: list[float] = []
    monkeypatch.setattr(power_meter.time, "sleep", slept.append)

    reading = power.measure_for(5.0)

    assert slept == []
    assert not reading.measured()


def test_the_baseline_still_waits_when_something_answers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import saggio.analyze.power as power

    monkeypatch.setattr(
        power.PowerMeter, "start", classmethod(lambda cls: cls(started_at=1_000_000))
    )
    slept: list[float] = []
    monkeypatch.setattr(power_meter.time, "sleep", slept.append)

    power.measure_for(2.0)

    assert slept == [2.0]
