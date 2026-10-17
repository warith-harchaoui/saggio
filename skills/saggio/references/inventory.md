# Handing a figure to the people who have to file it

The user in front of you may not be the one who will use this number. A
sustainability or CSR team has to place it, defend it, and sign it. This page is
what you need to answer them without overclaiming. The long form, with the
regulatory dates and the sources, is the repository's
[`INVENTORY.md`](../../../INVENTORY.md).

The command that does the placing:

```bash
saggio scopes cost_of_running.yaml
saggio scopes cost_of_running.yaml --json
```

## The one fact that settles the scope

Not the code, not the language, not the workload: **who buys the electricity and
owns the machine.** The model already states it, as `deployment.provider`, and the
providers catalogue records it as `operated_by`.

| Where it runs | The electricity | The hardware |
|---|---|---|
| A machine the organisation owns | Scope 2 | Scope 3, category 2, capital goods |
| AWS, GCP, Azure, a GPU cloud | Scope 3, category 1, purchased goods and services | Scope 3, category 1, the same line |
| A provider nobody classified | no scope, stated as a question | no scope |

Three mistakes this prevents, all of them common:

- **Cloud compute is not the customer's scope 2.** They bought a service. Filing
  it as scope 2 double-counts it against the provider's own disclosure.
- **Owned hardware is capital goods, not purchased goods.** Category 2, because
  the asset lasts more than a year, which is also why its footprint is amortised
  rather than charged once.
- **An unclassified provider gets no scope at all.** Not the nearest guess. The
  two answers differ by which legal entity reports the emission, and a wrong one
  looks exactly as tidy as a right one.

## Scope 2 has two halves, and only one of them is in the model

The grid intensities here are national averages, which **is** the location-based
method by definition. The market-based figure is a different number, and both are
required wherever contractual instruments exist.

**Never compute a market-based figure from a grid average, and never let the user
do it either.** It does not follow from one. It comes from the supplier's own
factor for their contract, from the instruments they hold, or from their market's
residual mix, and the organisation is the only party that holds any of the three.

What to do instead: tell them the dimension exists, `carbon_market_based`, and
that `audit` ships `assumptions.market_carbon_intensity` open on a machine they
operate. They state the factor with the document it came from, and the figure is
computed from the same energy, placed beside the first, and labelled with the
method that produced it.

Two rules that are stricter here than anywhere else in the package, and both are
worth saying out loud:

- **The document is required, as an error rather than a warning.** Nobody else can
  check a contract.
- **It is never published alone.** A market-based figure without its
  location-based companion reads better than the disclosure actually is.

On rented hardware there is no pair at all. The vendor holds the scope 2; what
reaches the customer is one purchased service in category 1.

## What has no scope, and why that is an answer

- **Money and time** are costs, not emissions.
- **Energy** is the activity datum the emission was computed from. Under the
  European standards it is disclosed on its own, beside the emissions, not as one.
- **Water** is not a greenhouse gas. It is reported under a different standard
  entirely.
- **A dimension the project registered itself** gets no scope, because whether it
  is a greenhouse gas is a question about their dimension, not about this package.

Say these as facts, not as gaps. "No scope applies" is a placement.

## What to tell an assurance provider

Every quantity carries four things the package enforces rather than suggests: a
status, a provenance URL with the date it was read, the inputs it was derived
from with the arithmetic re-checked, and a freshness window that fails a build
when nobody has re-read the figure.

Two consequences worth handing over directly:

- **The estimation disclosure is already written.** A filer has to say how much of
  an inventory rests on estimates. Every number here says so for itself, and
  `saggio scopes --json` counts them.
- **An open figure stays open.** No country means `TODO`, not zero. No published
  water figure means `TODO`, not a plausible one.

## What you must not claim on this subject

**This does not build an inventory, and saying otherwise is the fastest way to
lose the reader you were trying to win.** It covers compute for one unit of work.
No employee devices, no network transit, no storage at rest, no offices, no
travel, no end of life, nothing netted against removals.

Where the provider publishes a per-customer figure, **that** figure is the primary
source and this one is a cross-check. Most publish nothing at that granularity,
which is the reason to compute it at all.

And nothing here is an assurance opinion, or advice about who falls inside a
reporting obligation. If the user asks whether they are in scope of a directive,
say that the directive and their advisers answer that, and go back to the number.
