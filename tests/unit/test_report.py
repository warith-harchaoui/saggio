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
    honesty_overview,
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
    # Grouped, because both languages this package writes group: `1,235` in
    # English and `1 235` in French, from one rule in `saggio.i18n.number`.
    [(1234.5678, "1,235"), (2.5e-05, "2.5e-05"), (0, "0"), (0.0, "0"), (None, NOT_KNOWN)],
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


def _overview_legend(svg: str) -> list[str]:
    """The status names the overview's legend prints, in order."""
    return re.findall(r'fill="var\(--ink-soft\)">(\w+)</text>', svg)


def test_the_overview_legend_names_only_what_it_draws() -> None:
    """A swatch for a status no bar uses sends a reader hunting for a colour.

    The single-model bar has always skipped an empty status; the overview drew
    all four unconditionally, so every dashboard carried a `placeholder` key
    with nothing on the chart to match it. Most models have no placeholder at
    all, which made it the usual offender.
    """
    legend = _overview_legend(
        honesty_overview(
            [
                ("alpha", {"measured": 2, "estimated": 3, "TODO": 1}),
                ("gamma", {"measured": 1, "TODO": 5}),
            ]
        )
    )
    assert "placeholder" not in legend
    assert legend[-3:] == ["measured", "estimated", "TODO"]


def test_the_overview_legend_keeps_a_status_some_row_does_draw() -> None:
    """The other direction, which is the one worth pinning.

    A rule that hides an empty status is one edit away from hiding a full one,
    and the figure would still look plausible.
    """
    legend = _overview_legend(
        honesty_overview(
            [
                ("alpha", {"measured": 2, "estimated": 3, "TODO": 1}),
                ("beta", {"estimated": 4, "placeholder": 2}),
            ]
        )
    )
    assert "placeholder" in legend


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


# --- Projections reach the page ----------------------------------------------


def _model_with_a_projection() -> dict[str, Any]:
    """A model carrying what the run would cost on another accelerator."""
    # `_projections` moved into the module that owns it when the auditor became
    # a package. The public surface did not move; this is a private name, and a
    # test reaching for one points at where it lives.
    from saggio.auditor import AuditOptions
    from saggio.auditor.projections import _projections
    from saggio.estimate.machine import MachineProfile

    block, _ = _projections(
        {},
        Quantity(value=3600.0, unit="s", status="measured"),
        None,
        MachineProfile("linux"),
        AuditOptions(source_accelerator="RTX-4090", target_accelerator="H100"),
        compute_bound=True,
        site={
            "pue": Quantity(value=1.2, unit="ratio", status="estimated"),
            "electricity_price": Quantity(
                value=0.24, unit="USD/kWh", currency="USD", status="estimated"
            ),
            "grid_carbon_intensity": Quantity(value=56, unit="gCO2e/kWh", status="estimated"),
        },
    )
    return {"schema_version": "2.1", "scenarios": [], "projections": block}


def test_the_markdown_report_shows_what_the_run_would_cost_elsewhere() -> None:
    # The projected cost was invisible in the report for as long as the renderer
    # knew only one of the two shapes a projections block holds.
    text = render_markdown(_model_with_a_projection())
    assert "Projections" in text
    assert "money" in text and "carbon" in text
    assert "held constant" in text.lower() or "tariff" in text


def test_the_markdown_report_shows_the_bracket_not_only_the_point() -> None:
    text = render_markdown(_model_with_a_projection())
    assert "bracketed" in text


def test_the_html_report_has_a_projections_section_at_all() -> None:
    # The translations carried a heading for this section long before the page
    # had one, which is how a whole feature stays invisible to everyone who does
    # not read YAML.
    page = render_html(_model_with_a_projection())
    assert 'data-i18n="section.projections"' in page
    assert "H100" in page


def test_the_html_report_names_what_the_projection_held_constant() -> None:
    page = render_html(_model_with_a_projection())
    assert "tariff" in page


# --- Felt size: carbon restated so a reader can feel it ------------------------


def _scenario_with_carbon(grams: float | None, status: str = "estimated") -> dict[str, Any]:
    """A minimal model whose one scenario states a carbon figure."""
    quantity: dict[str, Any] = {"unit": "gCO2e", "status": status}
    if grams is not None:
        quantity["value"] = grams
    return {
        "schema_version": "2.1",
        "scenarios": [{"name": "one call", "costs": {"carbon": quantity}}],
    }


