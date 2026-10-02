"""The parts of a model that come from reading the repository.

Module summary
--------------
What one unit of work is, which models the code calls, and which paid services
it reaches. None of these is measured and none is guessed: each is read out of
the source, and each says where it was read from so a reader can disagree with
it.

Author
------
Warith Harchaoui
"""

from __future__ import annotations

from typing import Any, Final

from ..analyze.static import (
    RepositoryReading,
)
from ..catalog.pricing import open_price, rate_table
from ..model.quantity import Quantity
from ..model.taxonomy import TODO
from .options import AuditOptions

#: What one unit of work is, per archetype, when the repository does not say. It
#: is phrased as a question the user should answer rather than as a fact.
_UNIT_BY_ARCHETYPE: Final[dict[str, str]] = {
    "training": "one training run to completion",
    "inference": "one inference on a median-sized input",
    "service": "one request handled end to end",
    "batch-pipeline": "one pass over one day of input data",
    "command-line-tool": "one invocation of the command",
    "library": "one call to the library's main entry point",
}


def _unit_of_work(reading: RepositoryReading) -> dict[str, Any]:
    """Describe one unit of work, or say that nobody has yet.

    Parameters
    ----------
    reading : RepositoryReading
        The static reading, whose archetype suggests a unit.

    Returns
    -------
    dict
        The unit block. Its status is ``placeholder``, never ``estimated``: a
        guess at what somebody meant to measure is a structural stand-in, and
        calling it an estimate would be claiming it was derived from something.

    Examples
    --------
    >>> from pathlib import Path
    >>> _unit_of_work(RepositoryReading(root=Path("."), archetype="training"))["status"]
    'placeholder'
    """
    suggestion = _UNIT_BY_ARCHETYPE.get(reading.archetype)
    if suggestion is None:
        return {
            "name": "TODO: the one thing whose cost this model reports",
            "description": (
                "Reading the code did not make the unit obvious. State it "
                "precisely enough that two people would count it the same way."
            ),
            "status": TODO,
            "out_of_scope": [],
        }
    return {
        "name": suggestion,
        "description": (
            f"Proposed from the repository's shape, which reads as {reading.archetype}. "
            "Confirm or replace it: every number below is per one of these, so the "
            "whole model means whatever this sentence means."
        ),
        "status": "placeholder",
        "out_of_scope": [],
    }


def _model_blocks(reading: RepositoryReading, options: AuditOptions) -> list[dict[str, Any]]:
    """Describe each model the code names, priced when a source publishes a rate.

    A price is per model, not per vendor, so this is the block that can actually
    carry a number. What it never carries is a *cost*: how many tokens one unit
    of work spends is not something reading a repository establishes, so the
    usage stays open and the model says which half is missing.

    Parameters
    ----------
    reading : RepositoryReading
        The static reading, carrying the model hits.
    options : AuditOptions
        What the caller asked for; the rates are only looked up on request.

    Returns
    -------
    list of dict
        One block per model identifier found, with its evidence and its rates.

    Examples
    --------
    >>> from pathlib import Path
    >>> _model_blocks(RepositoryReading(root=Path(".")), AuditOptions())
    []
    """
    blocks: list[dict[str, Any]] = []
    for hit in reading.models:
        block = hit.to_mapping()
        if options.fetch_prices:
            table = rate_table(hit.identifier, timeout=options.timeout_seconds)
            if not table.is_empty():
                if table.provider:
                    block["provider"] = table.provider
                block["rates"] = table.to_mapping()
                block["rates_provenance"] = table.note
        block["units_per_unit_of_work"] = open_price(
            None,
            "How much of each rate one unit of work spends. Reading the code cannot "
            "establish this; measure a real call, or state it.",
        ).to_mapping()
        blocks.append(block)
    return blocks


def _service_blocks(reading: RepositoryReading) -> list[dict[str, Any]]:
    """Describe each paid service the code calls, with a price left open.

    A per-service price is deliberately not fetched, because a service is not
    what anybody is charged for: ``gpt-4o`` and ``gpt-4o-mini`` are one API at an
    eightfold difference. The rates live per model, in :func:`_model_blocks`. What
    belongs here is the identification, the line that proves the call, and the
    page where the vendor's own numbers live.

    Parameters
    ----------
    reading : RepositoryReading
        The static reading, carrying the service hits.

    Returns
    -------
    list of dict
        One block per detected service.

    Examples
    --------
    >>> from pathlib import Path
    >>> _service_blocks(RepositoryReading(root=Path(".")))
    []
    """
    blocks: list[dict[str, Any]] = []
    for hit in reading.services:
        block = hit.to_mapping()
        if hit.pricing_source_url:
            block["pricing_source_url"] = hit.pricing_source_url
        block["price_per_unit"] = Quantity(
            unit="currency",
            status=TODO,
            source_url=hit.pricing_source_url or None,
            notes=(
                "Read the current price from the page above and record what one "
                "unit of work spends. It is left open because a price copied "
                "today is wrong by next quarter."
            ),
        ).to_mapping()
        blocks.append(block)
    return blocks
