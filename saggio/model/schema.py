"""
The cost-model schema: its version, its shape, and its compatibility policy.

Module summary
--------------
A cost model is a plain YAML mapping, so it stays diffable, reviewable in a pull
request, and readable without this package installed. What makes it a *contract*
rather than a convention is the ``schema_version`` field and the rule for reading
it, both of which live here, together with the names of the blocks a model is
made of.

Compatibility policy. Within a major line the schema only grows: a model written
today keeps validating against every later release of the same major. A model
declaring a newer major than this build understands is rejected outright rather
than misread against the wrong rules.

Usage example
-------------
>>> from saggio.model.schema import SCHEMA_VERSION, schema_major
>>> schema_major(SCHEMA_VERSION) == schema_major("2.7")
True

Author
------
Warith Harchaoui
"""

from __future__ import annotations

from typing import Final

#: The schema line this build writes and understands. Bump the minor for an
#: additive change, the major only for a break.
SCHEMA_VERSION: Final[str] = "2.0"

#: Top-level blocks every model must carry.
REQUIRED_BLOCKS: Final[tuple[str, ...]] = (
    "schema_version",
    "date_updated",
    "unit_of_work",
    "deployment",
    "scenarios",
)

#: Top-level blocks a model may carry.
OPTIONAL_BLOCKS: Final[tuple[str, ...]] = (
    "project",
    "dimensions",
    "assumptions",
    "external_services",
    "analysis",
    "measurement",
    "projections",
    "exclusions",
    "provenance_rules",
)

#: Every top-level block this build recognises. An unknown top-level key is a
#: warning, not an error: a model may be richer than the tool reading it.
KNOWN_BLOCKS: Final[tuple[str, ...]] = REQUIRED_BLOCKS + OPTIONAL_BLOCKS

#: Dotted-path prefixes under which a bare number is structural rather than a
#: cost, and therefore exempt from the "every number is a quantity" rule. Kept
#: short and explicit: each entry is a place where a plain integer genuinely
#: means something other than a measured or estimated cost.
BARE_NUMBER_EXEMPT_PREFIXES: Final[tuple[str, ...]] = (
    "schema_version",
    "deployment.physical_cores",
    "deployment.logical_cores",
    "deployment.accelerator_count",
    "dimensions",
    "analysis.language_file_counts",
    "measurement.exit_code",
    "measurement.hot_path",
)


def schema_major(version: object) -> int | None:
    """Return the integer major component of a ``schema_version`` value.

    Parameters
    ----------
    version : object
        The raw value of a model's ``schema_version``, expected to be a
        ``"MAJOR"`` or ``"MAJOR.MINOR"`` string but tolerant of anything.

    Returns
    -------
    int or None
        The major version, or ``None`` when the value is not a well-formed
        ``MAJOR[.MINOR]`` string. Returning ``None`` lets the validator report a
        precise "malformed version" error instead of raising.

    Examples
    --------
    >>> schema_major("2.0")
    2
    >>> schema_major("3")
    3
    >>> schema_major("two") is None
    True
    >>> schema_major(None) is None
    True
    """
    if version is None:
        return None
    text = str(version).strip()
    if not text:
        return None
    head = text.split(".", 1)[0]
    if not head.isdigit():
        return None
    return int(head)


def is_bare_number_exempt(path: str) -> bool:
    """Return whether a bare number is legitimate at this dotted path.

    Every cost in a model must live inside a quantity, so its honesty status
    travels with it. A handful of places hold plain integers that are not costs
    at all, such as a byte count per language or a process exit code; this
    reports them so the validator does not cry wolf.

    Parameters
    ----------
    path : str
        A dotted path into the model, for example ``analysis.language_bytes.py``.

    Returns
    -------
    bool
        ``True`` when a bare number at this path is expected.

    Examples
    --------
    >>> is_bare_number_exempt("analysis.language_file_counts.Python")
    True
    >>> is_bare_number_exempt("scenarios[0].costs.energy")
    False
    """
    return any(
        path == prefix or path.startswith(f"{prefix}.") or path.startswith(f"{prefix}[")
        for prefix in BARE_NUMBER_EXEMPT_PREFIXES
    )
