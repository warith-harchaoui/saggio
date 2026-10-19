"""Reading a vendor's product carbon footprint, and refusing to guess.

Module summary
--------------
A manufacturer publishes a product carbon footprint as a document: a few pages
of prose with one number that matters. NVIDIA's summary for the HGX H100 says,
in a sentence any parser would find on the first try, that the cradle-to-gate
footprint of **one baseboard** is 1,312 kgCO2e.

This catalogue's unit is **one accelerator**. The divisor is on a different
page, in a specification table reading *"Form Factor: 8x NVIDIA H100 SXM"*, and
the knowledge that a division is needed at all comes from the schema rather than
from the document. A row carrying ``embodied_kgco2e: 1312`` under the key
``H100`` would be wrong by a factor of eight and would look impeccable: a real
vendor URL, a real date, a number genuinely printed in the document.

So this reads, and it refuses, and it never writes. What it produces is a
**draft** with its working shown — the sentence it took the figure from, the
line it took the divisor from, and the arithmetic between them — for somebody
who can be asked why to accept or reject. Three refusals make that safe:

1. **A figure must come from a sentence.** The extractor is an OCR engine, so a
   bar chart becomes text like everything else; a number lifted off a chart is
   the one thing this package will not put in a catalogue. The pattern here
   requires the prose that states what the figure *is*.
2. **A figure without a unit is refused**, not emitted with a guess. Where the
   document says "baseboard" and names no form factor, there is no per-chip
   number to be had and saying so is the answer.
3. **Nothing is written.** The draft is printed. A catalogue row is a claim
   somebody makes, and the person making it is the person who can defend it.

Usage example
-------------
>>> reading = read_text(
...     "the carbon footprint from cradle-to-gate for one HGX H100 GPU "
...     "baseboard is 1,312 kg CO2e. Form Factor 8x NVIDIA H100 SXM",
...     source_url="https://example.invalid/h100-pcf.pdf",
... )
>>> reading.per_unit, reading.units, reading.refused
(164.0, 8, None)

Author
------
Warith Harchaoui
"""

from __future__ import annotations

import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Final

#: What to send when fetching. A vendor's content-delivery host refuses a
#: default Python user agent, and being refused is not the same as being gone.
_HEADERS: Final[dict[str, str]] = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    ),
    "Accept": "*/*",
}

#: Seconds before a host is called unreachable rather than slow.
_TIMEOUT: Final[float] = 30.0

#: What to say when the document parser is not installed. Named here so the
#: refusal reads the same from every surface.
MISSING_PARSER: Final[str] = (
    "Reading a product carbon footprint needs a document parser, which is not "
    "in the default install: `pip install 'saggio[pcf]'`. The three runtime "
    "dependencies are deliberate, and a reader who never adds a catalogue row "
    "should not carry one."
)

#: The sentence that states a footprint. Deliberately demanding: it wants the
#: words around the number, because the number alone also appears on charts,
#: in tables and in page furniture, and this package cannot tell those apart
#: from a claim once they are all text.
_STATED: Final[re.Pattern[str]] = re.compile(
    r"carbon\s+footprint[^.]{0,200}?\bfor\s+(?:one|a|an)\s+(?P<thing>[^.]{3,80}?)\s+is\s+"
    r"(?P<value>[\d][\d,.\s]*)\s*(?:kg|kilograms?)\s*CO\s*[₂2]?\s*e",
    re.IGNORECASE,
)

#: How many of the catalogue's unit the document's unit holds. ``8x NVIDIA H100
#: SXM`` on a baseboard means the figure above covers eight accelerators.
_FORM_FACTOR: Final[re.Pattern[str]] = re.compile(
    r"form\s*factor\s*:?\s*(?P<count>\d{1,2})\s*[x×]\s*(?P<part>[A-Za-z][\w .-]{0,28})",
    re.IGNORECASE,
)

#: Words that say the stated figure is already about one chip or one card, so
#: no divisor is needed and none should be invented.
_ALREADY_ONE: Final[tuple[str, ...]] = ("card", "chip", "module", "package", "gpu", "die")