def test_a_small_carbon_figure_is_restated_per_million_units() -> None:
    # A millionth of a tree-month tells the reader nothing, so the sentence
    # scales up and says that it did.
    text = render_markdown(_scenario_with_carbon(1.4))
    assert "A million units emit about" in text
    assert "tree-months" in text
    assert "km by car" in text


def test_a_large_carbon_figure_is_restated_per_unit() -> None:
    # The paper's GEANT4-DNA study: 544 kg CO2e reads as thousands of km driven.
    text = render_markdown(_scenario_with_carbon(544_115.0))
    assert "One unit emits about" in text


def test_an_open_carbon_figure_is_not_restated() -> None:
    # A TODO restated as trees would still be a TODO; the table already says so.
    text = render_markdown(_scenario_with_carbon(None, status="TODO"))
    assert "tree-months" not in text


def test_the_restatement_names_its_source() -> None:
    assert "doi.org/10.1002/advs.202100707" in render_markdown(_scenario_with_carbon(1.4))


def _scenario_with_both_scope_two_figures() -> dict[str, Any]:
    """A model reporting scope 2 both ways, the two figures far apart."""
    model = _scenario_with_carbon(1.4)
    model["scenarios"][0]["costs"]["carbon_market_based"] = {
        "value": 14.0,
        "unit": "gCO2e",
        "status": "estimated",
    }
    return model


def test_the_restatement_says_which_scope_2_figure_it_restated() -> None:
    """Two carbon figures on a page, one set of kilometres, no label.

    The equivalences have always restated ``carbon``, which is correct and was
    unambiguous while it was the only carbon in the table. Beside a market-based
    figure it is not: the two can differ by a factor of ten, so a reader seeing
    one number of kilometres has no way to know which one it came from — and the
    restatement is the line in the report a non-specialist actually reads.
    """
    both = render_markdown(_scenario_with_both_scope_two_figures())
    assert "estimated restatements of the location-based figure" in both

    # And nothing changes on the ordinary model, where the qualifier would be
    # a sentence answering a question nobody could have asked.
    alone = render_markdown(_scenario_with_carbon(1.4))
    assert "estimated restatements, " in alone
    assert "location-based figure" not in alone


def test_the_html_restatement_labels_the_half_it_restated_translatably() -> None:
    page = render_html(_scenario_with_both_scope_two_figures())
    assert 'data-i18n="equivalence.note.located"' in page
    assert 'data-i18n="equivalence.note"' in render_html(_scenario_with_carbon(1.4))


def test_the_html_report_restates_carbon_with_translatable_labels() -> None:
    page = render_html(_scenario_with_carbon(1.4))
    assert 'data-i18n="equivalence.unit.million"' in page
    assert 'data-i18n="equivalence.trees"' in page


def test_every_language_translates_the_equivalence_labels() -> None:
    # The picker is built from the i18n file, so a missing key would silently
    # leave one language showing English mid-sentence.
    for language, table in translations().items():
        for key in (
            "equivalence.trees",
            "equivalence.car",
            "equivalence.note",
            "equivalence.note.located",
            "equivalence.unit.one",
            "equivalence.unit.million",
        ):
            assert key in table, f"{language} is missing {key}"


# --- The location panel ---------------------------------------------------------


def _grid_rows(count: int = 12) -> dict[str, dict[str, Any]]:
    """A synthetic grid catalogue spanning clean to dirty."""
    return {
        f"C{index}": {"name": f"Country {index}", "carbon_gco2e_per_kwh": 30 + 60 * index}
        for index in range(count)
    }


def test_the_location_panel_needs_something_to_compare() -> None:
    from saggio.report.figures import location_impact

    assert location_impact({}) == ""
    assert location_impact({"SE": {"name": "Sweden", "carbon_gco2e_per_kwh": 30}}) == ""


def test_the_location_panel_spans_the_range_and_keeps_the_readers_country() -> None:
    from saggio.report.figures import location_impact

    svg = location_impact(_grid_rows(), current="C5")
    # The cleanest and dirtiest grids anchor the scale, and the reader's own
    # country is always drawn, in the accent colour.
    assert "Country 0" in svg and "Country 11" in svg
    assert "Country 5" in svg
    assert "var(--accent)" in svg


def test_the_location_panel_names_its_polarity() -> None:
    from saggio.report.figures import location_impact

    assert "lower is better" in location_impact(_grid_rows())


