"""
Validation: where the honesty taxonomy stops being a convention.

Module summary
--------------
A status written in a file is a promise. This module is what makes the promise
enforceable, and it is the part of the package that earned the redesign.

Three rules do the real work.

*Every number lives in a quantity.* A cost written as a bare float has no status,
so it can be neither trusted nor distrusted. The validator walks the whole model
and reports any number outside a quantity, except at the few structural paths the
schema exempts by name. This is what stops a rich extra block from smuggling
numbers past the taxonomy.

*A derived value names its inputs.* Each quantity may carry ``derived_from``, a
list of dotted paths. The validator follows them: a path that names nothing is an
error, and a quantity claiming a stronger status than the weakest input it names
is an error too. Because the derivation is data rather than code, the rule covers
a dimension this package has never heard of exactly as well as it covers carbon.

*Money says which money.* A value on a money dimension carries an ISO 4217
currency, so a report never adds dollars to euros and never has to parse a field
name to find out which it was holding.

*Provenance says whose number it is.* A quantity may declare a ``source_kind``:
``stated`` when a human wrote it, ``first-party`` when it came from the vendor's
own machine-readable source, ``aggregator`` when it came from somebody else's
transcription of that. The vocabulary is closed, because an invented kind would
read as a stronger provenance than it is.

The rest is the usual hygiene: a schema version this build understands, the
required blocks, statuses drawn from the vocabulary, non-negative physical
quantities, sourced estimates, and provenance old enough to be worth re-reading.

Nothing here prints or exits. It returns a :class:`~saggio.model.results.Report`,
and every surface renders that its own way.

Usage example
-------------
>>> from saggio.model.cost_model import CostModel
>>> from saggio.model.validate import validate
>>> model = CostModel.from_mapping({"scenarios": [{"name": "d", "runtime": 0.5}]})
>>> [issue.message for issue in validate(model).errors if "quantity" in issue.message][:1]
['is a bare number; wrap it in a quantity so it carries an honesty status']

Author
------
Warith Harchaoui
"""

from __future__ import annotations

import math
import re
from datetime import date
from typing import Any, Final

from .cost_model import CostModel, walk_bare_numbers
from .derivation import candidates, disagrees, parse_unit
from .dimensions import CANONICAL_DIMENSIONS
from .quantity import (
    QUANTITY_KEYS,
    SOURCE_KINDS,
    Quantity,
    is_valid_source_kind,
    looks_like_quantity,
)
from .results import Report
from .schema import (
    REQUIRED_BLOCKS,
    SCHEMA_VERSION,
    is_bare_number_exempt,
    schema_major,
)
from .taxonomy import ESTIMATED, MEASURED, is_valid_status, overclaims, weakest

#: Provenance older than this is warned about: a price or a grid intensity from
#: last season is not wrong, but nobody should quote it without a fresh look.
FRESHNESS_WARN_DAYS: Final[int] = 90

#: The literal a template leaves behind, which must never survive into a model
#: a reader is asked to trust.
_TEMPLATE_DATE: Final[str] = "YYYY-MM-DD"

#: ISO 4217 codes are three uppercase letters. Checked by shape rather than
#: against a bundled list, which would go stale and reject legitimate codes.
# fullmatch semantics: `$` alone would let "USD\n" through, because re lets
# `$` match before a trailing newline.
_CURRENCY_PATTERN: Final[re.Pattern[str]] = re.compile(r"[A-Z]{3}")


def _is_calendar_date(value: object) -> bool:
    """Return whether a value is a ``YYYY-MM-DD`` calendar date.

    Parameters
    ----------
    value : object
        The candidate, typically a string from a model.

    Returns
    -------
    bool
        ``True`` when it parses as an ISO calendar date.

    Examples
    --------
    >>> _is_calendar_date("2026-02-29")
    False
    >>> _is_calendar_date("2026-02-28")
    True
    """
    if not isinstance(value, str):
        return False
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