@dataclass(frozen=True, slots=True)
class Reading:
    """What a product carbon footprint document was found to say.

    Parameters
    ----------
    source_url : str
        Where the document was read from, which is what a catalogue row would
        carry as its citation.
    stated : float or None
        The figure the document states, in kgCO2e, before any division.
    thing : str or None
        What the document says that figure is *of*, in its own words.
    sentence : str or None
        The sentence it came from, kept so a reader can judge the reading
        rather than take it.
    units : int or None
        How many of the catalogue's unit the document's unit holds, and where
        that was read from. ``1`` when the document already speaks of one.
    form_factor : str or None
        The line the divisor came from, or ``None`` when none was needed.
    refused : str or None
        Why there is no usable reading, when there is none.

    Examples
    --------
    >>> Reading("u", refused="nothing found").per_unit is None
    True
    """

    source_url: str
    stated: float | None = None
    thing: str | None = None
    sentence: str | None = None
    units: int | None = None
    form_factor: str | None = None
    refused: str | None = None

    @property
    def per_unit(self) -> float | None:
        """Return the figure for one of the catalogue's units, or ``None``.

        Returns
        -------
        float or None
            ``stated / units``, or ``None`` when either half is missing. A
            missing half is a refusal rather than a guess: the whole reason
            this module exists is that the two halves live on different pages.

        Examples
        --------
        >>> Reading("u", stated=1312.0, units=8).per_unit
        164.0
        >>> Reading("u", stated=1312.0).per_unit is None
        True
        """
        if self.stated is None or not self.units:
            return None
        return self.stated / self.units

    def scope(self) -> str | None:
        """Return the sentence a catalogue row would carry as its scope.

        The field that says which of the document's numbers this one is. It is
        written here rather than left to a contributor because the division is
        the part that has to be stated, and a draft that omitted it would be
        proposing exactly the row this module exists to prevent.

        Returns
        -------
        str or None
            The scope prose, or ``None`` when there is no reading.

        Examples
        --------
        >>> Reading("u", stated=1312.0, thing="HGX H100 GPU baseboard",
        ...         units=8).scope().startswith("One of the 8 on an HGX H100 GPU baseboard")
        True
        """
        if self.per_unit is None or self.thing is None:
            return None
        if self.units == 1:
            return (
                f"One {self.thing}, cradle-to-gate, as the document states it. "
                f"Check what the document excludes before relying on it."
            )
        return (
            f"One of the {self.units} on an {self.thing}: {self.stated:g} kgCO2e "
            f"cradle-to-gate for the whole of it, divided by {self.units}. "
            f"Check what the document excludes before relying on it."
        )

    def to_mapping(self) -> dict[str, Any]:
        """Serialise the reading, working and all.

        Returns
        -------
        dict
            Every surface shows the same thing, and the working is part of it:
            a draft whose arithmetic is hidden is a draft nobody can check.

        Examples
        --------
        >>> sorted(Reading("u", refused="no").to_mapping())
        ['refused', 'source_url']
        """
        if self.refused is not None:
            return {"source_url": self.source_url, "refused": self.refused}
        return {
            "source_url": self.source_url,
            "stated_kgco2e": self.stated,
            "stated_of": self.thing,
            "sentence": self.sentence,
            "units": self.units,
            "form_factor": self.form_factor,
            "per_unit_kgco2e": self.per_unit,
            "draft_row": self.draft_row(),
        }

    def draft_row(self) -> dict[str, Any] | None:
        """Return the catalogue row this reading would propose.

        Returns
        -------
        dict or None
            A row with the fields the footprint contract requires, and no key.
            The key is the one thing only a person can supply: it says which
            catalogue entry this document is about, and a document does not
            know what a catalogue calls things.

        Examples
        --------
        >>> Reading("u", stated=1312.0, thing="HGX H100 GPU baseboard",
        ...         units=8).draft_row()["embodied_kgco2e"]
        164.0
        """
        value = self.per_unit
        if value is None:
            return None
        return {
            "embodied_kgco2e": round(value, 2),
            "embodied_scope": self.scope(),
            "embodied_source_url": self.source_url,
            "embodied_retrieved_date": date.today().isoformat(),
        }


