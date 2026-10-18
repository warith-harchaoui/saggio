"""Ranking the open questions by what answering each one would close.

The rule under test is one sentence: a quantity names its inputs, so reading
those edges backwards says what would become computable. Everything here is
that sentence, plus the two things the ranking must refuse to do -- invent a
question, and ask a reader to supply a number the package computes itself.
"""

from __future__ import annotations

from saggio.model.questions import next_questions, questions_payload


def _chain() -> dict:
    # runtime -> energy -> carbon, with a water figure that closes nothing and a
    # contracted factor that closes one. The shape of a real audited model.
    return {
        "assumptions": {
            "power_draw": {"value": 50.0, "unit": "W", "status": "estimated"},
            "water_usage_effectiveness": {
                "value": None,
                "status": "TODO",
                "notes": "On-premises publishes none.",
            },
            "market_carbon_intensity": {"value": None, "status": "TODO"},
        },
        "scenarios": [
            {
                "name": "one",
                "runtime": {"value": None, "unit": "s", "status": "TODO", "notes": "Measure it."},
                "costs": {
                    "energy": {
                        "value": None,
                        "unit": "kWh",
                        "status": "TODO",
                        "derived_from": ["scenarios[0].runtime", "assumptions.power_draw"],
                    },
                    "carbon": {
                        "value": None,
                        "unit": "gCO2e",
                        "status": "TODO",
                        "derived_from": ["scenarios[0].costs.energy"],
                    },
                    "carbon_market_based": {
                        "value": None,
                        "unit": "gCO2e",
                        "status": "TODO",
                        "derived_from": [
                            "scenarios[0].costs.energy",
                            "assumptions.market_carbon_intensity",
                        ],
                    },
                    "water": {
                        "value": None,
                        "unit": "L",
                        "status": "TODO",
                        "derived_from": [
                            "scenarios[0].costs.energy",
                            "assumptions.water_usage_effectiveness",
                        ],
                    },
                },
            }
        ],
    }


def test_the_question_that_closes_the_most_comes_first() -> None:
    # The runtime closes energy, then carbon through it: the cascade is the
    # whole reason this is computed rather than guessed at.
    asked = next_questions(_chain())
    assert asked[0].path == "scenarios[0].runtime"
    assert asked[0].unlocks == 2
    assert asked[0].closes == ("scenarios[0].costs.carbon", "scenarios[0].costs.energy")


def test_a_field_that_closes_only_itself_is_still_asked() -> None:
    # "Closes nothing else" is the honest description of a water figure, not a
    # reason to hide it: somebody still has to supply it.
    water = next(
        q for q in next_questions(_chain()) if q.path.endswith("water_usage_effectiveness")
    )
    assert water.unlocks == 0
    assert water.note == "On-premises publishes none."


def test_a_derived_field_is_never_asked_of_a_reader() -> None:
    # Asking somebody to supply the energy by hand would be asking them to do
    # the arithmetic this package exists to do, and to do it unprovenanced.
    asked = {question.path for question in next_questions(_chain())}
    assert "scenarios[0].costs.energy" not in asked
    assert "scenarios[0].costs.carbon" not in asked


def test_the_cascade_counts_a_field_once_however_many_paths_reach_it() -> None:
    # water depends on the energy and on the effectiveness. Answering the
    # runtime closes the energy but not the water, and the count must say so.
    runtime = next(q for q in next_questions(_chain()) if q.path == "scenarios[0].runtime")
    assert "scenarios[0].costs.water" not in runtime.closes


def test_a_finished_model_has_nothing_to_ask() -> None:
    finished = {
        "scenarios": [
            {"name": "one", "costs": {"time": {"value": 1.0, "unit": "s", "status": "measured"}}}
        ]
    }
    assert next_questions(finished) == []
    assert questions_payload(finished)["open_total"] == 0


def test_the_payload_says_how_many_are_open_altogether() -> None:
    # The questions are fewer than the open fields, because a derived field is
    # open without being a question. A reader needs both numbers to judge.
    payload = questions_payload(_chain())
    assert payload["open_total"] == 7
    assert len(payload["questions"]) == 3


def test_the_order_is_stable_between_two_questions_of_equal_weight() -> None:
    equal = {
        "assumptions": {
            "b": {"value": None, "status": "TODO"},
            "a": {"value": None, "status": "TODO"},
        }
    }
    assert [q.path for q in next_questions(equal)] == ["assumptions.a", "assumptions.b"]
