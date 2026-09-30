"""
What each command-line verb does.

Module summary
--------------
One function per verb. Each takes the parsed arguments, does the work through the
library, prints for a human on standard output, and returns an exit code. None of
them calls :func:`sys.exit`, so every one of them is callable from a test and from
another program.

Two conventions run through all of them. Anything a machine might parse goes to
standard output; anything a human needs to read but a pipe should not receive goes
through the logger, which writes to standard error. And ``--json`` is available
wherever there is structure worth handing to another tool, so nothing here has to
be scraped.

Usage example
-------------
>>> import argparse, contextlib, io
>>> from saggio.cli.commands import machine
>>> with contextlib.redirect_stdout(io.StringIO()):
...     verdict = machine(argparse.Namespace(json=True))
>>> verdict
0

Author
------
Warith Harchaoui
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

import os_helper as osh

from ..analyze.capability import measurable, paths_read, probe, summary
from ..analyze.power import PowerMeter
from ..analyze.run import record_consent, run_slice
from ..auditor import AuditOptions, audit, audit_git_url
from ..catalog.registry import SECTION_OF_KIND, Catalog, add_row, stale_report
from ..diff import compare
from ..estimate.machine import detect_machine
from ..fold import fold_measurement
from ..model.cost_model import CostModel
from ..model.validate import overall_status, validate
from ..report.dashboard import render_dashboard
from ..report.html import render_html
from ..report.markdown import render_markdown
from ..report.office import OFFICE_FORMATS, render_office
from ..templates import template_text
from .exit_codes import DECLINED, INVALID, OK, UNAVAILABLE, USAGE


def _emit(payload: Any, *, as_json: bool) -> None:
    """Print a payload as JSON, or leave it to the caller.

    Parameters
    ----------
    payload : Any
        Something serialisable.
    as_json : bool
        Whether the caller asked for JSON.

    Examples
    --------
    >>> _emit({"a": 1}, as_json=False)
    """
    if as_json:
        print(json.dumps(payload, indent=2, ensure_ascii=False, default=str))


def _write(text: str, destination: str | None) -> None:
    r"""Write text to a file, or to standard output when there is no file.

    Parameters
    ----------
    text : str
        What to write.
    destination : str or None
        Where to write it.

    Examples
    --------
    >>> _write("hello\n", None)
    hello
    """
    if destination is None:
        sys.stdout.write(text)
        return
    target = Path(destination)
    osh.make_directory(str(target.parent))
    target.write_text(text, encoding="utf-8")
    osh.info(f"Wrote {target}")


def _load(path: str) -> CostModel:
    """Load a cost model, or raise with a message a user can act on.

    Parameters
    ----------
    path : str
        The file to read.

    Returns
    -------
    CostModel
        The parsed model.

    Raises
    ------
    AssertionError
        If the file is missing or empty.
    ValueError
        If it is not a YAML mapping.

    Examples
    --------
    >>> _load("/nonexistent.yaml")
    Traceback (most recent call last):
        ...
    AssertionError: ...
    """
    return CostModel.load(path)


def initialise(args: argparse.Namespace) -> int:
    """Write a starter cost model.

    Parameters
    ----------
    args : argparse.Namespace
        With ``template`` and ``output``.

    Returns
    -------
    int
        An exit code.

    Examples
    --------
    >>> initialise(argparse.Namespace(template="nope", output=None))
    2
    """
    try:
        text = template_text(args.template)
    except ValueError as exc:
        osh.error(str(exc))
        return USAGE
    _write(text, args.output)
    if args.output:
        osh.info(f"Now fill in the TODOs, then check it with `saggio validate {args.output}`.")
    return OK


def check(args: argparse.Namespace) -> int:
    """Validate a cost model against the schema and the honesty rules.

    Parameters
    ----------
    args : argparse.Namespace
        With ``model`` and ``json``.

    Returns
    -------
    int
        :data:`~saggio.cli.exit_codes.OK` when the model has no
        errors, :data:`~saggio.cli.exit_codes.INVALID` otherwise.
        Warnings never fail it: a model that admits it is incomplete is being
        honest, and this package does not punish that.

    Examples
    --------
    >>> check(argparse.Namespace(model="/nonexistent.yaml", json=False))
    2
    """
    try:
        model = _load(args.model)
    except (AssertionError, ValueError) as exc:
        osh.error(str(exc))
        return USAGE

    report = validate(model)
    if args.json:
        _emit(report.to_mapping() | {"overall_status": overall_status(model)}, as_json=True)
    else:
        if report.issues:
            print(report.to_text())
        print(report.summary())
        weakest = overall_status(model)
        if weakest:
            print(f"Weakest number anywhere in the model: {weakest}.")
    return OK if report.ok else INVALID


def render(args: argparse.Namespace) -> int:
    """Render a cost model as a report.

    Parameters
    ----------
    args : argparse.Namespace
        With ``model``, ``format``, ``output``, and ``reference_doc``.

    Returns
    -------
    int
        An exit code.

    Examples
    --------
    >>> render(argparse.Namespace(model="/nonexistent.yaml", format="md",
    ...                           output=None, reference_doc=None))
    2
    """
    try:
        model = _load(args.model)
    except (AssertionError, ValueError) as exc:
        osh.error(str(exc))
        return USAGE

    if args.format in {"md", "markdown"}:
        _write(render_markdown(model), args.output)
        return OK
    if args.format == "html":
        _write(render_html(model), args.output)
        return OK
    if args.format in OFFICE_FORMATS:
        if args.output is None:
            osh.error(f"{args.format} output needs --output, since it is not text.")
            return USAGE
        try:
            written = render_office(
                model,
                args.output,
                output_format=args.format,
                reference_document=args.reference_doc,
            )
        except RuntimeError as exc:
            osh.error(str(exc))
            return UNAVAILABLE
        osh.info(f"Wrote {written}")
        return OK

    osh.error(f"Unknown format {args.format!r}.")
    return USAGE


def dashboard(args: argparse.Namespace) -> int:
    """Render several cost models as one dashboard page.

    Parameters
    ----------
    args : argparse.Namespace
        With ``models`` (one path per model) and ``output``.

    Returns
    -------
    int
        An exit code. One unreadable model fails the whole page, because a
        dashboard silently missing a project would read as a team without it.

    Examples
    --------
    >>> dashboard(argparse.Namespace(models=["/nonexistent.yaml"], output=None))
    2
    """
    loaded = []
    for path in args.models:
        try:
            loaded.append(_load(path))
        except (AssertionError, ValueError) as exc:
            osh.error(str(exc))
            return USAGE
    _write(render_dashboard(loaded), args.output)
    return OK


def audit_command(args: argparse.Namespace) -> int:
    """Build a cost model for a repository or a git URL.

    Parameters
    ----------
    args : argparse.Namespace
        With ``target`` and the audit options.

    Returns
    -------
    int
        An exit code.

    Examples
    --------
    >>> isinstance(audit_command, type(audit_command))
    True
    """
    options = AuditOptions(
        run=args.run,
        use_llm=not args.no_llm,
        country=args.country,
        provider=args.provider,
        instance=args.instance,
        timeout_seconds=args.timeout,
        source_accelerator=args.source_accelerator,
        target_accelerator=args.target_accelerator,
        precision=args.precision,
        fetch_prices=args.fetch_prices,
    )
    target = str(args.target)
    try:
        if target.startswith(("http://", "https://", "git@")) or target.endswith(".git"):
            result = audit_git_url(target, options=options)
        else:
            result = audit(target, options=options)
    except RuntimeError as exc:
        osh.error(str(exc))
        return UNAVAILABLE
    except AssertionError as exc:
        osh.error(str(exc))
        return USAGE

    if args.json:
        _emit(
            {
                "model": result.model.data,
                "validation": result.report.to_mapping(),
                "notes": list(result.notes),
            },
            as_json=True,
        )
    else:
        _write(result.model.to_yaml(), args.output)
        if result.report.issues:
            print("\nThe model this audit produced has issues:", file=sys.stderr)
            print(result.report.to_text(), file=sys.stderr)
        if result.notes:
            # These go to standard error, so redirecting the model to a file still
            # shows the reader what the audit could not establish and why.
            print("\nRead before trusting this model:", file=sys.stderr)
            for note in result.notes:
                print(f"  - {note}", file=sys.stderr)
    return OK if result.report.ok else INVALID


def measure(args: argparse.Namespace) -> int:
    """Run a command and report what it cost to run.

    Parameters
    ----------
    args : argparse.Namespace
        With ``command``, ``directory``, ``timeout``, ``fraction``, and ``json``.

    Returns
    -------
    int
        An exit code. A command that itself fails is reported faithfully and
        still returns :data:`~saggio.cli.exit_codes.OK`: the
        measurement succeeded, and it measured a failure.

    Examples
    --------
    >>> measure(argparse.Namespace(command=["--"], directory=None, timeout=1.0,
    ...                            fraction=None, json=False, no_profile=False))
    2
    """
    # argparse.REMAINDER hands back the "--" separator along with the command, and
    # running it would look for a program literally called "--".
    command = list(args.command)
    if command and command[0] == "--":
        command = command[1:]
    if not command:
        osh.error(
            "Nothing to measure. Pass the command after --, for example: measure -- pytest -q"
        )
        return USAGE
    result = run_slice(
        command,
        working_directory=args.directory,
        timeout_seconds=args.timeout,
        fraction_completed=args.fraction,
        profile=not args.no_profile,
        baseline_seconds=args.baseline,
    )
    payload = {
        "command": list(result.command),
        "exit_code": result.exit_code,
        "wall_seconds": round(result.wall_seconds, 4),
        "watts": result.power.watts,
        "idle_watts": result.baseline.watts if result.baseline else None,
        "marginal_watts": result.marginal_watts(),
        "power_scope": result.power.scope,
        "truncated": result.truncated,
        "hot_path": [entry.to_mapping() for entry in result.hot_path],
        "warnings": list(result.warnings),
    }
    if args.json:
        _emit(payload, as_json=True)
    else:
        print(f"Ran: {' '.join(result.command)}")
        print(f"Exit code: {result.exit_code}")
        print(f"Wall-clock: {result.wall_seconds:.3f} s")
        if result.power.measured():
            print(f"Average power: {result.power.watts:.1f} W (measured)")
            if result.baseline is not None and result.baseline.measured():
                print(f"  machine at rest before it: {result.baseline.watts:.1f} W")
                marginal = result.marginal_watts()
                # The counter measured the machine. What the slice added is the
                # difference, and it is the figure worth quoting for the slice.
                print(
                    f"  added by this slice: {marginal:.1f} W"
                    if marginal is not None
                    else "  added by this slice: not established"
                )
        else:
            print("Average power: not measured")
        for entry in result.hot_path[:5]:
            print(f"  {entry.cumulative_seconds:8.3f} s  {entry.function}")
        for warning in result.warnings:
            osh.warning(warning)
    if args.into:
        return _fold_into(args, result)
    return OK


def _fold_into(args: argparse.Namespace, result: Any) -> int:
    """Write a measurement into a model, or say why it was not written.

    Parameters
    ----------
    args : argparse.Namespace
        With ``into``, ``units`` and ``scenario``.
    result : SliceResult
        What the run produced.

    Returns
    -------
    int
        An exit code. A run that failed or was cut short is refused rather than
        folded, because a command that exited non-zero measured a failure and a
        failure has no cost per unit of work: it produced no units.

    Examples
    --------
    >>> namespace = argparse.Namespace(into="/nope.yaml", units=1.0, scenario=None)
    >>> _fold_into(namespace, None)
    2
    """
    if result is not None and (result.exit_code != 0 or result.truncated):
        osh.error(
            f"The command exited {result.exit_code} and nothing was written to "
            f"{args.into}. A failed run measured a failure, which has no cost per "
            "unit of work because it produced no units."
        )
        return USAGE
    try:
        model = _load(args.into)
    except (AssertionError, ValueError) as exc:
        osh.error(str(exc))
        return USAGE
    folded = fold_measurement(
        model,
        seconds=result.wall_seconds,
        units=args.units,
        power=result.power,
        scenario=args.scenario,
        command=" ".join(result.command),
    )
    if folded.refused:
        osh.error(f"Nothing was written to {args.into}: {folded.refused}")
        return INVALID
    folded.model.save(args.into)
    osh.info(f"Wrote {args.into}")
    for change in folded.changes:
        print(f"  {change}")
    return OK


def difference(args: argparse.Namespace) -> int:
    """Compare two cost models and apply the drift gate.

    Parameters
    ----------
    args : argparse.Namespace
        With ``before``, ``after``, ``threshold``, and ``json``.

    Returns
    -------
    int
        An exit code.

    Examples
    --------
    >>> difference(argparse.Namespace(before="/nope.yaml", after="/nope.yaml",
    ...                               threshold=10.0, json=False))
    2
    """
    try:
        earlier, later = _load(args.before), _load(args.after)
    except (AssertionError, ValueError) as exc:
        osh.error(str(exc))
        return USAGE

    comparison = compare(earlier, later, threshold_percent=args.threshold)
    if args.json:
        _emit(comparison.to_mapping(), as_json=True)
    else:
        if not comparison.changes:
            print("Nothing changed.")
        for change in comparison.changes:
            print(change.describe())
        breaches = comparison.breaches()
        print(
            f"{len(comparison.changes)} change(s), {len(breaches)} past the "
            f"{args.threshold:g}% gate."
        )
    return OK if comparison.passes() else INVALID


def catalog_list(args: argparse.Namespace) -> int:
    """Print a catalogue's rows.

    Parameters
    ----------
    args : argparse.Namespace
        With ``kind`` and ``json``.

    Returns
    -------
    int
        An exit code.

    Examples
    --------
    >>> catalog_list(argparse.Namespace(kind="nope", json=False))
    2
    """
    if args.kind not in SECTION_OF_KIND:
        osh.error(f"Unknown kind {args.kind!r}. Known: {', '.join(sorted(SECTION_OF_KIND))}.")
        return USAGE
    name, section = SECTION_OF_KIND[args.kind]
    rows = Catalog.load(name).rows(section)
    if args.json:
        _emit(rows, as_json=True)
    else:
        for key, row in rows.items():
            summary = ", ".join(
                f"{field}={value}"
                for field, value in row.items()
                if field not in {"key", "source_url", "retrieved_date", "notes", "detect"}
            )
            print(f"{key:<28} {summary}")
        print(f"{len(rows)} row(s).")
    return OK


def catalog_add(args: argparse.Namespace) -> int:
    """Add a row to the user's catalogue overlay.

    Parameters
    ----------
    args : argparse.Namespace
        With ``kind``, ``key``, ``source_url``, ``retrieved_date``, and ``field``.

    Returns
    -------
    int
        An exit code.

    Examples
    --------
    >>> catalog_add(argparse.Namespace(kind="gpu", key="X", source_url="",
    ...                                retrieved_date="2026-01-01", field=["tdp_w=400"]))
    2
    """
    row: dict[str, Any] = {
        "key": args.key,
        "source_url": args.source_url,
        "retrieved_date": args.retrieved_date,
    }
    for pair in args.field or []:
        name, _, raw = str(pair).partition("=")
        if not name or not raw:
            osh.error(f"--field expects name=value, got {pair!r}.")
            return USAGE
        # int first, then float, so 400 stays an int but 2.5e-06 — the natural
        # spelling for a per-token price — lands as a number rather than as the
        # string "2.5e-06" that would never go stale and never compute.
        try:
            row[name] = int(raw)
        except ValueError:
            try:
                row[name] = float(raw)
            except ValueError:
                row[name] = raw
    try:
        written = add_row(args.kind, row)
    except ValueError as exc:
        osh.error(str(exc))
        return USAGE
    osh.info(f"Added {args.key} to {written}. It is usable straight away.")
    return OK


def catalog_freshness(args: argparse.Namespace) -> int:
    """Report the catalogue rows nobody has checked lately.

    Parameters
    ----------
    args : argparse.Namespace
        With ``json``.

    Returns
    -------
    int
        :data:`~saggio.cli.exit_codes.INVALID` when anything is
        stale, so this works as a continuous-integration gate against shipping
        numbers that have quietly gone out of date.

    Examples
    --------
    >>> import contextlib, io
    >>> with contextlib.redirect_stdout(io.StringIO()):
    ...     verdict = catalog_freshness(argparse.Namespace(json=True))
    >>> verdict in {0, 1}
    True
    """
    stale = stale_report()
    if args.json:
        _emit(stale, as_json=True)
    elif not stale:
        print("Every catalogue row is within its refresh window.")
    else:
        for kind, keys in stale.items():
            print(f"{kind}: {', '.join(keys)}")
        print("Re-read the sources and add the rows again with a fresh retrieved_date.")
    return INVALID if stale else OK


def machine(args: argparse.Namespace) -> int:
    """Print what this machine is and what the catalogue knows about it.

    Parameters
    ----------
    args : argparse.Namespace
        With ``json``.

    Returns
    -------
    int
        An exit code.

    Examples
    --------
    >>> import contextlib, io
    >>> with contextlib.redirect_stdout(io.StringIO()):
    ...     verdict = machine(argparse.Namespace(json=True))
    >>> verdict
    0
    """
    profile = detect_machine()
    if args.json:
        _emit(
            {
                "platform": profile.platform,
                "cpu": profile.cpu_model,
                "cpu_catalogue_key": profile.cpu_key,
                "cpu_is_fallback": profile.cpu_is_fallback,
                "physical_cores": profile.physical_cores,
                "logical_cores": profile.logical_cores,
                "memory_gb": profile.memory_gb,
                "gpus": list(profile.gpu_names),
                "gpu_catalogue_key": profile.gpu_key,
                "catalog_misses": list(profile.catalog_misses),
            },
            as_json=True,
        )
    else:
        print(profile.describe())
        print(f"Memory: {profile.memory_gb:g} GB")
        print(f"CPU catalogue key: {profile.cpu_key or 'none'}", end="")
        print(" (generic fallback)" if profile.cpu_is_fallback else "")
        print(f"GPU catalogue key: {profile.gpu_key or 'none'}")
        for miss in profile.catalog_misses:
            osh.warning(miss)
    return OK


def power(args: argparse.Namespace) -> int:
    """Print which energy counters this machine will let this user read.

    The question this answers is not "can power be measured here" but "what is
    in the way, and is it something you can decide about". A counter that is
    absent, one that is closed to you, and one that lives behind a password are
    three different answers, and only the middle one has a remedy.

    Nothing is escalated. A remedy is printed with the reason the counter is
    shut beside it, and running it stays the reader's decision.

    Parameters
    ----------
    args : argparse.Namespace
        With ``json`` and ``seconds``.

    Returns
    -------
    int
        :data:`~saggio.cli.exit_codes.OK` when at least one counter reads,
        :data:`~saggio.cli.exit_codes.OK` otherwise too: a machine without
        counters is not a broken machine, and a script that gates on this
        should read the states rather than the exit code.

    Examples
    --------
    >>> import contextlib, io
    >>> with contextlib.redirect_stdout(io.StringIO()):
    ...     verdict = power(argparse.Namespace(json=True, seconds=0.0))
    >>> verdict
    0
    """
    interfaces = probe()
    if args.json:
        payload: dict[str, Any] = {
            "measurable": measurable(),
            "paths_read": list(paths_read()),
            "interfaces": [
                {
                    "name": interface.name,
                    "covers": interface.covers,
                    "state": interface.state,
                    "detail": interface.detail,
                    "remedy": interface.remedy,
                }
                for interface in interfaces
            ],
        }
        if args.seconds > 0.0:
            payload["measurement"] = _measure_idle(args.seconds)
        _emit(payload, as_json=True)
        return OK

    print(summary(), end="")
    for path in paths_read():
        print(f"reads: {path}")
    if args.seconds > 0.0:
        reading = _measure_idle(args.seconds)
        print()
        if reading["watts"] is None:
            print(f"Over {args.seconds:g}s: nothing measured. {reading['scope']}")
        else:
            print(
                f"Over {args.seconds:g}s this machine drew {reading['watts']:.1f} W "
                f"({reading['joules']:.1f} J) through {', '.join(reading['sources'])}."
            )
            print(f"    {reading['scope']}")
    return OK


def _measure_idle(seconds: float) -> dict[str, Any]:
    """Measure the machine's own draw for a while, and return it as a mapping.

    This measures the *machine*, not any particular program: whatever else is
    running is in the figure. That is the point — a reader who sees an idle
    machine drawing thirty watts has learned why a slice measured on a busy
    laptop is not the slice's own cost.

    Parameters
    ----------
    seconds : float
        How long to watch.

    Returns
    -------
    dict
        Watts, joules, the counters that answered, and what they cover.

    Examples
    --------
    >>> sorted(_measure_idle(0.0))
    ['joules', 'scope', 'seconds', 'sources', 'watts']
    """
    meter = PowerMeter.start()
    if seconds > 0.0:
        time.sleep(seconds)
    reading = meter.stop(seconds=seconds)
    return {
        "seconds": seconds,
        "watts": reading.watts,
        "joules": reading.joules,
        "sources": list(reading.sources),
        "scope": reading.scope,
    }


def consent(args: argparse.Namespace) -> int:
    """Grant or revoke permission to run downloaded code.

    Parameters
    ----------
    args : argparse.Namespace
        With ``decision``.

    Returns
    -------
    int
        :data:`~saggio.cli.exit_codes.OK` when granted,
        :data:`~saggio.cli.exit_codes.DECLINED` when revoked, so
        a script can see which way it went.

    Examples
    --------
    >>> import tempfile
    >>> with tempfile.TemporaryDirectory() as folder:
    ...     consent(argparse.Namespace(decision="revoke", path=f"{folder}/d.json"))
    3
    """
    granted = args.decision == "grant"
    path = record_consent(granted, getattr(args, "path", None))
    osh.info(("Granted" if granted else "Revoked") + f", recorded in {path}.")
    return OK if granted else DECLINED
