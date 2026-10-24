"""Placing a cost in a greenhouse-gas inventory, and refusing to when nothing settles it.

The rule under test is one sentence of the GHG Protocol: the scope turns on who
buys the electricity and owns the machine. Everything here is that sentence,
applied to facts the model already states, plus the places this package has to
say "no" — a provider nobody classified, and a market-based figure nobody
stated, which is never derived from a grid average and never guessed at zero.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import pytest
import yaml

from saggio.cli.commands import scopes
from saggio.estimate.ghg import (
    GHG_PROTOCOL_SCOPE2,
    GHG_PROTOCOL_SCOPE3,
    OPERATED_BY_SELF,
    OPERATED_BY_VENDOR,
    market_based_figure_exists,
    placed_model,
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


# --- The other half of scope 2 ------------------------------------------------


def test_a_market_based_figure_on_your_own_machine_is_the_other_half_of_scope_2() -> None:
    """Same scope, different method, and the label says which.

    A scope 2 line that does not name its method is the failure the dual
    reporting requirement exists to prevent: two numbers that differ by a factor
    of ten, both correct, and nothing on the page to say why.
    """
    where = placement("carbon_market_based", "on-prem")
    assert (where.scope, where.category) == ("2", None)
    assert where.label == "Scope 2 (market-based)"
    assert placement("carbon", "on-prem").label == "Scope 2 (location-based)"
    assert where.source_url == GHG_PROTOCOL_SCOPE2


def test_a_market_based_figure_on_rented_hardware_answers_the_vendor_s_question() -> None:
    """The mirror of filing cloud electricity as your scope 2.

    The pair lives inside scope 2 and nowhere else. On a vendor's machine there
    is no scope 2 of yours to split in two, so a market-based number there is
    not a more precise answer — it is an answer about the vendor's electricity,
    and the standard draws no such pair in category 1.
    """
    where = placement("carbon_market_based", "gcp")
    assert where.is_open
    assert "no scope 2 of yours" in where.why
    assert "category 1" in where.why


def test_the_half_pair_sentence_becomes_a_whole_pair_sentence_only_on_a_real_figure() -> None:
    """A declared row is not a disclosure; a number is.

    Reading the key alone would tell a sustainability team the pair was complete
    while the second figure was still a ``TODO``, which is the precise failure
    this package exists to prevent.
    """
    half = placement("carbon", "on-prem")
    whole = placement("carbon", "on-prem", market_based_reported=True)
    assert "is not here" in half.dual_reporting
    assert "`carbon_market_based`" in whole.dual_reporting
    assert "does not replace this one" in whole.dual_reporting

    assert market_based_figure_exists({"carbon_market_based": {"value": 0.0}})
    assert not market_based_figure_exists({"carbon_market_based": {"status": "TODO"}})
    assert not market_based_figure_exists({"carbon": {"value": 1.0}})
    assert not market_based_figure_exists(None)


def test_a_model_that_only_declared_the_row_still_gets_the_shopping_list() -> None:
    # The whole point of the default: a caller that does not say, does not claim.
    placed = placements(["carbon", "carbon_market_based"], "on-prem")
    assert "is not here" in placed["carbon"].dual_reporting
    assert "assumptions.market_carbon_intensity" in placed["carbon"].dual_reporting


def test_the_market_based_half_names_the_location_based_one_as_its_companion() -> None:
    where = placement("carbon_market_based", "on-prem")
    assert "`carbon`" in where.dual_reporting
    assert "not what the grid emitted" in where.dual_reporting


def test_the_command_places_both_halves_and_says_the_pair_is_whole(tmp_path: Path, capsys) -> None:
    """End to end, on a model that states a factor: two scope 2 lines, labelled.

    Built from the walkthrough model rather than from a fixture, so the
    arithmetic under the second figure is the same arithmetic the validator
    reconciles for the first.
    """
    import yaml

    from saggio.estimate.energy import market_carbon_from_energy
    from saggio.model.quantity import Quantity
    from saggio.model.validate import validate

    model = yaml.safe_load(Path("examples/walkthrough/5-run.yaml").read_text(encoding="utf-8"))
    model["assumptions"]["market_carbon_intensity"] = {
        "value": 18.0,
        "status": "estimated",
        "unit": "gCO2e/kWh",
        "source_url": "https://www.aib-net.org/facts/european-residual-mix",
        "retrieved_date": "2026-10-15",
    }
    costs = model["scenarios"][0]["costs"]
    figure = market_carbon_from_energy(
        Quantity.from_mapping(costs["energy"]),
        Quantity.from_mapping(model["assumptions"]["market_carbon_intensity"]),
    ).with_derivation("scenarios[0].costs.energy", "assumptions.market_carbon_intensity")
    costs["carbon_market_based"] = figure.to_mapping()

    written = tmp_path / "pair.yaml"
    written.write_text(yaml.safe_dump(model, sort_keys=False, allow_unicode=True), encoding="utf-8")
    assert validate(model).ok, validate(model).to_text()

    assert scopes(_args(model=str(written), json=True)) == 0
    payload = json.loads(capsys.readouterr().out)
    placed = {row["dimension"]: row for row in payload["placements"]}
    assert placed["carbon"]["scope"] == placed["carbon_market_based"]["scope"] == "2"
    assert placed["carbon"]["label"] != placed["carbon_market_based"]["label"]
    assert "`carbon_market_based`" in placed["carbon"]["dual_reporting"]


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


def test_the_command_prints_why_an_emission_got_no_scope(tmp_path: Path, capsys) -> None:
    """The sentence a reader came for when a line says "No scope".

    A model built on-prem and later pointed at a vendor keeps its market-based
    row, and that row is where the placement's most specific refusal lives: the
    pair exists inside scope 2 and nowhere else. The command used to decide
    which refusals to print from its own two-item copy of the emissions list, so
    that explanation printed nowhere and the reader was left with "No scope" and
    no reason — on the one row where the reason is the whole point.
    """
    import yaml

    model = yaml.safe_load(Path("examples/walkthrough/5-run.yaml").read_text(encoding="utf-8"))
    model["deployment"]["provider"] = "aws"
    model["scenarios"][0]["costs"]["carbon_market_based"] = {
        "value": None,
        "status": "TODO",
        "unit": "gCO2e",
    }
    moved = tmp_path / "moved-to-aws.yaml"
    moved.write_text(yaml.safe_dump(model, sort_keys=False, allow_unicode=True), encoding="utf-8")

    assert scopes(_args(model=str(moved))) == 0
    # Flattened: the command wraps its prose to a terminal, so a phrase landing
    # across a line break is the paragraph being set rather than the sentence
    # changing. What is asserted is what the command says.
    out = " ".join(capsys.readouterr().out.split())
    assert "carbon_market_based: The machine is operated by a vendor" in out
    assert "somebody else's question" in out


def test_the_scope_table_stays_aligned_whatever_is_in_it(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Columns sized from the rows, not from two numbers typed once.

    They were 19 and 18, which fitted the English labels exactly and put every
    French table two characters past an eighty-column terminal. Worse, a
    dimension longer than nineteen characters -- which this package invites a
    team to register -- pushed the value column right and misaligned the rows
    below it.
    """
    model = yaml.safe_load(Path("examples/render.yaml").read_text(encoding="utf-8"))
    long_name = "embodied_carbon_of_the_network_fabric"
    model["scenarios"][0]["costs"][long_name] = {
        "value": 1.5e-07,
        "unit": "gCO2e",
        "status": "estimated",
        "derived_from": ["scenarios[0].costs.energy"],
        "notes": "A registered dimension whose name is longer than the old column.",
    }
    wide = tmp_path / "wide.yaml"
    wide.write_text(yaml.safe_dump(model, sort_keys=False, allow_unicode=True), encoding="utf-8")

    assert scopes(_args(model=str(wide))) == 0
    rows = [
        line
        for line in capsys.readouterr().out.split("\n")
        if line.startswith("  ") and ("Scope" in line or "No scope" in line)
    ]
    assert any(long_name in row for row in rows), "the long dimension is not in the table"

    # Where the second column starts, per row. Aligned means every row agrees.
    # The first version of this check compared the *first* column's offset,
    # which is two spaces on every row however broken the rest is, so it
    # passed against the hard-coded widths it was written to catch.
    def value_starts_at(row: str) -> int:
        rest = row[2:]
        name = rest[: len(rest) - len(rest.lstrip())] + rest.split(" ", 1)[0]
        after = rest[len(name) :]
        return 2 + len(name) + (len(after) - len(after.lstrip()))

    offsets = {value_starts_at(row) for row in rows}
    assert len(offsets) == 1, (
        f"the value column starts at different places on different rows: "
        f"{sorted(offsets)}. A width typed once cannot hold a name longer "
        f"than itself, and {long_name!r} is longer than the one that was there."
    )


