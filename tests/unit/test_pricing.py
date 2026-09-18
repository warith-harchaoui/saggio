"""The price ladder: what it reads, what it refuses, and what it records.

Every test here injects the source. None of them reaches the network, because a
suite that needs a working internet connection fails for reasons that have
nothing to do with the code under test.
"""

from __future__ import annotations

from datetime import date

from saggio.catalog.pricing import (
    AGGREGATOR_CURRENCY,
    LITELLM_SOURCE,
    RateTable,
    looks_like_a_rate,
    open_price,
    rate_table,
    unit_for,
)
from saggio.model.quantity import AGGREGATOR, source_strength
from saggio.model.validate import validate

#: One row in the shape the aggregator publishes, rates mixed in with the facts
#: about the model that are not rates.
ROWS = {
    "gpt-4o": {
        "input_cost_per_token": 2.5e-06,
        "output_cost_per_token": 1e-05,
        "cache_read_input_token_cost": 1.25e-06,
        "max_input_tokens": 128000,
        "supports_vision": True,
        "litellm_provider": "openai",
        "mode": "chat",
    }
}


def a_source(rows=ROWS):
    """Return a fetcher that answers with the given rows and never uses a socket."""
    return lambda _url, _timeout: rows


# --- What counts as a rate ---------------------------------------------------


def test_a_field_whose_name_says_cost_and_holds_a_number_is_a_rate() -> None:
    assert looks_like_a_rate("input_cost_per_token", 2.5e-06)


def test_a_context_window_is_not_a_rate() -> None:
    # It is a number, and its name says nothing about money.
    assert not looks_like_a_rate("max_input_tokens", 128000)


def test_a_capability_flag_is_not_a_rate_even_though_python_calls_it_an_int() -> None:
    assert not looks_like_a_rate("supports_vision", True)


def test_the_provider_field_is_not_a_rate() -> None:
    assert not looks_like_a_rate("litellm_provider", "openai")


# --- Reading a table ---------------------------------------------------------


def test_every_published_rate_is_read_and_nothing_else_is() -> None:
    table = rate_table("gpt-4o", fetch=a_source())
    assert sorted(table.rates) == [
        "cache_read_input_token_cost",
        "input_cost_per_token",
        "output_cost_per_token",
    ]


def test_each_rate_carries_its_unit_currency_status_and_provenance() -> None:
    table = rate_table("gpt-4o", fetch=a_source(), today=date(2026, 9, 13))
    rate = table.rates["input_cost_per_token"]
    assert rate.value == 2.5e-06
    assert rate.unit == "USD per input token"
    assert rate.currency == AGGREGATOR_CURRENCY
    assert rate.status == "estimated"
    assert rate.source_kind == AGGREGATOR
    assert rate.source_url == LITELLM_SOURCE
    assert rate.retrieved_date == "2026-09-13"


def test_a_rate_read_from_somebody_elses_table_is_never_measured() -> None:
    # A transcription of a vendor's page is a published figure, not a counter
    # reading, whatever else is true about it.
    table = rate_table("gpt-4o", fetch=a_source())
    assert {rate.status for rate in table.rates.values()} == {"estimated"}


def test_the_explanation_sits_once_on_the_table_not_on_every_rate() -> None:
    table = rate_table("gpt-4o", fetch=a_source())
    assert "Confirm against the vendor" in table.note
    assert all(rate.notes is None for rate in table.rates.values())


def test_the_provider_is_recorded_when_the_source_names_it() -> None:
    assert rate_table("gpt-4o", fetch=a_source()).provider == "openai"


def test_a_key_this_build_has_no_name_for_keeps_the_sources_own_spelling() -> None:
    # Inventing a normalisation would silently transform somebody else's data.
    assert unit_for("input_cost_per_token_above_200k_tokens") == (
        "input_cost_per_token_above_200k_tokens"
    )


# --- Refusing ----------------------------------------------------------------


def test_a_model_the_source_does_not_know_yields_no_rates() -> None:
    assert rate_table("not-a-real-model", fetch=a_source()).is_empty()


def test_an_unreachable_source_yields_no_rates_rather_than_an_error() -> None:
    # An audit with no network must produce the model it produces offline.
    assert rate_table("gpt-4o", fetch=lambda _u, _t: None).is_empty()


def test_a_source_that_answers_with_the_wrong_shape_yields_no_rates() -> None:
    assert rate_table("gpt-4o", fetch=lambda _u, _t: ["not", "a", "mapping"]).is_empty()


def test_an_open_price_states_no_number_and_says_what_would_close_it() -> None:
    price = open_price("https://openai.com/api/pricing/", "No model was named.")
    assert price.value is None
    assert price.status == "TODO"
    assert price.source_url == "https://openai.com/api/pricing/"
    assert "No model was named." in str(price.notes)


# --- What the rest of the package makes of it --------------------------------


def test_a_fetched_rate_passes_the_models_own_validation() -> None:
    table = rate_table("gpt-4o", fetch=a_source())
    model = {
        "schema_version": "2.1",
        "date_updated": date.today().isoformat(),
        "unit_of_work": {"name": "one request"},
        "deployment": {"provider": "on-prem"},
        "models_called": [{"model": "gpt-4o", "rates": table.to_mapping()}],
        "scenarios": [
            {
                "name": "default",
                "costs": {"energy": {"value": 1.0, "unit": "kWh", "status": "estimated"}},
            }
        ],
    }
    report = validate(model)
    assert report.ok, report.to_text()


def test_a_first_party_price_outranks_an_aggregated_one() -> None:
    assert (
        source_strength("stated") > source_strength("first-party") > source_strength("aggregator")
    )


def test_an_empty_table_serialises_to_nothing() -> None:
    assert RateTable("m").to_mapping() == {}
