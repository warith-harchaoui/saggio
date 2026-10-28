#!/usr/bin/env python3
"""
Read the film's narration aloud, once per scene and once per language.

The voice is not synthesized here and no engine is named here either.
``sprezzature-audio`` owns narration for this suite, so this calls its
command and reads back what it reports. An engine pinned in this file
would be a second place where the suite's default lives, and a default
copied is a default that drifts.

One file per scene rather than one per film, because the composition's
cuts are derived from how long each scene actually takes to say. A
single track would give one number and leave the nine cuts to guesswork,
which is the guesswork that puts a caption on the wrong slide.

Author
------
`Warith HARCHAOUI, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "script.yaml"
NARRATION = HERE / "narration"
LEXICON = HERE / "lexicon"

#: The brick's narration command. Named once, here, and nowhere else.
NARRATE = "sprezzature-audio-narrate-kokoro"


def say_scene(text: str, lang: str, scene_id: str) -> float:
    """Have the brick read one scene, and return how long it took.

    ``--voice`` is left empty on purpose: the command's own help says an
    empty voice means detect the language and pick one, and that choice
    belongs to whoever owns the voice.
    """
    out = NARRATION / lang / scene_id
    out.mkdir(parents=True, exist_ok=True)
    segments = out / "segments.json"
    segments.write_text(json.dumps([text], ensure_ascii=False), encoding="utf-8")

    command = [NARRATE, "--segments", str(segments), "--out-dir", str(out)]
    lexicon = LEXICON / f"{lang}.yaml"
    if lexicon.is_file():
        command += ["--lexicon", str(lexicon)]

    finished = subprocess.run(command, capture_output=True, text=True)
    if finished.returncode != 0:
        raise RuntimeError(f"{NARRATE} failed on {lang}/{scene_id}:\n{finished.stderr.strip()}")

    wav = out / "narration.wav"
    if not wav.is_file():
        raise RuntimeError(f"{NARRATE} wrote no narration.wav in {out}")
    return duration_of(wav)


def duration_of(wav: Path) -> float:
    """Length of a wav in seconds, read from the file rather than assumed."""
    import wave

    with wave.open(str(wav), "rb") as handle:
        return handle.getnframes() / float(handle.getframerate())


def main() -> int:
    """Read every scene aloud, in every language asked for."""
    if shutil.which(NARRATE) is None:
        print(
            f"{NARRATE} is not on PATH. Install the brick's narration tier:\n"
            f"    pip install 'sprezzature-audio[narrate]'",
            file=sys.stderr,
        )
        return 4

    script = yaml.safe_load(SCRIPT.read_text(encoding="utf-8"))
    languages = sys.argv[1:] or ["en", "fr"]
    measured: dict[str, dict[str, float]] = {}

    for lang in languages:
        measured[lang] = {}
        for scene in script["scenes"]:
            text = " ".join(scene[lang]["narration"].split())
            seconds = round(say_scene(text, lang, scene["id"]), 3)
            measured[lang][scene["id"]] = seconds
            print(f"{lang}/{scene['id']}: {seconds:6.2f}s")

    target = NARRATION / "measured.json"
    existing = json.loads(target.read_text(encoding="utf-8")) if target.is_file() else {}
    existing.update(measured)
    target.write_text(json.dumps(existing, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    for lang, scenes in measured.items():
        print(f"{lang}: {sum(scenes.values()):.1f}s of speech over {len(scenes)} scenes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