# --- The whole-model answer, which three surfaces share ------------------------


def _one_model() -> dict:
    return {
        "unit_of_work": {"name": "one request"},
        "deployment": {"provider": "on-prem"},
        "scenarios": [
            {
                "name": "cold",
                "costs": {
                    "carbon": {"value": 1.4, "unit": "gCO2e", "status": "estimated"},
                    "energy": {"value": 0.03, "unit": "Wh", "status": "measured"},
                    "water": {"value": None, "unit": "L", "status": "TODO"},
                },
            },
            {"name": "warm", "costs": {"carbon": {"value": 0.2, "status": "estimated"}}},
        ],
    }


def test_a_placed_model_keeps_the_dimension_order_the_model_wrote() -> None:
    # A reader compares the placement to their own file. Re-ordering the rows
    # alphabetically would make them hunt for the line they came to check.
    placed = placed_model(_one_model())
    assert [row["dimension"] for row in placed["placements"]] == ["carbon", "energy", "water"]


def test_a_placed_model_counts_only_what_it_actually_placed() -> None:
    # The count is the estimation disclosure a filer owes. Energy and water have
    # no scope, so counting their statuses would overstate how much of an
    # inventory this model answers for.
    assert placed_model(_one_model())["by_status"] == {"estimated": 1}


