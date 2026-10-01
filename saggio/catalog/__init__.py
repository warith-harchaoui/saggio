"""
The catalogues: facts about the world that a cost model needs and cannot measure.

Module summary
--------------
What a GPU draws, what a kilowatt-hour emits in a given country, what overhead a
datacenter adds, and where an API publishes its prices are facts this package
looks up rather than computes. They live in provenance-carrying YAML, shipped
with the package and extensible per user, and they expire on a schedule that
matches how fast each kind of fact actually moves.

Usage example
-------------
>>> from saggio.catalog import Catalog
>>> Catalog.bundled("grid").row("countries", "SE")["carbon_gco2e_per_kwh"]
13

Author
------
Warith Harchaoui
"""

from __future__ import annotations

from .registry import (
    BUNDLED_CATALOGS,
    DEFAULT_STALE_AFTER_DAYS,
    INTERNAL_DEFAULT_SOURCE,
    SECTION_OF_KIND,
    STALE_AFTER_DAYS,
    Catalog,
    add_row,
    carries_numbers,
    days_since,
    expiring_report,
    is_stale,
    overlay_directory,
    require_provenance,
    stale_after_days,
    stale_report,
)

__all__ = [
    "BUNDLED_CATALOGS",
    "DEFAULT_STALE_AFTER_DAYS",
    "INTERNAL_DEFAULT_SOURCE",
    "SECTION_OF_KIND",
    "STALE_AFTER_DAYS",
    "Catalog",
    "add_row",
    "carries_numbers",
    "days_since",
    "is_stale",
    "overlay_directory",
    "require_provenance",
    "stale_after_days",
    "expiring_report",
    "stale_report",
]
