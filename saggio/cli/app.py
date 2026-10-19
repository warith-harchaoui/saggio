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
import os
import sys
from collections.abc import Callable, Sequence
from typing import Final

import os_helper as osh

from .. import __version__
from ..analyze.run import DEFAULT_BASELINE_SECONDS, DEFAULT_TIMEOUT_SECONDS
from ..catalog.registry import EXPIRING_WITHIN_DAYS, SECTION_OF_KIND
from ..diff import DEFAULT_DRIFT_THRESHOLD_PERCENT
from ..estimate.extrapolate import DEFAULT_PRECISION
from ..i18n import DEFAULT_LANGUAGE, language, say
from ..i18n import languages as LANGUAGES_FROM_FILES
from ..model.taxonomy import STATUS_ORDER
from ..report.office import DEFAULT_AUTHOR, OFFICE_FORMATS
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
    "scopes": commands.scopes,
    "next": commands.next_question,
    "render": commands.render,
    "dashboard": commands.dashboard,
    "audit": commands.audit_command,
    "measure": commands.measure,
    "diff": commands.difference,
    "machine": commands.machine,
    "power": commands.power,
    "consent": commands.consent,
    "catalog list": commands.catalog_list,
    "catalog add": commands.catalog_add,
    "catalog freshness": commands.catalog_freshness,
    "catalog refresh": commands.catalog_refresh,
    "catalog read-pcf": commands.catalog_read_pcf,
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
    parser.add_argument(
        "--language",
        default=DEFAULT_LANGUAGE,
        choices=list(LANGUAGES_FROM_FILES()),
        help=say("cli.help.language"),
    )
    verbs = parser.add_subparsers(dest="verb", metavar="verb")

    _add_init(verbs)
    _add_validate(verbs)
    _add_scopes(verbs)
    _add_next(verbs)
    _add_render(verbs)
    _add_dashboard(verbs)
    _add_audit(verbs)
    _add_measure(verbs)
    _add_diff(verbs)
    _add_machine(verbs)
    _add_power(verbs)
    _add_consent(verbs)
    _add_catalog(verbs)
    _add_language_everywhere(verbs)
    return parser


def _add_language_everywhere(verbs: argparse._SubParsersAction) -> None:
    """Give every verb the same ``--language``, from one definition.

    Walked rather than written out once per verb, for the reason this package
    keeps its surfaces in step with tests rather than with discipline: a verb
    added later gets the option without anybody having to remember, and there
    is one sentence of help to keep true instead of sixteen.

    It is per-verb rather than global so that ``saggio audit --language fr``
    reads the way the cookbook writes it, and so each verb's own ``--help``
    lists it.

    Parameters
    ----------
    verbs : argparse._SubParsersAction
        The sub-parser collection, after every verb has been attached.

    Examples
    --------
    >>> build_parser().parse_args(["validate", "m.yaml"]).language
    'en'
    >>> build_parser().parse_args(["render", "m.yaml", "--language", "fr"]).language
    'fr'
    >>> build_parser().parse_args(["--language", "fr", "render", "m.yaml"]).language
    'fr'
    """
    offered = list(LANGUAGES_FROM_FILES())
    for parser in verbs.choices.values():
        parser.add_argument(
            "--language",
            # SUPPRESS rather than a default: a default here is written into the
            # namespace before the verb is parsed, and would overwrite a global
            # `--language` with the authored one whenever the verb's own was
            # absent — which is the argparse trap this comment exists to mark.
            default=argparse.SUPPRESS,
            choices=offered,
            help=say("cli.help.language"),
        )
        for action in parser._actions:
            if isinstance(action, argparse._SubParsersAction):
                _add_language_everywhere(action)


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
    parser = verbs.add_parser("init", help=say("cli.help.init.summary"), epilog=described)
    parser.add_argument(
        "--template",
        choices=template_names(),
        default=DEFAULT_TEMPLATE,
        help=say("cli.help.init.template", default=DEFAULT_TEMPLATE),
    )
    parser.add_argument(
        "-o",
        "--output",
        default=None,
        help=say("cli.help.init.o"),
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
        help=say("cli.help.validate.summary"),
        epilog=f"Statuses, strongest to weakest: {statuses}.",
    )
    parser.add_argument("model", help=say("cli.help.validate.model"))
    parser.add_argument("--json", action="store_true", help=say("cli.help.validate.json"))


