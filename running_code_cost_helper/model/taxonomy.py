"""
The honesty taxonomy: how much a number can be trusted.

Module summary
--------------
Every number this package reports carries a *status* saying how it came to be,
and derived numbers obey a *weakest-link* rule: a value computed from inputs may
never claim to be better founded than the worst of those inputs. This module owns
that vocabulary and the ordering that makes the rule computable. It imports
nothing from the rest of the package, so validation, estimation, rendering, and
every delivery surface share one definition.

The four statuses, strongest to weakest:

- ``measured``: recorded from an actual run on the target system.
- ``estimated``: computed from a sourced assumption or a published formula.
- ``placeholder``: a structural stand-in kept visible; not a real number.
- ``TODO``: a human must supply this before the model can be trusted.

Usage example
-------------
>>> from running_code_cost_helper.model.taxonomy import weakest
>>> weakest("measured", "estimated")   # energy from a measured runtime and an estimated power
'estimated'

Author
------
Warith Harchaoui
"""

from __future__ import annotations

from typing import Final

# The canonical status labels. Spelled out as constants so a typo in calling
# code fails at import time rather than silently creating a fifth status.
MEASURED: Final[str] = "measured"
ESTIMATED: Final[str] = "estimated"
PLACEHOLDER: Final[str] = "placeholder"
TODO: Final[str] = "TODO"

#: The whole vocabulary. Membership on a frozenset validates in O(1) and is
#: safe to test against non-strings.
ALLOWED_STATUSES: Final[frozenset[str]] = frozenset({MEASURED, ESTIMATED, PLACEHOLDER, TODO})

#: Statuses from strongest to weakest, the order reports and legends read in.
STATUS_ORDER: Final[tuple[str, ...]] = (MEASURED, ESTIMATED, PLACEHOLDER, TODO)

# Numeric strength of each status. Only the ordering is meaningful; the gaps are
# not, because the weakest-link rule merely compares them.
_STRENGTH: Final[dict[str, int]] = {
    MEASURED: 3,
    ESTIMATED: 2,
    PLACEHOLDER: 1,
    TODO: 0,
}

#: Strength given to an unrecognised label: below every real status, so a typo
#: can never accidentally *raise* a derived value's claimed trust.
_UNKNOWN_STRENGTH: Final[int] = -1

#: One-line meaning of each status, for report legends and error messages.
STATUS_MEANING: Final[dict[str, str]] = {
    MEASURED: "Recorded from an actual run on the target system.",
    ESTIMATED: "Computed from a sourced assumption or a published formula.",
    PLACEHOLDER: "A structural stand-in kept visible; not a real number.",
    TODO: "A human must supply this before the model can be trusted.",
}


def is_valid_status(status: object) -> bool:
    """Return whether ``status`` is one of the four allowed labels.

    Parameters
    ----------
    status : object
        Any value, typically a string parsed from a YAML cost model.

    Returns
    -------
    bool
        ``True`` when ``status`` is exactly one of the allowed labels.

    Examples
    --------
    >>> is_valid_status("measured")
    True
    >>> is_valid_status("guessed")
    False
    >>> is_valid_status(3)
    False
    >>> is_valid_status(["measured"])
    False
    """
    # The type check comes first because an unhashable value, such as a list that
    # a hand-edited YAML file put where a status belongs, would otherwise raise
    # from the membership test instead of being reported as the fault it is.
    return isinstance(status, str) and status in ALLOWED_STATUSES


def status_strength(status: object) -> int:
    """Return the comparable strength of a status.

    Parameters
    ----------
    status : object
        A status label. Anything unrecognised, including a non-string, scores
        below ``TODO``.

    Returns
    -------
    int
        Higher means better founded.

    Examples
    --------
    >>> status_strength("measured") > status_strength("estimated")
    True
    >>> status_strength("typo") < status_strength("TODO")
    True
    """
    if not isinstance(status, str):
        return _UNKNOWN_STRENGTH
    return _STRENGTH.get(status, _UNKNOWN_STRENGTH)


def weakest(*statuses: str | None) -> str | None:
    """Return the weakest of several statuses, ignoring the missing ones.

    This is the engine of the weakest-link rule. A derived quantity may claim at
    most the status returned here for the quantities it was computed from.

    Parameters
    ----------
    *statuses : str or None
        Input statuses. ``None`` entries are skipped, so a caller can pass the
        status of an optional input without special-casing it.

    Returns
    -------
    str or None
        The weakest status present, or ``None`` when every argument was ``None``.

    Examples
    --------
    >>> weakest("measured", "estimated")
    'estimated'
    >>> weakest("measured", None, "TODO")
    'TODO'
    >>> weakest(None, None) is None
    True
    """
    present = [s for s in statuses if s is not None]
    if not present:
        return None
    return min(present, key=status_strength)


def overclaims(derived: str | None, ceiling: str | None) -> bool:
    """Return whether a derived status claims more than its inputs allow.

    Parameters
    ----------
    derived : str or None
        The status the derived quantity declares.
    ceiling : str or None
        The weakest status among its inputs, as returned by :func:`weakest`.
        ``None`` means no inputs were declared, so there is nothing to enforce.

    Returns
    -------
    bool
        ``True`` when ``derived`` is strictly stronger than ``ceiling``.

    Examples
    --------
    >>> overclaims("measured", "estimated")
    True
    >>> overclaims("estimated", "estimated")
    False
    >>> overclaims("measured", None)
    False
    """
    if derived is None or ceiling is None:
        return False
    return status_strength(derived) > status_strength(ceiling)
