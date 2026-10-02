"""Where each number lives in the model an audit writes.

Module summary
--------------
Every ``derived_from`` entry an audit writes is one of these. They are constants
rather than literals scattered through the code because the validator resolves
them, and a typo in one would surface as a derivation that does not follow --
an error about arithmetic, pointing nowhere near the typo that caused it.

They lost their leading underscore when the auditor became a package. A name
private to one module was the right spelling while there was one module; now
that six of them share these paths, the underscore would have described the old
shape rather than the new one.

Usage example
-------------
>>> from saggio.auditor.paths import POWER_PATH, SCENARIO_NAME
>>> SCENARIO_NAME, POWER_PATH
('as-audited', 'assumptions.power_draw')
>>> RUNTIME_PATH
'scenarios[0].runtime'

Author
------
Warith Harchaoui
"""

from __future__ import annotations

from typing import Final

#: The scenario an audit writes, and the dotted path everything in it derives from.
SCENARIO_NAME: Final[str] = "as-audited"
SCENARIO_PATH: Final[str] = "scenarios[0]"

#: Dotted paths of the assumptions, used to wire up ``derived_from``.
POWER_PATH: Final[str] = "assumptions.power_draw"
PUE_PATH: Final[str] = "assumptions.pue"
PRICE_PATH: Final[str] = "assumptions.electricity_price"
GRID_PATH: Final[str] = "assumptions.grid_carbon_intensity"
LIFETIME_PATH: Final[str] = "assumptions.hardware_lifetime"
EMBODIED_PATH: Final[str] = "assumptions.hardware_embodied_carbon"
WUE_PATH: Final[str] = "assumptions.water_usage_effectiveness"
RUNTIME_PATH: Final[str] = f"{SCENARIO_PATH}.runtime"
IT_ENERGY_PATH: Final[str] = "assumptions.machine_energy"
ENERGY_PATH: Final[str] = f"{SCENARIO_PATH}.costs.energy"

#: The same, inside the block that says what the run would cost on another
#: accelerator. A projected cost names the projected numbers it came from, not
#: the measured ones it did not, or a reader following the trail would arrive at
#: the local machine and wonder why the arithmetic does not work out.
ELSEWHERE_PATH: Final[str] = "projections.on_other_hardware"
PROJECTED_RUNTIME_PATH: Final[str] = f"{ELSEWHERE_PATH}.runtime.result"
PROJECTED_POWER_PATH: Final[str] = f"{ELSEWHERE_PATH}.power_draw"
PROJECTED_IT_ENERGY_PATH: Final[str] = f"{ELSEWHERE_PATH}.machine_energy"
PROJECTED_ENERGY_PATH: Final[str] = f"{ELSEWHERE_PATH}.costs.energy"