def test_the_location_panel_escapes_country_names() -> None:
    from saggio.report.figures import location_impact

    rows = {
        "XX": {"name": "<script>alert(1)</script>", "carbon_gco2e_per_kwh": 100},
        "SE": {"name": "Sweden", "carbon_gco2e_per_kwh": 30},
    }
    svg = location_impact(rows)
    assert "<script>" not in svg


def test_the_whatif_card_carries_the_location_panel() -> None:
    model = template_mapping("annotated")
    page = render_html(model)
    if 'id="whatif-country"' in page:
        assert "How the location moves the carbon" in page


# --- Holes the third audit found, kept closed -----------------------------------


def test_a_hostile_source_url_cannot_break_a_markdown_table() -> None:
    from saggio.report.markdown import _source_cell

    cell = _source_cell(Quantity(source_url="https://x.invalid/a)b|c", retrieved_date="2026-01-01"))
    assert "|" not in cell.replace("\\|", "")
    assert "%29" in cell and "%7C" in cell


def test_a_newline_in_the_project_name_cannot_inject_a_heading() -> None:
    text = render_markdown({"project": {"name": "x\n# fake"}, "scenarios": []})
    assert text.splitlines()[0].startswith("# Cost of running x")
    assert "\n# fake" not in text


def test_the_location_panel_survives_zero_and_garbage_intensities() -> None:
    from saggio.report.figures import location_impact

    zeros = {
        "A": {"name": "A", "carbon_gco2e_per_kwh": 0},
        "B": {"name": "B", "carbon_gco2e_per_kwh": 0},
    }
    assert location_impact(zeros) == ""
    mixed = {
        "A": {"name": "A", "carbon_gco2e_per_kwh": "n/a"},
        "SE": {"name": "Sweden", "carbon_gco2e_per_kwh": 30},
        "AU": {"name": "Australia", "carbon_gco2e_per_kwh": 580},
    }
    svg = location_impact(mixed)
    assert "Sweden" in svg and "n/a" not in svg


def test_a_long_row_label_is_trimmed_into_its_column() -> None:
    from saggio.report.figures import _row_label

    display, size = _row_label("A" * 49)
    assert display.endswith("…") and len(display) <= 26
    assert size < 13


def test_the_html_report_shows_how_it_was_measured() -> None:
    page = render_html(
        {
            "schema_version": "2.1",
            "scenarios": [],
            "measurement": {
                "command": ["python", "train.py"],
                "warnings": ["profiler attached"],
            },
        }
    )
    assert 'data-i18n="section.measurement"' in page
    assert "train.py" in page and "profiler attached" in page


def test_the_dashboard_speaks_with_its_own_i18n_keys() -> None:
    from saggio.report.dashboard import render_dashboard

    page = render_dashboard([template_mapping("annotated")])
    assert 'data-i18n="dashboard.honesty"' in page
    assert 'data-i18n="dashboard.column.project"' in page
    assert 'data-i18n="section.honesty"' not in page


def _model_reporting_scope_two_both_ways() -> dict[str, Any]:
    """A model on a machine its owner operates, reporting scope 2 both ways.

    The provider is what turns the inventory section on at all, and both figures
    carrying a number is what turns its lead sentence from the shopping list
    into the one about the whole pair.
    """
    return {
        "schema_version": "2.1",
        "deployment": {"provider": "on-prem", "country": "FR"},
        "scenarios": [
            {
                "name": "one call",
                "costs": {
                    "carbon": {"value": 1.4, "unit": "gCO2e", "status": "estimated"},
                    "carbon_market_based": {
                        "value": 14.0,
                        "unit": "gCO2e",
                        "status": "estimated",
                    },
                },
            }
        ],
    }


def test_every_data_i18n_key_in_both_pages_exists_in_every_language() -> None:
    # An orphan key fails silently: the node just stays English.
    import re

    from saggio.report.dashboard import render_dashboard

    model = template_mapping("annotated")
    model["measurement"] = {"command": ["x"]}
    # Plus the pages only a whole scope 2 pair produces. Those branches swap one
    # key for another, so rendering the ordinary model alone would leave their
    # replacements unvisited here and orphanable in silence.
    pages = (
        render_html(model)
        + render_dashboard([model])
        + render_html(_scenario_with_both_scope_two_figures())
        + render_html(_model_reporting_scope_two_both_ways())
    )
    used = set(re.findall(r'data-i18n="([^"]+)"', pages))
    for language, table in translations().items():
        missing = used - set(table)
        assert not missing, f"{language} is missing {sorted(missing)}"


