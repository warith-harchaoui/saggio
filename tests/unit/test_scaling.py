"""Measuring how the work grows, and refusing to guess when it cannot be measured."""

from __future__ import annotations

import math

import pytest

from saggio.analyze.static import RepositoryReading, WorkSizeCandidate, scaling_ladder
from saggio.estimate.extrapolate import project_to_completion
from saggio.estimate.scaling import (
    DEFAULT_MINIMUM_R_SQUARED,
    MINIMUM_OBSERVATIONS,
    MINIMUM_SIZE_RATIO,
    Observation,
    ScalingFit,
    fit_power_law,
)
from saggio.model import Quantity
from saggio.model.schema import is_bare_number_exempt


def series(exponent: float, coefficient: float = 1e-3, sizes=(50, 200, 800)) -> list[Observation]:
    """A perfect power law, so a test can assert the exponent it put in."""
    return [Observation(size=float(n), seconds=coefficient * n**exponent) for n in sizes]


# --- The fit itself ----------------------------------------------------------


@pytest.mark.parametrize("exponent", [0.5, 1.0, 1.5, 2.0, 3.0])
def test_the_exponent_that_went_in_is_the_exponent_that_comes_out(exponent: float) -> None:
    fit = fit_power_law(series(exponent))
    assert fit.exponent.value == pytest.approx(exponent, abs=1e-9)
    assert fit.r_squared == pytest.approx(1.0)


def test_the_coefficient_comes_back_too_so_the_arithmetic_can_be_redone() -> None:
    fit = fit_power_law(series(2.0, coefficient=0.25))
    assert fit.coefficient == pytest.approx(0.25)
    assert fit.predict(100.0) == pytest.approx(0.25 * 100.0**2)


def test_an_exponent_fitted_from_timings_is_measured() -> None:
    # It is a summary of measurements, like watts from an energy counter over a
    # duration, so it is not weakened by being a fit.
    assert fit_power_law(series(1.0)).exponent.status == "measured"


def test_a_fit_is_never_stronger_than_the_timings_it_was_fitted_to() -> None:
    fit = fit_power_law(series(1.0), status="estimated")
    assert fit.exponent.status == "estimated"


def test_a_status_stronger_than_measured_is_not_invented() -> None:
    # Nothing above `measured` exists in the taxonomy, and a caller passing
    # nonsense must not be able to mint it.
    assert fit_power_law(series(1.0), status="measured").exponent.status == "measured"


def test_the_exponent_carries_the_range_it_was_measured_over() -> None:
    fit = fit_power_law(series(2.0, sizes=(10, 100, 1000)))
    assert fit.size_range() == (10.0, 1000.0)
    assert "10 to 1000" in str(fit.exponent.notes)
    assert "R²" in str(fit.exponent.notes)


def test_noise_is_tolerated_while_the_shape_still_holds() -> None:
    # Real timings wobble. A few percent must not turn a good fit into a refusal.
    wobbled = [
        Observation(size=50.0, seconds=2.55),
        Observation(size=200.0, seconds=39.2),
        Observation(size=800.0, seconds=648.0),
    ]
    fit = fit_power_law(wobbled)
    assert fit.usable()
    assert fit.exponent.value == pytest.approx(2.0, abs=0.05)


def test_flat_durations_read_as_a_zero_exponent_rather_than_a_refusal() -> None:
    # Constant cost is a real answer about a workload, and the fit explains all
    # of the variation there is, because there is none.
    fit = fit_power_law([Observation(size=float(n), seconds=3.0) for n in (10, 100, 1000)])
    assert fit.usable()
    assert fit.exponent.value == pytest.approx(0.0)
    assert fit.r_squared == pytest.approx(1.0)


# --- The refusals, each naming what would resolve it -------------------------


def test_two_points_are_refused_because_they_fit_every_line() -> None:
    fit = fit_power_law([Observation(1.0, 1.0), Observation(10.0, 10.0)])
    assert fit.refused and not fit.usable()
    assert str(MINIMUM_OBSERVATIONS) in str(fit.exponent.notes)


def test_a_refusal_keeps_the_runs_it_was_not_able_to_use() -> None:
    fit = fit_power_law([Observation(1.0, 1.0), Observation(10.0, 10.0)])
    assert len(fit.observations) == 2


def test_sizes_too_close_together_are_refused_with_the_ratio_named() -> None:
    fit = fit_power_law([Observation(100.0, 1.0), Observation(150.0, 1.5), Observation(180.0, 1.8)])
    assert fit.refused
    assert f"{MINIMUM_SIZE_RATIO:g}" in str(fit.exponent.notes)


