"""
The command line: one group of verbs, one dispatch table.

Module summary
--------------
This module declares the command line and routes each verb to its handler in
:mod:`saggio.cli.commands`. It holds no business logic at all,
which is the whole point: the command line is one way of reaching the library, and
anything it could do that the library cannot would be something a library user was
locked out of.

Built on click, and only on click. It was argparse, and the move was a decision
rather than a discovery, but three things the old version worked around stopped
being work:

* **A mistyped verb suggests the right one.** Click does this itself, and with
  thirteen verbs argparse's "invalid choice" was a true answer that helped
  nobody. Nothing here implements it -- an override that did was written, found
  to be restating click, and deleted.
* **The verbs are public.** A contract test used to reach into
  ``parser._subparsers._group_actions`` to find out what this surface offers,
  with a comment apologising for it; click publishes :attr:`click.Group.commands`.
* **Completion works**, because click generates it. Nothing here had it before.
* **Positional arguments explain themselves**, which argparse did and click
  learned in 8.5. A shim that carried the help was written here for 8.4 and
  deleted the day continuous integration resolved 8.5 and showed it restating
  the library -- the second override in this move to do that, which is why the
  floor is 8.5 rather than 8.1.

What did not change, and was the point of keeping the shapes identical: every
verb, every flag, every default, and every exit code. The handlers in
:mod:`saggio.cli.commands` were not touched -- they take an object with
attributes, and :func:`_verb` builds one from what click parsed, so the two
surfaces could be swapped without 1,689 lines moving underneath.

Usage example
-------------
>>> from saggio.cli.app import build_cli
>>> sorted(build_cli().commands)[:3]
['audit', 'catalog', 'consent']

Author
------
Warith Harchaoui
"""

from __future__ import annotations

import os
import re
import sys
import warnings
from collections.abc import Callable, Sequence
from types import SimpleNamespace
from typing import Any, Final

import click
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
from .exit_codes import MEANINGS, OK, USAGE

#: The console script's name, used in help text and in the messages commands print.
PROGRAM: Final[str] = "saggio"

#: The formats ``render`` can produce.
_RENDER_FORMATS: Final[tuple[str, ...]] = ("md", "html", *sorted(OFFICE_FORMATS))

