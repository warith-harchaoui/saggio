"""
The dimensions a cost model reports on.

Module summary
--------------
A *dimension* is one measurable axis of what it costs to run code: money, time,
energy, carbon, water, and whatever else a team needs to watch. Here a dimension
is a registered object rather than a hard-wired field name, and that registration
is load-bearing: the schema stores costs in a ``costs`` mapping keyed by
dimension, so the validator, the renderer, and the drift gate all iterate the
registry. A project that registers ``egress`` in gigabytes gets the same
validation, the same table column, and the same drift detection as ``carbon``,
with no change to this package.

A :class:`Dimension` carries no numbers. It is an identity, a label, a unit, a
sentence about what is and is not counted, and the direction that counts as a
regression. Values live in the cost model and name a dimension by its key.

Usage example
-------------
>>> from saggio.model.dimensions import Dimension, DimensionRegistry
>>> registry = DimensionRegistry()
>>> registry.get("energy").unit
'kWh'
>>> registry.register(Dimension("egress", "Network egress", "GB", "Bytes leaving the datacenter."))
>>> registry.keys()[-1]
'egress'

Author
------
Warith Harchaoui
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from typing import Any, Final

#: Reserved key prefix. A project may not register a dimension whose key starts
#: with this, so the package can add built-ins later without colliding.
_RESERVED_PREFIX: Final[str] = "_"


@dataclass(frozen=True, slots=True)
class Dimension:
    """One measurable axis of the cost of running a unit of work.

    Parameters
    ----------
    key : str
        Stable machine identifier used in YAML and in code, for example
        ``energy``. Lowercase, no spaces; once published it never changes.
    label : str
        Human-readable name shown in reports, for example ``Energy``.
    unit : str
        The unit values on this dimension are expressed in, for example ``kWh``.
        A single value may override it, but this states the intent.
    description : str
        One sentence saying what the dimension counts and where its boundary is,
        so a reader knows what a number on this axis does and does not include.
    higher_is_worse : bool
        Whether a larger value is a regression. ``True`` for every cost-like
        axis; exposed so the drift gate and any dashboard can reason about
        direction without hard-coding dimension names.
    is_money : bool
        Whether values on this axis are amounts of money, and therefore carry an
        ISO 4217 currency alongside the number.

    Examples
    --------
    >>> Dimension("money", "Money", "USD", "Electricity plus API price.", is_money=True).is_money
    True
    """

    key: str
    label: str
    unit: str
    description: str
    higher_is_worse: bool = True
    is_money: bool = False

    def to_mapping(self) -> dict[str, Any]:
        """Serialise to the YAML mapping a model uses to declare a dimension.

        Returns
        -------
        dict
            A mapping with ``key``, ``label``, ``unit``, ``description``, and the
            two flags only when they differ from the default.

        Examples
        --------
        >>> sorted(Dimension("t", "T", "s", "Time.").to_mapping())
        ['description', 'key', 'label', 'unit']
        """
        mapping: dict[str, Any] = {
            "key": self.key,
            "label": self.label,
            "unit": self.unit,
            "description": self.description,
        }
        if not self.higher_is_worse:
            mapping["higher_is_worse"] = False
        if self.is_money:
            mapping["is_money"] = True
        return mapping

    @classmethod
    def from_mapping(cls, mapping: dict[str, Any]) -> Dimension:
        """Build a dimension from the YAML mapping a model declares it with.

        Parameters
        ----------
        mapping : dict
            A mapping with ``key``; ``label``, ``unit``, ``description``, and the
            flags are optional and default to something usable.

        Returns
        -------
        Dimension
            The parsed dimension. A missing label falls back to the key so a
            half-filled declaration still renders.

        Examples
        --------
        >>> Dimension.from_mapping({"key": "egress", "unit": "GB"}).label
        'egress'
        """
        key = str(mapping.get("key", "")).strip()
        return cls(
            key=key,
            label=str(mapping.get("label") or key),
            unit=str(mapping.get("unit") or ""),
            description=str(mapping.get("description") or ""),
            higher_is_worse=bool(mapping.get("higher_is_worse", True)),
            is_money=bool(mapping.get("is_money", False)),
        )


MONEY: Final[Dimension] = Dimension(
    key="money",
    label="Money",
    unit="currency",
    description="Electricity for local compute plus the price of external API calls.",
    is_money=True,
)
TIME: Final[Dimension] = Dimension(
    key="time",
    label="Time",
    unit="s",
    description="Wall-clock time to complete one canonical unit of work.",
)
ENERGY: Final[Dimension] = Dimension(
    key="energy",
    label="Energy",
    unit="kWh",
    description="Electricity drawn by local compute for one unit, datacenter overhead included.",
)
CARBON: Final[Dimension] = Dimension(
    key="carbon",
    label="Carbon",
    unit="gCO2e",
    description="Grid emissions for that energy, at the deployment region's intensity.",
)
WATER: Final[Dimension] = Dimension(
    key="water",
    label="Water",
    unit="L",
    description="Datacenter cooling water for that energy, when a sourced WUE exists.",
)

#: The dimensions every model reports by default, in the order reports read.
CANONICAL_DIMENSIONS: Final[tuple[Dimension, ...]] = (MONEY, TIME, ENERGY, CARBON, WATER)


class DimensionRegistry:
    """An ordered collection of the dimensions one cost model reports.

    The registry starts from the canonical five and accepts more. It keeps
    insertion order so report columns are stable across runs, and refuses a
    duplicate key so two dimensions can never collide silently.

    Parameters
    ----------
    dimensions : iterable of Dimension, optional
        Initial dimensions. Defaults to :data:`CANONICAL_DIMENSIONS`.

    Raises
    ------
    ValueError
        If the initial dimensions contain a duplicate or an invalid key.

    Examples
    --------
    >>> registry = DimensionRegistry()
    >>> "carbon" in registry
    True
    >>> len(registry)
    5
    """

    def __init__(self, dimensions: Iterable[Dimension] = CANONICAL_DIMENSIONS) -> None:
        # Keyed storage gives O(1) lookup; dicts keep insertion order, which is
        # the report order, so one structure serves both needs.
        self._by_key: dict[str, Dimension] = {}
        for dimension in dimensions:
            self.register(dimension)

    def register(self, dimension: Dimension) -> None:
        """Add a dimension, refusing a duplicate or an unusable key.

        Parameters
        ----------
        dimension : Dimension
            The dimension to add.

        Raises
        ------
        ValueError
            If the key is empty, reserved, or already registered.

        Examples
        --------
        >>> registry = DimensionRegistry(())
        >>> registry.register(Dimension("energy", "Energy", "kWh", "Electricity."))
        >>> registry.keys()
        ('energy',)
        """
        key = dimension.key
        if not key:
            raise ValueError("A dimension needs a non-empty key.")
        if key.startswith(_RESERVED_PREFIX):
            raise ValueError(
                f"Dimension key {key!r} is reserved: keys starting with "
                f"{_RESERVED_PREFIX!r} are kept for future built-ins."
            )
        if key in self._by_key:
            raise ValueError(f"Dimension {key!r} is already registered.")
        self._by_key[key] = dimension

    def get(self, key: str) -> Dimension:
        """Return the dimension registered under ``key``.

        Parameters
        ----------
        key : str
            The dimension key to look up.

        Returns
        -------
        Dimension
            The registered dimension.

        Raises
        ------
        KeyError
            If no dimension is registered under ``key``.

        Examples
        --------
        >>> DimensionRegistry().get("water").unit
        'L'
        """
        return self._by_key[key]

    def keys(self) -> tuple[str, ...]:
        """Return the registered keys in report order.

        Returns
        -------
        tuple of str
            The keys, in the order they were registered.

        Examples
        --------
        >>> DimensionRegistry().keys()[:2]
        ('money', 'time')
        """
        return tuple(self._by_key)

    def __contains__(self, key: object) -> bool:
        """Return whether a dimension is registered under ``key``.

        Parameters
        ----------
        key : object
            The candidate key.

        Returns
        -------
        bool
            ``True`` when the key is registered.
        """
        return key in self._by_key

    def __iter__(self) -> Iterator[Dimension]:
        """Iterate the dimensions in report order.

        Returns
        -------
        iterator of Dimension
            The registered dimensions.
        """
        return iter(self._by_key.values())

    def __len__(self) -> int:
        """Return how many dimensions are registered.

        Returns
        -------
        int
            The number of dimensions.
        """
        return len(self._by_key)


def registry_for(declared: Any) -> DimensionRegistry:
    """Build the registry a model works with, canonical five plus its own.

    Parameters
    ----------
    declared : Any
        The model's ``dimensions`` node: a list of dimension mappings, or
        anything else (including ``None``) meaning "just the canonical five".

    Returns
    -------
    DimensionRegistry
        The canonical dimensions followed by every well-formed declared one.
        A declaration that duplicates a canonical key, or has no key, is skipped
        here and reported by the validator, which has a path to point at.

    Examples
    --------
    >>> registry_for([{"key": "egress", "unit": "GB"}]).keys()[-1]
    'egress'
    >>> len(registry_for(None))
    5
    """
    registry = DimensionRegistry()
    if not isinstance(declared, list):
        return registry
    for entry in declared:
        if not isinstance(entry, dict):
            continue
        dimension = Dimension.from_mapping(entry)
        try:
            registry.register(dimension)
        except ValueError:
            # A bad declaration is the validator's story to tell, with the
            # dotted path that produced it; building the registry must not fail.
            continue
    return registry
