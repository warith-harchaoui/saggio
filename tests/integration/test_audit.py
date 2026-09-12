"""The whole job: repository in, honest cost model out."""

from __future__ import annotations

from pathlib import Path

import pytest

from running_code_cost_helper.auditor import AuditOptions, audit, audit_github
from running_code_cost_helper.model import validate


def static_options(**kwargs) -> AuditOptions:
    kwargs.setdefault("run", False)
    kwargs.setdefault("use_llm", False)
    return AuditOptions(**kwargs)


# --- Reading only ------------------------------------------------------------


def test_an_audit_produces_a_model_that_passes_its_own_rules(
    training_repository: Path,
) -> None:
    result = audit(training_repository, options=static_options(country="FR"))
    assert result.report.ok, result.report.to_text()


def test_without_running_anything_the_runtime_stays_open(training_repository: Path) -> None:
    # Nothing about reading a repository tells you how long it runs, and a made-up
    # runtime would propagate into every other number in the model.
    result = audit(training_repository, options=static_options(country="FR"))
    assert result.model.get("scenarios[0].runtime")["status"] == "TODO"
    assert result.model.get("scenarios[0].costs.energy")["value"] is None


def test_the_unit_of_work_is_proposed_as_a_placeholder_not_an_estimate(
    training_repository: Path,
) -> None:
    # A guess at what somebody meant to measure is a structural stand-in. Calling
    # it an estimate would claim it was derived from something.
    result = audit(training_repository, options=static_options())
    assert result.model.get("unit_of_work")["status"] == "placeholder"


def test_a_repository_whose_shape_is_unreadable_asks_for_the_unit(tmp_path: Path) -> None:
    (tmp_path / "notes.txt").write_text("nothing to see", encoding="utf-8")
    result = audit(tmp_path, options=static_options())
    assert result.model.get("unit_of_work")["status"] == "TODO"


def test_an_unresolved_country_is_said_out_loud(tmp_path: Path) -> None:
    (tmp_path / "app.py").write_text("pass", encoding="utf-8")
    result = audit(tmp_path, options=static_options(country=None))
    if result.model.get("deployment.country") is None:
        assert any("country" in note.lower() for note in result.notes)


def test_a_stated_country_fills_in_the_grid_and_the_tariff(training_repository: Path) -> None:
    result = audit(training_repository, options=static_options(country="FR"))
    assert result.model.get("assumptions.grid_carbon_intensity")["value"] == 56
    assert result.model.get("assumptions.electricity_price")["currency"] == "USD"


def test_a_detected_service_is_recorded_with_its_evidence_and_no_price(
    training_repository: Path,
) -> None:
    # An API price copied today is wrong by next quarter, so the audit says where
    # the current one lives and leaves the figure open.
    result = audit(training_repository, options=static_options())
    services = result.model.data["external_services"]
    assert services[0]["key"] == "openai"
    assert "openai" in services[0]["evidence"]
    assert services[0]["price_per_unit"]["status"] == "TODO"


def test_water_stays_open_when_the_provider_publishes_no_figure(
    training_repository: Path,
) -> None:
    result = audit(training_repository, options=static_options(country="FR", provider="on-prem"))
    assert result.model.get("scenarios[0].costs.water")["status"] == "TODO"


def test_a_provider_that_publishes_one_can_still_need_the_energy(
    training_repository: Path,
) -> None:
    result = audit(training_repository, options=static_options(country="FR", provider="gcp"))
    assert result.model.get("assumptions.water_usage_effectiveness")["value"] == 0.99


def test_a_named_instance_supplies_the_power(training_repository: Path) -> None:
    result = audit(
        training_repository, options=static_options(country="FR", instance="node-1x-h100")
    )
    assert result.model.get("assumptions.power_draw")["value"] == 900


