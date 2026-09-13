

# saggio

[🇫🇷 LISEZMOI.md](LISEZMOI.md) · 🇬🇧 English

**What does it cost to run your code?** Money, time, energy, carbon, water, and
any other dimension you decide to watch, per unit of work, with every number
saying how far it can be trusted.

<p align="center">
  <img src="assets/logo.png" alt="saggio" >
</p>



The answer is a YAML file you commit next to the code, and reports rendered from
it. The file is reviewable in a pull request, the reports are readable by people
who will never open a terminal, and neither of them is allowed to state a number
without saying where it came from.

```bash
pip install saggio

saggio audit . --country FR --run -o cost_of_running.yaml
saggio render cost_of_running.yaml -f html -o cost_of_running.html
```

## The one idea

Every number carries a **status**:

| Status | What it means |
|---|---|
| `measured` | A counter on the machine said so. |
| `estimated` | A sourced formula or a published figure said so. |
| `placeholder` | The field is being held open. It is not a number. |
| `TODO` | A human has to supply this before the model can be trusted. |

And every derived number names the numbers it came from:

```yaml
costs:
  carbon:
    value: 0.0014
    unit: "gCO2e"
    status: "estimated"
    derived_from: ["scenarios[0].costs.energy", "assumptions.grid_carbon_intensity"]
```

From there the **weakest-link rule** follows, and the validator enforces it: a
derived value may never claim to be better founded than the worst of its inputs.
Measure the runtime and the energy becomes measured on its own. Leave the country
unstated and the carbon figure stays open, because nobody knows it yet.

Three properties fall out of writing it this way, and they are the reason for the
design:

- **Nothing can hide.** The validator walks the whole file. Any number outside a
  quantity is an error, wherever it is and whatever block it is in, so an extra
  block cannot smuggle a figure past the rules.
- **The rule is general.** Because the derivation is data rather than code, a
  dimension you invented this morning is checked exactly as carefully as carbon.
- **Nothing is invented.** An unresolved country gives a `TODO`, not a zero. A
  provider that publishes no water figure gives a `TODO`, not a plausible one. A
  run that failed projects to nothing at all.

## What it does

**Reads your repository.** Languages, workload shape, frameworks, how much work a
full run performs, which paid APIs you call and on which line. All of it
deterministic, all of it quoting its evidence.

**Runs a slice of it, if you let it.** With `--run`, and after you have agreed
once, it executes a capped slice of your real entry point, times it, reads the
machine's power counter where the operating system offers one, and profiles where
the time went. The size the slice covers is read from your own configuration, so
projecting to a whole run is arithmetic rather than a guess.

**Looks things up rather than assuming them.** What a GPU draws, what a kilowatt
hour emits in Poland, what overhead a datacenter adds, where an API publishes its
prices: sourced YAML catalogues, each row carrying the URL it came from and the
date somebody read it, each one going stale on a schedule that matches how fast
that kind of fact actually moves.

**Projects, and says what it assumed.** From a measured slice to a whole run. From
one accelerator to another, by peak-throughput ratio, refusing when the workload's
precision is one the catalogue cannot speak to and saying which one it is.

**Writes reports that people read.** Markdown for a pull request. A single
self-contained HTML page for everyone else: offline, light and dark, English and
French, with a panel that recomputes the model for a different country in the
browser. Word and PDF through `md2star` when a document is what somebody wants.

**Fails your build when a cost drifts.** `diff` compares two models and fails on a
cost that worsened past a threshold, on a status that weakened, and on a quantity
that quietly disappeared.

## Install

```bash
pip install saggio
```

