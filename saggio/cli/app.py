"""
The command line: one parser, one dispatch table.

Module summary
--------------
This module builds the argument parser and routes each verb to its handler in
:mod:`saggio.cli.commands`. It holds no business logic at all,
which is the whole point: the command line is one way of reaching the library, and
anything it could do that the library cannot would be something a library user was
locked out of.

Usage example
-------------
>>> from saggio.cli.app import build_parser
>>> build_parser().parse_args(["validate", "cost.yaml"]).verb
'validate'

Author
------
Warith Harchaoui
"""

from __future__ import annotations

import argparse
from collections.abc import Callable, Sequence
from typing import Final

import os_helper as osh

from .. import __version__
from ..analyze.run import DEFAULT_TIMEOUT_SECONDS
from ..catalog.registry import SECTION_OF_KIND
from ..diff import DEFAULT_DRIFT_THRESHOLD_PERCENT
from ..estimate.extrapolate import DEFAULT_PRECISION
from ..model.taxonomy import STATUS_ORDER
from ..report.office import OFFICE_FORMATS
from ..templates import DEFAULT_TEMPLATE, TEMPLATES, template_names
from . import commands
from .exit_codes import MEANINGS, USAGE

#: The console script's name, used in help text and in the messages commands print.
PROGRAM: Final[str] = "saggio"

#: The formats ``render`` can produce.
_RENDER_FORMATS: Final[tuple[str, ...]] = ("md", "html", *sorted(OFFICE_FORMATS))

#: Verb name to handler. Adding a verb means adding its parser and one line here.
_HANDLERS: Final[dict[str, Callable[[argparse.Namespace], int]]] = {
    "init": commands.initialise,
    "validate": commands.check,
    "render": commands.render,
    "audit": commands.audit_command,
    "measure": commands.measure,
    "diff": commands.difference,
    "machine": commands.machine,
    "consent": commands.consent,
    "catalog list": commands.catalog_list,
    "catalog add": commands.catalog_add,
    "catalog freshness": commands.catalog_freshness,
}

_EPILOG: Final[str] = "Exit codes: " + "; ".join(
    f"{code} {meaning.lower().rstrip('.')}" for code, meaning in MEANINGS.items()
)


def build_parser() -> argparse.ArgumentParser:
    """Build the full argument parser.

    Returns
    -------
    argparse.ArgumentParser
        The parser, with every verb attached.

    Examples
    --------
    >>> build_parser().prog
    'saggio'
    """
    parser = argparse.ArgumentParser(
        prog=PROGRAM,
        description=(
            "Measure what it costs to run code: money, time, energy, carbon, water, "
            "and any dimension you register, per unit of work, with every number "
            "saying how far it can be trusted."
        ),
        epilog=_EPILOG,
    )
    parser.add_argument("--version", action="version", version=f"{PROGRAM} {__version__}")
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Log more on standard error. Repeat for debug output.",
    )
    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Say nothing on standard error but errors themselves.",
    )
    verbs = parser.add_subparsers(dest="verb", metavar="verb")

    _add_init(verbs)
    _add_validate(verbs)
    _add_render(verbs)
    _add_audit(verbs)
    _add_measure(verbs)
    _add_diff(verbs)
    _add_machine(verbs)
    _add_consent(verbs)
    _add_catalog(verbs)
    return parser


def _add_init(verbs: argparse._SubParsersAction) -> None:
    """Attach the ``init`` verb.

    Parameters
    ----------
    verbs : argparse._SubParsersAction
        The sub-parser collection.

    Examples
    --------
    >>> "init" in build_parser().parse_args(["init"]).verb
    True
    """
    described = "; ".join(f"{name}: {TEMPLATES[name]}" for name in template_names())
    parser = verbs.add_parser("init", help="Write a starter cost model.", epilog=described)
    parser.add_argument(
        "--template",
        choices=template_names(),
        default=DEFAULT_TEMPLATE,
        help=f"Which starter to write. Default {DEFAULT_TEMPLATE}.",
    )
    parser.add_argument(
        "-o",
        "--output",
        default=None,
        help="Where to write it. Standard output when omitted.",
    )


