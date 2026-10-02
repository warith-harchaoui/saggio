"""Reading what this machine is, on machines that are not this one.

Why this file exists
--------------------
`detect_machine` turns what the operating system says about the hardware into
catalogue keys, and almost all of its branches are the ones that do *not* match:
a processor nobody has catalogued, two different accelerators in one box, an
overlay that has removed the generic rows. None of those happen on a developer's
laptop, and continuous integration runs on one cloud runner shape, so the paths
that matter most to somebody with unusual hardware were the least exercised.

Nothing here mocks the detection. Each test supplies the dictionary
``os_helper.hardware_info()` really returns -- the same keys, the same nesting,
taken from a live call -- and lets the real code read it.

Author
------
Warith Harchaoui
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

from saggio.estimate.machine import detect_machine

#: The shape a live call returns, with the fields the detection reads. Anything
#: not named here it does not look at, so inventing more would be inventing.
BASE: dict[str, Any] = {
    "platform": "linux",
    "cpu": {"physical_cores": 8, "logical_cores": 16, "model": "AMD EPYC 7742"},
    "ram_gb": 64.0,
    "gpu_vendor": "nvidia",
    "gpus": [],
}


def machine_saying(monkeypatch: pytest.MonkeyPatch, **over: Any) -> None:
    """Make the next detection read this hardware instead of the real one."""
    import saggio.estimate.machine as module

    info = BASE | over
    monkeypatch.setattr(module.osh, "hardware_info", lambda: info)


def catalogue_without_generics(tmp_path: Path) -> Path:
    """Return an overlay holding one real CPU and naming no generic rows.

    Written to prove something that turned out to be false: an overlay cannot
    remove a row, it merges over one. The test below asserts what actually
    happens instead.
    """
    (tmp_path / "hardware.yaml").write_text(
        yaml.safe_dump(
            {
                "schema_version": "2.1",
                "cpus": [
                    {
                        "key": "epyc-7742",
                        "w_per_core": 3.5,
                        "cores": 64,
                        "source_url": "https://example.invalid/epyc",
                        "retrieved_date": "2026-10-01",
                    }
                ],
                "gpus": [],
            }
        ),
        encoding="utf-8",
    )
    return tmp_path


def test_a_catalogued_processor_is_matched(monkeypatch: pytest.MonkeyPatch) -> None:
    machine_saying(monkeypatch)
    found = detect_machine()
    assert found.cpu_key == "epyc-7742"
    assert found.cpu_is_fallback is False
    assert found.catalog_misses == ()


def test_an_uncatalogued_processor_falls_back_and_says_which_row_to_add(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # A generic per-core wattage is a much weaker claim than a matched
    # datasheet, so a report has to be able to say which it has.
    machine_saying(
        monkeypatch, cpu={"physical_cores": 64, "logical_cores": 128, "model": "Imaginary Foo 9000"}
    )
    found = detect_machine()
    assert found.cpu_is_fallback is True
    assert found.cpu_key is not None
    assert any("Imaginary Foo 9000" in miss for miss in found.catalog_misses)
    assert any("saggio catalog add cpu" in miss for miss in found.catalog_misses)


def test_the_fallback_follows_the_core_count(monkeypatch: pytest.MonkeyPatch) -> None:
    machine_saying(
        monkeypatch, cpu={"physical_cores": 64, "logical_cores": 128, "model": "Imaginary Foo 9000"}
    )
    server = detect_machine().cpu_key
    machine_saying(
        monkeypatch, cpu={"physical_cores": 4, "logical_cores": 8, "model": "Imaginary Foo 9000"}
    )
    desktop = detect_machine().cpu_key
    assert server != desktop, "a 64-core box and a 4-core box got the same generic figure"


def test_an_overlay_cannot_remove_a_row_it_only_merges_over_one(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The premise a comment in the detection rested on, and it was false.

    An overlay that names no generic rows does not take them away:
    :meth:`Catalog.load` merges the overlay *over* the bundled catalogue, so
    the generic rows survive and the fallback still resolves. Worth a test of
    its own, because the opposite belief was written down in the code and
    would have been believed by the next person to read it.
    """
    machine_saying(
        monkeypatch, cpu={"physical_cores": 4, "logical_cores": 8, "model": "Imaginary Foo 9000"}
    )
    found = detect_machine(overlay=catalogue_without_generics(tmp_path))
    assert found.cpu_key is not None, "an overlay removed a bundled row"
    assert found.cpu_is_fallback is True


