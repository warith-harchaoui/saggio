"""
The quantity: a number that remembers where it came from.

Module summary
--------------
A bare float has forgotten whether it was measured or guessed, which currency it
is in, and who to ask if it looks wrong. :class:`Quantity` is the bundle that
remembers: the value, its unit, its currency when it is money, its honesty
status, its provenance, and the names of the quantities it was derived from.

That last field is what makes the weakest-link rule general. In earlier designs
the rule was hard-coded for three fields (energy from runtime and power, money
from energy and price, carbon from energy and grid intensity), so a project that
tracked a fourth dimension got no enforcement at all. Here the derivation is data:
a quantity names its inputs, and the validator walks whatever it finds.

A quantity maps one-to-one onto its YAML mapping, so parsing and serialising are
lossless and a hand-edited model round-trips unchanged.

Usage example
-------------
>>> from saggio.model.quantity import Quantity
>>> price = Quantity.from_mapping(
...     {"value": 0.28, "unit": "USD/kWh", "currency": "USD", "status": "estimated"}
... )
>>> price.value, price.status
(0.28, 'estimated')
>>> price.is_known()
True

Author
------
Warith Harchaoui
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Final

from .taxonomy import PLACEHOLDER, TODO, is_valid_status

#: The keys a quantity mapping may carry. Anything else in a mapping that also
#: has a ``value`` key is a typo or an invention, and the validator says so.
QUANTITY_KEYS: Final[frozenset[str]] = frozenset(
    {
        "value",
        "unit",
        "currency",
        "status",
        "source_kind",
        "source_url",
        "retrieved_date",
        "derived_from",
        "notes",
    }
)

#: How a sourced number was come by. The honesty status says how well founded a
#: number is; this says who founded it, which the status cannot express because
#: a figure read from a vendor's own price API and a figure copied out of a
#: community JSON are both, correctly, ``estimated``.
STATED: Final[str] = "stated"
FIRST_PARTY: Final[str] = "first-party"
AGGREGATOR: Final[str] = "aggregator"

#: The source kinds a quantity may declare, strongest first. Anything else is a
#: typo, and the validator says so rather than letting an invented kind through.
SOURCE_KINDS: Final[tuple[str, ...]] = (STATED, FIRST_PARTY, AGGREGATOR)

#: Comparable strength of each kind, so a drift gate can see a provenance that
#: weakened. Only the ordering is meaningful; the gaps are not.
_SOURCE_STRENGTH: Final[dict[str, int]] = {STATED: 3, FIRST_PARTY: 2, AGGREGATOR: 1}

#: Strength of an unrecognised kind: below every real one, so a typo can never
#: make a provenance look stronger than it is.
_UNKNOWN_SOURCE_STRENGTH: Final[int] = -1


def source_strength(kind: object) -> int:
    """Return the comparable strength of a source kind.

    Parameters
    ----------
    kind : object
        A source kind, or ``None`` when the quantity declares none.

    Returns
    -------
    int
        Higher means closer to whoever actually sets the number. ``0`` when no
        kind is declared, which is neither a promotion nor a demotion; anything
        unrecognised scores below that.

    Examples
    --------
    >>> source_strength("first-party") > source_strength("aggregator")
    True
    >>> source_strength(None)
    0
    >>> source_strength("vibes") < source_strength("aggregator")
    True
    """
    if kind is None:
        return 0
    if not isinstance(kind, str):
        return _UNKNOWN_SOURCE_STRENGTH
    return _SOURCE_STRENGTH.get(kind, _UNKNOWN_SOURCE_STRENGTH)


def is_valid_source_kind(kind: object) -> bool:
    """Return whether a value is one of the declared source kinds.

    Parameters
    ----------
    kind : object
        Any value, typically a string parsed from a cost model.

    Returns
    -------
    bool
        ``True`` when it is exactly one of :data:`SOURCE_KINDS`.

    Examples
    --------
    >>> is_valid_source_kind("aggregator")
    True
    >>> is_valid_source_kind("scraped")
    False
    """
    return isinstance(kind, str) and kind in SOURCE_KINDS


#: Statuses for which a missing (``None``) value is expected rather than a fault.
_VALUELESS_STATUSES: Final[frozenset[str]] = frozenset({PLACEHOLDER, TODO})


@dataclass(frozen=True, slots=True)
class Quantity:
    """One number with its unit, honesty status, provenance, and derivation.

    Parameters
    ----------
    value : float or int or None
        The number itself. ``None`` is the correct value for a ``placeholder`` or
        a ``TODO``: the field exists, the number does not yet.
    unit : str or None
        The unit the value is expressed in, for example ``kWh`` or ``USD/kWh``.
    currency : str or None
        ISO 4217 code when the quantity is money or a price. Kept separate from
        ``unit`` so a report can convert or group by currency without parsing
        strings, and so field names need no ``_usd`` suffix.
    status : str
        One of the four honesty labels. Not validated on construction;
        :meth:`has_valid_status` reports it, so the caller decides whether a bad
        label is a warning or an error.
    source_kind : str or None
        Who the number ultimately came from: ``stated`` when a human wrote it,
        ``first-party`` when it was read from the vendor's own machine-readable
        source, ``aggregator`` when it was read from somebody else's transcription
        of that. ``None`` when the question does not arise. The status cannot
        express this, because a vendor's published price and a community JSON's
        copy of it are both, correctly, ``estimated``.
    source_url : str or None
        A live reference establishing the value. Expected on every sourced
        ``estimated`` assumption.
    retrieved_date : str or None
        The ``YYYY-MM-DD`` date the source was read, so staleness is checkable.
    derived_from : tuple of str
        Dotted paths of the quantities this one was computed from, for example
        ``("scenario.runtime", "assumptions.power_draw")``. Empty for an input.
    notes : str or None
        A short human note, typically the formula or the reasoning.

    Examples
    --------
    >>> energy = Quantity(
    ...     value=1.28e-05,
    ...     unit="kWh",
    ...     status="estimated",
    ...     derived_from=("scenario.runtime", "assumptions.power_draw"),
    ... )
    >>> energy.is_derived()
    True
    >>> energy.to_mapping()["derived_from"]
    ['scenario.runtime', 'assumptions.power_draw']
    """

    value: float | int | None = None
    unit: str | None = None
    currency: str | None = None
    status: str = TODO
    source_kind: str | None = None
    source_url: str | None = None
    retrieved_date: str | None = None
    derived_from: tuple[str, ...] = field(default_factory=tuple)
    notes: str | None = None

    @classmethod
    def from_mapping(cls, mapping: dict[str, Any]) -> Quantity:
        """Build a quantity from its YAML mapping.

        Parsing is deliberately forgiving: a partial or malformed mapping still
        produces a :class:`Quantity` so the validator, not the parser, gets to
        report the fault with a path and a readable message.

        Parameters
        ----------
        mapping : dict
            A mapping carrying at least ``value``; every other key is optional.

        Returns
        -------
        Quantity
            The parsed quantity, with missing optional keys set to ``None``.

        Examples
        --------
        >>> Quantity.from_mapping({"value": 2, "status": "measured"}).unit is None
        True
        >>> Quantity.from_mapping({"value": 1, "derived_from": "a"}).derived_from
        ('a',)
        """
        raw_derived = mapping.get("derived_from") or ()
        # A single dotted path is a common hand-edit; accept it as a one-element
        # tuple rather than iterating its characters.
        if isinstance(raw_derived, str):
            derived = (raw_derived,)
        else:
            derived = tuple(str(item) for item in raw_derived)
        return cls(
            value=mapping.get("value"),
            unit=mapping.get("unit"),
            currency=mapping.get("currency"),
            status=str(mapping.get("status", TODO)),
            source_kind=mapping.get("source_kind"),
            source_url=mapping.get("source_url"),
            retrieved_date=mapping.get("retrieved_date"),
            derived_from=derived,
            notes=mapping.get("notes"),
        )

    def to_mapping(self) -> dict[str, Any]:
        """Serialise back to a YAML mapping, dropping the fields that are unset.

        Returns
        -------
        dict
            A mapping carrying ``value`` and ``status`` always, and every other
            field only when it is set, so a minimal quantity does not sprout
            empty keys on a round trip.

        Examples
        --------
        >>> sorted(Quantity(value=1.0, status="measured").to_mapping())
        ['status', 'value']
        """
        mapping: dict[str, Any] = {"value": self.value, "status": self.status}
        if self.unit is not None:
            mapping["unit"] = self.unit
        if self.currency is not None:
            mapping["currency"] = self.currency
        if self.source_kind is not None:
            mapping["source_kind"] = self.source_kind
        if self.source_url is not None:
            mapping["source_url"] = self.source_url
        if self.retrieved_date is not None:
            mapping["retrieved_date"] = self.retrieved_date
        if self.derived_from:
            mapping["derived_from"] = list(self.derived_from)
        if self.notes is not None:
            mapping["notes"] = self.notes
        return mapping

    def has_valid_status(self) -> bool:
        """Return whether this quantity's status is one of the four labels.

        Returns
        -------
        bool
            ``True`` when :attr:`status` is a recognised honesty label.

        Examples
        --------
        >>> Quantity(value=1, status="measured").has_valid_status()
        True
        >>> Quantity(value=1, status="probably").has_valid_status()
        False
        """
        return is_valid_status(self.status)

    def is_known(self) -> bool:
        """Return whether this quantity carries a usable number.

        Returns
        -------
        bool
            ``True`` when :attr:`value` is a real number. A boolean is rejected
            even though Python calls it an ``int``: ``True`` is not a measurement.

        Examples
        --------
        >>> Quantity(value=0.0, status="measured").is_known()
        True
        >>> Quantity(status="TODO").is_known()
        False
        >>> Quantity(value=True, status="measured").is_known()
        False
        """
        return isinstance(self.value, (int, float)) and not isinstance(self.value, bool)

    def is_derived(self) -> bool:
        """Return whether this quantity declares inputs it was computed from.

        Returns
        -------
        bool
            ``True`` when :attr:`derived_from` is non-empty.

        Examples
        --------
        >>> Quantity(value=1, derived_from=("a",)).is_derived()
        True
        """
        return bool(self.derived_from)

    def expects_a_value(self) -> bool:
        """Return whether this quantity's status promises a number.

        ``placeholder`` and ``TODO`` exist precisely to hold a field open with no
        number in it; ``measured`` and ``estimated`` do not.

        Returns
        -------
        bool
            ``True`` when the status is ``measured`` or ``estimated``.

        Examples
        --------
        >>> Quantity(status="TODO").expects_a_value()
        False
        >>> Quantity(value=1, status="measured").expects_a_value()
        True
        """
        return self.status not in _VALUELESS_STATUSES

    def with_derivation(self, *paths: str) -> Quantity:
        """Return a copy of this quantity that names the inputs it came from.

        Estimators compute physics and know nothing about where the numbers sit
        in a particular model. The caller that assembles the model knows the
        dotted paths, and attaches them here, which is what lets the validator
        re-check the weakest-link rule against the file as written.

        Parameters
        ----------
        *paths : str
            Dotted paths of the input quantities.

        Returns
        -------
        Quantity
            A copy carrying those paths in :attr:`derived_from`.

        Examples
        --------
        >>> Quantity(value=1.0, status="estimated").with_derivation("a", "b").derived_from
        ('a', 'b')
        """
        return Quantity(
            value=self.value,
            unit=self.unit,
            currency=self.currency,
            status=self.status,
            source_kind=self.source_kind,
            source_url=self.source_url,
            retrieved_date=self.retrieved_date,
            derived_from=tuple(paths),
            notes=self.notes,
        )

    def unknown(self, *, reason: str | None = None) -> Quantity:
        """Return a copy of this quantity with its number withdrawn.

        Used when an estimator cannot produce a number after all: the field keeps
        its unit and shape, but stops claiming a value.

        Parameters
        ----------
        reason : str or None
            A note explaining what is missing, written into :attr:`notes`.

        Returns
        -------
        Quantity
            A ``TODO`` quantity with the same unit and currency.

        Examples
        --------
        >>> Quantity(value=3.0, unit="kWh", status="estimated").unknown().status
        'TODO'
        """
        return Quantity(
            value=None,
            unit=self.unit,
            currency=self.currency,
            status=TODO,
            notes=reason if reason is not None else self.notes,
        )


def looks_like_quantity(node: object) -> bool:
    """Return whether a parsed YAML node is a quantity mapping.

    The test is deliberately structural rather than positional: anywhere in a
    cost model, a mapping that carries a ``value`` key is a quantity and is held
    to the quantity rules. This is what lets the validator insist that *every*
    number in a model lives inside one.

    Parameters
    ----------
    node : object
        Any node from a parsed cost model.

    Returns
    -------
    bool
        ``True`` when ``node`` is a mapping with a ``value`` key.

    Examples
    --------
    >>> looks_like_quantity({"value": 1, "status": "measured"})
    True
    >>> looks_like_quantity({"name": "default"})
    False
    >>> looks_like_quantity(3.14)
    False
    """
    return isinstance(node, dict) and "value" in node
