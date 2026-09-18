"""
Estimation: from a machine, a place, and a runtime to a cost.

Module summary
--------------
Everything here turns facts into numbers, and every number it produces says how
it was arrived at. :mod:`machine` asks the operating system what hardware this
is; :mod:`context` resolves where the code runs and what that place charges and
emits; :mod:`energy` applies the Green Algorithms chain from power and time to
energy, carbon, water, and money; :mod:`equivalences` restates a carbon figure
in tree-months, car kilometres, and reference flights so a reader can feel its
size; :mod:`extrapolate` projects a measured slice to a whole run, and one
machine's run to another's.

Usage example
-------------
>>> from saggio.estimate import DeploymentContext, energy_from_runtime
>>> from saggio.model import Quantity
>>> context = DeploymentContext.build(country="FR")
>>> runtime = Quantity(value=3600.0, unit="s", status="measured")
>>> power = Quantity(value=100.0, unit="W", status="estimated")
>>> round(energy_from_runtime(runtime, power, context.pue()).value, 4)
0.15

Author
------
Warith Harchaoui
"""

from __future__ import annotations

from .context import (
    CATALOG_CURRENCY,
    COUNTRY_ENVIRONMENT_VARIABLE,
    DEFAULT_PROVIDER,
    DeploymentContext,
    country_from_timezone,
    local_timezone_name,
)
from .energy import (
    GREEN_ALGORITHMS_SOURCE,
    MEMORY_POWER_W_PER_GB,
    carbon_from_energy,
    energy_from_runtime,
    facility_energy,
    it_energy_from_runtime,
    money_from_energy,
    node_power,
    total_money,
    water_from_energy,
)
from .equivalences import (
    CAR_GCO2_PER_KM,
    FLIGHT_GCO2,
    TREE_MONTH_GCO2,
    car_km,
    equivalences,
    flight_fraction,
    tree_months,
)
from .extrapolate import (
    DEFAULT_PRECISION,
    THROUGHPUT_PRECISIONS,
    Projection,
    project_to_completion,
    project_to_machine,
)
from .machine import MachineProfile, detect_machine

__all__ = [
    "CAR_GCO2_PER_KM",
    "CATALOG_CURRENCY",
    "COUNTRY_ENVIRONMENT_VARIABLE",
    "DEFAULT_PRECISION",
    "DEFAULT_PROVIDER",
    "FLIGHT_GCO2",
    "GREEN_ALGORITHMS_SOURCE",
    "MEMORY_POWER_W_PER_GB",
    "THROUGHPUT_PRECISIONS",
    "TREE_MONTH_GCO2",
    "DeploymentContext",
    "MachineProfile",
    "Projection",
    "car_km",
    "carbon_from_energy",
    "country_from_timezone",
    "detect_machine",
    "energy_from_runtime",
    "equivalences",
    "flight_fraction",
    "facility_energy",
    "it_energy_from_runtime",
    "local_timezone_name",
    "money_from_energy",
    "node_power",
    "project_to_completion",
    "project_to_machine",
    "total_money",
    "tree_months",
    "water_from_energy",
]