def test_every_cost_names_the_numbers_it_came_from(training_repository: Path) -> None:
    result = audit(training_repository, options=static_options(country="FR"))
    costs = result.model.get("scenarios[0].costs")
    for key in ("time", "energy", "money", "carbon", "water"):
        assert costs[key]["derived_from"], f"{key} names no inputs"


def test_a_work_size_disagreement_reaches_the_reader(tmp_path: Path) -> None:
    (tmp_path / "config.py").write_text("max_iters = 600000\n", encoding="utf-8")
    (tmp_path / "train.py").write_text("max_iters = 300\n", encoding="utf-8")
    result = audit(tmp_path, options=static_options())
    assert any("disagree" in note for note in result.notes)


# --- Projections -------------------------------------------------------------


def test_projecting_onto_another_machine_needs_a_machine_to_project_from(
    training_repository: Path,
) -> None:
    result = audit(
        training_repository, options=static_options(country="FR", target_accelerator="H100")
    )
    if result.model.get("deployment.gpu") is None:
        assert any("--source-accelerator" in note for note in result.notes)


def test_a_stated_source_machine_makes_the_projection_possible(
    training_repository: Path,
) -> None:
    # This is what makes the feature usable at all: a cost model is usually
    # written on a laptop, which has no datacenter accelerator to project from.
    result = audit(
        training_repository,
        options=static_options(
            country="FR", source_accelerator="RTX-4090", target_accelerator="H100"
        ),
    )
    projection = result.model.get("projections.on_other_hardware")
    assert projection is not None
    assert projection["source"] == "RTX-4090"


def test_a_precision_the_catalogue_cannot_speak_to_is_refused_out_loud(
    training_repository: Path,
) -> None:
    result = audit(
        training_repository,
        options=static_options(
            country="FR",
            source_accelerator="RTX-4090",
            target_accelerator="H100",
            precision="fp32",
        ),
    )
    projection = result.model.get("projections.on_other_hardware")
    assert projection is not None
    assert projection["runtime"]["refused"] is True


# --- Running -----------------------------------------------------------------


@pytest.mark.slow
def test_running_a_slice_replaces_the_guess_with_a_measurement(
    training_repository: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("running_code_cost_helper.auditor.require_consent", lambda: True)
    result = audit(
        training_repository,
        options=static_options(run=True, country="FR", timeout_seconds=120.0),
    )
    assert result.slice_result is not None
    assert result.model.get("scenarios[0].runtime")["status"] == "measured"
    assert result.model.get("scenarios[0].costs.energy")["value"] is not None
    assert validate(result.model).ok


@pytest.mark.slow
def test_a_measured_slice_projects_to_the_whole_run(
    training_repository: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("running_code_cost_helper.auditor.require_consent", lambda: True)
    result = audit(
        training_repository,
        options=static_options(run=True, country="FR", timeout_seconds=120.0),
    )
    whole = result.model.get("projections.whole_run")
    assert whole is not None
    assert whole["costs"]["energy"]["result"]["status"] == "estimated"


def test_declining_to_run_says_so_and_carries_on(
    training_repository: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("running_code_cost_helper.auditor.require_consent", lambda: False)
    result = audit(training_repository, options=static_options(run=True, country="FR"))
    assert result.slice_result is None
    assert any("declined" in note.lower() for note in result.notes)
    assert result.report.ok


def test_nothing_safe_to_run_is_reported(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / "library.py").write_text("VALUE = 1\n", encoding="utf-8")
    monkeypatch.setattr("running_code_cost_helper.auditor.require_consent", lambda: True)
    result = audit(tmp_path, options=static_options(run=True))
    assert result.slice_result is None
    assert any("nothing safe to run" in note.lower() for note in result.notes)


# --- Cloning -----------------------------------------------------------------


def test_cloning_something_that_is_not_a_repository_says_why() -> None:
    with pytest.raises(RuntimeError, match=r"clone|git"):
        audit_github("https://example.invalid/not-a-repository.git", options=static_options())
