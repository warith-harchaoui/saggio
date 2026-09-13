"""
The starter models that ship with the package.

Module summary
--------------
Two templates, and the choice between them is a choice about what a blank page
should contain. ``minimal`` is a scaffold whose every number is ``TODO``, which is
the only honest state for a model nobody has filled in yet. ``annotated`` is a
worked example with a real arithmetic chain, so a reader can see what a finished
model looks like before writing their own.

They are read through :mod:`importlib.resources`, so they are found identically in
a checkout and in an installed wheel. An earlier design walked up from the module
file to find files that lived outside the package, which worked in a checkout and
silently failed, or found someone else's files, anywhere else.

Usage example
-------------
>>> from saggio.templates import template_text
>>> "unit_of_work" in template_text("minimal")
True

Author
------
Warith Harchaoui
"""

from __future__ import annotations

from importlib import resources
from typing import Any, Final

import yaml

#: The templates that ship with the package, with a sentence on when to use each.
TEMPLATES: Final[dict[str, str]] = {
    "minimal": "A scaffold with every number left open, for starting from nothing.",
    "annotated": "A worked example with a real arithmetic chain and notes on every field.",
}

#: The template used when a caller expresses no preference.
DEFAULT_TEMPLATE: Final[str] = "minimal"


def template_names() -> tuple[str, ...]:
    """Return the available template names.

    Returns
    -------
    tuple of str
        The names, sorted.

    Examples
    --------
    >>> template_names()
    ('annotated', 'minimal')
    """
    return tuple(sorted(TEMPLATES))


def template_text(name: str = DEFAULT_TEMPLATE) -> str:
    """Return a template's YAML text.

    Parameters
    ----------
    name : str, optional
        A template name.

    Returns
    -------
    str
        The template as shipped.

    Raises
    ------
    ValueError
        If the name is not one of the templates, listing the ones that are.

    Examples
    --------
    >>> template_text("annotated").startswith("#")
    True
    >>> template_text("fancy")
    Traceback (most recent call last):
        ...
    ValueError: Unknown template 'fancy'. Available: annotated, minimal.
    """
    if name not in TEMPLATES:
        available = ", ".join(template_names())
        raise ValueError(f"Unknown template {name!r}. Available: {available}.")
    return resources.files("saggio.data").joinpath("templates", f"{name}.yaml").read_text("utf-8")


def template_mapping(name: str = DEFAULT_TEMPLATE) -> dict[str, Any]:
    """Return a template already parsed.

    Parameters
    ----------
    name : str, optional
        A template name.

    Returns
    -------
    dict
        The parsed model.

    Examples
    --------
    >>> template_mapping("minimal")["schema_version"]
    '2.0'
    """
    return yaml.safe_load(template_text(name))