def _add_scopes(verbs: argparse._SubParsersAction) -> None:
    """Attach the ``scopes`` verb.

    Parameters
    ----------
    verbs : argparse._SubParsersAction
        The sub-parser collection.

    Examples
    --------
    >>> build_parser().parse_args(["scopes", "m.yaml"]).model
    'm.yaml'
    """
    parser = verbs.add_parser(
        "scopes",
        help=say("cli.help.scopes.summary"),
        epilog=(
            "The scope turns on who operates the machine, which the model already "
            "states. A market-based scope 2 figure is never produced here: it "
            "cannot be derived from a grid average, so what it would take is "
            "printed instead."
        ),
    )
    parser.add_argument("model", help=say("cli.help.scopes.model"))
    parser.add_argument(
        "--scenario",
        default=None,
        help=say("cli.help.scopes.scenario"),
    )
    parser.add_argument("--json", action="store_true", help=say("cli.help.scopes.json"))


def _add_next(verbs: argparse._SubParsersAction) -> None:
    """Register `next`, which ranks the open fields by what answering closes."""
    described = (
        "The fields are not independent: a measured runtime closes six figures "
        "through the derivation chain and a water usage effectiveness closes "
        "one. This reads `derived_from` backwards and says which to answer "
        "first, in the words the model already wrote for each field."
    )
    parser = verbs.add_parser(
        "next",
        help=say("cli.help.next.summary"),
        epilog=described,
    )
    parser.add_argument("model", help=say("cli.help.next.model"))
    parser.add_argument("--json", action="store_true", help=say("cli.help.next.json"))


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
    parser = verbs.add_parser("render", help=say("cli.help.render.summary"))
    parser.add_argument("model", help=say("cli.help.render.model"))
    parser.add_argument(
        "-f",
        "--format",
        choices=_RENDER_FORMATS,
        default="md",
        help=say("cli.help.render.f"),
    )
    parser.add_argument("-o", "--output", default=None, help=say("cli.help.render.o"))
    parser.add_argument(
        "--reference-doc",
        default=None,
        help=say("cli.help.render.reference_doc"),
    )
    parser.add_argument(
        "--author",
        default=DEFAULT_AUTHOR,
        help=(say("cli.help.render.author", default=DEFAULT_AUTHOR)),
    )
    parser.add_argument(
        "--generated",
        default=None,
        metavar="DATE",
        help=(say("cli.help.render.generated")),
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help=(say("cli.help.render.offline")),
    )


