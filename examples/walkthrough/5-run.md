# Cost of running counter

**This model is only as good as its weakest number, which is `TODO`.** A human must supply this before the model can be trusted.

Last updated 2026-10-01. Schema 2.1.

## Honesty

| Status | Count | Meaning |
|---|---|---|
| `measured` | 5 | Recorded from an actual run on the target system. |
| `estimated` | 10 | Computed from a sourced assumption or a published formula. |
| `TODO` | 5 | A human must supply this before the model can be trusted. |

## One unit of work

**one inference on a median-sized input**

Proposed from the repository's shape, which reads as inference. Confirm or replace it: every number below is per one of these, so the whole model means whatever this sentence means.

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

## What one unit costs

### as-audited

One unit of work as this audit found it, on the machine it ran on.

| Dimension | Per unit | Status | Derived from | Notes |
|---|---|---|---|---|
| Money | 1.575e-06 USD | `estimated` | `scenarios[0].costs.energy`, `assumptions.electricity_price` | Facility energy x price per kilowatt-hour; hardware and staff are not included. |
| Time | 0.4941 s | `measured` | `scenarios[0].runtime` | Wall-clock time of `python3.13 predict.py --num_samples 400`. |
| Energy | 6.564e-06 kWh | `estimated` | `assumptions.machine_energy`, `assumptions.pue` | Machine energy x power usage effectiveness: what the building draws. |
| Carbon | 0.0002704 gCO2e | `estimated` | `scenarios[0].costs.energy`, `assumptions.grid_carbon_intensity` | Facility energy x grid carbon intensity, operating emissions only. |
| Embodied carbon | not known | `TODO` | `assumptions.hardware_embodied_carbon`, `assumptions.hardware_lifetime`, `scenarios[0].runtime` | No product carbon footprint is on file for this hardware, so the carbon of building it is open. Nobody has read one for this part; that is not the same as it having been free to build. Add an `embodied_kgco2e` to the catalogue row with the footprint's own URL and the date it was read. |
| Water | not known | `TODO` | `assumptions.machine_energy`, `assumptions.water_usage_effectiveness` | Needs the machine's energy and a published water usage effectiveness. |

*A million units emit about 0.295 tree-months · 1.545 km by car (EU average) · 1% of a Paris–London flight — estimated restatements, [Green Algorithms](https://doi.org/10.1002/advs.202100707) coefficients.*

## What the numbers rest on

| Assumption | Value | Status | Provenance | Notes |
|---|---|---|---|---|
| `power_draw` | 31.88 W | `measured` | — | Read from the machine while the slice ran. The figure covers the chip's processor cores, graphics cores, and neural engine, from the system-on-chip's own energy counters and the chip's memory, from its own energy counter, read from the CPU Energy, GPU Energy, ANE0, DRAM0 counters. Memory is measured rather than estimated here: the machine publishes its own memory energy counter, so the figure is what the memory drew rather than what its installed capacity suggests it would draw. These are the chip's own energy counters, which are a model inside the silicon rather than a meter on the power rail, and Apple says they are not a basis for comparing one machine against another. Left out of them: the display, storage, networking, the fans, and the power supply's own losses. |
| `pue` | 1.5 ratio | `estimated` | [source](https://www.uptimeinstitute.com/resources/research-and-reports/uptime-institute-global-data-center-survey-results-2024), read 2026-09-12 | Power usage effectiveness published by On-premises. |
| `electricity_price` | 0.24 USD | `estimated` | [source](https://ember-energy.org/data/electricity-data-explorer/), read 2026-09-12 | Indicative tariff for France. |
| `grid_carbon_intensity` | 41.2 gCO2e/kWh | `estimated` | [source](https://api.ember-energy.org/v1/carbon-intensity/yearly), read 2026-10-02 | Annual average for France, data year 2025. |
| `water_usage_effectiveness` | not known | `TODO` | — | On-premises publishes no water usage effectiveness. Leave this open rather than inventing a figure. |
| `hardware_embodied_carbon` | not known | `TODO` | — | No accelerator was identified, so the carbon of building one is not this model's to carry. A processor's own footprint is not in the catalogue yet; it is excluded rather than assumed to be zero. |
| `hardware_lifetime` | not known | `TODO` | — | How long this hardware stays in service, which only you know. The published footprints are cradle-to-gate and exclude the use phase, so none of them states a lifespan. Reported figures cluster between three and six years; choosing within that range moves the embodied carbon by a factor of two, which is why this is asked rather than assumed. |
| `machine_energy` | 4.376e-06 kWh | `measured` | [source](https://doi.org/10.1002/advs.202100707) | runtime in hours x average power in watts / 1000. |

## How it was measured

```
~/miniconda3/bin/python3.13 ~/saggio/examples/walkthrough/counter/predict.py --num_samples 400
```

|  |  |
|---|---|
| exit code | 0 |
| measured on | 2026-10-01 |
| power scope | The figure covers the chip's processor cores, graphics cores, and neural engine, from the system-on-chip's own energy counters and the chip's memory, from its own energy counter, read from the CPU Energy, GPU Energy, ANE0, DRAM0 counters. Memory is measured rather than estimated here: the machine publishes its own memory energy counter, so the figure is what the memory drew rather than what its installed capacity suggests it would draw. These are the chip's own energy counters, which are a model inside the silicon rather than a meter on the power rail, and Apple says they are not a basis for comparing one machine against another. Left out of them: the display, storage, networking, the fans, and the power supply's own losses. |
| cpu seconds | 0.4714 |
| attributed watts | 2.88 |
| attributed scope | the processor cores alone, which is the only part a share of processor work can price |

## Projections

A projection is not a measurement of the thing it projects to.

### whole run

What the whole run would cost, projected from the slice that was measured and from the exponent by which its cost was measured to grow with the size of the job.

|  | Value | Status | Method |
|---|---|---|---|
| time | 56.81 s | `estimated` | Whole run = measured slice / 0.001^0.687. Least squares of log(seconds) on log(size) over 3 runs: seconds = 0.007966 × size^0.687. |
| energy | 0.0007546 kWh | `estimated` | Whole run = measured slice / 0.001^0.687. Least squares of log(seconds) on log(size) over 3 runs: seconds = 0.007966 × size^0.687. |
| money | 0.0001811 USD | `estimated` | Whole run = measured slice / 0.001^0.687. Least squares of log(seconds) on log(size) over 3 runs: seconds = 0.007966 × size^0.687. |
| carbon | 0.04226 gCO2e | `estimated` | Whole run = measured slice / 0.001^0.687. Least squares of log(seconds) on log(size) over 3 runs: seconds = 0.007966 × size^0.687. |

*A million runs emit about 46.1 tree-months · 241.5 km by car (EU average) · 85% of a Paris–London flight — estimated restatements, [Green Algorithms](https://doi.org/10.1002/advs.202100707) coefficients.*

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
