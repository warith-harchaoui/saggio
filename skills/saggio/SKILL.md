---
name: saggio
description: >-
  Builds a repository-native cost-of-running model: money, time, energy, carbon,
  water, and any dimension the project registers, per unit of work, every number
  carrying an honesty status (measured / estimated / placeholder / TODO) and naming
  what it was derived from. Renders it, and places each figure on the line of a
  greenhouse-gas inventory it belongs to. Use when the user asks what it costs to
  run their code, says "cost per request", "carbon per inference", "energy of this
  training run", "audit the running cost of this repo", "which scope does our
  software fall under", "empreinte carbone de notre service", "bilan carbone du
  numérique", "scope 2 market-based", "un chiffre pour la CSRD ou ESRS E1", or
  wants that cost watched in CI. Do not use for cloud-billing breakdowns,
  live-service observability, a whole organisational carbon inventory, or hardware
  purchasing decisions.
license: BSD-3-Clause
compatibility: >-
  Requires Python 3.10 or newer and the saggio package
  (pip install saggio). Word and PDF output additionally need
  the [office] extra and Pandoc.
metadata:
  author: Warith Harchaoui
  version: "1.5.0"
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

**Fire on the engineer's wording.** "What does it cost to run this?", "cost per
inference", "how much energy does this script use", "carbon footprint of our API",
"audit this repo for running cost", "what would this cost on an H100", "fail the
build if this gets more expensive".

**Fire on the sustainability wording too, which is the same question asked from the
other end.** "Empreinte carbone de notre service", "bilan carbone du numérique",
"which scope does our software fall under", "we need a figure for CSRD", "ESRS E1",
"scope 2 location-based and market-based", "scope 3 category 1 for our cloud
spend", "the auditor wants the source of this number". The model this skill builds
is the evidence behind those lines, and `saggio scopes` is what places it.

**Do not fire** for a cloud-billing breakdown, for live-service observability, for
a whole organisational inventory, or for "which GPU should we buy". Those are
different questions with better tools, listed in
[`references/landscape.md`](references/landscape.md).

The boundary with an inventory is worth stating once, because it is where this
skill is most likely to be reached for wrongly. **It does not build a bilan
carbone.** It builds the figure for one unit of work, says how far that figure can
be trusted, and names the inventory line it belongs on. Everything else in the
inventory, the buildings, the commuting, the purchased hardware, the business
travel, comes from somewhere else. See
[`references/inventory.md`](references/inventory.md).

## The rule you must not break

**Never write a number that was not established.** Not a plausible default, not a
zero, not a figure you know is roughly right. If it cannot be established, it is a
`TODO` with a sentence saying what would resolve it.

This applies to you more than to the package, because you are the component most
likely to break it. You know that an A100 draws about 400 watts and that French
electricity is around 56 gCO2e/kWh. Writing either from memory, rather than from
the catalogue, produces a model that looks identical and is worthless, because
nobody can tell which numbers were checked.

That second figure is the demonstration. 56 was the catalogue's own number until
a refresh replaced it with Ember's 2025 figure, which is **41.2**. A model
carrying 56 today is wrong by a third, reads exactly like a correct one, and has
no field anywhere that would tell a reader which it is. Look it up:

```bash
python -c "from saggio.estimate.context import DeploymentContext as D; print(D.build(country='FR').grid_intensity())"
```

The answer comes back with its unit, its status, the address (Uniform Resource Locator) it was read from and the
date it was read. Those four are the reason to ask rather than to remember.

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

`--country` is an International Organization for Standardization (ISO) 3166-1 alpha-2 code and must come from the user or from
something the repository states. Never infer it from their locale, their language,
or where you think they are. Without it the carbon and money figures stay open, and
that is the correct outcome.

**Pass `--language` when the user is not writing to you in English.** One sentence
of the model is not read from a file: a local model is asked what shape of work the
repository does, and it writes the answer into the `analysis` block. Everything
else in a report can be read in the reader's language — the HyperText Markup Language (HTML) page has a
language button — so that one sentence arriving in English is the single thing
that makes the deliverable bilingual by accident rather than on purpose.

```bash
saggio audit . --country FR --language fr -o cost_of_running.yaml
```

`saggio audit --help` lists the languages; adding one is a translation file, not a
code change. A tag nothing is written in falls back to English and says so in the
notes.

**A language is not a country.** `--language fr` says how to write a sentence. It
says nothing about where the code runs: French is written in Belgium, Switzerland,
Canada, Senegal and a dozen other grids, and reading `--country FR` out of it
would put a number in the model that nobody established — the one rule above all
others. Ask for the country; infer the language.

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

Both the audit's own question and `saggio consent grant` print the terms in full
before anything is recorded, and print them in the language `--language` names.
Pass the user's language so that what they are agreeing to is in it, and leave
the answer to them: the recorded decision says which terms were agreed to, so a
yes you typed would be a yes attributed to them.

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

### 7. Place each figure in the inventory

If anyone downstream has to report these numbers, the next question is not what
they are but **whose emission they are**, and under which scope the organisation
declares them:

```bash
saggio scopes cost_of_running.yaml
```

The answer turns on one fact the model already states, who operates the machine.
Code on hardware the organisation owns means it bought the kilowatt-hour, so the
electricity is its scope 2 and the hardware its scope 3 category 2. Code on
somebody's cloud means it bought a service, and the same two emissions reach it as
scope 3 category 1. A provider whose operator nobody has recorded gets no scope at
all rather than a guessed one.

Two things to carry into your reply rather than smooth over. **A market-based
scope 2 figure is never computed here**: it rests on contracts, and no grid average
implies one, so what prints is the list of what the organisation would have to
state. And **water has no scope**, because it is not a greenhouse gas; it is
reported elsewhere.

### 8. Offer to watch it

```bash
saggio diff cost_of_running.yaml /tmp/now.yaml --threshold 10
```

Suggest a continuous-integration step. A cost model nobody re-checks stops being true within a quarter.

## What you must not do

**Do not supply a number the tool refused to.** If a projection was refused, the
refusal is the answer. Explain it; do not work around it.

**Do not quote a figure without its status.** In your reply to the user, say "an
estimated 0.0014 gCO2e per request", not "0.0014 gCO2e per request".

**Do not edit the YAML (YAML Ain't Markup Language) to make validation pass.** Fix what the error is pointing
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
> plus a host allowance), the French grid is at an estimated 41.2 gCO2e/kWh
> (Ember, 2025 data year, read today), and the code calls the OpenAI API from
> `app/handlers.py:14`.
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
- [`references/code-analysis.md`](references/code-analysis.md) — which analyses
  may produce a number, under which status, and which may not, ever.
- [`references/inventory.md`](references/inventory.md) — which line of a corporate
  greenhouse-gas inventory each figure belongs on, and what never to claim in
  front of the people who file it.
- [`references/landscape.md`](references/landscape.md) — when another tool is the
  right answer.
