# Changelog

This project follows [semantic versioning](https://semver.org/). The cost-model
schema is versioned separately, in its own `schema_version` field: within a major
line it only grows, so a model written today keeps validating against every later
release of that line.

## 1.2.0 — 2026-10-01

### The hardware's own carbon, and the standard it completes

- A new canonical dimension, `embodied_carbon`: what building the hardware
  emitted, amortised over the share of its life one unit of work reserved.
  Manufacturing one HGX H100 baseboard emits 1,312 kgCO2e before it computes
  anything, and a model that reported only the electricity was claiming that
  figure was zero.
- `saggio.embodied_carbon` implements the Software Carbon Intensity
  specification's `M = TE × TS × RS`, and `saggio.software_carbon_intensity`
  assembles `(E × I + M) per R` — refusing when either half is open, because
  reporting one of them under the name of a standard would understate it with
  the standard's authority.
- Three sourced footprints in the catalogue, each read from its own primary
  document and carrying its boundary in words: A100 at 127.6 kgCO2e from a
  teardown LCA, H100 at 164.0 and B200 at 284.25 from NVIDIA's own ISO
  14067 product carbon footprints, both one eighth of a baseboard. A part with
  no row gives a `TODO` saying nobody has read a footprint for it, which is not
  the same as it having been free to build.
- **The lifespan ships open, on purpose.** Every one of those footprints is
  cradle-to-gate and excludes the use phase, so the vendor gave the numerator
  and withheld the denominator. `assumptions.hardware_lifetime` is a `TODO`
  until a human states it; published figures cluster between three and six
  years and that range alone moves the answer by a factor of two.
- The amortisation is calendar time, as the specification defines it, so a card
  idle half its life charges that half to nobody. Every figure says so, because
  the common alternative gives a larger number and is not what the standard
  says.
- `STANDARDS.md` and `NORMES.md` are the new bilingual page: the four terms,
  where each comes from, and — the half of a conformance claim worth reading —
  exactly where this is *not* conformant. Plus what the EU AI Act's Annex XI
  asks, which is less: energy rather than emissions, no embodied carbon at all,
  and disclosure to the regulator rather than the public.

### The baseline stops costing what it cannot buy

- A machine that publishes no counter no longer waits a second to find that out.
  `PowerMeter.reads_anything()` answers from the opening readings the meter has
  already taken, so `measure_for` skips the sleep and returns the same "not
  measured" it would have returned a second later. Asked of the meter rather
  than of `saggio.analyze.capability.probe()`, which runs `nvidia-smi` and has
  no business in the path of every measured run.
- `saggio audit --baseline SECONDS`, matching `saggio measure`, and
  `AuditOptions.baseline_seconds` behind it. An audit could not be told to skip
  a second it does not need, and a scaling series could not be told either; both
  can now. A scaling series already took **one** baseline for the whole ladder
  rather than one per rung, and still does.


### The landscape, read again against what shipped

- `LANDSCAPE.md` and `PAYSAGE.md`: the self-criticism had gone out of date in the
  direction that flatters, which is the worse direction for a page whose premise
  is honesty. "Nothing on macOS or Windows" and "no GPU power measurement" were
  both true when written and are not now, so they are replaced by the gaps that
  remain: nothing is attributed to a *process*, Windows still publishes no
  unprivileged counter, and a counter is not the wall — the gap to a physical
  meter is a slope of about 1.17 that varies per node, not a constant anyone
  could add back.
- One rating moves, and only because something checkable shipped: **Measures
  power** goes from three stars to four. Not five, because the fifth is
  per-process attribution and Scaphandre, PowerAPI and Kepler have it.
- Kepler's entry notes its 2026 move off eBPF to `/proc` and `/sys`, dropping
  `CAP_BPF` and `CAP_SYSADMIN`. CodeCarbon's notes the measured price of its
  sampling: 5.4% to 46.8% time overhead at 1 kHz in a 2026 study of RAPL-based
  tools, which argues for its default interval rather than against the tool.
- The positioning map is regenerated from the refreshed table. The axes come out
  as *Efficient ↔ Transparent* (55%) and *Accessible ↔ Robust* (25%), 80%
  together, and the placement tells the same story as before — which is the
  point of regenerating rather than redrawing.

### The diagrams carry colour

- The Mermaid diagram in `ANALYSIS.md` and `ANALYSE.md` is coloured with Okabe
  and Ito's colour-vision-deficiency-safe set, the palette the reports and the
  website already use: blue for what is read, green for what is run, the kept
  answer filled, the refusal dashed in vermillion. Every colour sits beside a
  written label, so it carries emphasis and never the meaning on its own.


### The whole-run projection stops assuming the work is uniform

- `saggio audit --scaling-steps N` runs the slice at N sizes a factor of four
  apart instead of once, and fits `seconds = a × size^b` by least squares on
  log-log axes. The projection to a whole run becomes
  `slice / fraction ** exponent`, which is the division it always was when the
  exponent is one and is a factor of a thousand different when the work is
  quadratic and the slice was a thousandth.
- The exponent is `measured`, over the sizes that were run and nowhere else: it
  summarises readings off a clock, the way watts from an energy counter over a
  duration do. The projection stays `estimated`, because a measurement of
  something smaller was never a measurement of this. R² and every run the fit
  used travel with it in `measurement.scaling`, so a reader can redo the
  arithmetic instead of taking the exponent on trust.
- The refusals are the point. Fewer than three sizes — two points fit a straight
  line exactly and rule nothing out — a size range under a factor of four, a
  size or duration that has no logarithm, or a fit explaining less than 95% of
  the variation: each returns a refusal naming what would resolve it.
- A fit whose exponent comes out *negative* is refused too, and separately from
  the goodness of fit, because a downward line through three points fits
  beautifully and means nothing. Work does not shrink when there is more of it:
  larger runs finishing sooner says something other than the work decided the
  durations — start-up dominating every rung, a cache warming, another process
  on the machine — and the refusal says so and suggests `saggio power`. Zero is
  still an answer: constant cost is what it looks like. Found by the audit test
  failing on a machine that had another job on it, where the exponent came out
  at -0.08 and the validator rejected it as a negative cost, failing the whole
  audit instead of leaving one figure open.
- A fit that poor changes an answer rather than withholding one. It means the
  slice is not representative of the run it was cut from, so the whole-run block
  is not written at all and the reason reaches the reader. Having measured the
  scaling and failed is kept distinct from never having looked: without the flag
  the projection keeps the linear assumption and records it, and now also
  records that nothing checked it.
- The ladder is cheap on purpose. Its top rung is the slice that would have been
  run anyway, and the rungs below it add a quarter and a sixteenth of it, so the
  series costs about 1.3 times the single slice. It runs without the profiler,
  because cProfile charges per call and would fit its own growth curve; the
  trade is no hot path, and in exchange every cost figure comes from an
  unprofiled run rather than an inflated one.
- New: `saggio.estimate.scaling` (`Observation`, `ScalingFit`, `fit_power_law`),
  `saggio.analyze.static.scaling_ladder`,
  `saggio.analyze.run.run_scaling_series`, and a `scaling` keyword on
  `project_to_completion`. Exported at the top level. `EXAMPLES.md` and
  `EXEMPLES.md` show the command, the YAML, and the refusals; `ANALYSIS.md` and
  `ANALYSE.md` record why this was the one change worth making.


### What reading code, and running it, can each be asked

- `ANALYSIS.md` and `ANALYSE.md`: the investigation behind the package's
  division of labour between the static pass and the measured one. What static
  cost-bound analysis (COSTA, RaML, KoAT) and static energy analysis (worst-case
  energy consumption on an instruction set) actually require, why neither reaches
  a Python repository on a machine with an accelerator, and what static analysis
  is genuinely good for here.
- The refusals are argued rather than asserted, and the central one is now
  sourced: static source metrics predict measured energy with an R² near zero on
  their own, rising to 0.46 once execution time is added. A cyclomatic complexity
  figure may therefore never appear in a cost model, in any status, because it
  would look exactly like a checked number.
- The empirical side is the useful half. trend-prof's method — run over sizes
  spanning orders of magnitude, fit `y = a·x^b`, report the goodness of fit —
  would turn `project_to_completion`'s standing assumption that work is uniform
  into a measured exponent, using a work size the static pass already reads.
  Recorded as the one change worth making.
- The measurement discipline the package already follows is now backed by its
  sources: the gap between a counter and the wall is not a constant offset
  (regression slopes of 1.17 and 1.18, varying per node), and a sampler polling
  at 1 kHz distorts the wall time every downstream figure multiplies.
- `skills/saggio/references/code-analysis.md` is the short form an agent applies:
  which analyses may produce a number and under which status, and which may not,
  ever.


### macOS measures power now, and asks nobody for a password

- `saggio.analyze.apple` reads an Apple Silicon chip's own energy counters
  through `IOReport`, as an ordinary user. Processor cores, graphics cores,
  neural engine, and memory, as monotonic counters in units the library labels
  itself, so a measurement is a difference between two reads rather than a mean
  of samples. Every Mac in this package's history reported `not measured` and
  fell back to a datasheet; that was a limitation of the code, not of macOS.
- The figures carry what they are: the chip's own energy model rather than a
  meter on the power rail, and Apple's own warning that they do not compare
  across machines. Which is true of Intel's RAPL too, on every part that is not
  a Haswell server chip.

### The Linux counters are read by name, and the memory beside them is no longer lost

- Powercap zones are read by the name each zone gives itself rather than by the
  shape of its directory. That is what tells a package apart from the `psys`
  zone that already contains it — now preferred when present, never added to the
  packages — and from the `dram` zone beside it, whose energy is **not** inside
  the package figure and was therefore missing from every reading this package
  ever took on a machine that publishes it.
- `amd-rapl` zones are read like `intel-rapl` ones. `intel-rapl-mmio`, which is
  the same package through a second interface, is still left alone.
- A counter that passed its ceiling once during a run is unwrapped by its
  published `max_energy_range_uj` instead of voiding the measurement, and the
  figure carries the wattage above which that recovery would have been wrong. A
  counter that was *reset* rather than wrapped is still refused.
- Where NVIDIA is not the board present, Linux's own `amdgpu`, `i915`, and `xe`
  drivers are read through sysfs — an accumulated microjoule counter where the
  driver keeps one, sampled instantaneous watts where it does not. No vendor
  tool, no privileges.

### `saggio power` says what this machine will let you read, and never opens it for you

- A new verb reports every energy interface relevant to this platform in one of
  four states: `reads`, `blocked`, `root-only`, `absent`. The distinction is the
  point. A counter that is absent and a counter that is present but closed to
  you are different situations, and "could not measure power" told a reader
  nothing they could act on.
- `blocked` is the only state with a remedy, and the remedy is printed rather
  than run, with the reason the counter is shut beside it: Linux has kept
  `energy_uj` root-only since 5.10 because sampling it fast enough recovers what
  other processes are computing — CVE-2020-8694, the PLATYPUS attack. Reopening
  a published side channel on a shared machine is a judgement, and it stays the
  reader's.
- Nothing in this package escalates: no `sudo`, no password prompt, no quiet
  fall-back to a tool that would ask for one. `powermetrics` and the baseboard
  controller are named as `root-only` and left alone.
- `saggio power --seconds N` measures the machine itself for N seconds, so the
  counters can be seen working before a run depends on them — and so a reader
  meets, early, the fact that a machine-wide counter measures the machine and
  not their program.
- `saggio power --json` prints the same thing as data, including the exact
  filesystem paths that would be read.

### A run can be projected onto another processor, using what was measured

- `project_to_processor` scales a measured runtime from one processor to
  another. A processor has two speeds that do not move together — one thread on
  one core, and every core busy at once — so a part with many slow cores wins
  the second and loses the first, and the two speeds are the two ends of a
  bracket rather than one number.
- Which end applies is measured, not assumed. `SliceResult.cores_busy()` is
  processor-seconds over wall-clock seconds: near one the run follows the
  single-threaded ratio and a many-core target makes it *slower*; near the
  machine's core count it follows the throughput ratio; between the two nothing
  is settled and the slower end is quoted.
- The catalogue gains `cores` on the processor rows whose own notes already
  stated it, and the two score columns the projection reads. The scores ship
  empty on purpose: a processor publishes no peak figure worth scaling by, so
  the refusal explains how to take one from a published result, divide it by the
  system's socket count, and record which benchmark it was. A score of one
  benchmark is never divided by a score of another — that is refused by name.

### A measurement now has a floor under it

- A counter measures the machine, not your program. `saggio measure` watches the
  machine for a second before the slice starts and reports three figures: what
  the machine drew during the run, what it drew at rest before it, and the
  difference — which is the only one of the three that is about the slice.
  `--baseline 0` skips it on a machine known to be quiet.
- The subtraction assumes the rest of the machine kept doing what it was doing,
  and that assumption is written into the model beside the number rather than
  left for the reader to supply. The floor itself is recorded as
  `measurement.idle_watts`, diagnostic like `cpu_seconds` rather than a cost.
- Two cases are said out loud instead of subtracted quietly. A machine already
  drawing more than half the total is called out as busy, with both numbers in
  the warning. A machine that grew *quieter* during the slice yields no marginal
  figure at all: whatever else was running stopped, so the baseline was never
  this slice's floor and nothing follows from it.

### A page about measuring, in both languages

- `MEASURING.md` / `MESURER.md`: which counters exist on each platform, which
  ones this machine will let *you* read, what each of them covers and leaves
  out, what happens to the number afterwards, and how to check any of it by
  hand. Every claim links to the interface it describes — the kernel's powercap
  and hwmon ABIs, the `xe` sysfs documentation, NVML, Microsoft's Energy Meter
  Interface, Redfish — and the reason the Linux counter is shut links to the
  attack that shut it.
- Two contract tests now walk every markdown page in the repository rather than
  the documentation map alone: a relative link that points nowhere fails the
  build, and so does a link to a section heading that no longer exists. A table
  of contents rots by having a heading reworded underneath it, and that is now
  caught rather than noticed.

## 1.1.0 — 2026-09-18

### Carbon is restated in terms a reader can feel

- `saggio.estimate.equivalences` restates a carbon figure the three ways the
  Green Algorithms paper does, with the paper's own coefficients: months of
  sequestration by a mature tree (11 kg of CO2 a year), kilometres in an average
  passenger car (175 g/km in Europe, 251 in the United States), and a fraction
  of a reference flight (Paris–London, New York–San Francisco, New York–Melbourne).
  An equivalence is a restatement, not a new measurement: it inherits the
  carbon's status capped at `estimated`, and an open carbon figure gives an open
  equivalence. Nothing becomes more convincing by being turned into trees.
- Both reports now carry the felt-size line under every scenario and projection
  whose carbon is known. A figure under a kilogram per unit is restated per
  million units, and the sentence says so. The HTML version translates its
  labels, so the French report speaks of mois-arbre.

### The reports grew the calculator's flagship panel, and a team view

- The HTML report's what-if card ends with *how the location moves the carbon*:
  one bar of grid intensity per country, sampled across the catalogue so the
  cleanest and dirtiest grids always anchor the scale, the model's own country
  in the accent colour. Hand-authored inline SVG on the page's own tokens, with
  its polarity stated.
- `saggio dashboard model.yaml [model.yaml ...]` renders every committed model
  on one self-contained page. It leads with the only comparison that is honest
  across projects — the share of each model that is measured, estimated, or
  still open — and says plainly that the cost rows, each per its own unit of
  work, do not compare with each other.
- The HTML report gains the measurement section the Markdown always had: the
  command, the hot path, and the warnings that qualify every number above.

### The power estimate accepts a usage factor

- `node_power(usage_factor=...)` scales the processor and accelerator terms by
  the Green Algorithms core usage factor, never the memory term, because memory
  draws by being populated rather than by being busy. The default stays the
  paper's own: full rated draw when nothing measured the utilisation.

### One audit of the whole package, and what it closed

Three passes of verified-by-execution review covered every module, and each
finding landed with a regression test. The ones a user could have met:

- A `TODO` or `placeholder` smuggling a value can no longer be computed with:
  `is_known()` now means a finite number under a status entitled to one, so
  estimators, projections, and equivalences leave the result open instead of
  laundering it. The validator also sees numbers hidden inside a quantity's own
  fields, rejects NaN and infinity, names string-typed values, warns on the
  template's literal `YYYY-MM-DD`, and reports scenario faults at the document's
  own indices.
- A timed-out slice now ends the whole process tree it spawned, not just the
  direct child; its stdout no longer buffers unbounded in the auditor's memory;
  the child's processor time is recorded. The RAPL reader no longer double-counts
  package subzones, and the sampled accelerator figure multiplies by the board
  count instead of reporting an eight-board node at the wattage of one.
- Work sizes written `6e5` are read whole, not as their mantissa; a commented-out
  size no longer outranks the real one; a repository cloned under a directory
  named `build` is still read; `openai_agents` no longer matches `openai`.
- A partial catalogue overlay updates its columns instead of erasing the ones it
  did not restate; an unquoted `NO` key is refused out loud; a future
  `retrieved_date` reads as stale; the aggregator price table is fetched once
  per process instead of once per detected model.
- `diff` fails the gate on a unit or currency switch even at an equal number;
  `fold` refuses an invalid model up front and writes the energy row its money
  and carbon derivations stand on; `total_money` refuses a currency-less amount
  next to a currency; negative runtimes, powers, tariffs, and intensities are
  refused as the sign errors they are.
- `saggio catalog` with no action exits as the usage error it is; a hostile URL
  cannot break a Markdown table; a malformed catalogue row cannot take the HTML
  page down; the dashboard, the projections table, and the bar controls all
  translate.


### A measurement can be put into a model without retyping it

- `saggio measure --into MODEL` writes the measured runtime into a cost model and
  recomputes everything that derives from it: the machine's energy, the facility's
  energy, the money and the carbon, by the same functions the audit uses. This is
  the step people got wrong by hand, and until now there was no other way to take
  it: pasting a runtime into the YAML left the energy, the money and the carbon
  holding their old values, and a model whose energy no longer matches its runtime
  is worse than one that had neither, because it looks finished.
- `--units N` says how many units of work the command performed, so the recorded
  figure is per unit. When the model already states how much work a whole run
  performs, a whole-run projection follows, carrying the assumption it rests on:
  that one unit of work is one of the things the repository counts.
- A power figure the machine actually measured replaces the catalogue's estimate,
  and a reading that measured nothing leaves the estimate alone rather than
  replacing a sourced number with silence.
- Three things are refused rather than written: a command that exited non-zero,
  because a failed run measured a failure and a failure has no cost per unit of
  work; a model with no scenario to write into; and any result that would no
  longer validate. Nothing is written by halves, and every figure that moved is
  printed.

### Three defects the gallery exposed, fixed

- **A type annotation is no longer read as a model being called.** Auditing
  Whisper reported a model named `Whisper`, from `model: "Whisper", mel: Tensor`
  in a function signature. Python has no unquoted mapping keys, so a colon after a
  bare name is an annotation; JavaScript, TypeScript and Go do have them, and
  there the same line really is a model being chosen. The detector now knows which
  language it is reading.
- **A string being built is no longer read as a model being named.** Auditing
  FastAPI reported a model named `Body_`, from `model_name = "Body_" + name` in its
  own internals. A literal with a concatenation, an interpolation or a format call
  against it is a fragment, not a name.
- **A training configuration now outranks an evaluation one.** Auditing DINOv2
  took the length of a training run from `configs/eval/`, because the rule was
  alphabetical within a rank and `eval` sorts before `train`. A repository that
  separates the two is saying which one a real run reads. Directory names decide
  it, never the file's own name, and the disagreement is still reported either way.

### A gallery, with the files in it

- `GALLERY.md` and `GALERIE.md` introduce six cost models this package produced,
  committed under `examples/` with the report rendered beside each one: nanoGPT,
  Whisper, DINOv2, FastAPI, Airflow, and this repository. Every one names the
  command that regenerates it. "Reviewable in a pull request" had been a claim
  with no exhibit.
- `examples/walkthrough/` takes one small repository through four stages in the
  order a maintainer works: the audit with nothing run, a real `saggio measure`
  over a slice, the measurement folded in and a whole run projected from it, and
  what `diff` reports between the first and the third. The third stage is written
  by a committed, re-runnable script that calls the package's exported functions,
  so its numbers come from saggio's arithmetic rather than from whoever typed the
  file, and a contract test checks the script still reproduces it.
- The gallery pages say what is wrong in their own files. Two false positives are
  named with the evidence line that produced them: a `model:` type annotation in
  Whisper's `decoding.py`, and FastAPI's `model_name = "Body_" + name`. So is the
  work-size precedence rule that made DINOv2 take its epoch count from an
  evaluation config rather than a training one.
- A model built from a clone now records `deployment.machine_provenance`, saying
  that the processor, the core count and the operating system are the auditing
  machine's and not where the code runs. Reading a model of a training framework
  and taking a laptop's figures for a cluster's would carry that mistake into
  every energy number under it.

### Projecting onto another accelerator is a bracket, and it reaches a cost

- The catalogue carries `memory_gb`, and a projection onto a board smaller than
  the one the measurement came from says so before the number is used: 80 GB of
  measured work does not fit on a 24 GB card, and an arithmetic answer for a run
  that would not start is worse than a warning. It is a warning rather than a
  refusal because nothing here knows how much of the board the run actually used.
  The Apple rows carry no `memory_gb` on purpose: their memory is unified with the
  host and chosen per machine, so it is a property of a laptop, not of a part.

- Two things limit a workload on an accelerator: arithmetic throughput and memory
  bandwidth. The projection used to know about the first only, which made it
  optimistic by construction. It now reads both, and the catalogue carries
  `memory_bandwidth_gbps` for every accelerator in it. Between an A100 and an H100
  the two ratios are 3.2 and 2.2; reporting the first alone understated the bill of
  a memory-bound run by a third.
- The result is a bracket. The point estimate is the compute ratio when the read
  established the work is compute-bound, the bandwidth ratio when it established
  the opposite, and the slower of the two when nothing established either, because
  the slower ratio is the longer run and the larger bill. Both ends are on the
  record under `bounds`. A part whose bandwidth the catalogue does not carry still
  projects, and says the figure is an upper bound on the speed-up rather than a
  bracket around it.
- The projection reaches energy, money and carbon on the target board instead of
  stopping at a duration, with every figure naming the projected numbers it came
  from rather than the local ones it did not. It states in the model that the
  country, the tariff, the grid intensity and the datacenter overhead are the ones
  stated for this deployment, because moving work to another accelerator usually
  means moving it somewhere else.
- Precision is now a catalogue question rather than a wall. Each precision names
  the column that quotes throughput for it, and a refusal says which column is
  missing for which part and how to add it. FP16 and BF16 share a column, and the
  projection says so instead of substituting one for the other in silence.
- Both reports show all of it. The HTML page had no projections section at all,
  while its translations already carried a heading for one, and the Markdown
  renderer knew only the shape a whole-run projection takes, so every projected
  cost was dropped without a word. Both now render the figures and the bracket.

### The whole tool is now run against repositories shaped like repositories

- A family of integration tests audits four repositories that look like real ones
  — a Python training project, a TypeScript service, a Go command-line tool, and a
  handbook that only talks about frameworks — each with a suite, a README naming
  technologies it does not use, and a vendored tree. The assertions are about the
  whole answer: what was found, and equally what was not.
- One of them audits this repository. It is the guard for the defect above, which
  a suite of five hundred passing unit tests did not catch, because none of them
  ran the tool against something shaped like code and read the reply.
- A Go repository's shape is asserted to come back `unknown` rather than guessed
  at, which is the answer the package exists to give.

### The suite is no longer mistaken for the workload

- A framework is now detected by a line that imports it, not by a file that
  contains its name. Auditing this repository used to report fourteen frameworks,
  from PyTorch to Spark, because its own detector table and its own fixtures spell
  those names out. It reports one now, and that one is a quoted program name in
  the detector table itself.
- The code that tests a repository is read apart from the code it runs. The
  workload's own files are read first and decide what the audit reports; frameworks
  only the suite imports are listed under `frameworks_in_suite_only`; a service or
  a model whose only evidence line is a test file carries a `caveat` saying so.
  The shape of the workload is no longer decided by a file that exists to test one.
- A work size stated in a test ranks below every size the workload states, and no
  longer counts as a disagreement with it. A suite says `max_iters = 100` so that
  a test finishes; that is not a contradiction of the real configuration, and
  reporting it as one buried the contradictions that matter.

### The accelerator is measured, not assumed

- Power now comes from two counters instead of one. Alongside the Intel package
  counter on Linux, the NVIDIA driver is asked what the board is drawing, without
  privileges, on Linux and on Windows alike: the accumulated energy counter where
  the board keeps one, otherwise the mean of readings taken every half second for
  the length of the run. On the workloads this package exists for, the board is
  most of the machine's draw, and a model reporting only the processor was wrong
  by a factor of several.
- A measurement now names which counters answered, in `power_sources`, and the
  scope sentence says what the figure leaves out: the processor when only the
  board answered, the board when only the processor did, and the rest of the
  machine in both cases. Two models measured on different boundaries can no
  longer be mistaken for two models of the same one.
- A board that answers `[N/A]` voids the query rather than contributing half a
  machine's power, a driver counter that went backwards yields nothing, and fewer
  than two readings is not a mean. In each case the figure stays `estimated` and
  says why.

### The documentation is checked as bilingual

- Every page written in both languages is now checked as a pair: both halves
  exist, each links to the other, and both show the same commands with the same
  flags. A page written once is listed with the reason it is written once, and a
  new page that is neither fails the build. The French half was quietly missing a
  `diff` invocation and carried a different retrieval date for the same catalogue
  row; both are fixed.

### Renamed to saggio

- The project, the package, the command and the import are all `saggio`, where
  they were `running-code-cost-helper` and the alias `rcch`. *Saggio* is Italian
  for the assay of a metal, for an essay, and for judicious; the README says why
  all three fit. Nothing had been published under the old name, so no release
  carries it and no import ever has to be kept working.
- The short alias is gone. It existed because the old name was long to type, and
  the new one is six letters.

### The report's pieces moved out of the package

- The HTML report's document shell is now a file, `reporting/report.html`, with
  named tokens the renderer fills, rather than an f-string inside `report/html.py`.
  The stylesheet, the script, the translations and the logo moved to `reporting/`
  beside it, so everything the report is made of is authored as the kind of file
  it is.
- `reporting/sync.py` copies them into `saggio/data/report/`,
  which is what the wheel ships, and `--check` reports drift without writing. A
  contract test runs it, so editing the packaged copy by mistake fails the build.
- A token the renderer does not fill now raises, because a report containing a
  literal `{{BODY}}` would be worse than a failure.
- Nothing changed in the rendered page: the same document comes out.
- A value the renderer substitutes is no longer scanned for tokens itself. The
  shell is filled in one pass, so a model whose notes contained `{{SCRIPT}}` can
  no longer have that text replaced by the report's own script.

### Prices, read rather than scraped

- `saggio audit --fetch-prices` looks up what the APIs a repository calls
  actually charge. Nothing parses a pricing page and nothing asks a language
  model what one says: a price read off a marketing page fails silently and
  wrongly, returning the struck-through old figure, the enterprise tier, or the
  cached-input rate instead of the input rate. Only sources published *as data*
  are read. Off by default, because it is the only part of an audit that reaches
  the network beyond a local model.
- A price is per model, not per vendor, so the static pass now finds the model
  identifiers the code names — `model="gpt-4o"` and its spellings — and quotes
  the line that names them. A model held in a variable is not guessed at, because
  knowing what it holds would mean running the program.
- A model is charged on several axes at once. `gpt-4o` publishes eight rates, and
  all of them are recorded, each as a quantity with its own unit, currency,
  status, source and date. A rate key this build has no readable name for keeps
  the source's own spelling rather than being silently renamed.
- The rate is what gets known; the usage does not. How many tokens one unit of
  work spends is not something reading a repository establishes, so it stays
  `TODO` and the model shows which half is missing.

### Provenance, beside the honesty status

- A quantity may carry `source_kind`: `stated`, `first-party`, or `aggregator`.
  The status could not express this — a vendor's own published price and a
  community transcription of it are both, correctly, `estimated` — and the
  difference is exactly the kind this package exists to make visible.
- `saggio diff` fails when a price's provenance weakens, the way it already fails
  when a status weakens. The same number from a worse citation is a regression.
- **Schema 2.1.** `source_kind` on a quantity and `models_called` at the top
  level, both optional and additive, so every 2.0 model validates unchanged.

### Fixed

- `saggio diff` crashed with a `TypeError` whenever a quantity gained or lost its
  number, which is the most ordinary change there is: audit a repository, get a
  `TODO`, measure it, and compare. A side with no number now reads as
  `no number`, in both directions, and the gate still fails the run that goes
  from a measurement back to an open field.
- A machine with an accelerator the catalogue cannot name no longer gets a power
  figure with the accelerator silently left out of it. Several hundred watts used
  to vanish from a sum that still called itself this machine's nameplate total;
  the figure is now a `TODO` naming the row to add.
- A slice run with the function-level profiler attached says so. `cProfile`
  charges per call, so a call-heavy workload can take close to twice as long
  under it, and that inflated wall time is what every energy, carbon and money
  figure downstream is multiplied by. The warning names `--no-profile`.
- A repository that states its size in several places, under several keys, no
  longer gets a conflict sentence claiming a figure "was used" when nothing read
  it. Only the key the read actually went with says so; the others say which
  figure was used instead.
- A test file inside `.venv`, `node_modules` or another vendored tree no longer
  counts as this repository having a test suite, which is what used to make the
  audit offer to run somebody else's tests.
- `total_money` no longer returns a `TODO` carrying a number, which the validator
  itself warned about. A sum missing a term is not the total, so the number is
  withdrawn and what the known terms came to is kept in the notes. **This changes
  a public contract:** callers reading `.value` off a partial total now read
  `None`.
- The validator reports a dimension declaration that collides with a built-in or
  with an earlier declaration. The registry has always dropped the colliding one;
  until now it did so without a word, leaving the model saying one thing and the
  tool reading another.

### Renamed

- The two environment variables kept the dead project's name. They are now
  `SAGGIO_COUNTRY` and `SAGGIO_MODEL`, where they were `RUNNING_CODE_COST_COUNTRY`
  and `RUNNING_CODE_COST_MODEL`. Nothing was published under the old name, so the
  old spellings are not kept working.
- The catalogue module pointed at a `saggio.catalog.contribute` that does not
  exist. It names `add_row` and `saggio catalog add`, which do.

### Documentation

- `docs/` holds a map of every document in the repository, in English and in
  French, and `docs/api.md`: the library reference, one row per name in
  `__all__`, written from the docstrings by `docs/sync_api.py`. A contract test
  runs `--check`, so the reference cannot drift from the package.
- The two environment variables are documented, in both cookbooks, alongside
  `OLLAMA_HOST`. They were part of the public surface and appeared in no
  document.
- The cookbooks say what the function-level profile costs, and name
  `--no-profile`.
- `saggio machine` is shown in both READMEs, which listed every other verb.
- The conda environment installed the package's dependencies but never the
  package, so `conda env create` left a reader with no `saggio` command. Two
  contract tests now watch that, and watch the `requirements*.txt` files against
  `pyproject.toml`.
- The English README showed the logo at its full 1254 pixels where the French one
  showed it at 120.

### Continuous integration

- The push trigger watched `main` while the repository's default branch is
  `master`, so no push ever ran the checks. It watches both.

## 1.0.0 — 2026-09-13

First release.

### The model

- **Schema 2.0.** A cost model is a YAML file where every number lives in a
  *quantity*: a value with its unit, its currency when it is money, its honesty
  status, its provenance, and the paths of the numbers it was derived from.
- **The weakest-link rule is general.** Because a quantity names its inputs in
  `derived_from`, the validator resolves those paths and applies the rule to
  whatever it finds. A dimension a project invented is checked exactly as
  carefully as carbon, with no change to this package.
- **Every number lives in a quantity.** The validator walks the whole file and
  reports any number outside one, except at a short list of structural paths the
  schema names. A block this build has never heard of cannot carry a figure past
  the honesty rules.
- **Dimensions are load-bearing.** Costs are keyed by dimension in a `costs`
  mapping, and a project declares its own dimensions at the top of the model. The
  validator, both reports, and the drift gate all read the registry.
- **Money says which money.** A value on a money dimension carries an ISO 4217
  currency, so a report never adds dollars to euros.

### Finding out what things cost

- `audit` reads a repository: languages, workload shape, frameworks, how much work
  a full run performs, and which paid APIs it calls, with the line that proves it.
- `audit --run` executes a capped slice of the real entry point after explicit,
  once-only consent, times it, reads the machine's power counter where the
  operating system offers one, and profiles where the time went.
- The slice's share of the whole run is read from the repository's own
  configuration, so the whole-run projection is arithmetic rather than a guess.
- When two files disagree about how big a run is, the audit reports the
  disagreement instead of settling it quietly.
- `--source-accelerator` states which machine a measurement stands for, which is
  what makes projecting from a laptop onto a datacenter accelerator possible at
  all.
- Machine-to-machine projection is precision-aware: it refuses a precision the
  catalogue does not quote throughput at, and says which one.
- A local model, through Ollama, is asked what shape the work is and nothing else.
  Anything numeric it returns is discarded before it reaches the model.

### The catalogues

- Hardware, grids, providers, instances, and services, as provenance-carrying YAML
  shipped in the wheel and extensible per user through an overlay.
- A row cannot be added without a `source_url` and a `retrieved_date`.
- Staleness matches the fact: tariffs and grid mixes expire in a month, datasheet
  wattages in a year, and a row that asserts no number never expires at all.
- `catalog freshness` exits non-zero when anything has gone out of date, so a
  scheduled job can ask the question.

### Reports

- Markdown for a pull request, and one self-contained HTML page for everyone else:
  offline, light and dark, English and French, with a panel that recomputes the
  model for a different country in the browser.
- The stylesheet, the script, and the translations are files, packaged with the
  wheel and read through `importlib.resources`.
- The derivation figure is drawn from the model's own `derived_from` edges, so it
  shows the arithmetic a model actually does.
- Word and PDF through `md2star`, as an optional extra.

### Keeping it honest

- `diff` fails on a cost that worsened past a threshold, on a status that weakened
  even when the number did not move, and on a quantity that disappeared.
- `validate` returns a verdict with a path and a sentence for every issue, and
  warnings never fail a model: a model that admits it is incomplete is being
  honest.

### Surfaces

- A library, and a command line that is a thin adapter over it. Every verb routes
  through a public function, so the command line can do nothing a library caller
  cannot.
- An agent skill under `skills/`.
