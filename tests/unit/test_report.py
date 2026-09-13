"""Reports: what they show, and what they refuse to make look like a number."""

from __future__ import annotations

import json
import re
from typing import Any

import pytest

from saggio.model import Quantity
from saggio.report.figures import (
    count_statuses,
    derivation_chain,
    derivation_edges,
    honesty_bar,
    scenario_energy,
)
from saggio.report.html import render_html, translations
from saggio.report.markdown import (
    NOT_KNOWN,
    format_number,
    format_quantity,
    render_markdown,
)
from saggio.report.office import render_office
from saggio.templates import template_mapping

# --- Formatting --------------------------------------------------------------


@pytest.mark.parametrize(
    ("value", "expected"),
    [(1234.5678, "1235"), (2.5e-05, "2.5e-05"), (0, "0"), (0.0, "0"), (None, NOT_KNOWN)],
)
def test_numbers_are_shown_without_false_precision(value: float | None, expected: str) -> None:
    assert format_number(value) == expected


def test_a_quantity_is_shown_with_its_unit() -> None:
    assert format_quantity(Quantity(value=1.5, unit="kWh", status="measured")) == "1.5 kWh"


def test_money_is_shown_in_its_currency() -> None:
    assert format_quantity(Quantity(value=2.0, currency="EUR", status="measured")) == "2 EUR"


def test_an_absent_number_says_so_rather_than_showing_a_zero() -> None:
    # A blank invites a reader to fill it in themselves with something optimistic.
    assert format_quantity(Quantity(status="TODO")) == NOT_KNOWN


# --- Markdown ----------------------------------------------------------------


def test_the_markdown_report_leads_with_the_verdict(sound_model: dict[str, Any]) -> None:
    report = render_markdown(sound_model)
    assert report.startswith("# Cost of running")
    assert "weakest number" in report


def test_every_cost_row_carries_its_status(sound_model: dict[str, Any]) -> None:
    report = render_markdown(sound_model)
    for line in report.splitlines():
        if line.startswith("| Energy ") or line.startswith("| Money "):
            assert "`estimated`" in line


def test_a_dimension_the_project_registered_appears_by_itself() -> None:
    report = render_markdown(template_mapping("annotated"))
    assert "Network egress" in report


def test_the_report_never_runs_three_blank_lines_together(sound_model: dict[str, Any]) -> None:
    assert "\n\n\n" not in render_markdown(sound_model)


def test_a_pipe_in_a_note_cannot_break_a_table(sound_model: dict[str, Any]) -> None:
    sound_model["assumptions"]["power_draw"]["notes"] = "a | b"
    assert "a \\| b" in render_markdown(sound_model)


def test_an_empty_model_still_renders() -> None:
    assert render_markdown({}).startswith("# Cost of running")


def test_the_services_section_says_where_to_price_them() -> None:
    report = render_markdown(template_mapping("annotated"))
    assert "Where to price it" in report
    assert "openai.com/api/pricing" in report


# --- Figures -----------------------------------------------------------------


def test_the_honesty_bar_counts_every_quantity(sound_model: dict[str, Any]) -> None:
    counts = count_statuses(sound_model)
    assert counts["measured"] + counts["estimated"] == sum(counts.values())


def test_the_honesty_bar_is_described_for_a_reader_who_cannot_see_it() -> None:
    svg = honesty_bar({"measured": 2, "estimated": 1, "placeholder": 0, "TODO": 0})
    assert "<desc" in svg and "2 measured" in svg


def test_an_empty_model_draws_an_empty_bar() -> None:
    assert honesty_bar({}).count("<rect") == 0


def test_the_derivation_graph_is_read_from_the_model_not_assumed() -> None:
    edges = derivation_edges(
        {
            "e": {"value": 1, "status": "measured", "derived_from": ["r"]},
            "r": {"value": 1, "status": "measured"},
        }
    )
    assert edges == {"e": ("r",), "r": ()}


