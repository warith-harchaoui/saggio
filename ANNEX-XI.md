# The energy line of a European Union (EU) artificial intelligence (AI) Act filing

[🇫🇷 ANNEXE-XI.md](ANNEXE-XI.md) · 🇬🇧 English

This page is for a provider of a general-purpose AI (artificial intelligence) model who has to write down
what their model's energy consumption was. It says which part of that sentence
this package answers, which part it does not, and what is still being written
by the Commission. **Dates and numbering move; these were checked on
2026-10-18, and this is a tool's documentation rather than legal advice.**

## What the Act asks, and the sentence this package was built around

Annex XI requires the provider of a general-purpose AI model to document, among
much else, the computational resources used to train the model and its **known
or estimated energy consumption**. Where the consumption is not known, the Act
explicitly permits an estimate **from the compute used**.

That permission is the whole of this package's method, written into law: power
multiplied by time is energy, and where the power was never metered a sourced
figure stands in, labelled as an estimate rather than as a reading.

**The dates, because they are the reason to care now.** The documentation duty
has applied to models placed on the market since 2 August 2025. The Commission
has been able to enforce the general-purpose chapter since **2 August 2026**,
with fines of up to 3% of worldwide annual turnover or €15 million. Models
placed on the market before 2 August 2025 have until **2 August 2027**.

## What is still being written, and why that matters

The methodology is not settled. The Commission ran a targeted consultation
between April and June 2026 on **measuring the energy consumption and emissions
of AI models and systems**, aimed at the organisations that build and deploy
them. The AI Office is to publish an aggregated summary, and the Act empowers
the Commission to adopt delegated acts detailing measurement and calculation
methods **"with a view to allowing for comparable and verifiable
documentation"** — with an energy and emissions labelling scheme named as a
possible outcome.

Two words in that phrase are the whole design brief of this package.
*Comparable* means the boundary and the unit have to travel with the figure, or
two filings cannot be read against each other —
[`BOUNDARIES.md`](BOUNDARIES.md) shows what happens when they do not.
*Verifiable* means somebody other than the author has to be able to check it,
which is what a source URL (Uniform Resource Locator), a retrieval date and a re-computable derivation are
for.

## What this package hands a filer, line by line

| What Annex XI asks for | What a cost model carries | Where |
|---|---|---|
| Computational resources used | the machine, its processor and accelerator, the cores, the measured runtime | `deployment`, `measurement` |
| Known energy consumption | a figure marked `measured`, with the counter that produced it named | `scenarios[].costs.energy` |
| Estimated energy consumption | the same figure marked `estimated`, naming the power assumption it came from | `derived_from` |
| An estimate from the compute used | the Green Algorithms chain, sourced to the paper | `assumptions.power_draw`, `assumptions.pue` |
| Something a reader can check | a source URL, the date it was read, and a derivation re-computed on validation | every quantity |
| Which share of the whole run this is | the scaling exponent, measured over several sizes, with its goodness of fit | `measurement.scaling` |

The share of a filing that rests on estimates rather than readings — the thing
an assurance process asks about first — is counted rather than asserted:
`saggio scopes --json` reports it, because every number already says which it
is.

## What it does not do, said plainly

- **It is not a filing, and it is not advice.** Whether a given model is in
  scope, and what else Annex XI asks of it, is for the regulation and your
  advisers. This package produces one artefact that one line of it needs.
- **It covers one unit of work on one machine.** A training run on a cluster is
  only covered if the measurement happened on that cluster; otherwise the
  figures describe the machine that did the reading, and the model says so in
  `deployment.machine_provenance`.
- **It documents energy, not the rest of the annex.** Data, copyright, design
  choices and evaluations are elsewhere in the same document and not here.
- **It does not include embodied carbon in the energy line, because the Act
  does not ask for it.** The Act's energy question is narrower than the
  Software Carbon Intensity specification this package implements, which is why
  a model satisfying SCI answers Annex XI with room to spare and the reverse is
  not true. [`STANDARDS.md`](STANDARDS.md) has the comparison.

## What a provider would actually do with it

Measure a representative slice on the hardware the model really runs on, with
`saggio audit --run --scaling-steps 3` so the projection to the whole run
carries a measured exponent rather than an assumption. Commit the model next to
the code. Re-run it on every release, and let `saggio diff` fail the build when
a figure moves — a documentation duty that is satisfied once and never re-read
is the failure mode the whole freshness mechanism in this package exists to
prevent.

## Sources

- [Energy efficiency requirements under the EU AI Act](https://www.whitecase.com/insight-alert/energy-efficiency-requirements-under-eu-ai-act) — the Annex XI energy duty, the dates and the penalties.
- [Targeted consultation on measuring energy consumption and emissions of AI models and systems](https://digital-strategy.ec.europa.eu/en/consultations/targeted-consultation-measuring-energy-consumption-and-emissions-ai-models-and-systems) — what the Commission asked, and what it intends to do with the answers.
- [SCI for AI and EU AI Act environmental compliance](https://greensoftware.foundation/policy/research/sci-ai-eu-ai-act/) — the Green Software Foundation's mapping of one onto the other.
- [Annex XI — general-purpose artificial intelligence (GPAI) technical documentation](https://artificialintelligenceact.eu/ai-act-explorer/) — the text itself.
