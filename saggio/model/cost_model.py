"""
The cost model itself: load it, walk it, address any number inside it.

Module summary
--------------
A cost model is a YAML mapping, and this module is the one place that knows how
to move around inside one. It offers three services the rest of the package
builds on.

*Walking.* :func:`walk_quantities` yields every quantity in the model with its
dotted path. Because a quantity is recognised structurally (any mapping with a
``value`` key), nothing can hide a number in a block the walker does not know
about. That closes the loophole where a rich extra block carried numbers past
the honesty rules.

*Addressing.* :func:`resolve_path` turns a dotted path such as
``assumptions.power_draw`` or ``scenarios[0].costs.energy`` into the node it
names. This is what makes a quantity's ``derived_from`` list checkable: the
validator follows each path and compares statuses.

*Round-tripping.* :class:`CostModel` wraps the mapping with its file path,
its dimension registry, and its scenarios, and writes back out with the key
order a reader expects rather than alphabetical soup.

Usage example
-------------
>>> from saggio.model.cost_model import CostModel
>>> model = CostModel.from_mapping({
...     "schema_version": "2.0",
...     "scenarios": [{"name": "default",
...                    "costs": {"energy": {"value": 1.0, "status": "measured"}}}],
... })
>>> [path for path, _ in model.quantities()]
['scenarios[0].costs.energy']

Author
------
Warith Harchaoui
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Final

import os_helper as osh
import yaml

from .dimensions import DimensionRegistry, registry_for
from .quantity import Quantity, looks_like_quantity
from .schema import KNOWN_BLOCKS, SCHEMA_VERSION

#: The order top-level blocks are written in. A reader meets the model the way a
#: reviewer wants to read it: what it measures, where it runs, what it assumes,
#: then the numbers. Keys not listed here are appended in their existing order.
_BLOCK_ORDER: Final[tuple[str, ...]] = (
    "schema_version",
    "date_updated",
    "project",
    "unit_of_work",
    "deployment",
    "dimensions",
    "assumptions",
    "external_services",
    "models_called",
    "scenarios",
    "projections",
    "analysis",
    "measurement",
    "exclusions",
    "provenance_rules",
)


def walk_quantities(node: Any, path: str = "") -> Iterator[tuple[str, dict[str, Any]]]:
    """Yield every quantity mapping in a model, with its dotted path.

    A quantity is recognised by shape, not by position: any mapping carrying a
    ``value`` key is one. Walking structurally means a block this build has never
    heard of still has its numbers checked.

    Parameters
    ----------
    node : Any
        A node from a parsed cost model; call with the whole model to walk it all.
    path : str, optional
        The dotted path of ``node``, used to build the paths of its children.

    Yields
    ------
    tuple of (str, dict)
        The dotted path and the raw quantity mapping at it.

    Examples
    --------
    >>> list(walk_quantities({"a": {"value": 1, "status": "measured"}}))
    [('a', {'value': 1, 'status': 'measured'})]
    >>> [p for p, _ in walk_quantities({"xs": [{"value": 0, "status": "TODO"}]})]
    ['xs[0]']
    """
    if isinstance(node, dict):
        if looks_like_quantity(node):
            yield path, node
            # A quantity is a leaf. Descending into it would treat its own
            # ``notes`` or ``unit`` as if they were nested model structure.
            return
        for key, child in node.items():
            yield from walk_quantities(child, f"{path}.{key}" if path else str(key))
    elif isinstance(node, list):
        for index, child in enumerate(node):
            yield from walk_quantities(child, f"{path}[{index}]")


def walk_bare_numbers(node: Any, path: str = "") -> Iterator[tuple[str, float | int]]:
    """Yield every number in a model that is *not* inside a quantity.

    The rule this supports is that a cost must never be a naked float, because a
    naked float has no status and so cannot be trusted or distrusted. Whatever
    this yields is either a structural integer, which the schema exempts by path,
    or a number that escaped its quantity.

    Parameters
    ----------
    node : Any
        A node from a parsed cost model.
    path : str, optional
        The dotted path of ``node``.

    Yields
    ------
    tuple of (str, int or float)
        The dotted path and the bare number found at it.

    Examples
    --------
    >>> list(walk_bare_numbers({"runtime": 0.3}))
    [('runtime', 0.3)]
    >>> list(walk_bare_numbers({"runtime": {"value": 0.3, "status": "measured"}}))
    []
    >>> list(walk_bare_numbers({"enabled": True}))
    []
    """
    if isinstance(node, dict):
        if looks_like_quantity(node):
            return
        for key, child in node.items():
            yield from walk_bare_numbers(child, f"{path}.{key}" if path else str(key))
    elif isinstance(node, list):
        for index, child in enumerate(node):
            yield from walk_bare_numbers(child, f"{path}[{index}]")
    elif isinstance(node, (int, float)) and not isinstance(node, bool):
        yield path, node


def _split_path(path: str) -> list[str | int]:
    """Split a dotted path into its mapping keys and list indices.

    Parameters
    ----------
    path : str
        A path such as ``scenarios[0].costs.energy``.

    Returns
    -------
    list of (str or int)
        Keys as strings and indices as integers, in order.

    Examples
    --------
    >>> _split_path("scenarios[0].costs.energy")
    ['scenarios', 0, 'costs', 'energy']
    >>> _split_path("")
    []
    >>> resolve_path({"a": [1, 2]}, "a[x]") is None
    True
    """
    steps: list[str | int] = []
    for chunk in path.split("."):
        if not chunk:
            continue
        name, _, rest = chunk.partition("[")
        if name:
            steps.append(name)
        # A chunk may carry several indices, as in ``matrix[0][1]``.
        while rest:
            index, _, rest = rest.partition("]")
            if index.strip().lstrip("-").isdigit():
                steps.append(int(index))
            else:
                # A malformed index such as ``[x]`` names nothing. Dropping it
                # would resolve the path to the parent list, so the typo in a
                # derived_from would be reported as the wrong error. Keep a
                # step no real node satisfies instead.
                steps.append(f"[{index}]")
            rest = rest.lstrip("[")
    return steps


def resolve_path(model: Any, path: str) -> Any:
    """Return the node a dotted path names, or ``None`` when it names nothing.

    Parameters
    ----------
    model : Any
        The parsed cost model, or any sub-node to resolve relative to.
    path : str
        A dotted path such as ``assumptions.power_draw`` or
        ``scenarios[0].costs.energy``.

    Returns
    -------
    Any
        The node at that path, or ``None`` when any step is missing. A missing
        path is not an exception here because ``derived_from`` is written by
        humans and a typo should be reported, not raised.

    Examples
    --------
    >>> resolve_path({"a": {"b": [10, 20]}}, "a.b[1]")
    20
    >>> resolve_path({"a": 1}, "a.b") is None
    True
    """
    node = model
    for step in _split_path(path):
        if isinstance(step, int):
            if not isinstance(node, list) or not -len(node) <= step < len(node):
                return None
            node = node[step]
        else:
            if not isinstance(node, dict) or step not in node:
                return None
            node = node[step]
    return node


def status_at(model: Any, path: str) -> str | None:
    """Return the honesty status of the quantity a path names.

    Parameters
    ----------
    model : Any
        The parsed cost model.
    path : str
        A dotted path expected to name a quantity.

    Returns
    -------
    str or None
        The status string, or ``None`` when the path names nothing or names
        something that is not a quantity.

    Examples
    --------
    >>> status_at({"p": {"value": 1, "status": "estimated"}}, "p")
    'estimated'
    >>> status_at({"p": 1}, "p") is None
    True
    """
    node = resolve_path(model, path)
    if not looks_like_quantity(node):
        return None
    return str(node.get("status")) if node.get("status") is not None else None


@dataclass(slots=True)
class CostModel:
    """A parsed cost model, with the context needed to read and write it.

    Parameters
    ----------
    data : dict
        The model mapping as parsed from YAML. Held by reference, so a caller
        that mutates it sees the change here and vice versa; this is deliberate,
        because the auditor builds a model block by block.
    path : pathlib.Path or None
        Where the model was loaded from, for error messages and for resolving
        relative references. ``None`` for a model built in memory.

    Examples
    --------
    >>> model = CostModel.from_mapping({"schema_version": "2.0", "scenarios": []})
    >>> model.schema_version
    '2.0'
    >>> model.scenarios()
    []
    """

    data: dict[str, Any] = field(default_factory=dict)
    path: Path | None = None

    @classmethod
    def from_mapping(cls, data: dict[str, Any], path: Path | None = None) -> CostModel:
        """Wrap an already-parsed mapping.

        Parameters
        ----------
        data : dict
            The model mapping.
        path : pathlib.Path or None, optional
            Where it came from.

        Returns
        -------
        CostModel
            The wrapped model.

        Examples
        --------
        >>> CostModel.from_mapping({}).data
        {}
        """
        return cls(data=data, path=path)

    @classmethod
    def load(cls, path: str | Path) -> CostModel:
        r"""Read and parse a cost model from a YAML file.

        Parameters
        ----------
        path : str or pathlib.Path
            The file to read.

        Returns
        -------
        CostModel
            The parsed model.

        Raises
        ------
        AssertionError
            If the file does not exist or is empty, reported through
            ``os_helper.check`` so every surface gets the same message.
        ValueError
            If the file is not valid YAML, or parses to something other than a
            mapping.

        Examples
        --------
        >>> import tempfile, pathlib
        >>> with tempfile.TemporaryDirectory() as folder:
        ...     target = pathlib.Path(folder) / "m.yaml"
        ...     _ = target.write_text("schema_version: '2.0'", encoding="utf-8")
        ...     version = CostModel.load(target).schema_version
        >>> version
        '2.0'
        """
        target = Path(path)
        osh.check(
            osh.file_exists(str(target), check_empty=True),
            f"Cost model not found or empty: {target}",
        )
        try:
            parsed = yaml.safe_load(target.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            raise ValueError(f"{target} is not valid YAML: {exc}") from exc
        if not isinstance(parsed, dict):
            raise ValueError(f"{target} must contain a mapping, got {type(parsed).__name__}.")
        return cls(data=parsed, path=target)

    @property
    def schema_version(self) -> str:
        """Return the model's declared schema version.

        Returns
        -------
        str
            The declared version, or this build's :data:`SCHEMA_VERSION` when the
            model does not declare one.
        """
        declared = self.data.get("schema_version")
        return str(declared) if declared is not None else SCHEMA_VERSION

    @property
    def registry(self) -> DimensionRegistry:
        """Return the dimensions this model reports on.

        Returns
        -------
        DimensionRegistry
            The canonical dimensions plus any the model declares.

        Examples
        --------
        >>> CostModel.from_mapping({"dimensions": [{"key": "egress"}]}).registry.keys()[-1]
        'egress'
        """
        return registry_for(self.data.get("dimensions"))

    def scenarios(self) -> list[dict[str, Any]]:
        """Return the model's scenarios as a list, whichever spelling it used.

        A model may carry a single ``scenario`` mapping or a ``scenarios`` list.
        Both flatten to a list here so every caller iterates one way.

        Returns
        -------
        list of dict
            Zero or more scenario mappings.

        Examples
        --------
        >>> CostModel.from_mapping({"scenario": {"name": "one"}}).scenarios()
        [{'name': 'one'}]
        """
        scenarios = self.data.get("scenarios")
        if isinstance(scenarios, list):
            return [entry for entry in scenarios if isinstance(entry, dict)]
        single = self.data.get("scenario")
        if isinstance(single, dict):
            return [single]
        return []

    def indexed_scenarios(self) -> list[tuple[int, dict[str, Any]]]:
        """Return the scenarios with their positions in the document.

        :meth:`scenarios` drops entries that are not mappings, which is right
        for iteration and wrong for addressing: a stray string at position 0
        would shift every later scenario's reported path by one, so the errors
        would point at the wrong entry. This keeps the document's own indices.

        Returns
        -------
        list of (int, dict)
            Original position and scenario mapping, in document order.

        Examples
        --------
        >>> CostModel.from_mapping(
        ...     {"scenarios": ["stray", {"name": "real"}]}).indexed_scenarios()
        [(1, {'name': 'real'})]
        """
        scenarios = self.data.get("scenarios")
        if isinstance(scenarios, list):
            return [
                (index, entry) for index, entry in enumerate(scenarios) if isinstance(entry, dict)
            ]
        single = self.data.get("scenario")
        if isinstance(single, dict):
            return [(0, single)]
        return []

    def scenario_path(self, index: int) -> str:
        """Return the dotted path of the scenario at ``index``.

        The path depends on which spelling the model used, and ``derived_from``
        entries have to match it, so this is the single place that decides.

        Parameters
        ----------
        index : int
            Position of the scenario in :meth:`scenarios`.

        Returns
        -------
        str
            ``scenarios[i]`` or ``scenario``.

        Examples
        --------
        >>> CostModel.from_mapping({"scenario": {}}).scenario_path(0)
        'scenario'
        >>> CostModel.from_mapping({"scenarios": [{}]}).scenario_path(0)
        'scenarios[0]'
        """
        if isinstance(self.data.get("scenarios"), list):
            return f"scenarios[{index}]"
        return "scenario"

    def quantities(self) -> list[tuple[str, dict[str, Any]]]:
        """Return every quantity in the model with its dotted path.

        Returns
        -------
        list of (str, dict)
            Paths and raw quantity mappings, in document order.

        Examples
        --------
        >>> CostModel.from_mapping({"a": {"value": 1, "status": "TODO"}}).quantities()
        [('a', {'value': 1, 'status': 'TODO'})]
        """
        return list(walk_quantities(self.data))

    def typed_quantities(self) -> list[tuple[str, Quantity]]:
        """Return every quantity parsed into a :class:`Quantity`.

        Returns
        -------
        list of (str, Quantity)
            Paths and parsed quantities, in document order.

        Examples
        --------
        >>> model = CostModel.from_mapping({"a": {"value": 2, "status": "measured"}})
        >>> model.typed_quantities()[0][1].value
        2
        """
        return [(path, Quantity.from_mapping(raw)) for path, raw in self.quantities()]

    def get(self, path: str) -> Any:
        """Return the node at a dotted path inside this model.

        Parameters
        ----------
        path : str
            A dotted path such as ``deployment.country``.

        Returns
        -------
        Any
            The node, or ``None`` when the path names nothing.

        Examples
        --------
        >>> CostModel.from_mapping({"deployment": {"country": "FR"}}).get("deployment.country")
        'FR'
        """
        return resolve_path(self.data, path)

    def status_of(self, path: str) -> str | None:
        """Return the status of the quantity at a dotted path.

        Parameters
        ----------
        path : str
            A dotted path expected to name a quantity.

        Returns
        -------
        str or None
            The status, or ``None`` when the path names no quantity.

        Examples
        --------
        >>> CostModel.from_mapping({"p": {"value": 1, "status": "measured"}}).status_of("p")
        'measured'
        """
        return status_at(self.data, path)

    def unknown_blocks(self) -> tuple[str, ...]:
        """Return the top-level keys this build does not recognise.

        Returns
        -------
        tuple of str
            Unknown top-level keys, sorted. An unknown block is a warning rather
            than an error: a model may legitimately be richer than the tool.

        Examples
        --------
        >>> CostModel.from_mapping({"invented": 1}).unknown_blocks()
        ('invented',)
        """
        known = set(KNOWN_BLOCKS) | {"scenario"}
        return tuple(sorted(key for key in self.data if key not in known))

    def to_yaml(self) -> str:
        r"""Serialise the model to YAML with the block order a reader expects.

        Returns
        -------
        str
            The YAML text, ending in a newline.

        Examples
        --------
        >>> CostModel.from_mapping({"scenarios": [], "schema_version": "2.0"}).to_yaml()
        "schema_version: '2.0'\nscenarios: []\n"
        """
        ordered: dict[str, Any] = {}
        for key in _BLOCK_ORDER:
            if key in self.data:
                ordered[key] = self.data[key]
        for key, value in self.data.items():
            if key not in ordered:
                ordered[key] = value
        return yaml.safe_dump(ordered, sort_keys=False, allow_unicode=True, width=100)

    def save(self, path: str | Path | None = None) -> Path:
        """Write the model back to disk.

        Parameters
        ----------
        path : str or pathlib.Path or None, optional
            Where to write. Defaults to the path the model was loaded from.

        Returns
        -------
        pathlib.Path
            The path written.

        Raises
        ------
        ValueError
            If no path was given and the model was built in memory.

        Examples
        --------
        >>> import tempfile, pathlib
        >>> with tempfile.TemporaryDirectory() as folder:
        ...     out = CostModel.from_mapping({"a": 1}).save(pathlib.Path(folder) / "m.yaml")
        ...     out.name
        'm.yaml'
        """
        target = Path(path) if path is not None else self.path
        if target is None:
            raise ValueError("This model has no path; pass one to save().")
        osh.make_directory(str(target.parent))
        target.write_text(self.to_yaml(), encoding="utf-8")
        self.path = target
        return target