def test_a_named_scenario_is_the_one_placed() -> None:
    placed = placed_model(_one_model(), scenario="warm")
    assert placed["scenario"] == "warm"
    assert [row["value"] for row in placed["placements"]] == [0.2]


def test_the_first_scenario_is_placed_when_none_is_named() -> None:
    assert placed_model(_one_model())["scenario"] == "cold"


def test_a_scenario_nobody_has_is_refused_and_the_message_names_the_ones_there() -> None:
    # Placing the wrong scenario under the name the caller asked for would be
    # undetectable downstream, so this raises rather than falling back.
    with pytest.raises(
        ValueError, match=re.escape("No scenario named 'hot'. The model has: cold, warm")
    ):
        placed_model(_one_model(), scenario="hot")


def test_a_model_object_and_its_mapping_are_placed_identically() -> None:
    # The surfaces hand this function whatever they hold: the command line a
    # loaded CostModel, the HTTP API a parsed document. A difference between the
    # two would be the package disagreeing with itself about an inventory line.
    from saggio.model import CostModel

    data = _one_model()
    assert placed_model(CostModel.from_mapping(data)) == placed_model(data)


def test_the_standards_cited_are_the_ones_that_settle_the_placements() -> None:
    standards = placed_model(_one_model())["standards"]
    assert standards["scope_2_guidance"] == GHG_PROTOCOL_SCOPE2
    assert standards["scope_3_standard"] == GHG_PROTOCOL_SCOPE3
