"""
The model layer: what a cost model means, and what makes one honest.

Module summary
--------------
This package is the pure heart of saggio. It defines the
honesty taxonomy, the quantity that carries a number together with how far it can
be trusted, the dimensions a model reports on, the schema contract, the navigation
over a parsed model, and the validation that turns all of it from convention into
rule.

Nothing here touches a network, a subprocess, or a delivery surface. Every other
part of the package, and every adapter over it, builds on this one definition of
what a cost model *is*.

Usage example
-------------
>>> from saggio.model import CostModel, validate
>>> validate(CostModel.from_mapping({"scenarios": []})).ok
False

Author
------
Warith Harchaoui
"""

from __future__ import annotations

from .cost_model import (
    CostModel,
    resolve_path,
    status_at,
    walk_bare_numbers,
    walk_quantities,
)
from .dimensions import (
    CANONICAL_DIMENSIONS,
    CARBON,
    ENERGY,
    MONEY,
    TIME,
    WATER,
    Dimension,
    DimensionRegistry,
    registry_for,
)
from .quantity import (
    AGGREGATOR,
    FIRST_PARTY,
    QUANTITY_KEYS,
    SOURCE_KINDS,
    STATED,
    Quantity,
    is_valid_source_kind,
    looks_like_quantity,
    source_strength,
)
from .results import Issue, Report, Severity
from .schema import (
    KNOWN_BLOCKS,
    OPTIONAL_BLOCKS,
    REQUIRED_BLOCKS,
    SCHEMA_VERSION,
    is_bare_number_exempt,
    schema_major,
)
from .taxonomy import (
    ALLOWED_STATUSES,
    ESTIMATED,
    MEASURED,
    PLACEHOLDER,
    STATUS_MEANING,
    STATUS_ORDER,
    TODO,
    is_valid_status,
    overclaims,
    status_strength,
    weakest,
)
from .validate import FRESHNESS_WARN_DAYS, overall_status, validate

__all__ = [
    # Taxonomy.
    "ALLOWED_STATUSES",
    "MEASURED",
    "ESTIMATED",
    "PLACEHOLDER",
    "TODO",
    "STATUS_ORDER",
    "STATUS_MEANING",
    "is_valid_status",
    "status_strength",
    "weakest",
    "overclaims",
    # Quantity.
    "Quantity",
    "QUANTITY_KEYS",
    "SOURCE_KINDS",
    "STATED",
    "FIRST_PARTY",
    "AGGREGATOR",
    "is_valid_source_kind",
    "source_strength",
    "looks_like_quantity",
    # Dimensions.
    "Dimension",
    "DimensionRegistry",
    "CANONICAL_DIMENSIONS",
    "MONEY",
    "TIME",
    "ENERGY",
    "CARBON",
    "WATER",
    "registry_for",
    # Schema.
    "SCHEMA_VERSION",
    "REQUIRED_BLOCKS",
    "OPTIONAL_BLOCKS",
    "KNOWN_BLOCKS",
    "schema_major",
    "is_bare_number_exempt",
    # Navigation.
    "CostModel",
    "walk_quantities",
    "walk_bare_numbers",
    "resolve_path",
    "status_at",
    # Verdicts.
    "Issue",
    "Report",
    "Severity",
    "validate",
    "overall_status",
    "FRESHNESS_WARN_DAYS",
]