def _contains_number(node: object) -> bool:
    """Return whether a value holds a bare number anywhere inside it.

    Parameters
    ----------
    node : object
        Any YAML value.

    Returns
    -------
    bool
        ``True`` when the value is a number or nests one, however deeply. A
        boolean is not a number here, for the same reason it is not one in a
        quantity.

    Examples
    --------
    >>> _contains_number({"a": [{"b": 3.0}]})
    True
    >>> _contains_number("three")
    False
    """
    if isinstance(node, bool):
        return False
    if isinstance(node, (int, float)):
        return True
    if isinstance(node, dict):
        return any(_contains_number(item) for item in node.values())
    if isinstance(node, list):
        return any(_contains_number(item) for item in node)
    return False


def _days_since(value: str, *, today: date | None = None) -> int | None:
    """Return how many days have passed since an ISO date.

    Parameters
    ----------
    value : str
        An ISO ``YYYY-MM-DD`` date.
    today : datetime.date or None, optional
        The day to measure from. Defaults to the real today; injectable so tests
        do not drift as the calendar moves.

    Returns
    -------
    int or None
        The age in days, or ``None`` when the string is not a date.

    Examples
    --------
    >>> from datetime import date
    >>> _days_since("2026-01-01", today=date(2026, 1, 31))
    30
    >>> _days_since("not-a-date") is None
    True
    """
    if not _is_calendar_date(value):
        return None
    return ((today or date.today()) - date.fromisoformat(value)).days


def _check_schema_version(model: CostModel, report: Report) -> None:
    """Apply the schema-version compatibility policy.

    Parameters
    ----------
    model : CostModel
        The model under validation.
    report : Report
        Accumulator for the verdict.

    Examples
    --------
    >>> report = Report()
    >>> _check_schema_version(CostModel.from_mapping({"schema_version": "99.0"}), report)
    >>> report.ok
    False
    """
    if "schema_version" not in model.data:
        report.warning(
            "schema_version",
            f'is missing; assuming "{SCHEMA_VERSION}". Add it at the top of the model.',
        )
        return
    declared = schema_major(model.data["schema_version"])
    current = schema_major(SCHEMA_VERSION)
    if declared is None:
        report.error("schema_version", f'must be a MAJOR.MINOR string such as "{SCHEMA_VERSION}"')
    elif current is not None and declared > current:
        report.error(
            "schema_version",
            f"declares major {declared}, newer than this build understands "
            f"({SCHEMA_VERSION}); upgrade saggio",
        )
    elif current is not None and declared < current:
        report.warning(
            "schema_version",
            f"declares major {declared}, older than the current {SCHEMA_VERSION}; "
            "re-audit the model or bump it once you have checked the numbers",
        )


def _check_required_blocks(model: CostModel, report: Report) -> None:
    """Verify the mandatory structure is present and shaped correctly.

    Parameters
    ----------
    model : CostModel
        The model under validation.
    report : Report
        Accumulator for the verdict.

    Examples
    --------
    >>> report = Report(); _check_required_blocks(CostModel.from_mapping({}), report)
    >>> "unit_of_work" in report.to_text()
    True
    """
    for block in REQUIRED_BLOCKS:
        # schema_version and scenarios each have their own check, with their own
        # message; reporting them here as well would say the same thing twice and
        # would contradict the version policy, which forgives an absent version.
        if block in {"schema_version", "scenarios"}:
            continue
        if block not in model.data:
            report.error(block, "is required and missing")

    updated = model.data.get("date_updated")
    if updated is not None:
        text = str(updated)
        if text == _TEMPLATE_DATE:
            report.warning("date_updated", "is still the template placeholder")
        elif not _is_calendar_date(text):
            report.error("date_updated", f"must be a {_TEMPLATE_DATE} calendar date, got {text!r}")

    unit = model.data.get("unit_of_work")
    if unit is not None and not isinstance(unit, dict):
        report.error("unit_of_work", "must be a mapping")
    elif isinstance(unit, dict) and not str(unit.get("name") or "").strip():
        report.error(
            "unit_of_work.name",
            "is required: state the one thing whose cost this model reports, "
            "such as 'one inference on a median request'",
        )

    deployment = model.data.get("deployment")
    if deployment is not None and not isinstance(deployment, dict):
        report.error("deployment", "must be a mapping")

    if not model.scenarios():
        report.error("scenarios", "a model must define at least one scenario")

    for block in model.unknown_blocks():
        report.warning(block, "is not a block this build knows; it is carried through untouched")


