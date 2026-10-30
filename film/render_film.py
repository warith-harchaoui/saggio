#!/usr/bin/env python3
"""
Turn a composition into frames, and the frames into a film.

The page is asked for one time after another and photographed each time.
Nothing here plays: ``seek(t)`` is a pure function of ``t``, so the
hundredth frame is the same pixels whether it is taken first or last,
and a render that dies at frame 900 resumes at frame 900.

That resumption is only sound while the page is the same page. It is a
pure function of ``t`` *and* of the composition, and the second argument
used to go unread: a frame already on disk was kept whatever had been
rewritten since. Re-rendering a changed cut then reshot only the frames
the new cut had added and kept the rest, and the result was two films
spliced at the seam -- one that played, carried a plausible duration,
and showed the previous script for its first eighty seconds. Nothing
downstream could catch it, because every gate here reads the composition
or the spec and none of them reads the pixels. So the frames are stamped
with the composition they came from and dropped when it changes.

The track is assembled from the same per-scene files the timings came
from, each followed by the tail its scene was given. Audio laid out from
the same numbers as the picture cannot drift against it.

Author
------
`Warith HARCHAOUI, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "script.yaml"
MEASURED = HERE / "narration" / "measured.json"
FRAMES = HERE / "frames"
OUT = HERE / "out"


def timeline(lang: str) -> tuple[list[dict], float, int]:
    """Each scene's start and length, the film's length, and its frame rate."""
    script = yaml.safe_load(SCRIPT.read_text(encoding="utf-8"))
    measured = json.loads(MEASURED.read_text(encoding="utf-8"))
    tail = float(script["film"]["tail"])
    fps = int(script["film"]["fps"])
    scenes, clock = [], 0.0
    for scene in script["scenes"]:
        spoken = float(measured[lang][scene["id"]])
        scenes.append(
            {
                "id": scene["id"],
                "start": round(clock, 3),
                "dur": round(spoken + tail, 3),
                "spoken": spoken,
            }
        )
        clock += spoken + tail
    return scenes, round(clock, 3), fps


def stamp(page: Path) -> str:
    """Identify the composition a directory of frames was taken from."""
    return hashlib.sha256(page.read_bytes()).hexdigest()


def keep_or_clear(target: Path, page: Path) -> bool:
    """
    Drop frames that were taken from a different composition.

    Parameters
    ----------
    target : pathlib.Path
        The directory frames are written to.
    page : pathlib.Path
        The composition they are taken from.

    Returns
    -------
    bool
        Whether frames already on disk were discarded.
    """
    mark = target / ".composition"
    current = stamp(page)
    if mark.is_file() and mark.read_text(encoding="utf-8").strip() == current:
        return False
    stale = list(target.glob("*.png"))
    for frame in stale:
        frame.unlink()
    target.mkdir(parents=True, exist_ok=True)
    mark.write_text(current + "\n", encoding="utf-8")
    return bool(stale)


def shoot(lang: str) -> tuple[int, int]:
    """Photograph every frame of one language. Returns (written, total)."""
    from playwright.sync_api import sync_playwright

    _, total_seconds, fps = timeline(lang)
    count = round(total_seconds * fps)
    target = FRAMES / lang
    target.mkdir(parents=True, exist_ok=True)
    composition = HERE / "composition" / f"index.{lang}.html"
    if keep_or_clear(target, composition):
        print(f"{lang}: composition changed, previous frames dropped", flush=True)
    page_url = "file://" + str(composition.resolve())

    written = 0
    with sync_playwright() as play:
        browser = play.chromium.launch(args=["--force-color-profile=srgb", "--disable-lcd-text"])
        page = browser.new_page(viewport={"width": 1920, "height": 1080}, device_scale_factor=1)
        page.goto(page_url)
        # The variable fonts are a block-display @font-face; a frame taken
        # before they land is a frame in the fallback face, and only the
        # first few would have it. Waiting once is cheaper than noticing.
        page.wait_for_timeout(1200)
        page.evaluate("document.fonts.ready")

        for index in range(count):
            shot = target / f"{index:05d}.png"
            if shot.is_file():
                continue
            page.evaluate(f"seek({index / fps:.5f})")
            page.screenshot(path=str(shot))
            written += 1
            if written % 200 == 0:
                print(f"{lang}: {index + 1}/{count} frames", flush=True)
        browser.close()
    return written, count


def track(lang: str) -> Path:
    """Lay the per-scene narration out on the film's own timeline."""
    scenes, total, _ = timeline(lang)
    OUT.mkdir(parents=True, exist_ok=True)
    pieces, filters, inputs = [], [], []
    for index, scene in enumerate(scenes):
        wav = HERE / "narration" / lang / scene["id"] / "narration.wav"
        inputs += ["-i", str(wav)]
        delay = round(scene["start"] * 1000)
        filters.append(f"[{index}:a]adelay={delay}|{delay}[a{index}]")
        pieces.append(f"[a{index}]")
    graph = (
        ";".join(filters) + ";" + "".join(pieces) + f"amix=inputs={len(pieces)}:normalize=0[out]"
    )
    path = OUT / f"narration.{lang}.wav"
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            *inputs,
            "-filter_complex",
            graph,
            "-map",
            "[out]",
            "-t",
            f"{total:.3f}",
            "-ar",
            "48000",
            "-ac",
            "1",
            str(path),
        ],
        check=True,
        capture_output=True,
    )
    return path


def assemble(lang: str) -> Path:
    """Frames plus track into one file a browser will play."""
    _, total, fps = timeline(lang)
    audio = track(lang)
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"what-it-costs.{lang}.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-framerate",
            str(fps),
            "-i",
            str(FRAMES / lang / "%05d.png"),
            "-i",
            str(audio),
            "-c:v",
            "libx264",
            "-preset",
            "slow",
            "-crf",
            "20",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            "-t",
            f"{total:.3f}",
            str(path),
        ],
        check=True,
        capture_output=True,
    )
    return path


def main() -> int:
    """Render every language asked for, picture then sound."""
    languages = sys.argv[1:] or ["en", "fr"]
    for lang in languages:
        written, count = shoot(lang)
        print(f"{lang}: {written} frames taken, {count} on disk", flush=True)
        path = assemble(lang)
        size = path.stat().st_size / 1_000_000
        print(f"{lang}: {path.name}  {size:.1f} MB", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
