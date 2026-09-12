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
DDR4. The per-core figures and the board wattages come from the hardware catalogue,
each row carrying the datasheet it was read from.

The result is always `estimated`. A datasheet is not a wattmeter.

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
