# The film

Ninety-five seconds of what this package is for, in English and in French,
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
make-film poster film/out/what-it-costs.en.mp4 --out film/out/what-it-costs.en.jpg --at 76.5

make-film verify film/film.yaml --root .                 # do the numbers still hold
make-film scan film/composition/index.en.html --spec film/film.yaml   # anything on screen nobody declared
make-film pitch film/film.yaml --duration 94.98          # problem, then solution, then the one idea
make-film prose film/film.yaml --lang en                 # the named machine tics
sprezzature-audio-audit film/out/what-it-costs.en.vtt --line-chars 58
sprezzature-audio-audit film/out/what-it-costs.fr.vtt --line-chars 58 --cps 20
```

Both tracks come back clean, and the two commands differ on purpose.

`--line-chars 58` rather than the Netflix default of 42: 58 is the budget the
caption writer in `sprezzature-video` splits a line at, so it is the number
that actually governs this file.

`--cps 20` on the French track, and nothing on the English one. The English cut
reads inside the 17-characters-a-second ceiling the audit defaults to, which is
Netflix's figure for adult content: it averages 15.5 and peaks at 16.6. The
French cut does not, and at 17 it reports forty-seven findings over fifty-five
cues. That is not this script. The French cut averages 17.7 characters a second
and never exceeds 19.9, because French spends more characters on the same
sentence, so an English-calibrated ceiling flags a track a French reader
follows perfectly well. The audit's own help says the defaults are conventions
rather than laws and that each one is a flag, which is the licence being used
here — so 20 is the ceiling that measured peak asks for, written down rather
than the flag dropped, and the next person can disagree with it.

The one finding that was a real defect was fixed rather than reclassified: a
cue that held **d'exécution,** alone for 0.755 seconds, because the line split
mid-phrase. The French call to action is three short sentences now, and each
gets its own breath.

Two further gates are worth running and one of them cannot answer here:

```bash
make-film assets film/film.yaml --tree . --repo .   # can a clone rebuild this
make-film calque film/film.yaml --from en --to fr   # is the second cut a translation
```

`assets` reports 9 of 9 in hand: nothing this film is built from exists only on
the machine that built it.

`calque` scores this film 0.89 and will go on doing so. It compares the two cuts
position by position on how many sentences a line holds and which numerals it
carries — and this film's narration is split one sentence to a line with no
numerals anywhere, so 26 of 27 English lines and 25 of 25 French ones reduce to
the same `(1, ())`. It is comparing two near-constant sequences, which is the
case its own documentation excludes: *a film whose lines are each one sentence
with no numbers will score high and may be perfectly composed.* The score is
not evidence about this French. Read the two cuts side by side instead, which
is what the gate asks for in any case.

## Rendering

The frames are grabbed with Playwright and assembled with ffmpeg rather than
through Hyperframes. Both are named by `sprezzature-video` as renderers behind
the same seam, and the page this film is published on is offline-first with no
build step of its own, so the shorter dependency chain was the one to take.

Frames already on disk are kept, so a render that dies at frame 900 resumes at
frame 900. That holds only while the page is the same page, and it once did not:
re-rendering a recut French cut reshot the 63 frames the longer cut had added,
kept 2139 from the previous one, and assembled a film that played, carried a
plausible duration, and showed the old script for its first eighty-nine seconds.
No gate here reads pixels, so none of them could have caught it. The frames now
carry a hash of the composition they came from in `frames/<lang>/.composition`
and are dropped when it changes — if a render reports far fewer frames taken
than are on disk, that is the number to look at.