def _add_dashboard(verbs: argparse._SubParsersAction) -> None:
    """Attach the ``dashboard`` verb.

    Parameters
    ----------
    verbs : argparse._SubParsersAction
        The sub-parser collection.

    Examples
    --------
    >>> build_parser().parse_args(["dashboard", "a.yaml", "b.yaml"]).models
    ['a.yaml', 'b.yaml']
    """
    parser = verbs.add_parser(
        "dashboard",
        help=say("cli.help.dashboard.summary"),
        epilog=(
            "Each project's costs are per its own unit of work, so the page "
            "compares how well founded the models are, never the costs across rows."
        ),
    )
    parser.add_argument("models", nargs="+", help=say("cli.help.dashboard.models"))
    parser.add_argument("-o", "--output", default=None, help=say("cli.help.dashboard.o"))


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
        help=say("cli.help.audit.summary"),
        epilog=(
            "Without --run, nothing is executed and the runtime stays open. With "
            "--run, a capped slice of the repository is executed on your machine, "
            "with your permissions, after you have agreed to it once."
        ),
    )
    parser.add_argument("target", help=say("cli.help.audit.target"))
    parser.add_argument(
        "-o",
        "--output",
        default=None,
        help=say("cli.help.audit.o"),
    )
    parser.add_argument("--json", action="store_true", help=say("cli.help.audit.json"))
    parser.add_argument(
        "--run",
        action="store_true",
        help=say("cli.help.audit.run"),
    )
    parser.add_argument(
        "--no-llm",
        action="store_true",
        help=(say("cli.help.audit.no_llm")),
    )
    parser.add_argument(
        "--country",
        default=None,
        help=say("cli.help.audit.country"),
    )
    parser.add_argument("--provider", default=None, help=say("cli.help.audit.provider"))
    parser.add_argument("--instance", default=None, help=say("cli.help.audit.instance"))
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT_SECONDS,
        help=say("cli.help.audit.timeout", default=f"{DEFAULT_TIMEOUT_SECONDS:g}"),
    )
    parser.add_argument(
        "--baseline",
        type=float,
        default=DEFAULT_BASELINE_SECONDS,
        metavar="SECONDS",
        help=(say("cli.help.audit.baseline")),
    )
    parser.add_argument(
        "--scaling-steps",
        type=int,
        default=1,
        metavar="N",
        help=(say("cli.help.audit.scaling_steps")),
    )
    parser.add_argument(
        "--source-accelerator",
        default=None,
        help=(say("cli.help.audit.source_accelerator")),
    )
    parser.add_argument(
        "--target-accelerator", default=None, help=say("cli.help.audit.target_accelerator")
    )
    parser.add_argument(
        "--precision",
        default=DEFAULT_PRECISION,
        help=say("cli.help.audit.precision", default=DEFAULT_PRECISION),
    )
    parser.add_argument(
        "--fetch-prices",
        action="store_true",
        help=(say("cli.help.audit.fetch_prices")),
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
        help=say("cli.help.measure.summary"),
        epilog="Put the command after --, for example: measure -- python train.py --steps 100",
    )
    parser.add_argument("command", nargs=argparse.REMAINDER, help=say("cli.help.measure.command"))
    parser.add_argument("-C", "--directory", default=None, help=say("cli.help.measure.C"))
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT_SECONDS,
        help=say("cli.help.measure.timeout", default=f"{DEFAULT_TIMEOUT_SECONDS:g}"),
    )
    parser.add_argument(
        "--fraction",
        type=float,
        default=None,
        help=say("cli.help.measure.fraction"),
    )
    parser.add_argument(
        "--no-profile", action="store_true", help=say("cli.help.measure.no_profile")
    )
    parser.add_argument(
        "--baseline",
        type=float,
        default=DEFAULT_BASELINE_SECONDS,
        metavar="SECONDS",
        help=(say("cli.help.measure.baseline")),
    )
    parser.add_argument(
        "--repeat",
        type=int,
        default=1,
        metavar="N",
        help=(say("cli.help.measure.repeat")),
    )
    parser.add_argument(
        "--into",
        default=None,
        metavar="MODEL",
        help=(say("cli.help.measure.into")),
    )
    parser.add_argument(
        "--units",
        type=float,
        default=1.0,
        help=(say("cli.help.measure.units")),
    )
    parser.add_argument(
        "--scenario",
        default=None,
        help=say("cli.help.measure.scenario"),
    )
    parser.add_argument("--json", action="store_true", help=say("cli.help.measure.json"))


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
        help=say("cli.help.diff.summary"),
        epilog=(
            "A status that weakened, or a quantity that disappeared, fails the gate "
            "whatever the numbers did."
        ),
    )
    parser.add_argument("before", help=say("cli.help.diff.before"))
    parser.add_argument("after", help=say("cli.help.diff.after"))
    parser.add_argument(
        "--threshold",
        type=float,
        default=DEFAULT_DRIFT_THRESHOLD_PERCENT,
        help=say("cli.help.diff.threshold", default=f"{DEFAULT_DRIFT_THRESHOLD_PERCENT:g}"),
    )
    parser.add_argument("--json", action="store_true", help=say("cli.help.diff.json"))


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
    parser = verbs.add_parser("machine", help=say("cli.help.machine.summary"))
    parser.add_argument("--json", action="store_true", help=say("cli.help.machine.json"))