def _check_quantity(path: str, raw: dict[str, Any], model: CostModel, report: Report) -> None:
    """Check one quantity's status, value, currency, provenance, and derivation.

    Parameters
    ----------
    path : str
        The dotted path of the quantity.
    raw : dict
        The raw quantity mapping.
    model : CostModel
        The whole model, needed to resolve ``derived_from`` paths.
    report : Report
        Accumulator for the verdict.

    Examples
    --------
    >>> report = Report()
    >>> _check_quantity("p", {"value": -1, "status": "measured"},
    ...                 CostModel.from_mapping({}), report)
    >>> "cannot be negative" in report.to_text()
    True
    """
    quantity = Quantity.from_mapping(raw)

    unknown_keys = sorted(set(raw) - QUANTITY_KEYS)
    for key in unknown_keys:
        # An unknown key is untidiness; an unknown key with numbers inside it is
        # a smuggling route. The first is a warning, the second defeats the one
        # promise this validator makes, so it is an error.
        if _contains_number(raw[key]):
            report.error(
                path,
                f"hides numbers under {key!r}, which a quantity does not define; "
                "a number the walker cannot see is a number outside the rules",
            )
        else:
            report.warning(
                path,
                f"carries {key!r}, which a quantity does not define; "
                "move it to notes or to its own block",
            )

    for key in (
        "unit",
        "currency",
        "status",
        "source_kind",
        "source_url",
        "retrieved_date",
        "notes",
    ):
        entry = raw.get(key)
        if isinstance(entry, (dict, list)):
            report.error(
                path,
                f"has a block where {key!r} should be text; "
                "a number hidden inside it would escape the rules",
            )

    if not quantity.has_valid_status():
        report.error(
            path,
            f"has status {quantity.status!r}; it must be one of "
            "measured, estimated, placeholder, TODO",
        )
        return

    value = quantity.value
    if value is not None and not quantity.carries_number():
        report.error(
            path,
            f"has value {value!r}, which is not a number; write numbers unquoted, "
            "or move prose to notes",
        )
    elif quantity.carries_number():
        if not math.isfinite(value):
            report.error(
                path,
                f"is {value!r}, which is not a finite number; NaN and infinity "
                "state nothing a reader can check",
            )
        elif value < 0:
            report.error(
                path,
                f"is {value!r}; a cost of running code cannot be negative",
            )
        if not quantity.expects_a_value():
            report.warning(
                path,
                f"is status {quantity.status!r} but carries the number {value!r}; "
                "a placeholder or a TODO should have no value",
            )
    elif quantity.expects_a_value():
        report.error(
            path,
            f"claims {quantity.status!r} but has no number; "
            "either supply one or lower the status to TODO",
        )

    if quantity.source_kind is not None and not is_valid_source_kind(quantity.source_kind):
        listed = ", ".join(SOURCE_KINDS)
        report.error(
            path,
            f"has source_kind {quantity.source_kind!r}; it must be one of {listed}",
        )

    if quantity.currency is not None and not _CURRENCY_PATTERN.fullmatch(str(quantity.currency)):
        report.error(
            path,
            f"has currency {quantity.currency!r}; it must be a three-letter ISO 4217 code",
        )

    retrieved = quantity.retrieved_date
    if retrieved == _TEMPLATE_DATE:
        report.warning(
            path,
            f"has retrieved_date {_TEMPLATE_DATE!r}, still the template's literal; "
            "write the date the source was actually read",
        )
    elif retrieved is not None:
        age = _days_since(str(retrieved))
        if age is None:
            report.error(path, f"has retrieved_date {retrieved!r}, which is not a calendar date")
        elif age > FRESHNESS_WARN_DAYS:
            report.warning(
                path,
                f"was sourced {age} days ago, past the {FRESHNESS_WARN_DAYS}-day mark; "
                "re-read the source and refresh the number",
            )

    _check_derivation(path, quantity, model, report)
    _check_measured_is_attributable(path, quantity, model, report)