def test_a_derivation_naming_something_absent_is_left_out_of_the_graph() -> None:
    edges = derivation_edges({"e": {"value": 1, "status": "measured", "derived_from": ["gone"]}})
    assert edges == {"e": ()}


def test_a_model_that_derives_nothing_draws_no_graph() -> None:
    assert derivation_chain({"a": {"value": 1, "status": "measured"}}) == ""


def test_the_graph_colours_every_node_by_its_status(sound_model: dict[str, Any]) -> None:
    svg = derivation_chain(sound_model)
    assert "var(--measured)" in svg and "var(--estimated)" in svg


def test_the_what_if_baseline_comes_from_the_model_or_not_at_all() -> None:
    assert scenario_energy(template_mapping("annotated")).is_known()
    assert not scenario_energy({}).is_known()


# --- HTML --------------------------------------------------------------------


def test_the_page_is_a_complete_document() -> None:
    page = render_html(template_mapping("annotated"))
    assert page.startswith("<!doctype html>")
    assert page.rstrip().endswith("</html>")


def test_the_page_makes_no_request_to_anybody() -> None:
    page = render_html(template_mapping("annotated"))
    # Every src and href that is not a data URI must be a link a reader clicks,
    # never something the page fetches to render itself.
    for match in re.finditer(r'src="([^"]+)"', page):
        assert match.group(1).startswith("data:")
    assert '<link rel="icon" href="data:image/png;base64,' in page


def test_the_page_carries_its_data_as_json_not_as_a_javascript_literal() -> None:
    # The earlier design pasted a translation table into a JavaScript string and
    # the first French apostrophe closed it, silently killing every control.
    page = render_html(template_mapping("annotated"))
    blob = re.search(r'<script type="application/json" id="report-data">(.*?)</script>', page, re.S)
    assert blob is not None
    payload = json.loads(blob.group(1).replace("<\\/", "</"))
    assert "fr" in payload["i18n"]
    assert payload["machine_energy_kwh"] is not None


def test_french_apostrophes_survive_the_round_trip() -> None:
    page = render_html(template_mapping("annotated"))
    blob = re.search(r'<script type="application/json" id="report-data">(.*?)</script>', page, re.S)
    assert blob is not None
    payload = json.loads(blob.group(1).replace("<\\/", "</"))
    assert "n'est" in payload["i18n"]["fr"]["whatif.note"]


def test_the_translation_table_has_the_same_keys_in_every_language() -> None:
    tables = translations()
    reference = set(tables["en"])
    for code, table in tables.items():
        assert set(table) == reference, f"{code} is missing keys"


def test_the_page_declares_both_themes() -> None:
    page = render_html(template_mapping("annotated"))
    assert "prefers-color-scheme: dark" in page
    assert '[data-theme="dark"]' in page


def test_a_model_with_no_baseline_gets_no_what_if_panel(sound_model: dict[str, Any]) -> None:
    # A what-if built on an invented baseline would be the worst number on the page.
    assert '<select id="whatif-country"' not in render_html(sound_model)


def test_a_model_with_a_baseline_gets_one() -> None:
    assert '<select id="whatif-country"' in render_html(template_mapping("annotated"))


def test_markup_in_a_model_cannot_escape_into_the_page(sound_model: dict[str, Any]) -> None:
    sound_model["project"] = {"name": "<script>alert(1)</script>"}
    page = render_html(sound_model)
    assert "<script>alert(1)</script>" not in page
    assert "&lt;script&gt;" in page


def test_an_empty_model_still_renders_a_page() -> None:
    assert render_html({}).startswith("<!doctype html>")


# --- Office ------------------------------------------------------------------


def test_an_unknown_office_format_is_refused_by_name() -> None:
    with pytest.raises(ValueError, match="Unknown output format"):
        render_office({}, "out.odt", output_format="odt")
