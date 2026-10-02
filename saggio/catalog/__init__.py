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
>>> row = Catalog.bundled("grid").row("countries", "SE")
>>> row["name"], isinstance(row["carbon_gco2e_per_kwh"], (int, float))
('Sweden', True)
>>> row["carbon_source_url"].startswith("https://")
True

The figure itself is deliberately not shown here. It is a number this package
refreshes, and an example that restated it would be wrong the first time
somebody ran ``saggio catalog refresh grid`` -- which is the whole point of
shipping that command.

Author
------
Warith Harchaoui
"""

from __future__ import annotations

from .refresh import GridRefresh, apply_grid, fetch_grid
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
    "GridRefresh",
    "add_row",
    "apply_grid",
    "carries_numbers",
    "days_since",
    "is_stale",
    "overlay_directory",
    "require_provenance",
    "stale_after_days",
    "expiring_report",
    "fetch_grid",
    "stale_report",
]
