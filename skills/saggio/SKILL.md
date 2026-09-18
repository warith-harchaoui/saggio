---
name: saggio
description: >-
  Builds and maintains a repository-native cost-of-running model for a codebase,
  and turns it into reports: money, time, energy, carbon, water, and any dimension
  the project registers, per unit of work, with every number carrying an honesty
  status (measured / estimated / placeholder / TODO) and naming the numbers it was
  derived from. Use when the user asks what it costs to run their code, wants a
  carbon or energy figure per request or per run, asks to audit the running cost
  of a repository, wants a cost-of-running report, or wants that cost watched in
  CI. Do not use for cloud-billing breakdowns, live-service observability,
  organisational carbon accounting, or hardware purchasing decisions.
license: BSD-3-Clause
compatibility: >-
  Requires Python 3.10 or newer and the saggio package
  (pip install saggio). Word and PDF output additionally need
  the [office] extra and Pandoc.
metadata:
  author: Warith Harchaoui
  version: "1.1.0"
  homepage: https://github.com/warith-harchaoui/saggio
---

# Cost of running code

Produce a cost model for a repository that a reader can question and still trust.
The load-bearing rule, from which everything else follows: **every number says how
far it can be trusted, and a derived number never claims more than its weakest
input.**

## When this applies

Fire when the user wants the cost of *running* code: per request, per inference,
per job, per invocation, per training run. Money, energy, carbon, water, or a
dimension of their own.

Do not fire for a cloud-billing breakdown, for live-service observability, for
organisational carbon accounting, or for "which GPU should we buy". Those are
different questions with better tools, listed in
[`references/landscape.md`](references/landscape.md).

## The rule you must not break

**Never write a number that was not established.** Not a plausible default, not a
zero, not a figure you know is roughly right. If it cannot be established, it is a
`TODO` with a sentence saying what would resolve it.

This applies to you more than to the package, because you are the component most
likely to break it. You know that an A100 draws about 400 watts and that French
electricity is around 56 gCO2e/kWh. Writing either from memory, rather than from
the catalogue, produces a model that looks identical and is worthless, because
nobody can tell which numbers were checked.

The four statuses:

- `measured` — a counter on the machine said so.
- `estimated` — a sourced formula or a published figure said so.
- `placeholder` — the field is being held open; it is not a number.
- `TODO` — a human has to supply it.

Details in [`references/honesty-taxonomy.md`](references/honesty-taxonomy.md).

## Workflow

### 1. Establish the unit of work

Everything in the model is *per one of these*, so the whole model means whatever
this sentence means. It has to be precise enough that two people would count the
same way: "one inference on a median-sized request" is a unit; "some usage" is not.

If the repository does not make it obvious, **ask**. Do not pick one. An audit
proposes a unit with status `placeholder` precisely so that a human confirms it.

### 2. Audit the repository

```bash
saggio audit . --country FR -o cost_of_running.yaml
```

`--country` is an ISO 3166-1 alpha-2 code and must come from the user or from
something the repository states. Never infer it from their locale, their language,
or where you think they are. Without it the carbon and money figures stay open, and
that is the correct outcome.

Read the notes the audit prints to standard error. They name every catalogue row
that is missing and every projection that was refused, each with what would resolve
it.

### 3. Measure, if the user allows it

```bash
saggio audit . --country FR --run -o cost_of_running.yaml
```

This executes a capped slice of the repository on their machine, with their
permissions, with no sandbox. **Tell the user that before suggesting it**, and let
them grant consent themselves. Never run `consent grant` on their behalf.

A measured runtime turns the whole chain from `TODO` into real numbers, so it is
worth asking for.

### 4. Fill in what only a human can

Work through the `TODO`s with the user, one at a time:

- **The country**, if it is still open.
- **API prices.** The model names the service, the line of code that proves it is
  called, and the page where the price lives. Read the page, agree the number with
  the user, and record it with `source_url` and `retrieved_date`. Do not write a
  price from memory; they change every quarter.
- **The water figure**, only if their provider publishes one. Most do not. Leave it
  open rather than inventing it.

### 5. Fix a catalogue miss rather than working around it

When the audit says a device is not in the catalogue, find the vendor datasheet,
then:

```bash
saggio catalog add gpu H300 \
    --source-url "https://www.nvidia.com/..." \
    --retrieved-date 2026-09-13 \
    --field tdp_w=800 --field peak_bf16_tflops=2400
```

The row is refused without a source and a date. That is the rule; do not route
around it by editing the model directly.

### 6. Validate, then report

```bash
saggio validate cost_of_running.yaml
saggio render cost_of_running.yaml -f html -o cost_of_running.html
```

Validation failing is information, not an obstacle. The most common error is a
derived value claiming more than its inputs allow, which means either the status
is wrong or the derivation is.

### 7. Offer to watch it

```bash
saggio diff cost_of_running.yaml /tmp/now.yaml --threshold 10
```

Suggest a CI step. A cost model nobody re-checks stops being true within a quarter.

## What you must not do

**Do not supply a number the tool refused to.** If a projection was refused, the
refusal is the answer. Explain it; do not work around it.

**Do not quote a figure without its status.** In your reply to the user, say "an
estimated 0.0014 gCO2e per request", not "0.0014 gCO2e per request".

**Do not edit the YAML to make validation pass.** Fix what the error is pointing
at.

**Do not present a projection as a measurement.** A measured slice projected to a
whole run is `estimated`, and a runtime scaled onto another accelerator is a
datasheet ratio that real workloads rarely reach.

**Do not add up currencies.** The model carries ISO 4217 codes for this reason.

## Answering the user

Lead with the weakest status in the model, because that is what the whole thing is
worth. Then the numbers, each with its status. Then what would improve it, in order
of how much difference it would make. Something like:

> This model is `TODO` overall: the runtime has not been measured, so energy,
> money, and carbon are all open.
>
> What is established: the machine draws an estimated 600 W (RTX 4090 datasheet
> plus a host allowance), the French grid is at an estimated 56 gCO2e/kWh (Ember,
> read today), and the code calls the OpenAI API from `app/handlers.py:14`.
>
> Two things would close most of it. Running `audit --run` would measure the
> runtime and turn the whole chain into real numbers. Reading the OpenAI pricing
> page would close the largest cost in the model, which is almost certainly the
> API call rather than the electricity.

## References

- [`references/honesty-taxonomy.md`](references/honesty-taxonomy.md) — the four
  statuses, the weakest-link rule, and the mistakes to avoid.
- [`references/schema.md`](references/schema.md) — what a cost model file looks
  like, field by field.
- [`references/green-algorithms.md`](references/green-algorithms.md) — the
  arithmetic, and the distinction between machine and facility energy.
- [`references/landscape.md`](references/landscape.md) — when another tool is the
  right answer.
