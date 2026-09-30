# What an analysis is allowed to produce

Two ways to learn what code costs, and the line between them is which one may
write a number into a cost model.

The long form, with the evidence, is [`ANALYSIS.md`](../../../ANALYSIS.md) and
[`ANALYSE.md`](../../../ANALYSE.md). This page is the rule an agent applies
without re-reading the literature.

## The division of labour

**Static analysis owns the counting.** Languages, archetype, frameworks, the
declared size of a full run, which paid services are called and on which line.
Every one of those is a fact about the text, checkable by re-reading the text.

**Dynamic analysis owns the quantities.** Duration from a clock, energy from a
counter, a share of time from a profile, a scaling exponent from repeated runs.

**Neither owns a wattage inferred from source.** There is no path from the shape
of a Python file to joules, and the attempts that exist need a per-instruction
energy model for the target processor, which no laptop, server, or GPU has.

## May produce a number

| Analysis | Output | Status |
|---|---|---|
| Declared work size, read from the repository's own configuration | A count of units | `estimated` |
| Wall time, CPU time of a slice | Seconds | `measured` |
| Energy counter read twice, with a named scope | Joules | `measured` |
| `FLOPs ≈ 6 · N · D`, when parameters and tokens are both declared | Operations | `estimated`, with the coefficient's source |
| Scaling exponent `b` from `y = a · x^b` over three or more slice sizes | An exponent and an R² | `measured` over the sizes run |
| Instruction count under Cachegrind | A count | `measured`; never converted to energy |

## May not produce a number, ever

| Analysis | Why not |
|---|---|
| Cyclomatic, cognitive, or Halstead complexity | R² ≈ 0.005 against measured energy on its own. It would look like a checked figure. |
| Rule-catalogue findings scored or totalled | A rule count is not a quantity and does not compare between repositories. Quote the file and the line instead. |
| Complexity predicted by a language model | A number nobody can check. The same rule as every other figure a model produces. |
| A datasheet wattage presented as a reading | It is what the part can draw, not what this machine drew. `estimated`, and the note says nameplate. |
| Node power inferred from a counter by adding an offset | The gap between a counter and the wall is not constant: measured regression slopes of 1.17 and 1.18, varying per node. |

## Four facts that decide designs

**Time carries the variance.** Controlled for cores, warm-up and libraries, the
choice of language implementation has no significant effect on energy beyond
execution time. Measure duration hardest; read power off a counter; never infer
either from source.

**Fast sampling distorts what it measures.** RAPL-based tools polling at 1 kHz
show time overheads from 0.25% to 46.75%, and energy overheads above 40%. At
1 Hz the overhead is negligible. Prefer an accumulating counter read twice over
a sampled wattage, and keep any unavoidable sampler slow.

**Data movement dominates arithmetic.** At 45 nm, a floating-point operation
costs 0.4–3.7 pJ and an off-chip 64-bit DRAM access 1300–2600 pJ. An estimate
built on operation counts alone is counting the cheap part, which is why a
projection onto another accelerator is a bracket and not a number.

**A profile is not free.** `cProfile` charges per call and inflates the wall
time that every downstream figure multiplies. A run taken with the profiler
attached says so.

## The open improvement

`project_to_completion` assumes the work is uniform and records the assumption.
Running the slice at three or more sizes read from the repository's own
configuration, and fitting `y = a · x^b`, turns that assumption into a measured
exponent with a goodness-of-fit. A poor fit is a finding: the slice is not
representative, and the projection should refuse rather than extrapolate.