def test_a_duration_of_zero_is_refused_because_it_has_no_logarithm() -> None:
    runs = series(1.0)
    runs[0] = Observation(size=runs[0].size, seconds=0.0)
    fit = fit_power_law(runs)
    assert fit.refused
    assert "above" in str(fit.exponent.notes)


def test_a_size_of_zero_is_refused_too() -> None:
    runs = series(1.0)
    runs[0] = Observation(size=0.0, seconds=1.0)
    assert fit_power_law(runs).refused


@pytest.mark.parametrize("bad", [math.nan, math.inf, -math.inf])
def test_a_number_that_is_not_finite_is_refused(bad: float) -> None:
    runs = series(1.0)
    runs[1] = Observation(size=runs[1].size, seconds=bad)
    assert fit_power_law(runs).refused


def test_a_poor_fit_is_refused_rather_than_reported() -> None:
    # The useful output here is the finding: these slices are not measuring one
    # consistent behaviour, so no exponent from them describes the run.
    scattered = [
        Observation(size=10.0, seconds=5.0),
        Observation(size=100.0, seconds=0.5),
        Observation(size=1000.0, seconds=40.0),
    ]
    fit = fit_power_law(scattered)
    assert fit.refused
    assert f"{DEFAULT_MINIMUM_R_SQUARED:.2f}" in str(fit.exponent.notes)


def test_the_bar_for_a_good_fit_can_be_lowered_on_purpose() -> None:
    scattered = [
        Observation(size=10.0, seconds=1.0),
        Observation(size=100.0, seconds=8.0),
        Observation(size=1000.0, seconds=200.0),
    ]
    assert fit_power_law(scattered, minimum_r_squared=0.0).usable()


def test_a_refused_fit_predicts_nothing() -> None:
    assert fit_power_law([Observation(1.0, 1.0)]).predict(10.0) is None


# --- What the exponent means, in words --------------------------------------


def test_a_linear_reading_says_the_projection_is_sound() -> None:
    assert "proportion" in fit_power_law(series(1.0)).reading


def test_a_superlinear_reading_warns_that_a_linear_projection_understates() -> None:
    reading = fit_power_law(series(2.0)).reading
    assert "understate" in reading
    # And it says by how much, per doubling, which is the actionable form.
    assert "4.00" in reading


def test_a_sublinear_reading_blames_fixed_overhead_rather_than_the_algorithm() -> None:
    reading = fit_power_law(series(0.2)).reading
    assert "overhead" in reading or "start-up" in reading
    assert "overstate" in reading


# --- Serialisation ----------------------------------------------------------


def test_the_fit_serialises_its_evidence_not_just_its_answer() -> None:
    mapping = fit_power_law(series(2.0)).to_mapping()
    assert mapping["exponent"]["status"] == "measured"
    assert mapping["r_squared"] == pytest.approx(1.0)
    assert len(mapping["observations"]) == 3
    assert "refused" not in mapping


def test_a_refusal_serialises_as_a_refusal() -> None:
    mapping = fit_power_law([Observation(1.0, 1.0)]).to_mapping()
    assert mapping["refused"] is True
    assert mapping["exponent"]["status"] == "TODO"


def test_the_exponent_is_not_smuggled_in_as_a_bare_number() -> None:
    # The exponent is a quantity and is checked like one; only the evidence
    # beside it is exempt from the every-number-is-a-quantity rule.
    assert not is_bare_number_exempt("measurement.scaling.exponent")
    assert is_bare_number_exempt("measurement.scaling.r_squared")
    assert is_bare_number_exempt("measurement.scaling.observations")


# --- The projection that uses it --------------------------------------------


def test_without_a_fit_the_projection_is_exactly_what_it_always_was() -> None:
    projection = project_to_completion(
        Quantity(value=2.0, unit="kWh", status="measured"), fraction=0.25
    )
    assert projection.quantity.value == pytest.approx(8.0)
    assert any("same per unit" in assumption for assumption in projection.assumptions)


def test_without_a_fit_the_projection_now_says_the_assumption_is_unchecked() -> None:
    projection = project_to_completion(Quantity(value=1.0, status="measured"), fraction=0.5)
    assert any("uniform" in limit for limit in projection.limits)


def test_a_measured_linear_exponent_reproduces_the_old_arithmetic() -> None:
    # The generalisation has to reduce to the special case, or it is a different
    # feature wearing the same name.
    fit = fit_power_law(series(1.0))
    projection = project_to_completion(
        Quantity(value=2.0, unit="kWh", status="measured"), fraction=0.25, scaling=fit
    )
    assert projection.quantity.value == pytest.approx(8.0)


