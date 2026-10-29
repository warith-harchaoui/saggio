# Cost of running saggio — one HTTP request, with the uncertainty carried through

**This model is only as good as its weakest number, which is `estimated`.** Computed from a sourced assumption or a published formula.

Last updated 2026-10-29. Schema 2.1.

## Honesty

| Status | Count | Meaning |
|---|---|---|
| `measured` | 3 | Recorded from an actual run on the target system. |
| `estimated` | 4 | Computed from a sourced assumption or a published formula. |

## One unit of work

**one /scopes request handled end to end**

The same unit of work as `request.yaml`, and the same measured runtime and power. What differs is the grid carbon intensity: there it is a point, here it is scored on the pedigree matrix and carries the interval those scores give. The carbon figure then has to carry an interval too, because a value computed from a number known within a factor cannot be known better than that factor.

Not part of a unit:

- Network transit, since client and server are the same machine.
- Server start-up, which happens before the measurement window.

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

### one request

| Dimension | Per unit | Status | Derived from | Notes |
|---|---|---|---|---|
| Carbon (location-based) | 1.189e-06 gCO2e (9.764e-07 – 1.448e-06) | `estimated` | `scenarios[0].costs.building_energy`, `assumptions.grid_carbon_intensity` | The building's energy multiplied by the grid intensity. The interval is the intensity's interval carried through: the energy is measured and pins down to a point, the intensity does not, so the product cannot be a point either. This is the whole demonstration — nothing here chose to be cautious, the arithmetic left no other answer. |
| Machine energy | 1.924e-08 kWh | `measured` | `scenarios[0].runtime`, `assumptions.power_draw` | runtime in hours x average power in watts / 1000. |
| Building energy | 2.886e-08 kWh | `estimated` | `scenarios[0].costs.machine_energy`, `assumptions.pue` | The machine's energy multiplied by the building's overhead. |

*A million units emit about 0.001297 tree-months · 0.006795 km by car (EU average) — estimated restatements, [Green Algorithms](https://doi.org/10.1002/advs.202100707) coefficients.*

## Where this goes in a GHG inventory

| Cost | Per unit | Status | GHG Protocol |
|---|---|---|---|
| `carbon` | 1.189e-06 gCO2e (9.764e-07 – 1.448e-06) | `estimated` | [Scope 2 (location-based)](https://ghgprotocol.org/scope-2-guidance) |

The scope turns on who operates the machine, which is why the same code lands on a different line of a different company's inventory depending on where it runs.

- **`carbon`** — The organisation operates the machine, so it bought the electricity. The figure here is location-based: a grid-average emission factor for the country, carrying no adjustment for any contractual instrument.

**Only half of what scope 2 requires is here.** The market-based figure is a different number and is not here. It is built from your supplier's own emission factor, from the contractual instruments you hold — guarantees of origin, RECs, a PPA — or, failing both, from your market's residual mix, which exists precisely so that unclaimed electricity is not counted as clean by default. None of the three can be derived from a grid average, so this package reports neither a market-based figure nor a zero. Record the factor as `assumptions.market_carbon_intensity` and the figure is computed and placed beside this one. Where contractual instruments exist in your market, the GHG Protocol requires both numbers, each labelled with the method that produced it.

How well founded these are: 1 `estimated`. A sustainability disclosure is asked to state how much of an inventory rests on estimates rather than readings; every number in this report already says so.

## What the numbers rest on

| Assumption | Value | Status | Provenance | Notes |
|---|---|---|---|---|
| `power_draw` | 17.98 W | `measured` | — | Read from the machine while the command ran. The figure covers the chip's processor cores, graphics cores, and neural engine, from the system-on-chip's own energy counters and the chip's memory, from its own energy counter, read from the CPU Energy, GPU Energy, ANE0, DRAM0 counters. Memory is measured rather than estimated here: the machine publishes its own memory energy counter, so the figure is what the memory drew rather than what its installed capacity suggests it would draw. These are the chip's own energy counters, which are a model inside the silicon rather than a meter on the power rail, and Apple says they are not a basis for comparing one machine against another. Left out of them: the display, storage, networking, the fans, and the power supply's own losses. This is the whole machine's draw, not this run's alone: these counters meter hardware and not processes, so whatever else the machine was doing while the command ran is inside the figure. Nothing here established how much of it was, so treat the figure as an upper bound on what the run cost and not as what it cost. Measured once, so nothing here bounds how far a second run would move it. Pass `--repeat N` to find out. |
| `pue` | 1.5 ratio | `estimated` | [source](https://www.uptimeinstitute.com/resources/research-and-reports/uptime-institute-global-data-center-survey-results-2024), read 2026-09-12 | Power usage effectiveness published by On-premises. |
| `grid_carbon_intensity` | 41.2 gCO2e/kWh (33.83 – 50.18) | `estimated` | [source](https://ember-energy.org/data/yearly-electricity-data/), read 2026-10-17 | Annual average for France, data year 2025. The scores read: a published dataset whose method is documented but which rests partly on reported rather than metered figures (reliability 2); the whole country rather than a sample of it (completeness 1); one year older than the period modelled (temporal 2); the country being modelled (geographical 1); an annual average standing in for the mix at the hour the request ran, which is a different technology on a different day (technological 3). The basic uncertainty is stated here and is not supplied by this package: it depends on the kind of quantity, and the published table that sets it describes industrial flows rather than these dimensions. |

## Not counted

- Idle capacity is inside these figures, not outside them. The power was read from the machine's own counters, which meter hardware and not processes.
- Making the hardware. Only the electricity to run it is counted.
- The people. Salaries, offices, and travel are out of scope.

---

Generated by [saggio](https://github.com/warith-harchaoui/saggio).
