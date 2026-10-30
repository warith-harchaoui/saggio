# Cost of running saggio — one HTTP request served

**This model is only as good as its weakest number, which is `TODO`.** A human must supply this before the model can be trusted.

Last updated 2026-10-18. Schema 2.1.

## Honesty

| Status | Count | Meaning |
|---|---|---|
| `measured` | 4 | Recorded from an actual run on the target system. |
| `estimated` | 10 | Computed from a sourced assumption or a published formula. |
| `TODO` | 15 | A human must supply this before the model can be trusted. |

## One unit of work

**one /scopes request handled end to end**

One POST to the HTTP surface's /scopes route, placing a small cost model in a greenhouse-gas inventory and answering as JSON. Measured over two hundred requests from a client on the same machine, so the figure covers the client and the server together: that is what the machine's counter can see, and splitting it would be a model rather than a measurement.

Not part of a unit:

- Network transit, since client and server are the same machine.
- Server start-up, which happens before the measurement window.
- TLS, which a local HTTP listener does not do.

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
| Money | 7.966e-09 USD | `estimated` | `scenarios[0].costs.energy`, `assumptions.electricity_price` | Facility energy x price per kilowatt-hour; hardware and staff are not included. |
| Time | 3.853 ms | `measured` | `scenarios[0].runtime` | Timed with `saggio measure`: python3 -c  import json, urllib.request body = json.dumps({"cost_model": {"deployment": {"provider": "on-prem"},  "scenarios": [{"name": "one", "costs": {"carbon": {"value": 1.4, "unit": "gCO2e", "status": "estimated"}}}]}}).encode() for _ in range(200):     req = urllib.request.Request("http://127.0.0.1:8795/scopes", data=body, headers={"content-type": "application/json"})     urllib.request.urlopen(req, timeout=10).read() . The command performed 200 units of work, so the figure is the wall-clock time divided by 200. Measured once, so nothing here bounds how far a second run would move it. Pass `--repeat N` to find out. |
| Energy | 2.886e-08 kWh | `estimated` | `assumptions.machine_energy`, `assumptions.pue` | Machine energy x power usage effectiveness: what the building draws. |
| Carbon (location-based) | 1.189e-06 gCO2e | `estimated` | `scenarios[0].costs.energy`, `assumptions.grid_carbon_intensity` | Facility energy x grid carbon intensity, operating emissions only. |
| Carbon (market-based) | not known | `TODO` | `scenarios[0].costs.energy`, `assumptions.market_carbon_intensity` | Needs the energy drawn and the emission factor of the electricity you contracted for. A grid average is the other method and will not do here. |
| Embodied carbon | not known | `TODO` | `assumptions.hardware_embodied_carbon`, `assumptions.hardware_lifetime`, `scenarios[0].runtime` | No product carbon footprint is on file for this hardware, so the carbon of building it is open. Nobody has read one for this part; that is not the same as it having been free to build. Add an `embodied_kgco2e` to the catalogue row with the footprint's own URL and the date it was read. |
| Water | not known | `TODO` | `assumptions.machine_energy`, `assumptions.water_usage_effectiveness` | Needs the machine's energy and a published water usage effectiveness. |