def _check_derivation(path: str, quantity: Quantity, model: CostModel, report: Report) -> None:
    """Resolve a quantity's inputs and apply the weakest-link rule.

    Overclaiming is an error rather than a warning, because the whole proposition
    of this package is that a number says how far it can be trusted. A value that
    calls itself measured when its inputs were guessed contradicts that directly.

    Parameters
    ----------
    path : str
        The dotted path of the derived quantity.
    quantity : Quantity
        The parsed quantity.
    model : CostModel
        The whole model, to resolve input paths against.
    report : Report
        Accumulator for the verdict.

    Examples
    --------
    >>> model = CostModel.from_mapping({
    ...     "runtime": {"value": 1, "status": "estimated"},
    ...     "energy": {"value": 1, "status": "measured", "derived_from": ["runtime"]},
    ... })
    >>> report = Report()
    >>> _check_derivation("energy", Quantity.from_mapping(model.data["energy"]), model, report)
    >>> "cannot outrank" in report.to_text()
    True
    """
    if not quantity.is_derived():
        return

    input_statuses: list[str | None] = []
    inputs: list[dict[str, Any]] = []
    for reference in quantity.derived_from:
        if reference == path:
            report.error(path, "lists itself in derived_from")
            continue
        node = model.get(reference)
        if node is None:
            report.error(
                path,
                f"derives from {reference!r}, which names nothing in this model",
            )
            continue
        if not looks_like_quantity(node):
            report.error(
                path,
                f"derives from {reference!r}, which is not a quantity; "
                "a derivation must name something that carries a status",
            )
            continue
        input_statuses.append(str(node.get("status")) if node.get("status") is not None else None)
        inputs.append(node)

    ceiling = weakest(*input_statuses)
    if overclaims(quantity.status, ceiling):
        report.error(
            path,
            f"claims {quantity.status!r} but its weakest input is {ceiling!r}; "
            "a derived value cannot outrank the numbers it came from",
        )

    _check_arithmetic(path, quantity, inputs, report)


#: The base dimensions a timed run with power counters actually produces. A
#: carbon figure comes from an intensity somebody published, and a cost from a
#: tariff; neither is a thing a stopwatch or an energy counter observes.
_OBSERVABLE_BASES: Final[frozenset[str]] = frozenset({"s", "J", "B"})


def _a_run_can_observe(unit: str | None) -> bool:
    """Return whether a timed run with power counters produces this unit.

    Parameters
    ----------
    unit : str or None
        As written in the model.

    Returns
    -------
    bool
        True for durations, energy, power and data, and for any unit this does
        not recognise — an unknown dimension gets the benefit of the doubt,
        because asserting that somebody's instrument cannot exist would be
        inventing a rule about their field.

    Examples
    --------
    >>> _a_run_can_observe("s"), _a_run_can_observe("kWh"), _a_run_can_observe("W")
    (True, True, True)
    >>> _a_run_can_observe("gCO2e"), _a_run_can_observe("USD")
    (False, False)
    >>> _a_run_can_observe("sheep")
    True
    """
    parsed = parse_unit(unit)
    if parsed is None:
        return True
    _, dimensions = parsed
    return all(base in _OBSERVABLE_BASES for base in dimensions)