def _add_validate(verbs: argparse._SubParsersAction) -> None:
    """Attach the ``validate`` verb.

    Parameters
    ----------
    verbs : argparse._SubParsersAction
        The sub-parser collection.

    Examples
    --------
    >>> build_parser().parse_args(["validate", "m.yaml"]).model
    'm.yaml'
    """
    statuses = ", ".join(STATUS_ORDER)
    parser = verbs.add_parser(
        "validate",
        help="Check a model against the schema and the honesty rules.",
        epilog=f"Statuses, strongest to weakest: {statuses}.",
    )
    parser.add_argument("model", help="The cost model to check.")
    parser.add_argument("--json", action="store_true", help="Print the verdict as JSON.")


def _add_render(verbs: argparse._SubParsersAction) -> None:
    """Attach the ``render`` verb.

    Parameters
    ----------
    verbs : argparse._SubParsersAction
        The sub-parser collection.

    Examples
    --------
    >>> build_parser().parse_args(["render", "m.yaml"]).format
    'md'
    """
    parser = verbs.add_parser("render", help="Turn a model into a report.")
    parser.add_argument("model", help="The cost model to render.")
    parser.add_argument(
        "-f",
        "--format",
        choices=_RENDER_FORMATS,
        default="md",
        help="Markdown for a pull request, HTML for anyone else, docx or pdf for a document.",
    )
    parser.add_argument(
        "-o", "--output", default=None, help="Where to write it. Standard output when omitted."
    )
    parser.add_argument(
        "--reference-doc",
        default=None,
        help="A .docx whose styles a Word or PDF output should follow.",
    )


def _add_audit(verbs: argparse._SubParsersAction) -> None:
    """Attach the ``audit`` verb.

    Parameters
    ----------
    verbs : argparse._SubParsersAction
        The sub-parser collection.

    Examples
    --------
    >>> build_parser().parse_args(["audit", "."]).run
    False
    """
    parser = verbs.add_parser(
        "audit",
        help="Build a cost model for a repository.",
        epilog=(
            "Without --run, nothing is executed and the runtime stays open. With "
            "--run, a capped slice of the repository is executed on your machine, "
            "with your permissions, after you have agreed to it once."
        ),
    )
    parser.add_argument("target", help="A directory, or a git URL to clone and audit.")
    parser.add_argument(
        "-o",
        "--output",
        default=None,
        help="Where to write the model. Standard output when omitted.",
    )
    parser.add_argument("--json", action="store_true", help="Print the model and verdict as JSON.")
    parser.add_argument(
        "--run",
        action="store_true",
        help="Execute a capped slice to measure it. Asks for consent once.",
    )
    parser.add_argument(
        "--no-llm",
        action="store_true",
        help=(
            "Do not ask a local model to classify the workload. Numbers never come from it anyway."
        ),
    )
    parser.add_argument(
        "--country",
        default=None,
        help="ISO 3166-1 alpha-2 code where the code runs, for example FR. Never guessed.",
    )
    parser.add_argument(
        "--provider", default=None, help="Provider key, for example gcp or on-prem."
    )
    parser.add_argument(
        "--instance", default=None, help="Machine-shape key, for example node-1x-h100."
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT_SECONDS,
        help=f"Seconds a slice may run. Default {DEFAULT_TIMEOUT_SECONDS:g}.",
    )
    parser.add_argument(
        "--source-accelerator",
        default=None,
        help=(
            "Accelerator the measurement represents, when it is not this machine's. "
            "This is what lets a laptop project onto a datacenter GPU."
        ),
    )
    parser.add_argument(
        "--target-accelerator", default=None, help="Accelerator to project the runtime onto."
    )
    parser.add_argument(
        "--precision",
        default=DEFAULT_PRECISION,
        help=f"Numeric precision the workload runs in. Default {DEFAULT_PRECISION}.",
    )


