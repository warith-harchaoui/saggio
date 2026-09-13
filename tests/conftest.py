"""Shared fixtures.

Every fixture that touches state outside the test process points it at a
temporary directory. A test that wrote to the real catalogue overlay, or changed
what the person running it had consented to, would be a test that broke their
machine to check a package.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

from saggio.model import CostModel


@pytest.fixture
def overlay(tmp_path: Path) -> Path:
    """An empty catalogue overlay, so a developer's own rows never change a result."""
    folder = tmp_path / "overlay"
    folder.mkdir()
    return folder


@pytest.fixture
def consent_file(tmp_path: Path) -> Path:
    """A consent record the test owns, never the user's."""
    return tmp_path / "consent" / "decision.json"


@pytest.fixture
def sound_model() -> dict[str, Any]:
    """A small model that passes every rule, for tests that break one thing at a time."""
    return {
        "schema_version": "2.0",
        "date_updated": "2026-09-12",
        "unit_of_work": {"name": "one request", "status": "estimated"},
        "deployment": {"provider": "on-prem", "country": "FR"},
        "assumptions": {
            "power_draw": {
                "value": 100.0,
                "unit": "W",
                "status": "estimated",
                "source_url": "https://example.invalid/datasheet",
                "retrieved_date": "2026-09-12",
            },
            "electricity_price": {
                "value": 0.24,
                "unit": "USD/kWh",
                "currency": "USD",
                "status": "estimated",
                "source_url": "https://example.invalid/tariff",
                "retrieved_date": "2026-09-12",
            },
        },
        "scenarios": [
            {
                "name": "default",
                "runtime": {"value": 3600.0, "unit": "s", "status": "measured", "notes": "timed"},
                "costs": {
                    "time": {
                        "value": 3600.0,
                        "unit": "s",
                        "status": "measured",
                        "derived_from": ["scenarios[0].runtime"],
                    },
                    "energy": {
                        "value": 0.1,
                        "unit": "kWh",
                        "status": "estimated",
                        "derived_from": ["scenarios[0].runtime", "assumptions.power_draw"],
                    },
                    "money": {
                        "value": 0.024,
                        "unit": "USD",
                        "currency": "USD",
                        "status": "estimated",
                        "derived_from": [
                            "scenarios[0].costs.energy",
                            "assumptions.electricity_price",
                        ],
                    },
                },
            }
        ],
    }


@pytest.fixture
def sound_cost_model(sound_model: dict[str, Any]) -> CostModel:
    """The same model, wrapped."""
    return CostModel.from_mapping(sound_model)


@pytest.fixture
def training_repository(tmp_path: Path) -> Path:
    """A small repository that looks like a training project and really runs."""
    root = tmp_path / "trainer"
    root.mkdir()
    (root / "config.py").write_text("max_iters = 100000\nbatch_size = 8\n", encoding="utf-8")
    (root / "train.py").write_text(
        "import argparse, math\n"
        "parser = argparse.ArgumentParser()\n"
        'parser.add_argument("--max_iters", type=int, default=100000)\n'
        "args = parser.parse_args()\n"
        "total = sum(math.sqrt(step + 1) for step in range(args.max_iters))\n"
        'print("done", total)\n',
        encoding="utf-8",
    )
    (root / "serve.py").write_text("import openai\nclient = openai.OpenAI()\n", encoding="utf-8")
    return root


@pytest.fixture
def python_command() -> list[str]:
    """A command that runs this interpreter and exits cleanly."""
    return [sys.executable, "-c", "pass"]
