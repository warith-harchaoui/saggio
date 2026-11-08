"""The footprint of a whole machine, and the note that says how to supply one.

Why this file exists
--------------------
Manufacturers publish carbon footprints for the products they sell, a Mac or a
rack server, far more often than for the chips inside them. So the catalogue
has a ``machines`` section matched on the identifier the firmware gives, and
the embodied assumption reads it between the accelerator and the processor.
And when no row answers, the ``TODO`` has to say how to close it, with the
command written out, or it hands the reader a search instead of a step.

Author
------
Warith Harchaoui
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

import saggio.estimate.machine as machine_module
from saggio.auditor.assumptions import _embodied_assumption
from saggio.auditor.options import AuditOptions
from saggio.cli.commands import _footprint_keeps_its_own_source
from saggio.estimate.machine import MachineProfile, detect_machine, machine_model, match_machine

#: A whole-machine row, shaped as the bundled ones are.
LAPTOP: dict[str, Any] = {
    "key": "test-laptop",
    "vendor": "Example",
    "name": "Example Laptop 14",
    "model_identifiers": ["Example14,1"],
    "embodied_kgco2e": 120.5,
    "embodied_scope": "Production phase for the base configuration.",
    "embodied_source_url": "https://example.invalid/per.pdf",
    "embodied_retrieved_date": "2026-11-08",
    "source_url": "https://example.invalid/per.pdf",
    "retrieved_date": "2026-11-08",
}


def overlay_with(tmp_path: Path, **sections: list[dict[str, Any]]) -> Path:
    """Write a hardware overlay holding these sections, and return its folder."""
    (tmp_path / "hardware.yaml").write_text(yaml.safe_dump(sections), encoding="utf-8")
    return tmp_path


def test_a_machine_is_matched_on_the_identifier_its_firmware_gives(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(machine_module, "machine_model", lambda platform: "Example14,1")
    profile = detect_machine(overlay=overlay_with(tmp_path, machines=[LAPTOP]))
    assert (profile.machine_model, profile.machine_key) == ("Example14,1", "test-laptop")


def test_a_neighbouring_model_is_not_a_match() -> None:
    # The 16-inch laptop is not the 14-inch one, however close the names.
    rows = {"test-laptop": LAPTOP}
    assert match_machine("Example14,2", rows) is None
    assert match_machine("Example14", rows) is None


def test_a_placeholder_product_name_names_no_machine(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # Unbranded boards answer with a sentence nobody wrote for them; matching a
    # row on it would match every such board in the world.
    name = tmp_path / "product_name"
    name.write_text("To Be Filled By O.E.M.\n", encoding="utf-8")
    monkeypatch.setattr(machine_module, "_DMI_PRODUCT_NAME", name)
    assert machine_model("linux") is None
    name.write_text("PowerEdge R760\n", encoding="utf-8")
    assert machine_model("linux") == "PowerEdge R760"


def test_the_machine_footprint_answers_before_the_processor(tmp_path: Path) -> None:
    folder = overlay_with(tmp_path, machines=[LAPTOP])
    profile = MachineProfile(
        "darwin", cpu_key="epyc-7742", machine_model="Example14,1", machine_key="test-laptop"
    )
    figure = _embodied_assumption(profile, AuditOptions(overlay=folder))
    assert figure.value == pytest.approx(120.5)
    assert figure.source_url == LAPTOP["embodied_source_url"]
    assert figure.notes == LAPTOP["embodied_scope"]


def test_an_accelerator_still_answers_before_the_machine(tmp_path: Path) -> None:
    # Work on a card reserves that card, and the card is what its footprint covers.
    folder = overlay_with(tmp_path, machines=[LAPTOP])
    profile = MachineProfile(
        "linux",
        gpu_key="H100",
        accelerator_count=1,
        machine_model="Example14,1",
        machine_key="test-laptop",
    )
    assert _embodied_assumption(profile, AuditOptions(overlay=folder)).value == pytest.approx(164.0)


def test_an_open_footprint_says_how_to_close_it_with_the_command_written_out(
    tmp_path: Path,
) -> None:
    profile = MachineProfile("darwin", cpu_key="apple-m3-max", machine_model="Mac15,9")
    figure = _embodied_assumption(profile, AuditOptions(overlay=tmp_path))
    assert figure.status == "TODO"
    assert "assumptions.hardware_embodied_carbon" in figure.notes
    assert "saggio catalog add cpu apple-m3-max" in figure.notes
    assert 'model_identifiers="Mac15,9"' in figure.notes
    assert "saggio catalog read-pcf" in figure.notes


def test_a_machine_already_catalogued_is_not_offered_again(tmp_path: Path) -> None:
    folder = overlay_with(tmp_path, machines=[{**LAPTOP, "embodied_kgco2e": None}])
    profile = MachineProfile(
        "darwin", cpu_key="apple-m3-max", machine_model="Example14,1", machine_key="test-laptop"
    )
    notes = _embodied_assumption(profile, AuditOptions(overlay=folder)).notes
    assert "saggio catalog add machine" not in notes


def test_a_footprint_added_to_a_known_row_keeps_the_row_s_own_source() -> None:
    # The wattage was read off a datasheet; the footprint was not. Writing the
    # footprint's link into source_url would re-attribute the wattage.
    row = {
        "key": "H100",
        "source_url": "https://pcf.invalid",
        "retrieved_date": "2026-11-08",
        "embodied_kgco2e": 164.0,
    }
    kept = _footprint_keeps_its_own_source("gpu", row)
    assert kept["embodied_source_url"] == "https://pcf.invalid"
    assert kept["embodied_retrieved_date"] == "2026-11-08"
    assert kept["source_url"] != "https://pcf.invalid"


def test_a_new_row_takes_the_footprint_s_source_for_both() -> None:
    row = {
        "key": "never-seen",
        "source_url": "https://pcf.invalid",
        "retrieved_date": "2026-11-08",
        "embodied_kgco2e": 90.0,
    }
    kept = _footprint_keeps_its_own_source("machine", row)
    assert kept["source_url"] == kept["embodied_source_url"] == "https://pcf.invalid"


def test_a_row_with_other_columns_is_left_as_written() -> None:
    row = {
        "key": "H100",
        "source_url": "https://datasheet.invalid",
        "retrieved_date": "2026-11-08",
        "tdp_w": 700,
        "embodied_kgco2e": 164.0,
    }
    assert _footprint_keeps_its_own_source("gpu", row) == row