def test_a_catalogue_missing_even_its_generic_rows_yields_no_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Handing out a key the catalogue cannot honour would surface much later.

    It would arrive as a TODO telling the user to add the *fallback* row, which
    is a baffling thing to be told. Saying now that even the generic figure is
    unavailable is the honest shape of the same answer.

    Reachable only by the bundled rows going missing, which is an editing
    mistake rather than anything a user can do. The catalogue is stubbed here,
    and a contract test keeps the real rows in place.
    """
    import saggio.estimate.machine as module

    class OneCpu:
        """A catalogue holding a real processor and no generic fallback."""

        def rows(self, section: str) -> dict[str, Any]:
            """Return the rows of a section, as the real catalogue does."""
            return {"epyc-7742": {"w_per_core": 3.5}} if section == "cpus" else {}

    machine_saying(
        monkeypatch, cpu={"physical_cores": 4, "logical_cores": 8, "model": "Imaginary Foo 9000"}
    )
    monkeypatch.setattr(module.Catalog, "load", classmethod(lambda cls, *a, **k: OneCpu()))
    found = detect_machine()
    assert found.cpu_key is None
    assert found.cpu_is_fallback is False
    assert any("no per-core power" in miss for miss in found.catalog_misses)


def test_one_catalogued_accelerator_is_matched_and_counted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    machine_saying(
        monkeypatch, gpus=[{"name": "NVIDIA H100 80GB HBM3"}, {"name": "NVIDIA H100 80GB HBM3"}]
    )
    found = detect_machine()
    assert found.gpu_key == "H100"
    assert found.accelerator_count == 2


def test_an_uncatalogued_accelerator_is_counted_but_not_priced(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    machine_saying(monkeypatch, gpus=[{"name": "Imaginary Accelerator Z1"}])
    found = detect_machine()
    assert found.gpu_key is None
    assert found.accelerator_count == 1
    assert any("Imaginary Accelerator Z1" in miss for miss in found.catalog_misses)


def test_two_different_accelerators_resolve_to_neither(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Half a guess is worse than none.

    A box with an A100 and an H100 in it draws neither card's wattage, and
    picking one would put a number in a file nobody chose.
    """
    machine_saying(
        monkeypatch, gpus=[{"name": "NVIDIA A100-SXM4-40GB"}, {"name": "NVIDIA H100 80GB HBM3"}]
    )
    found = detect_machine()
    assert found.gpu_key is None
    assert found.accelerator_count == 2
    assert any("A100" in miss and "H100" in miss for miss in found.catalog_misses)


def test_a_machine_that_cannot_be_inspected_still_reports_its_platform(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # A container with no /proc, a locked-down host: the detection has to come
    # back with something rather than raise into an audit.
    import saggio.estimate.machine as module

    def refuse() -> dict[str, Any]:
        raise OSError("cannot inspect this machine")

    monkeypatch.setattr(module.osh, "hardware_info", refuse)
    found = detect_machine()
    assert found.platform in {"linux", "darwin", "windows"}
    assert found.cpu_key is None
    assert found.gpu_key is None


def test_an_apple_chip_is_read_from_the_field_that_names_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Apple Silicon reports no `cpu.model` worth matching; the chip arrives in
    # its own field, and the detection has to look there.
    machine_saying(
        monkeypatch,
        platform="darwin",
        cpu={"physical_cores": 12, "logical_cores": 12, "model": None},
        apple_chip="Apple M2 Max",
        gpu_vendor="apple",
    )
    found = detect_machine()
    assert found.cpu_key == "apple-m2-max"
    assert found.cpu_is_fallback is False
