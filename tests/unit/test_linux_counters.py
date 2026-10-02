"""The Linux power and processor counters, exercised from a machine that is not Linux.

Why this file exists
--------------------
The Linux readers were the least covered code in the package, and the reason was
circular: they are only exercised on Linux, the developer's machine is a Mac, and
so the branches that read ``/proc/stat`` and the powercap tree were never run by
anybody until a real Linux box ran them in anger. Shrinking continuous
integration to a single Linux job made that worse rather than better -- CI runs
the Linux branches now, but on a runner whose sysfs tree publishes no RAPL zones
at all, so the code still falls straight through its first guard.

Nothing here mocks the readers. Each test builds the actual files the kernel
would publish -- the same names, the same layout, the same formats -- and points
the module's own path constants at them. What is being tested is the parsing and
the arithmetic, which is all of these functions that can be wrong.

The trees are the real shapes, taken from the kernel's own documentation:
``/proc/stat`` as ``Documentation/filesystems/proc.rst`` describes it, and
``/sys/class/powercap`` as ``Documentation/power/powercap/powercap.rst`` does.

Author
------
Warith Harchaoui
"""

from __future__ import annotations

from pathlib import Path

import pytest

from saggio.analyze import cpu as cpu_module

# The RAPL readers moved into the module that owns them when power became a
# package. Patching the package's re-export would not reach them: `rapl.py`
# imports the glob, so the name it looks up lives there. Patch where it is
# looked up, not where it is defined.
from saggio.analyze.power import rapl as power_module

# --- The processor counter ----------------------------------------------------

#: A real first line of /proc/stat: user, nice, system, idle, iowait, irq,
#: softirq, steal, guest, guest_nice, in USER_HZ ticks since boot.
PROC_STAT_BODY = (
    "cpu  120000 3000 40000 900000 5000 100 2000 0 0 0\n"
    "cpu0 60000 1500 20000 450000 2500 50 1000 0 0 0\n"
    "cpu1 60000 1500 20000 450000 2500 50 1000 0 0 0\n"
    "intr 12345678\n"
    "ctxt 98765432\n"
    "btime 1759000000\n"
)


def write_proc_stat(tmp_path: Path, body: str) -> Path:
    """Write a /proc/stat and return its path."""
    path = tmp_path / "stat"
    path.write_text(body, encoding="utf-8")
    return path


