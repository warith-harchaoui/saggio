# Cost of running nanoGPT

**This model is only as good as its weakest number, which is `TODO`.** A human must supply this before the model can be trusted.

Last updated 2026-10-01. Schema 2.1.

## Honesty

| Status | Count | Meaning |
|---|---|---|
| `estimated` | 4 | Computed from a sourced assumption or a published formula. |
| `TODO` | 11 | A human must supply this before the model can be trusted. |

## One unit of work

**one training run to completion**

Proposed from the repository's shape, which reads as training. Confirm or replace it: every number below is per one of these, so the whole model means whatever this sentence means.

## Where it runs

|  |  |
|---|---|
| provider | on-prem |
| country | FR |
| country provenance | Stated by the caller. |
| operating system | darwin |
| logical cores | 12 |
| physical cores | 12 |
| cpu | Apple M2 Max |
| machine provenance | This describes the machine that ran the audit, not where the code runs. https://github.com/karpathy/nanoGPT was cloned and read here. Replace the machine, the provider and the country with the ones it actually runs on before any number below means anything about this project. |

## What one unit costs

### as-audited

One unit of work as this audit found it, on the machine it ran on.

| Dimension | Per unit | Status | Derived from | Notes |
|---|---|---|---|---|
| Money | not known | `TODO` | `scenarios[0].costs.energy`, `assumptions.electricity_price` | Needs the energy drawn and a price per kilowatt-hour. |
| Time | not known | `TODO` | `scenarios[0].runtime` | No run was measured. Measure the real command with `saggio measure`, or audit again with --run. |
| Energy | not known | `TODO` | `assumptions.machine_energy`, `assumptions.pue` | Needs the machine's own energy and the site's power usage effectiveness. |
| Carbon (location-based) | not known | `TODO` | `scenarios[0].costs.energy`, `assumptions.grid_carbon_intensity` | Needs the energy drawn and the grid carbon intensity where it runs. |
| Embodied carbon | not known | `TODO` | `assumptions.hardware_embodied_carbon`, `assumptions.hardware_lifetime`, `scenarios[0].runtime` | No product carbon footprint is on file for this hardware, so the carbon of building it is open. Nobody has read one for this part; that is not the same as it having been free to build. Add an `embodied_kgco2e` to the catalogue row with the footprint's own URL and the date it was read. |
| Water | not known | `TODO` | `assumptions.machine_energy`, `assumptions.water_usage_effectiveness` | Needs the machine's energy and a published water usage effectiveness. |

## Where this goes in a GHG inventory

| Cost | Per unit | Status | GHG Protocol |
|---|---|---|---|
| `carbon` | not known | `TODO` | [Scope 2 (location-based)](https://ghgprotocol.org/scope-2-guidance) |
| `embodied_carbon` | not known | `TODO` | [Scope 3, category 2 — capital goods](https://ghgprotocol.org/corporate-value-chain-scope-3-standard) |

The scope turns on who operates the machine, which is why the same code lands on a different line of a different company's inventory depending on where it runs.

- **`carbon`** — The organisation operates the machine, so it bought the electricity. The figure here is location-based: a grid-average emission factor for the country, carrying no adjustment for any contractual instrument.

- **`embodied_carbon`** — The organisation operates the machine, so it bought the hardware. Capital goods rather than purchased goods and services, because the asset's useful life is longer than a year — which is the distinction the standard draws between the two categories, and also the reason this figure is amortised rather than counted once.

**Only half of what scope 2 requires is here.** The market-based figure is a different number and is not here. It is built from your supplier's own emission factor, from the contractual instruments you hold — guarantees of origin, RECs, a PPA — or, failing both, from your market's residual mix, which exists precisely so that unclaimed electricity is not counted as clean by default. None of the three can be derived from a grid average, so this package reports neither a market-based figure nor a zero. Record the factor as `assumptions.market_carbon_intensity` and the figure is computed and placed beside this one. Where contractual instruments exist in your market, the GHG Protocol requires both numbers, each labelled with the method that produced it.

How well founded these are: 2 `TODO`. A sustainability disclosure is asked to state how much of an inventory rests on estimates rather than readings; every number in this report already says so.

## What the numbers rest on

| Assumption | Value | Status | Provenance | Notes |
|---|---|---|---|---|
| `power_draw` | 83.76 W | `estimated` | [source](https://doi.org/10.1002/advs.202100707), read 2026-09-12 | Nameplate sum, Green Algorithms method: 12 cores x 4.0 W + 96 GB x 0.3725 W/GB |
| `pue` | 1.5 ratio | `estimated` | [source](https://www.uptimeinstitute.com/resources/research-and-reports/uptime-institute-global-data-center-survey-results-2024), read 2026-09-12 | Power usage effectiveness published by On-premises. |
| `electricity_price` | 0.276 USD | `estimated` | [source](https://www.globalpetrolprices.com/electricity_prices/), read 2026-10-02 | Indicative tariff for France. Collected Q3 2026. |
| `grid_carbon_intensity` | 41.2 gCO2e/kWh | `estimated` | [source](https://ember-energy.org/data/yearly-electricity-data/), read 2026-10-02 | Annual average for France, data year 2025. |
| `water_usage_effectiveness` | not known | `TODO` | — | On-premises publishes no water usage effectiveness. Leave this open rather than inventing a figure. |
| `hardware_embodied_carbon` | not known | `TODO` | — | No accelerator was identified, so the carbon of building one is not this model's to carry. A processor's own footprint is not in the catalogue yet; it is excluded rather than assumed to be zero. |
| `hardware_lifetime` | not known | `TODO` | — | How long this hardware stays in service, which only you know. The published footprints are cradle-to-gate and exclude the use phase, so none of them states a lifespan. Reported figures cluster between three and six years; choosing within that range moves the embodied carbon by a factor of two, which is why this is asked rather than assumed. |
| `machine_energy` | not known | `TODO` | — | Needs both a runtime and an average power draw. |

## Not counted

- Making the hardware. Only the electricity to run it is counted.
- The people. Salaries, offices, and travel are out of scope.
- Idle capacity. This is the cost of one unit of work, not of being ready.

## Rules this model follows

- Every sourced value carries source_url and retrieved_date.
- A derived value names its inputs and never outranks the weakest of them.
- The country is stated by a human, never inferred from a developer's locale.

---

Generated by [saggio](https://github.com/warith-harchaoui/saggio).