*A million units emit about 0.001297 tree-months · 0.006795 km by car (EU average) — estimated restatements, [Green Algorithms](https://doi.org/10.1002/advs.202100707) coefficients.*

## Where this goes in a GHG inventory

| Cost | Per unit | Status | GHG Protocol |
|---|---|---|---|
| `carbon` | 1.189e-06 gCO2e | `estimated` | [Scope 2 (location-based)](https://ghgprotocol.org/scope-2-guidance) |
| `carbon_market_based` | not known | `TODO` | [Scope 2 (market-based)](https://ghgprotocol.org/scope-2-guidance) |
| `embodied_carbon` | not known | `TODO` | [Scope 3, category 2 — capital goods](https://ghgprotocol.org/corporate-value-chain-scope-3-standard) |

The scope turns on who operates the machine, which is why the same code lands on a different line of a different company's inventory depending on where it runs.

- **`carbon`** — The organisation operates the machine, so it bought the electricity. The figure here is location-based: a grid-average emission factor for the country, carrying no adjustment for any contractual instrument.

- **`carbon_market_based`** — The organisation operates the machine, so it bought the electricity, and it bought it under a contract. The figure here is market-based: the emission factor of the electricity this organisation contracted for, rather than the average of the grid it drew from. It rests on a factor you stated, which is the one fact about this number nobody else holds — this package neither derived it nor can refresh it.

- **`embodied_carbon`** — The organisation operates the machine, so it bought the hardware. Capital goods rather than purchased goods and services, because the asset's useful life is longer than a year — which is the distinction the standard draws between the two categories, and also the reason this figure is amortised rather than counted once.

**Only half of what scope 2 requires is here.** The market-based figure is a different number and is not here. It is built from your supplier's own emission factor, from the contractual instruments you hold — guarantees of origin, RECs, a PPA — or, failing both, from your market's residual mix, which exists precisely so that unclaimed electricity is not counted as clean by default. None of the three can be derived from a grid average, so this package reports neither a market-based figure nor a zero. Record the factor as `assumptions.market_carbon_intensity` and the figure is computed and placed beside this one. Where contractual instruments exist in your market, the GHG Protocol requires both numbers, each labelled with the method that produced it.

How well founded these are: 2 `TODO`, 1 `estimated`. A sustainability disclosure is asked to state how much of an inventory rests on estimates rather than readings; every number in this report already says so.

## What the numbers rest on

| Assumption | Value | Status | Provenance | Notes |
|---|---|---|---|---|
| `power_draw` | 17.98 W | `measured` | — | Read from the machine while the command ran. The figure covers the chip's processor cores, graphics cores, and neural engine, from the system-on-chip's own energy counters and the chip's memory, from its own energy counter, read from the CPU Energy, GPU Energy, ANE0, DRAM0 counters. Memory is measured rather than estimated here: the machine publishes its own memory energy counter, so the figure is what the memory drew rather than what its installed capacity suggests it would draw. These are the chip's own energy counters, which are a model inside the silicon rather than a meter on the power rail, and Apple says they are not a basis for comparing one machine against another. Left out of them: the display, storage, networking, the fans, and the power supply's own losses. This is the whole machine's draw, not this run's alone: these counters meter hardware and not processes, so whatever else the machine was doing while the command ran is inside the figure. Nothing here established how much of it was, so treat the figure as an upper bound on what the run cost and not as what it cost. Measured once, so nothing here bounds how far a second run would move it. Pass `--repeat N` to find out. |
| `pue` | 1.5 ratio | `estimated` | [source](https://www.uptimeinstitute.com/resources/research-and-reports/uptime-institute-global-data-center-survey-results-2024), read 2026-09-12 | Power usage effectiveness published by On-premises. |
| `electricity_price` | 0.276 USD | `estimated` | [source](https://www.globalpetrolprices.com/electricity_prices/), read 2026-10-17 | Indicative tariff for France. Collected Q3 2026. |
| `grid_carbon_intensity` | 41.2 gCO2e/kWh | `estimated` | [source](https://ember-energy.org/data/yearly-electricity-data/), read 2026-10-17 | Annual average for France, data year 2025. |
| `market_carbon_intensity` | not known | `TODO` | — | The emission factor of the electricity you contracted for, which no catalogue can hold: it is a property of your contract, not of your country. It is built from your supplier's own emission factor, from the contractual instruments you hold — guarantees of origin, RECs, a PPA — or, failing both, from your market's residual mix, which exists precisely so that unclaimed electricity is not counted as clean by default. Record it with the supplier document or certificate that states it and the date you read it — this is the one figure in the model nobody else can check and nothing here can refresh. Leaving it open is a complete answer; a zero because the electricity is 'green' is not one. |
| `water_usage_effectiveness` | not known | `TODO` | — | On-premises publishes no water usage effectiveness. Leave this open rather than inventing a figure. This room is in a European Union Member State, where large data centres must report their water: the `on-prem-eu` provider carries the Union-wide average published from that duty. Name it only if this room resembles it. |
| `hardware_embodied_carbon` | not known | `TODO` | — | No product carbon footprint is on file for apple-m2-max. Add `embodied_kgco2e` to its catalogue row with the footprint's own URL and the date it was read; `saggio catalog add cpu` does the rest. |
| `hardware_lifetime` | not known | `TODO` | — | How long this hardware stays in service, which only you know. The published footprints are cradle-to-gate and exclude the use phase, so none of them states a lifespan. Reported figures cluster between three and six years; choosing within that range moves the embodied carbon by a factor of two, which is why this is asked rather than assumed. |
| `machine_energy` | 1.924e-08 kWh | `measured` | [source](https://doi.org/10.1002/advs.202100707) | runtime in hours x average power in watts / 1000. |

## Services this code pays for

Prices are not copied into this model. An API price copied today is wrong by next quarter, so the report says where the current one lives and leaves the figure open until somebody reads it.

| Service | Found at | Evidence | Per unit | Where to price it |
|---|---|---|---|---|
| OpenAI API | `tests/conftest.py:113` | `(root / "serve.py").write_text("import openai\nclient = openai.OpenAI()\n", encoding="utf-8")` | not known | [prices](https://openai.com/api/pricing/) |

## Models this code calls

A rate is not a cost. These are what the vendor charges per unit; how many of those units one unit of work spends is the open half, and reading the code cannot establish it.

### `examples/walkthrough/5-run.yaml` — found at `tests/unit/test_ghg.py:272`

_No published rate was found for this model._

### `/nonexistent.yaml` — found at `tests/unit/test_ghg.py:312`

_No published rate was found for this model._

### `gpt-4o` — found at `tests/unit/test_static.py:307`

_No published rate was found for this model._

### `claude-3-5-sonnet` — found at `tests/unit/test_static.py:317`

_No published rate was found for this model._

### `mistral-large-latest` — found at `tests/unit/test_static.py:318`

_No published rate was found for this model._

### `AMD EPYC 7742` — found at `tests/unit/test_machine_detection.py:35`

_No published rate was found for this model._

### `Imaginary Foo 9000` — found at `tests/unit/test_machine_detection.py:92`

_No published rate was found for this model._

## Projections

A projection is not a measurement of the thing it projects to.

### whole run

What a whole run would cost, from the per-unit costs in scenarios[0]. A whole run performs 400000 num_samples, as examples/walkthrough/counter/config.py::num_samples states. This assumes one unit of work is one num_sample; if the model's unit of work means something else, restate this.

|  | Value | Status | How it was obtained |
|---|---|---|---|
| time | 25 min 41 s (1,541.4 s) | `estimated` | Whole run = measured slice / 2.5e-06. |
| energy | 0.01155 kWh | `estimated` | Whole run = measured slice / 2.5e-06. |
| money | 0.003187 USD | `estimated` | Whole run = measured slice / 2.5e-06. |
| carbon | 0.4757 gCO2e | `estimated` | Whole run = measured slice / 2.5e-06. |

**What it assumes**

- The remaining work costs the same per unit as the slice that was run.
- Warm-up, checkpointing, and data loading are spread evenly across the run.

**Where it breaks**

- A run whose later stages differ in shape, such as a learning-rate schedule that changes batch size, will not scale linearly.
- One-off costs paid entirely inside the slice are counted as though they recurred throughout.
- Nothing here checked that the work is uniform. Measuring a few slices of different sizes would turn that assumption into an exponent; see saggio.estimate.scaling.

*A million runs emit about 518.9 tree-months · 2,718 km by car (EU average) · 9.513 Paris–London flights — estimated restatements, [Green Algorithms](https://doi.org/10.1002/advs.202100707) coefficients.*

## Not counted

- Making the hardware. Only the electricity to run it is counted.
- The people. Salaries, offices, and travel are out of scope.
- Idle capacity is inside these figures, not outside them. The power was read from the machine's own counters, which meter hardware and not processes.

## Rules this model follows

- Every sourced value carries source_url and retrieved_date.
- A derived value names its inputs and never outranks the weakest of them.
- The country is stated by a human, never inferred from a developer's locale.

---

Generated by [saggio](https://github.com/warith-harchaoui/saggio).