def _check_measured_is_attributable(
    path: str, quantity: Quantity, model: CostModel, report: Report
) -> None:
    """Report a ``measured`` value that does not say what measured it.

    ``estimated`` has to name a source. ``measured`` — the strongest status in
    the taxonomy — asked for nothing at all, which is the wrong way round. A
    human writing a model by hand could put ``measured`` on any number and
    nothing in the file would say which instrument, or whether one existed.

    Three things count as saying. The quantity is derived, and its provenance is
    its derivation. It carries a note of its own, which is where the auditor
    writes the command it timed and the counters that answered. Or the model
    carries a ``measurement`` block, which is what this package writes when it
    did the measuring itself.

    But a measurement block attests only what a run can actually observe. A
    timed run with power counters produces durations, energy, power and bytes;
    it does not produce a grid's carbon intensity or a cloud bill. Letting the
    block vouch for every ``measured`` value in the file was the same mistake in
    a quieter place: a carbon figure marked ``measured``, with nothing in the
    world that could have measured it, inheriting the standing of a stopwatch.
    So the block vouches by dimension, and a value outside what a run observes
    has to attribute itself.

    A warning rather than an error: somebody may genuinely have measured this
    with their own wattmeter, or read that money off an invoice, and refusing
    their model would be refusing the truth. But an unattributed measurement
    should not pass in silence.

    Parameters
    ----------
    path : str
        Dotted path of the quantity.
    quantity : Quantity
        The value under check.
    model : CostModel
        The whole model, to look for a measurement block.
    report : Report
        Accumulator for the verdict.

    Examples
    --------
    >>> report = Report()
    >>> bare = Quantity(value=1.0, unit="s", status="measured")
    >>> _check_measured_is_attributable("r", bare, CostModel.from_mapping({}), report)
    >>> "what measured it" in report.to_text()
    True
    """
    if quantity.status != MEASURED or not quantity.is_known():
        return
    if quantity.is_derived() or quantity.notes or quantity.source_url:
        return
    block = model.data.get("measurement")
    if isinstance(block, dict) and block:
        if _a_run_can_observe(quantity.unit):
            return
        report.warning(
            path,
            f"is measured in {quantity.unit!r}, which a timed run does not observe. "
            "The measurement block in this model attests durations, energy, power "
            "and bytes; it cannot attest this one. Say in notes what measured it, "
            "or derive it from something that was measured",
        )
        return
    report.warning(
        path,
        "is measured but nothing says what measured it: no note, no derivation, "
        "and no measurement block in this model. `estimated` has to name a source; "
        "the stronger status should not ask for less",
    )


def _check_arithmetic(
    path: str, quantity: Quantity, inputs: list[dict[str, Any]], report: Report
) -> None:
    """Report a derived value that does not follow from the inputs it names.

    The check `derived_from` was always supposed to earn. A reader seeing a list
    of inputs concludes the number came from them; until this existed, nothing
    said so. A value wrong by four orders of magnitude, carrying a perfectly
    correct derivation, looked better founded than anything else on the page.

    Only relationships recognisable from the units are checked, and silence is
    the ordinary answer: a dimension a project registered this morning must not
    become an error because this does not know it.

    Parameters
    ----------
    path : str
        Dotted path of the derived quantity.
    quantity : Quantity
        The derived value.
    inputs : list of dict
        The quantities it named, already resolved.
    report : Report
        Accumulator for the verdict.

    Examples
    --------
    >>> report = Report()
    >>> wrong = Quantity(value=0.00004, unit="kWh", status="estimated",
    ...                  derived_from=("a", "b"))
    >>> _check_arithmetic("e", wrong, [{"value": 3600.0, "unit": "s"},
    ...                                {"value": 400.0, "unit": "W"}], report)
    >>> "does not follow" in report.to_text()
    True
    """
    if not quantity.is_known():
        return
    pairs: list[tuple[float, str | None]] = []
    for node in inputs:
        value = node.get("value")
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            return
        pairs.append((float(value), node.get("unit")))

    possible = candidates(pairs, quantity.unit)
    if possible is None:
        # A unit this does not know. Saying anything here would be inventing a
        # rule for somebody else's dimension, which is what the house refuses.
        return
    if not possible:
        report.error(
            path,
            f"is written in {quantity.unit!r}, which cannot come from the inputs it "
            f"names: no way of multiplying and dividing them gives that unit. The "
            "derivation and the unit disagree",
        )
        return

    stated = float(quantity.value)
    if any(not disagrees(stated, value) for value in possible):
        return
    # Several arrangements can produce the claimed unit when the units cannot say
    # whether an input multiplies or divides — amortising over a lifetime is the
    # case that matters. Matching none of them is still wrong, under every
    # reading of the derivation, which is worth saying without guessing which was
    # meant.
    gives = " or ".join(f"{value:.6g}" for value in sorted(possible))
    report.error(
        path,
        f"states {quantity.value!r} but does not follow from the inputs it names, "
        f"which give {gives} {quantity.unit}. Either the number or the derivation "
        "is wrong; naming inputs a value did not come from is the one mistake this "
        "field exists to make impossible",
    )


