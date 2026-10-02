"""The whole job: repository in, honest cost model out."""

from __future__ import annotations

from pathlib import Path

import pytest

from saggio.auditor import AuditOptions, audit, audit_git_url
from saggio.model import validate


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
    # Against the catalogue rather than against a number copied out of it. A
    # package built to refresh its own data cannot have tests that break every
    # time it does: restating 56 here made the refresh look like a regression.
    from saggio.catalog import Catalog

    expected = Catalog.bundled("grid").rows("countries")["FR"]["carbon_gco2e_per_kwh"]
    result = audit(training_repository, options=static_options(country="FR"))
    intensity = result.model.get("assumptions.grid_carbon_intensity")
    assert intensity["value"] == pytest.approx(float(expected))
    assert intensity["unit"] == "gCO2e/kWh"
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


def test_a_projection_onto_another_machine_carries_what_it_would_cost(
    training_repository: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # "How long would it take on an H100" is not the question anybody asked. The
    # projection has to reach money and carbon, or the feature stops one step
    # short of the thing the package exists to report.
    from saggio.model.quantity import Quantity

    monkeypatch.setattr(
        "saggio.auditor.build._runtime_assumption",
        lambda *a, **k: Quantity(value=3600.0, unit="s", status="measured"),
    )
    result = audit(
        training_repository,
        options=static_options(
            country="FR", source_accelerator="RTX-4090", target_accelerator="H100"
        ),
    )
    projection = result.model.get("projections.on_other_hardware")
    assert projection["runtime"]["refused"] is False if "refused" in projection["runtime"] else True
    costs = projection["costs"]
    assert {"time", "energy", "money", "carbon"} <= set(costs)
    assert costs["money"]["value"] > 0
    # A projected cost names the projected numbers it came from, never the local
    # ones, or the trail a reader follows arrives at the wrong machine.
    assert costs["energy"]["derived_from"][0].startswith("projections.on_other_hardware")
    assert validate(result.model).ok


def test_a_projection_onto_another_machine_says_what_it_held_constant(
    training_repository: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from saggio.model.quantity import Quantity

    monkeypatch.setattr(
        "saggio.auditor.build._runtime_assumption",
        lambda *a, **k: Quantity(value=3600.0, unit="s", status="measured"),
    )
    result = audit(
        training_repository,
        options=static_options(
            country="FR", source_accelerator="RTX-4090", target_accelerator="H100"
        ),
    )
    held = result.model.get("projections.on_other_hardware")["held_constant"]
    assert "tariff" in held and "carbon" in held


def test_a_projection_onto_another_machine_brackets_the_speed_up(
    training_repository: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # An H100 has six times the arithmetic of a 4090 and three times the
    # bandwidth. Reporting the six alone would halve the bill on paper.
    from saggio.model.quantity import Quantity

    monkeypatch.setattr(
        "saggio.auditor.build._runtime_assumption",
        lambda *a, **k: Quantity(value=3600.0, unit="s", status="measured"),
    )
    result = audit(
        training_repository,
        options=static_options(
            country="FR", source_accelerator="RTX-4090", target_accelerator="H100"
        ),
    )
    bounds = result.model.get("projections.on_other_hardware")["runtime"]["bounds"]
    assert bounds["fastest"]["value"] < bounds["slowest"]["value"]


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
    monkeypatch.setattr("saggio.auditor.measuring.require_consent", lambda: True)
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
    monkeypatch.setattr("saggio.auditor.measuring.require_consent", lambda: True)
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
    monkeypatch.setattr("saggio.auditor.measuring.require_consent", lambda: False)
    result = audit(training_repository, options=static_options(run=True, country="FR"))
    assert result.slice_result is None
    assert any("declined" in note.lower() for note in result.notes)
    assert result.report.ok


def test_nothing_safe_to_run_is_reported(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / "library.py").write_text("VALUE = 1\n", encoding="utf-8")
    monkeypatch.setattr("saggio.auditor.measuring.require_consent", lambda: True)
    result = audit(tmp_path, options=static_options(run=True))
    assert result.slice_result is None
    assert any("nothing safe to run" in note.lower() for note in result.notes)


# --- Cloning -----------------------------------------------------------------


def test_cloning_something_that_is_not_a_repository_says_why() -> None:
    with pytest.raises(RuntimeError, match=r"clone|git"):
        audit_git_url("https://example.invalid/not-a-repository.git", options=static_options())


# --- Measuring how the work grows --------------------------------------------


def _synthetic_series(exponent: float, sizes=(25.0, 100.0, 400.0)):
    """Rungs with times that follow a known power law exactly.

    The arithmetic of the fit is checked against synthetic observations in
    `tests/unit/test_scaling.py`. What these tests check is the wiring: that an
    exponent measured by the series reaches the model, the projection, and the
    validator. Real timings would make the same assertions flaky for reasons
    that have nothing to do with the code under test — a shared runner, a cache
    warming, thirty milliseconds of interpreter start-up on the smallest rung.
    """
    from saggio.analyze.power import PowerReading
    from saggio.analyze.run import SliceResult

    return tuple(
        (
            size,
            SliceResult(
                command=("python", "train.py", "--max_iters", str(int(size))),
                exit_code=0,
                wall_seconds=1e-4 * size**exponent,
                power=PowerReading(None, None, "n/a"),
                fraction_completed=size / 400000.0,
            ),
        )
        for size in sizes
    )


def test_a_scaling_series_puts_a_measured_exponent_in_the_model(
    training_repository: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("saggio.auditor.measuring.require_consent", lambda: True)
    monkeypatch.setattr(
        "saggio.auditor.measuring.run_scaling_series", lambda *a, **k: _synthetic_series(2.0)
    )
    result = audit(
        training_repository, options=static_options(run=True, country="FR", scaling_steps=3)
    )

    scaling = result.model.get("measurement.scaling")
    assert scaling is not None
    assert scaling["exponent"]["value"] == pytest.approx(2.0)
    assert scaling["exponent"]["status"] == "measured"
    assert len(scaling["observations"]) == 3
    assert validate(result.model).ok, validate(result.model).to_text()


def test_the_exponent_changes_the_whole_run_projection_it_feeds(
    training_repository: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("saggio.auditor.measuring.require_consent", lambda: True)
    monkeypatch.setattr(
        "saggio.auditor.measuring.run_scaling_series", lambda *a, **k: _synthetic_series(2.0)
    )
    result = audit(
        training_repository, options=static_options(run=True, country="FR", scaling_steps=3)
    )

    whole = result.model.get("projections.whole_run")
    assert whole is not None
    assert "^2.000" in whole["costs"]["energy"]["method"]
    assert "measured to" in whole["description"]


def test_a_linear_series_leaves_the_projection_where_it_was(
    training_repository: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The generalisation has to reduce to the special case end to end, not just
    # in the arithmetic.
    monkeypatch.setattr("saggio.auditor.measuring.require_consent", lambda: True)
    monkeypatch.setattr(
        "saggio.auditor.measuring.run_scaling_series", lambda *a, **k: _synthetic_series(1.0)
    )
    result = audit(
        training_repository, options=static_options(run=True, country="FR", scaling_steps=3)
    )
    assert "^1.000" in result.model.get("projections.whole_run")["costs"]["energy"]["method"]
    assert any("proportion" in note for note in result.notes)


def test_a_series_that_cannot_be_fitted_refuses_to_project_and_says_why(
    training_repository: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from saggio.analyze.power import PowerReading
    from saggio.analyze.run import SliceResult

    scattered = tuple(
        (
            size,
            SliceResult(
                command=("python", "train.py"),
                exit_code=0,
                wall_seconds=seconds,
                power=PowerReading(None, None, "n/a"),
                fraction_completed=size / 400000.0,
            ),
        )
        for size, seconds in ((25.0, 5.0), (100.0, 0.5), (400.0, 40.0))
    )
    monkeypatch.setattr("saggio.auditor.measuring.require_consent", lambda: True)
    monkeypatch.setattr("saggio.auditor.measuring.run_scaling_series", lambda *a, **k: scattered)
    result = audit(
        training_repository, options=static_options(run=True, country="FR", scaling_steps=3)
    )

    assert result.model.get("projections.whole_run") is None
    assert any("not measuring one consistent behaviour" in note for note in result.notes)
    assert result.model.get("measurement.scaling")["refused"] is True
    assert validate(result.model).ok


def test_too_few_rungs_completing_keeps_the_linear_assumption(
    training_repository: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("saggio.auditor.measuring.require_consent", lambda: True)
    monkeypatch.setattr(
        "saggio.auditor.measuring.run_scaling_series",
        lambda *a, **k: _synthetic_series(2.0, sizes=(400.0,)),
    )
    result = audit(
        training_repository, options=static_options(run=True, country="FR", scaling_steps=3)
    )
    assert result.model.get("measurement.scaling") is None
    assert result.model.get("projections.whole_run") is not None
    assert any("rungs completed" in note for note in result.notes)


def test_every_rung_failing_leaves_no_measurement_at_all(
    training_repository: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("saggio.auditor.measuring.require_consent", lambda: True)
    monkeypatch.setattr("saggio.auditor.measuring.run_scaling_series", lambda *a, **k: ())
    result = audit(
        training_repository, options=static_options(run=True, country="FR", scaling_steps=3)
    )
    assert result.slice_result is None
    assert any("ran out of time" in note for note in result.notes)
    assert result.report.ok


def test_a_stated_size_too_small_to_cut_falls_back_to_one_slice(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "tiny"
    root.mkdir()
    (root / "config.py").write_text("epochs = 2\n", encoding="utf-8")
    (root / "train.py").write_text(
        "import argparse\n"
        "parser = argparse.ArgumentParser()\n"
        'parser.add_argument("--epochs", type=int, default=2)\n'
        "parser.parse_args()\n",
        encoding="utf-8",
    )
    monkeypatch.setattr("saggio.auditor.measuring.require_consent", lambda: True)
    result = audit(root, options=static_options(run=True, country="FR", scaling_steps=3))
    assert any("distinct size" in note for note in result.notes)


@pytest.mark.slow
def test_a_real_repository_really_runs_the_whole_ladder(
    training_repository: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # No assertion on the exponent: over a range this short, interpreter start-up
    # is a real part of every rung and the fit says so. What is asserted is that
    # three rungs ran, that whatever came out is honest about itself, and that
    # the model still passes its own rules either way.
    monkeypatch.setattr("saggio.auditor.measuring.require_consent", lambda: True)
    result = audit(
        training_repository,
        options=static_options(run=True, country="FR", timeout_seconds=120.0, scaling_steps=3),
    )
    scaling = result.model.get("measurement.scaling")
    assert scaling is not None
    assert len(scaling["observations"]) == 3
    assert scaling["exponent"]["status"] in {"measured", "TODO"}
    assert validate(result.model).ok, validate(result.model).to_text()
    assert any("without the profiler" in note for note in result.notes)


def test_an_audit_can_be_told_to_skip_the_baseline(
    training_repository: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # `saggio measure` has had this knob since the baseline existed; an audit
    # could not be told to skip a second it does not need, and a scaling series
    # could not be told either.
    seen: list[float] = []

    def remember(*args, **kwargs):
        seen.append(kwargs["baseline_seconds"])
        from saggio.analyze.power import PowerReading
        from saggio.analyze.run import SliceResult

        return SliceResult(
            command=("true",),
            exit_code=0,
            wall_seconds=1.0,
            power=PowerReading(None, None, "n/a"),
            fraction_completed=0.001,
        )

    monkeypatch.setattr("saggio.auditor.measuring.require_consent", lambda: True)
    monkeypatch.setattr("saggio.auditor.measuring.run_slice", remember)
    audit(training_repository, options=static_options(run=True, country="FR", baseline_seconds=0.0))

    assert seen == [0.0]


def test_a_scaling_series_is_given_the_audit_baseline(
    training_repository: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen: list[float] = []

    def remember(ladder, **kwargs):
        seen.append(kwargs["baseline_seconds"])
        return _synthetic_series(1.0)

    monkeypatch.setattr("saggio.auditor.measuring.require_consent", lambda: True)
    monkeypatch.setattr("saggio.auditor.measuring.run_scaling_series", remember)
    audit(
        training_repository,
        options=static_options(run=True, country="FR", scaling_steps=3, baseline_seconds=0.0),
    )

    assert seen == [0.0]
