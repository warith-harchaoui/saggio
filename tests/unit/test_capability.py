"""What the machine will tell us about its own power, and what it would take.

The point of these tests is the *distinction* the module exists to make: a
counter that is absent and a counter that is present but closed to this user are
different situations with different remedies, and conflating them tells a reader
nothing they can act on.
"""

from __future__ import annotations

import os
import pathlib
from pathlib import Path

import pytest

from saggio.analyze import capability
from saggio.analyze.capability import (
    ABSENT,
    BLOCKED,
    READS,
    ROOT_ONLY,
    STATES,
    Interface,
    measurable,
    paths_read,
    summary,
)


def _zone(root: Path, directory: str, name: str, **files: str) -> Path:
    path = root / directory
    path.mkdir(parents=True)
    (path / "name").write_text(name, encoding="utf-8")
    for filename, contents in files.items():
        (path / filename).write_text(contents, encoding="utf-8")
    return path


def _point_at(monkeypatch: pytest.MonkeyPatch, root: Path) -> None:
    monkeypatch.setattr("saggio.analyze.power.RAPL_ZONE_GLOB", f"{root}/[ai]*-rapl:*")


def test_every_interface_reports_a_known_state() -> None:
    assert all(interface.state in STATES for interface in capability.probe())


def test_the_probe_only_lists_this_platform() -> None:
    # A Linux user is not helped by being told macOS ships a tool they do not
    # have, so interfaces belonging to other platforms are left out entirely.
    names = [interface.name for interface in capability.probe()]
    assert len(names) == len(set(names))
    assert any("Baseboard" in name for name in names)


def test_no_counter_at_all_is_absent_not_blocked(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _point_at(monkeypatch, tmp_path)
    interface = capability._rapl_interface()
    assert interface.state == ABSENT
    assert interface.remedy is None
    assert "container" in interface.detail


def test_a_readable_counter_reads_and_names_its_zones(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _zone(tmp_path, "intel-rapl:0", "package-0", energy_uj="1000")
    _zone(tmp_path, "intel-rapl:0:2", "dram", energy_uj="400")
    _point_at(monkeypatch, tmp_path)
    interface = capability._rapl_interface()
    assert interface.state == READS
    assert "package-0" in interface.detail
    assert "memory" in interface.covers


def test_a_counter_closed_to_this_user_is_blocked_and_carries_the_remedy(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # This is the case the module exists for. Since Linux 5.10 the counter is
    # root-only by default, so on most servers this is what an ordinary user
    # meets, and "no counter found" would send them looking for the wrong thing.
    zone = _zone(tmp_path, "intel-rapl:0", "package-0", energy_uj="1000")
    os.chmod(zone / "energy_uj", 0o000)
    _point_at(monkeypatch, tmp_path)
    interface = capability._rapl_interface()
    assert interface.state == BLOCKED
    assert interface.remedy is not None
    assert "energy_uj" in interface.remedy


def test_the_remedy_never_arrives_without_the_reason_it_is_shut(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # Opening a published side channel is a decision about who shares the
    # machine. The command and the trade-off travel together or not at all.
    zone = _zone(tmp_path, "intel-rapl:0", "package-0", energy_uj="1000")
    os.chmod(zone / "energy_uj", 0o000)
    _point_at(monkeypatch, tmp_path)
    interface = capability._rapl_interface()
    assert "CVE-2020-8694" in interface.detail
    assert "PLATYPUS" in interface.detail


def test_nothing_here_escalates() -> None:
    # No interface's remedy is run; they are printed. The guarantee is worth a
    # test because the failure mode is silent and the blast radius is the
    # user's machine.
    text = summary()
    assert "sudo" not in text.replace("sudo chmod", "").replace("sudo powermetrics", "")


def test_a_tool_behind_a_password_is_root_only_rather_than_absent() -> None:
    interface = capability._powermetrics_interface()
    assert interface.state in {ROOT_ONLY, ABSENT}
    if interface.state == ROOT_ONLY:
        assert "will not ask" in interface.detail


def test_the_node_meter_is_named_but_never_reached() -> None:
    interface = capability._node_interface()
    assert interface.state == ROOT_ONLY
    assert "does not ask for them" in interface.detail


def test_the_summary_says_when_nothing_measures(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        capability,
        "probe",
        lambda: (Interface("x", "y", ABSENT, "nothing here"),),
    )
    text = summary()
    assert "estimated" in text
    assert "weaker number, not a" in text


def test_measurable_follows_the_probe(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(capability, "probe", lambda: (Interface("x", "y", ABSENT, "no"),))
    assert not measurable()
    monkeypatch.setattr(capability, "probe", lambda: (Interface("x", "y", READS, "yes"),))
    assert measurable()


def test_the_paths_read_are_disclosed(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _zone(tmp_path, "intel-rapl:0", "package-0", energy_uj="1000")
    _point_at(monkeypatch, tmp_path)
    assert any(path.endswith("energy_uj") for path in paths_read())


# --- The platforms this package supports, and the one it does not -------------


def test_the_two_supported_platforms_are_named() -> None:
    from saggio.analyze.capability import SUPPORTED_PLATFORMS

    assert SUPPORTED_PLATFORMS == ("linux", "darwin")


@pytest.mark.parametrize("platform", ["linux", "linux2", "darwin"])
def test_a_supported_platform_is_supported(platform: str) -> None:
    from saggio.analyze.capability import is_supported

    assert is_supported(platform)


@pytest.mark.parametrize("platform", ["win32", "cygwin", "aix"])
def test_an_unsupported_platform_is_not(platform: str) -> None:
    from saggio.analyze.capability import is_supported

    assert not is_supported(platform)


def test_the_package_refuses_to_import_on_an_unsupported_platform() -> None:
    # The refusal lives at import, so an unsupported platform meets a sentence
    # rather than a missing stdlib module three imports deeper.
    source = (pathlib.Path(__file__).resolve().parents[2] / "saggio" / "__init__.py").read_text(
        encoding="utf-8"
    )
    assert "raise ImportError(" in source
    assert "does not support" in source


def test_the_early_list_and_the_real_one_cannot_drift() -> None:
    # `saggio/__init__.py` repeats the tuple because it cannot import
    # `capability` that early without a cycle. This is what keeps the copy honest.
    import saggio
    from saggio.analyze.capability import SUPPORTED_PLATFORMS

    assert saggio.SUPPORTED_PLATFORMS == SUPPORTED_PLATFORMS


def test_nothing_probes_an_interface_for_a_platform_we_do_not_support() -> None:
    from saggio.analyze import capability

    assert not hasattr(capability, "_windows_interface")


def test_the_reason_says_what_is_missing_rather_than_apologising() -> None:
    from saggio.analyze.capability import UNSUPPORTED_REASON

    assert "Linux and macOS" in UNSUPPORTED_REASON
    for missing in ("energy counter", "processor-time", "resource accounting"):
        assert missing in UNSUPPORTED_REASON
