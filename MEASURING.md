# Measuring

[🇫🇷 MESURER.md](MESURER.md) · 🇬🇧 English

A wattage taken from a datasheet is a guess about a chip. A wattage taken from a
counter is a fact about a run. This page is about the counters: which ones exist,
which ones this machine will let *you* read, what each of them actually covers,
and what happens to the number afterwards.

It exists because "could not measure power" is not an answer. A laptop with no
counter, a server whose counter is closed to everyone but root, a container that
cannot see `/sys`, and a chip nobody has taught this package to read are four
different situations with four different remedies, and only one of them is a
question for the reader.

## Contents

- [Ask the machine first](#ask-the-machine-first)
- [What answers, by platform](#what-answers-by-platform)
- [The four states](#the-four-states)
- [The rule about privileges](#the-rule-about-privileges)
- [What each figure leaves out](#what-each-figure-leaves-out)
- [From a counter to a cost](#from-a-counter-to-a-cost)
- [From this machine to another](#from-this-machine-to-another)
- [Checking it yourself](#checking-it-yourself)
- [Sources](#sources)

## Ask the machine first

```bash
saggio power
```

One block per interface, each in one of four states, each saying what it covers
and why it is in that state. Where something can be done about it, the command
that would do it is printed — and not run. See
[EXAMPLES.md](EXAMPLES.md#what-this-machine-will-let-you-read) for the output and
what to make of it.

To watch the counters work before a run depends on them:

```bash
saggio power --seconds 2
```

That measures the *machine*, not your program. On a busy laptop the figure is
mostly other people's work, which is the first thing worth knowing about a
machine-wide counter.

## What answers, by platform

| Platform | Interface | Covers | Privilege | How it is read |
|---|---|---|---|---|
| Linux | [powercap / RAPL](https://docs.kernel.org/power/powercap/powercap.html) | processor packages, the `psys` zone where present, and the memory zone beside them | **root by default since 5.10** | accumulating `energy_uj`, one difference per run |
| Linux | [`amdgpu` hwmon](https://docs.kernel.org/gpu/amdgpu/thermal.html) | the graphics board | none | `power1_average` in µW, sampled across the run |
| Linux | [`i915`](https://www.kernel.org/doc/html/latest/gpu/i915.html) / [`xe` hwmon](https://github.com/torvalds/linux/blob/master/Documentation/ABI/testing/sysfs-driver-intel-xe-hwmon) | the graphics board | none | accumulating `energy1_input` in µJ |
| Linux, Windows | [NVIDIA driver](https://developer.nvidia.com/management-library-nvml), through [`nvidia-smi`](https://docs.nvidia.com/deploy/nvidia-smi/index.html) | the whole accelerator board | none | accumulated energy where the board keeps it, otherwise sampled board power |
| macOS, Apple Silicon | `IOReport`, the library behind `powermetrics` | processor cores, graphics cores, neural engine, memory | **none** | monotonic per-subsystem counters, one difference per run |
| macOS | `powermetrics` | the same subsystems | root | not used by this package |
| Windows | [Energy Meter Interface](https://learn.microsoft.com/en-us/windows-hardware/drivers/powermeter/energy-meter-interface) | whatever a vendor chose to meter | a driver | not used by this package |
| Any server | IPMI / DCMI / [Redfish](https://www.dmtf.org/standards/redfish) | the whole node, fans and power supply losses included | controller credentials | not used by this package |

Two entries in that table deserve a sentence each.

**Apple Silicon.** For most of this package's history a Mac measured nothing,
and the stated reason was that macOS publishes power only through
`powermetrics`, which needs a password. The first half was wrong. The counters
`powermetrics` prints come from `IOReport`, which answers an ordinary user, and
that is what [`saggio/analyze/apple.py`](saggio/analyze/apple.py) reads. Apple
documents neither the library nor the channel names; the mapping used here was
established by reading the channels on real machines, in the way
[macmon](https://github.com/vladkens/macmon) and its relatives do, and a chip
whose channels are not recognised measures nothing rather than something
invented.

**The memory zone.** On Linux, `dram` is a *subzone* of a package in the sysfs
tree, but its energy is **not** inside that package's figure. Reading zones by
the name each gives itself, rather than by the shape of its directory, is what
makes that difference visible — and it means a machine that publishes the zone
now reports memory it had been leaving out. On Apple Silicon the same figure
comes from the `DRAM0` channel. Where either answers, the measured memory
replaces the term [Green Algorithms](https://doi.org/10.1002/advs.202100707)
estimates from installed capacity.

## The four states

| State | What it means | Is it your decision? |
|---|---|---|
| `reads` | The counter answers you, now, with nothing asked for. | No, it already works. |
| `blocked` | The counter is on this machine and closed to *you*. | **Yes.** This is the only one with a remedy. |
| `root-only` | It exists only behind administrator rights, and this package will not reach for it. | No, by design. |
| `absent` | There is nothing here to read. | No, it is a property of the machine. |

`absent` is not a failure. A virtual machine whose host does not pass the
counters through, an ARM board with no powercap tree, a container without
`/sys/class/powercap` mounted: all of them are honest `absent`, and the cost
model falls back to an estimate labelled as one. A weaker number, not a wrong
one.

## The rule about privileges

**Nothing in this package escalates.** No `sudo`, no password prompt, no quiet
fall-back to a tool that would ask for one. A measurement tool that acquires
privileges on its own behalf is a worse problem than an estimated wattage.

That rule has teeth on Linux, where the processor's counter is `blocked` for
ordinary users on any kernel from 5.10 onwards. The kernel closed it on purpose:
sampled fast enough, `energy_uj` recovers what *other* processes are computing —
the [PLATYPUS attack](https://platypusattack.com/),
[CVE-2020-8694](https://nvd.nist.gov/vuln/detail/CVE-2020-8694). So `saggio
power` prints the remedy with that reason beside it, and stops:

```
to open it: Until the next reboot:  sudo chmod a+r /sys/class/powercap/*/energy_uj
    Across reboots, a udev rule that touches the energy files and nothing else:
      SUBSYSTEM=="powercap", ACTION=="add", RUN+="/bin/chmod a+r /sys%p/energy_uj"
    in /etc/udev/rules.d/99-saggio-rapl.rules.
```

Read-only, and only the energy files: the power limits beside them stay shut, so
nothing here lets a reader throttle or overheat the machine. Whether to reopen a
published side channel on a machine you may share with other people is a
judgement about who those people are, and it stays yours.

On a shared cluster the better answer is usually not to open anything. Your
operator already meters whole nodes through the baseboard controller, and a
figure from there covers the fans and the power supply's losses, which no
counter inside the chip ever will. A cost model can carry that figure as a
`measured` quantity with its own source; see
[EXAMPLES.md](EXAMPLES.md#putting-the-measurement-into-the-model).

## What each figure leaves out

Every reading this package produces says what it covers, in the model and in the
report. The boundaries are worth stating once, plainly:

- **RAPL package** covers cores and uncore. Not the memory unless the `dram`
  zone answered too, not a discrete accelerator, not storage, not the fans, not
  the power supply's own losses.
- **`psys`**, where a machine publishes it, covers the whole system-on-chip, and
  already contains the packages — so it is used *instead of* them, never added
  to them.
- **Apple's counters** cover the processor cores, graphics cores, neural engine
  and memory. Not the display, which on a laptop is a large omission.
- **An accelerator counter** covers the board, which is the right boundary for
  the board and no boundary at all for the machine it sits in.
- **None of them** are a meter on the power rail. RAPL is a model inside the
  chip on every part that is not a Haswell server chip with on-board regulation,
  and Apple says the same of its own, adding that they are not a basis for
  comparing one machine against another. Within one machine, across one run,
  against that machine's own idle, they are exactly the right instrument, and
  that is all this package asks of them.
- **A counter that passed its ceiling** once during a long run is unwrapped from
  its published range, and the figure carries the wattage above which that
  recovery would have been wrong. A counter that was *reset* rather than wrapped
  is refused outright.

## From a counter to a cost

A measured average power is the first link in a chain, and the rest of the chain
is [Green Algorithms](https://doi.org/10.1002/advs.202100707), written out in
[`skills/saggio/references/green-algorithms.md`](skills/saggio/references/green-algorithms.md):
runtime × power × datacentre overhead gives energy, energy × grid intensity
gives carbon, and every step names the numbers it came from.

The measurement changes the *status* of what follows, not only its value. Measure
the runtime and the energy becomes `measured` on its own; leave the country
unstated and the carbon stays open, because nobody knows it yet. The
[weakest-link rule](skills/saggio/references/honesty-taxonomy.md) does the rest:
a derived value may never claim to be better founded than the worst of its
inputs.

This is also the shape the [Software Carbon Intensity
specification](https://sci.greensoftware.foundation/) asks for — ISO/IEC
21031:2024, and [SCI for AI](https://greensoftware.foundation/standards/sci-ai/)
above it: emissions per functional unit of work rather than a total, with the
boundary disclosed. A saggio model is per unit of work by construction, and what
it does *not* yet carry is the embodied term — the manufacturing of the hardware,
which [Boavizta](https://boavizta.org/en) models bottom-up and
[EcoLogits](https://ecologits.ai/) uses for inference. That absence is an open
figure in this package, not a zero.

## From this machine to another

A measurement is about the machine it was taken on. Two projections turn it into
something else, and both say what they assumed:

- **To a whole run**, from a slice: division by the fraction the slice covered,
  which is read from your own configuration rather than guessed. Defensible while
  the work is uniform, and the assumption is written into the model.
- **To another accelerator**: not a swap of wattages. A faster chip finishes
  sooner, so it draws more power for less time. The projection scales runtime by
  the ratio of peak throughputs *at the precision the work runs in*, and reports
  a **bracket** rather than a number, because arithmetic throughput and memory
  bandwidth give different ratios — 3.2 and 2.2 between an A100 and an H100 — and
  a real run lands between them. It refuses outright when the catalogue has no
  throughput figure for that precision.

Peak throughput is a datasheet figure, not a benchmark. A real run reaches a
fraction of it, and the fraction differs by chip; a workload bound by storage, by
the data loader, or by the host processor will gain from neither ratio. The
bracket says so, and so does the report. See
[EXAMPLES.md](EXAMPLES.md#projecting-onto-other-hardware).

## Checking it yourself

The point of a measurement nobody can check is hard to state. So:

```bash
saggio power --json
```

prints every interface, every state, and the exact filesystem paths that would be
read, so a figure can be reproduced by hand — `cat` the counter, wait, `cat` it
again, divide. On macOS, `sudo powermetrics --samplers cpu_power -n 1` is the
comparison Apple ships; this package will not run it for you, and the numbers
should agree.

If a machine's counters are not recognised — a new Apple chip renaming a channel,
a driver publishing an unfamiliar unit — it measures nothing and says so. Sending
the channel names is enough to add the part; see
[CONTRIBUTING.md](CONTRIBUTING.md).

## Sources

**Kernel and driver interfaces**

- [Power Capping Framework](https://docs.kernel.org/power/powercap/powercap.html) — the Linux powercap ABI, zones and `energy_uj`.
- [Reading RAPL energy measurements from Linux](https://web.eece.maine.edu/~vweaver/projects/rapl/) — Vince Weaver's reference on domains, ranges, and what RAPL actually measures.
- [GPU Power/Thermal Controls and Monitoring](https://docs.kernel.org/gpu/amdgpu/thermal.html) — `amdgpu` hwmon attributes.
- [`sysfs-driver-intel-xe-hwmon`](https://github.com/torvalds/linux/blob/master/Documentation/ABI/testing/sysfs-driver-intel-xe-hwmon) — Intel's `energy1_input`, in microjoules.
- [hwmon sysfs interface](https://www.kernel.org/doc/html/latest/hwmon/sysfs-interface.html) — units and naming for both of the above.
- [NVIDIA Management Library](https://developer.nvidia.com/management-library-nvml) and [`nvidia-smi`](https://docs.nvidia.com/deploy/nvidia-smi/index.html).
- [Energy Meter Interface](https://learn.microsoft.com/en-us/windows-hardware/drivers/powermeter/energy-meter-interface) — what Windows offers, and to whom.
- [Redfish](https://www.dmtf.org/standards/redfish) — the standard way a server reports its own whole-node draw.

**Why the Linux counter is shut**

- [PLATYPUS](https://platypusattack.com/) — the attack that closed it.
- [CVE-2020-8694](https://nvd.nist.gov/vuln/detail/CVE-2020-8694) — the entry, and the kernel's response.

**Turning energy into cost**

- Lannelongue, Grealey & Inouye, *Green Algorithms: Quantifying the Carbon Footprint of Computation*, [doi:10.1002/advs.202100707](https://doi.org/10.1002/advs.202100707) — the arithmetic this package uses, extracted in [`green-algorithms.md`](skills/saggio/references/green-algorithms.md).
- [Software Carbon Intensity](https://sci.greensoftware.foundation/) (ISO/IEC 21031:2024) and [SCI for AI](https://greensoftware.foundation/standards/sci-ai/) — emissions per functional unit, and what a disclosure has to say.
- [Boavizta](https://boavizta.org/en) and [EcoLogits](https://ecologits.ai/) — the embodied side, which this package leaves open rather than zero.
- [Kepler](https://sustainable-computing.io/) — attributing a node's energy to what ran on it, which is the problem beyond this page.

---

[🇫🇷 MESURER.md](MESURER.md) · [README.md](README.md) · [EXAMPLES.md](EXAMPLES.md) · [LANDSCAPE.md](LANDSCAPE.md)
