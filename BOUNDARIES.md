# The boundary is the answer

[🇫🇷 FRONTIERES.md](FRONTIERES.md) · 🇬🇧 English

Two companies published a carbon figure for one inference in 2026. The two are
more than an order of magnitude apart. One is market-based and counts idle fleet
capacity; the other is location-based and counts the hardware's manufacture,
under the Association française de normalisation (AFNOR) Frugal artificial
intelligence (AI) method.

| | Figure | Boundary | Method |
|---|---|---|---|
| [Google, median Gemini text prompt](https://cloud.google.com/blog/products/infrastructure/measuring-the-environmental-impact-of-ai-inference) | 0.24 Wh, **0.03 gCO2e**, 0.26 mL water | accelerator, host, datacenter overhead, **and idle machine capacity** | **market-based** electricity |
| Mistral, average 400-token response | **1.14 gCO2e** | the serving infrastructure **and manufacturing the hardware** | **location-based**, AFNOR Frugal AI |

Roughly a factor of thirty-eight, with **neither of them being evasive**. One
counts the electricity a contract paid for and the capacity reserved to serve
you; the other counts the grid average and the factories. They answer two
different questions that share a sentence.

That is the whole proposition of this package, demonstrated by somebody else:
**a figure without its boundary is not a figure.** This page takes one model
committed in this repository and shows what its number becomes under each
boundary — including the two it refuses to produce, with what each refusal would
need.

## The model

[`examples/request.yaml`](examples/request.yaml): one `/scopes` request handled
end to end, measured on an Apple M2 Max in France, two hundred requests inside
one interpreter.

```bash
saggio scopes examples/request.yaml
saggio next examples/request.yaml
```

Measured: a runtime of 0.0038534 s and a machine drawing **17.98 W**, read from
the counter rather than from the datasheet the package would otherwise have
assumed, which says 83.76 W.

## The same request, under four boundaries

| Boundary | Carbon per request | Status |
|---|---|---|
| The processor and its memory only, location-based | 7.93e-07 gCO2e | **computed** |
| Plus the building's overhead (power usage effectiveness, PUE 1.5), location-based — *this package's default* | 1.19e-06 gCO2e | **computed** |
| Plus a contract, market-based — *Google's shape* | — | **refused**: needs `assumptions.market_carbon_intensity` |
| Plus manufacturing the hardware — *AFNOR's shape* | — | **refused**: needs a footprint for this machine and a lifetime |

The first two differ by the datacenter overhead alone: **50%**, from one
assumption. That is the small end of the range.

## What manufacturing would do, on hardware the catalogue knows

This laptop has no published product carbon footprint, so the fourth row above
stays open rather than guessing. But the catalogue holds NVIDIA's own
International Organization for Standardization (ISO) 14067
figure for an HGX H100, **164.0 kgCO2e** per board eighth, third-party verified
and read on 2026-10-01. Amortised over the same 0.0038534 s of runtime:

| Hardware lifetime | Embodied carbon per request | Against the operational 1.19e-06 |
|---|---|---|
| 3 years | 6.68e-06 gCO2e | **5.6×** |
| 4 years | 5.01e-06 gCO2e | **4.2×** |
| 6 years | 3.34e-06 gCO2e | **2.8×** |

Read that twice. On datacenter hardware, **manufacturing dominates a short
request by between three and six times the electricity** — and the lifetime
alone, which nobody outside your own fleet can tell you, **moves the answer by
a factor of two**. A figure that leaves it out is not a conservative figure; it
is a different figure.

Published lifetimes cluster between three and six years, which is why this
package will not pick one for you and holds `assumptions.hardware_lifetime`
open until somebody states it.

## Five questions to ask of any published figure

Before comparing two numbers for the same workload, ask what the pair above
makes unavoidable:

1. **What is the unit?** One prompt, one response of four hundred tokens, one
   request, one training run. None of these convert into the others.
2. **Where does the boundary stop?** Accelerator, host, building, idle
   capacity, factories, end of life.
3. **Which scope 2 method?** Location-based follows the grid; market-based
   follows a contract. They can differ by tenfold and both are required.
4. **Is manufacturing in it?** On short requests it is usually the larger term.
5. **Measured or modelled, and by what?** A counter, a datasheet, a fleet
   average, a published coefficient.

Every report this package renders answers all five on its own face, which is
the only reason its numbers can be put beside somebody else's at all.

## Sources

- [Measuring the environmental impact of AI inference](https://cloud.google.com/blog/products/infrastructure/measuring-the-environmental-impact-of-ai-inference) — Google's per-prompt figures and the boundary they cover.
- [HGX H100 product carbon footprint summary](https://images.nvidia.com/aem-dam/Solutions/documents/HGX-H100-PCF-Summary.pdf) — the 164.0 kgCO2e this page amortises, ISO 14067, third-party verified.
- [Scope 2 Guidance](https://ghgprotocol.org/scope-2-guidance) — why both methods are required.
- [`STANDARDS.md`](STANDARDS.md) — the four terms, and where this package is deliberately not conformant.
- [`INVENTORY.md`](INVENTORY.md) — which line of an inventory each figure goes on.
