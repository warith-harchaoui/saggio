#!/usr/bin/env python3
"""
Read the film's narration aloud, once per language, and keep its cues.

The voice is not synthesized here and no engine is named here either.
``speaker-helper`` decides which engine reads which language for the whole
Sprezzature suite, and ``sprezzature-audio`` reads with it; this asks the
router the same question the suite's own films ask, so the two sets of films
cannot end up in two different voices.

One call per language, every sentence a segment. Chatterbox spends most of
a call loading its model, so a call per scene was eight loads for a minute
and a half of speech. More to the point, the call returns a cue per segment
laid out on the very audio it wrote: the scene cuts are then read off that
timeline rather than computed beside it, and the two cannot disagree.

Author
------
`Warith HARCHAOUI, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import json
import re
import sys
import wave
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "script.yaml"
NARRATION = HERE / "narration"
LEXICON = HERE / "lexicon"

#: The voice *name* each engine wants, the one thing an engine decides by
#: nature: chatterbox renders from its own reference recording when given
#: ``""``. Mirrors the suite's films, which make the same choice.
VOICES: dict[str, dict[str, str]] = {
    "kokoro": {"en": "af_heart", "fr": "ff_siwis"},
    "chatterbox": {"en": "", "fr": ""},
}


def voice_of(lang: str) -> tuple[str, str]:
    """Return the engine and voice for one language, as ``speaker-helper`` routes it."""
    from speaker_helper import RouteRequest, route

    engine = route(RouteRequest(condition="offline", language=lang)).engine
    return engine, VOICES.get(engine, {}).get(lang, "")


def segments_of(script: dict, lang: str) -> tuple[list[dict], list[str]]:
    """Every sentence of the film as a segment, and the scene each belongs to."""
    pause = int(script["film"]["pause_ms"])
    scene_pause = int(script["film"]["scene_pause_ms"])
    segments, owners = [], []
    for scene in script["scenes"]:
        for k, text in enumerate(scene["narration"][lang]):
            segment = {"text": " ".join(text.split())}
            if segments:
                segment["pause_before_ms"] = pause if k else scene_pause
            segments.append(segment)
            owners.append(scene["id"])
    return segments, owners


def read_cues(vtt: Path) -> list[tuple[float, float]]:
    """Return the (start, end) of every cue in a WebVTT file, in order."""

    def seconds(stamp: str) -> float:
        h, m, s = stamp.split(":")
        return int(h) * 3600 + int(m) * 60 + float(s)

    times = re.findall(r"(\d+:\d+:[\d.]+) --> (\d+:\d+:[\d.]+)", vtt.read_text(encoding="utf-8"))
    return [(seconds(a), seconds(b)) for a, b in times]


#: How many times a language is read again when a sentence comes back wrong.
ATTEMPTS = 3


def stalled(lines: list[dict]) -> list[str]:
    """Sentences read at under half the language's median pace.

    Chatterbox samples, and now and then a sentence runs on: the engine
    repeats tokens until it forces an end, and seventy characters of French
    came back fifteen seconds long. Nothing fails, and the film would hold
    one sentence on screen for a quarter of its length. Pace is the one
    measure that catches it, because it is the only thing about the
    sentence that changed.
    """
    pace = sorted(len(line["text"]) / max(0.01, line["end"] - line["start"]) for line in lines)
    median = pace[len(pace) // 2]
    return [
        line["text"]
        for line in lines
        if len(line["text"]) / max(0.01, line["end"] - line["start"]) < median / 2
    ]


def narrate(script: dict, lang: str) -> dict:
    """Read one language until every sentence comes back at a speaking pace."""
    for attempt in range(1, ATTEMPTS + 1):
        result = read_once(script, lang)
        slow = stalled(result["lines"])
        if not slow:
            return result
        print(f"{lang}: attempt {attempt} ran on at {slow[0][:50]!r}; reading again")
    raise RuntimeError(f"{lang}: {len(slow)} sentence(s) still run on after {ATTEMPTS} readings")


def read_once(script: dict, lang: str) -> dict:
    """Read one language once, and return its cues grouped by scene."""
    import sprezzature_audio

    segments, owners = segments_of(script, lang)
    out = NARRATION / lang
    out.mkdir(parents=True, exist_ok=True)
    engine, voice = voice_of(lang)
    lexicon = LEXICON / f"{lang}.yaml"
    report = sprezzature_audio.narrate(
        engine,
        segments,
        voice=voice,
        voice_sample=None,
        out_dir=out,
        lang=lang,
        lexicon=lexicon if lexicon.is_file() else None,
    )
    cues = read_cues(out / "narration.vtt")
    if len(cues) != len(segments):
        raise RuntimeError(
            f"{lang}: {len(segments)} sentences were read and {len(cues)} cues came back; "
            "a scene cut placed from that would land on the wrong sentence."
        )
    with wave.open(str(out / "narration.wav"), "rb") as handle:
        seconds = handle.getnframes() / handle.getframerate()
    lines = [
        {"scene": owner, "text": seg["text"], "start": round(a, 3), "end": round(b, 3)}
        for owner, seg, (a, b) in zip(owners, segments, cues, strict=True)
    ]
    return {
        "engine": engine,
        "voice": report.get("voice", voice),
        "seconds": round(seconds, 3),
        "lines": lines,
    }


def main() -> int:
    """Read every language asked for, and record what was said and when."""
    script = yaml.safe_load(SCRIPT.read_text(encoding="utf-8"))
    languages = sys.argv[1:] or ["en", "fr"]
    target = NARRATION / "measured.json"
    measured = json.loads(target.read_text(encoding="utf-8")) if target.is_file() else {}
    for lang in languages:
        measured[lang] = narrate(script, lang)
        print(f"{lang}: {measured[lang]['seconds']:.1f}s of speech, {measured[lang]['engine']}")
    target.write_text(json.dumps(measured, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
