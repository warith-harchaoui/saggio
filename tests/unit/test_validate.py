"""Validation: the three rules that make the taxonomy enforceable."""

from __future__ import annotations

from typing import Any

import pytest

from saggio.model import CostModel, overall_status, validate


def messages(model: Any) -> str:
    return validate(model).to_text()


def test_a_sound_model_passes_with_nothing_to_say(sound_model: dict[str, Any]) -> None:
    report = validate(sound_model)
    assert report.ok
    assert not report.warnings


# --- Every number lives in a quantity ---------------------------------------


def test_a_bare_number_anywhere_is_an_error(sound_model: dict[str, Any]) -> None:
    sound_model["scenarios"][0]["runtime_seconds"] = 3600.0
    report = validate(sound_model)
    assert not report.ok
    assert "bare number" in report.to_text()


def test_a_bare_number_in_an_unknown_block_is_still_caught(sound_model: dict[str, Any]) -> None:
    # This is the loophole the redesign closed: a block the tool has never heard
    # of used to carry numbers straight past every honesty rule.
    sound_model["our_own_extra_block"] = {"cost_per_month": 4200}
    assert "bare number" in messages(sound_model)


def test_structural_counts_are_exempt(sound_model: dict[str, Any]) -> None:
    sound_model["deployment"]["physical_cores"] = 64
    sound_model["analysis"] = {"language_file_counts": {"Python": 12}}
    assert validate(sound_model).ok


def test_a_boolean_is_not_a_bare_number(sound_model: dict[str, Any]) -> None:
    sound_model["deployment"]["dedicated"] = True
    assert validate(sound_model).ok


# --- A derived value names its inputs ---------------------------------------


def test_overclaiming_its_inputs_is_an_error(sound_model: dict[str, Any]) -> None:
    sound_model["scenarios"][0]["costs"]["energy"]["status"] = "measured"
    report = validate(sound_model)
    assert not report.ok
    assert "cannot outrank" in report.to_text()


def test_matching_its_inputs_is_fine(sound_model: dict[str, Any]) -> None:
    sound_model["assumptions"]["power_draw"]["status"] = "measured"
    sound_model["assumptions"]["power_draw"]["notes"] = "read from a wattmeter"
    sound_model["scenarios"][0]["costs"]["energy"]["status"] = "measured"
    # money still derives from an estimated price, so it stays estimated.
    assert validate(sound_model).ok


def test_a_derivation_pointing_nowhere_is_an_error(sound_model: dict[str, Any]) -> None:
    sound_model["scenarios"][0]["costs"]["energy"]["derived_from"] = ["assumptions.typo"]
    assert "names nothing" in messages(sound_model)


def test_a_derivation_pointing_at_something_that_is_not_a_quantity_is_an_error(
    sound_model: dict[str, Any],
) -> None:
    sound_model["scenarios"][0]["costs"]["energy"]["derived_from"] = ["deployment"]
    assert "not a quantity" in messages(sound_model)


def test_a_quantity_cannot_derive_from_itself(sound_model: dict[str, Any]) -> None:
    sound_model["scenarios"][0]["costs"]["energy"]["derived_from"] = ["scenarios[0].costs.energy"]
    assert "itself" in messages(sound_model)


def test_the_rule_covers_a_dimension_the_package_has_never_heard_of(
    sound_model: dict[str, Any],
) -> None:
    sound_model["dimensions"] = [
        {"key": "egress", "label": "Egress", "unit": "GB", "description": "Bytes out."}
    ]
    sound_model["scenarios"][0]["costs"]["egress"] = {
        "value": 1.0,
        "unit": "GB",
        "status": "measured",
        "derived_from": ["assumptions.power_draw"],
    }
    assert "cannot outrank" in messages(sound_model)


# --- Money says which money --------------------------------------------------


def test_money_without_a_currency_is_an_error(sound_model: dict[str, Any]) -> None:
    del sound_model["scenarios"][0]["costs"]["money"]["currency"]
    assert "currency" in messages(sound_model)


def test_a_currency_that_is_not_iso_4217_is_an_error(sound_model: dict[str, Any]) -> None:
    sound_model["scenarios"][0]["costs"]["money"]["currency"] = "dollars"
    assert "ISO 4217" in messages(sound_model)


