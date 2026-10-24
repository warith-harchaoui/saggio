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
import os
import sys
import textwrap
import time
from pathlib import Path
from typing import Any, Final

import os_helper as osh
import yaml

from ..analyze.capability import measurable, paths_read, probe, summary
from ..analyze.power import PowerMeter
from ..analyze.repeat import run_slices
from ..analyze.run import consent_terms, record_consent
from ..auditor import AuditOptions, audit, audit_git_url
from ..catalog.refresh import (
    EMBER_KEY_VARIABLE,
    EMBODIED_METHOD_URL,
    PRICE_CROSSCHECK,
    PRICE_CROSSCHECK_RATE,
    accelerators_refused,
    apply_embodied,
    apply_grid,
    apply_prices,
    apply_timezone_check,
    check_timezones,
    fetch_embodied,
    fetch_grid,
    fetch_grid_public,
    fetch_prices,
)
from ..catalog.registry import (
    SECTION_OF_KIND,
    Catalog,
    add_row,
    expiring_report,
    stale_report,
)
from ..diff import compare
from ..estimate.ghg import (
    GHG_EMISSIONS,
    placed_model,
)
from ..estimate.machine import detect_machine
from ..fold import fold_measurement
from ..i18n import DEFAULT_LANGUAGE, phrase, say
from ..i18n import number as localised
from ..model.cost_model import CostModel
from ..model.questions import questions_payload
from ..model.validate import overall_status, validate
from ..report.dashboard import render_dashboard
from ..report.html import render_html
from ..report.markdown import format_number, not_known, render_markdown
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
        osh.info(say("cli.init.next_step", path=args.output))
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
            print(say("cli.validate.weakest", status=weakest))
    return OK if report.ok else INVALID


#: How wide a paragraph this package prints to a terminal. Seventy-six leaves
#: room for the four-space indent the explanations carry and still fits the
#: eighty columns a terminal is assumed to have when it will not say.
_PROSE_WIDTH: Final[int] = 76


def _hanging(label: str, text: str) -> str:
    """Return ``label`` and ``text`` as one wrapped block, label on the first line.

    The shape a reader already knows -- ``carbon_market_based: the reason`` --
    kept when the reason is too long for one line, by indenting only what
    wraps onto the next.

    Examples
    --------
    >>> _hanging("a: ", "one two")
    'a: one two'
    >>> print(_hanging("name: ", "word " * 30))  # doctest: +ELLIPSIS
    name: word word...
          word...
    """
    # The label's own leading spaces go through ``initial_indent`` rather than
    # into the text: textwrap normalises whitespace it finds in the string, so
    # a label written as "  field=" lost its indent on any value long enough to
    # take a line of its own.
    lead = label[: len(label) - len(label.lstrip())]
    wrapped = textwrap.wrap(
        label.lstrip() + text,
        width=_PROSE_WIDTH - len(lead),
        initial_indent=lead,
        subsequent_indent=lead + " " * len(label.lstrip()),
        # A URL is one word. Split across two lines it cannot be copied, which
        # is the only reason it is printed, so it is allowed to run past the
        # margin instead.
        break_long_words=False,
        break_on_hyphens=False,
    )
    return "\n".join(wrapped)


def _paragraph(text: str, indent: str = "") -> str:
    """Return one paragraph of prose, wrapped, with every line indented.

    The sentences this package prints are long on purpose -- they say where a
    number came from and what would resolve it -- and one of them ran to 732
    characters on a single line, which a terminal turns into a block of text
    with no left edge. ``next`` had wrapped its notes since it was written;
    ``scopes`` and ``power`` printed theirs raw, so the same kind of sentence
    read well from one verb and badly from another.

    Parameters
    ----------
    text : str
        The prose to wrap. Empty input gives an empty string rather than a
        blank line, because a missing explanation should take no space.
    indent : str, optional
        Put in front of every line, continuation lines included.

    Returns
    -------
    str
        The wrapped paragraph, ready to print.

    Examples
    --------
    >>> _paragraph("")
    ''
    >>> print(_paragraph("one two three", indent="  "))
      one two three
    >>> len(max(_paragraph("word " * 60).splitlines(), key=len)) <= _PROSE_WIDTH
    True
    """
    if not text:
        return ""
    return "\n".join(
        f"{indent}{line}"
        for line in textwrap.wrap(
            text,
            width=_PROSE_WIDTH - len(indent),
            break_long_words=False,
            break_on_hyphens=False,
        )
    )


