"""Which open question would close the most numbers, and what it would close.

Module summary
--------------
A fresh audit comes back with fifteen open fields and the reader is alone with
them. Every one carries a sentence saying what would resolve it, which is the
package's own rule, and none of them says *which to answer first*. That is not
a detail: the fields are not independent. State the country and three figures
compute themselves; measure the runtime and six more follow; name the water
usage effectiveness and exactly one does. A reader working top to bottom
spends an afternoon on the field that unlocks nothing.

The ordering is not a judgement about importance, and nothing here decides what
matters to a project. It is arithmetic on the model's own derivation graph,
read backwards: a quantity names its inputs in ``derived_from``, so the inputs
name their dependents once the edges are reversed, and closing one is a
cascade whose size can be counted exactly.

What it will not do is invent the questions. It asks about fields the model
already holds open, in the words the model already wrote for them.

Usage example
-------------
>>> model = {
...     "assumptions": {
...         "power_draw": {"value": None, "status": "TODO", "unit": "W",
...                        "notes": "Measure it, or state the nameplate."},
...     },
...     "scenarios": [{"name": "one", "costs": {
...         "energy": {"value": None, "status": "TODO", "unit": "kWh",
...                    "derived_from": ["assumptions.power_draw"]},
...     }}],
... }
>>> asked = next_questions(model)
>>> asked[0].path
'assumptions.power_draw'
>>> asked[0].unlocks
1
>>> asked[0].closes
('scenarios[0].costs.energy',)

Author
------
Warith Harchaoui, Ph.D. — https://linkedin.com/in/warithmetics
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .cost_model import CostModel, walk_quantities
from .quantity import Quantity


@dataclass(frozen=True)
class Question:
    """One open field, with what answering it would close.

    Parameters
    ----------
    path : str
        Where the field lives in the document, in the same spelling
        ``derived_from`` uses, so a reader can go straight to it.
    unlocks : int
        How many other open quantities would become computable. Zero is a real
        answer: some fields are asked for their own sake.
    closes : tuple of str
        Those quantities, named. A count with nothing behind it is a claim.
    note : str
        The sentence the model already carries about what would resolve this.
        Empty when the field never wrote one, which is itself worth seeing.
    status : str
        ``TODO`` or ``placeholder``: a field a human must supply, or one being
        held open.

    Examples
    --------
    >>> Question("assumptions.country", 3, ("a", "b", "c"), "State it.", "TODO").unlocks
    3
    """

    path: str
    unlocks: int
    closes: tuple[str, ...]
    note: str
    status: str


def _quantities(model: CostModel | dict[str, Any]) -> dict[str, Quantity]:
    """Return every quantity in the document, by path."""
    wrapped = model if isinstance(model, CostModel) else CostModel.from_mapping(model)
    return {path: Quantity.from_mapping(raw) for path, raw in walk_quantities(wrapped.data)}


def _closes_with(known: set[str], quantities: dict[str, Quantity], opened: set[str]) -> set[str]:
    """Return the open quantities that become computable once `known` is known.

    A derived quantity closes when every path it names is known. Closing one
    can close another, so this runs until nothing more moves: that cascade is
    the whole reason the ordering is worth computing rather than guessing.
    """
    settled = set(known)
    closed: set[str] = set()
    moved = True
    while moved:
        moved = False
        for path in opened - closed:
            inputs = quantities[path].derived_from
            # A field nobody computes cannot be closed by answering something
            # else; it is a question in its own right rather than a consequence.
            if not inputs:
                continue
            if all(name in settled for name in inputs):
                closed.add(path)
                settled.add(path)
                moved = True
    return closed


def next_questions(model: CostModel | dict[str, Any]) -> list[Question]:
    """Return the model's open questions, the ones closing the most first.

    Parameters
    ----------
    model : CostModel or dict
        The model to read. Nothing is written and nothing is computed: this
        reports what answering would do, it does not answer.

    Returns
    -------
    list of Question
        Ordered by how many quantities each would close, then by path so that
        two questions of equal weight come back in a stable order. Empty when
        the model holds nothing open, which is the answer a finished model
        deserves.

    Examples
    --------
    >>> next_questions({"scenarios": [{"name": "one", "costs": {
    ...     "time": {"value": 1.0, "unit": "s", "status": "measured"}}}]})
    []
    """
    quantities = _quantities(model)
    opened = {path for path, quantity in quantities.items() if not quantity.is_known()}
    known = set(quantities) - opened

    # The questions are the open fields nobody computes. A derived field that is
    # open is not a question: it is a consequence of one, and asking a reader to
    # supply it by hand would be asking them to do the arithmetic themselves.
    asked = [path for path in opened if not quantities[path].derived_from]

    questions: list[Question] = []
    for path in asked:
        closes = _closes_with(known | {path}, quantities, opened)
        questions.append(
            Question(
                path=path,
                unlocks=len(closes),
                closes=tuple(sorted(closes)),
                note=(quantities[path].notes or "").strip(),
                status=quantities[path].status or "TODO",
            )
        )
    questions.sort(key=lambda question: (-question.unlocks, question.path))
    return questions


def questions_payload(model: CostModel | dict[str, Any]) -> dict[str, Any]:
    """Return the questions as data, in the shape every surface reports.

    Three surfaces print this — the command line, the HTTP route and the agent
    tool built on it — so the shape is assembled once here rather than three
    times, which is the arrangement a placement defect taught this package to
    prefer.

    Parameters
    ----------
    model : CostModel or dict
        The model to read.

    Returns
    -------
    dict
        ``questions``, each with what it would close, and ``open_total``: how
        many quantities are open altogether, so a reader can see what share the
        questions account for.

    Examples
    --------
    >>> payload = questions_payload({"assumptions": {
    ...     "country": {"value": None, "status": "TODO", "notes": "State it."}}})
    >>> payload["open_total"], payload["questions"][0]["path"]
    (1, 'assumptions.country')
    """
    questions = next_questions(model)
    quantities = _quantities(model)
    opened = [path for path, quantity in quantities.items() if not quantity.is_known()]
    return {
        "open_total": len(opened),
        "questions": [
            {
                "path": question.path,
                "status": question.status,
                "unlocks": question.unlocks,
                "closes": list(question.closes),
                "note": question.note,
            }
            for question in questions
        ],
    }
