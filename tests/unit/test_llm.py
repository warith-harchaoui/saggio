"""The local model: what it may say, and what is thrown away."""

from __future__ import annotations

import pytest

from running_code_cost_helper.analyze.llm import (
    ALLOWED_FIELDS,
    WORKLOAD_KINDS,
    Classification,
    _build_prompt,
    _coerce,
    classify,
    host,
    installed_models,
    is_available,
    pick_model,
)


def test_the_endpoint_is_local_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OLLAMA_HOST", raising=False)
    assert host().startswith("http://127.0.0.1")


def test_a_bare_host_gets_a_scheme(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OLLAMA_HOST", "example.invalid:11434")
    assert host() == "http://example.invalid:11434"


def test_a_pinned_model_wins(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RUNNING_CODE_COST_MODEL", "my-model:latest")
    assert pick_model() == "my-model:latest"


def test_an_absent_server_is_a_normal_outcome(monkeypatch: pytest.MonkeyPatch) -> None:
    # Most machines have no Ollama running, and an audit must not care.
    monkeypatch.setenv("OLLAMA_HOST", "http://127.0.0.1:1")
    monkeypatch.delenv("RUNNING_CODE_COST_MODEL", raising=False)
    assert is_available() is False
    assert installed_models() == ()
    assert pick_model() is None
    assert classify("a repository") is None


def test_the_prompt_forbids_numbers() -> None:
    prompt = _build_prompt("a repository")
    assert "Do not include any number" in prompt
    assert "discarded" in prompt


def test_the_prompt_offers_a_closed_set_of_answers() -> None:
    prompt = _build_prompt("a repository")
    for kind in WORKLOAD_KINDS:
        assert kind in prompt


def test_numbers_the_model_returns_are_thrown_away() -> None:
    # Every number in a cost model comes from a file that can be opened or a
    # counter that can be read. A figure from a language model is one nobody can
    # check, so it never reaches the model at all.
    result = _coerce({"workload_kind": "training", "cost_usd": 3.5, "runtime_seconds": 900}, "m")
    assert result is not None
    assert "cost_usd" not in result.to_mapping()
    assert "runtime_seconds" not in result.to_mapping()


def test_only_the_allowed_fields_survive() -> None:
    result = _coerce({"workload_kind": "inference", "invented": "x"}, "m")
    assert result is not None
    assert set(result.to_mapping()) <= ALLOWED_FIELDS | {
        "evidence_source",
        "confidence",
    }


def test_an_answer_outside_the_closed_set_is_discarded() -> None:
    assert _coerce({"workload_kind": "vibes"}, "m") is None


def test_an_answer_with_no_kind_is_discarded() -> None:
    assert _coerce({"reasoning": "it looks like a thing"}, "m") is None


def test_a_non_boolean_compute_bound_becomes_unknown() -> None:
    result = _coerce({"workload_kind": "training", "compute_bound": "yes"}, "m")
    assert result is not None
    assert result.compute_bound is None


def test_the_classification_names_the_model_that_gave_it() -> None:
    mapping = Classification("training", "matmul", True, "why", "qwen:7b").to_mapping()
    assert mapping["evidence_source"] == "llm:qwen:7b"
    assert mapping["confidence"] == "low"
