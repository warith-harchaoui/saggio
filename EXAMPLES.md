# Examples

[🇫🇷 EXEMPLES.md](EXEMPLES.md) · 🇬🇧 English

Every command shown here is parsed by the real argument parser in the test suite,
and the library snippets whose output is printed are run. A renamed flag or an
arithmetic that drifts turns the build red.

## Contents

- [The five-minute version](#the-five-minute-version)
- [Starting from nothing](#starting-from-nothing)
- [Auditing a repository](#auditing-a-repository)
- [Measuring instead of guessing](#measuring-instead-of-guessing)
- [Projecting onto other hardware](#projecting-onto-other-hardware)
- [Adding a dimension of your own](#adding-a-dimension-of-your-own)
- [Reports](#reports)
- [Keeping it honest in CI](#keeping-it-honest-in-ci)
- [The catalogues](#the-catalogues)
- [The library](#the-library)
- [Exit codes](#exit-codes)

## The five-minute version

```bash
pip install saggio

cd your-project
saggio audit . --country FR -o cost_of_running.yaml
saggio render cost_of_running.yaml -f html -o cost_of_running.html
open cost_of_running.html
```

You now have a cost model where the runtime is a `TODO`, because nothing has been
run yet, and everything derived from it is a `TODO` too. That is the correct state
for a model nobody has measured, and the report says so at the top.

To make it real, measure it:

```bash
saggio audit . --country FR --run -o cost_of_running.yaml
```

## Starting from nothing

Two starters ship with the package.

```bash
# Everything left open, for filling in by hand.
saggio init --template minimal -o cost_of_running.yaml

# A worked example with a real arithmetic chain and a note on every field.
saggio init --template annotated -o cost_of_running.yaml
```

The minimal one states no number at all. That is deliberate: a scaffold full of
plausible defaults tells a lie that survives into a report, while a scaffold full
of `TODO` tells the truth about itself.

Check it whenever you have edited it:

```bash
saggio validate cost_of_running.yaml
```

```
Valid: 0 errors, 1 warning.
Weakest number anywhere in the model: TODO.
```

Warnings never fail a model. A model that admits it is incomplete is being honest,
and this package does not punish that.

## Auditing a repository

```bash
saggio audit . --country FR -o cost_of_running.yaml
```

Reading a repository establishes what it is: its languages, its shape, the
frameworks it imports, how much work a full run performs, and which paid APIs it
calls. All of it is deterministic and quotes the line it came from.

The code that tests a repository is read apart from the code it runs. A suite
writes fixtures, and a fixture that writes `import torch` into a temporary file
is not a project that trains anything. A framework is counted when a line
actually imports it, never when a line merely contains its name, so a table of
framework names in a comment detects nothing. What the suite alone imports is
reported under `frameworks_in_suite_only`, and a service or a model whose only
evidence line is a test file arrives with a `caveat` saying so rather than being
priced as part of the workload.

A detected service looks like this in the model:

```yaml
external_services:
  - key: openai
    name: OpenAI API
    detected_at: app/handlers.py:14
    evidence: from openai import OpenAI
    pricing_source_url: https://openai.com/api/pricing/
    price_per_unit:
      value: null
      status: TODO
      notes: Read the current price from the page above and record what one unit
        of work spends.
```

The price is left open on purpose. A price copied today is wrong by next quarter,
so the audit records where the current one lives instead of pretending to know it.

Audit a repository you have not cloned:

```bash
saggio audit https://github.com/someone/their-project --country FR
```

Ask a local model what shape the work is, if you have Ollama running:

```bash
# On by default. The model classifies; it never supplies a number.
saggio audit . --country FR

# Off.
saggio audit . --country FR --no-llm
```

### From the environment

Two things can be set once instead of passed every time, which is what a container
or a continuous-integration job wants:

| Variable | What it sets |
|---|---|
| `SAGGIO_COUNTRY` | The ISO 3166-1 alpha-2 country the code runs in. Stating it this way is a human assertion, so it counts as `measured`, exactly as `--country` does. |
| `SAGGIO_MODEL` | The Ollama model tag to classify with, instead of the first preferred one installed. |
| `OLLAMA_HOST` | Where Ollama listens, when it is not `http://127.0.0.1:11434`. |

```bash
export SAGGIO_COUNTRY=FR
saggio audit . -o cost_of_running.yaml
```

`--country` wins over the variable, and neither is ever guessed: with no country
from either, the carbon and money figures stay open.

### Pricing the APIs it calls

A price is per *model*, not per vendor: `gpt-4o` and `gpt-4o-mini` are one API at
an eightfold difference. So the audit reads the model identifier out of your code,
with the line that names it, and looks the rates up only when you ask:

```bash
saggio audit . --country FR --fetch-prices -o cost_of_running.yaml
```

```yaml
models_called:
  - model: gpt-4o
    detected_at: app.py:7
    evidence: model="gpt-4o",
    provider: openai
    rates:
      input_cost_per_token:
        value: 2.5e-06
        status: estimated
        unit: USD per input token
        currency: USD
        source_kind: aggregator
        source_url: https://github.com/BerriAI/litellm
        retrieved_date: '2026-09-13'
      output_cost_per_token: {...}     # eight rates in all, for this one model
    units_per_unit_of_work:
      value: null
      status: TODO
```

Three things are deliberate there.

**Nothing parses a web page, and no model is asked what one says.** A price on a
marketing page fails silently and wrongly: a layout change returns the
struck-through old figure, or the enterprise tier, or the cached-input rate
instead of the input rate. Only sources published *as data* are read.

**`source_kind` says how close the figure is to whoever sets it.** `stated` when
a human wrote it, `first-party` when it came from the vendor's own price API,
`aggregator` when it came from somebody else's transcription. The large
language-model vendors publish no price API, so their rates are `aggregator` and
the model says so rather than dressing it up. `saggio diff` fails when a price's
provenance weakens, exactly as it fails when a status weakens.

**The rate is known; the usage is not.** How many tokens one unit of work spends
is not something reading a repository establishes, so it stays `TODO`. The model
shows precisely which half is missing.

Without `--fetch-prices` nothing reaches the network and the audit produces the
same model it produces offline, with the prices left open.

## Measuring instead of guessing

### One command of yours

```bash
saggio measure -- python train.py --steps 100
```

```
Ran: python train.py --steps 100
Exit code: 0
Wall-clock: 12.481 s
Average power: 96.3 W (measured)
     8.204 s  train.py:88(train_step)
     2.106 s  dataloader.py:41(__next__)
```

Power is measured where the machine will say, from two counters rather than one.
On Linux with an Intel processor, the package energy counter gives the processor.
On any machine with an NVIDIA board, the driver gives the accelerator without
needing privileges, either as an accumulated energy counter or, on boards that
keep no running total, as the mean of readings taken every half second across the
run. The accelerator is the one that matters: a processor drawing 50 W beside a
board drawing 300 W is a 350 W machine, and a model that reported the 50 W would
be wrong by a factor of seven.

Whatever answered is named in the report, and so is whatever did not. Both
counters give a figure that says what it leaves out; the accelerator alone says
the processor is missing; neither says so, the report says `not measured` and the
model falls back to an estimate labelled as one. On macOS there is no
unprivileged counter on either side.

The two lines under the total are the function-level profile, and they cost
something to obtain. `cProfile` charges per call, so a call-heavy workload can
take close to twice as long under it, and the wall-clock above is of the profiled
run. The command says so in a warning. When the runtime is what you are after
rather than where it went, take it without the profiler:

```bash
saggio measure --no-profile -- python train.py --steps 100
```

### Putting the measurement into the model

A measurement printed to a terminal is a number nobody kept. `--into` writes it
into a model and recomputes everything that derives from it:

```bash
saggio measure --into cost_of_running.yaml --units 500 -- python predict.py --n 500
```

```
  runtime: not known -> 0.0011 s, TODO -> measured
  time: not known -> 0.0011 s, TODO -> measured
  energy: not known -> 3.93e-08 kWh, TODO -> estimated
  money: not known -> 9.43e-09 USD, TODO -> estimated
  carbon: not known -> 2.2e-06 gCO2e, TODO -> estimated
  whole run: projected from the per-unit costs above
```

This is the step people get wrong by hand. Pasting a runtime into the YAML leaves
the energy, the money and the carbon holding their old values, and a model whose
energy no longer matches its runtime is worse than one that had neither, because
it looks finished. Every figure above is recomputed from the model's own
assumptions, by the same functions the audit uses, and the result is validated
before anything is written.

`--units 500` says the command performed five hundred units of work, so the
recorded runtime is per unit. When the model already knows how much work a whole
run performs, a whole-run projection follows from the per-unit costs.

An analysis is rarely performed once. State how many times yours actually runs —
tuning, debugging, re-runs — as `assumptions.pragmatic_scaling_factor` (the Green
Algorithms paper's term; its worked examples range from 11 to 180), and the next
fold projects `repeated_runs`: the whole run times that factor, derived from both
so the validator watches the arithmetic. The factor is the team's own estimate;
nothing here invents one, and a factor still marked `TODO` yields a projection
whose figures are open rather than absent, so the report shows the question.

Three things are refused rather than written: a command that exited non-zero,
because a failed run measured a failure and a failure has no cost per unit of work;
a model with no scenario to write into; and any result that would no longer
validate. Nothing is half-written, and a fold that changes six numbers prints all
six.

```bash
saggio measure --into cost_of_running.yaml --scenario production -- pytest -q
```

### A slice of somebody else's repository

```bash
saggio consent grant
saggio audit . --country FR --run -o cost_of_running.yaml
```

The audit runs a capped slice of your real entry point. The cap comes from your own
configuration, so the slice covers a known share:

```yaml
projections:
  whole_run:
    description: What the whole run would cost, projected from the slice that was measured.
    costs:
      energy:
        method: Whole run = measured slice / 0.001.
        result:
          value: 0.0016
          unit: kWh
          status: estimated
        assumptions:
          - The remaining work costs the same per unit as the slice that was run.
        limits:
          - A run whose later stages differ in shape will not scale linearly.
```

When there is no entry point with a stated size, the repository's own test suite is
run instead. It covers an unknown share of a real workload, so no whole-run
projection follows from it, and the audit says exactly that.

## Projecting onto other hardware

Most cost models are written on a laptop. Projecting from one needs you to say
which machine the measurement stands for:

```bash
saggio audit . --country FR --run \
    --source-accelerator RTX-4090 \
    --target-accelerator H100
```

```yaml
projections:
  on_other_hardware:
    source: RTX-4090
    target: H100
    runtime:
      method: Runtime on H100 = runtime on RTX-4090 / 3.32, where 3.32 is the
        memory bandwidth ratio, 3350 / 1008 GB/s.
      result:
        value: 13.79
        unit: s
        status: estimated
      bounds:
        fastest: {value: 7.65, unit: s, status: estimated}
        slowest: {value: 13.79, unit: s, status: estimated}
    power_draw:
      value: 700.0
      unit: W
      status: estimated
    costs:
      energy: {value: 0.0032, unit: kWh, status: estimated}
      money: {value: 0.00077, unit: USD, status: estimated}
      carbon: {value: 0.18, unit: gCO2e, status: estimated}
    held_constant: The country, the tariff, the grid carbon intensity and the
      datacenter overhead are the ones stated for this deployment.
```

Two things limit a workload on an accelerator, and a projection that knows about
only one of them is optimistic by construction. Arithmetic throughput limits work
that keeps the tensor cores fed; memory bandwidth limits work that spends its time
moving weights. Between a 4090 and an H100 those ratios are 6.0 and 3.3, so the
answer is a bracket rather than a number. The point estimate is the compute ratio
when the read established the work is compute-bound, the bandwidth ratio when it
established the opposite, and the slower of the two when nothing established
either, because the slower ratio is the longer run and the larger bill.

The projection reaches money and carbon, not just a duration, because a duration
is not the question. It holds the country, the tariff and the grid constant and
says so: running the work on another accelerator usually means running it
somewhere else, and where it runs is what sets the price.

The throughput figure comes from the catalogue column for the precision the work
runs in. Ask for one the catalogue has not been given and it refuses rather than
scaling by a figure about different arithmetic:

```bash
saggio audit . --run \
    --source-accelerator RTX-4090 --target-accelerator H100 --precision fp32
```

```
Read before trusting this model:
  - The catalogue has no peak_fp32_tflops for 'RTX-4090' and 'H100', so there is
    no fp32 ratio to scale by. Add it with `saggio catalog add gpu RTX-4090
    --field peak_fp32_tflops=...` from the vendor datasheet, or measure on the
    target.
```

## Adding a dimension of your own

Declare it at the top of the model and then use it as an ordinary cost key:

```yaml
dimensions:
  - key: "egress"
    label: "Network egress"
    unit: "GB"
    description: "Bytes leaving the datacenter to answer one request."

scenarios:
  - name: "default"
    costs:
      egress:
        value: 0.004
        unit: "GB"
        status: "measured"
        notes: "Median response size, from the access log."
```

Nothing in the package needs to change. The validator holds it to the same rules,
the report gives it a row, and the drift gate watches it. A custom dimension that
overclaims its inputs is an error exactly as carbon would be.

To say that more is better rather than worse:

```yaml
dimensions:
  - key: "throughput"
    label: "Throughput"
    unit: "req/s"
    description: "Requests served per second at steady state."
    higher_is_worse: false
```

The drift gate now fails when it goes *down*.

## Reports

```bash
# For a pull request.
saggio render cost_of_running.yaml -f md -o cost_of_running.md

# For everyone else: one self-contained page, offline, light and dark, EN and FR.
saggio render cost_of_running.yaml -f html -o cost_of_running.html

# For a document. Needs `pip install "saggio[office]"`.
saggio render cost_of_running.yaml -f docx -o cost_of_running.docx
saggio render cost_of_running.yaml -f pdf -o cost_of_running.pdf

# In your own house style.
saggio render cost_of_running.yaml -f docx -o cost_of_running.docx \
    --reference-doc assets/template.docx
```

The HTML page carries its own stylesheet, script, logo, and catalogue data, so it
opens with no network at all. Its what-if panel recomputes carbon and money for a
different country or provider in the browser, from the energy the model already
states. A model with no stated energy gets no panel, because a what-if built on an
invented baseline would be the worst number on the page.

Wherever a report shows a known carbon figure, a line beneath it restates the
number in terms a reader can feel — tree-months, kilometres in an average
European car, a fraction of a reference flight — using the Green Algorithms
coefficients. The restatement never gains confidence: an open figure stays open.

### The team page

```bash
# Every committed model, side by side, on one self-contained page.
saggio dashboard examples/nanoGPT.yaml examples/whisper.yaml examples/fastapi.yaml -o dashboard.html
```

The dashboard leads with the one comparison that is honest across projects: how
much of each model is measured, estimated, or still open, drawn as one stacked
bar per project on the same hundred-percent scale. The costs table follows, per
each project's own unit of work, and the page says plainly that those rows do not
compare with each other — one project's unit is a request, another's is a whole
training run.

## Keeping it honest in CI

```yaml
# .github/workflows/cost.yml
- name: Has the cost of running this drifted?
  run: |
    pip install saggio
    saggio validate cost_of_running.yaml
    saggio audit . --country FR -o /tmp/now.yaml
    saggio diff cost_of_running.yaml /tmp/now.yaml --threshold 10
```

`diff` fails on three things, and the third is the one people forget:

```bash
saggio diff before.yaml after.yaml
```

```
scenarios[0].costs.energy: 0.001 -> 0.0016 (+60.0%), worse
scenarios[0].costs.carbon: measured -> estimated
scenarios[0].costs.water: gone, was measured
3 change(s), 3 past the 10% gate.
```

A number that worsened past the threshold. A status that weakened, because the
model now knows less than it did even when the number is identical. And a quantity
that disappeared, because the usual way a cost stops being reported is that
somebody deleted the field.

## The catalogues

```bash
saggio catalog list gpu
saggio catalog list country --json | jq '.FR'
saggio catalog list service
```

A miss is a normal outcome, and the tool names what it could not find:

```
Read before trusting this model:
  - GPU 'NVIDIA H300' is not in the catalogue; add it with
    `saggio catalog add gpu` once you have a datasheet TDP
```

```bash
saggio catalog add gpu H300 \
    --source-url "https://www.nvidia.com/en-us/data-center/h300/" \
    --retrieved-date 2026-09-12 \
    --field tdp_w=800 \
    --field peak_bf16_tflops=2400
```

The row lands in your own overlay, works immediately, and can be offered upstream
later. Without a source and a date it is refused, which is the rule that keeps the
catalogues worth trusting.

Ask which numbers have gone quietly out of date:

```bash
saggio catalog freshness   # exits 1 when anything is stale
```

Tariffs and grid mixes expire in a month, datasheet wattages in a year. A single
threshold would either nag about a GPU or wave last year's electricity price
through.

## The library

Everything the command line does, it does by calling this.

```python
import saggio

# Audit a repository.
result = saggio.audit(".", options=saggio.AuditOptions(country="FR", use_llm=False))
print(result.report.summary())
for note in result.notes:
    print("-", note)

# Render it.
open("cost.md", "w").write(saggio.render_markdown(result.model))
open("cost.html", "w").write(saggio.render_html(result.model))
```

Validate a model you built yourself:

```python
from saggio import CostModel, validate

model = CostModel.load("cost_of_running.yaml")
report = validate(model)
if not report.ok:
    print(report.to_text())
```

Compute one step of the chain by hand:

```python
from saggio import Quantity, carbon_from_energy, energy_from_runtime

runtime = Quantity(value=3600.0, unit="s", status="measured")
power = Quantity(value=400.0, unit="W", status="estimated")
overhead = Quantity(value=1.2, unit="ratio", status="estimated")

energy = energy_from_runtime(runtime, power, overhead)
carbon = carbon_from_energy(energy, Quantity(value=56, unit="gCO2e/kWh", status="estimated"))

print(energy.value, energy.status)   # 0.48 estimated
print(carbon.value, carbon.status)   # 26.88 estimated
```

The status is `estimated` rather than `measured` even though the runtime was
measured, because the power draw was not. That is the weakest-link rule, applied
by the arithmetic itself.

Ask what this machine is:

```python
from saggio import detect_machine

machine = detect_machine()
print(machine.describe())
for miss in machine.catalog_misses:
    print("-", miss)
```

Compare two models:

```python
from saggio import compare

comparison = compare(before, after, threshold_percent=10.0)
for change in comparison.changes:
    print(change.describe())
if not comparison.passes():
    raise SystemExit(1)
```

## Exit codes

| Code | Meaning |
|---|---|
| `0` | Everything worked. |
| `1` | The model or catalogue failed its own rules. |
| `2` | The command was asked for something it cannot do. |
| `3` | Consent was declined for something the command needed. |
| `4` | An external dependency is missing or failed. |

The distinction between `1` and `2` is the one CI needs: fail the build on the
first, stop and look at the command on the second.