def _add_power(verbs: argparse._SubParsersAction) -> None:
    """Attach the ``power`` verb.

    Parameters
    ----------
    verbs : argparse._SubParsersAction
        The sub-parser collection.

    Examples
    --------
    >>> build_parser().parse_args(["power"]).verb
    'power'
    >>> build_parser().parse_args(["power", "--seconds", "2"]).seconds
    2.0
    """
    parser = verbs.add_parser(
        "power",
        help=say("cli.help.power.summary"),
        epilog=(
            "Nothing here is run as another user. Where a counter needs "
            "administrator rights, the command that would open it is printed "
            "and not executed, together with the reason it is shut."
        ),
    )
    parser.add_argument("--json", action="store_true", help=say("cli.help.power.json"))
    parser.add_argument(
        "--seconds",
        type=float,
        default=0.0,
        help=(say("cli.help.power.seconds")),
    )


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
        help=say("cli.help.consent.summary"),
        epilog=(
            "Running a repository under study executes third-party code on this "
            "machine, with your permissions. There is no sandbox."
        ),
    )
    parser.add_argument("decision", choices=("grant", "revoke"))
    parser.add_argument(
        "--path",
        default=None,
        help=say("cli.help.consent.path"),
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
        help=say("cli.help.catalog.summary"),
    )
    sub = parser.add_subparsers(dest="catalog_verb", metavar="action")

    listing = sub.add_parser("list", help=say("cli.help.list.summary"))
    listing.add_argument("kind", choices=kinds)
    listing.add_argument("--json", action="store_true", help=say("cli.help.catalog.list.json"))

    adding = sub.add_parser(
        "add",
        help=say("cli.help.add.summary"),
        epilog=(
            "A row cannot be added without a source and a date. That is the rule "
            "that keeps the catalogues worth trusting."
        ),
    )
    adding.add_argument("kind", choices=kinds)
    adding.add_argument("key", help=say("cli.help.catalog.add.key"))
    adding.add_argument("--source-url", required=True, help=say("cli.help.catalog.add.source_url"))
    adding.add_argument(
        "--retrieved-date", required=True, help=say("cli.help.catalog.add.retrieved_date")
    )
    adding.add_argument(
        "--field",
        action="append",
        default=[],
        metavar="NAME=VALUE",
        help=say("cli.help.catalog.add.field"),
    )
    pcf = sub.add_parser(
        "read-pcf",
        help=say("cli.help.read_pcf.summary"),
        epilog=(
            "It reads, shows its working, and stops. Nothing is written: a "
            "catalogue row is a claim somebody makes, and the person making it "
            "is the person who can defend it."
        ),
    )
    pcf.add_argument(
        "document",
        help=say("cli.help.catalog.read-pcf.document"),
    )
    pcf.add_argument("--json", action="store_true", help=say("cli.help.catalog.read-pcf.json"))

    refresh = sub.add_parser(
        "refresh",
        help=say("cli.help.refresh.summary"),
    )
    refresh.add_argument("catalog", help=say("cli.help.catalog.refresh.catalog"))
    refresh.add_argument(
        "--api-key",
        default=None,
        help=(say("cli.help.catalog.refresh.api_key")),
    )
    refresh.add_argument(
        "--year",
        type=int,
        default=None,
        help=(say("cli.help.catalog.refresh.year")),
    )
    refresh.add_argument(
        "--column",
        choices=("carbon", "price", "timezones", "embodied", "both", "all"),
        default="carbon",
        help=(say("cli.help.catalog.refresh.column")),
    )
    refresh.add_argument(
        "--write",
        default=None,
        metavar="PATH",
        help=say("cli.help.catalog.refresh.write"),
    )
    refresh.add_argument("--json", action="store_true", help=say("cli.help.catalog.refresh.json"))

    freshness = sub.add_parser(
        "freshness",
        help=say("cli.help.freshness.summary"),
    )
    freshness.add_argument(
        "--within",
        type=int,
        default=EXPIRING_WITHIN_DAYS,
        metavar="DAYS",
        help=(say("cli.help.catalog.freshness.within", default=EXPIRING_WITHIN_DAYS)),
    )
    freshness.add_argument(
        "--json", action="store_true", help=say("cli.help.catalog.freshness.json")
    )


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


