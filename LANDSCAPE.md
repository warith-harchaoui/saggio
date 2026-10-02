# Landscape

[🇫🇷 PAYSAGE.md](PAYSAGE.md) · 🇬🇧 English

Other tools in the "what does running this code cost" space, and where each of
them is the better choice. Ratings are ⭐ (1) to ⭐⭐⭐⭐⭐ (5), scored against
*this* tool's job: **a committed, reviewable, per-unit-of-work cost model across
several dimensions, where every number states how far it can be trusted**. A tool
built for a different job is not penalised for being good at that job instead; the
score says fit to this niche, nothing more.

Figures were checked on 2026-10-01. Projects move; if something here is out of
date, [say so](CONTRIBUTING.md).

## At a glance

| | Per-unit model | Provenance on every number | Multi-dimension | Committed artefact | Measures power | Estimates without running | Drift gate | Reports for people | Offline |
| --- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **saggio** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| CodeCarbon | ⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ | ⭐ | ⭐ | ⭐⭐⭐ | ⭐⭐⭐ |
| Green Algorithms calculator | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐ | ⭐ | ⭐⭐⭐⭐⭐ | ⭐ | ⭐⭐⭐ | ⭐ |
| Scaphandre | ⭐ | ⭐⭐ | ⭐ | ⭐ | ⭐⭐⭐⭐⭐ | ⭐ | ⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ |
| PowerAPI / pyJoules | ⭐⭐ | ⭐⭐ | ⭐ | ⭐ | ⭐⭐⭐⭐⭐ | ⭐ | ⭐ | ⭐ | ⭐⭐⭐⭐⭐ |
| Kepler | ⭐ | ⭐⭐ | ⭐⭐ | ⭐ | ⭐⭐⭐⭐ | ⭐⭐ | ⭐ | ⭐⭐ | ⭐⭐⭐⭐ |
| eco2AI | ⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐⭐ | ⭐ | ⭐ | ⭐⭐ | ⭐⭐⭐ |
| carbontracker | ⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐ | ⭐⭐ | ⭐⭐ |
| Cloud Carbon Footprint | ⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐ | ⭐ | ⭐⭐⭐ | ⭐ | ⭐⭐⭐⭐ | ⭐ |
| Infracost | ⭐⭐⭐ | ⭐⭐⭐ | ⭐ | ⭐⭐⭐ | ⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐ |
| OpenCost / Kubecost | ⭐⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐ | ⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ | ⭐ |
| Cloud billing consoles | ⭐ | ⭐⭐⭐⭐ | ⭐ | ⭐ | ⭐ | ⭐ | ⭐⭐ | ⭐⭐⭐⭐ | ⭐ |

## The map

