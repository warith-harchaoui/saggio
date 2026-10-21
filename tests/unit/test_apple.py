"""The Apple chip's own energy counters, and the arithmetic over them.

The library call itself cannot be tested off an Apple Silicon Mac, and is not
worth faking. What *is* worth testing, and what would silently produce a figure
wrong by a factor of two or a thousand, is the assembly: which channels are
summed, which are refused as a double count, and how a unit label becomes joules.
"""

from __future__ import annotations

import pytest

from saggio.analyze import apple
from saggio.analyze.apple import (
    _JOULES_PER_UNIT,
    SocEnergy,
    _assemble,
    available,
    soc_model_note,
    unavailable_reason,
)
from saggio.analyze.power import _soc_reading
from saggio.i18n import say


def test_the_rollup_is_preferred_over_the_clusters_it_rolls_up() -> None:
    # "CPU Energy" is the sum of the cluster channels beside it. Adding both
    # would report the processor at twice what it drew, and the number would
    # look entirely plausible.
    energy = _assemble(
        {
            "CPU Energy": 14.0,
            "EACC_CPU": 0.6,
            "PACC0_CPU": 6.7,
            "PACC1_CPU": 6.7,
            "GPU Energy": 1.0,
        }
    )
    assert energy is not None
    assert energy.by_domain["cpu"] == 14.0
    assert energy.compute_joules == 15.0


def test_the_clusters_are_summed_when_there_is_no_rollup() -> None:
    energy = _assemble({"EACC_CPU": 1.0, "PACC0_CPU": 2.0, "PACC1_CPU": 3.0})
    assert energy is not None
    assert energy.by_domain["cpu"] == 6.0


def test_a_sample_without_the_processor_is_not_a_measurement() -> None:
    # Every Apple chip reports its cores. A sample that does not is a sample
    # this package has misread, and half a chip is not a measurement of it.
    assert _assemble({"GPU Energy": 1.0, "DRAM0": 0.5}) is None


def test_memory_is_kept_out_of_the_compute_figure() -> None:
    energy = _assemble({"CPU Energy": 10.0, "DRAM0": 4.0})
    assert energy is not None
    assert energy.compute_joules == 10.0
    assert energy.memory_joules == 4.0


def test_a_missing_subsystem_is_simply_absent_rather_than_zero() -> None:
    energy = _assemble({"CPU Energy": 10.0})
    assert energy is not None
    assert energy.memory_joules is None
    assert "gpu" not in energy.by_domain


def test_every_unit_label_the_counters_use_is_known() -> None:
    # The graphics roll-up is published in nanojoules while the processor is in
    # millijoules on the same machine. A label assumed rather than read would be
    # wrong by a million.
    assert _JOULES_PER_UNIT["nj"] == 1e-9
    assert _JOULES_PER_UNIT["mj"] == 1e-3
    assert _JOULES_PER_UNIT["j"] == 1.0


def test_the_channels_that_produced_a_figure_are_named() -> None:
    energy = _assemble({"CPU Energy": 1.0, "GPU Energy": 1.0, "ANE0": 0.0, "DRAM0": 1.0})
    assert energy is not None
    assert set(energy.channels) == {"CPU Energy", "GPU Energy", "ANE0", "DRAM0"}


def test_a_reading_divides_energy_by_time_and_says_what_it_is() -> None:
    reading = _soc_reading(
        SocEnergy(20.0, 4.0, {"cpu": 18.0, "gpu": 2.0, "memory": 4.0}, ("CPU Energy", "DRAM0")),
        seconds=2.0,
    )
    assert reading.watts == 12.0
    assert reading.sources == ("system-on-chip", "memory")
    assert "CPU Energy" in reading.scope


def test_the_reading_always_says_the_counters_are_a_model() -> None:
    # Apple's figures are the chip's own model, not a meter on the rail, and the
    # vendor is explicit that they do not compare across machines. That caveat
    # ships with every figure rather than living in documentation nobody reads.
    reading = _soc_reading(SocEnergy(2.0, None, {"cpu": 2.0}, ("CPU Energy",)), seconds=1.0)
    assert soc_model_note() in reading.scope


def test_availability_and_its_reason_agree() -> None:
    # Either the counters answer, or there is a sentence saying why not. Never
    # both, and never neither.
    assert available() == (unavailable_reason() is None) or not available()


def test_a_library_that_loads_is_not_a_counter_that_answers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Availability is a reading that came back, not a successful library load.

    These were the same answer for as long as availability meant "the library
    loaded", and they are not the same answer on every Mac. One machine loads
    ``libIOReport.dylib``, publishes an energy group with no channel for the
    processor cores behind it, and so comes back unmeasured from every run --
    while the capability report said the counters read. Nothing compared the two
    claims until a test did, and then the report was the half that was wrong: a
    capability report is a promise about the next run, so the only honest way to
    make it is to have taken one.
    """
    monkeypatch.setattr(apple, "_counters_answer", lambda: False)
    assert not apple.available()


def test_a_mac_whose_counters_stay_silent_is_not_told_it_is_an_unknown_chip(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Three refusals on a Mac, and each one names a different machine.

    An Intel Mac, a chip whose channel names this package has never seen, and a
    chip that publishes no energy channel at all are three situations with three
    remedies. Collapsing the third into "Not an Apple Silicon Mac." -- which is
    what it said while availability was a library load -- tells the reader of an
    Apple Silicon runner something they can see is false, and the one thing they
    could have done about it (report the channel names) goes unsaid.
    """
    monkeypatch.setattr(apple.osh, "macos", lambda: True)
    monkeypatch.setattr(apple.platform, "machine", lambda: "arm64")
    monkeypatch.setattr(apple, "_load", lambda: (object(), object()))
    monkeypatch.setattr(apple, "_counters_answer", lambda: False)
    assert unavailable_reason() == say("apple.silent_counters")

    # And the chip nobody has taught this to read still gets its own sentence.
    monkeypatch.setattr(apple, "_load", lambda: None)
    assert unavailable_reason() == say("apple.unknown_layout")