def _add_measure(verbs: argparse._SubParsersAction) -> None:
    """Attach the ``measure`` verb.

    Parameters
    ----------
    verbs : argparse._SubParsersAction
        The sub-parser collection.

    Examples
    --------
    >>> build_parser().parse_args(["measure", "--", "echo", "hi"]).command
    ['--', 'echo', 'hi']
    """
    parser = verbs.add_parser(
        "measure",
        help="Run a command and report what it cost to run.",
        epilog="Put the command after --, for example: measure -- python train.py --steps 100",
    )
    parser.add_argument("command", nargs=argparse.REMAINDER, help="The command to run.")
    parser.add_argument("-C", "--directory", default=None, help="Where to run it.")
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT_SECONDS,
        help=f"Seconds before it is stopped. Default {DEFAULT_TIMEOUT_SECONDS:g}.",
    )
    parser.add_argument(
        "--fraction",
        type=float,
        default=None,
        help="The share of a whole run this command covers, if you know it.",
    )
    parser.add_argument(
        "--no-profile", action="store_true", help="Skip the function-level profile."
    )
    parser.add_argument("--json", action="store_true", help="Print the measurement as JSON.")


def _add_diff(verbs: argparse._SubParsersAction) -> None:
    """Attach the ``diff`` verb.

    Parameters
    ----------
    verbs : argparse._SubParsersAction
        The sub-parser collection.

    Examples
    --------
    >>> build_parser().parse_args(["diff", "a.yaml", "b.yaml"]).threshold
    10.0
    """
    parser = verbs.add_parser(
        "diff",
        help="Compare two models and fail when a cost has drifted.",
        epilog=(
            "A status that weakened, or a quantity that disappeared, fails the gate "
            "whatever the numbers did."
        ),
    )
    parser.add_argument("before", help="The earlier model.")
    parser.add_argument("after", help="The later model.")
    parser.add_argument(
        "--threshold",
        type=float,
        default=DEFAULT_DRIFT_THRESHOLD_PERCENT,
        help=f"Percentage a cost may worsen by. Default {DEFAULT_DRIFT_THRESHOLD_PERCENT:g}.",
    )
    parser.add_argument("--json", action="store_true", help="Print the comparison as JSON.")


def _add_machine(verbs: argparse._SubParsersAction) -> None:
    """Attach the ``machine`` verb.

    Parameters
    ----------
    verbs : argparse._SubParsersAction
        The sub-parser collection.

    Examples
    --------
    >>> build_parser().parse_args(["machine"]).verb
    'machine'
    """
    parser = verbs.add_parser(
        "machine", help="Show what this machine is and whether the catalogue knows it."
    )
    parser.add_argument("--json", action="store_true", help="Print it as JSON.")


def _add_consent(verbs: argparse._SubParsersAction) -> None:
    """Attach the ``consent`` verb.

    Parameters
    ----------
    verbs : argparse._SubParsersAction
        The sub-parser collection.

    Examples
    --------
    >>> build_parser().parse_args(["consent", "revoke"]).decision
    'revoke'
    """
    parser = verbs.add_parser(
        "consent",
        help="Grant or revoke permission to run downloaded code.",
        epilog=(
            "Running a repository under study executes third-party code on this "
            "machine, with your permissions. There is no sandbox."
        ),
    )
    parser.add_argument("decision", choices=("grant", "revoke"))
    parser.add_argument(
        "--path",
        default=None,
        help="Record the decision in this file instead of the per-user one.",
    )


