# Contributing

[🇫🇷 CONTRIBUER.md](CONTRIBUER.md) · 🇬🇧 English

Thank you for looking. The most useful contributions to this project are small
and specific. Three of them need no Python at all.

## The three easiest contributions, and the most valuable

### A catalogue row

The package cannot know every accelerator, every national grid, or every paid API (application programming interface).
When it meets one it does not know, it says so by name:

```
GPU 'NVIDIA H300' is not in the catalogue; add it with
`saggio catalog add gpu` once you have a datasheet TDP
```

Adding it is one command and one pull request:

```bash
saggio catalog add gpu H300 \
    --source-url "https://example.invalid/nvidia-h300-datasheet" \
    --retrieved-date 2026-09-13 \
    --field tdp_w=800 \
    --field peak_bf16_tflops=2400
```

That writes it to your own overlay, where it works immediately. To offer it
upstream, copy the row into the matching file under
`saggio/data/` and open a pull request.

**A row without a source and a date will not be merged.** Not because of
process, but because a catalogue of unsourced numbers is folklore, which this
package exists to be the opposite of. Link the vendor datasheet, the regulator's
page, the provider's own sustainability report. "Everyone knows an A100 is 400
watts" is not a source.

**And a manufacturing footprint needs one thing more: what one of it is.** This
is the field people expect a tool to fill in for them, and the one a tool
cannot. NVIDIA's PCF (product carbon footprint) summaries state, in prose a
parser would find on the first try, that the cradle-to-gate footprint of an HGX
H100 baseboard is 1,312 kgCO2e — 2,274 for an HGX B200. This catalogue's unit is
**one accelerator**. The divisor is on a different page, in a spec table reading
*"Form Factor: 8x NVIDIA H100 SXM"*, and the knowledge that it is needed at all
comes from the schema rather than from the document.

A row carrying `embodied_kgco2e: 1312` under the key `H100` would be wrong by a
factor of eight and would look impeccable: a real vendor URL (Uniform Resource
Locator), a real date, a number genuinely printed in the document. That is the
worst output this package can produce, and it is why **there is no verb that
reads a PCF and proposes a row**. Reading the number is the easy half; knowing
what one unit of the destination is, and writing down that you divided, is the
half that has to be done by somebody who can be asked why.

So `embodied_scope` is required, and has to begin by naming one unit — *"One SXM
40GB card…"*, *"One of the eight GPUs on an HGX H100 baseboard: 1312 kgCO2e…
divided by eight"*. A contract test refuses a footprint without it.

### A number that is wrong

If a figure in `saggio/data/` is wrong or has gone stale, say so, with what it
should be and where you read that. Corrections are the highest value thing here,
welcome even without a patch.

### A language

The third contribution that needs no Python. Two files, one top-level code in
each:

- `reporting/i18n.yaml` — every label on the HTML (HyperText Markup Language) report. Word them however
  reads best; they are read by people.
- `saggio/data/prompts.yaml` — the sentence asking a local model to write its
  one sentence of prose in your language. This one is not free text: it has to
  go on naming `dominant_operation`, `reasoning` and `workload_kind` exactly as
  they are, because the answer is matched against those names literally and a
  translated key is an answer this package throws away.

Then `python3 reporting/sync.py`, so the packaged copy of the report assets
matches the authored one, then the tests. Contract tests refuse a language only
one of the two files has, and a language missing any key the English table has.
Nothing else changes: the report's language button, `saggio audit --language`,
the HTTP (HyperText Transfer Protocol) field and the agent tool are all built
from what those files contain.

## Changing the code

```bash
git clone https://github.com/warith-harchaoui/saggio
cd saggio
pip install -e ".[dev]"

pytest                   # the whole suite, including every docstring example
ruff check .
ruff format --check .
```

All three have to pass. The test suite runs the doctests as well as the tests, so
an example in a docstring that stops being true fails the build; that is the point
of writing them.

### What a change needs

**A test that fails without it.** For a bug, a test that reproduces it. For a
feature, a test that pins the behaviour you want. A pull request with no test is a
claim that nobody can check later.

