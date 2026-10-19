"""Reading a vendor's product carbon footprint, and refusing to guess.

The defect this exists to prevent: NVIDIA's summary states 1,312 kgCO2e for an
HGX H100 **baseboard**, this catalogue's unit is one accelerator, and the
divisor is on a different page. A row carrying 1312 under the key `H100` would
be wrong by a factor of eight and would look impeccable.
"""

from __future__ import annotations

from saggio.catalog.pcf import MISSING_PARSER, Reading, read, read_text

#: The two sentences that matter, as the documents actually word them.
H100 = (
    "Our PCF determined that the carbon footprint from cradle-to-gate for one "
    "HGX H100 GPU baseboard is 1,312 kg CO2e. The central contributors are "
    "materials and components. Product weight 24 kg Typical power consumption "
    "5600 W Form Factor 8x NVIDIA H100 SXM FP8 Tensor Core 32 PFLOPS"
)


# --- What it reads -----------------------------------------------------------


def test_it_takes_the_figure_from_the_sentence_that_states_it() -> None:
    reading = read_text(H100, source_url="u")
    assert reading.stated == 1312.0
    assert reading.thing == "HGX H100 GPU baseboard"
    assert "carbon footprint" in str(reading.sentence)


def test_it_takes_the_divisor_from_the_form_factor_line() -> None:
    reading = read_text(H100, source_url="u")
    assert reading.units == 8
    assert "8x NVIDIA H100" in str(reading.form_factor)


def test_the_arithmetic_is_the_one_a_human_did_a_month_earlier() -> None:
    # The committed catalogue row says 164.0, written by hand from this
    # document. The reader is only worth having if it lands on the same figure.
    assert read_text(H100, source_url="u").per_unit == 164.0


def test_the_draft_scope_states_the_division() -> None:
    # The field the contract requires, and the one a contributor is most likely
    # to leave out: it must begin by naming one unit and say what it divided.
    row = read_text(H100, source_url="u").draft_row()
    assert row["embodied_scope"].startswith("One of the 8 on an HGX H100 GPU baseboard")
    assert "divided by 8" in row["embodied_scope"]
    assert row["embodied_source_url"] == "u"
    assert row["embodied_retrieved_date"]


def test_the_draft_carries_no_key() -> None:
    # A document does not know what this catalogue calls things, and guessing
    # would be the one judgement nobody could be asked about afterwards.
    assert "key" not in read_text(H100, source_url="u").draft_row()


# --- What it refuses ---------------------------------------------------------


def test_a_number_without_the_words_around_it_is_not_a_claim() -> None:
    # The extractor is an OCR engine: a bar chart becomes text like everything
    # else. "546" off a chart and "1,312 kg CO2e" in a sentence are the same
    # kind of token afterwards, and only one of them is a statement.
    chart = "Material Breakdown by Component Type Memory 546 42% ICs 332 25%"
    reading = read_text(chart, source_url="u")
    assert reading.refused is not None
    assert "only in a table or on a chart" in reading.refused


def test_a_board_with_no_form_factor_is_refused_rather_than_divided() -> None:
    reading = read_text(
        "the carbon footprint from cradle-to-gate for one HGX H100 GPU baseboard "
        "is 1,312 kg CO2e and nothing else is said",
        source_url="u",
    )
    assert reading.per_unit is None
    assert reading.refused is not None
    assert "there is no per-unit figure to be had" in reading.refused
    assert "1312" in reading.refused, "the refusal still reports what it did read"


def test_a_document_already_about_one_card_needs_no_divisor() -> None:
    reading = read_text(
        "the carbon footprint from cradle-to-gate for one A100 SXM 40GB card is 127.6 kg CO2e",
        source_url="u",
    )
    assert reading.units == 1
    assert reading.per_unit == 127.6
    assert reading.draft_row()["embodied_scope"].startswith("One A100 SXM 40GB card")


def test_a_missing_parser_says_what_to_install() -> None:
    assert "saggio[pcf]" in MISSING_PARSER
    assert "deliberate" in MISSING_PARSER


def test_a_document_that_is_not_there_is_a_refusal_not_a_crash() -> None:
    reading = read("/nonexistent-product-carbon-footprint.pdf")
    assert reading.refused is not None
    assert reading.per_unit is None


def test_a_refusal_serialises_as_a_refusal() -> None:
    payload = Reading("u", refused="no sentence").to_mapping()
    assert payload == {"source_url": "u", "refused": "no sentence"}


def test_a_reading_serialises_its_working() -> None:
    # A draft whose arithmetic is hidden is a draft nobody can check.
    payload = read_text(H100, source_url="u").to_mapping()
    for field in ("sentence", "form_factor", "stated_kgco2e", "units", "draft_row"):
        assert payload[field], f"{field} is missing from the reading"
