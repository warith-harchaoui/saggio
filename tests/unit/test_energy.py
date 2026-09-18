"""The Green Algorithms chain, and the two distinctions it keeps."""

from __future__ import annotations

import pytest

from saggio.catalog import Catalog
from saggio.estimate.energy import (
    MEMORY_POWER_W_PER_GB,
    carbon_from_energy,
    energy_from_runtime,
    facility_energy,
    it_energy_from_runtime,
    money_from_energy,
    node_power,
    total_money,
    water_from_energy,
)
from saggio.model import Quantity

MEASURED = "measured"
ESTIMATED = "estimated"


def q(value: float | None, status: str = MEASURED, **kwargs: object) -> Quantity:
    return Quantity(value=value, status=status, **kwargs)  # type: ignore[arg-type]


# --- The arithmetic ----------------------------------------------------------


def test_an_hour_at_a_kilowatt_is_a_kilowatt_hour() -> None:
    assert it_energy_from_runtime(q(3600.0), q(1000.0)).value == pytest.approx(1.0)


def test_the_building_draws_the_machine_times_its_overhead() -> None:
    assert facility_energy(q(2.0), q(1.5)).value == pytest.approx(3.0)


def test_the_convenience_chains_both_steps() -> None:
    direct = energy_from_runtime(q(3600.0), q(1000.0), q(1.5))
    stepwise = facility_energy(it_energy_from_runtime(q(3600.0), q(1000.0)), q(1.5))
    assert direct.value == pytest.approx(stepwise.value)


def test_carbon_is_energy_times_intensity() -> None:
    assert carbon_from_energy(q(2.0), q(56)).value == pytest.approx(112.0)


def test_money_is_energy_times_price_and_keeps_the_currency() -> None:
    cost = money_from_energy(q(10.0), q(0.24, currency="EUR"))
    assert cost.value == pytest.approx(2.4)
    assert cost.currency == "EUR"


def test_water_is_machine_energy_times_effectiveness() -> None:
    assert water_from_energy(q(10.0), q(0.3)).value == pytest.approx(3.0)


def test_water_uses_machine_energy_not_facility_energy() -> None:
    # Water usage effectiveness is defined per kilowatt-hour of IT load. Feeding
    # it the facility figure would count the cooling overhead in both terms.
    machine = it_energy_from_runtime(q(3600.0), q(1000.0))
    facility = facility_energy(machine, q(1.5))
    assert water_from_energy(machine, q(1.0)).value < water_from_energy(facility, q(1.0)).value


# --- Confidence --------------------------------------------------------------


def test_a_result_takes_the_weakest_input_status() -> None:
    assert it_energy_from_runtime(q(3600.0, MEASURED), q(1.0, ESTIMATED)).status == ESTIMATED


@pytest.mark.parametrize(
    "compute",
    [
        lambda: it_energy_from_runtime(q(None, "TODO"), q(1.0)),
        lambda: facility_energy(q(1.0), q(None, "TODO")),
        lambda: carbon_from_energy(q(1.0), q(None, "TODO")),
        lambda: money_from_energy(q(1.0), q(None, "TODO")),
        lambda: water_from_energy(q(1.0), q(None, "TODO")),
    ],
)
def test_a_missing_input_yields_an_open_field_not_a_zero(compute) -> None:
    # "We do not know" and "it costs nothing" are different statements, and the
    # second one is the lie this whole package exists to prevent.
    result = compute()
    assert result.status == "TODO"
    assert result.value is None


def test_an_unresolved_country_leaves_carbon_open_with_its_unit_intact() -> None:
    carbon = carbon_from_energy(q(2.0), Quantity(unit="gCO2e/kWh", status="TODO"))
    assert carbon.unit == "gCO2e"
    assert carbon.value is None


# --- Node power --------------------------------------------------------------


def test_node_power_sums_cores_memory_and_accelerators() -> None:
    power = node_power(
        cpu_key="epyc-7742", physical_cores=64, memory_gb=512, gpu_key="A100", accelerator_count=1
    )
    expected = 3.5 * 64 + 512 * MEMORY_POWER_W_PER_GB + 400
    assert power.value == pytest.approx(expected)
    assert power.status == ESTIMATED