Three runtime dependencies, on purpose. [`os-helper`](https://pypi.org/project/os-helper/)
answers every question about the machine and the operating system, on macOS,
Linux, and Windows alike. PyYAML parses the models and the catalogues.
`platformdirs` finds the per-user config directory. Everything else this package
does, it does itself.

Word and PDF need one more thing, and only if you want them:

```bash
pip install "saggio[office]"
```

For conda:

```bash
conda env create -f environment.yaml
conda activate env-for-saggio
```

## Use it

```bash
# Start from a worked example, or from a scaffold with everything left open.
saggio init --template annotated -o cost_of_running.yaml

# Check it against the schema and the honesty rules.
saggio validate cost_of_running.yaml

# Read a repository and write a model for it.
saggio audit . --country FR -o cost_of_running.yaml

# Read it, and run a capped slice to measure what it really costs.
saggio audit . --country FR --run -o cost_of_running.yaml

# What would this cost on an H100, from a measurement taken on a 4090?
saggio audit . --country FR --run \
    --source-accelerator RTX-4090 --target-accelerator H100

# Measure one command of your own.
saggio measure -- python train.py --steps 100

# Turn the model into something a person reads.
saggio render cost_of_running.yaml -f html -o report.html

# Fail the build when a cost has drifted.
saggio diff main.yaml branch.yaml --threshold 10
```

The library is the same thing without the printing:

```python
import saggio

result = saggio.audit(".", options=saggio.AuditOptions(country="FR"))
print(result.report.summary())
print(saggio.render_markdown(result.model))
```

[`EXAMPLES.md`](EXAMPLES.md) is the cookbook.

## Running your code, and what that means

Measuring what code costs to run means running it. There is no sandbox here and
none is pretended: your repository under study executes as you, with your
permissions and your network access.

So consent is explicit, asked for once, and recorded where you can find and
revoke it:

```bash
saggio consent grant
saggio consent revoke
```

Without it, `--run` does nothing and the audit proceeds on reading alone. A
session with no terminal is refused rather than defaulted, so a build server can
never agree on your behalf.

## What it never does

It never puts a number in a file that nobody chose. The country is stated by a
person or inferred from the machine's timezone and labelled as an inference; it is
never read off a locale and written down as fact.

It never copies an API price into your model. Prices move, and a stale one shipped
as authoritative is exactly the dishonesty this package exists to prevent. It
records which service you call, the line of code that proves it, and the page
where the current price lives.

It never lets a language model supply a number. A local model, when you have one
running, is asked what shape of work your repository does and nothing else. Its
answer is labelled with the model's name and marked low confidence. Every number
comes from a file you can open or a counter you can read.

And it never counts what it cannot count. Making the hardware, the people, the
office, the idle capacity: all of it is listed in the report as excluded, because
a footprint that quietly leaves out the largest term is worse than no footprint.

## Where the numbers come from

The method is [Green Algorithms](https://doi.org/10.1002/advs.202100707)
(Lannelongue, Grealey, and Inouye, 2021): power multiplied by time is energy,
energy multiplied by a grid intensity is carbon, energy multiplied by a tariff is
money, energy multiplied by a water usage effectiveness is water.

One distinction is kept that is easy to lose. The machine draws one amount; the
building draws that amount multiplied by its power usage effectiveness. Carbon and
money follow the building, because that is what the meter counts. Water follows
the machine, because water usage effectiveness is defined per kilowatt-hour of IT
load and using the building figure would count the cooling twice.

Hardware wattages, grid intensities, tariffs, and datacenter overheads live in
[`saggio/data/`](saggio/data/), one row each
with its source and its date. Missing a row is a normal outcome, and the tool
tells you which one by name:

```bash
saggio catalog list gpu
saggio catalog add gpu H300 \
    --source-url https://www.nvidia.com/... --retrieved-date 2026-09-12 \
    --field tdp_w=800 --field peak_bf16_tflops=2400
saggio catalog freshness   # exits 1 when a number has gone stale
```

A row cannot be added without a source and a date. That rule is what keeps the
catalogues worth trusting.

## How it is put together

```
model/      What a cost model means: the taxonomy, the quantity, the dimensions,
            the schema, the validation. No I/O, no network, no subprocess.
catalog/    Sourced facts about the world, and the rule that a row without
            provenance does not enter.
estimate/   Facts and measurements into numbers: the machine, the deployment,
            the Green Algorithms chain, the projections.
analyze/    What a repository is: reading it, running a slice of it, and asking a
            local model about its shape (never about its numbers).
auditor.py  The whole job, in one function.
report/     Markdown, HTML, Word, PDF.
cli/        Argument parsing and printing. Nothing else.
```

The dependency direction only points one way, so the command line can do nothing a
library caller cannot.

The HTML report's own pieces are authored outside the package, in
[`reporting/`](reporting/): the document shell with the tokens the renderer
fills, the stylesheet, the script, the translations. They are a stylesheet and a
script there rather than strings quoted inside Python, and `reporting/sync.py`
copies them into the package that ships them, with a test that fails the build if
the two ever drift apart. Copy that trio to render reports of your own shape.

## Contributing

[`CONTRIBUTING.md`](CONTRIBUTING.md) has the details. The short version: add a
catalogue row with its source and its date, or a test that pins a behaviour you
care about. [`CODING.md`](CODING.md) is the style this repository is written in.

```bash
pip install -e ".[dev]"
pytest          # 1000+ checks, including every example in every docstring
ruff check .
ruff format --check .
```

## Related work

[`LANDSCAPE.md`](LANDSCAPE.md) places this alongside CodeCarbon, Green Algorithms,
Scaphandre, PowerAPI, Cloud Carbon Footprint, and the rest of the field, and is
honest about where each of them is the better tool.

## The name

*Saggio* is Italian for the assay of a metal: you draw a sample, you determine
its fineness, and the result is stamped with who determined it and when. It also
means an essay, and it means judicious. All three are the point. This tool draws
a capped sample of a real run, reports how well founded each number is, and
records where every figure came from and on what date somebody read it.

## Licence

[BSD 3-Clause](LICENSE). Warith Harchaoui, Ph.D.