def read_text(text: str, *, source_url: str) -> Reading:
    """Return what a document's text says about a product carbon footprint.

    Parameters
    ----------
    text : str
        The document, already turned into text.
    source_url : str
        Where it came from.

    Returns
    -------
    Reading
        A reading, or a refusal naming which half is missing.

    Examples
    --------
    >>> read_text("nothing here", source_url="u").refused is not None
    True
    """
    found = _STATED.search(" ".join(text.split()))
    if found is None:
        return Reading(
            source_url,
            refused=(
                "No sentence in this document states a carbon footprint. A "
                "figure that appears only in a table or on a chart is not a "
                "claim this package will carry: the words around a number are "
                "what say which number it is."
            ),
        )
    try:
        stated = float(found.group("value").replace(",", "").replace(" ", ""))
    except ValueError:  # pragma: no cover - the pattern admits only digits
        return Reading(source_url, refused=f"{found.group('value')!r} is not a number.")

    thing = found.group("thing").strip()
    sentence = found.group(0).strip()

    if any(word in thing.lower() for word in _ALREADY_ONE) and "board" not in thing.lower():
        return Reading(source_url, stated, thing, sentence, units=1)

    shape = _FORM_FACTOR.search(" ".join(text.split()))
    if shape is None:
        return Reading(
            source_url,
            stated,
            thing,
            sentence,
            refused=(
                f"The document states {stated:g} kgCO2e for one {thing}, and "
                f"this catalogue's unit is one accelerator. Nothing in the "
                f"document says how many it holds, so there is no per-unit "
                f"figure to be had here — not a figure to be guessed at."
            ),
        )
    return Reading(
        source_url,
        stated,
        thing,
        sentence,
        units=int(shape.group("count")),
        form_factor=shape.group(0).strip(),
    )


def _fetch(where: str) -> bytes:
    """Return the bytes of a document, from a URL or a path.

    Parameters
    ----------
    where : str
        An ``http(s)`` URL or a local path.

    Returns
    -------
    bytes
        The document.

    Raises
    ------
    FileNotFoundError
        When a local path does not exist, or a URL cannot be reached.

    Examples
    --------
    >>> _fetch("/nonexistent-pcf.pdf")
    Traceback (most recent call last):
    FileNotFoundError: ...
    """
    if where.startswith(("http://", "https://")):
        request = urllib.request.Request(where, headers=_HEADERS, method="GET")  # noqa: S310
        try:
            with urllib.request.urlopen(request, timeout=_TIMEOUT) as answer:  # noqa: S310
                return bytes(answer.read())
        except (urllib.error.URLError, TimeoutError, OSError) as error:
            raise FileNotFoundError(f"{where} could not be read: {error}") from error
    path = Path(where)
    if not path.is_file():
        raise FileNotFoundError(f"{where} is not a file and is not an http link.")
    return path.read_bytes()


def read(where: str) -> Reading:
    """Return what the document at a URL or path says about a footprint.

    Parameters
    ----------
    where : str
        An ``http(s)`` URL, which is what a catalogue row would cite, or a
        local path for a document already downloaded.

    Returns
    -------
    Reading
        The reading, or a refusal. A missing parser is a refusal that says what
        to install, not an import error three frames deep.

    Examples
    --------
    >>> read("/nonexistent-pcf.pdf").refused is not None
    True
    """
    try:
        from kreuzberg import extract_bytes_sync
    except ImportError:
        return Reading(where, refused=MISSING_PARSER)
    try:
        payload = _fetch(where)
    except FileNotFoundError as error:
        return Reading(where, refused=str(error))
    try:
        extracted = extract_bytes_sync(payload, mime_type="application/pdf")
    except Exception as error:
        return Reading(where, refused=f"The document could not be read: {error}")
    return read_text(getattr(extracted, "content", "") or "", source_url=where)
