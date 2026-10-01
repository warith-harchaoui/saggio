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

Three footprints ship in the catalogue, each read from its own primary source
and carrying the boundary in words beside the number:

| Part | kgCO2e per device | Boundary | Source |
|---|---|---|---|
| A100 (SXM 40GB) | 127.6 | Cradle-to-gate, teardown LCA with primary elemental analysis | [arXiv:2509.00093](https://arxiv.org/abs/2509.00093) |
| H100 | 164.0 | One of eight on an HGX H100 baseboard: 1,312 kg ÷ 8, ISO 14067, third-party reviewed | [NVIDIA PCF summary](https://images.nvidia.com/aem-dam/Solutions/documents/HGX-H100-PCF-Summary.pdf) |
| B200 | 284.25 | One of eight on an HGX B200 baseboard: 2,274 kg ÷ 8, same method | [NVIDIA PCF summary](https://images.nvidia.com/aem-dam/Solutions/documents/HGX-B200-PCF-Summary.pdf) |

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

**Only the accelerator is counted.** The processor, the board, the memory, the
network and the storage all had to be made too. None of them is in the
catalogue, so none of them is in the figure, and the figure says which part it
covers.

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
- [NVIDIA HGX H100 PCF summary](https://images.nvidia.com/aem-dam/Solutions/documents/HGX-H100-PCF-Summary.pdf) · [HGX B200 PCF summary](https://images.nvidia.com/aem-dam/Solutions/documents/HGX-B200-PCF-Summary.pdf) — ISO 14067, third-party reviewed, cradle-to-gate.
- *More than Carbon: Cradle-to-Grave environmental impacts of GenAI training on the NVIDIA A100 GPU*, [arXiv:2509.00093](https://arxiv.org/abs/2509.00093).
- [EU AI Act guidelines for GPAI providers](https://digital-strategy.ec.europa.eu/en/faqs/guidelines-obligations-general-purpose-ai-providers) · [SCI for AI and EU AI Act compliance](https://greensoftware.foundation/policy/research/sci-ai-eu-ai-act/)
- [Green Algorithms](https://doi.org/10.1002/advs.202100707) — the operational arithmetic, extracted in [`skills/saggio/references/green-algorithms.md`](skills/saggio/references/green-algorithms.md).

---

[`MEASURING.md`](MEASURING.md) is where E comes from. [`ANALYSIS.md`](ANALYSIS.md)
is what reading and running the code can each be asked. [`LANDSCAPE.md`](LANDSCAPE.md)
places this among the tools that answer nearby questions.