def test_a_currency_on_a_non_money_dimension_is_a_warning(sound_model: dict[str, Any]) -> None:
    sound_model["scenarios"][0]["costs"]["energy"]["currency"] = "USD"
    report = validate(sound_model)
    assert report.ok
    assert "not a money dimension" in report.to_text()


# --- The rest of the hygiene -------------------------------------------------


def test_a_negative_cost_is_an_error(sound_model: dict[str, Any]) -> None:
    sound_model["scenarios"][0]["costs"]["energy"]["value"] = -0.1
    assert "cannot be negative" in messages(sound_model)


def test_claiming_a_status_without_a_number_is_an_error(sound_model: dict[str, Any]) -> None:
    sound_model["scenarios"][0]["costs"]["energy"]["value"] = None
    assert "no number" in messages(sound_model)


def test_a_todo_carrying_a_number_is_a_warning(sound_model: dict[str, Any]) -> None:
    sound_model["scenarios"][0]["costs"]["energy"]["status"] = "TODO"
    report = validate(sound_model)
    assert "should have no value" in report.to_text()


def test_an_invalid_status_is_an_error(sound_model: dict[str, Any]) -> None:
    sound_model["scenarios"][0]["costs"]["energy"]["status"] = "probably"
    assert "must be one of" in messages(sound_model)


def test_an_unregistered_dimension_key_is_an_error(sound_model: dict[str, Any]) -> None:
    sound_model["scenarios"][0]["costs"]["vibes"] = {"value": 1, "status": "TODO"}
    assert "not a registered dimension" in messages(sound_model)


def test_a_scenario_needs_a_name_and_costs(sound_model: dict[str, Any]) -> None:
    sound_model["scenarios"][0]["name"] = ""
    del sound_model["scenarios"][0]["costs"]
    report = validate(sound_model)
    assert "name" in report.to_text()
    assert "costs" in report.to_text()


def test_a_newer_major_schema_is_refused() -> None:
    assert "newer than this build" in messages({"schema_version": "99.0"})


def test_a_malformed_schema_version_is_refused() -> None:
    assert "MAJOR.MINOR" in messages({"schema_version": "two point oh"})


def test_a_missing_schema_version_is_only_a_warning(sound_model: dict[str, Any]) -> None:
    del sound_model["schema_version"]
    report = validate(sound_model)
    assert report.ok
    assert "is missing" in report.to_text()


def test_an_unsourced_estimate_in_the_assumptions_is_a_warning(
    sound_model: dict[str, Any],
) -> None:
    del sound_model["assumptions"]["power_draw"]["source_url"]
    report = validate(sound_model)
    assert report.ok
    assert "no source_url" in report.to_text()


def test_a_derived_assumption_needs_no_source(sound_model: dict[str, Any]) -> None:
    # Its provenance is its derivation; asking for a URL as well would be asking
    # where a multiplication was published.
    sound_model["assumptions"]["machine_energy"] = {
        "value": 0.05,
        "unit": "kWh",
        "status": "estimated",
        "derived_from": ["scenarios[0].runtime", "assumptions.power_draw"],
    }
    assert "machine_energy" not in validate(sound_model).to_text()


def test_stale_provenance_is_a_warning(sound_model: dict[str, Any]) -> None:
    sound_model["assumptions"]["power_draw"]["retrieved_date"] = "2019-01-01"
    report = validate(sound_model)
    assert report.ok
    assert "re-read the source" in report.to_text().lower()


def test_an_unknown_top_level_block_is_a_warning_not_an_error(
    sound_model: dict[str, Any],
) -> None:
    sound_model["notes_for_the_team"] = ["remember the batching scenario"]
    report = validate(sound_model)
    assert report.ok
    assert "not a block this build knows" in report.to_text()


def test_a_model_with_no_scenario_is_invalid() -> None:
    assert "at least one scenario" in messages({"schema_version": "2.0"})