The same table, drawn. [standpoint](https://github.com/warith-harchaoui/standpoint)
runs a principal component analysis over the nine ratings and lays every tool out
along the two directions they actually differ on, orienting the map so saggio sits
top-right. Two axes keep about 80% of what
separates these tools: 55% horizontally, 25% vertically. The axis names are the
machine's own reading of the loadings; what the loadings say is plainer: the
further **right**, the more a tool produces sourced, committed, per-unit answers;
the further **left**, the more it measures live power. The further **up**, the
more it runs on your own machine and reads it; the further **down**, the more it
is something you point at a bill or a form.

<p align="center">
  <img src="assets/landscape.png" alt="Positioning map of the twelve tools along two principal components, saggio in the top-right corner" width="720">
</p>

The distances are the table's, not an opinion: two tools sit together because
their rating rows are close. Regenerate after editing the table with
`standpoint <table> -r saggio --model qwen3:8b` and commit the refreshed
`assets/landscape.png` and `assets/landscape.svg`.

## The projects

### [CodeCarbon](https://codecarbon.io/)

The best known tool in the space, and the right first choice if what you want is a
line of Python that logs the emissions of a training run while it happens. It
tracks CPU, GPU, and memory through RAPL and `nvidia-smi`, looks up a regional grid
intensity, and writes a CSV.

Where it differs: CodeCarbon measures an *episode*. It answers "what did this run
emit", not "what does one request cost", and its output is a log rather than a
reviewed artefact. Its sampling is coarse by design, and that has a measured
price: a 2026 study of RAPL-based tools polling at 1 kHz put CodeCarbon's own time
overhead between 5.4% and 46.8%, which is the argument for its default interval
rather than against the tool. It emits a number whether or not the inputs justify one, which
is the right call for telemetry and the wrong one for a figure somebody will quote
in a report. **Use CodeCarbon when you want passive measurement of training runs.
Use this when you want a per-unit figure you are prepared to defend.**

### [Green Algorithms](https://www.green-algorithms.org/)

The calculator behind the method this package implements, from the
[2021 paper](https://doi.org/10.1002/advs.202100707). Excellent for a one-off
estimate of a computation that has already happened or has not happened yet, with
no instrumentation at all. Well sourced and clearly explained.

Where it differs: it is a web form, so its answer lives in a browser tab rather
than in your repository, and it does not measure, compare versions, or read your
code. **Use the calculator for a quick estimate. Use this when the estimate needs
to live next to the code and be checked again next quarter.**

### [Scaphandre](https://github.com/hubblo-org/scaphandre) and [PowerAPI](https://powerapi.org/) / [pyJoules](https://github.com/powerapi-ng/pyJoules)

Serious power measurement. Scaphandre is an agent that exposes per-process power
to Prometheus; PowerAPI and pyJoules give you fine-grained RAPL readings from
Python. Both measure far better than this package does, which reads the package
counter around a bounded slice and nothing more.

Where they differ: they produce watts, not costs. There is no grid intensity, no
tariff, no unit of work, no provenance, and no report. **Use Scaphandre or
PowerAPI when you need real, continuous power measurement. Feed the result into a
model like this one when you need it to mean something to a reader.**

### [Kepler](https://sustainable-computing.io/)

Power and carbon attribution for Kubernetes workloads, from hardware counters,
exported to Prometheus. Strong at what it does. In 2026 it rewrote its collection
to read `/proc` and `/sys` instead of eBPF, dropping the `CAP_BPF` and
`CAP_SYSADMIN` it used to need — the same least-privilege direction this package
takes when it prints the remedy for a root-only counter rather than acquiring the
rights to read it.

Where it differs: it is cluster infrastructure. It answers "which pods are drawing
power right now", not "what does one unit of work cost", and it needs a cluster to
answer anything at all. **Use Kepler for a running fleet. Use this for a codebase.**

### [eco2AI](https://github.com/sb-ai-lab/Eco2AI) and [carbontracker](https://github.com/lfwa/carbontracker)

Both are decorator-style trackers for machine-learning training, close in spirit to
CodeCarbon. `carbontracker` additionally predicts the footprint of a full run from
its first epochs, which is the same idea as this package's whole-run projection.

Where they differ: same as CodeCarbon. Episode-shaped, log-shaped, and silent about
how well founded any particular figure is. **Use them for training telemetry.**

### [Cloud Carbon Footprint](https://www.cloudcarbonfootprint.org/)

Reads your cloud billing data and estimates emissions from it, with a good
dashboard and a published, defensible methodology.

Where it differs: it starts from the bill, so it can only describe what you have
already spent, at account granularity. It cannot tell you what one inference costs,
and it cannot tell you anything before you have run the thing. **Use it for
organisational reporting on cloud spend. Use this for engineering decisions about
a codebase.**

### [Infracost](https://www.infracost.io/)

The closest thing in spirit to this project, in a different domain. It reads
Terraform, estimates what the infrastructure will cost before it is applied, and
comments the difference on your pull request. The drift gate here is the same idea.

Where it differs: Infracost prices declared infrastructure, not executed code. It
is money-only, and it answers "what will this stack cost per month", not "what does
one unit of work cost across five dimensions". **Use Infracost for infrastructure
as code. The two answer different halves of the same question and sit happily side
by side.**

### [OpenCost](https://www.opencost.io/) and Kubecost

Real-time cost allocation for Kubernetes, by namespace, workload, and label. The
standard answer for "which team is spending what" on a cluster.

Where it differs: allocation of an incurred bill, not a model of a unit of work.
Money-first, with carbon added on. **Use OpenCost for chargeback.**

### Cloud billing consoles

AWS Cost Explorer, GCP Billing, Azure Cost Management. Authoritative on what you
were charged, which is exactly one dimension of one question, after the fact.
**Use them when the question is "why was the bill that size".**

## Where this one is weakest

Being honest about the gaps, since that is the whole premise of the tool.

- **Nothing is attributed to a process.** Every counter here measures the
  *machine*, and a baseline taken before the slice is the only thing separating
  the run from the browser beside it. Scaphandre, PowerAPI and Kepler model
  per-process and per-container draw; this package does not, and says so in the
  scope every reading carries. That is the gap that matters most on a shared box.
- **Two platforms, not three.** Linux and macOS, both reading real counters —
  powercap zones by name, `IOReport` on Apple Silicon, NVML and the `amdgpu` /
  `i915` / `xe` sysfs interfaces for the accelerator. Windows is out of scope
  rather than unfinished: it offers no unprivileged processor energy counter, no
  machine-wide processor-time total, and no POSIX resource accounting, so every
  figure there would be an estimate. Narrower than the tools above it in this
  table, and narrow on purpose.
- **A counter is not the wall.** Fans, storage, network and the power supply sit
  outside RAPL and NVML by construction, and the gap is not a constant that could
  be added back: measured against physical meters it is a slope of about 1.17,
  varying per node. Every figure here is the scope it names, never the machine.
- **No continuous monitoring.** One bounded slice, once. If you want a time series,
  this is the wrong shape of tool.
- **Embodied carbon is implemented and barely catalogued.** The arithmetic is
  there — the four terms of ISO/IEC 21031, amortised over calendar time — and so
  are seven footprints: three accelerators out of 25 rows and four processors out
  of 12. Everything else reports `TODO`. The lifetime is still yours to state,
  because how long a card stays in service is a fact about a fleet rather than
  about a part. See [`STANDARDS.md`](STANDARDS.md) for the table and the eight
  refusals.
- **The catalogues are small.** They cover the common accelerators and the larger
  grids. Beyond that you will meet a miss, and the tool will tell you which row to
  add.
- **Projection between machines is a datasheet ratio.** Peak throughput is not a
  benchmark. Real speedups are smaller, and the projection says so in its limits
  rather than in a footnote.

## Where it is worth choosing

When the number has to survive being questioned. When somebody is going to put a
per-request carbon figure in a customer-facing document, or a per-run cost in a
budget, and will be asked six months later where it came from. That is the case
these tools mostly do not serve: they produce numbers, and this one produces
numbers that come with their own audit trail and refuse to exist when they would
have to be invented.

It is also the only tool in this table that will *measure how the cost grows with
the size of the job*: three slices of different sizes, a fitted exponent, a
goodness of fit, and a refusal to project at all when the fit says the slices are
not measuring one consistent behaviour. Every other tool here projects by the
ratio of sizes, or does not project.
