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


def test_an_unknown_term_drags_the_total_down_rather_than_counting_as_zero() -> None:
    total = total_money(
        Quantity(value=5.0, currency="USD", status=MEASURED),
        Quantity(currency="USD", status="TODO"),
    )
    assert total.value == pytest.approx(5.0)
    assert total.status == "TODO"


def test_totalling_nothing_is_open() -> None:
    assert total_money().status == "TODO"