#: Verb name to handler. Adding a verb means declaring its command and one line here.
_HANDLERS: Final[dict[str, Callable[[SimpleNamespace], int]]] = {
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

#: Where a deployment states the language once, so a container does not repeat
#: it on every verb.
LANGUAGE_ENVIRONMENT_VARIABLE: Final[str] = "SAGGIO_LANGUAGE"

#: What a shell sets when it is asking what could come next rather than asking
#: for work. The name is click's convention, derived from the program's, and it
#: is written here because :func:`main` has to notice it before anything else.
COMPLETION_VARIABLE: Final[str] = f"_{PROGRAM.upper()}_COMPLETE"


def _language_option(command: Callable[..., Any]) -> Callable[..., Any]:
    """Give a verb the same ``--language``, from one definition.

    Applied as a decorator rather than written out per verb, for the reason this
    package keeps its surfaces in step with tests rather than with discipline:
    there is one sentence of help to keep true instead of seventeen, and a gate
    refuses a verb that does not carry it.

    It is per-verb *as well as* on the group so that ``saggio audit --language
    fr`` reads the way the cookbook writes it and each verb's own ``--help``
    lists it. The verb's own value wins when both are given; the default is
    ``None`` rather than a language, because a default here would be
    indistinguishable from a caller asking for English and would overwrite the
    group's. Under argparse the same problem was solved with
    ``default=SUPPRESS``, and a contract test asserted that constant --
    a test about a library's internals rather than about the behaviour. The
    behaviour is what is pinned now.
    """
    return click.option(
        "--language",
        type=click.Choice(list(LANGUAGES_FROM_FILES())),
        default=None,
        help=say("cli.help.language"),
    )(command)


def _verb(name: str) -> Callable[..., int]:
    """Return the callback for a verb: gather what click parsed, hand it over.

    The handlers predate this module's move to click and read their arguments
    off an object's attributes. Rather than rewrite seventeen of them, click's
    keyword arguments are collected into one, which is the whole of the
    adaptation. Tuples become lists because that is what the handlers were
    written against -- click gives a tuple for a repeatable option where
    argparse gave a list, and a handler doing ``args.field.append`` would have
    found out at runtime.

    Parameters
    ----------
    name : str
        The key in :data:`_HANDLERS`.

    Returns
    -------
    callable
        A click callback returning the handler's exit code.
    """

    def callback(**given: Any) -> int:
        context = click.get_current_context()
        root = context.find_root()
        chosen = given.pop("language", None) or root.params.get("language") or DEFAULT_LANGUAGE
        arguments = SimpleNamespace(
            language=chosen,
            verbose=root.params.get("verbose") or 0,
            quiet=bool(root.params.get("quiet")),
            **{
                key: list(value) if isinstance(value, tuple) else value
                for key, value in given.items()
            },
        )
        with language(chosen):
            return _HANDLERS[name](arguments)

    return callback


class VerbGroup(click.Group):
    """The root group, listing its verbs in the order they were declared.

    One departure from click's defaults, and it is the only one needed. Click
    sorts commands alphabetically, which would put ``audit`` first and ``init``
    sixth; these are listed in the order somebody uses them -- ``init``,
    ``validate``, … ``catalog`` -- which is the order the cookbooks teach and
    the order argparse happened to give.

    There was a second departure here and it has been deleted, which is worth
    recording: a ``resolve_command`` that answered a mistyped verb with the
    nearest one. Click 8.4 already does that -- ``No such command 'vlaidate'.
    Did you mean 'validate'?`` -- so the override was twenty lines restating a
    feature, and the claim that this package had added the suggestion was
    false. It is a thing the move to click bought, not a thing written here.

    Examples
    --------
    >>> group = build_cli()
    >>> list(group.commands)[:2]
    ['init', 'validate']
    """

    def list_commands(self, ctx: click.Context) -> list[str]:
        """Return the verbs unsorted, which is to say in the order declared."""
        return list(self.commands)


def build_cli() -> VerbGroup:
    """Build the command group, in the language in force right now.

    **Built per call, and that is the whole reason this is a function.**
    Every help string comes from the message catalogue through
    :func:`~saggio.i18n.say`, and a decorator evaluates its arguments when
    the module is imported -- so declaring these at module level froze all
    of them in the language the package was written in, and
    ``saggio --language fr validate --help`` answered in English. The
    argparse version did not have the bug because it built the parser
    inside the language context on every run, and this keeps that.

    Measured, because a group rebuilt on every invocation sounds expensive
    and is not: see the startup figure in the changelog entry for this
    move. Declaring a command is attaching decorators to a function, which
    is cheap; the imports it would otherwise repeat have already happened.

    Returns
    -------
    VerbGroup
        The root group, with every verb attached.

    Examples
    --------
    >>> build_cli().name
    'saggio'
    >>> "catalog" in build_cli().commands
    True
    >>> list(build_cli().commands)[:2]
    ['init', 'validate']
    >>> from ..i18n import language as in_language
    >>> with in_language("fr"):
    ...     build_cli().commands["validate"].help.startswith("Confronter")
    True
    """

    @click.group(
        cls=VerbGroup,
        name=PROGRAM,
        help=(
            "Measure what it costs to run code: money, time, energy, carbon, water, "
            "and any dimension you register, per unit of work, with every number "
            "saying how far it can be trusted."
        ),
        epilog=_EPILOG,
        # Click prints help and exits 0 for a bare invocation; this surface answers
        # 2, because being asked for nothing is being asked for something it cannot
        # do. `main` prints the help itself for that case.
        invoke_without_command=True,
        no_args_is_help=False,
        context_settings={"help_option_names": ["-h", "--help"]},
    )
    @click.version_option(
        version=__version__,
        prog_name=PROGRAM,
        # argparse printed "saggio 1.5.0" and `python -m saggio --version` is quoted
        # with that answer beside it in the module's own docstring, which a contract
        # test checks. Click's default would have said "saggio, version 1.5.0".
        message="%(prog)s %(version)s",
    )
    @click.option(
        "-v",
        "--verbose",
        count=True,
        help="Log more on standard error. Repeat for debug output.",
    )
    @click.option(
        "-q",
        "--quiet",
        is_flag=True,
        help="Say nothing on standard error but errors themselves.",
    )
    @click.option(
        "--language",
        type=click.Choice(list(LANGUAGES_FROM_FILES())),
        default=DEFAULT_LANGUAGE,
        help=say("cli.help.language"),
    )
    @click.pass_context
    def cli(context: click.Context, verbose: int, quiet: bool, language: str) -> None:
        """Route the verbs. The body runs before whichever one was named."""
        _configure_logging(SimpleNamespace(verbose=verbose, quiet=quiet))

    # --- The verbs ----------------------------------------------------------------

    @cli.command(
        name="init",
        help=say("cli.help.init.summary"),
        epilog="; ".join(f"{name}: {TEMPLATES[name]}" for name in template_names()),
    )
    @click.option(
        "--template",
        type=click.Choice(template_names()),
        default=DEFAULT_TEMPLATE,
        show_default=False,
        help=say("cli.help.init.template", default=DEFAULT_TEMPLATE),
    )
    @click.option("-o", "--output", default=None, help=say("cli.help.init.o"))
    @_language_option
    def _init_command(**given: Any) -> int:
        return _verb("init")(**given)

    @cli.command(
        name="validate",
        help=say("cli.help.validate.summary"),
        epilog=f"Statuses, strongest to weakest: {', '.join(STATUS_ORDER)}.",
    )
    @click.argument("model", help=say("cli.help.validate.model"))
    @click.option("--json", "json", is_flag=True, help=say("cli.help.validate.json"))
    @_language_option
    def _validate_command(**given: Any) -> int:
        return _verb("validate")(**given)

    @cli.command(
        name="scopes",
        help=say("cli.help.scopes.summary"),
        epilog=(
            "The scope turns on who operates the machine, which the model already "
            "states. A market-based scope 2 figure is never produced here: it "
            "cannot be derived from a grid average, so what it would take is "
            "printed instead."
        ),
    )
    @click.argument("model", help=say("cli.help.scopes.model"))
    @click.option("--scenario", default=None, help=say("cli.help.scopes.scenario"))
    @click.option("--json", "json", is_flag=True, help=say("cli.help.scopes.json"))
    @_language_option
    def _scopes_command(**given: Any) -> int:
        return _verb("scopes")(**given)

    @cli.command(
        name="next",
        help=say("cli.help.next.summary"),
        epilog=(
            "The fields are not independent: a measured runtime closes six figures "
            "through the derivation chain and a water usage effectiveness closes "
            "one. This reads `derived_from` backwards and says which to answer "
            "first, in the words the model already wrote for each field."
        ),
    )
    @click.argument("model", help=say("cli.help.next.model"))
    @click.option("--json", "json", is_flag=True, help=say("cli.help.next.json"))
    @_language_option
    def _next_command(**given: Any) -> int:
        return _verb("next")(**given)

    @cli.command(name="render", help=say("cli.help.render.summary"))
    @click.argument("model", help=say("cli.help.render.model"))
    @click.option(
        "-f",
        "--format",
        "format",
        type=click.Choice(_RENDER_FORMATS),
        default="md",
        show_default=False,
        help=say("cli.help.render.f"),
    )
    @click.option("-o", "--output", default=None, help=say("cli.help.render.o"))
    @click.option("--reference-doc", default=None, help=say("cli.help.render.reference_doc"))
    @click.option(
        "--author",
        default=DEFAULT_AUTHOR,
        show_default=False,
        help=say("cli.help.render.author", default=DEFAULT_AUTHOR),
    )
    @click.option(
        "--generated", default=None, metavar="DATE", help=say("cli.help.render.generated")
    )
    @click.option("--offline", is_flag=True, help=say("cli.help.render.offline"))
    @_language_option
    def _render_command(**given: Any) -> int:
        return _verb("render")(**given)

    @cli.command(
        name="dashboard",
        help=say("cli.help.dashboard.summary"),
        epilog=(
            "Each project's costs are per its own unit of work, so the page "
            "compares how well founded the models are, never the costs across rows."
        ),
    )
    @click.argument("models", nargs=-1, required=True, help=say("cli.help.dashboard.models"))
    @click.option("-o", "--output", default=None, help=say("cli.help.dashboard.o"))
    @_language_option
    def _dashboard_command(**given: Any) -> int:
        return _verb("dashboard")(**given)

    @cli.command(
        name="audit",
        help=say("cli.help.audit.summary"),
        epilog=(
            "Without --run, nothing is executed and the runtime stays open. With "
            "--run, a capped slice of the repository is executed on your machine, "
            "with your permissions, after you have agreed to it once."
        ),
    )
    @click.argument("target", help=say("cli.help.audit.target"))
    @click.option("-o", "--output", default=None, help=say("cli.help.audit.o"))
    @click.option("--json", "json", is_flag=True, help=say("cli.help.audit.json"))
    @click.option("--run", is_flag=True, help=say("cli.help.audit.run"))
    @click.option("--no-llm", is_flag=True, help=say("cli.help.audit.no_llm"))
    @click.option("--country", default=None, help=say("cli.help.audit.country"))
    @click.option("--provider", default=None, help=say("cli.help.audit.provider"))
    @click.option("--instance", default=None, help=say("cli.help.audit.instance"))
    @click.option(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT_SECONDS,
        show_default=False,
        help=say("cli.help.audit.timeout", default=f"{DEFAULT_TIMEOUT_SECONDS:g}"),
    )
    @click.option(
        "--baseline",
        type=float,
        default=DEFAULT_BASELINE_SECONDS,
        metavar="SECONDS",
        show_default=False,
        help=say("cli.help.audit.baseline"),
    )
    @click.option(
        "--scaling-steps",
        type=int,
        default=1,
        metavar="N",
        show_default=False,
        help=say("cli.help.audit.scaling_steps"),
    )
    @click.option(
        "--source-accelerator", default=None, help=say("cli.help.audit.source_accelerator")
    )
    @click.option(
        "--target-accelerator", default=None, help=say("cli.help.audit.target_accelerator")
    )
    @click.option(
        "--precision",
        default=DEFAULT_PRECISION,
        show_default=False,
        help=say("cli.help.audit.precision", default=DEFAULT_PRECISION),
    )
    @click.option("--fetch-prices", is_flag=True, help=say("cli.help.audit.fetch_prices"))
    @_language_option
    def _audit_command(**given: Any) -> int:
        return _verb("audit")(**given)

    @cli.command(
        name="measure",
        help=say("cli.help.measure.summary"),
        epilog="Put the command after --, for example: measure -- python train.py --steps 100",
        # The command being measured carries its own flags, and they are not this
        # one's to interpret: `measure -- python train.py --steps 100` must hand
        # `--steps` to the script. Under argparse this was REMAINDER, which handed
        # back the `--` as well and left the handler to strip it; click consumes the
        # separator itself, so the handler's guard is now belt and braces.
        context_settings={"ignore_unknown_options": True, "allow_interspersed_args": False},
    )
    @click.argument(
        "command", nargs=-1, type=click.UNPROCESSED, help=say("cli.help.measure.command")
    )
    @click.option("-C", "--directory", default=None, help=say("cli.help.measure.C"))
    @click.option(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT_SECONDS,
        show_default=False,
        help=say("cli.help.measure.timeout", default=f"{DEFAULT_TIMEOUT_SECONDS:g}"),
    )
    @click.option("--fraction", type=float, default=None, help=say("cli.help.measure.fraction"))
    @click.option("--no-profile", is_flag=True, help=say("cli.help.measure.no_profile"))
    @click.option(
        "--baseline",
        type=float,
        default=DEFAULT_BASELINE_SECONDS,
        metavar="SECONDS",
        show_default=False,
        help=say("cli.help.measure.baseline"),
    )
    @click.option(
        "--repeat",
        type=int,
        default=1,
        metavar="N",
        show_default=False,
        help=say("cli.help.measure.repeat"),
    )
    @click.option("--into", default=None, metavar="MODEL", help=say("cli.help.measure.into"))
    @click.option(
        "--units", type=float, default=1.0, show_default=False, help=say("cli.help.measure.units")
    )
    @click.option("--scenario", default=None, help=say("cli.help.measure.scenario"))
    @click.option("--json", "json", is_flag=True, help=say("cli.help.measure.json"))
    @_language_option
    def _measure_command(**given: Any) -> int:
        return _verb("measure")(**given)

    @cli.command(
        name="diff",
        help=say("cli.help.diff.summary"),
        epilog=(
            "A status that weakened, or a quantity that disappeared, fails the gate "
            "whatever the numbers did."
        ),
    )
    @click.argument("before", help=say("cli.help.diff.before"))
    @click.argument("after", help=say("cli.help.diff.after"))
    @click.option(
        "--threshold",
        type=float,
        default=DEFAULT_DRIFT_THRESHOLD_PERCENT,
        show_default=False,
        help=say("cli.help.diff.threshold", default=f"{DEFAULT_DRIFT_THRESHOLD_PERCENT:g}"),
    )
    @click.option("--json", "json", is_flag=True, help=say("cli.help.diff.json"))
    @_language_option
    def _diff_command(**given: Any) -> int:
        return _verb("diff")(**given)

    @cli.command(
        name="machine",
        help=say("cli.help.machine.summary"),
        epilog=(
            "Nothing here is run as another user. Where a counter needs "
            "administrator rights, the command that would open it is printed "
            "and not executed, together with the reason it is shut."
        ),
    )
    @click.option("--json", "json", is_flag=True, help=say("cli.help.machine.json"))
    @_language_option
    def _machine_command(**given: Any) -> int:
        return _verb("machine")(**given)

    @cli.command(
        name="power",
        help=say("cli.help.power.summary"),
        epilog=(
            "Nothing here is run as another user. Where a counter needs "
            "administrator rights, the command that would open it is printed "
            "and not executed, together with the reason it is shut."
        ),
    )
    @click.option("--json", "json", is_flag=True, help=say("cli.help.power.json"))
    @click.option(
        "--seconds", type=float, default=0.0, show_default=False, help=say("cli.help.power.seconds")
    )
    @_language_option
    def _power_command(**given: Any) -> int:
        return _verb("power")(**given)

    @cli.command(
        name="consent",
        help=say("cli.help.consent.summary"),
        epilog=(
            "Running a repository under study executes third-party code on this "
            "machine, with your permissions. There is no sandbox."
        ),
    )
    @click.argument("decision", type=click.Choice(["grant", "revoke"]))
    @click.option("--path", default=None, help=say("cli.help.consent.path"))
    @_language_option
    def _consent_command(**given: Any) -> int:
        return _verb("consent")(**given)

    # --- catalog, and its actions -------------------------------------------------

    @cli.group(
        name="catalog",
        cls=VerbGroup,
        help=say("cli.help.catalog.summary"),
        invoke_without_command=True,
        no_args_is_help=False,
    )
    @click.pass_context
    def catalog_group(context: click.Context) -> None:
        """Hold the catalogue actions. Naming none of them is a usage error."""
        if context.invoked_subcommand is None:
            # Not `context.get_help()` and exit 0: a usage error that reads as
            # success is the defect this replaced. Under argparse the equivalent was
            # argparse's help action raising SystemExit(0), which made a script
            # checking the exit code believe the command had worked.
            osh.error(
                "catalog needs an action: list, add, freshness, or refresh. "
                f"Try `{PROGRAM} catalog -h`."
            )
            context.exit(USAGE)

    _KINDS: Final[list[str]] = sorted(SECTION_OF_KIND)

    @catalog_group.command(name="list", help=say("cli.help.list.summary"))
    @click.argument("kind", type=click.Choice(_KINDS))
    @click.option("--json", "json", is_flag=True, help=say("cli.help.catalog.list.json"))
    @_language_option
    def _catalog_list_command(**given: Any) -> int:
        return _verb("catalog list")(**given)

    @catalog_group.command(
        name="add",
        help=say("cli.help.add.summary"),
        epilog=(
            "A row cannot be added without a source and a date. That is the rule "
            "that keeps the catalogues worth trusting."
        ),
    )
    @click.argument("kind", type=click.Choice(_KINDS))
    @click.argument("key", help=say("cli.help.catalog.add.key"))
    @click.option("--source-url", required=True, help=say("cli.help.catalog.add.source_url"))
    @click.option(
        "--retrieved-date", required=True, help=say("cli.help.catalog.add.retrieved_date")
    )
    @click.option(
        "--field",
        multiple=True,
        metavar="NAME=VALUE",
        help=say("cli.help.catalog.add.field"),
    )
    @_language_option
    def _catalog_add_command(**given: Any) -> int:
        return _verb("catalog add")(**given)

    @catalog_group.command(
        name="read-pcf",
        help=say("cli.help.read_pcf.summary"),
        epilog=(
            "It reads, shows its working, and stops. Nothing is written: a "
            "catalogue row is a claim somebody makes, and the person making it "
            "is the person who can defend it."
        ),
    )
    @click.argument("document", help=say("cli.help.catalog.read-pcf.document"))
    @click.option("--json", "json", is_flag=True, help=say("cli.help.catalog.read-pcf.json"))
    @_language_option
    def _catalog_read_pcf_command(**given: Any) -> int:
        return _verb("catalog read-pcf")(**given)

    @catalog_group.command(name="refresh", help=say("cli.help.refresh.summary"))
    @click.argument("catalog", help=say("cli.help.catalog.refresh.catalog"))
    @click.option("--api-key", default=None, help=say("cli.help.catalog.refresh.api_key"))
    @click.option("--year", type=int, default=None, help=say("cli.help.catalog.refresh.year"))
    @click.option(
        "--column",
        type=click.Choice(["carbon", "price", "timezones", "embodied", "both", "all"]),
        default="carbon",
        show_default=False,
        help=say("cli.help.catalog.refresh.column"),
    )
    @click.option(
        "--write", default=None, metavar="PATH", help=say("cli.help.catalog.refresh.write")
    )
    @click.option("--json", "json", is_flag=True, help=say("cli.help.catalog.refresh.json"))
    @_language_option
    def _catalog_refresh_command(**given: Any) -> int:
        return _verb("catalog refresh")(**given)

    @catalog_group.command(name="freshness", help=say("cli.help.freshness.summary"))
    @click.option(
        "--within",
        type=int,
        default=EXPIRING_WITHIN_DAYS,
        metavar="DAYS",
        show_default=False,
        help=say("cli.help.catalog.freshness.within", default=EXPIRING_WITHIN_DAYS),
    )
    @click.option("--json", "json", is_flag=True, help=say("cli.help.catalog.freshness.json"))
    @_language_option
    def _catalog_freshness_command(**given: Any) -> int:
        return _verb("catalog freshness")(**given)

    return cli


# --- The surrounding machinery ------------------------------------------------


def accepts(argv: Sequence[str]) -> bool:
    """Return whether this surface would accept an invocation, without running it.

    The documentation gate parses every command the pages show to catch a page
    teaching a flag that was renamed. Under
    argparse it called ``parse_args`` and caught :class:`SystemExit`; the
    equivalent is published here instead of rebuilt in the test, because getting
    it right needs one thing about click that is easy to get wrong.

    A group's ``make_context`` does not resolve the verb. It leaves the verb and
    its arguments unparsed, and in click 8 it puts the verb in
    ``protected_args`` and the rest in ``args`` -- so a walker reading only
    ``args`` resolves the verb's *first argument* as a verb, and reports that
    ``validate m.yaml`` is an unknown command called ``m.yaml``. Click 9 will
    put them all back in ``args``, which is why both are read.

    Parameters
    ----------
    argv : sequence of str
        The arguments, without the program name.

    Returns
    -------
    bool
        ``True`` when every verb, flag and argument is one this surface knows,
        and every required argument is present.

    Examples
    --------
    >>> accepts(["validate", "cost.yaml"])
    True
    >>> accepts(["render", "cost.yaml", "-f", "html"])
    True
    >>> accepts(["render", "cost.yaml", "-f", "sideways"])
    False
    >>> accepts(["validate"])
    False
    """
    group = build_cli()
    command: click.Command = group
    try:
        context = group.make_context(PROGRAM, list(argv), resilient_parsing=False)
        while isinstance(command, click.Group):
            with warnings.catch_warnings():
                # Click 8 warns that `protected_args` is going. It is read here
                # *because* it is going: when it does, the attribute is absent,
                # `getattr` yields nothing, and `args` carries the verb instead
                # -- so this line is already the click 9 line. Silencing the
                # notice is narrower than pinning a version or reimplementing
                # the parser, and the suite turns warnings into errors.
                warnings.simplefilter("ignore", DeprecationWarning)
                leftover = list(getattr(context, "protected_args", []))
            rest = [*leftover, *context.args]
            if not rest:
                break
            name, found, rest = command.resolve_command(context, rest)
            if found is None:  # pragma: no cover - click raises instead.
                return False
            context = found.make_context(name, rest, parent=context)
            command = found
    except click.ClickException:
        return False
    except click.exceptions.Exit:
        # `--help` and `--version` are accepted invocations that stop early.
        return True
    return True


def _configure_logging(args: SimpleNamespace) -> None:
    """Set the logger's level from the verbosity flags.

    Parameters
    ----------
    args : types.SimpleNamespace
        Parsed arguments, with ``verbose`` and ``quiet``.

    Examples
    --------
    >>> _configure_logging(SimpleNamespace(verbose=0, quiet=True))
    >>> osh.verbosity()
    -1
    >>> _configure_logging(SimpleNamespace(verbose=0, quiet=False))
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


def requested_language(argv: Sequence[str] | None = None) -> str | None:
    """Find the language before the help text is built, because it is built with it.

    ``--help`` is rendered from strings the commands already hold, and those are
    fixed when this module is imported. So the language has to be read off the
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


#: Numpydoc-style section headings and the rest of what a docstring carries for
#: somebody reading the source. Click shows a command's whole docstring in its
#: help when no ``help=`` is given; every command here gives one, so this is a
#: guard rather than a filter, and the gate below is what keeps it honest.
_NOT_FOR_A_TERMINAL = re.compile(
    r"\n\s*(?:Parameters|Returns|Examples|Raises)\s*\n\s*-{3,}.*", re.S
)


def _let_the_streams_degrade_rather_than_die() -> None:
    """Make the output streams survive a character they cannot encode.

    This package's prose uses typography that plain byte encodings do not carry:
    the em dash in both languages, and in French the accents and the ``œ``
    ligature. Written to a stream that cannot encode them -- a container with
    no language set, a wrapper that exports ``PYTHONIOENCODING=ascii``, a log
    collector reading a pipe -- every one of those raised
    :class:`UnicodeEncodeError` from inside the write, so the command died with
    a traceback and printed nothing. Measured across eight verbs on an ASCII
    stream: all eight failed in French and three in English, the English ones
    on the em dash alone.

    The streams now use ``backslashreplace``, so an unencodable character is
    written as the escape naming it and the report still arrives.

    **The declared encoding is kept, deliberately.** Forcing the stream to
    UTF-8 would print the prose correctly far more often, and it is the wrong
    thing to do here: ``PYTHONIOENCODING`` is something the operator stated,
    and replacing a stated input with a more plausible one is the defect this
    package exists to refuse -- the same one :func:`~saggio.estimate.context.
    local_timezone_name` was fixed for. So the escape is visible and reversible
    rather than quietly correct, and ``?`` was refused for the opposite reason:
    it loses the character instead of naming it.

    Examples
    --------
    >>> _let_the_streams_degrade_rather_than_die()
    """
    for stream in (sys.stdout, sys.stderr):
        # A doctest or a caller may have replaced the stream with something
        # that holds text rather than bytes, and has nothing to reconfigure.
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(errors="backslashreplace")
        except (OSError, ValueError):  # pragma: no cover - a stream that refuses
            pass


def main(argv: Sequence[str] | None = None) -> int:
    """Run the command line.

    Click is driven with ``standalone_mode=False`` so that it returns the verb's
    exit code instead of raising :class:`SystemExit` with it. That keeps this
    function what it was under argparse -- something a test, a server or
    :func:`run` can call and read an integer from -- and keeps the exit codes
    the property of :mod:`saggio.cli.exit_codes` rather than of a library's
    defaults.

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
    # Before anything writes, including the help text.
    _let_the_streams_degrade_rather_than_die()
    arguments = list(sys.argv[1:] if argv is None else argv)
    # Before the help is rendered, because the help is built from the catalogue
    # and a `--help` in the wrong language would be the one piece of this
    # surface nobody could ask to change.
    with language(requested_language(arguments)):
        if COMPLETION_VARIABLE in os.environ:
            # The shell is asking what could come next, not asking for work.
            # Click answers that inside its own `main`, before parsing, so this
            # has to reach it -- and it must reach it even with no arguments at
            # all, which is the common case: a bare `saggio <TAB>`. Completion
            # is the one thing argparse never offered and the reason this
            # branch exists.
            try:
                build_cli().main(args=arguments, prog_name=PROGRAM, standalone_mode=False)
            except SystemExit as finished:
                # Click exits from the completion path. `main` promises an
                # integer, so the exit code is returned rather than thrown.
                return int(finished.code or OK)
            return OK
        if not arguments:
            # Being asked for nothing is being asked for something this cannot
            # do, so the help goes out and the code says so.
            group = build_cli()
            click.echo(group.get_help(click.Context(group, info_name=PROGRAM)))
            return USAGE
        try:
            return int(
                build_cli().main(args=arguments, prog_name=PROGRAM, standalone_mode=False) or OK
            )
        except click.exceptions.Exit as asked:
            # `--help` and `--version` are not failures, and click signals them
            # this way rather than by returning.
            return int(asked.exit_code)
        except click.UsageError as wrong:
            wrong.show()
            return int(wrong.exit_code)
        except click.ClickException as refused:
            refused.show()
            return int(refused.exit_code)
        except click.exceptions.Abort:
            osh.error("Interrupted.")
            return USAGE


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
