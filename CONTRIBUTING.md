# Contributing

Thank you for looking. The most useful contributions to this project are small and
specific, and two of them need no Python at all.

## The two easiest, and most valuable, contributions

### A catalogue row

The package cannot know every accelerator, every national grid, or every paid API.
When it meets one it does not know, it says so by name:

```
GPU 'NVIDIA H300' is not in the catalogue; add it with
`saggio catalog add gpu` once you have a datasheet TDP
```

Adding it is one command and one pull request:

```bash
saggio catalog add gpu H300 \
    --source-url "https://www.nvidia.com/en-us/data-center/h300/" \
    --retrieved-date 2026-09-13 \
    --field tdp_w=800 \
    --field peak_bf16_tflops=2400
```

That writes it to your own overlay, where it works immediately. To offer it
upstream, copy the row into the matching file under
`saggio/data/` and open a pull request.

**A row without a source and a date will not be merged.** Not because of process,
but because a catalogue of unsourced numbers is folklore, and this package exists
to be the opposite of that. Link the vendor datasheet, the regulator's page, the
provider's own sustainability report. "Everyone knows an A100 is 400 watts" is not
a source.

### A number that is wrong

If a figure in `saggio/data/` is wrong or has gone stale, say so,
and say what it should be and where you read that. Corrections are the highest
value thing here, and they are welcome even without a patch.

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

The dependency direction only points one way: `cli` may import `report`, `report`
may import `model`, and nothing in `model` imports anything above it. A change that
needs an exception to that is a change that needs a conversation first.

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

## Changing the schema

The cost-model schema is versioned separately from the package. Within a major
line it only grows, so a model somebody wrote last year keeps validating.

- Adding an optional field: fine, bump the minor.
- Adding a required field, renaming one, or changing what a value means: that is a
  major bump, and it needs a reason worth breaking every committed model for.

If you add a field, add it to the annotated template too, so a reader meets it
with a sentence explaining what it is for.

## Reporting something

An issue is most useful with the model that shows it. `cost_of_running.yaml` is
plain YAML and safe to paste; check first that yours carries nothing private, since
a model can name internal services and repository paths.

For anything with a security dimension, write to the address in `pyproject.toml`
rather than opening a public issue.

## Licence

By contributing you agree that your contribution is licensed under the
[BSD 3-Clause](LICENSE) licence, the same as the rest of the project.
