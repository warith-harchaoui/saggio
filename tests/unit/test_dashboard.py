"""The dashboard: several models on one page, compared only where that is honest."""

from __future__ import annotations

import pytest

from saggio.report.dashboard import render_dashboard
from saggio.templates import template_mapping


def _named(name: str) -> dict:
    model = template_mapping("annotated")
    model["project"]["name"] = name
    return model


def test_a_dashboard_of_nothing_is_refused() -> None:
    with pytest.raises(ValueError, match="at least one"):
        render_dashboard([])


def test_every_project_appears_by_name() -> None:
    page = render_dashboard([_named("alpha"), _named("beta")])
    assert "alpha" in page and "beta" in page


def test_a_nameless_model_is_shown_as_such_not_dropped() -> None:
    model = template_mapping("annotated")
    model.pop("project", None)
    page = render_dashboard([model])
    assert "unnamed project 1" in page


def test_the_page_leads_with_the_honesty_comparison() -> None:
    page = render_dashboard([_named("alpha"), _named("beta")])
    assert "How well founded each model is" in page
    assert page.index("How well founded") < page.index("What one unit costs")


def test_the_page_says_rows_do_not_compare() -> None:
    # Each project defines its own unit of work; a dashboard that let bar
    # lengths imply a ranking across projects would be lying politely.
    page = render_dashboard([_named("alpha")])
    assert "do not compare" in page
    assert 'data-i18n="dashboard.lede"' in page


def test_the_page_is_self_contained() -> None:
    page = render_dashboard([_named("alpha")])
    assert page.startswith("<!doctype html>")
    assert 'id="report-data"' in page


def test_markup_in_a_project_name_cannot_escape_into_the_page() -> None:
    page = render_dashboard([_named("<script>alert(1)</script>")])
    assert "<script>alert(1)</script>" not in page
