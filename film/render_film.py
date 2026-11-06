#!/usr/bin/env python3
"""
Render the six cuts, check what came out, and put them where the site reads them.

Each project under ``film/hf/`` is rendered by HyperFrames with the flags the
Sprezzature films are rendered with: 4K, the canvas's own layout at four
times the pixels, streamed rather than staged so a cut does not need sixty
gigabytes of scratch. Then every file is measured, because a killed render
leaves a short film behind and a stale render leaves the previous one.

What lands in ``film/out/``, named as the suite names its films:
``what-it-costs.<lang>.mp4`` for the landscape cut, ``.portrait.mp4`` and
``.square.mp4`` beside it, a poster for each and one caption track per
language.

Usage::

    python film/render_film.py            # every cut
    python film/render_film.py en         # one language

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

HERE = Path(__file__).resolve().parent
HF = HERE / "hf"
OUT = HERE / "out"
NAME = "what-it-costs"

#: The renderer, pinned to the version the suite's films are rendered with.
HYPERFRAMES = "hyperframes@0.8.46"

#: Frame size each canvas must come out at, in 4K.
SIZES = {"landscape": "3840x2160", "portrait": "2160x3840", "square": "2160x2160"}

#: Where the poster is cut: inside the opening card, after the hairline under
#: the rails has drawn itself, so the still carries the name, the sentence
#: and the address.
POSTER_AT = 1.5


def probe(path: Path) -> tuple[float, str]:
    """A film's length in seconds and its frame size, read off the file."""
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
         "stream=width,height:format=duration", "-of", "json", str(path)],
        capture_output=True, text=True, check=True,
    )
    data = json.loads(out.stdout)
    stream = data["streams"][0]
    return float(data["format"]["duration"]), f"{stream['width']}x{stream['height']}"


def render(folder: Path, fmt: str) -> Path:
    """Render one project and return the film it produced."""
    log = folder.with_suffix(".render.log")
    with log.open("w") as handle:
        done = subprocess.run(
            ["npx", "--yes", HYPERFRAMES, "render", "--quality", "looks",
             "--resolution", f"{fmt}-4k", "--low-memory-mode"],
            cwd=folder, stdout=handle, stderr=subprocess.STDOUT,
        )
    if done.returncode != 0:
        raise RuntimeError(f"{folder.name} failed to render; see {log}")
    films = sorted((folder / "renders").glob("*.mp4"), key=lambda p: p.stat().st_mtime)
    if not films:
        raise RuntimeError(f"{folder.name} rendered nothing; see {log}")
    return films[-1]


def main() -> int:
    """Render, measure and install every cut asked for."""
    timeline = json.loads((HERE / "narration" / "timeline.json").read_text(encoding="utf-8"))
    languages = sys.argv[1:] or ["en", "fr"]
    OUT.mkdir(exist_ok=True)
    bad = 0
    for lang in languages:
        want = timeline[lang]["duration"]
        for fmt, size in SIZES.items():
            folder = HF / f"saggio-{lang}-{fmt}"
            film = render(folder, fmt)
            seconds, got = probe(film)
            if abs(seconds - want) > 1.0 or got != size:
                print(f"BAD  {folder.name}: {seconds:.2f}s at {got}, expected {want:.2f}s at {size}")
                bad += 1
                continue
            suffix = "" if fmt == "landscape" else f".{fmt}"
            target = OUT / f"{NAME}.{lang}{suffix}.mp4"
            shutil.copyfile(film, target)
            subprocess.run(
                ["make-film", "poster", str(target), "--out", str(target.with_suffix(".jpg")),
                 "--at", str(POSTER_AT)],
                check=True, capture_output=True,
            )
            print(f"ok   {target.relative_to(HERE.parent)}  {seconds:.2f}s  {got}")
        subprocess.run(
            ["make-film", "captions", str(HERE / "film.yaml"), "--lang", lang,
             "--out", str(OUT / f"{NAME}.{lang}.vtt")],
            check=True,
        )
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
