#!/usr/bin/env python3
"""
Lay the film out on its measured voice, and emit it through the Sprezzature engine.

The picture is not drawn here. Every Sprezzature film is drawn by one
generator, ``brag-output/build_films.py`` in the suite's repository: the
scene types this film uses, the music bed and the three canvases. This module
hands it a spec and takes back a page, so the saggio film looks like the
suite's films because it is made by the same code rather than by a copy of it.

What is decided here is time, and none of it is typed. ``narrate_film.py``
wrote a cue per sentence on the audio it produced; a cut goes in the gap
between the last sentence of one scene and the first of the next, moved to
the nearest beat of the music when that beat falls inside the gap. Every
reveal inside a scene is placed on the sentence that names it.

Output: one HyperFrames project per language and canvas under ``film/hf/``,
which ``render_film.py`` turns into films.

Author
------
`Warith HARCHAOUI, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import json
import os
import re
import shutil
import sys
from itertools import pairwise
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
SCRIPT = HERE / "script.yaml"
MEASURED = HERE / "narration" / "measured.json"
HF = HERE / "hf"
ASSETS = HF / "_assets"

#: Where the suite keeps its film generator. Its assets (fonts, the music
#: bed, the effects, the GSAP build) are linked rather than copied: they are
#: the suite's, and a second copy is a second version.
ENGINE = Path(os.environ.get("SPREZZATURE_FILMS", Path.home() / "sprezzature" / "brag-output"))
SHARED = ("fonts", "music", "sfx", "vendor")

#: Where the voice enters on the film's clock. The suite's films start
#: speaking at 1.10 s, over a first frame that is already complete.
VO_AT = 1.10

#: Seconds the last frame is held after the voice stops, long enough to read
#: the closing line twice. A script that runs long eats into the ninety
#: seconds before it lengthens them.
HOLD = 2.4

RAILS_SUITE = '<p id="rail-l">Sprezzature</p><p id="rail-r">sprezzature.ai</p>'
RAILS_HERE = '<p id="rail-l">saggio</p><p id="rail-r">deraison.ai/saggio</p>'


def engine():
    """Import the suite's film generator from its own folder."""
    if not (ENGINE / "build_films.py").is_file():
        raise SystemExit(
            f"No Sprezzature film generator at {ENGINE}. `pip install -r "
            "requirements-dev.txt` brings the voice and the checks, but the "
            "generator is not on PyPI: clone the suite there, or point "
            "SPREZZATURE_FILMS at its brag-output folder."
        )
    sys.path.insert(0, str(ENGINE))
    import build_films

    build_films.ASSETS = ASSETS
    # The French of this film is written next to its English in the script.
    # A film the generator does not list as rewritten has its bare strings
    # run through the suite's lookup table instead, which would turn a status
    # name such as `measured` into whatever the table holds for that word.
    build_films.REWRITTEN = build_films.REWRITTEN | {"saggio"}
    return build_films


def link_assets() -> None:
    """Build ``hf/_assets``: the suite's shared files, then this film's own."""
    ASSETS.mkdir(parents=True, exist_ok=True)
    for name in SHARED:
        target = ASSETS / name
        if target.is_symlink() or target.exists():
            target.unlink()
        target.symlink_to(ENGINE / "_assets" / name)
    shutil.copyfile(REPO / "assets" / "logo-512.png", ASSETS / "saggio-logo.png")
    for lang in ("en", "fr"):
        wav = ASSETS / f"vo-saggio.{lang}.wav"
        if wav.is_symlink() or wav.exists():
            wav.unlink()
        wav.symlink_to(HERE / "narration" / lang / "narration.wav")


def scene_lines(lines: list[dict], scene_id: str) -> list[dict]:
    """Return the sentences one scene says, on the film's clock."""
    return [
        {**line, "start": line["start"] + VO_AT, "end": line["end"] + VO_AT}
        for line in lines
        if line["scene"] == scene_id
    ]


def timeline(bf, script: dict, lines: list[dict]) -> tuple[list[tuple[float, float]], float]:
    """Each scene's (start, end) on the film's clock, and the film's length."""
    scenes = script["scenes"]
    spoken = [scene_lines(lines, s["id"]) for s in scenes]
    cuts = [0.0]
    for before, after in pairwise(spoken):
        gap_from, gap_to = before[-1]["end"], after[0]["start"]
        cut = (gap_from + gap_to) / 2
        beat = bf.on_beat(cut)[0]
        cuts.append(beat if gap_from + 0.15 <= beat <= gap_to - 0.15 else cut)
    duration = max(float(script["film"]["duration"]), spoken[-1][-1]["end"] + HOLD)
    duration = round(duration, 2)
    bounds = [(round(a, 3), round(b, 3)) for a, b in pairwise([*cuts, duration])]
    return bounds, duration


def on_grid(bf, t: float, lo: float, hi: float) -> float:
    """``t`` moved to the nearest beat, unless that beat leaves the window.

    ``t`` itself is held to the window too: a reveal placed after the scene
    has started fading out is a reveal nobody gets to read.
    """
    t = min(max(t, lo), hi)
    beat = bf.on_beat(t)[0]
    return round(beat if lo <= beat <= hi else t, 3)


