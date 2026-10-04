# saggio

[🇫🇷 LISEZMOI.md](https://github.com/warith-harchaoui/saggio/blob/master/LISEZMOI.md) · 🇬🇧 English

**What does it cost to run your code?** Money, time, energy, carbon, water, and
any other dimension you decide to watch, per unit of work, with every number
saying how far it can be trusted.

<p>
  <img src="https://raw.githubusercontent.com/warith-harchaoui/saggio/master/assets/logo.png" alt="saggio logo">
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

And the derivation is **checked, not just declared**. The validator parses every
unit down to its base dimensions — a watt *is* a joule per second — and recomputes
the value from its named inputs, multiplying them and, where that cannot reach the
stated unit, dividing: amortising an embodied footprint over a lifetime is a
division, and the model names the lifetime among its inputs just the same. A value
more than a percent from what its inputs give is an error. Where several readings
reach the unit and the units cannot say which was meant, a value matching none of
them is still an error, because it is wrong under every reading. A unit no
arrangement of the inputs can produce is an error needing no arithmetic at all.
The mistake this closes is the worst-looking one: a number orders of magnitude
out, carrying a perfectly correct list of the inputs it supposedly came from,
reads as better founded than anything else on the page. And where any unit
involved is one the package does not know — a dimension you registered this
morning — it says nothing rather than inventing a rule.

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
once, it executes a capped slice of your real entry point, times it, reads
whatever energy counters the machine publishes to an ordinary user, and profiles
where the time went. On Linux that is the powercap tree, memory zone included,
and the graphics driver's own sensor; on an Apple Silicon Mac it is the chip's
own counters, read without a password; on any machine with an NVIDIA board it is
the driver. `saggio power` says which of them answer here, and prints what it
would take to open the ones that do not — without ever opening them itself. The
size the slice covers is read from your own configuration, so projecting to a
whole run is arithmetic rather than a guess.

**Looks things up rather than assuming them.** What a GPU draws, what a kilowatt
hour emits in Poland, what overhead a datacenter adds, where an API publishes its
prices: sourced YAML catalogues, each row carrying the URL it came from and the
date somebody read it, each one going stale on a schedule that matches how fast
that kind of fact actually moves.

**Projects, and says what it assumed — or measures the assumption away.** From a
measured slice to a whole run.
From one accelerator to another, and all the way to money and carbon rather than
stopping at a duration. The first projection rests on the work being uniform, and `--scaling-steps 3`
replaces that assumption with a number: three slices of different sizes, a fitted
exponent, and a refusal to project at all when the fit says the slices are not
measuring one consistent behaviour. That second projection is a bracket, not a number: work is
limited by arithmetic throughput or by memory bandwidth, the two ratios differ by
more than a factor of two between an A100 and an H100, and reporting the compute
ratio alone would understate the bill by a third. It refuses outright when the
catalogue has no throughput figure for the precision the work runs in.

**Counts the hardware, not only the electricity.** Manufacturing one HGX H100
baseboard emits 1,312 kgCO2e before it computes anything, and a model that
reports only the energy is claiming that figure is zero. The `embodied_carbon`
dimension amortises a published product carbon footprint over the share of the
hardware's life one unit of work reserved — which completes the four terms of
[ISO/IEC 21031:2024](https://greensoftware.foundation/standards/sci/), the
Software Carbon Intensity standard, whose shape this package already had.

The arithmetic is complete; **the catalogue is not, and will not pretend to
be.** Seven footprints ship: three accelerators out of 25 rows and four
processors out of 12. Everything else reports `TODO` with a sentence saying
nobody has read a footprint for it, which is not the same as it having been free
to build. The reason the gap is that wide is that most vendors publish a
footprint for a whole server and not for the part inside it, and the one open
database that covers processors answers for a chip it does not have by
substituting the nearest one it does — asked for an Apple M4 Max it returns an
Apple M1 Max, four generations earlier, with no warning. Those answers are
refused by name rather than imported.
[`STANDARDS.md`](https://github.com/warith-harchaoui/saggio/blob/master/STANDARDS.md) has the table, the boundary of every figure, and
the eight refusals with their reasons.

**Writes reports that people read.** Markdown for a pull request. A single
self-contained HTML page for everyone else: offline, light and dark, English and
French, with a panel that recomputes the model for a different country in the
browser and a chart of how the grid would move the carbon elsewhere. Word and PDF
through `md2star` when a document is what somebody wants, their title block
naming what produced them and the date they were produced — which is not the
date the model last changed, and says so. Every known carbon
figure is also restated in terms a reader can feel — tree-months of
sequestration, kilometres in an average car, a fraction of a Paris–London
flight — with the [Green Algorithms](https://doi.org/10.1002/advs.202100707)
coefficients, and without gaining any confidence in the restating: an open figure
stays open, and a measured one reads `estimated`, because the tree is an average
tree.

**Shows the team, not just the project.** `saggio dashboard` renders every
committed cost model on one page. It leads with the one comparison that is honest
across projects — how much of each model is measured, estimated, or still open —
and says plainly that the cost rows, each per its own unit of work, do not
compare with each other.

**Fails your build when a cost drifts.** `diff` compares two models and fails on a
cost that worsened past a threshold, on a status that weakened, and on a quantity
that quietly disappeared.

## Install

```bash
pip install saggio
```

**Linux and macOS.** Windows is out of scope, deliberately and for good: it
publishes no vendor-neutral processor energy counter to an unprivileged process,
no machine-wide processor-time total this package can read, and no POSIX resource
accounting for a child. A tool whose whole proposition is that a number says how
far it can be trusted should not pretend to support a platform where it could
only ever estimate, so `import saggio` there raises rather than half-working.

Three runtime dependencies, on purpose. [`os-helper`](https://pypi.org/project/os-helper/)
answers every question about the machine and the operating system on both of
them. PyYAML parses the models and the catalogues.
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

# What is this machine, and does the catalogue know its parts?
saggio machine

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

[`EXAMPLES.md`](https://github.com/warith-harchaoui/saggio/blob/master/EXAMPLES.md) is the cookbook, [`MEASURING.md`](https://github.com/warith-harchaoui/saggio/blob/master/MEASURING.md) is
which counters this machine will let you read and what each of them covers,
[`GALLERY.md`](https://github.com/warith-harchaoui/saggio/blob/master/GALLERY.md) is what it says about nanoGPT, Whisper, DINOv2,
FastAPI and Airflow with the files committed beside it,
[`docs/api.md`](https://github.com/warith-harchaoui/saggio/blob/master/docs/api.md) is every name `import saggio` gives you, and
[`docs/`](https://github.com/warith-harchaoui/saggio/blob/master/docs/README.md) is the map of the rest.

[`ANALYSIS.md`](https://github.com/warith-harchaoui/saggio/blob/master/ANALYSIS.md) is the investigation behind the division of labour
above: what static and dynamic analysis have actually been shown to deliver for
complexity and for consumption, which of it belongs here, and which of it is
refused and why.

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

It never parses a pricing page, and never asks a model what one says. With
`--fetch-prices` it reads rates from sources published *as data*, records which
model the code names and on which line, and stamps every rate with where it was
read and when. A rate from the vendor's own price API and a rate from somebody
else's transcription are both `estimated`, so each one also carries a
`source_kind` saying which it is, and the drift gate fails when that weakens.
Without the flag nothing reaches the network and the price stays open, pointing
at the page where the current number lives.

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
[`saggio/data/`](https://github.com/warith-harchaoui/saggio/tree/master/saggio/data), one row each
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
diff.py     What changed between two models, and whether it fails the gate.
templates.py  The starter models the wheel ships.
report/     Markdown, HTML, Word, PDF.
cli/        Argument parsing and printing. Nothing else.
```

The dependency direction only points one way, so the command line can do nothing a
library caller cannot.

The HTML report's own pieces are authored outside the package, in
[`reporting/`](https://github.com/warith-harchaoui/saggio/tree/master/reporting): the document shell with the tokens the renderer
fills, the stylesheet, the script, the translations. They are a stylesheet and a
script there rather than strings quoted inside Python, and `reporting/sync.py`
copies them into the package that ships them, with a test that fails the build if
the two ever drift apart. Copy that trio to render reports of your own shape.

## Contributing

[`CONTRIBUTING.md`](https://github.com/warith-harchaoui/saggio/blob/master/CONTRIBUTING.md) has the details. The short version: add a
catalogue row with its source and its date, or a test that pins a behaviour you
care about. [`CODING.md`](https://github.com/warith-harchaoui/saggio/blob/master/CODING.md) is the style this repository is written in.

```bash
pip install -e ".[dev]"
pytest          # 1000+ checks, including every example in every docstring
ruff check .
ruff format --check .
```

## Related work

[`LANDSCAPE.md`](https://github.com/warith-harchaoui/saggio/blob/master/LANDSCAPE.md) places this alongside CodeCarbon, Green Algorithms,
Scaphandre, PowerAPI, Cloud Carbon Footprint, and the rest of the field, and is
honest about where each of them is the better tool.

## The name

*Saggio* is Italian for the assay of a metal: you draw a sample, you determine
its fineness, and the result is stamped with who determined it and when. It also
means an essay, and it means judicious. All three are the point. This tool draws
a capped sample of a real run, reports how well founded each number is, and
records where every figure came from and on what date somebody read it.

## Licence

[BSD 3-Clause](https://github.com/warith-harchaoui/saggio/blob/master/LICENSE). Warith Harchaoui, Ph.D.