def scopes(args: argparse.Namespace) -> int:
    """Say which line of a greenhouse-gas inventory each of a model's costs goes on.

    The command this package was missing for the person who has to file the
    numbers rather than produce them. A cost model answers *what one unit of work
    costs*; an inventory asks *whose emission is it, and under which scope*. The
    second question is settled by one fact the model already states — who
    operates the machine — and nothing in the package said so out loud.

    It reports no figure the model does not already carry, and it refuses the
    one a reviewer most wants invented: a market-based scope 2 number cannot be
    derived from a grid average, so the output says what it would take instead
    of producing something plausible.

    Parameters
    ----------
    args : argparse.Namespace
        With ``model``, ``scenario`` and ``json``.

    Returns
    -------
    int
        :data:`~saggio.cli.exit_codes.OK` even when placements are open.
        An unplaceable cost is a question for a human, not a broken model, and
        this is not a gate.

    Examples
    --------
    >>> scopes(argparse.Namespace(model="/nonexistent.yaml", scenario=None, json=False))
    2
    """
    try:
        model = _load(args.model)
    except (AssertionError, ValueError) as exc:
        osh.error(str(exc))
        return USAGE

    try:
        placed = placed_model(model, scenario=args.scenario)
    except ValueError as exc:
        osh.error(str(exc))
        return USAGE

    rows = placed["placements"]
    counted = placed["by_status"]
    provider = placed["provider"]

    if args.json:
        _emit(placed, as_json=True)
        return OK

    named = placed["unit_of_work"] or say("cli.scopes.unit_default")
    print(
        say(
            "cli.scopes.heading",
            unit=named,
            provider=provider or say("cli.scopes.provider_default"),
        )
        + "\n"
    )
    # The report's own rounding, so the same figure reads the same in both
    # places. Seven decimal places of a derived gram are noise either way.
    shown = {
        row["dimension"]: (
            not_known()
            if row["value"] is None
            else f"{format_number(row['value'])} {row['unit'] or ''}".strip()
        )
        for row in rows
    }
    # Sized from what is in the table rather than from two numbers typed once.
    # Those numbers were 19 and 18, which fitted English exactly and put every
    # French table two characters past an eighty-column terminal: "Scope 3,
    # catégorie 2 — biens d'équipement" is six characters longer than the
    # English label, and nothing had looked at the French table.
    name_width = max((len(row["dimension"]) for row in rows), default=0)
    value_width = max((len(text) for text in shown.values()), default=0)
    for row in rows:
        print(
            f"  {row['dimension']:<{name_width}}  "
            f"{shown[row['dimension']]:<{value_width}}  {row['label']}"
        )
    print()
    for row in rows:
        # Why an emission got no scope, which is the answer a reader came for
        # when a line says "No scope". Read from the one list of what counts as
        # an emission: a copy kept here would have swallowed the market-based
        # explanation, which exists for exactly this case.
        if row["scope"] is None and row["dimension"] in GHG_EMISSIONS:
            print(_hanging(f"{row['dimension']}: ", row["why"]) + "\n")
    placed_rows = [row for row in rows if row["scope"] is not None]
    for row in placed_rows:
        print(f"{row['dimension']} — {row['label']}")
        print(_paragraph(row["why"], indent="  "))
        if row["source_url"]:
            print(f"  {row['source_url']}")
        if row["dual_reporting"]:
            print(_paragraph(say("cli.scopes.dual", sentence=row["dual_reporting"]), indent="  "))
        print()
    if counted:
        summary = ", ".join(f"{count} {status}" for status, count in sorted(counted.items()))
        print(_paragraph(say("cli.scopes.founded", summary=summary)))
        print(_paragraph(say("cli.scopes.filer")))
    return OK


