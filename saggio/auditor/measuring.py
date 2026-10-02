"""Running a slice of the work, and reporting what it cost.

Module summary
--------------
The one part of an audit that executes somebody's code. It is consent-gated,
bounded, and it reports the scope of every counter it read rather than implying
the wall socket.

Author
------
Warith Harchaoui
"""

from __future__ import annotations

import os_helper as osh

from ..analyze.run import (
    SliceResult,
    require_consent,
    run_scaling_series,
    run_slice,
)
from ..analyze.static import (
    RepositoryReading,
    capped_entrypoint_command,
    scaling_ladder,
)
from ..estimate.scaling import (
    MINIMUM_OBSERVATIONS,
    Observation,
    ScalingFit,
    fit_power_law,
)
from .options import AuditOptions


def _run_a_slice(
    reading: RepositoryReading, options: AuditOptions
) -> tuple[SliceResult | None, ScalingFit | None, list[str]]:
    """Run a bounded slice, if the user allows it and there is one to run.

    With ``scaling_steps`` above one this runs a ladder of differently sized
    slices instead of a single one, so that how the work grows with the job is
    measured rather than assumed. The largest rung is the slice that would have
    been run anyway, and it is the one every cost figure comes from; the smaller
    rungs exist only to fit the exponent, and together they add about a third to
    the time the single slice took.

    A ladder is run without the profiler, for a reason that is in
    :func:`saggio.analyze.run.run_scaling_series`: ``cProfile`` charges per call
    and would put its own growth curve into the fit. The trade is that a scaling
    series reports no hot path, and in exchange every cost figure comes from an
    unprofiled run rather than an inflated one.

    Parameters
    ----------
    reading : RepositoryReading
        The static reading, which supplies the command and the fraction.
    options : AuditOptions
        What the caller asked for.

    Returns
    -------
    tuple
        The result, or ``None``; the scaling fit, or ``None`` when no series was
        run; and any notes for the reader.

    Examples
    --------
    >>> from pathlib import Path
    >>> _run_a_slice(RepositoryReading(root=Path(".")), AuditOptions(run=False))[0] is None
    True
    >>> from pathlib import Path
    >>> _run_a_slice(RepositoryReading(root=Path(".")), AuditOptions(run=False))[1] is None
    True
    """
    notes: list[str] = []
    if not options.run:
        return None, None, notes

    # What would run is decided before consent is asked: prompting a person for
    # permission — and persisting their answer — over a repository with nothing
    # safe to run would spend their trust on a no-op.
    command, fraction = capped_entrypoint_command(reading, cap_fraction=options.cap_fraction)
    fallback_note: str | None = None
    ladder: tuple[tuple[tuple[str, ...], float, float], ...] = ()
    if command is None:
        if not reading.has_tests:
            notes.append(
                "There was nothing safe to run: no entry point with a stated work "
                "size, and no test suite. Measure your own command with "
                "`saggio measure`."
            )
            return None, None, notes
        command, fraction = reading.test_command, None
        fallback_note = (
            "No entry point with a stated work size was found, so the repository's "
            "own test suite was run instead. It covers an unknown share of a real "
            "workload, so no whole-run projection follows from it."
        )
    elif options.scaling_steps > 1:
        ladder = scaling_ladder(
            reading,
            cap_fraction=options.cap_fraction,
            steps=options.scaling_steps,
        )
        if len(ladder) < MINIMUM_OBSERVATIONS:
            notes.append(
                f"A scaling series of {options.scaling_steps} sizes was asked for, but "
                f"{reading.work_size.key if reading.work_size else 'the work size'} "
                f"cuts into only {len(ladder)} distinct size(s) at this cap. One slice "
                "was run instead, and the projection keeps the linear assumption."
            )
            ladder = ()

    if not require_consent():
        notes.append(
            "Running the code was declined, so every number below comes from "
            "reading it and from the catalogues, never from a measurement."
        )
        return None, None, notes
    if fallback_note:
        notes.append(fallback_note)

    if ladder:
        osh.info(f"Running a scaling series of {len(ladder)} sizes")
        series = run_scaling_series(
            ladder,
            working_directory=reading.root,
            timeout_seconds=options.timeout_seconds,
            baseline_seconds=options.baseline_seconds,
        )
        if not series:
            notes.append(
                "Every rung of the scaling series failed or ran out of time, so "
                "nothing was measured. The warnings from the largest attempt "
                "explain why; `saggio measure` runs one command with the same "
                "machinery and reports it directly."
            )
            return None, None, notes
        primary = series[-1][1]
        notes.extend(primary.warnings)
        notes.append(
            "The slice was run without the profiler, because a scaling series "
            "needs every rung timed the same way and cProfile charges per call. "
            "There is no hot path below; the runtime is not inflated either."
        )
        if len(series) < MINIMUM_OBSERVATIONS:
            notes.append(
                f"Only {len(series)} of {len(ladder)} rungs completed, which is fewer "
                f"than the {MINIMUM_OBSERVATIONS} a scaling exponent needs, so the "
                "projection keeps the linear assumption."
            )
            return primary, None, notes
        fit = fit_power_law(
            [Observation(size=size, seconds=result.wall_seconds) for size, result in series]
        )
        notes.append(fit.reading if fit.usable() else str(fit.exponent.notes))
        return primary, fit, notes

    osh.info(f"Running a slice: {' '.join(command)}")
    result = run_slice(
        command,
        working_directory=reading.root,
        timeout_seconds=options.timeout_seconds,
        fraction_completed=fraction,
        profile=True,
        baseline_seconds=options.baseline_seconds,
    )
    notes.extend(result.warnings)
    return result, None, notes