def _check_derivation_cycles(model: CostModel, report: Report) -> None:
    """Report a set of values that derive from each other and from nothing else.

    A direct self-reference is caught where the derivation is read, one quantity
    at a time. A cycle through an intermediate is not visible from there: each
    row names an input that exists, carries a plausible status, and resolves. It
    only shows when the whole graph is laid out.

    Why this matters more than it looks. The weakest-link rule assumes a chain
    can be walked back to something measured or sourced. A cycle has no bottom:
    every value in it is grounded in another value in it, and nothing in the set
    rests on a fact. The package would then compute a status out of nothing and
    state it with the same confidence as the rest of the page, which is the one
    thing it exists to refuse.

    Parameters
    ----------
    model : CostModel
        The model under validation.
    report : Report
        Accumulator for the verdict.

    Examples
    --------
    >>> report = Report()
    >>> _check_derivation_cycles(CostModel.from_mapping({"assumptions": {
    ...     "a": {"value": 1.0, "derived_from": ["assumptions.b"]},
    ...     "b": {"value": 1.0, "derived_from": ["assumptions.a"]}}}), report)
    >>> "circle" in report.to_text()
    True
    >>> report = Report()
    >>> _check_derivation_cycles(CostModel.from_mapping({"assumptions": {
    ...     "a": {"value": 1.0, "derived_from": ["assumptions.b"]},
    ...     "b": {"value": 1.0, "source_url": "https://example.invalid"}}}), report)
    >>> report.to_text()
    ''
    """
    edges: dict[str, list[str]] = {}
    for path, raw in model.quantities():
        references = raw.get("derived_from")
        if isinstance(references, list):
            edges[path] = [str(reference) for reference in references]

    # Depth-first, keeping the path walked so a cycle can be named in the order
    # a reader would follow it rather than as an unordered set.
    unvisited, walking, done = 0, 1, 2
    colour: dict[str, int] = dict.fromkeys(edges, unvisited)
    reported: set[frozenset[str]] = set()

    def walk(node: str, trail: list[str]) -> None:
        colour[node] = walking
        trail.append(node)
        for other in edges.get(node, ()):
            if other not in colour:
                # Names nothing in this model, which is already reported where
                # the derivation is read.
                continue
            if colour[other] == walking:
                circle = [*trail[trail.index(other) :], other]
                mark = frozenset(circle)
                if mark not in reported:
                    reported.add(mark)
                    report.error(
                        node,
                        f"derives in a circle: {' -> '.join(circle)}. Every value in "
                        "it is founded on another value in it, so none of them rests "
                        "on anything measured or sourced",
                    )
            elif colour[other] == unvisited:
                walk(other, trail)
        trail.pop()
        colour[node] = done

    for node in list(edges):
        if colour[node] == unvisited:
            walk(node, [])


def _check_bare_numbers(model: CostModel, report: Report) -> None:
    """Report every number that escaped its quantity.

    Parameters
    ----------
    model : CostModel
        The model under validation.
    report : Report
        Accumulator for the verdict.

    Examples
    --------
    >>> report = Report()
    >>> _check_bare_numbers(CostModel.from_mapping({"scenario": {"runtime": 2.0}}), report)
    >>> report.ok
    False
    """
    for path, _ in walk_bare_numbers(model.data):
        if is_bare_number_exempt(path):
            continue
        report.error(
            path,
            "is a bare number; wrap it in a quantity so it carries an honesty status",
        )


