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

### What this machine will let you read

Before a measurement is worth anything, it is worth knowing what this machine is
willing to say, and to whom.

```bash
saggio power
```

```
[reads] Linux powercap (RAPL)
    covers: the processor package and its memory
    Zones answering: dram, package-0, package-1.

[reads] NVIDIA driver (nvidia-smi)
    covers: the whole accelerator board
    The board keeps an accumulated energy counter, which is read exactly.

[absent] Linux graphics driver (amdgpu, i915, xe)
    covers: the graphics device
    No graphics device here publishes a power sensor through sysfs.

[root-only] Baseboard controller (IPMI, DCMI, Redfish)
    covers: the whole node, including fans, storage, and the power supply's losses
    ...
```

Four states, and only one of them is a question for you. `absent` is a property
of the machine, not a failure. `root-only` is a counter this package will not
reach for, on purpose. `reads` needs nothing from anybody. `blocked` is the
interesting one: the counter is here and closed to *you*, which on Linux since
5.10 is the default, because sampling it fast enough recovers what other
processes are computing — the PLATYPUS attack, CVE-2020-8694. So the remedy is
printed rather than run, with the reason beside it:

```
[blocked] Linux powercap (RAPL)
    covers: the processor package, and the memory where a zone exists for it
    2 zone(s) are here and closed to you. Linux has kept this counter root-only
    since 5.10 on purpose: sampled fast enough it leaks what other processes are
    computing (CVE-2020-8694, the PLATYPUS attack). Opening it to a group is a
    judgement about who shares this machine, which is why it is printed here
    rather than done for you.
    to open it: Until the next reboot:  sudo chmod a+r /sys/class/powercap/*/energy_uj
        Across reboots, a udev rule that touches the energy files and nothing else.
```

Nothing here escalates. No `sudo`, no password prompt, no quiet fall-back to a
tool that would ask for one. Whether to reopen a published side channel on a
machine you may share is a decision, and it stays yours.

To watch the counters work before a run depends on them, ask for a measurement
of the machine itself:

```bash
saggio power --seconds 2
```

```
Over 2s this machine drew 27.2 W (54.3 J) through system-on-chip, memory.
```

That figure is the *machine*, not your program: everything else running is in
it. A laptop drawing 27 W while doing nothing of yours is exactly why a slice
timed on a busy machine is not the slice's own cost, and why every figure this
package prints says what it covers.

### One command of yours

```bash
saggio measure -- python train.py --steps 100
```

```
Ran: python train.py --steps 100
Exit code: 0
Wall-clock: 12.481 s
Average power: 96.3 W (measured)
  machine at rest before it: 18.7 W
  added by this slice: 77.6 W
     8.204 s  train.py:88(train_step)
     2.106 s  dataloader.py:41(__next__)
```

Three power figures, because a counter measures the *machine* and not your
program. The machine is watched for a second before the slice starts, and the
difference is what the slice added. On a laptop with a browser and an indexer
running, that difference is the only one of the three worth quoting.

The subtraction assumes something nobody checked — that the rest of the machine
kept doing what it was doing — so the assumption is written into the model
beside the number. Two cases get said out loud instead: a machine already
drawing more than half of the total is called out as busy, and a machine that
grew *quieter* during the slice yields no marginal figure at all, because
whatever else was running stopped and the baseline was never the slice's floor.

On a machine you know is quiet, skip it and save the second:

```bash
saggio measure --baseline 0 -- python train.py --steps 100
```

An audit takes the same knob, and a scaling series takes **one** baseline for the
whole ladder rather than one per rung — the rungs run back to back on the same
machine, so three baselines would measure the same idle three times:

```bash
saggio audit . --country FR --run --baseline 0 --scaling-steps 3 -o cost_of_running.yaml
```

On a machine that publishes no counter at all there is nothing to skip: the
baseline returns "not measured" immediately rather than watching an instrument
that does not exist for a second first.

Power is measured from whichever counters this machine publishes, which
`saggio power` above has already listed. On Linux that is the powercap tree —
every package, the `psys` zone in preference to the packages it contains, and the
memory zone beside them, whose energy is *not* inside the package figure. On an
Apple Silicon Mac it is the chip's own counters: processor cores, graphics cores,
neural engine, and memory, read without a password. On any machine with an NVIDIA
board the driver answers, either as an accumulated energy counter or, on boards
that keep no running total, as the mean of readings taken every half second
across the run; where NVIDIA is not the board present, Linux's own `amdgpu`,
`i915`, and `xe` drivers publish the same thing through sysfs to an ordinary
user.

The accelerator is usually the one that matters: a processor drawing 50 W beside
a board drawing 300 W is a 350 W machine, and a model that reported the 50 W
would be wrong by a factor of seven.