def next_question(args: argparse.Namespace) -> int:
    """Say which open field would close the most numbers, and what it would close.

    The verb this package was missing for the person holding a fresh audit. A
    model comes back with fifteen open fields, each carrying a sentence about
    what would resolve it, and nothing saying which to answer first. They are
    not independent: a measured runtime closes six figures through the
    derivation chain, and a water usage effectiveness closes one. Working top
    to bottom spends the afternoon on the field that unlocks nothing.

    Parameters
    ----------
    args : argparse.Namespace
        With ``model`` and ``json``.

    Returns
    -------
    int
        :data:`~saggio.cli.exit_codes.OK` whatever it finds. An open model is
        the ordinary state of an honest one, so this reports and never gates.

    Examples
    --------
    >>> next_question(argparse.Namespace(model="/nonexistent.yaml", json=False))
    2
    """
    try:
        model = _load(args.model)
    except (AssertionError, ValueError) as exc:
        osh.error(str(exc))
        return USAGE

    payload = questions_payload(model)
    if args.json:
        _emit(payload, as_json=True)
        return OK

    questions = payload["questions"]
    if not payload["open_total"]:
        print(say("cli.next.nothing_open"))
        return OK

    unlocking = [q for q in questions if q["unlocks"]]
    closed_by_them = sum(q["unlocks"] for q in unlocking)
    print(
        say(
            "cli.next.unlocking",
            open_total=payload["open_total"],
            question_count=len(unlocking),
            closed_count=closed_by_them,
        )
        if unlocking
        else say("cli.next.none_unlocks", open_total=payload["open_total"])
    )
    print()

    for question in unlocking:
        print(f"  +{question['unlocks']}  {question['path']}  [{question['status']}]")
        if question["note"]:
            # The sentence the model already wrote about what would resolve it.
            # Repeating it here rather than inventing a prompt is the whole
            # reason this command can be trusted to ask the right thing.
            print(_paragraph(question["note"], indent="      "))
        print("      " + say("cli.next.closes", paths=", ".join(question["closes"])))
        print()

    alone = [q for q in questions if not q["unlocks"]]
    if alone:
        print(say("cli.next.alone", count=len(alone)))
        for question in alone:
            print(f"  {question['path']}")
    return OK


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
            osh.error(say("cli.render.needs_output", format=args.format))
            return USAGE
        try:
            written = render_office(
                model,
                args.output,
                output_format=args.format,
                reference_document=args.reference_doc,
                author=args.author,
                generated=args.generated,
                offline=args.offline,
            )
        except RuntimeError as exc:
            osh.error(str(exc))
            return UNAVAILABLE
        osh.info(say("cli.fold.wrote", path=written))
        return OK

    osh.error(
        say(
            "cli.render.unknown_format",
            format=repr(args.format),
            known=", ".join(("md", "html", *sorted(OFFICE_FORMATS))),
        )
    )
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
        language=args.language,
        country=args.country,
        provider=args.provider,
        instance=args.instance,
        timeout_seconds=args.timeout,
        baseline_seconds=args.baseline,
        scaling_steps=args.scaling_steps,
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
            print("\n" + say("cli.audit.has_issues"), file=sys.stderr)
            print(result.report.to_text(), file=sys.stderr)
        if result.notes:
            # These go to standard error, so redirecting the model to a file still
            # shows the reader what the audit could not establish and why.
            print("\n" + say("cli.audit.read_first"), file=sys.stderr)
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
        osh.error(say("cli.measure.nothing"))
        return USAGE
    repeats = int(getattr(args, "repeat", 1) or 1)
    if repeats < 1:
        osh.error(say("repeat.cannot_run", repeats=repeats))
        return USAGE
    series = run_slices(
        command,
        repeats=repeats,
        working_directory=args.directory,
        timeout_seconds=args.timeout,
        fraction_completed=args.fraction,
        profile=not args.no_profile,
        baseline_seconds=args.baseline,
    )
    # The run the model would carry, and the one every printed figure below is
    # about. The spread beside it says how far the others fell from it.
    result = series.representative()
    measurement = series.to_mapping()
    # The same mapping a model is given, plus the three figures that belong to
    # the run rather than to the model. Hand-listing the keys here is what let
    # this surface drop the attribution it had just computed: the warning below
    # quoted a share of processor work that no field of the JSON carried.
    payload = dict(measurement)
    payload.update(
        {
            "wall_seconds": round(result.wall_seconds, 4),
            "watts": result.power.watts,
            "idle_watts": result.baseline.watts if result.baseline else None,
            "marginal_watts": result.marginal_watts(),
            "truncated": result.truncated,
        }
    )
    if args.json:
        _emit(payload, as_json=True)
    else:
        print(say("cli.measure.ran", command=" ".join(result.command)))
        print(say("cli.measure.exit_code", code=result.exit_code))
        if len(series.runs) > 1:
            spread = series.runtime_spread()
            print(say("cli.measure.runs", count=len(series.runs)))
            print(
                say(
                    "cli.measure.wall_clock_median",
                    seconds=localised(f"{result.wall_seconds:.3f} s"),
                    count=len(series.runs),
                    low=localised(f"{spread.low:.3f}"),
                    high=localised(f"{spread.high:.3f} s"),
                )
            )
        else:
            print(
                say(
                    "cli.measure.wall_clock",
                    seconds=localised(f"{result.wall_seconds:.3f} s"),
                )
            )
        if result.power.measured():
            watts = series.power_spread()
            if watts is not None and len(series.runs) > 1:
                print(
                    say(
                        "cli.measure.power_median",
                        watts=localised(f"{result.power.watts:.1f} W"),
                        count=len(series.runs),
                        low=localised(f"{watts.low:.1f}"),
                        high=localised(f"{watts.high:.1f} W"),
                    )
                )
            else:
                print(
                    say(
                        "cli.measure.power",
                        watts=localised(f"{result.power.watts:.1f} W"),
                    )
                )
            if result.baseline is not None and result.baseline.measured():
                print(
                    "  "
                    + say(
                        "cli.measure.at_rest",
                        watts=localised(f"{result.baseline.watts:.1f} W"),
                    )
                )
                marginal = result.marginal_watts()
                # The counter measured the machine. What the slice added is the
                # difference, and it is the figure worth quoting for the slice.
                print(
                    "  " + say("cli.measure.added", watts=localised(f"{marginal:.1f} W"))
                    if marginal is not None
                    else "  " + say("cli.measure.added_unknown")
                )
            attributed = result.attributed_watts()
            if attributed is not None:
                # The other end of the bracket. On a machine doing anything
                # else, this is the better of the two, and printing only the
                # subtraction left the reader with the half that flatters.
                share = result.cpu_share.share if result.cpu_share else None
                by_share = (
                    say("cli.measure.attributable_share", share=localised(f"{share:.0%}"))
                    if share
                    else ""
                )
                print(
                    "  "
                    + say(
                        "cli.measure.attributable",
                        share=by_share,
                        watts=localised(f"{attributed:.1f} W"),
                    )
                )
                print("    " + say("cli.measure.covering", scope=result.attributed_scope()))
        else:
            print(say("cli.measure.power_not_measured"))
        for entry in result.hot_path[:5]:
            print(f"  {entry.cumulative_seconds:8.3f} s  {entry.function}")
        for warning in measurement.get("warnings", result.warnings):
            osh.warning(warning)
    if args.into:
        return _fold_into(args, result, measurement)
    return OK