def _check_dimensions(model: CostModel, report: Report) -> None:
    """Check each scenario's costs against the model's dimension registry.

    Parameters
    ----------
    model : CostModel
        The model under validation.
    report : Report
        Accumulator for the verdict.

    Examples
    --------
    >>> report = Report()
    >>> _check_dimensions(CostModel.from_mapping({"scenarios": [
    ...     {"name": "d", "costs": {"vibes": {"value": 1, "status": "TODO"}}}]}), report)
    >>> "not a registered dimension" in report.to_text()
    True
    """
    registry = model.registry
    declared = model.data.get("dimensions")
    if declared is not None and not isinstance(declared, list):
        report.error("dimensions", "must be a list of dimension declarations")
    elif isinstance(declared, list):
        # The registry drops a colliding declaration rather than failing to build,
        # which leaves the model saying one thing and the tool reading another. The
        # collision is reported here, where there is a path to point at.
        seen: set[str] = set()
        canonical = {dimension.key for dimension in CANONICAL_DIMENSIONS}
        for index, entry in enumerate(declared):
            entry_path = f"dimensions[{index}]"
            if not isinstance(entry, dict):
                report.error(entry_path, "must be a mapping with at least a key")
                continue
            key = str(entry.get("key") or "").strip()
            if not key:
                report.error(f"{entry_path}.key", "is required")
                continue
            if key in seen:
                report.error(
                    f"{entry_path}.key",
                    f"declares {key!r} a second time; the later declaration is ignored, "
                    "so remove it or give this dimension its own key",
                )
                continue
            seen.add(key)
            if key in canonical:
                report.warning(
                    f"{entry_path}.key",
                    f"redeclares the built-in dimension {key!r}; the built-in label and "
                    "unit are what reports use, so this declaration changes nothing",
                )
            if not str(entry.get("unit") or "").strip():
                report.warning(
                    f"{entry_path}.unit", "is empty; say what the numbers are counted in"
                )

    raw_scenarios = model.data.get("scenarios")
    if isinstance(raw_scenarios, list):
        for index, entry in enumerate(raw_scenarios):
            if not isinstance(entry, dict):
                report.error(
                    f"scenarios[{index}]",
                    "is not a mapping; a scenario is a block with a name and costs",
                )

    # indexed_scenarios keeps the document's own positions: a stray non-mapping
    # entry must not shift every later error onto the wrong scenario.
    for index, scenario in model.indexed_scenarios():
        base = model.scenario_path(index)
        if not str(scenario.get("name") or "").strip():
            report.error(f"{base}.name", "is required so reports and diffs can name the scenario")
        costs = scenario.get("costs")
        if costs is None:
            report.error(
                f"{base}.costs",
                "is required: a scenario states what one unit of work costs, keyed by dimension",
            )
            continue
        if not isinstance(costs, dict):
            report.error(f"{base}.costs", "must be a mapping of dimension key to quantity")
            continue
        for key, value in costs.items():
            key_path = f"{base}.costs.{key}"
            if key not in registry:
                report.error(
                    key_path,
                    f"{key!r} is not a registered dimension; register it under the model's "
                    "top-level dimensions block or correct the spelling",
                )
                continue
            if not looks_like_quantity(value):
                report.error(key_path, "must be a quantity with a value and a status")
                continue
            dimension = registry.get(key)
            currency = value.get("currency")
            if dimension.is_money and not currency:
                report.error(
                    key_path,
                    f"is on the money dimension {key!r} but names no currency; "
                    "add an ISO 4217 code so nobody adds dollars to euros",
                )
            if not dimension.is_money and currency:
                report.warning(
                    key_path,
                    f"names a currency but {key!r} is not a money dimension",
                )