def test_a_quadratic_exponent_projects_by_the_square_of_the_ratio() -> None:
    fit = fit_power_law(series(2.0))
    projection = project_to_completion(
        Quantity(value=2.0, unit="kWh", status="measured"), fraction=0.25, scaling=fit
    )
    assert projection.quantity.value == pytest.approx(32.0)
    assert "^2.000" in projection.method


def test_the_projection_says_how_far_beyond_the_measured_range_it_reaches() -> None:
    fit = fit_power_law(series(2.0, sizes=(10, 40, 160)))
    projection = project_to_completion(
        Quantity(value=1.0, status="measured"), fraction=0.01, scaling=fit
    )
    assert any("100 times the largest size" in limit for limit in projection.limits)


def test_a_projection_with_a_measured_exponent_is_still_only_estimated() -> None:
    fit = fit_power_law(series(1.0))
    projection = project_to_completion(
        Quantity(value=1.0, status="measured"), fraction=0.5, scaling=fit
    )
    assert projection.quantity.status == "estimated"


def test_a_weakly_founded_exponent_weakens_the_projection() -> None:
    fit = fit_power_law(series(1.0), status="estimated")
    projection = project_to_completion(
        Quantity(value=1.0, status="measured"), fraction=0.5, scaling=fit
    )
    assert projection.quantity.status == "estimated"


def test_a_refused_fit_refuses_the_projection_and_carries_the_reason() -> None:
    # Having measured the scaling and failed is not the same as never having
    # looked: projecting anyway would assert a proportionality the runs contradict.
    refused = fit_power_law([Observation(1.0, 1.0), Observation(10.0, 10.0)])
    projection = project_to_completion(
        Quantity(value=1.0, status="measured"), fraction=0.5, scaling=refused
    )
    assert projection.refused
    assert str(MINIMUM_OBSERVATIONS) in str(projection.quantity.notes)


def test_an_unusable_fit_object_is_refused_even_if_it_claims_not_to_be() -> None:
    hollow = ScalingFit(
        exponent=Quantity(unit="exponent", status="measured"), method="m", reading="r"
    )
    assert project_to_completion(
        Quantity(value=1.0, status="measured"), fraction=0.5, scaling=hollow
    ).refused


# --- The ladder the runs come from ------------------------------------------


def reading_with(size: float, key: str = "max_iters") -> RepositoryReading:
    from pathlib import Path

    return RepositoryReading(
        root=Path("."),
        entrypoint="train.py",
        work_size=WorkSizeCandidate(key, size, f"config.py::{key}"),
    )


def test_the_top_rung_is_the_slice_that_would_have_been_run_anyway() -> None:
    ladder = scaling_ladder(reading_with(600000.0))
    assert ladder[-1][2] == 600.0
    assert ladder[-1][1] == pytest.approx(0.001)


def test_the_ladder_spans_enough_to_tell_a_line_from_a_curve() -> None:
    sizes = [size for _, _, size in scaling_ladder(reading_with(600000.0))]
    assert max(sizes) / min(sizes) >= MINIMUM_SIZE_RATIO


def test_the_rungs_below_the_top_cost_a_fraction_of_it() -> None:
    # The whole point is that checking the assumption is cheap.
    sizes = [size for _, _, size in scaling_ladder(reading_with(600000.0))]
    assert sum(sizes) < 1.4 * max(sizes)


def test_the_ladder_comes_back_smallest_first() -> None:
    sizes = [size for _, _, size in scaling_ladder(reading_with(600000.0))]
    assert sizes == sorted(sizes)


def test_rungs_that_collide_after_rounding_are_dropped_rather_than_run_twice() -> None:
    ladder = scaling_ladder(reading_with(2.0))
    sizes = [size for _, _, size in ladder]
    assert sizes == [1.0]


def test_a_repository_with_no_stated_size_gets_no_ladder() -> None:
    from pathlib import Path

    assert scaling_ladder(RepositoryReading(root=Path("."), entrypoint="train.py")) == ()


def test_the_command_passes_the_size_as_the_repository_own_flag() -> None:
    ladder = scaling_ladder(reading_with(600000.0, key="n_steps"))
    assert ladder[-1][0][-2:] == ("--n_steps", "600")


@pytest.mark.parametrize(("steps", "growth"), [(0, 4.0), (-1, 4.0), (3, 1.0), (3, 0.5)])
def test_a_ladder_nobody_can_build_is_empty_rather_than_wrong(steps: int, growth: float) -> None:
    assert scaling_ladder(reading_with(600000.0), steps=steps, growth=growth) == ()
