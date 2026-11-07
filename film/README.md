# The film

Ninety seconds of what this package is for, in English and in French, cut
wide, tall and square, and served from the home page of
[deraison.ai/saggio](https://deraison.ai/saggio).

It is a Sprezzature film. It follows the spine every film of that suite
follows, in Guy KAWASAKI's order: what it is, the problem, the solution, the
secret sauce, the finest example, then the ask. Unlike the suite's films, it
does not label those beats across the top of the picture. And it is drawn by
the suite's own generator,
`brag-output/build_films.py`, so it looks like those films because the same
code makes it.

A film is the worst place to put a number. Prose in a README gets re-read; a
figure burned into a frame does not, and it stays wrong silently. So every
number this film states is declared in `claims.yaml` next to the place in the
code that decides it, and `make-film verify` fails when the code and the film
stop agreeing.

## The parts

| File | What it holds |
|---|---|
| `script.yaml` | What the film says and shows, scene by scene, in both languages. The content. |
| `claims.yaml` | Every number the film states, the file that decides it, and how to read that file. Written by hand; diffed by a reviewer. |
| `lexicon/` | How the voice says the words it would otherwise get wrong. |
| `narration/` | One track per language, its cues, and `measured.json`: when each sentence starts and stops. |
| `film.yaml` | The checkable contract `make-film` reads. Generated: do not edit. |
| `hf/` | One HyperFrames project per language and canvas. Generated, not committed. |

## Rebuilding it

The package needs none of this. `requirements.txt` and the `dev` extra that
continuous integration installs carry no Sprezzature; the film's Python tools
are listed in `film/requirements.txt`, which `requirements-dev.txt` pulls in
for whoever works on the film.

Three things stay outside pip:

- **The generator**, `brag-output/build_films.py`, which no package ships.
  It is read from the Sprezzature repository beside this one
  (`~/sprezzature`, or set `SPREZZATURE_FILMS` to its `brag-output` folder).
- **Its assets**, `brag-output/_assets/`, which git does not track. The music
  bed is licensed and exists in one place only, so the film cannot be rebuilt
  from a clone alone; `restore_assets.py` in that folder says what is missing.
- **Node** for HyperFrames, and **ffmpeg**.

```bash
pip install -r requirements-dev.txt  # the package's tools, and the film's
python film/narrate_film.py          # the voice, through sprezzature-audio
python film/compose.py               # six projects, cut on that voice
python film/make_spec.py             # film.yaml, claims plus the measured timings
python film/render_film.py           # six films, posters and captions in film/out/
```

Each step reads what the one before it wrote, and nothing is timed by hand.

- **The voice** is whatever `speaker-helper` routes to for each language,
  the same question the suite's films ask, so the two sets of films speak
  with one voice. Each language is read in one call with every sentence as a
  segment, which returns a cue per sentence on the audio it wrote. Chatterbox
  samples, and now and then a sentence runs on; a sentence read at under half
  the language's median pace sends the whole language back to be read again.
- **The cuts** go in the gap between the last sentence of one scene and the
  first of the next, on the nearest beat of the music when that beat falls
  inside the gap. Every reveal in a scene lands on the sentence that names it.
  A script that outruns ninety seconds lengthens the film: the voice is never
  cut.
- **The captions** are written by `make-film captions` from the script and
  those cues, so they say what the voice says, sentence for sentence, from the
  moment it starts saying it, and stay up through the pause after. They ship as a separate WebVTT track and are never burned into the
  picture: the player offers them, and the viewer turns them on.

Then the four gates:

```bash
make-film verify film/film.yaml --root .                 # do the numbers still hold
make-film scan film/hf/saggio-en-landscape/index.html --spec film/film.yaml
make-film pitch film/film.yaml --duration 90             # problem, then solution, then the one idea
make-film prose film/film.yaml --lang en                 # the named machine tics
sprezzature-audio-audit film/out/what-it-costs.en.vtt --line-chars 58
sprezzature-audio-audit film/out/what-it-costs.fr.vtt --line-chars 58 --cps 20
```

`--cps 20` on the French track: French spends more characters on the same
sentence, so the 17-characters-a-second ceiling, which is Netflix's figure for
English, flags a track a French reader follows perfectly well.

Two more gates, and one of them cannot answer here:

```bash
make-film assets film/film.yaml --tree . --repo .   # 8 of 8 in hand: a clone can rebuild it
make-film calque film/film.yaml --from en --to fr   # 0.94, and not evidence
```

`calque` compares the two cuts line by line on how many sentences each holds
and which numerals it carries. This narration is one sentence to a line with
almost no numerals, so it is comparing two near-constant sequences, the case
its own documentation excludes. Read the two cuts side by side instead; the
French was written next to the English, not from it.

## Rendering

`render_film.py` renders each project with the flags the Sprezzature films are
rendered with: 4K, the canvas's own layout at four times the pixels, streamed
rather than staged so a cut does not need sixty gigabytes of scratch. Every
film is then measured, length and frame size, because a killed render leaves a
short film behind and a stale one leaves the previous cut.
