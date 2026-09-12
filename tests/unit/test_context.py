"""The deployment context, and the country ladder that refuses to guess."""

from __future__ import annotations

from pathlib import Path

import pytest

from running_code_cost_helper.estimate.context import (
    COUNTRY_ENVIRONMENT_VARIABLE,
    DeploymentContext,
    country_from_timezone,
    local_timezone_name,
)


def build(**kwargs) -> DeploymentContext:
    kwargs.setdefault("allow_timezone_inference", False)
    return DeploymentContext.build(**kwargs)


# --- The country ladder ------------------------------------------------------


def test_a_stated_country_is_a_human_assertion() -> None:
    context = build(country="FR")
    assert (context.country, context.country_status) == ("FR", "measured")


def test_a_stated_country_is_normalised() -> None:
    assert build(country=" fr ").country == "FR"


def test_the_environment_can_state_it(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(COUNTRY_ENVIRONMENT_VARIABLE, "se")
    context = build()
    assert (context.country, context.country_status) == ("SE", "measured")


def test_a_timezone_inference_is_only_an_estimate(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(COUNTRY_ENVIRONMENT_VARIABLE, raising=False)
    monkeypatch.setenv("TZ", "Europe/Paris")
    context = DeploymentContext.build(allow_timezone_inference=True)
    assert (context.country, context.country_status) == ("FR", "estimated")
    assert "timezone" in str(context.country_note)


def test_nothing_resolved_stays_open(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(COUNTRY_ENVIRONMENT_VARIABLE, raising=False)
    context = build()
    assert context.country is None
    assert context.country_status == "TODO"


def test_a_country_in_two_countries_timezone_resolves_to_neither() -> None:
    # Half a guess is worse than none: it would put a number in a file nobody chose.
    assert country_from_timezone("Antarctica/Troll") is None


def test_the_timezone_reader_returns_a_zone_or_nothing() -> None:
    name = local_timezone_name()
    assert name is None or "/" in name


def test_a_country_the_catalogue_does_not_know_is_still_the_users_word() -> None:
    context = build(country="ZZ")
    assert context.country == "ZZ"
    assert context.grid_intensity().status == "TODO"


# --- What the context implies ------------------------------------------------


def test_the_grid_intensity_comes_with_its_source() -> None:
    intensity = build(country="PL").grid_intensity()
    assert intensity.value == 773
    assert intensity.source_url
    assert intensity.retrieved_date


def test_norway_survives_yaml_reading_it_as_a_boolean() -> None:
    # Unquoted, YAML reads NO as false and Norway vanishes from the catalogue
    # with no error anywhere. The keys are quoted; this is the guard for it.
    assert build(country="NO").grid_intensity().value == 19


def test_an_inferred_country_carries_its_provenance_into_what_it_derives(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(COUNTRY_ENVIRONMENT_VARIABLE, raising=False)
    monkeypatch.setenv("TZ", "Europe/Paris")
    context = DeploymentContext.build(allow_timezone_inference=True)
    assert "timezone" in str(context.grid_intensity().notes)


def test_a_stated_country_does_not_clutter_the_notes() -> None:
    assert "timezone" not in str(build(country="FR").grid_intensity().notes)


def test_the_overhead_comes_from_the_provider() -> None:
    assert build(provider="gcp").pue().value == 1.09


def test_an_unknown_provider_leaves_the_overhead_open() -> None:
    assert build(provider="not-a-provider").pue().status == "TODO"


def test_a_provider_with_no_published_water_figure_leaves_water_open() -> None:
    water = build(provider="lambda").water_effectiveness()
    assert water.status == "TODO"
    assert "publishes no water" in str(water.notes)


def test_a_provider_that_publishes_one_gives_a_number() -> None:
    assert build(provider="gcp").water_effectiveness().value == 0.99


def test_a_cloud_price_falls_back_to_the_local_tariff_and_says_so() -> None:
    price = build(country="DE", provider="aws").electricity_price()
    assert price.currency == "USD"
    assert "machine-hours" in str(price.notes)


def test_no_country_leaves_the_price_open() -> None:
    assert build(provider="aws").electricity_price().status == "TODO"


def test_an_instance_gives_a_nameplate_power() -> None:
    power = build(instance="node-1x-a100").instance_power()
    assert power.value == 550
    assert power.status == "estimated"


def test_no_instance_leaves_the_power_open() -> None:
    assert build().instance_power().status == "TODO"


def test_an_unknown_instance_names_itself() -> None:
    result = build(instance="not-an-instance").instance_power()
    assert "not-an-instance" in str(result.notes)


def test_the_context_serialises_only_prose() -> None:
    mapping = build(country="FR", provider="aws", instance="node-1x-a100").to_mapping()
    assert set(mapping) == {"provider", "country", "country_provenance", "instance_type"}
    assert all(isinstance(value, str) for value in mapping.values())


def test_the_country_name_is_available_for_a_report() -> None:
    assert build(country="JP").country_name() == "Japan"
    assert build().country_name() is None


def test_an_overlay_row_wins(overlay: Path) -> None:
    import yaml

    (overlay / "grid.yaml").write_text(
        yaml.safe_dump(
            {
                "countries": [
                    {
                        "key": "FR",
                        "name": "France",
                        "carbon_gco2e_per_kwh": 1,
                        "price_usd_per_kwh": 0.01,
                        "source_url": "https://example.invalid",
                        "retrieved_date": "2026-09-12",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    context = DeploymentContext.build(country="FR", overlay=overlay, allow_timezone_inference=False)
    assert context.grid_intensity().value == 1