def test_busy_seconds_exclude_idle_and_io_wait(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # A processor waiting on a disk is not doing work anybody should be charged
    # for. Counting it would shrink every share by whatever the machine happened
    # to be waiting on, which is the one way this number can be quietly wrong.
    monkeypatch.setattr(cpu_module, "PROC_STAT", write_proc_stat(tmp_path, PROC_STAT_BODY))
    ticks_per_second = float(__import__("os").sysconf("SC_CLK_TCK"))

    # user + nice + system + irq + softirq + steal, with idle and iowait dropped.
    busy_ticks = 120000 + 3000 + 40000 + 100 + 2000
    assert cpu_module._linux_cpu_seconds() == pytest.approx(busy_ticks / ticks_per_second)


def test_every_column_after_the_known_ones_still_counts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The kernel has added columns to this line over the years and may again.
    # Summing everything and subtracting the two idle columns is what makes a
    # future column count as busy rather than vanish.
    body = "cpu  100 0 0 0 0 0 0 0 0 0 7\n"
    monkeypatch.setattr(cpu_module, "PROC_STAT", write_proc_stat(tmp_path, body))
    ticks_per_second = float(__import__("os").sysconf("SC_CLK_TCK"))
    assert cpu_module._linux_cpu_seconds() == pytest.approx(107 / ticks_per_second)


@pytest.mark.parametrize(
    ("body", "why"),
    [
        ("", "an empty file"),
        ("btime 1759000000\n", "a first line that is not the cpu total"),
        ("cpu  one two three four\n", "counts that are not numbers"),
        ("cpu  1 2 3\n", "fewer columns than the format defines"),
    ],
)
def test_a_counter_it_cannot_read_is_no_counter_at_all(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, body: str, why: str
) -> None:
    # None, never zero. A zero here would be a measurement saying the machine did
    # no work, which is the kind of invented number this package exists to refuse.
    monkeypatch.setattr(cpu_module, "PROC_STAT", write_proc_stat(tmp_path, body))
    assert cpu_module._linux_cpu_seconds() is None, why


def test_an_absent_proc_stat_reads_as_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(cpu_module, "PROC_STAT", tmp_path / "not-there")
    assert cpu_module._linux_cpu_seconds() is None


def test_a_machine_with_no_tick_rate_reports_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Ticks are meaningless without the rate that turns them into seconds.
    monkeypatch.setattr(cpu_module, "PROC_STAT", write_proc_stat(tmp_path, PROC_STAT_BODY))
    monkeypatch.setattr(cpu_module.os, "sysconf", lambda _name: 0)
    assert cpu_module._linux_cpu_seconds() is None


# --- The energy counters ------------------------------------------------------


def build_powercap(tmp_path: Path, zones: dict[str, dict[str, object]]) -> str:
    """Build a powercap tree and return the glob that finds its zones.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Where to build it.
    zones : dict
        Directory name, as sysfs spells it, to the files it should contain.
        Flat, like the real tree: ``intel-rapl:0`` and ``intel-rapl:0:0`` are
        siblings there, each a symlink into the device tree, not nested.

    Returns
    -------
    str
        A glob matching the zones, shaped like the one the module uses.
    """
    root = tmp_path / "powercap"
    root.mkdir(exist_ok=True)
    for directory, files in zones.items():
        here = root / directory
        here.mkdir(parents=True, exist_ok=True)
        for filename, content in files.items():
            (here / filename).write_text(f"{content}\n", encoding="utf-8")
    return str(root / "[ai]*-rapl:*")


def test_a_package_and_its_subzones_are_told_apart(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The whole reason each zone's own `name` file is read rather than its
    # directory name: a memory subzone's energy sits *outside* the package
    # figure, while a core subzone's sits inside it. A reader that went by
    # directory shape could not tell them apart and would double-count.
    glob = build_powercap(
        tmp_path,
        {
            "intel-rapl:0": {"name": "package-0", "energy_uj": 5_000_000},
            "intel-rapl:0:0": {"name": "core", "energy_uj": 3_000_000},
            "intel-rapl:0:1": {"name": "dram", "energy_uj": 900_000},
        },
    )
    monkeypatch.setattr(power_module, "RAPL_ZONE_GLOB", glob)

    assert sorted(name for name, _ in power_module._zones()) == ["core", "dram", "package-0"]
    # The compute figure is the package alone, not the package plus its children.
    assert power_module.read_package_energy_microjoules() == 5_000_000
    # And memory is read separately, because it is not inside that figure.
    assert power_module.read_memory_energy_microjoules() == 900_000


def test_both_sockets_of_a_two_socket_machine_are_counted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    glob = build_powercap(
        tmp_path,
        {
            "intel-rapl:0": {"name": "package-0", "energy_uj": 4_000_000},
            "intel-rapl:1": {"name": "package-1", "energy_uj": 6_000_000},
        },
    )
    monkeypatch.setattr(power_module, "RAPL_ZONE_GLOB", glob)
    assert power_module.read_package_energy_microjoules() == 10_000_000


def test_psys_is_used_alone_because_it_already_contains_the_packages(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Summing psys with the packages it contains would report the machine
    # roughly twice. This is the arithmetic that cannot be checked by looking.
    glob = build_powercap(
        tmp_path,
        {
            "intel-rapl:0": {"name": "package-0", "energy_uj": 4_000_000},
            "intel-rapl:1": {"name": "psys", "energy_uj": 9_000_000},
        },
    )
    monkeypatch.setattr(power_module, "RAPL_ZONE_GLOB", glob)
    assert power_module.read_package_energy_microjoules() == 9_000_000


def test_amd_zones_are_found_too(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # The glob is `[ai]*-rapl:*` for exactly this: amd-rapl as well as intel-rapl.
    glob = build_powercap(tmp_path, {"amd-rapl:0": {"name": "package-0", "energy_uj": 2_500_000}})
    monkeypatch.setattr(power_module, "RAPL_ZONE_GLOB", glob)
    assert power_module.read_package_energy_microjoules() == 2_500_000


def test_a_zone_with_no_energy_file_is_not_a_zone(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    glob = build_powercap(
        tmp_path,
        {
            "intel-rapl:0": {"name": "package-0"},
            "intel-rapl:1": {"name": "package-1", "energy_uj": 7_000_000},
        },
    )
    monkeypatch.setattr(power_module, "RAPL_ZONE_GLOB", glob)
    assert [name for name, _ in power_module._zones()] == ["package-1"]
    assert power_module.read_package_energy_microjoules() == 7_000_000


def test_one_unreadable_zone_does_not_void_a_readable_one(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Half a measurement is worse than none only if it is reported as whole.
    # Here the readable zone is reported, and the caller is not told the figure
    # covers both -- which is why the scope sentence names the zones it read.
    glob = build_powercap(
        tmp_path,
        {
            "intel-rapl:0": {"name": "package-0", "energy_uj": 1_000_000},
            "intel-rapl:1": {"name": "package-1", "energy_uj": "not a number"},
        },
    )
    monkeypatch.setattr(power_module, "RAPL_ZONE_GLOB", glob)
    assert power_module.read_package_energy_microjoules() == 1_000_000


def test_a_machine_that_publishes_nothing_reports_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Which is the case on every cloud runner, including the one CI uses, and
    # the reason these tests exist rather than relying on CI to exercise them.
    monkeypatch.setattr(power_module, "RAPL_ZONE_GLOB", str(tmp_path / "empty" / "*"))
    assert power_module._zones() == []
    assert power_module.read_package_energy_microjoules() is None
    assert power_module.read_memory_energy_microjoules() is None


def test_memory_is_nothing_when_the_machine_publishes_no_memory_zone(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Not zero. A machine without the counter drew memory power all the same;
    # saying zero would be inventing the one number nobody measured.
    glob = build_powercap(tmp_path, {"intel-rapl:0": {"name": "package-0", "energy_uj": 3_000_000}})
    monkeypatch.setattr(power_module, "RAPL_ZONE_GLOB", glob)
    assert power_module.read_memory_energy_microjoules() is None


def test_every_memory_zone_of_a_two_socket_machine_is_summed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    glob = build_powercap(
        tmp_path,
        {
            "intel-rapl:0": {"name": "package-0", "energy_uj": 4_000_000},
            "intel-rapl:0:1": {"name": "dram", "energy_uj": 500_000},
            "intel-rapl:1": {"name": "package-1", "energy_uj": 4_000_000},
            "intel-rapl:1:1": {"name": "dram", "energy_uj": 600_000},
        },
    )
    monkeypatch.setattr(power_module, "RAPL_ZONE_GLOB", glob)
    assert power_module.read_memory_energy_microjoules() == 1_100_000


# --- The graphics device, from a tree this machine does not have ----------------


def build_hwmon(tmp_path: Path, nodes: dict[str, dict[str, object]]) -> str:
    """Build a graphics hwmon tree and return the glob that finds it.

    The real shape: Linux hangs a monitoring node off each graphics device at
    ``/sys/class/drm/card*/device/hwmon/hwmon*``, and the driver writes its own
    name in a ``name`` file beside the sensors. That name is what separates a
    graphics device from the dozen other hwmon nodes a machine publishes.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Where to build it.
    nodes : dict
        Node directory name to the files it should contain.

    Returns
    -------
    str
        A glob matching the nodes, shaped like the one the module uses.
    """
    root = tmp_path / "drm"
    for directory, files in nodes.items():
        here = root / directory / "device" / "hwmon" / "hwmon0"
        here.mkdir(parents=True, exist_ok=True)
        for filename, content in files.items():
            (here / filename).write_text(f"{content}\n", encoding="utf-8")
    return str(root / "card*" / "device" / "hwmon" / "hwmon*")


def point_graphics_at(monkeypatch: pytest.MonkeyPatch, glob: str) -> None:
    """Point every reader of the graphics glob at this tree.

    Two modules look the name up: the one that finds the directories and the
    one that probes them for a report. Patching the package's re-export would
    reach neither.
    """
    from saggio.analyze.power import graphics

    monkeypatch.setattr(graphics, "GRAPHICS_HWMON_GLOB", glob)


def test_an_amd_card_publishing_a_counter_is_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from saggio.analyze.power import graphics

    point_graphics_at(
        monkeypatch,
        build_hwmon(tmp_path, {"card0": {"name": "amdgpu", "energy1_input": 7_000_000}}),
    )
    assert len(graphics._graphics_hwmon_directories()) == 1
    assert graphics.read_graphics_energy_microjoules() == 7_000_000


def test_an_intel_card_publishing_instantaneous_watts_is_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # i915 and xe publish microwatts rather than a running total, so the figure
    # is a sample rather than a counter and the scope sentence has to say so.
    from saggio.analyze.power import graphics

    point_graphics_at(
        monkeypatch,
        build_hwmon(tmp_path, {"card0": {"name": "i915", "power1_average": 23_000_000}}),
    )
    assert graphics.read_graphics_watts() == pytest.approx(23.0)
    assert graphics.read_graphics_energy_microjoules() is None


def test_a_node_that_is_not_a_graphics_driver_is_not_a_graphics_device(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # A machine publishes hwmon nodes for fans, batteries and chipsets. Reading
    # the driver's own name is what keeps a fan tachometer out of the energy
    # figure.
    from saggio.analyze.power import graphics

    point_graphics_at(
        monkeypatch,
        build_hwmon(tmp_path, {"card0": {"name": "nouveau", "energy1_input": 5_000_000}}),
    )
    assert graphics._graphics_hwmon_directories() == []
    assert graphics.read_graphics_energy_microjoules() is None


def test_two_cards_are_summed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from saggio.analyze.power import graphics

    point_graphics_at(
        monkeypatch,
        build_hwmon(
            tmp_path,
            {
                "card0": {"name": "amdgpu", "energy1_input": 3_000_000},
                "card1": {"name": "amdgpu", "energy1_input": 4_000_000},
            },
        ),
    )
    assert graphics.read_graphics_energy_microjoules() == 7_000_000


# --- What the capability report says about a machine it is not running on ------


def test_a_graphics_counter_is_reported_as_readable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from saggio.analyze import capability

    point_graphics_at(
        monkeypatch,
        build_hwmon(tmp_path, {"card0": {"name": "amdgpu", "energy1_input": 9_000_000}}),
    )
    found = capability._graphics_interface()
    assert found.state == "reads"
    assert "no privileges" in found.detail


def test_a_machine_with_no_graphics_sensor_says_so_plainly(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from saggio.analyze import capability

    point_graphics_at(monkeypatch, str(tmp_path / "nothing" / "*"))
    found = capability._graphics_interface()
    assert found.state == "absent"
    assert "No graphics device" in found.detail


def test_a_sensor_this_user_cannot_read_is_blocked_rather_than_absent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The distinction the whole report exists for.

    Absent means the machine does not publish it; blocked means it does and
    this user may not read it. Collapsing the two would tell somebody to go
    looking for hardware they already have.
    """
    import os

    from saggio.analyze import capability

    glob = build_hwmon(tmp_path, {"card0": {"name": "amdgpu", "energy1_input": 9_000_000}})
    point_graphics_at(monkeypatch, glob)
    import glob as globbing

    for directory in globbing.glob(glob):
        (Path(directory) / "energy1_input").chmod(0o000)
    try:
        found = capability._graphics_interface()
        # Running as root defeats the permission, and that is not a failure of
        # the code under test; skip rather than assert something untrue.
        if os.getuid() == 0:
            pytest.skip("root can read a file with no permission bits")
        assert found.state == "blocked"
    finally:
        for directory in globbing.glob(glob):
            (Path(directory) / "energy1_input").chmod(0o644)
