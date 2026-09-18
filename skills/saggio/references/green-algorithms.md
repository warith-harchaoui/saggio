# The arithmetic

The method is Green Algorithms: Lannelongue, Grealey, and Inouye, *Green
Algorithms: Quantifying the Carbon Footprint of Computation*, Advanced Science,
2021, [doi:10.1002/advs.202100707](https://doi.org/10.1002/advs.202100707).

## The chain

```
machine energy (kWh)  = runtime (hours) x average power (W) / 1000
facility energy (kWh) = machine energy x power usage effectiveness
carbon (gCO2e)        = facility energy x grid carbon intensity (gCO2e/kWh)
money                 = facility energy x price per kWh
water (L)             = machine energy x water usage effectiveness (L/kWh)
```

## The distinction that is easy to lose

The machine draws one amount. The building draws that amount multiplied by its
**power usage effectiveness**, which covers cooling, lighting, and conversion loss.
A power usage effectiveness of 1.0 would be a datacenter with none of those, which
does not exist; a self-run server room is around 1.5, and a large cloud provider
publishes between 1.09 and 1.2.

Carbon and money follow the **facility** figure, because that is what the grid
supplies and the meter counts.

Water follows the **machine** figure. **Water usage effectiveness** is defined as
litres of on-site water per kilowatt-hour of IT load, so it already accounts for
the cooling. Multiplying it by facility energy would count the cooling overhead
twice.

## Estimating power when nothing measured it

```
watts = physical cores x watts per core
      + memory in GB x 0.3725
      + accelerators x board TDP
```

The 0.3725 W per gigabyte is from the paper, derived from manufacturer figures for
DDR4. It applies to the memory **available** to the job, not the memory used:
populated slots idle in a power-hungry state whether or not the algorithm touches
them. The per-core figures and the board wattages come from the hardware
catalogue, each row carrying the datasheet it was read from.

The result is always `estimated`. A datasheet is not a wattmeter.

**The usage factor.** The paper's full formula scales the compute terms by a core
usage factor `u_c` in `(0, 1]`: the fraction of rated power actually drawn while
the code runs. `node_power(usage_factor=...)` accepts it, applied to processors
and accelerators but never to memory. When nothing measured the utilisation the
default stays 1.0, the paper's own assumption — full rated draw is the honest
upper figure, not a hedge. Note the TDP itself can *understate* real draw when
hyperthreading is on (up to 2x in pathological cases), which is one more reason a
datasheet number is `estimated`.

**Storage** draws about 0.001 W per gigabyte — two orders of magnitude below
memory — so it is excluded, as the paper excludes it. The motherboard is excluded
for the same reason the paper gives: it serves every job on the machine at once,
and no fraction of it is attributable to this one.

## The pragmatic scaling factor

An analysis is rarely run once. Parameter tuning, debugging, and re-runs multiply
the footprint by a factor the paper calls the **pragmatic scaling factor** (PSF):
the number of times the computation was actually performed. Its worked examples
use PSF 11 (one per energy level tested), 100 (a conservative hyper-parameter
search), and 180 (operational forecasts per day). saggio's per-unit-of-work
framing composes with it: the model prices one unit, and repetitions are a
multiplication the reader can see, not a hidden assumption.

## Restating carbon so a reader can feel it

Grams of CO2 equivalent are exact and mean nothing to most readers. The paper
contextualises them three ways, implemented in `saggio.estimate.equivalences`
with the paper's coefficients:

```
tree-months = carbon / (11 000 / 12) g   (a mature tree sequesters ~11 kg CO2/year)
car km      = carbon / 175 g (EU fleet)  or / 251 g (US fleet)
flights     = carbon / 50 000 g   (Paris-London, per passenger, economy)
              carbon / 570 000 g  (New York-San Francisco)
              carbon / 2 310 000 g (New York-Melbourne)
```

An equivalence is a restatement, not a new measurement: it inherits the carbon's
status capped at `estimated`, because the tree is an average tree and the car an
average car, and an open carbon figure gives an open equivalence.

## Reference values worth knowing

- Worldwide average grid carbon intensity, as used by the paper: **475 gCO2e/kWh**;
  the national range runs from under 20 (Norway, Switzerland, mainly hydro) to
  880 (Australia, mainly coal and gas).
- Global average datacenter PUE in 2019: **1.67**; Google publishes 1.10; the
  paper uses 1.0, with a caveat, when the machine is a laptop or the PUE unknown.
- For a *relocation* decision the **marginal** carbon intensity — the plant that
  answers the extra demand, usually gas — is the right figure, and the average is
  a lower bound on the benefit of moving.
- The GHG basket behind "CO2e" is CO2, CH4, and N2O under GWP100 (IPCC), which
  together cover 97.9% of global GHG emissions.
- Parallelising has an optimum: past it, adding cores cuts runtime slower than it
  adds power, and the footprint climbs (the paper doubles emissions going from 15
  to 60 cores for a halved runtime).

## Projecting a measured slice to a whole run

```
whole run = measured slice / fraction the slice covered
```

Defensible when the work is uniform. Less so when later stages differ in shape, or
when a one-off cost was paid entirely inside the slice and is now being counted as
though it recurred. The package records both caveats alongside the number, and
refuses a fraction outside `(0, 1]`.

## Projecting onto another accelerator

```
runtime on target = runtime on source x (source peak TFLOP/s / target peak TFLOP/s)
```

This holds only while the work is **compute-bound**. A workload waiting on memory
bandwidth, on storage, or on a data loader will not gain the ratio and may gain
none of it.

It also holds only at the precision the catalogue quotes, which is BF16. Two chips
do not keep the same ratio across precisions: an H100 pulls much further ahead of
an A100 in BF16 than it does in FP32. Asking for a projection in another precision
is refused rather than approximated.

Peak throughput is a datasheet figure, not a benchmark. Real speedups are smaller.

## What is not counted, and why

**Making the hardware.** Embodied carbon is real and large. Amortising it over one
unit of work needs a lifetime and a utilisation figure, both of which would be
guesses, so it is excluded and said to be excluded in every report. A footprint
that quietly leaves out the largest term is worse than no footprint.

**The people.** Salaries, offices, and travel dwarf the electricity, and belong in
a different model.

**Idle capacity.** This is the cost of one unit of work, not the cost of being
ready to do it.

**Generating the electricity's own water.** Water usage effectiveness is on-site
only. Thermoelectric generation consumes considerably more water upstream.