#: Where a deployment states the language once, so a container does not repeat
#: it on every verb.
LANGUAGE_ENVIRONMENT_VARIABLE: Final[str] = "SAGGIO_LANGUAGE"


def requested_language(argv: Sequence[str] | None = None) -> str | None:
    """Find the language before a parser exists, because help is built with it.

    ``--help`` is rendered from strings the parser already holds, and the parser
    is built before anything is parsed. So the language has to be read off the
    arguments by hand, once, or every ``--help`` would come out in the authored
    language however the caller asked.

    Parameters
    ----------
    argv : sequence of str or None, optional
        The arguments, without the program name. Taken from the process when
        omitted, which is what :func:`main` does.

    Returns
    -------
    str or None
        What was asked for, or what the environment says, or ``None``.

    Examples
    --------
    >>> requested_language(["audit", ".", "--language", "fr"])
    'fr'
    >>> requested_language(["audit", ".", "--language=fr"])
    'fr'
    >>> requested_language(["audit", "."]) is None
    True
    """
    arguments = list(sys.argv[1:] if argv is None else argv)
    for index, argument in enumerate(arguments):
        if argument == "--language" and index + 1 < len(arguments):
            return arguments[index + 1]
        if argument.startswith("--language="):
            return argument.split("=", 1)[1]
    return os.environ.get(LANGUAGE_ENVIRONMENT_VARIABLE, "").strip() or None


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
    # Before the parser, because the parser's help text is built from the
    # catalogue and a `--help` in the wrong language would be the one piece of
    # this surface nobody could ask to change.
    with language(requested_language(argv)):
        return _dispatch(build_parser(), argv)


def _dispatch(parser: argparse.ArgumentParser, argv: Sequence[str] | None) -> int:
    """Parse the arguments and run the verb they name.

    Parameters
    ----------
    parser : argparse.ArgumentParser
        The parser, already built in the caller's language.
    argv : sequence of str or None
        The arguments.

    Returns
    -------
    int
        The exit code.

    Examples
    --------
    >>> import contextlib, io
    >>> with contextlib.redirect_stdout(io.StringIO()):
    ...     code = _dispatch(build_parser(), ["machine", "--json"])
    >>> code
    0
    """
    args = parser.parse_args(argv)
    _configure_logging(args)

    if args.verb is None:
        parser.print_help()
        return USAGE
    if args.verb == "catalog":
        if getattr(args, "catalog_verb", None) is None:
            # Not parse_args([verb, "--help"]): argparse's help action raises
            # SystemExit(0), which made a usage error read as success to any
            # script checking the exit code.
            osh.error(
                "catalog needs an action: list, add, freshness, or refresh. "
                "Try `saggio catalog -h`."
            )
            return USAGE
        key = f"catalog {args.catalog_verb}"
    else:
        key = args.verb

    handler = _HANDLERS.get(key)
    if handler is None:
        parser.print_help()
        return USAGE
    # The whole verb runs inside the language it was given, so a sentence
    # composed four modules deep comes out in the reader's language without that
    # tag being threaded through every signature between here and there.
    with language(getattr(args, "language", None)):
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
