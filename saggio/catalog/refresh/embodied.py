"""What building a processor emitted, where that can be stood behind.

Module summary
--------------
Two guards, both earned by probing the source rather than trusting it. It
answers about a chip it was not asked about -- asked for an Apple M4 Max it
returns an Apple M1 Max, four generations earlier, and says so nowhere -- and it
answers for a die size it does not have by filling in a family average. Either
failure produces a number indistinguishable from a real one, under the name that
was asked for.

The accelerator half of that API is refused outright: asked for any GPU by name
it answers the same figure for every card, because it holds one archetype.

Author
------
Warith Harchaoui
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Final

#: Where the processor footprints come from. Boavizta publishes an open,
#: keyless API over a crowd-sourced database of chip die sizes, and computes a
#: cradle-to-gate footprint from the die. It is the only source found that
#: covers ordinary processors at all: vendors publish footprints for whole
#: servers, not for the chip inside them.
EMBODIED_CPU_API: Final[str] = "https://api.boavizta.org/v1/component/cpu"


#: The method behind that figure, and what a row cites. The endpoint below is
#: where the number came from and what a refresh queries, but it is not what a
#: reader should be sent to: asked for nothing in particular it answers 19.0
#: kgCO2e -- the default for an unnamed chip, which is the very figure this
#: module refuses -- so a row citing it would display a wrong number to anybody
#: who followed the link. The endpoint is named in each row's scope instead.
EMBODIED_METHOD_URL: Final[str] = "https://doc.api.boavizta.org/Explanations/components/cpu/"


#: The vendor name each catalogue key is known by there. The key is this
#: package's own shorthand and would not match anything.
EMBODIED_NAME_OF_KEY: Final[dict[str, str]] = {
    "xeon-platinum-8175": "intel xeon platinum 8175m",
    "xeon-gold-6248": "intel xeon gold 6248",
    "epyc-7742": "amd epyc 7742",
    "epyc-9654": "amd epyc 9654",
    "core-i9-13900k": "intel core i9-13900k",
    "ryzen-9-7950x": "amd ryzen 9 7950x",
    "apple-m2-max": "apple m2 max",
    "apple-m3-max": "apple m3 max",
    "apple-m4-max": "apple m4 max",
}


#: A die size the source did not actually have for this chip. It fills the gap
#: with a family average or a regression and says so in the field's `source`,
#: which is the only reason this can be caught at all -- the figure that comes
#: back looks exactly like a real one.
_INVENTED_DIE: Final[tuple[str, ...]] = ("average value", "regression")


#: Why the GPU half of that API is refused outright. Asked for any GPU by name
#: it answers 575.1 kgCO2e -- the same number for a GTX 1080 Ti, an A100 and an
#: H100 -- because it holds one archetype called "Large GPU" and no per-model
#: data at all. Against NVIDIA's own verified 164 kgCO2e for an H100 card that
#: is three and a half times too high, and it arrives wearing the model name
#: that was asked for.
GPU_REFUSAL: Final[str] = (
    "That source holds one generic GPU archetype, not per-model data: it answers "
    "575.1 kgCO2e for every card from a GTX 1080 Ti to an H100, which is three and "
    "a half times NVIDIA's own verified figure for an H100. A number that arrives "
    "wearing the model name you asked for, and is the same for every model, is "
    "worse than no number. Accelerator footprints are entered by hand from a "
    "published product carbon footprint, one card at a time."
)


@dataclass(frozen=True)
class EmbodiedRefresh:
    """Processor footprints the source could stand behind, and the ones it could not.

    Parameters
    ----------
    rows : dict
        Catalogue key to ``(kgCO2e, the chip the source matched, the die it used)``.
    refused : dict
        Catalogue key to why its answer was not usable.
    source : str
        The URL that answered.
    retrieved : str
        The day this was read.

    Examples
    --------
    >>> EmbodiedRefresh({"epyc-7742": (40.66, "AMD EPYC 7742", "1600")}, {}, "x").rows[
    ...     "epyc-7742"][0]
    40.66
    """

    rows: dict[str, tuple[float, str, str]]
    refused: dict[str, str]
    source: str = EMBODIED_CPU_API
    retrieved: str = field(default_factory=lambda: date.today().isoformat())


def _asked_for_what_came_back(asked: str, matched: str) -> bool:
    """Return whether the source answered about the chip it was asked about.

    It matches names fuzzily and never says it has substituted one. Asked for an
    Apple M4 Max it answers about an Apple M1 Max -- four generations earlier --
    with no warning anywhere in the reply. Comparing the two names is the only
    thing standing between that and a catalogue row.

    Parameters
    ----------
    asked : str
        The name sent.
    matched : str
        The name the reply says it used.

    Returns
    -------
    bool
        True when they are the same chip.

    Examples
    --------
    >>> _asked_for_what_came_back("amd epyc 7742", "AMD EPYC 7742")
    True
    >>> _asked_for_what_came_back("apple m4 max", "Apple M1 Max")
    False
    """
    flatten = str.maketrans("", "", " -_")
    return asked.lower().translate(flatten) == matched.lower().translate(flatten)


def fetch_embodied(keys: list[str] | tuple[str, ...], *, timeout: int = 30) -> EmbodiedRefresh:
    """Return a cradle-to-gate footprint for each processor the source really knows.

    Two guards, and both earned the hard way. The source answers for a name it
    does not have by quietly substituting the nearest one it does, and it
    answers for a die size it does not have by filling in a family average --
    asked about a chip called ``banana chip 9000`` it returns 19.0 kgCO2e
    without a word. Either failure produces a number indistinguishable from a
    real one, under the name that was asked for.

    So a row is only accepted when the name that came back is the name that went
    out, and when the die size it was computed from is this chip's rather than a
    default or a regression. Everything else is refused by name and left for a
    human, which is the behaviour this package has everywhere else.

    Parameters
    ----------
    keys : list of str
        Catalogue keys to look up. Keys with no vendor name on file are refused.
    timeout : int, optional
        Seconds to allow each request.

    Returns
    -------
    EmbodiedRefresh
        What was found, and why anything missing was missed.

    Examples
    --------
    >>> fetch_embodied([]).rows
    {}
    """
    found: dict[str, tuple[float, str, str]] = {}
    refused: dict[str, str] = {}
    for key in keys:
        name = EMBODIED_NAME_OF_KEY.get(key)
        if not name:
            refused[key] = "no vendor name on file for this key."
            continue
        request = urllib.request.Request(  # noqa: S310 - a fixed https endpoint.
            f"{EMBODIED_CPU_API}?verbose=true&criteria=gwp",
            data=json.dumps({"name": name}).encode("utf-8"),
            headers={"Content-Type": "application/json", "Accept": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as answer:  # noqa: S310
                payload = json.loads(answer.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, ValueError) as exc:
            refused[key] = f"the source did not answer: {exc}"
            continue
        verbose = payload.get("verbose") or {}
        matched = str((verbose.get("name") or {}).get("value", ""))
        if not _asked_for_what_came_back(name, matched):
            refused[key] = (
                f"the source answered about {matched!r}, not {name!r}. It substitutes "
                "the nearest name it holds without saying so."
            )
            continue
        die = verbose.get("die_size") or {}
        die_source = str(die.get("source", ""))
        if any(mark in die_source.lower() for mark in _INVENTED_DIE):
            refused[key] = (
                f"the die size it computed from is not this chip's: {die_source!r}. "
                "The footprint is a function of the die, so a default die is a "
                "default footprint wearing this chip's name."
            )
            continue
        try:
            value = float(payload["impacts"]["gwp"]["embedded"]["value"])
        except (KeyError, TypeError, ValueError):
            refused[key] = "the answer carried no footprint this could read."
            continue
        found[key] = (value, matched, str(die.get("value", "unstated")))
    return EmbodiedRefresh(rows=found, refused=refused)


def apply_embodied(path: Path, refresh: EmbodiedRefresh, *, section: str = "cpus") -> int:
    r"""Write processor footprints into a catalogue file, line by line.

    Parameters
    ----------
    path : pathlib.Path
        The catalogue to edit. It must already exist.
    refresh : EmbodiedRefresh
        What to write.
    section : str, optional
        Which block of the file to edit, for the error message only.

    Returns
    -------
    int
        How many rows were written.

    Raises
    ------
    FileNotFoundError
        When the path is not there.

    Examples
    --------
    >>> import tempfile, pathlib
    >>> text = 'cpus:\n  - key: "epyc-7742"\n    tdp_w: 225\n'
    >>> with tempfile.TemporaryDirectory() as folder:
    ...     target = pathlib.Path(folder) / "hardware.yaml"
    ...     _ = target.write_text(text, encoding="utf-8")
    ...     written = apply_embodied(
    ...         target, EmbodiedRefresh({"epyc-7742": (40.66, "AMD EPYC 7742", "1600")}, {}, "x"))
    ...     body = target.read_text(encoding="utf-8")
    >>> written
    1
    >>> "embodied_kgco2e: 40.66" in body
    True
    >>> "1600 mm2" in body
    True
    """
    if not path.is_file():
        raise FileNotFoundError(
            f"{path} is not there. This edits a catalogue; it does not create one."
        )
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    written = 0
    current: str | None = None
    out: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("- key:"):
            current = stripped.split(":", 1)[1].strip().strip('"').strip("'")
        if current in refresh.rows and stripped.startswith(
            (
                "embodied_kgco2e:",
                "embodied_scope:",
                "embodied_source_url:",
                "embodied_retrieved_date:",
            )
        ):
            continue
        out.append(line)
        if current in refresh.rows and stripped.startswith("- key:"):
            indent = " " * (len(line) - len(line.lstrip()) + 2)
            value, matched, die = refresh.rows[current]
            scope = (
                f"One {matched} package, cradle-to-gate, computed from its die of "
                f"{die} mm2 by {EMBODIED_CPU_API}. Excludes the use phase and, per "
                "the source, end of life."
            )
            out.append(f"{indent}embodied_kgco2e: {value}\n")
            out.append(f'{indent}embodied_scope: "{scope}"\n')
            out.append(f'{indent}embodied_source_url: "{EMBODIED_METHOD_URL}"\n')
            out.append(f'{indent}embodied_retrieved_date: "{refresh.retrieved}"\n')
            written += 1
    path.write_text("".join(out), encoding="utf-8")
    return written
