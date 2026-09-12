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
pip install running-code-cost-helper

cd your-project
running-code-cost-helper audit . --country FR -o cost_of_running.yaml
running-code-cost-helper render cost_of_running.yaml -f html -o cost_of_running.html
open cost_of_running.html
```

You now have a cost model where the runtime is a `TODO`, because nothing has been
run yet, and everything derived from it is a `TODO` too. That is the correct state
for a model nobody has measured, and the report says so at the top.

To make it real, measure it:

```bash
running-code-cost-helper audit . --country FR --run -o cost_of_running.yaml
```

## Starting from nothing

Two starters ship with the package.

```bash
# Everything left open, for filling in by hand.
running-code-cost-helper init --template minimal -o cost_of_running.yaml

# A worked example with a real arithmetic chain and a note on every field.
running-code-cost-helper init --template annotated -o cost_of_running.yaml
```

The minimal one states no number at all. That is deliberate: a scaffold full of
plausible defaults tells a lie that survives into a report, while a scaffold full
of `TODO` tells the truth about itself.

Check it whenever you have edited it:

```bash
running-code-cost-helper validate cost_of_running.yaml
```

```
Valid: 0 errors, 1 warning.
Weakest number anywhere in the model: TODO.
```

Warnings never fail a model. A model that admits it is incomplete is being honest,
and this package does not punish that.

## Auditing a repository

```bash
running-code-cost-helper audit . --country FR -o cost_of_running.yaml
```

Reading a repository establishes what it is: its languages, its shape, the
frameworks it imports, how much work a full run performs, and which paid APIs it
calls. All of it is deterministic and quotes the line it came from.

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
running-code-cost-helper audit https://github.com/someone/their-project --country FR
```

Ask a local model what shape the work is, if you have Ollama running:

```bash
# On by default. The model classifies; it never supplies a number.
running-code-cost-helper audit . --country FR

# Off.
running-code-cost-helper audit . --country FR --no-llm
```

## Measuring instead of guessing

### One command of yours

```bash
running-code-cost-helper measure -- python train.py --steps 100
```

```
Ran: python train.py --steps 100
Exit code: 0
Wall-clock: 12.481 s
Average power: 96.3 W (measured)
     8.204 s  train.py:88(train_step)
     2.106 s  dataloader.py:41(__next__)
```

Power is measured where the operating system will say. On Linux with an Intel
processor that is the package energy counter. On macOS and Windows there is no
unprivileged counter to read, so the report says `not measured` and the model
falls back to an estimate labelled as one.

### A slice of somebody else's repository

```bash
running-code-cost-helper consent grant
running-code-cost-helper audit . --country FR --run -o cost_of_running.yaml
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
running-code-cost-helper audit . --country FR --run \
    --source-accelerator RTX-4090 \
    --target-accelerator H100
```

```yaml
projections:
  on_other_hardware:
    source: RTX-4090
    target: H100
    runtime:
      method: Runtime on H100 = runtime on RTX-4090 x (165 / 989) peak bf16 TFLOP/s.
      result:
        value: 7.65
        unit: s
        status: estimated
      limits:
        - A workload bound by memory bandwidth, storage, or the data loader will
          not gain the full ratio, and may gain none of it.
```

The scaling is a ratio of peak throughputs, which only means anything when the work
is compute-bound and the precision is one the catalogue quotes. Ask for a precision
it cannot speak to and it refuses rather than guessing:

```bash
running-code-cost-helper audit . --run \
    --source-accelerator RTX-4090 --target-accelerator H100 --precision fp32
```

```
Read before trusting this model:
  - The catalogue quotes peak throughput at bf16, bfloat16, fp16, float16 only,
    and this workload runs in fp32. Two chips do not keep the same ratio across
    precisions, so scaling by a BF16 figure would overstate the faster one.
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
running-code-cost-helper render cost_of_running.yaml -f md -o cost_of_running.md

# For everyone else: one self-contained page, offline, light and dark, EN and FR.
running-code-cost-helper render cost_of_running.yaml -f html -o cost_of_running.html

# For a document. Needs `pip install "running-code-cost-helper[office]"`.
running-code-cost-helper render cost_of_running.yaml -f docx -o cost_of_running.docx
running-code-cost-helper render cost_of_running.yaml -f pdf -o cost_of_running.pdf

# In your own house style.
running-code-cost-helper render cost_of_running.yaml -f docx -o cost_of_running.docx \
    --reference-doc assets/template.docx
```

The HTML page carries its own stylesheet, script, logo, and catalogue data, so it
opens with no network at all. Its what-if panel recomputes carbon and money for a
different country or provider in the browser, from the energy the model already
states. A model with no stated energy gets no panel, because a what-if built on an
invented baseline would be the worst number on the page.

## Keeping it honest in CI

```yaml
# .github/workflows/cost.yml
- name: Has the cost of running this drifted?
  run: |
    pip install running-code-cost-helper
    running-code-cost-helper validate cost_of_running.yaml
    running-code-cost-helper audit . --country FR -o /tmp/now.yaml
    running-code-cost-helper diff cost_of_running.yaml /tmp/now.yaml --threshold 10
```

`diff` fails on three things, and the third is the one people forget:

```bash
running-code-cost-helper diff before.yaml after.yaml
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
running-code-cost-helper catalog list gpu
running-code-cost-helper catalog list country --json | jq '.FR'
running-code-cost-helper catalog list service
```

A miss is a normal outcome, and the tool names what it could not find:

```
Read before trusting this model:
  - GPU 'NVIDIA H300' is not in the catalogue; add it with
    `running-code-cost-helper catalog add gpu` once you have a datasheet TDP
```

```bash
running-code-cost-helper catalog add gpu H300 \
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
running-code-cost-helper catalog freshness   # exits 1 when anything is stale
```

Tariffs and grid mixes expire in a month, datasheet wattages in a year. A single
threshold would either nag about a GPU or wave last year's electricity price
through.

## The library

Everything the command line does, it does by calling this.

```python
import running_code_cost_helper as rcch

# Audit a repository.
result = rcch.audit(".", options=rcch.AuditOptions(country="FR", use_llm=False))
print(result.report.summary())
for note in result.notes:
    print("-", note)

# Render it.
open("cost.md", "w").write(rcch.render_markdown(result.model))
open("cost.html", "w").write(rcch.render_html(result.model))
```

Validate a model you built yourself:

```python
from running_code_cost_helper import CostModel, validate

model = CostModel.load("cost_of_running.yaml")
report = validate(model)
if not report.ok:
    print(report.to_text())
```

Compute one step of the chain by hand:

```python
from running_code_cost_helper import Quantity, carbon_from_energy, energy_from_runtime

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
from running_code_cost_helper import detect_machine

machine = detect_machine()
print(machine.describe())
for miss in machine.catalog_misses:
    print("-", miss)
```

Compare two models:

```python
from running_code_cost_helper import compare

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