def _add_catalog(verbs: argparse._SubParsersAction) -> None:
    """Attach the ``catalog`` verb and its sub-verbs.

    Parameters
    ----------
    verbs : argparse._SubParsersAction
        The sub-parser collection.

    Examples
    --------
    >>> build_parser().parse_args(["catalog", "list", "gpu"]).kind
    'gpu'
    """
    kinds = sorted(SECTION_OF_KIND)
    parser = verbs.add_parser(
        "catalog",
        help="Read and extend the catalogues of hardware, grids, providers, and services.",
    )
    sub = parser.add_subparsers(dest="catalog_verb", metavar="action")

    listing = sub.add_parser("list", help="Print a catalogue's rows.")
    listing.add_argument("kind", choices=kinds)
    listing.add_argument("--json", action="store_true", help="Print them as JSON.")

    adding = sub.add_parser(
        "add",
        help="Add a row locally, provenance required.",
        epilog=(
            "A row cannot be added without a source and a date. That is the rule "
            "that keeps the catalogues worth trusting."
        ),
    )
    adding.add_argument("kind", choices=kinds)
    adding.add_argument("key", help="The row key, for example H200 or FR.")
    adding.add_argument("--source-url", required=True, help="Where the numbers came from.")
    adding.add_argument("--retrieved-date", required=True, help="YYYY-MM-DD you read it.")
    adding.add_argument(
        "--field",
        action="append",
        default=[],
        metavar="NAME=VALUE",
        help="A field of the row, repeatable, for example --field tdp_w=700.",
    )

    freshness = sub.add_parser(
        "freshness",
        help="List the rows nobody has checked lately. Exits 1 when any are stale.",
    )
    freshness.add_argument("--json", action="store_true", help="Print them as JSON.")


def _configure_logging(args: argparse.Namespace) -> None:
    """Set the logger's level from the verbosity flags.

    Parameters
    ----------
    args : argparse.Namespace
        Parsed arguments, with ``verbose`` and ``quiet``.

    Examples
    --------
    >>> _configure_logging(argparse.Namespace(verbose=0, quiet=True))
    >>> osh.verbosity()
    -1
    >>> _configure_logging(argparse.Namespace(verbose=0, quiet=False))
    >>> osh.verbosity()
    0
    """
    # os-helper's loggers need a handler before anything they are told reaches a
    # terminal, and the handler writes to standard error, which keeps every human
    # message out of a pipe that is reading the command's real output.
    osh.init_logging(stdout=False)
    # Quiet by default. The library logs a great deal that is useful while
    # debugging and noise the rest of the time, and anything the user genuinely
    # has to read is printed by the command itself rather than logged.
    if args.quiet:
        osh.verbosity(-1)
    elif args.verbose >= 2:
        osh.verbosity(2)
    elif args.verbose == 1:
        osh.verbosity(1)
    else:
        osh.verbosity(0)


def main(argv: Sequence[str] | None = None) -> int:
    """Run the command line.

    Parameters
    ----------
    argv : sequence of str or None, optional
        Arguments, without the program name. Taken from the process when omitted.

    Returns
    -------
    int
        The exit code, which the console-script wrapper passes to the shell.

    Examples
    --------
    >>> import contextlib, io
    >>> with contextlib.redirect_stdout(io.StringIO()):
    ...     without_a_verb = main([])
    ...     with_a_verb = main(["machine", "--json"])
    >>> without_a_verb, with_a_verb
    (2, 0)
    """
    parser = build_parser()
    args = parser.parse_args(argv)
    _configure_logging(args)

    if args.verb is None:
        parser.print_help()
        return USAGE
    if args.verb == "catalog":
        if getattr(args, "catalog_verb", None) is None:
            parser.parse_args([args.verb, "--help"])
            return USAGE
        key = f"catalog {args.catalog_verb}"
    else:
        key = args.verb

    handler = _HANDLERS.get(key)
    if handler is None:
        parser.print_help()
        return USAGE
    return handler(args)


def run() -> None:
    """Entry point for the console script.

    Runs :func:`main` and exits with its code, so the shell and any surrounding
    script see the verdict.

    Examples
    --------
    >>> callable(run)
    True
    """
    raise SystemExit(main())
