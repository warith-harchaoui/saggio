"""
The data that ships with the package.

Module summary
--------------
Two kinds of file live here. The **catalogues** hold facts about the world that a
cost model needs and cannot measure: what hardware draws, what grids emit, what
datacenters add, where services publish their prices. The **templates** hold
starter cost models.

This is a real package rather than a bare directory so that
:mod:`importlib.resources` finds the files the same way in a source checkout and
in an installed wheel, and so that packaging cannot quietly leave them out.

Usage example
-------------
>>> from importlib import resources
>>> catalogues = resources.files("running_code_cost_helper.data")
>>> "gpus:" in catalogues.joinpath("hardware.yaml").read_text("utf-8")
True

Author
------
Warith Harchaoui
"""

from __future__ import annotations
