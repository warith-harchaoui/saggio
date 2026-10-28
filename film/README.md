# The film

Eighty-four seconds of what this package is for, in English and in French,
served from the home page of [deraison.ai/saggio](https://deraison.ai/saggio).

A film is the worst place to put a number. Prose in a README gets re-read;
a figure burned into a keyframe does not, and it stays wrong silently. So
every count this film says out loud is declared in `claims.yaml` next to
the place in the code that decides it, and `make-film verify` fails when
the code and the film stop agreeing.

## The parts

| File | What it holds |
|---|---|
| `script.yaml` | What the film says and shows, scene by scene, in both languages. The content. |
| `claims.yaml` | Every number the film states, the file that decides it, and how to read that file. Written by hand; diffed by a reviewer. |
| `lexicon/` | How the voice says the words it would otherwise get wrong. |
| `film.yaml` | The checkable contract `make-film` reads. Generated: do not edit. |
| `composition/` | One self-contained page per language. `seek(t)` is a pure function of time, so a renderer can ask for any frame and get the same pixels. |
| `narration/` | One audio file per scene per language, and the lengths measured off them. The cuts are derived from these rather than typed. |

## Rebuilding it

Four steps, in this order. Each reads what the one before it wrote.

```bash
python film/narrate_film.py          # the voice, through sprezzature-audio
python film/compose.py               # the two compositions, timed to that voice
python film/make_spec.py             # film.yaml, claims plus derived timings
python film/render_film.py           # frames, then two MPEG-4 (MP4) films in film/out/
```

Then the parts a function owns, and the four gates:

```bash
make-film captions film/film.yaml --lang en --out film/out/what-it-costs.en.vtt
make-film poster film/out/what-it-costs.en.mp4 --out film/out/what-it-costs.en.jpg --at 51.67

make-film verify film/film.yaml --root .                 # do the numbers still hold
make-film scan film/composition/index.en.html --spec film/film.yaml   # anything on screen nobody declared
make-film pitch film/film.yaml --duration 84.37          # problem, then solution, then the one idea
make-film prose film/film.yaml --lang en                 # the named machine tics
sprezzature-audio-audit film/out/what-it-costs.en.vtt --line-chars 58
```

`--line-chars 58` rather than the Netflix default of 42: 58 is the budget the
caption writer in `sprezzature-video` splits a line at, so it is the number
that actually governs this file. The two cues that still read fast are the
voice's pace on one scene, which the audit's own help calls a reason to move
the flag rather than a defect.

## Rendering

The frames are grabbed with Playwright and assembled with ffmpeg rather than
through Hyperframes. Both are named by `sprezzature-video` as renderers behind
the same seam, and the page this film is published on is offline-first with no
build step of its own, so the shorter dependency chain was the one to take.