Whatever answered is named in the report, and so is whatever did not. Both
counters give a figure that says what it leaves out; the accelerator alone says
the processor is missing; neither says so, the report says `not measured` and the
model falls back to an estimate labelled as one. A counter that passed its
ceiling once during the run is unwrapped by its published range, and the figure
carries the wattage above which that recovery would have been wrong.

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

### Measuring how the work grows, instead of assuming it

The projection above divides by `0.001` because the slice covered a thousandth of
the run. That is right when the work is uniform, and when it is not, it is wrong
by a *power* rather than by a margin: a step that is quadratic in the batch turns
a thousandth of a run into a millionth of its cost, and the projection understates
the bill by three orders of magnitude while looking exactly as confident as a
correct one.

Nothing used to check that assumption. This does:

```bash
saggio audit . --country FR --run --scaling-steps 3 -o cost_of_running.yaml
```

Three slices are run instead of one, at sizes a factor of four apart, and the
largest of them is the slice that would have been run anyway. The two below it
add about a third to the time — a quarter and a sixteenth of the top rung — and
in exchange the exponent stops being an assumption:

```yaml
measurement:
  scaling:
    method: "Least squares of log(seconds) on log(size) over 3 runs: seconds = 0.0001 × size^2.000."
    reading: The work grew faster than the size, by a power of 2.00. Doubling the job
      multiplies the cost by 4.00 rather than by 2, so a projection that divided by
      the size ratio would understate the whole run.
    exponent:
      value: 2.0
      unit: exponent
      status: measured
      notes: Fitted over 3 runs of sizes 37 to 600, R² = 1.000.
    r_squared: 1.0
    observations:
      - {size: 37.0, seconds: 0.1369}
      - {size: 150.0, seconds: 2.25}
      - {size: 600.0, seconds: 36.0}
```

The exponent is `measured`, because it is a summary of three readings off a clock,
in the same way that watts from an energy counter over a duration is a
measurement. What it is *not* is a law: it is `measured` **over the sizes that were
run**, and every projection that uses it says how far past them it reached.

The projection that follows divides by `0.001^2.000` rather than by `0.001`, which
on this workload is a factor of a thousand:

```yaml
projections:
  whole_run:
    description: What the whole run would cost, projected from the slice that was
      measured and from the exponent by which its cost was measured to grow with
      the size of the job.
    costs:
      energy:
        method: "Whole run = measured slice / 0.001^2.000. Least squares of log(seconds) on log(size) over 3 runs: …"
        result:
          value: 1.6
          unit: kWh
          status: estimated
          notes: Projected from a slice covering 0.1% of the run, with a measured
            scaling exponent of 2.000.
        limits:
          - The exponent holds between sizes 37 and 600, and the whole run is about
            6e+05 at the same scale, which is 1e+03 times the largest size actually run.
```

#### When it refuses, and why that is the useful answer

A measurement that comes back saying *I cannot tell* is worth more than an
exponent nobody can check, so the series refuses in four situations and each
refusal names what would resolve it:

| Situation | Why | What it says |
|---|---|---|
| Fewer than three sizes ran | Two points fit a straight line exactly, so they rule nothing out | Asks for three, and says why two is not two-thirds of an answer |
| The sizes span less than a factor of four | Over a narrow range every exponent fits about as well as every other | Names the ratio it got and the one it needs |
| A size or a duration is not above zero | A power law is fitted on logarithms | Says a run too short for the clock needs a *larger* slice |
| The fit explains less than 95% of the variation | The slices are not measuring one consistent behaviour | Names the R² and the usual causes — a cache warming, a schedule that changes shape, a busy machine |

The last one matters most, because it is the one that changes an answer. When the
fit is that poor, the finding is that **the slice is not representative of the run
it was cut from**, and a projection made anyway would assert a proportionality the
runs on hand contradict. So the whole-run block is not written at all, the reason
travels to the reader as a note, and the refusal is recorded in the model:

```yaml
measurement:
  scaling:
    refused: true
    exponent:
      status: TODO
      notes: A power law explains only 0.42 of the variation across 3 runs, below
        the 0.95 required. The slices are not measuring one consistent behaviour …
```

Having measured the scaling and failed is not the same as never having looked,
and the model distinguishes them: without `--scaling-steps` the projection keeps
the linear assumption and records it as an assumption; with it, an unfittable
workload gets no projection.

Two more things worth knowing before you use it. A scaling series runs **without
the profiler**, because `cProfile` charges per call and would put its own growth
curve into the fit — so there is no hot path in the model, and in exchange every
cost figure comes from an unprofiled run rather than an inflated one. And a
repository whose stated size is too small to cut three distinct ways falls back
to a single slice and says so.

