# Triggers

What `running-code-cost-helper` is for, and the phrasings, commands, files, and
questions that should reach for it. Written for a person deciding whether this is
the right tool, and for an agent deciding whether to invoke the
[skill](skills/running-code-cost-helper/SKILL.md).

## In one sentence

It answers **what does it cost to run this code, per unit of work, and how much
should I trust that answer**: money, time, energy, carbon, water, and any
dimension a team registers, written to a YAML file that lives next to the code and
rendered into reports.

## What it does, and how to reach it

| Intent | Command | Library |
|---|---|---|
| Start a cost model | `... init` | `template_text` |
| Check one against the rules | `... validate` | `validate` |
| Build one from a repository | `... audit` | `audit`, `audit_github` |
| Measure a real command | `... measure` | `run_slice` |
| Report it for people | `... render` | `render_markdown`, `render_html`, `render_office` |
| Fail a build on drift | `... diff` | `compare` |
| Look up or extend the facts | `... catalog` | `Catalog`, `add_row` |
| Ask what this machine is | `... machine` | `detect_machine` |
| Allow or refuse running code | `... consent` | `require_consent` |

## Phrasings that should fire

**Cost of running.** "What does it cost to run this?", "cost per inference",
"cost per request", "cost per training run", "how much does this job cost",
"cost per API call", "unit economics of this service", "what is our cost per
thousand predictions".

**Energy and power.** "How much energy does this use", "watts", "kilowatt hours",
"power draw of this training run", "measure the energy of this script", "how much
electricity", "is this code efficient".

**Carbon and sustainability.** "Carbon footprint of this model", "CO2 per
inference", "emissions of this pipeline", "green software", "how much CO2 does
our API emit", "sustainability report for this service", "grid intensity",
"Green Algorithms", "scope 2 for this workload".

**Water.** "Water footprint of this datacenter workload", "WUE", "how much cooling
water".

**Auditing a codebase.** "Audit this repo for running cost", "what is expensive in
this codebase", "which paid APIs does this call", "what does this project spend
per run", "profile where the cost goes".

**Projecting.** "What would this cost on an H100", "extrapolate from this run",
"if we moved this to GCP", "what would the whole training run cost", "what if we
ran this in Sweden instead", "cost at a million requests a day".

**Keeping it honest.** "Has our cost per request drifted", "fail the build if this
gets more expensive", "track the carbon cost in CI", "is this number still true".

## Files and artefacts that should fire

- `cost_of_running.yaml` anywhere in a repository.
- A request to write, review, or update one.
- A `cost_of_running.md` or `.html` report.
- A sustainability or FinOps section of a README that states a per-unit figure.

## Phrasings that should *not* fire

- **Cloud billing.** "Why was our AWS bill so high last month" is a question for
  Cost Explorer. This tool models the cost of a unit of work from first
  principles; it does not read invoices.
- **Live observability.** "Which endpoint is slow right now" is a question for
  tracing and metrics. This tool measures a bounded slice, once.
- **Organisational carbon accounting.** Scope 1 and scope 3, business travel,
  procurement. Different scope, different tool, different standard.
- **Code optimisation on its own.** "Make this function faster" is a profiling
  question. This tool profiles a slice to attribute cost, but it does not rewrite
  your code.
- **Hardware purchasing.** "Which GPU should we buy" needs embodied carbon,
  lifetime, and utilisation, none of which this tool models.

## What it will refuse, out loud

It refuses rather than guessing, and each refusal names what would resolve it.

- **No country stated.** Carbon and money stay open. It never reads a country off
  a locale. A timezone inference is offered and labelled as an inference.
- **No water figure published.** Water stays open. It will not invent a water
  usage effectiveness.
- **A precision the catalogue does not quote.** A machine-to-machine projection is
  refused, naming the precision, because two chips do not keep the same ratio
  across precisions.
- **A slice that failed or was cut short.** Nothing is projected from it, and the
  model says why.
- **A hardware row it does not have.** It names the device and the command that
  would add it.
- **No consent to run code.** `--run` does nothing and the audit proceeds on
  reading alone. A session with no terminal is refused, never defaulted.

## What a number from this tool means

Every value carries a status, and a derived value never outranks its weakest
input:

- `measured` — a counter on the machine said so.
- `estimated` — a sourced formula or a published figure said so.
- `placeholder` — the field is held open; it is not a number.
- `TODO` — a human has to supply it.

If you are quoting a figure from this tool in public, quote its status with it.