def _fold_into(args: argparse.Namespace, result: Any, measurement: Any = None) -> int:
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
    >>> _fold_into(namespace, None, None)
    2
    """
    if result is not None and (result.exit_code != 0 or result.truncated):
        osh.error(say("cli.fold.failed_run", code=result.exit_code, path=args.into))
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
        measurement=measurement if measurement is not None else result.to_mapping(),
        scenario=args.scenario,
        command=" ".join(result.command),
    )
    if folded.refused:
        osh.error(say("cli.fold.refused", path=args.into, reason=folded.refused))
        return INVALID
    folded.model.save(args.into)
    osh.info(say("cli.fold.wrote", path=args.into))
    for change in folded.changes:
        print(f"  {change}")
    return OK


def catalog_read_pcf(args: argparse.Namespace) -> int:
    """Read a vendor's product carbon footprint and draft a row from it.

    Parameters
    ----------
    args : argparse.Namespace
        With ``document`` and ``json``.

    Returns
    -------
    int
        An exit code. A document that states a footprint without saying how
        many units it covers is :data:`~saggio.cli.exit_codes.INVALID` rather
        than a row with a guessed divisor: the whole point of the verb is that
        it does not invent the half the document does not give.

    Examples
    --------
    >>> catalog_read_pcf(argparse.Namespace(document="/nope.pdf", json=False))
    1
    """
    from ..catalog.pcf import read

    reading = read(args.document)
    if args.json:
        _emit(reading.to_mapping(), as_json=True)
        return INVALID if reading.refused else OK
    if reading.refused:
        osh.error(reading.refused)
        return INVALID
    # The working, before the answer. A draft whose arithmetic is hidden is a
    # draft nobody can check, and checking it is the only job left for the
    # person this is printed to.
    print(say("cli.pcf.read", url=reading.source_url))
    print("  " + say("cli.pcf.says", sentence=reading.sentence))
    if reading.form_factor:
        print("  " + say("cli.pcf.elsewhere", line=reading.form_factor))
        print(
            "  "
            + say(
                "cli.pcf.divided",
                units=reading.units,
                stated=localised(f"{reading.stated:g}"),
                per_unit=localised(f"{reading.per_unit:g}"),
            )
        )
    else:
        print("  " + say("cli.pcf.already_one", per_unit=localised(f"{reading.per_unit:g}")))
    print("\n" + say("cli.pcf.draft") + "\n")
    print(yaml.safe_dump(reading.draft_row(), sort_keys=False, allow_unicode=True).rstrip())
    print("\n" + say("cli.pcf.key_is_yours"))
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
            print(say("cli.diff.nothing_changed"))
        for change in comparison.changes:
            print(change.describe(threshold_percent=args.threshold))
        breaches = comparison.breaches()
        excused = comparison.excused()
        tail = (
            say("cli.diff.excused", count=len(excused))
            # Said out loud rather than silently subtracted: a release excused
            # by a hundred-per-cent band should show the reader the band.
            if excused
            else ""
        )
        print(
            say(
                "cli.diff.summary",
                count=len(comparison.changes),
                breaches=len(breaches),
                threshold=localised(f"{args.threshold:g}%"),
                tail=tail,
            )
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
        shown = [
            (
                key,
                [
                    (field, value)
                    for field, value in row.items()
                    if field not in {"key", "source_url", "retrieved_date", "notes", "detect"}
                ],
            )
            for key, row in rows.items()
        ]
        # Short rows stay on one line, which is what a reader wants from a
        # listing. A row stops fitting when one of its *values* is a sentence:
        # `embodied_scope` is prose with commas and a URL in it, so joining
        # fields with ", " produced 391-character lines a reader could not tell
        # apart from the commas inside the sentence. Those rows go one field to
        # a line, where the separator is the line break and cannot be confused
        # with anything in the value.
        width = max((len(key) for key, _ in shown), default=0)
        for key, fields in shown:
            summary = ", ".join(f"{field}={value}" for field, value in fields)
            if width + 1 + len(summary) <= _PROSE_WIDTH:
                print(f"{key:<{width}} {summary}")
                continue
            print(key)
            for field, value in fields:
                print(_hanging(f"  {field}=", str(value)))
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
            osh.error(say("cli.catalog.bad_field", pair=repr(pair)))
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
    osh.info(say("cli.catalog.added", key=args.key, path=written))
    return OK


def catalog_freshness(args: argparse.Namespace) -> int:
    """Report the catalogue rows nobody has checked lately.

    Parameters
    ----------
    args : argparse.Namespace
        With ``json`` and ``within``.

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
    ...     verdict = catalog_freshness(argparse.Namespace(json=True, within=7))
    >>> verdict in {0, 1}
    True
    """
    stale = stale_report()
    soon = expiring_report(within=args.within)
    if args.json:
        _emit(
            {
                "stale": stale,
                "expiring": {
                    kind: [{"key": key, "days_left": left} for key, left in rows]
                    for kind, rows in soon.items()
                },
            },
            as_json=True,
        )
        return INVALID if stale else OK

    if stale:
        for kind, keys in stale.items():
            print(say("cli.freshness.stale", kind=kind, keys=", ".join(keys)))
        print(say("cli.freshness.re_read"))
    else:
        print(say("cli.freshness.all_fresh"))

    # Said even when nothing is stale, and deliberately without failing. A gate
    # that turns red overnight gets the date bumped in a hurry rather than the
    # source re-read, which is the one outcome this mechanism exists to prevent.
    for kind, rows in soon.items():
        nearest = rows[0][1]
        listed = ", ".join(key for key, _ in rows[:6])
        more = say("cli.freshness.and_more", count=len(rows) - 6) if len(rows) > 6 else ""
        print(
            say(
                "cli.freshness.expiring",
                kind=kind,
                count=len(rows),
                days=nearest,
                keys=listed,
                more=more,
            )
        )
    return INVALID if stale else OK


def _refresh_embodied(args: argparse.Namespace) -> int:
    """Re-read the processor footprints, and say what was refused and why.

    Parameters
    ----------
    args : argparse.Namespace
        With ``column``, ``write`` and ``json``.

    Returns
    -------
    int
        An exit code.

    Examples
    --------
    >>> import argparse, contextlib, io
    >>> args = argparse.Namespace(column="carbon", write=None, json=False)
    >>> with contextlib.redirect_stdout(io.StringIO()):
    ...     verdict = _refresh_embodied(args)
    >>> verdict  # the hardware catalogue has only one column to refresh
    2
    """
    if getattr(args, "column", "carbon") not in ("embodied", "all"):
        osh.error(say("cli.refresh.one_column"))
        return USAGE

    rows = Catalog.bundled("hardware").rows("cpus")
    refresh = fetch_embodied(sorted(rows))

    if args.json:
        _emit(
            {
                "source": refresh.source,
                "method": EMBODIED_METHOD_URL,
                "read_on": refresh.retrieved,
                "found": {
                    key: {"kgco2e": value, "matched": matched, "die_mm2": die}
                    for key, (value, matched, die) in refresh.rows.items()
                },
                "refused": refresh.refused,
                "accelerators": accelerators_refused(),
            },
            as_json=True,
        )
    else:
        print(
            say(
                "cli.refresh.embodied.heading",
                source=refresh.source,
                found=len(refresh.rows),
                total=len(rows),
            )
        )
        for key, (value, matched, die) in sorted(refresh.rows.items()):
            print(
                "  "
                + say(
                    "cli.refresh.embodied.row",
                    key=key,
                    value=localised(f"{value:g}"),
                    matched=matched,
                    die=die,
                )
            )
        for key, why in sorted(refresh.refused.items()):
            print("  " + say("cli.refresh.refused", key=key, reason=why))
        print("  " + say("cli.refresh.embodied.method", url=EMBODIED_METHOD_URL))
        print("  " + say("cli.refresh.embodied.accelerators", reason=accelerators_refused()))
        if args.write is None:
            print(say("cli.refresh.read_only"))

    if args.write is not None:
        written = apply_embodied(Path(args.write), refresh)
        print(say("cli.refresh.embodied.wrote", count=written, path=args.write))
    return OK


def _check_timezones(args: argparse.Namespace, current: dict[str, Any]) -> int:
    """Check the timezone names against IANA and stamp the release they match.

    Parameters
    ----------
    args : argparse.Namespace
        With ``write`` and ``json``.
    current : dict
        The catalogue as it stands.

    Returns
    -------
    int
        An exit code. A zone the database does not publish fails the command
        rather than being written over: the catalogue lists compatibility names
        on purpose, so a mismatch is a question, not a correction to apply.

    Examples
    --------
    >>> import argparse, contextlib, io
    >>> with contextlib.redirect_stdout(io.StringIO()):
    ...     verdict = _check_timezones(argparse.Namespace(write=None, json=False), {})
    >>> verdict
    0
    """
    try:
        check = check_timezones(current)
    except RuntimeError as exc:
        osh.error(str(exc))
        return UNAVAILABLE

    if args.json:
        _emit(
            {
                "source": check.source,
                "tzdb_version": check.version,
                "checked": check.known,
                "unknown": check.unknown,
                "read_on": check.retrieved,
            },
            as_json=True,
        )
    else:
        print(
            say(
                "cli.refresh.timezones.heading",
                source=check.source,
                version=check.version or say("cli.refresh.timezones.unknown_version"),
                count=check.known,
            )
        )
        for key, zones in sorted(check.unknown.items()):
            print("  " + say("cli.refresh.timezones.unknown", key=key, zones=", ".join(zones)))
        if check.ok:
            print("  " + say("cli.refresh.timezones.all_known"))
        if args.write is None:
            print(say("cli.refresh.timezones.read_only"))

    if not check.ok:
        osh.error(say("cli.refresh.timezones.not_stamped"))
        return INVALID

    if args.write is not None:
        written = apply_timezone_check(Path(args.write), check)
        print(say("cli.refresh.timezones.stamped", count=written, path=args.write))
    return OK


def _refresh_prices(args: argparse.Namespace, current: dict[str, Any]) -> int:
    """Re-read the tariff column and report, or write it.

    Parameters
    ----------
    args : argparse.Namespace
        With ``write`` and ``json``.
    current : dict
        The catalogue as it stands.

    Returns
    -------
    int
        An exit code.

    Examples
    --------
    >>> import argparse, contextlib, io
    >>> with contextlib.redirect_stdout(io.StringIO()):
    ...     verdict = _refresh_prices(argparse.Namespace(write=None, json=False), {})
    >>> verdict
    0
    """
    names = {key: row.get("name", "") for key, row in current.items()}
    try:
        refresh = fetch_prices(sorted(current), names=names)
    except RuntimeError as exc:
        osh.error(str(exc))
        return UNAVAILABLE

    moved = refresh.changed(current)
    if args.json:
        _emit(
            {
                "source": refresh.source,
                "cross_check": PRICE_CROSSCHECK,
                "cross_check_rate": PRICE_CROSSCHECK_RATE,
                "collected": refresh.collected,
                "read_on": refresh.retrieved,
                "changed": {key: {"was": was, "now": now} for key, (was, now) in moved.items()},
                "unchanged": sorted(set(refresh.rows) - set(moved)),
                "skipped": refresh.skipped,
            },
            as_json=True,
        )
    else:
        when = (
            say("cli.refresh.prices.collected", when=refresh.collected) if refresh.collected else ""
        )
        print(
            say(
                "cli.refresh.prices.heading",
                source=refresh.source,
                count=len(refresh.rows),
                when=when,
            )
        )
        for key, (was, now) in sorted(moved.items()):
            shown = say("cli.refresh.prices.nothing") if was is None else localised(f"{was:g}")
            print(
                "  "
                + say(
                    "cli.refresh.prices.row",
                    key=key,
                    was=shown,
                    now=localised(f"{now:g}"),
                )
            )
        if not moved:
            print("  " + say("cli.refresh.nothing_moved"))
        for key, reason in sorted(refresh.skipped.items()):
            print("  " + say("cli.refresh.left_alone", key=key, reason=reason))
        print("  " + say("cli.refresh.prices.cross_check", source=PRICE_CROSSCHECK))
        if args.write is None:
            print(say("cli.refresh.read_only"))

    if args.write is not None:
        written = apply_prices(Path(args.write), refresh)
        print(say("cli.refresh.prices.wrote", count=written, path=args.write))
    return OK


def catalog_refresh(args: argparse.Namespace) -> int:
    """Re-read a catalogue's numbers from the source it cites.

    Read-only by default. A command that rewrites thirty-eight sourced figures
    on a bare invocation is a command somebody runs by accident, and the diff it
    leaves looks exactly like one a person checked. So it prints what would
    change and exits; ``--write`` is the deliberate second step.

    Parameters
    ----------
    args : argparse.Namespace
        With ``catalog``, ``api_key``, ``year``, ``write`` and ``json``.

    Returns
    -------
    int
        :data:`~saggio.cli.exit_codes.USAGE` for a catalogue this cannot
        refresh, :data:`~saggio.cli.exit_codes.UNAVAILABLE` when the source
        could not be reached or needs a key, otherwise
        :data:`~saggio.cli.exit_codes.OK`.

    Examples
    --------
    >>> import contextlib, io
    >>> args = argparse.Namespace(catalog="hardware", api_key=None, year=None,
    ...                           write=None, json=False)
    >>> with contextlib.redirect_stdout(io.StringIO()):
    ...     verdict = catalog_refresh(args)
    >>> verdict  # a catalogue with no machine-readable source is a usage error
    2
    """
    if args.catalog == "hardware":
        return _refresh_embodied(args)
    if args.catalog != "grid":
        osh.error(say("cli.refresh.no_source", catalog=args.catalog))
        return USAGE

    current = Catalog.bundled("grid").rows("countries")
    column = getattr(args, "column", "carbon")
    if column in ("timezones", "all"):
        verdict = _check_timezones(args, current)
        if verdict != OK or column == "timezones":
            return verdict
    if column in ("price", "both", "all"):
        verdict = _refresh_prices(args, current)
        if verdict != OK or column == "price":
            return verdict

    # A key is used when one is offered and never required. Both paths are Ember
    # and the same series; the one that answered is printed rather than left to
    # be inferred from whether it worked.
    offered = args.api_key or os.environ.get(EMBER_KEY_VARIABLE)
    try:
        refresh = (
            fetch_grid(sorted(current), api_key=offered, year=args.year)
            if offered
            else fetch_grid_public(sorted(current), year=args.year)
        )
    except RuntimeError as exc:
        osh.error(str(exc))
        return UNAVAILABLE

    moved = refresh.changed(current)
    # The countries the source has not caught up on. Printed on its own line
    # because this is precisely the fact a single refresh-wide data year used to
    # bury: every row got the newest year, including the rows that had not
    # reached it, and the stamp was the only place it could ever have shown.
    behind = sorted(key for key, found in refresh.years.items() if found != refresh.year)
    if args.json:
        _emit(
            {
                "source": refresh.source,
                "citation": refresh.citation,
                "data_year": refresh.year,
                "data_year_by_country": dict(sorted(refresh.years.items())),
                "behind_the_newest_year": behind,
                "read_on": refresh.retrieved,
                "changed": {key: {"was": was, "now": now} for key, (was, now) in moved.items()},
                "unchanged": sorted(set(refresh.rows) - set(moved)),
                "skipped": refresh.skipped,
            },
            as_json=True,
        )
    else:
        print(
            say(
                "cli.refresh.grid.heading",
                source=refresh.source,
                count=len(refresh.rows),
                year=refresh.year,
            )
        )
        for key, (was, now) in sorted(moved.items()):
            print(
                "  "
                + say(
                    "cli.refresh.grid.row",
                    key=key,
                    was=localised(f"{was:g}") if isinstance(was, (int, float)) else was,
                    now=localised(f"{now:.1f}"),
                )
            )
        if not moved:
            print("  " + say("cli.refresh.nothing_moved"))
        for key in behind:
            print("  " + say("cli.refresh.grid.behind", key=key, year=refresh.years[key]))
        for key, reason in sorted(refresh.skipped.items()):
            print("  " + say("cli.refresh.left_alone", key=key, reason=reason))
        print("  " + say("cli.refresh.grid.citation", source=refresh.citation))
        if args.write is None:
            print(say("cli.refresh.read_only"))

    if args.write is not None:
        written = apply_grid(Path(args.write), refresh)
        print(say("cli.refresh.grid.wrote", count=written, path=args.write))
    return OK


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
        print(say("cli.machine.memory", amount=localised(f"{profile.memory_gb:g} GB")))
        print(
            say("cli.machine.cpu_key", key=profile.cpu_key or say("cli.machine.none")),
            end="",
        )
        print(say("cli.machine.generic_fallback") if profile.cpu_is_fallback else "")
        print(say("cli.machine.gpu_key", key=profile.gpu_key or say("cli.machine.none")))
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
        print(say("cli.power.reads", path=path))
    if args.seconds > 0.0:
        reading = _measure_idle(args.seconds)
        print()
        if reading["watts"] is None:
            print(
                say(
                    "cli.power.nothing_measured",
                    seconds=localised(f"{args.seconds:g} s"),
                    scope=reading["scope"],
                )
            )
        else:
            print(
                say(
                    "cli.power.drew",
                    seconds=localised(f"{args.seconds:g} s"),
                    watts=localised(f"{reading['watts']:.1f} W"),
                    joules=localised(f"{reading['joules']:.1f} J"),
                    sources=", ".join(reading["sources"]),
                )
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
    >>> import contextlib, io, tempfile
    >>> with tempfile.TemporaryDirectory() as folder, contextlib.redirect_stdout(io.StringIO()):
    ...     code = consent(argparse.Namespace(decision="revoke", path=f"{folder}/d.json"))
    >>> code
    3
    """
    granted = args.decision == "grant"
    language = getattr(args, "language", DEFAULT_LANGUAGE)
    # Printed, not logged, and printed *before* anything is written. This verb
    # recorded `granted: true` without ever showing what was being agreed to —
    # and the cookbook recommends it as the first step of measuring somebody
    # else's repository. A yes to terms nobody displayed is not a yes.
    if granted:
        print(consent_terms(language))
    path = record_consent(granted, getattr(args, "path", None), language=language)
    print(
        phrase(
            "prompt.consent.granted" if granted else "prompt.consent.revoked",
            language=language,
        ).format(path=path)
    )
    return OK if granted else DECLINED