def _check_assumption_provenance(model: CostModel, report: Report) -> None:
    """Warn when a sourced estimate in the assumptions block has no source.

    An estimate in ``assumptions`` stands for an external fact: a tariff, a grid
    intensity, a datasheet power figure. Without a URL a reader cannot check it
    or refresh it, which is a warning rather than an error because the model
    still works, it just cannot be audited. An assumption that names its inputs
    is exempt: it was computed here, not read somewhere, and its provenance is
    the derivation.

    Parameters
    ----------
    model : CostModel
        The model under validation.
    report : Report
        Accumulator for the verdict.

    Examples
    --------
    >>> report = Report()
    >>> _check_assumption_provenance(CostModel.from_mapping(
    ...     {"assumptions": {"pue": {"value": 1.2, "status": "estimated"}}}), report)
    >>> "no source_url" in report.to_text()
    True
    """
    assumptions = model.data.get("assumptions")
    if not isinstance(assumptions, dict):
        if assumptions is not None:
            report.error("assumptions", "must be a mapping of name to quantity")
        return
    for key, value in assumptions.items():
        if not looks_like_quantity(value):
            continue
        if value.get("derived_from"):
            # A derived assumption states its provenance by naming its inputs.
            # Asking it for a URL as well would be asking where a multiplication
            # was published.
            continue
        if value.get("status") == ESTIMATED and not value.get("source_url"):
            report.warning(
                f"assumptions.{key}",
                "is estimated with no source_url; add the page the number came from "
                "so a reader can verify and refresh it",
            )
        if value.get("status") == MEASURED and not value.get("notes"):
            report.warning(
                f"assumptions.{key}",
                "is measured but says nothing about how; note the instrument in notes",
            )


def validate(model: CostModel | dict[str, Any]) -> Report:
    """Validate a cost model and return the accumulated verdict.

    Parameters
    ----------
    model : CostModel or dict
        The model, already parsed. A plain mapping is wrapped for convenience.

    Returns
    -------
    Report
        Every error and warning found. The model is usable when the report has
        no errors; warnings never fail it, because a model that admits it is
        incomplete is being honest, and honesty is what this package rewards.

    Examples
    --------
    >>> model = {
    ...     "schema_version": "2.0",
    ...     "date_updated": "2026-09-12",
    ...     "unit_of_work": {"name": "one inference", "status": "estimated"},
    ...     "deployment": {"provider": "on-prem"},
    ...     "scenarios": [{"name": "default",
    ...                    "costs": {"energy": {"value": 1.0, "unit": "kWh",
    ...                                         "status": "estimated"}}}],
    ... }
    >>> validate(model).ok
    True
    """
    wrapped = model if isinstance(model, CostModel) else CostModel.from_mapping(model)
    report = Report()
    _check_schema_version(wrapped, report)
    _check_required_blocks(wrapped, report)
    _check_bare_numbers(wrapped, report)
    for path, raw in wrapped.quantities():
        _check_quantity(path, raw, wrapped, report)
    _check_derivation_cycles(wrapped, report)
    _check_dimensions(wrapped, report)
    _check_assumption_provenance(wrapped, report)
    return report


def overall_status(model: CostModel | dict[str, Any]) -> str | None:
    """Return the weakest status anywhere in a model.

    This is the number a reader should keep in mind for the model as a whole: it
    is only as good as its worst input, wherever that input hides.

    Parameters
    ----------
    model : CostModel or dict
        The model, already parsed.

    Returns
    -------
    str or None
        The weakest status found, or ``None`` when the model holds no quantity.

    Examples
    --------
    >>> overall_status({"a": {"value": 1, "status": "measured"},
    ...                 "b": {"value": None, "status": "TODO"}})
    'TODO'
    >>> overall_status({}) is None
    True
    """
    wrapped = model if isinstance(model, CostModel) else CostModel.from_mapping(model)
    statuses = [
        str(raw.get("status")) for _, raw in wrapped.quantities() if raw.get("status") is not None
    ]
    valid = [status for status in statuses if is_valid_status(status)]
    return weakest(*valid) if valid else None