The method is not new. It is [Goldsmith, Aiken and Wilkerson's *Measuring
Empirical Computational Complexity*](https://theory.stanford.edu/~aiken/publications/papers/fse07.pdf)
(FSE 2007) — run over sizes spanning orders of magnitude, fit a power law, report
the goodness of fit — with this package's refusals attached.
[`ANALYSIS.md`](ANALYSIS.md) is the survey of that literature and of what the
alternatives can and cannot deliver.

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

When something does go stale, there is a way to answer it rather than re-date it:

```bash
saggio catalog refresh grid
```

Read-only. It prints what the source says today against what the catalogue
holds, and writes nothing. `--write saggio/data/grid.yaml` is the deliberate
second step. `--column` picks what to re-read — `carbon` by default, `price`, or
`both` — because the two columns do not come from the same place and do not move
together:

```bash
saggio catalog refresh grid --column price
saggio catalog refresh grid --column both --write saggio/data/grid.yaml
```

Each column carries its own `*_source_url`, its own `*_retrieved_date`, and the
period the figure describes — `carbon_data_year: 2025`, `price_collected: "Q3
2026"`. The date a number was *read* is not the period it describes, and a row
that recorded only the first would let a figure from 2019 look like today's.

**The carbon column** comes from [Ember](https://ember-energy.org/data/), through
its API, and needs a free key in `EMBER_API_KEY` or `--api-key`. Nothing else is
substituted. There is one tempting alternative — Our World in Data publishes an
Ember-derived series through a stable CSV with no key at all — and it is wrong:
its own metadata calls it *lifecycle* carbon intensity, while this column is
*operating* emissions. Swapping one for the other would change what every
committed model means, silently, and leave every number looking exactly as
trustworthy as before. So the command refuses and says that, rather than quietly
doing it.

**The timezone column** is checked rather than replaced, against the [IANA Time
Zone Database](https://data.iana.org/time-zones/tzdb/zone1970.tab) that defines
those names — the one every operating system ships, in the public domain, and
versioned, so a row records which release it matched (`timezones_tzdb_version:
"2026e"`) and not merely when somebody looked. The list is not rewritten: the
database says which zones exist, not which of them a country uses in the way
this catalogue means it, and the catalogue deliberately carries compatibility
names like `Europe/Kiev` and `Asia/Calcutta` because those are what a real
machine reports. A zone the database publishes under no name at all fails the
command instead of being corrected, since that is a question and not a fix.

Each column also runs on its own clock. A tariff and a grid mix move monthly; a
timezone list is published a handful of times a year, and asking for it monthly
would teach a maintainer to re-date rather than re-read — the habit the whole
freshness mechanism exists to prevent.

**The tariff column** comes from
[GlobalPetrolPrices](https://www.globalpetrolprices.com/electricity_prices/),
which publishes a residential price per kilowatt-hour — power, distribution,
transmission and all taxes — for every country in one table and one currency.
That table is written by a script rather than served, so the refresh renders the
page in a headless browser; with no browser installed it says so and stops
rather than guessing.

The more authoritative body for Europe is
[Eurostat](https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/nrg_pc_204?format=JSON&lang=EN&nrg_cons=KWH2500-4999&tax=I_TAX&currency=EUR&unit=KWH&lastTimePeriod=1),
and it was read — as a **check**, not as the source. It publishes in euros and
for Europe only, so taking it would have meant a second source for the exchange
rate, a conversion going stale daily, and eighteen rows that could not be
compared with the other twenty. Converted at the [European Central Bank's
reference rate](https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml),
the two agree to a median of 7% across the eighteen countries both cover, and
disagree by more than 15% for six: Finland, Romania, Poland, Norway, Sweden and
Italy. That is a difference of method rather than an error in either — Eurostat
averages a half-year by consumption band, the other is one collection. All three
URLs are in the source, so the comparison can be run again.

A country the source does not answer for is left alone and named. Nothing is
interpolated, carried over, or averaged.

**What the first real run found.** Before writing anything, the refreshed figures
were checked against Ember's full series, year by year, to confirm the catalogue
was simply a year behind. It was not. The committed values best-matched Ember
years scattered from 2000 to 2025, and eight countries matched no Ember year
within 8% — Sweden sat at 13 gCO2e/kWh where the lowest figure Ember has ever
published for it is 34.91. Every row cited Ember. A `source_url` that does not
contain the number beside it is the exact failure this package exists to object
to, and it was in the package's own data until `saggio catalog refresh grid`
replaced the lot with one verifiable 2025 vintage.

Seven tests then failed, every one of them because it had copied a catalogue
number into an assertion rather than reading it. A package whose argument is that
it refreshes its own facts cannot have a suite that breaks when it does — the
refresh read as a regression. They now assert what their names claim.

It also says what is *about* to expire, without failing:

```bash
saggio catalog freshness --within 14
```

> expiring country: 38 row(s) go stale in 12 day(s) — AE, AT, AU, BE, BR, CA and
> 32 more. Re-read the source now rather than re-dating it later.

That warning exists for one reason. A gate that turns red overnight gets the
date bumped in a hurry rather than the source re-read, and a re-dated number
nobody looked at is precisely the thing this whole mechanism was built to stop.
A week's notice — `--within 0` turns it off — is enough to go and read Ember
properly.

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