# --- Durations read the way somebody would say them ---------------------------


def test_a_long_duration_is_not_spelled_in_scientific_notation() -> None:
    # `1.087e+04 s` is three hours. A package whose argument is that a figure
    # should be legible has no business printing the first spelling.
    from saggio.report import format_duration

    assert format_duration(10870.4) == "3 h 1 min (10,870.4 s)"
    assert "e+" not in format_duration(10870.4)


def test_a_short_duration_takes_the_prefix_a_reader_thinks_in() -> None:
    from saggio.report import format_duration

    assert format_duration(0.0272) == "27.2 ms"
    assert format_duration(2.5e-07) == "250 ns"
    assert format_duration(1.5e-06) == "1.5 µs"


def test_the_exact_seconds_stay_beside_the_readable_form() -> None:
    # A reader checking the report against the model needs the figure the model
    # holds, so the spelled form never replaces it — it precedes it. Written the
    # way the reader's language writes it, which is the ruling already made about
    # the decimal separator: the file holds a float for a machine to read, and
    # the report holds a number for a person to read.
    from saggio.report import format_duration

    assert "(90 s)" in format_duration(90)
    assert "(190,800 s)" in format_duration(190800)


def test_a_quantity_in_seconds_is_rendered_as_a_duration() -> None:
    from saggio.model import Quantity
    from saggio.report import format_quantity

    assert format_quantity(Quantity(value=10870.4, unit="s", status="estimated")).startswith("3 h")
    # And nothing else is: a figure in kWh is not a duration.
    energy = Quantity(value=10870.4, unit="kWh", status="estimated")
    assert format_quantity(energy) == "1.087e+04 kWh"


def test_both_reports_spell_a_projected_duration_the_same_way() -> None:
    # Two surfaces may not answer the same question differently.
    from pathlib import Path

    import yaml

    from saggio.model import CostModel
    from saggio.report import render_html, render_markdown

    root = Path(__file__).resolve().parents[2]
    data = yaml.safe_load((root / "examples/render.yaml").read_text(encoding="utf-8"))
    model = CostModel.from_mapping(data)
    for page in (render_markdown(model), render_html(model)):
        assert "3 h 1 min" in page, "a projected whole run is hours, and should say so"


# --- Contrast, measured rather than eyeballed --------------------------------


def _contrast(foreground: str, background: str) -> float:
    """Return the WCAG 2.x contrast ratio between two hex colours."""

    def channel(value: float) -> float:
        value /= 255
        return value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4

    def luminance(colour: str) -> float:
        colour = colour.lstrip("#")
        red, green, blue = (int(colour[i : i + 2], 16) for i in (0, 2, 4))
        return 0.2126 * channel(red) + 0.7152 * channel(green) + 0.0722 * channel(blue)

    first, second = luminance(foreground), luminance(background)
    return (max(first, second) + 0.05) / (min(first, second) + 0.05)


def test_the_muted_text_a_reader_most_needs_is_readable() -> None:
    """`--ink-faint` carries the uncertainty, and used to be the least legible.

    It colours `th`, `td.unknown`, `.muted` and the what-if labels — every
    place the report says a figure is weak or missing. At #86867c it was
    3.55:1 against the page, below the 4.5:1 WCAG AA needs for text that size.
    The colour marking a number you should trust less was the hardest to read.
    """
    import importlib.resources

    css = importlib.resources.files("saggio.data.report").joinpath("report.css").read_text("utf-8")
    faint = re.findall(r"--ink-faint:\s*(#[0-9a-f]{6})", css)
    assert len(faint) == 3, "one light value and two dark declarations"
    light, dark = faint[0], faint[1]
    # The darkest surface each one ever sits on, which is what decides it.
    assert _contrast(light, "#f4f4f2") >= 4.5, f"{light} is unreadable on the sunken surface"
    assert _contrast(dark, "#232419") >= 4.5, f"{dark} is unreadable on the sunken surface"


def test_the_estimated_badge_is_readable_on_its_own_background() -> None:
    import importlib.resources

    css = importlib.resources.files("saggio.data.report").joinpath("report.css").read_text("utf-8")
    ink = re.search(r"--estimated:\s*(#[0-9a-f]{6})", css)
    soft = re.search(r"--estimated-soft:\s*(#[0-9a-f]{6})", css)
    assert ink and soft
    assert _contrast(ink.group(1), soft.group(1)) >= 4.5
