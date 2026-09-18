"""
Reports: the same model, rendered for whoever has to read it.

Module summary
--------------
A cost model is a YAML file, which is the right thing to commit and the wrong
thing to hand to anybody. Four renderings exist because four audiences do.
:mod:`markdown` is the one that renders in a pull request. :mod:`html` is the one
you send to somebody who is not going to open a terminal: a single self-contained
page, offline, themed, translated, with a panel that recomputes the model for a
different country. :mod:`office` is the one that goes into a report nobody chose
the format of. :mod:`dashboard` is the team view: every committed model on one
page, compared only where a comparison is honest.

Usage example
-------------
>>> from saggio.report import render_markdown
>>> from saggio.templates import template_mapping
>>> render_markdown(template_mapping("minimal")).startswith("# Cost of running")
True

Author
------
Warith Harchaoui
"""

from __future__ import annotations

from .dashboard import render_dashboard
from .figures import (
    count_statuses,
    derivation_chain,
    honesty_bar,
    honesty_overview,
    location_impact,
    scenario_energy,
)
from .html import PROJECT_URL, render_html, translations
from .markdown import NOT_KNOWN, format_number, format_quantity, render_markdown
from .office import OFFICE_FORMATS, md2star_available, render_office

__all__ = [
    "NOT_KNOWN",
    "OFFICE_FORMATS",
    "PROJECT_URL",
    "count_statuses",
    "derivation_chain",
    "format_number",
    "format_quantity",
    "honesty_bar",
    "honesty_overview",
    "location_impact",
    "md2star_available",
    "render_dashboard",
    "render_html",
    "render_markdown",
    "render_office",
    "scenario_energy",
    "translations",
]
