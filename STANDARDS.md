# The standard this is, and the part it still lacks

[🇫🇷 NORMES.md](NORMES.md) · 🇬🇧 English

There is an international standard for the thing this package produces, and it
has been one since 2024. The **Software Carbon Intensity** specification —
[ISO/IEC 21031:2024](https://greensoftware.foundation/standards/sci/), written
by the Green Software Foundation — asks for emissions *per functional unit of
work*, with the boundary declared, no offsets, and a location-based grid
intensity.

That is not a shape this package was adapted to. It is the shape it was built
in, before anybody here had read the specification: a cost model is per unit of
work by construction, the boundary is written beside every number, nothing may
be subtracted for a purchase, and the grid intensity comes from where the code
actually runs. Three of the specification's four terms were already here.

The fourth was missing, and it was the expensive one.

## The four terms

```
SCI = (E × I + M) per R
```

| Term | What it is | Where it comes from here |
|---|---|---|
| **E** | Energy the run drew | Measured from the machine's own counters where it will give them, estimated from a sourced power figure otherwise. See [`MEASURING.md`](MEASURING.md). |
| **I** | Carbon intensity of that electricity | `assumptions.grid_carbon_intensity`, from the bundled grid catalogue, by country, location-based. |
| **M** | Carbon emitted making the hardware | `scenarios[].costs.embodied_carbon`. New, and the subject of this page. |
| **R** | The functional unit | `unit_of_work`. The first thing an audit asks and the thing every other number is divided by. |

`E × I` is the `carbon` dimension this package has always reported. `M` is the
`embodied_carbon` dimension beside it. The score is their sum, and
`saggio.software_carbon_intensity` will add them — refusing when either half is
open, because reporting one of them under the name of a standard would
understate it with the standard's authority.

## M, and what it costs to not have it

Manufacturing one HGX H100 baseboard emits **1,312 kgCO2e** before it has
computed anything. A cost model that reports only the electricity is not silent
about that figure: it is claiming it is zero.

The specification defines

```
M = TE × TS × RS
```

the total embodied emissions of the hardware, times the share of its life the
run reserved, times the share of the hardware it reserved. On an hour of one
H100 over a four-year life, that is 164 kg × 1 h / 35 064 h × 1 ≈ **4.7 gCO2e**
— small next to the ~400 W-hour the same run draws, and not nothing, and
emphatically not zero.

Eight footprints ship in the catalogue — **four accelerators out of 25 rows,
four processors out of 12** — each read from its own primary source and carrying
the boundary in words beside the number:

| Part | kgCO2e per device | Boundary | Source |
|---|---|---|---|
| A100 (SXM 40GB) | 127.6 | Cradle-to-gate, teardown LCA with primary elemental analysis | [arXiv:2509.00093](https://arxiv.org/abs/2509.00093) |
| H100 | 164.0 | One of eight on an HGX H100 baseboard: 1,312 kg ÷ 8, ISO 14067, third-party reviewed | [NVIDIA PCF summary](https://images.nvidia.com/aem-dam/Solutions/documents/HGX-H100-PCF-Summary.pdf) |
| B200 | 284.25 | One of eight on an HGX B200 baseboard: 2,274 kg ÷ 8, same method | [NVIDIA PCF summary](https://images.nvidia.com/aem-dam/Solutions/documents/HGX-B200-PCF-Summary.pdf) |
| TPU v4 | 366.0 | One chip with its HBM, cradle-to-gate, ISO 14040/14044, modelled by the designer from its own node, die and yield | [arXiv:2502.01671](https://arxiv.org/abs/2502.01671) |
| EPYC 7742 | 40.66 | Cradle-to-gate, from a 1,600 mm² die | [Boavizta](https://doc.api.boavizta.org/Explanations/components/cpu/) |
| EPYC 9654 | 33.98 | Cradle-to-gate, from a 1,261 mm² die | [Boavizta](https://doc.api.boavizta.org/Explanations/components/cpu/) |
| Core i9-13900K | 14.2 | Cradle-to-gate, from a 257 mm² die | [Boavizta](https://doc.api.boavizta.org/Explanations/components/cpu/) |
| Ryzen 9 7950X | 14.34 | Cradle-to-gate, from a 264 mm² die | [Boavizta](https://doc.api.boavizta.org/Explanations/components/cpu/) |

The two kinds of row are not the same strength of claim, and the table keeps
them apart rather than averaging them into one word. The accelerators are
vendor-published, torn down and weighed, or modelled by the part's own designer
from parameters nobody outside has. The processors are **computed from the
chip's die size by a published model** — a weaker thing, and the reason the
method is linked rather than only the figure.

**The four other TPU generations in that paper are not here, and the reason is a
column rather than a doubt.** It publishes a footprint for v4i, v5e, v6e and v5p
as well, and they would be as good as the v4 row. What it does not publish is a
power figure of the kind every row here carries: `tdp_w` is a datasheet rating,
and what the paper gives is a *measured mean across a production fleet* — a
better number for estimating energy, and a different quantity. Putting one under
the other's name would make the column mean two things, which is the substitution
this package spends its time refusing. Those four need a published rating, or a
column of their own.

**What a `source_url` is, and what it is not.** It exists so a reader can check
the figure beside it, which means it has to be something a person can open. Two
of the sources here are APIs, and they behave differently when a reader follows
the link rather than a program: Boavizta answers **19.0 kgCO2e** — the default
for an unnamed chip, and the exact figure this package refuses on import — while
Ember answers HTTP 403 and `{"detail":"No API key set"}`. Four processor rows
cited the first, so anybody who clicked saw a number with nothing to do with the
processor on that row.

Thirty-eight grid rows cited the second, and that one took three more iterations
to fix, because this page had already noticed it and talked itself out of it:
*unhelpful but true*. It is not true. A citation is a claim that the figure can
be checked there, and no figure can be checked at a 403 — the row was asserting
something about a page that does not exist for the reader. Both are now named in
the scope or in prose, where naming an endpoint is provenance of method, and
neither is in a field a reader is invited to follow. The grid rows cite [Ember's
published yearly dataset](https://ember-energy.org/data/yearly-electricity-data/),
which is the same series under CC-BY-4.0, needs no key, and was checked against
the API country by country before it was adopted rather than assumed equivalent.

**The one non-vendor figure here has been checked against an independent one.**
The A100 number comes from a teardown with primary elemental analysis; a
parametric model published separately, over 174 NVIDIA cards from 2013 to 2024
([dataset](https://doi.org/10.5281/zenodo.20321644), CC-BY-4.0, from
[arXiv:2607.01258](https://arxiv.org/abs/2607.01258)), reaches the figure a
different way:

| Part | Here | That dataset | Apart |
|---|---|---|---|
| A100 SXM4 40GB | 127.6 | 123.2 | **3.4%** |
| H100 SXM5 80GB | 164.0 | 196.5 | **19.8%** |
| B200 | 284.25 | not covered | — |

Two methods that share no inputs landing 3.4% apart on the A100 is the best
evidence available that the number is about right. The H100 is a different
story, and the paper says why itself: it estimates the memory higher than
NVIDIA does, from a different life-cycle database, while estimating the
processor and the board lower. **The vendor figure is kept** — it is
third-party verified under ISO 14067 and it is about the exact part — but a
reader should know a credible independent estimate puts it a fifth higher.

The dataset is a **check, not a source**, for the same reason Eurostat is a
check on the tariffs: it is a parametric model, and a model is a weaker claim
than a teardown or a verified vendor disclosure. Nothing in the catalogue comes
from it.


The eight remaining processors are refused rather than filled. Four are refused
because that source answers about a chip it was not asked about: asked for an
Apple M4 Max it returns an Apple M1 Max, four generations earlier, with no
warning anywhere in the reply. Two are refused because the die size it computed
from is a family average rather than this chip's, which makes the footprint a
family average wearing the chip's name. Two are generic catalogue defaults,
whose footprint would be a default too.

Accelerators cannot be filled this way at all. The same source, asked for any
GPU by name, answers 575.1 kgCO2e — the same number for a GTX 1080 Ti, an A100
and an H100, because it holds one archetype called "Large GPU". That is three
and a half times NVIDIA's own verified figure for an H100, and it arrives
wearing the model name that was asked for. The refresh refuses it by name
and says why.

A part with no row gives a `TODO`, with a sentence saying that nobody has read a
footprint for it — which is not the same as it having been free to build.

## Where this is not conformant, and why

The useful half of a conformance claim is the part that fails.

**The lifespan is yours, and it ships open.** Every one of those footprints is
cradle-to-gate and explicitly excludes the use phase. The vendor has given the
numerator and deliberately withheld the denominator, because how long a card
stays in service is a fact about a fleet rather than about a part. So
`assumptions.hardware_lifetime` is a `TODO` until you state it. Published
figures cluster between three and six years, and choosing within that range
moves the answer by a factor of two — which is exactly why it is asked rather
than assumed.

**End of life is excluded, because the sources exclude it.** The footprints stop
at the factory gate. Recycling and disposal are real and are not in these
numbers, and the report says so rather than letting the omission pass as a zero.

**The board, the memory, the network and the storage are not counted.** They all
had to be made too. None of them is in the catalogue, so none of them is in the
figure, and the figure says which part it covers. The processor is counted now
where one is on file, and only then: a machine with an accelerator reports the
accelerator, a machine without one reports its processor if that chip is known,
and otherwise reports `TODO`. Nothing is added across parts, because no source
here covers two of them under one boundary.

**The amortisation is calendar time, not busy time.** The specification defines
the time share as duration over expected lifespan, so a card idle for half its
life charges that half to nobody. The common alternative — loading all of the
embodied carbon onto the hours that did work — gives a larger number and is not
what the standard says. This package follows the standard, and every figure it
produces carries a note saying which convention it used.

Three things the specification requires that were already true here, and are
worth naming because they are the ones tools most often get wrong: **no
offsets** are subtracted anywhere; the intensity is **location-based**, from
where the code runs, never a market instrument; and the **boundary is
declared** on every quantity rather than in a footnote.

## What the regulations ask, which is less

The [EU AI Act](https://digital-strategy.ec.europa.eu/en/faqs/guidelines-obligations-general-purpose-ai-providers)
requires providers of general-purpose AI models to document, in Annex XI, the
computational resources used for training and the **known or estimated energy
consumption** of the model. Where it is not known, the Act explicitly permits an
estimate from the compute used — which is, almost word for word, this package's
job. Non-compliance carries fines up to €15 million or 3% of global annual
turnover; models placed on the market before 2 August 2025 have until 2 August
2027.

It asks for less than SCI does, in three ways worth knowing: it covers energy
rather than emissions, it **ignores embodied carbon entirely**, and the
disclosure goes to the regulator rather than to the public. A model that
satisfies SCI satisfies Annex XI with room to spare; the reverse is not true.

The Green Software Foundation has mapped one onto the other in
[SCI for AI and EU AI Act environmental compliance](https://greensoftware.foundation/policy/research/sci-ai-eu-ai-act/).

### And one regulation that publishes numbers back

The recast Energy Efficiency Directive goes the other way: under Article 12,
Member States must make operators of data centres above 500 kW report their
energy and water performance, and the Commission publishes what comes back.
[COM(2026) 500 final](https://data.consilium.europa.eu/doc/document/ST-13443-2026-INIT/en/pdf),
of 21 September 2026, is the first such assessment.

For 2024 it gives a Union-wide **PUE of 1.36**, energy-weighted over the 681
data centres whose figure passed the quality review, and a **WUE of 0.58**
litres per kilowatt-hour over the 458 that reported water above zero. Both are
in the catalogue as the `on-prem-eu` provider, and the second one matters more
than it looks: water was a `TODO` on every self-run model this package wrote,
because *"On-premises publishes no water usage effectiveness"*. For a room
inside the Union, that sentence is no longer true.

**What the report says about itself**, carried in the row rather than left for a
reader to find: only about 36% of the data centres in scope reported at all,
70.1% of what they reported passed the quality review, and the WUE average
excludes dry-cooled rooms and therefore overstates the typical one.

**And what cannot be put in a catalogue.** National averages are in the report —
they range from 1.15 to 1.66 — but only as labels on a bar chart, and the four
Member States with fewer than three reporting facilities are flagged by the
Commission itself as possibly unrepresentative. Transcribing a figure off a
chart is how a number stops being able to say where it came from, so none of
them is here. Facility-level figures are not available at all, and will not be:
Article 5(5) of Delegated Regulation (EU) 2024/1364 requires the database to be
anonymised.

## Doing it

```bash
saggio audit . --country FR --run -o cost_of_running.yaml
```

The audit writes `assumptions.hardware_embodied_carbon` from the catalogue and
`assumptions.hardware_lifetime` as an open figure. Fill the lifetime in, and
`embodied_carbon` resolves along with everything derived from it:

```yaml
assumptions:
  hardware_lifetime:
    value: 4.0
    unit: "years"
    status: "estimated"
    notes: "Fleet replacement cycle, from our own procurement records."
```

Leave it open and the embodied figure stays open, the SCI score stays open with
it, and the report says which of the four terms is missing. That is the whole
design: a standard you half-satisfy, and know exactly which half.

## Sources

- [Software Carbon Intensity specification](https://sci.greensoftware.foundation/), ISO/IEC 21031:2024 · [SCI for AI](https://greensoftware.foundation/standards/sci-ai/)
- *Report on the energy efficiency of data centres in the EU*, COM(2026) 500 final, 21 September 2026 — [Council copy, PDF](https://data.consilium.europa.eu/doc/document/ST-13443-2026-INIT/en/pdf) · the Commission's own page redirects to [EUR-Lex](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A52026DC0500), which serves an empty body to anything that is not a browser.
- [NVIDIA HGX H100 PCF summary](https://images.nvidia.com/aem-dam/Solutions/documents/HGX-H100-PCF-Summary.pdf) · [HGX B200 PCF summary](https://images.nvidia.com/aem-dam/Solutions/documents/HGX-B200-PCF-Summary.pdf) — ISO 14067, third-party reviewed, cradle-to-gate.
- *More than Carbon: Cradle-to-Grave environmental impacts of GenAI training on the NVIDIA A100 GPU*, [arXiv:2509.00093](https://arxiv.org/abs/2509.00093).
- *Life-Cycle Emissions of AI Hardware: A Cradle-To-Grave Approach and
  Generational Trends*, [arXiv:2502.01671](https://arxiv.org/abs/2502.01671) —
  Google's own LCA of five TPU generations, ISO 14040/14044, and the first
  published manufacturing figure for an AI accelerator by the people who
  designed it. The TPU v4 row comes from its Table 1.
- [Ember's yearly electricity data](https://ember-energy.org/data/yearly-electricity-data/)
  (CC-BY-4.0) — the grid carbon intensities, and what the 38 grid rows cite.
- *The Rising Unsustainability of AI Graphics Cards Production*,
  [arXiv:2607.01258](https://arxiv.org/abs/2607.01258), with its
  [dataset](https://doi.org/10.5281/zenodo.20321644) of 174 NVIDIA cards
  (CC-BY-4.0) — used here to check the accelerator figures, never to supply one.
- [Boavizta's processor method](https://doc.api.boavizta.org/Explanations/components/cpu/)
  — how a footprint is computed from a die size, which is what the four
  processor rows cite.
- [EU AI Act guidelines for GPAI providers](https://digital-strategy.ec.europa.eu/en/faqs/guidelines-obligations-general-purpose-ai-providers) · [SCI for AI and EU AI Act compliance](https://greensoftware.foundation/policy/research/sci-ai-eu-ai-act/)
- [Green Algorithms](https://doi.org/10.1002/advs.202100707) — the operational arithmetic, extracted in [`skills/saggio/references/green-algorithms.md`](skills/saggio/references/green-algorithms.md).

---

[`MEASURING.md`](MEASURING.md) is where E comes from. [`ANALYSIS.md`](ANALYSIS.md)
is what reading and running the code can each be asked. [`LANDSCAPE.md`](LANDSCAPE.md)
places this among the tools that answer nearby questions.
