"""Placing a cost in a greenhouse-gas inventory, and refusing to when nothing settles it.

The rule under test is one sentence of the GHG Protocol: the scope turns on who
buys the electricity and owns the machine. Everything here is that sentence,
applied to facts the model already states, plus the two places this package has
to say "no" — a provider nobody classified, and a market-based figure that
cannot be derived from a grid average.
"""

from __future__ import annotations

import argparse
import json

import pytest

from saggio.cli.commands import scopes
from saggio.estimate.ghg import (
    GHG_PROTOCOL_SCOPE2,
    GHG_PROTOCOL_SCOPE3,
    OPERATED_BY_SELF,
    OPERATED_BY_VENDOR,
    placement,
    placements,
)

# --- The rule -----------------------------------------------------------------


def test_electricity_on_your_own_machine_is_scope_2() -> None:
    where = placement("carbon", "on-prem")
    assert where.scope == "2"
    assert where.category is None
    assert where.source_url == GHG_PROTOCOL_SCOPE2


def test_hardware_you_own_is_capital_goods_rather_than_purchased_goods() -> None:
    """Category 2, and the reason is the useful life rather than the kind of thing.

    The standard splits category 1 from category 2 on whether the asset lasts
    more than a year. A server does, which is also why this package amortises
    the footprint instead of charging it once — the same fact, twice over.
    """
    where = placement("embodied_carbon", "on-prem")
    assert (where.scope, where.category) == ("3", 2)
    assert "useful life" in where.why


def test_the_same_two_costs_on_a_vendor_s_machine_are_one_purchased_service() -> None:
    """The code did not change; the inventory line changed completely.

    On rented hardware the organisation bought neither the electricity nor the
    machine. Both emissions are the vendor's own scope 2 and 3.2, and reach the
    customer as a purchased service — one category, not two.
    """
    for dimension in ("carbon", "embodied_carbon"):
        where = placement(dimension, "gcp")
        assert (where.scope, where.category) == ("3", 1), dimension
        assert where.source_url == GHG_PROTOCOL_SCOPE3


def test_a_laptop_is_your_own_machine_and_a_gpu_cloud_is_not() -> None:
    # Both ends of the catalogue, because the rule is read from a row rather
    # than from whether a name sounds like a datacenter.
    assert placement("carbon", "laptop").scope == "2"
    assert placement("carbon", "lambda").category == 1


@pytest.mark.parametrize("key", ["on-prem", "laptop", "aws", "gcp", "azure", "oci"])
def test_every_bundled_provider_can_be_placed(key: str) -> None:
    # A provider shipped without `operated_by` would silently make every carbon
    # figure on it unplaceable, and the model would look complete while the
    # inventory line was missing.
    assert placement("carbon", key).scope is not None, key


def test_the_catalogue_only_says_self_or_vendor() -> None:
    import yaml

    from saggio.catalog.registry import Catalog

    rows = Catalog.bundled("providers").rows("providers")
    for key, row in rows.items():
        said = row.get("operated_by")
        assert said in (OPERATED_BY_SELF, OPERATED_BY_VENDOR), (
            f"{key} says operated_by={said!r}, which is neither of the two values the rule reads"
        )
    assert yaml  # the import exists to fail loudly if the catalogue stops parsing


# --- The refusals -------------------------------------------------------------


def test_a_provider_nobody_classified_gets_no_scope_rather_than_a_guess() -> None:
    """The two answers differ by which company reports the emission.

    Guessing from a name would be the worst kind of wrong here: it is not a
    number that would be slightly off, it is an emission filed against the wrong
    legal entity, and it would look exactly as tidy as a right one.
    """
    where = placement("carbon", "some-provider-registered-this-morning")
    assert where.is_open
    assert "operated_by" in where.why


def test_a_model_with_no_provider_is_told_which_field_to_fill() -> None:
    where = placement("carbon", None)
    assert where.is_open
    assert "deployment.provider" in where.why


def test_energy_is_an_activity_datum_and_not_an_emission() -> None:
    # The commonest category error in this area: energy has no scope, it is what
    # a scope 2 figure is computed from. Saying "no scope" without the sentence
    # would read as an omission.
    where = placement("energy", "on-prem")
    assert where.is_open
    assert "activity datum" in where.why


def test_water_is_not_a_greenhouse_gas() -> None:
    where = placement("water", "on-prem")
    assert where.is_open
    assert "not a greenhouse gas" in where.why


def test_a_dimension_this_project_invented_is_not_filed_as_carbon() -> None:
    # A registered dimension in grams of something is not carbon because its unit
    # looks like carbon's. The question is handed back rather than answered.
    where = placement("egress", "on-prem")
    assert where.is_open
    assert "egress" in where.why


def test_no_market_based_figure_is_produced_and_the_shopping_list_is() -> None:
    """The number a reviewer most wants invented, and the one that cannot be.

    A grid average *is* the location-based method. The market-based figure comes
    from a supplier factor, a contractual instrument, or a residual mix, and
    none of those is in this package. What it would take is printed instead of a
    plausible number, which is the difference between a refusal and a dead end.
    """
    where = placement("carbon", "on-prem")
    assert "location-based" in where.why
    for needed in ("supplier", "residual mix", "guarantees of origin"):
        assert needed in where.dual_reporting, needed
    assert "0" not in where.dual_reporting.replace("CO2", ""), "no figure is offered"


def test_only_a_scope_2_placement_carries_the_dual_reporting_note() -> None:
    assert placement("carbon", "gcp").dual_reporting == ""
    assert placement("embodied_carbon", "on-prem").dual_reporting == ""
    assert placement("carbon", "on-prem").dual_reporting != ""


def test_placing_many_keeps_the_order_it_was_given() -> None:
    found = placements(["water", "carbon", "money"], "on-prem")
    assert list(found) == ["water", "carbon", "money"]


# --- The command --------------------------------------------------------------


def _args(**over: object) -> argparse.Namespace:
    base = {"model": "examples/walkthrough/5-run.yaml", "scenario": None, "json": False}
    return argparse.Namespace(**(base | over))


def test_the_command_places_a_real_model(capsys) -> None:
    assert scopes(_args()) == 0
    out = capsys.readouterr().out
    assert "Scope 2" in out
    assert "capital goods" in out


def test_the_command_reports_how_well_founded_the_inventory_is(capsys) -> None:
    """The disclosure a filer is asked for, which this model can already answer.

    A sustainability report has to say how much of an inventory rests on
    estimates rather than readings. Every number here already carries that word;
    the command only has to count them.
    """
    scopes(_args(json=True))
    payload = json.loads(capsys.readouterr().out)
    assert payload["by_status"], "no status counted at all"
    assert set(payload["by_status"]) <= {"measured", "estimated", "placeholder", "TODO"}


def test_the_json_carries_the_standards_it_rests_on(capsys) -> None:
    scopes(_args(json=True))
    payload = json.loads(capsys.readouterr().out)
    assert payload["standards"]["scope_2_guidance"] == GHG_PROTOCOL_SCOPE2
    placed = {row["dimension"]: row for row in payload["placements"]}
    assert placed["carbon"]["scope"] == "2"
    assert placed["embodied_carbon"]["category"] == 2


def test_a_scenario_that_is_not_there_is_a_usage_error_not_the_wrong_scenario(capsys) -> None:
    # Reporting the first scenario when asked for a named one would place the
    # wrong costs under the right heading, silently.
    assert scopes(_args(scenario="no-such-scenario")) == 2


def test_a_model_that_is_not_there_is_a_usage_error() -> None:
    assert scopes(_args(model="/nonexistent.yaml")) == 2