def reveals(bf, scene: dict, said: list[dict], start: float, end: float) -> dict:
    """Return the film-clock seconds at which a scene's parts appear, from its voice."""
    lo, hi = start + 0.3, end - 0.8
    kind = scene["type"]
    if kind == "panel":
        # Rows arrive as their status is said: two per sentence, after the first.
        moments = []
        for line in said[1:]:
            moments += [line["start"], (line["start"] + line["end"]) / 2]
        return {"at": [on_grid(bf, t, lo, hi) for t in moments[: len(scene["rows"])]]}
    if kind == "flow":
        first, last = said[0]["start"], said[min(1, len(said) - 1)]["end"]
        n = len(scene["stages"])
        step = (last - first) / max(1, n - 1)
        return {"at": [on_grid(bf, first + k * step, lo, hi) for k in range(n)]}
    if kind == "verify":
        return {
            "at": [
                (on_grid(bf, line["start"], lo, hi), on_grid(bf, line["start"] + 1.6, lo, hi))
                for line in said[: len(scene["claims"])]
            ]
        }
    if kind == "cta":
        # The closing line is the last thing on screen, and it is held at
        # least three seconds whatever the voice did before it.
        return {"punch_at": on_grid(bf, said[-1]["end"] + 0.6, lo, end - 3.0)}
    return {}


def spec_for(bf, script: dict, measured: dict, lang: str) -> dict:
    """One language's film, in the shape the suite's generator reads."""
    lines = measured[lang]["lines"]
    bounds, duration = timeline(bf, script, lines)
    scenes = []
    for k, (scene, (start, end)) in enumerate(zip(script["scenes"], bounds, strict=True)):
        body = {key: value for key, value in scene.items() if key not in ("id", "narration")}
        # Clip windows overlap by a tenth so the incoming scene fades up over
        # the outgoing one, as in every Sprezzature film.
        begin = 0.0 if k == 0 else round(start - 0.1, 3)
        body.update(start=begin, end=end, dur=round(end - begin, 3))
        body.update(reveals(bf, scene, scene_lines(lines, scene["id"]), start, end))
        scenes.append(body)
    sfx = [("tile", round(scenes[k]["start"] + 0.1, 3)) for k in range(1, len(scenes) - 1)]
    sfx.append(("bell", scenes[-1]["punch_at"]))
    return {"duration": duration, "vo": [(f"saggio.{lang}", VO_AT)], "sfx": sfx, "scenes": scenes}


def without_beats(html: str) -> str:
    """Drop the row of beat names the suite's films carry across the top.

    The suite's films used to label their beats in a rail above the picture.
    Warith asked for no navigation trail at the top of the video
    (2026-11-06), so the row of six words and the tweens that light them go
    if a generator still draws them.
    """
    out = re.sub(r'<div id="beats">.*?</div>', "", html, count=1, flags=re.S)
    return re.sub(r'\n\s*tl\.set\("#beat-[a-z]+",[^\n]*;', "", out)


def emit(bf, spec: dict, fmt: str, lang: str) -> Path:
    """Write one HyperFrames project, and return its folder."""
    html = bf.compose("saggio", spec, fmt, lang)
    # The suite's generator dropped its rails on 2026-11-06, wordmark and all.
    # Where a generator still draws them, they name this film rather than the
    # suite; where it does not, there is nothing to rename.
    html = html.replace(RAILS_SUITE, RAILS_HERE).replace(
        '<html lang="en">', f'<html lang="{lang}">'
    )
    html = without_beats(html)
    folder = HF / f"saggio-{lang}-{fmt}"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "index.html").write_text(html, encoding="utf-8")
    (folder / "hyperframes.json").write_text(
        json.dumps(
            {
                "$schema": "https://hyperframes.heygen.com/schema/hyperframes.json",
                "paths": {"assets": "assets"},
                "media": {"autoProxy": True},
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    link = folder / "assets"
    if link.is_symlink() or link.exists():
        link.unlink()
    link.symlink_to("../_assets")
    return folder


def main() -> int:
    """Emit every language on every canvas, and record the timings used."""
    bf = engine()
    script = yaml.safe_load(SCRIPT.read_text(encoding="utf-8"))
    measured = json.loads(MEASURED.read_text(encoding="utf-8"))
    link_assets()
    timings = {}
    for lang in ("en", "fr"):
        spec = spec_for(bf, script, measured, lang)
        timings[lang] = {
            "duration": spec["duration"],
            "scenes": [{"start": s["start"], "end": s["end"]} for s in spec["scenes"]],
        }
        for fmt in bf.FORMATS:
            print(emit(bf, spec, fmt, lang).relative_to(REPO), f"{spec['duration']:.2f}s")
    (HERE / "narration" / "timeline.json").write_text(
        json.dumps(timings, indent=2) + "\n", encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