def test_node_power_scales_compute_but_not_memory_by_the_usage_factor() -> None:
    # The Green Algorithms core usage factor applies to processors and
    # accelerators; memory draws by being populated, not by being busy.
    power = node_power(
        cpu_key="epyc-7742",
        physical_cores=64,
        memory_gb=512,
        gpu_key="A100",
        accelerator_count=1,
        usage_factor=0.5,
    )
    expected = (3.5 * 64 + 400) * 0.5 + 512 * MEMORY_POWER_W_PER_GB
    assert power.value == pytest.approx(expected)
    assert "0.5 usage" in str(power.notes)


def test_node_power_refuses_a_usage_factor_outside_the_unit_interval() -> None:
    for bad in (0.0, -0.1, 1.5):
        with pytest.raises(ValueError, match="usage_factor"):
            node_power(cpu_key="epyc-7742", physical_cores=1, memory_gb=0, usage_factor=bad)


def test_node_power_without_a_cpu_is_open() -> None:
    assert node_power(cpu_key=None, physical_cores=8, memory_gb=16).status == "TODO"


def test_node_power_names_the_catalogue_row_that_is_missing() -> None:
    result = node_power(cpu_key="not-a-cpu", physical_cores=8, memory_gb=16)
    assert result.status == "TODO"
    assert "not-a-cpu" in str(result.notes)


def test_node_power_names_a_missing_accelerator_row() -> None:
    result = node_power(
        cpu_key="epyc-7742",
        physical_cores=8,
        memory_gb=16,
        gpu_key="not-a-gpu",
        accelerator_count=1,
    )
    assert "not-a-gpu" in str(result.notes)


def test_node_power_accepts_a_preloaded_catalogue(overlay) -> None:
    catalog = Catalog.load("hardware", overlay=overlay)
    assert node_power(
        cpu_key="epyc-7742", physical_cores=1, memory_gb=0, overlay_catalog=catalog
    ).is_known()


# --- Totals ------------------------------------------------------------------


def test_totalling_money_adds_and_weakens() -> None:
    total = total_money(
        Quantity(value=1.0, currency="USD", status=MEASURED),
        Quantity(value=2.0, currency="USD", status=ESTIMATED),
    )
    assert total.value == pytest.approx(3.0)
    assert total.status == ESTIMATED


def test_totalling_refuses_to_mix_currencies() -> None:
    total = total_money(
        Quantity(value=1.0, currency="USD", status=MEASURED),
        Quantity(value=1.0, currency="EUR", status=MEASURED),
    )
    assert total.status == "TODO"
    assert "different currencies" in str(total.notes)


def test_an_unknown_term_opens_the_total_rather_than_counting_as_zero() -> None:
    total = total_money(
        Quantity(value=5.0, currency="USD", status=MEASURED),
        Quantity(currency="USD", status="TODO"),
    )
    # A sum missing a term is not the total, so no number is claimed; what the
    # known terms came to is kept in the notes, where it cannot be mistaken for
    # a figure the model may quote.
    assert total.value is None
    assert total.status == "TODO"
    assert total.currency == "USD"
    assert "5 USD so far" in str(total.notes)


def test_totalling_nothing_is_open() -> None:
    assert total_money().status == "TODO"


# --- Holes the first audit found, kept closed ----------------------------------


def test_a_smuggled_value_on_a_todo_is_not_computed_with() -> None:
    # A TODO carrying a number is an invalid model; the estimator must not
    # launder that number into a result carrying a value.
    smuggled = Quantity(value=3600.0, status="TODO")
    result = it_energy_from_runtime(smuggled, q(1000.0))
    assert result.status == "TODO"
    assert result.value is None


def test_totalling_refuses_a_currencyless_amount_next_to_a_currency() -> None:
    total = total_money(
        Quantity(value=1.0, status=MEASURED),
        Quantity(value=2.0, currency="USD", status=MEASURED),
    )
    assert total.status == "TODO"
    assert "no currency" in str(total.notes)


def test_node_power_notes_state_the_arithmetic_that_produced_the_value() -> None:
    # Zero cores are clamped to one; the note must show the clamped figure, or
    # the stated formula would not reproduce the number beside it.
    power = node_power(cpu_key="epyc-7742", physical_cores=0, memory_gb=0)
    assert "1 cores" in str(power.notes)
    assert power.value == pytest.approx(3.5)


def test_a_negative_runtime_is_a_sign_error_not_a_cost() -> None:
    result = it_energy_from_runtime(q(-3600.0), q(1000.0))
    assert result.status == "TODO"
    assert "sign error" in str(result.notes)


def test_a_negative_intensity_does_not_produce_negative_carbon() -> None:
    result = carbon_from_energy(q(2.0), q(-56.0))
    assert result.status == "TODO"
    assert result.value is None