**Docstrings in the style of the file you are editing.** Every function, private
ones included, has a NumPy-style docstring with a runnable example.
[`CODING.md`](CODING.md) says why and shows the shape.

**A comment saying why, where the why is not obvious.** The code in this repository
explains its reasoning where the reasoning was not forced. Keep that habit; a
comment restating what the next line does is worse than no comment.

**Nothing that guesses.** This is the one rule that will get a pull request sent
back regardless of how good the rest of it is. If a number cannot be established,
the answer is a `TODO` with a sentence saying what would resolve it, never a
plausible default, never a zero. "We have to put something there" is precisely the
reasoning this package is built to refuse.

## Where things live

```
model/       What a cost model means. No I/O, no network, no subprocess. A change
             here is a schema change; say so in the pull request.
catalog/     Sourced facts and the provenance rule.
estimate/    Facts and measurements into numbers.
analyze/     Reading a repository, running a slice of it, asking a local model.
auditor.py   The whole job.
report/      Markdown, HTML, Word, PDF. It assembles; it does not author.
cli/         Argument parsing and printing, and nothing else.
reporting/   What the HTML report is made of: the document shell with the tokens
             the renderer fills, the stylesheet, the script, the translations.
             Files of their own kind, not Python strings.
```

The dependency direction only points one way: `cli` may import `report`,
`report` may import `model`, and nothing in `model` imports anything above it. A
change that needs an exception to that is a change that needs a conversation
first.

`reporting/` sits outside the package because its files are edited as a
stylesheet, a script and an HTML shell rather than as Python. The renderer reads
them through `importlib.resources`, which only reaches inside the package, so a
copy lives at `saggio/data/report/` and that copy is what the
wheel ships. Edit the originals, then:

```bash
python reporting/sync.py
```

A contract test runs `python reporting/sync.py --check`, so a change made in the
packaged copy fails the build rather than shipping.

`docs/api.md` works the same way, in the other direction: it is written *from*
the docstrings rather than beside them. Change a public signature or the first
line of a public docstring, then:

```bash
python docs/sync_api.py
```

A contract test runs `python docs/sync_api.py --check`, so a reference that has
drifted away from the package fails the build rather than misleading a reader.

`docs/check_links.py` is the third of these, and the only one that reaches the
network. Run it before a release:

```bash
python docs/check_links.py
```

It follows every link the repository asks a reader to follow — in the pages and
in the catalogue rows beside the numbers they vouch for — then sorts the answers
rather than reducing them to pass or fail. A 403 from Legifrance or ResearchGate
is a robot filter, not a dead document, and calling it dead would be the worse
lie. Only a server stating that it holds no such document fails the run.

Two of its categories are worth reading even when the exit code is zero:
**redirected** means the document moved and the citation did not follow — that
is how the Gemini pricing row was found pointing at a page Google had retired —
and **no reply at all** means a host that may simply be slow today.

A link that *illustrates a command* rather than vouching for a number belongs on
a domain reserved for documentation (`example.invalid` and the rest of Request
for Comments (RFC) 2606), which the checker skips by rule. This is not a
convenience: an invented source on a real vendor's domain is indistinguishable
from a stale one, which is the worst a citation can be. Four pages carried
`nvidia.com/en-us/data-center/h300/` for a graphics card that does not exist.

## Changing the schema

The cost-model schema is versioned separately from the package. Within a major
line it only grows, so a model somebody wrote last year keeps validating.

- Adding an optional field: fine, bump the minor.
- Adding a required field, renaming one, or changing what a value means: that is
  a major bump, needing a reason worth breaking every committed model for.

If you add a field, add it to the annotated template too, so a reader meets it
with a sentence explaining what it is for.

## Reporting something

An issue is most useful with the model that shows it. `cost_of_running.yaml` is
plain YAML (YAML Ain't Markup Language) and safe to paste; check first that yours carries nothing private, since
a model can name internal services and repository paths.

For anything with a security dimension, write to the address in `pyproject.toml`
rather than opening a public issue.

## Licence

By contributing you agree that your contribution is licensed under the
[BSD 3-Clause](LICENSE) licence (Berkeley Software Distribution), the same
as the rest of the project.