@pytest.mark.parametrize("spelling", ["scenario", "scenarios"])
def test_both_scenario_spellings_are_accepted(sound_model: dict[str, Any], spelling: str) -> None:
    scenario = sound_model.pop("scenarios")[0]
    if spelling == "scenario":
        scenario["costs"]["time"]["derived_from"] = ["scenario.runtime"]
        scenario["costs"]["energy"]["derived_from"] = [
            "scenario.runtime",
            "assumptions.power_draw",
        ]
        scenario["costs"]["money"]["derived_from"] = [
            "scenario.costs.energy",
            "assumptions.electricity_price",
        ]
        sound_model["scenario"] = scenario
    else:
        sound_model["scenarios"] = [scenario]
    assert validate(sound_model).ok


# --- The overall verdict -----------------------------------------------------


def test_the_overall_status_is_the_weakest_anywhere(sound_model: dict[str, Any]) -> None:
    assert overall_status(sound_model) == "estimated"
    sound_model["scenarios"][0]["costs"]["water"] = {"value": None, "status": "TODO"}
    assert overall_status(sound_model) == "TODO"


def test_a_model_with_no_quantities_has_no_overall_status() -> None:
    assert overall_status({}) is None


def test_validation_accepts_a_wrapped_model(sound_cost_model: CostModel) -> None:
    assert validate(sound_cost_model).ok


# --- Holes the first audit found, kept closed ----------------------------------


def _one_cost_model(quantity: dict) -> CostModel:
    from saggio.model.cost_model import CostModel

    return CostModel.from_mapping(
        {
            "schema_version": "2.1",
            "project": {"name": "x"},
            "unit_of_work": {"name": "one call", "status": "measured"},
            "scenarios": [{"name": "s", "costs": {"energy": quantity}}],
        }
    )


def test_a_number_hidden_inside_notes_is_an_error() -> None:
    report = validate(
        _one_cost_model({"value": 1, "status": "measured", "notes": {"hidden": 9999.0}})
    )
    assert any("should be text" in issue.message for issue in report.errors)


def test_a_number_hidden_under_an_unknown_key_is_an_error_not_a_warning() -> None:
    report = validate(
        _one_cost_model(
            {"value": 1, "status": "measured", "sub": {"value": 5, "status": "measured"}}
        )
    )
    assert any("hides numbers" in issue.message for issue in report.errors)


def test_an_unknown_key_without_numbers_stays_a_warning() -> None:
    report = validate(_one_cost_model({"value": 1, "status": "measured", "remark": "cheap"}))
    assert not any("remark" in issue.message for issue in report.errors)
    assert any("remark" in issue.message for issue in report.warnings)


def test_nan_is_not_a_measured_cost() -> None:
    report = validate(_one_cost_model({"value": float("nan"), "status": "measured"}))
    assert any("finite" in issue.message for issue in report.errors)


def test_a_string_typed_value_is_named_for_what_it_is() -> None:
    report = validate(_one_cost_model({"value": "3.14", "status": "TODO"}))
    assert any("not a number" in issue.message for issue in report.errors)


def test_the_template_retrieved_date_does_not_pass_silently() -> None:
    report = validate(
        _one_cost_model(
            {
                "value": 1,
                "status": "estimated",
                "source_url": "https://x.invalid",
                "retrieved_date": "YYYY-MM-DD",
            }
        )
    )
    assert any("template" in issue.message for issue in report.warnings)


def test_a_currency_with_a_trailing_newline_is_rejected() -> None:
    report = validate(_one_cost_model({"value": 1, "status": "measured", "currency": "USD\n"}))
    assert any("ISO 4217" in issue.message for issue in report.errors)


def test_scenario_errors_point_at_the_documents_own_index() -> None:
    from saggio.model.cost_model import CostModel

    model = CostModel.from_mapping(
        {
            "schema_version": "2.1",
            "project": {"name": "x"},
            "unit_of_work": {"name": "one call", "status": "measured"},
            "scenarios": ["stray-comment", {"name": "", "costs": {}}],
        }
    )
    report = validate(model)
    paths = [issue.path for issue in report.errors]
    assert "scenarios[0]" in paths  # the stray entry itself
    assert any(path.startswith("scenarios[1]") for path in paths)  # the real scenario's faults
    assert not any(path == "scenarios[0].name" for path in paths)


def test_an_invalid_source_kind_is_an_error() -> None:
    report = validate(_one_cost_model({"value": 1, "status": "measured", "source_kind": "hearsay"}))
    assert any("source_kind" in issue.message for issue in report.errors)
