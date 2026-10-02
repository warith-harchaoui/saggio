# Changelog

This project follows [semantic versioning](https://semver.org/). The cost-model
schema is versioned separately, in its own `schema_version` field: within a major
line it only grows, so a model written today keeps validating against every later
release of that line.

## 1.3.0 — 2026-10-02

### The grid catalogue is one vintage, from one source

- The 38 country intensities are refreshed from the Ember API, data year 2025.
  Each row now carries `carbon_source_url`, `carbon_retrieved_date` and
  `carbon_data_year` of its own, rather than inheriting the row's: the carbon
  figure and the tariff beside it do not come from the same place and do not
  move together.
- Checking the old figures against Ember's full series first — year by year,
  to confirm the catalogue was merely a year behind — showed it was not. The
  committed values best-matched Ember years scattered from 2000 to 2025, and
  **eight countries matched no Ember year within 8%**. Sweden sat at 13
  gCO2e/kWh where the lowest figure Ember has ever published for it is 34.91.
  Every row cited Ember. A `source_url` that does not contain the number beside
  it is the exact failure this package exists to object to.
- `DeploymentContext.grid_intensity` reads the carbon provenance rather than the
  row's. Without that it reported an API figure read today under the URL and date
  of a web page read last month — a false provenance introduced by the very
  commit that fixed the numbers.
- `saggio catalog refresh grid` sent `is_aggregate_series`, which is not a
  parameter this API has; the published schema spells it `is_aggregate_entity`.
  Unknown query parameters are ignored rather than refused, so the filter the
  code believed it was setting was never set.
- The two walkthrough models had a carbon figure derived from the old intensity.
  The arithmetic check added in this same release caught both, by name and with
  the right answer beside them, which is what it was written for.

### The power meter is a package, and the last long file is gone

- `power.py` was 1,227 lines: 28 constants and 20 symbols covering four
  different hardware interfaces. Now `saggio/analyze/power/`, nine modules,
  split by **where the energy comes from** rather than by what kind of thing
  each symbol is — which is the structure the problem actually has, since each
  interface has its own units, its own failure mode and its own scope:
  `tables`, `sysfs`, `rapl`, `accelerator`, `graphics`, `soc`, `reading`,
  `meter`.
- **Behaviour identical**, against a baseline captured before the first cut and
  verified first by halving a figure on purpose and confirming it noticed.
- The monkeypatch lesson a third time, and costlier here: **28 patch targets**
  across three test files, all naming `saggio.analyze.power.<x>` for names that
  now live in submodules. A patch on the package's re-export does not reach the
  module that imported the name. Among them one I wrote myself last week.
- The three files the assessment named are done: `auditor.py` 1,319 → 9 modules,
  `static.py` 1,649 → 10, `power.py` 1,227 → 9. All three were checked the same
  way, and **the method is worth more than the result**: capture what the thing
  does before touching it, prove the capture can fail, then split on the syntax
  tree rather than by hand.
- **The commit message for this one overclaimed**, and the correction belongs
  here rather than in a force-push. It said no file in the package was over a
  thousand lines. Five are: `refresh.py` 1,213, `html.py` 1,168,
  `commands.py` 1,151, `run.py` 1,117, `markdown.py` 1,001.
- Worse, **`refresh.py` grew from 424 lines to 1,213 today, by this hand** —
  the price refresh, the timezone check and the embodied-carbon reader, each
  added without looking at what the file was becoming. Three long files were
  split while a fourth was grown into the longest one in the package. It is on
  the list now, measured rather than remembered.

### Two more examples, and the two defects they found

- The gallery gains **detectron2**, the first example read as **inference** —
  the archetype that matters most to anyone pricing a request, and the one the
  six before it never exercised — and **xberg** (formerly Kreuzberg), a
  document-intelligence engine whose core is Rust: 2,278 Rust files, 435 Java,
  400 C#, 391 Kotlin and 143 Python. **Every other example here is Python**, so
  this is the breadth claim demonstrated on a repository that could have
  embarrassed it.
- **The suite-detection rule was Python- and JavaScript-shaped**: `tests/`,
  `test_*.py`, `*.test.ts`. Rust puts its tests in a *file* called `tests.rs`,
  so ten model identifiers named `test-model` and `mock-model` arrived with no
  caveat at all. It now recognises a suite in whatever language it is written —
  and refuses `latest.rs`, `contest.py` and `protest.go`, which a looser first
  attempt swept up before a probe caught it.
- **An example is not the workload either.** The package already refused to take
  a training run's length from an evaluation config; the same reasoning had never
  been applied to what the code *calls*. A model named in `examples/` or
  `benchmarks/` now carries a caveat saying so. Auditing vLLM is what showed it:
  333 model identifiers across 150 files, 127 of them from those directories.
  The signal went from 152 uncaveated identifiers to 17.
- vLLM itself is **not shipped**: its model is 162 KB, 95% of it a list nobody
  will read. The finding is in the gallery, the file is not, and the page says
  so rather than letting the omission pass.
- **One defect named rather than hidden**: Rust keeps unit tests inside the file
  they test, in a `#[cfg(test)] mod tests` block. File-level detection cannot see
  inside a file, so fixtures still appear beside the genuine `openai/gpt-4o` and
  `anthropic/claude-sonnet-4-20250514` that xberg really calls.

### The static reader is a package too

- `static.py` was 1,649 lines — the ledger said 1,584, which was another stale
  figure — across 27 symbols and **26 constants scattered through the file**,
  some above the first function and some between the last two. That scattering
  was most of the problem: a reader asking "why did it decide that" is nearly
  always asking about a table, and had to go hunting.
- Now `saggio/analyze/static/`, ten modules, the largest 350: `tables`,
  `walking`, `findings`, `languages`, `archetype`, `worksize`, `calls`,
  `running`, `read`. Every import path resolves as before.
- The tables live together and apart from the code that reads with them.
  `FRAMEWORK_PATTERNS` is built rather than written, so the small function that
  builds it sits there too — it makes a table rather than reading one.
- **Verified against a behaviour baseline**, and the baseline was itself
  verified: deliberately breaking a detector changed it, which is what proves a
  witness is not blind. After the split, the only difference across fifteen
  probes was this repository's own Python file count, 94 → 103 — the ten modules
  added less the one removed, which is the reader correctly reporting a changed
  repository rather than a changed reader.
- The first extraction pass cut the header at the first `def` and lost every
  constant below it. Redone over the **syntax tree**, which finds a top-level
  assignment wherever it sits, with an assertion that nothing was left unplaced.
- Four more doctests made self-contained, the same lesson as the auditor: an
  example that leans on its module's namespace breaks the moment the module
  moves.

### The freshness job gives notice before the deadline, not after

- The scheduled job ran `saggio catalog freshness` bare. That prints "every
  catalogue row is within its refresh window" every Monday until the week the
  rows expire, and only then fails — **notice after the deadline**, which is no
  notice at all for a figure somebody is about to quote. It now passes
  `--within 21`: four Mondays of warning, each carrying the refresh command
  already printed beside it.
- It still does **not** fail on a merely-expiring row, and that was left alone
  deliberately. A gate that turns red overnight gets the date bumped in a hurry
  rather than the source re-read, which is the one outcome the whole mechanism
  exists to prevent. Expiring is a reminder; stale is a defect; collapsing
  either into the other breaks it in a different direction.
- Two contract tests hold both halves, and removing the flag or shortening it
  below two weekly runs fails the one named for it.

### The auditor is a package, not a file with seven jobs

- `auditor.py` was 1,319 lines carrying seven unrelated concerns, which made the
  one question a reader arrives with — where does *this* number come from —
  answerable only by reading the whole thing. It is now
  `saggio/auditor/`, nine modules, the largest 331 lines: `paths`, `options`,
  `naming`, `blocks`, `assumptions`, `measuring`, `projections`, `build`.
- **The public surface did not move.** `from saggio.auditor import audit,
  AuditOptions, AuditResult, audit_git_url, repository_name` resolves exactly as
  before, because the file became a package of the same name.
- **The output did not move either**, and that was checked rather than assumed: a
  baseline of three audits, the repository-naming helper and the command
  renderer was captured before the first line was cut and compared after every
  step. Byte-for-byte identical throughout.
- The dotted-path constants lost their leading underscore. A name private to one
  module was the right spelling while there was one module; now that six of them
  share these paths, the underscore would describe the old shape.
- Two things a split breaks that a test suite catches and a reader would not:
  **private imports** (`_projections` moved to the module that owns it) and
  **monkeypatch targets** (25 of them, now naming the module that *looks the name
  up* rather than the one that defines it, which is where patching has to
  happen once a name is imported).
- And one that `ruff` cannot catch: `--fix` removed imports used only by
  **doctests**, because F401 reads code and an example in a docstring is not
  code until it runs. Six examples were made self-contained rather than left
  leaning on their module's namespace — which is what made them fragile.
- `audit` itself is still long, and deliberately: it is a linear recipe, and
  breaking a recipe into steps called once each makes a reader jump about to
  recover an order they were already being told. The package docstring says so.
- `examples/saggio.yaml` is regenerated. Its embodied-carbon note still said a
  processor's footprint "is not in the catalogue yet", which stopped being true
  with the previous release.

### The gallery compares, without pretending the numbers do

- The gallery showed one tool's output on six repositories and said nothing
  about the alternatives, which for a lot of jobs are the better answer. It now
  carries **the same work, through the other tools**: five families — episode
  trackers, power daemons, calculators, spend tools, and this one — on the
  artefact each produces, the unit its answer is per, and **what each does when
  an input is missing**.
- That last column is the comparison. saggio writes `TODO`; episode trackers
  emit a number anyway; a daemon's series has a gap; a calculator's field is
  required; a spend tool simply has no line. **None of those is a flaw** — a
  daemon that stopped the world to ask a question would be a bad daemon — and
  the page says so, because the column is the reason the tools are not
  interchangeable rather than a scoreboard.
- What it refuses to do is rank them by output. A CodeCarbon figure for a
  training run and a saggio figure for one inference are not two measurements of
  one thing, any more than the gallery's own six models compare with each other.
- A hand-authored SVG carries the comparison; the table beside it carries the
  named tools and their links, so the two do different jobs rather than saying
  the same thing twice. Both language versions come out of one generator,
  `assets/make_gallery_figure.py`, because two hand-edited SVGs drift the first
  time a row changes and a figure that disagrees with its translation leaves
  nobody able to tell which is right.
- Four contract tests hold it: every tool named in the comparison must be one
  `LANDSCAPE.md` actually researched, the caveat about incomparable numbers may
  not be dropped, each language must show its own figure, and a figure edited by
  hand instead of regenerated fails by name.
- `LANDSCAPE.md` / `PAYSAGE.md` said **"No embodied carbon"**, which stopped
  being true some releases ago. A stale self-assessment is worse than none when
  it is the page a comparison is drawn from, so it now states what is
  implemented and how thinly it is catalogued.

### The embodied-carbon promise meets its catalogue

- The README offered the four terms of ISO/IEC 21031. The arithmetic had them;
  the catalogue had **three footprints across 25 accelerator rows and none at
  all across 12 processors**, so most real machines got a `TODO`. Both halves
  are addressed: the catalogue is extended where it honestly can be, and the
  promise now states its own coverage rather than implying more.
- `saggio catalog refresh hardware --column embodied` reads processor footprints
  from [Boavizta](https://doc.api.boavizta.org/Explanations/components/cpu/), an
  open keyless API over a crowd-sourced database of die sizes. **Four of twelve**
  processors are accepted; the other eight are refused by name, with the reason.
- Two guards, both earned by probing the source rather than trusting it:
  - It answers about a chip it was not asked about. Asked for an **Apple M4 Max
    it returns an Apple M1 Max** — four generations earlier — and says so
    nowhere in the reply. Three Apple rows would have carried an M1 Max figure.
  - It answers for a die size it does not have by filling in a family average.
    Asked about a chip called `banana chip 9000` it returns **19.0 kgCO2e**
    without a word. The footprint is a function of the die, so a default die is
    a default footprint wearing the chip's name. Two Xeon rows would have
    carried one.
- The accelerator half of that API is **refused outright and in words**: asked
  for any GPU by name it answers 575.1 kgCO2e — the same number for a GTX 1080
  Ti, an A100 and an H100, because it holds one archetype called "Large GPU".
  That is three and a half times NVIDIA's own verified figure for an H100.
- The auditor falls back from the accelerator to the processor. Its old note
  said a processor's footprint "is not in the catalogue yet", which stopped
  being true the day four of them were: a machine whose only chip is known would
  have gone on reporting `TODO` while the figure sat in the file beside it. A
  generic default chip still reports `TODO`, because a default's footprint is a
  default too.
- `STANDARDS.md` / `NORMES.md` carry the seven figures in one table, keep the
  two strengths of claim apart rather than averaging them into one word, and
  list the eight refusals with their reasons. The README says the catalogue is
  incomplete and why, instead of leaving it to be discovered.

### Every column of a grid row says where it came from, and runs on its own clock

- The same defect a third time. Carbon cited Ember, which was right. The tariff
  cited Ember, which publishes no tariff. The **timezone list cited Ember too**,
  which publishes no timezones either. The row-level `source_url` stood for
  whatever nobody had looked at, and it is now gone: there is no row-level
  source left, because covering nothing in particular is exactly how it lied.
- `saggio catalog refresh grid --column timezones` checks the names against the
  [IANA Time Zone Database](https://data.iana.org/time-zones/tzdb/zone1970.tab)
  and stamps the release each row matched — `timezones_tzdb_version: "2026e"`.
  It **verifies rather than replaces**: the database says which zones exist, not
  which a country uses in the way this catalogue means it, and the catalogue
  deliberately carries compatibility names like `Europe/Kiev` and
  `Asia/Calcutta` because those are what a real machine reports. All 64 zones on
  file check out. A zone published under no name fails the command rather than
  being corrected. `--column all` does the three in one pass.
- `COLUMN_STALE_AFTER_DAYS` gives a column its own window where it differs from
  its row's kind. This is the reason `STALE_AFTER_DAYS` was a table in the first
  place, applied one level down: a grid row now carries three columns from three
  sources at three speeds. Under one clock the row went stale monthly on account
  of a timezone list nobody needed to re-read, which teaches a maintainer to
  re-date rather than re-read.
- Three provenance contracts generalised from one `source_url` per row to one
  per column, which is a stronger claim than they made before: every number has
  a source, not every row.

### Continuous integration that can go green

- The workflow had not passed in **twenty-five consecutive runs**. A gate that is
  always red is not a gate: nobody reads it, nobody fixes it, and the one time it
  catches something real it looks like the twenty-four times it did not.
- Four jobs become one: Linux, Python 3.10 — the floor of `requires-python`, so
  the version most likely to reject something. The whole suite, `ruff check` and
  `ruff format --check` all pass there, verified before pushing rather than
  discovered in a log.
- What that costs is in the workflow's own header rather than left to be noticed:
  macOS is no longer exercised in CI, and only the floor of the version range is
  run. The contract test that pinned the matrix to `SUPPORTED_PLATFORMS` now
  asserts the invariant that caught the real bug — no job may run somewhere the
  package refuses to import — instead of a matrix shape that also quietly claimed
  CI covered every platform.
- The formatting drift that was failing it: `ruff format` was never in the local
  loop, only `ruff check`. Four files were unformatted.

### The tariff column gets a source that publishes tariffs

- Every row cited one URL for the whole row. The carbon intensity came from
  Ember; the tariff beside it did not and could not — that page publishes
  generation, emissions, capacity and demand, and **no price at all**. Thirty-
  eight rows carried a `source_url` that did not contain the number next to it.
  The defect dates to the first commit and was invisible until splitting the
  carbon provenance out left the tariff alone with a citation that was never
  about it.
- `saggio catalog refresh grid --column price` re-reads the tariffs from
  [GlobalPetrolPrices](https://www.globalpetrolprices.com/electricity_prices/),
  which publishes a residential price per kilowatt-hour — power, distribution,
  transmission and all taxes — for every country in one table and one currency.
  `--column both` does the two in one pass.
- Each column now carries `*_source_url`, `*_retrieved_date`, and the period the
  figure describes: `carbon_data_year: 2025`, `price_collected: "Q3 2026"`. The
  day a number was read is not the period it covers.
- [Eurostat](https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/nrg_pc_204?format=JSON&lang=EN&nrg_cons=KWH2500-4999&tax=I_TAX&currency=EUR&unit=KWH&lastTimePeriod=1)
  is the more authoritative body for Europe and was read — as a **check**, not
  as the source. It publishes in euros and for Europe only, so taking it would
  have meant a second source for the exchange rate, a conversion going stale
  daily, and eighteen rows that could not be compared with the other twenty.
  Converted at the [ECB reference
  rate](https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml), the two
  agree to a median of 7% across the eighteen countries both cover and diverge
  by more than 15% for six — Finland, Romania, Poland, Norway, Sweden, Italy —
  which is a difference of method, not an error in either. All three URLs are in
  the source so the comparison can be run again.
- `DeploymentContext.electricity_price` reads the tariff's own provenance and
  names the collection period.
- Three contract tests now hold the line: every column cites a source of its own
  and says when it was read; the two columns may never share a URL, since that
  would mean one of them is vouched for by a page that does not publish it; and
  the URLs on file are the ones the refresh would write. Putting the original
  defect back makes the first of them fail by name.
- The two walkthrough models had a money figure derived from the old tariff.
  The arithmetic check caught both, with the right answer beside them.

### Tests stop restating what the package refreshes

- Seven tests failed on the refresh, every one because it had copied a catalogue
  number into an assertion instead of reading it. A package whose argument is
  that it refreshes its own facts cannot have a suite that breaks when it does:
  the refresh read as a regression.
- Each now asserts what its own name claims. The audit and context tests compare
  against the catalogue; the Norway test checks that Norway resolves at all,
  which is what guards against YAML reading `NO` as false; the JSON-report test
  stubs a value far from anything the catalogue could hold, rather than a
  plausible one that passed only until the catalogue caught up with it.
- Three doctests now show the unit, the status and that a `source_url` came with
  the figure, rather than the figure. An example restating a refreshable number
  is wrong the first time somebody runs the refresh command this package ships.

### A derivation is checked, not just declared

- `derived_from` bought a status check and nothing else. A value could name its
  inputs correctly and state a number four orders of magnitude from what they
  multiply to, and validate. That was the worst shape the gap could take: a
  wrong number carrying a correct derivation reads as *better* founded than
  anything else on the page.
- `saggio.model.derivation` recomputes the value from its inputs, by **units**
  rather than by field name. Every unit is parsed into a scale and a set of base
  dimensions — joules, seconds, grams of CO₂ equivalent, litres, bytes, and
  whatever currency a model names. `W` is `J/s`, `kWh` is 3 600 000 joules,
  `gCO2e/kWh` is grams over joules with the factor folded in. Nothing is a
  special case: seconds times watts come out as energy because a watt *is* a
  joule per second.
- The **product comes first**, and where it lands on the stated unit that is the
  reading: a derivation multiplies unless it cannot. Where the product misses,
  each input is tried as a divisor too, because a derivation may divide —
  amortising an embodied footprint over a lifetime is a division, and the model
  names the lifetime among its inputs just the same.
- Exactly one arrangement reaching the unit means the relationship is
  unambiguous, and more than 1% away is an **error**. Several arrangements mean
  the units cannot say which was meant, so no single answer is claimed — but a
  value matching **none** of them is still an error, because it is wrong under
  every reading. That is what closes the three-input case, where an embodied
  figure five orders of magnitude out passed with a perfectly correct list of
  inputs beside it.
- A unit no arrangement can produce — a duration times a plain number gives a
  duration, never a mass of carbon dioxide — is an **error** too, cheaper to be
  sure of, and decidable however many inputs there are.
- Where any unit involved is one the package does not know, the validator says
  **nothing**. Silence is the honest answer to "I cannot tell", here as
  everywhere else.
- It found a wrong number on its first run, inside a test fixture named
  `sound_model`: 0.05 kWh where 3600 s at 100 W is 0.1. All nine committed
  example models passed, before and after the rule was widened.

### `measured` has to say what measured it

- `estimated` must name a source; `measured`, the stronger status, asked for
  nothing. A value claiming it must now be derived, carry a note, or sit in a
  model with a `measurement` block.
- And a `measurement` block vouches only for **what a run can actually
  observe**: durations, energy, power and bytes. It does not produce a grid's
  carbon intensity or a cloud bill. Letting it vouch for every `measured` value
  in the file was the same mistake in a quieter place — a carbon figure marked
  `measured`, with nothing in the world that could have measured it, inheriting
  the standing of a stopwatch because the file happened to contain one. A value
  outside what a run observes now has to attribute itself; a cost read off an
  invoice is a real measurement, and saying so in `notes` is all the rule asks.
- A unit the package does not recognise gets the benefit of the doubt. Asserting
  that somebody's instrument cannot exist would be inventing a rule about their
  field.
- A **warning** throughout, not an error: somebody may genuinely have measured it
  with their own wattmeter, and refusing their model would be refusing the
  truth.

### Breaking

- `import saggio` raises on a platform that is not Linux or macOS. Windows is
  out of scope deliberately; see `MEASURING.md`.
- `saggio catalog freshness --json` returns `{"stale": …, "expiring": …}` rather
  than the bare stale mapping.

### The gallery demonstrates a measurement

- Counted before this change: **0 measured, 24 estimated, 144 TODO** across the
  six committed examples. The package's whole proposition is that `measured`
  means a counter said so, and the most visible artefact it ships demonstrated
  none of it.
- The walkthrough was re-run and now does. Its power comes off a counter rather
  than a datasheet, which the diff reports in the line worth reading twice:
  `assumptions.power_draw: 83.76 -> 31.1047 (-62.9%), estimated -> measured`.
  The nameplate was wrong by a factor of two and a half.
- With the power measured, `machine_energy` rises to `measured` on its own —
  both of its inputs are — while the **facility** energy stays `estimated`,
  because the datacenter overhead is still an assumption. The weakest-link rule
  computing itself, in four steps, in a committed file.
- A fifth stage, `5-run.yaml`: `saggio audit --run --scaling-steps 3` in one
  command, with a **measured scaling exponent of 0.687 at R² = 0.999**. It is
  also bad news about the measurement, which is the point — the exponent says
  the slice is mostly Python starting up, so a projection from it would
  overstate the run, and the tool says so rather than projecting anyway.
- The walkthrough leads the website's gallery grid, where the honesty figure now
  shows a green `measured` segment instead of six bars of estimate and TODO.
- The toy workload's `num_samples` goes from 5,000 to 400,000, with the reason
  in the file: at a thousandth of five thousand, three slices a factor of four
  apart round to two, and the workload was too small to demonstrate something
  the tool can do.

### One unambiguous script is an entry point

- `find_entrypoint` knew four names — `train.py`, `main.py`, `run.py`,
  `benchmark.py` — and returned nothing for a repository whose single script is
  called anything else. The walkthrough's own toy workload was one: a stated
  work size, one runnable file, and "there was nothing safe to run".
- It now falls back to the one Python file at the root that runs itself, when
  there is exactly one. Two is not unambiguous and still returns nothing: a
  slice of the wrong script measures the wrong thing, and the reader would have
  no way to tell from the number.

### The CI ran two jobs that could only fail

- The workflow matrix still listed `windows-latest` after Windows was excluded,
  and its header comment still said "the three operating systems this package
  claims to support". Since `import saggio` now raises there, both Windows jobs
  failed at collection. The sweep that excluded Windows searched `*.md`, `*.py`,
  `*.toml` and `*.yaml`; the workflow is `.yml`.
- Fixed, and pinned: a contract test maps `SUPPORTED_PLATFORMS` to the runners
  in the matrix and fails when they drift, and a second one refuses an excluded
  platform in any `os:` or `runs-on:` line. A list of supported platforms that
  lives in two files needs a test, not a convention.

### A catalogue can be re-read from the source it cites

- `saggio catalog refresh grid` asks Ember what each country's grid emitted and
  prints it against what the catalogue holds. **Read-only**: a command that
  rewrites thirty-eight sourced figures on a bare invocation is one somebody
  runs by accident, and the diff it leaves looks exactly like one a person
  checked. `--write PATH` is the deliberate second step.
- It needs a free Ember API key and **substitutes nothing**. Our World in Data
  publishes an Ember-derived series through a stable CSV with no key, and it is
  the wrong series: its own metadata calls it *lifecycle* carbon intensity while
  this column is *operating* emissions. Taking it would have changed what every
  committed model means, silently. The refusal names the shortcut and the
  reason, so the next person to look for it finds the reason first.
- It writes one column. The carbon intensity gets its own `carbon_source_url`,
  `carbon_retrieved_date` and `carbon_data_year`; the row's price and timezones
  came from elsewhere and keep the row's own provenance. The file is edited line
  by line rather than round-tripped through a YAML dumper, which would have lost
  the header, the grouping, and the comment explaining that an unquoted `NO`
  is the boolean false and takes Norway out of the catalogue.
- A country the source does not answer for is left alone and named. Nothing is
  interpolated, carried over, or averaged.
- **A row is now as fresh as its stalest number.** Rows carry more than one date
  since this and the embodied footprints landed, so `is_stale` and
  `expiring_report` take the oldest of every `*_retrieved_date` rather than only
  the row's own. That change immediately failed a test pinning freshness to a
  hard-coded day the catalogue had moved past; the test now measures from the
  day the newest row was read, which is true whenever it runs.
- Found by the test written to find it: five of the thirty-eight country keys
  had no ISO 3166-1 alpha-3 code on file and would have been silently
  un-refreshable.

### Windows is out of scope, definitively

- **The supported platforms are Linux and macOS**, stated in the packaging
  classifiers, in both READMEs, and in one constant,
  `saggio.analyze.capability.SUPPORTED_PLATFORMS`. `import saggio` on anything
  else raises an `ImportError` carrying the reason, rather than half-working or
  failing three imports deeper on a missing stdlib module.
- The reason, said once instead of four different ways: Windows publishes no
  vendor-neutral processor energy counter to an unprivileged process — the
  Energy Meter Interface exists only where a manufacturer implemented it and
  only through a driver, and `powercfg`'s per-application figures are a battery
  model rather than a counter — no machine-wide processor-time total this
  package can read, and no POSIX resource accounting for a child. Each alone
  would be survivable; together they mean every number this package exists to
  produce would be an estimate there.
- The accommodations go with it. `capability.probe()` loses its Windows branch
  and `_windows_interface()` is gone; `power.unavailable_reason()` loses its
  Windows case; `run.py` imports `resource` like any other stdlib module instead
  of guarding an import that could only fail on a platform now excluded.
- The documentation stops treating it as a gap. Windows leaves the table of
  interfaces in `MEASURING.md` / `MESURER.md` and becomes a statement of scope
  beneath it, and the "where this is weakest" list in `LANDSCAPE.md` /
  `PAYSAGE.md` now reads "two platforms, not three" — narrower than its
  neighbours, and narrow on purpose. The Energy Meter Interface stays in the
  sources, as the evidence for the exclusion rather than as a capability.

### The freshness gate gives notice before it fails

- `saggio catalog freshness --within DAYS` names the rows that are still inside
  their refresh window but near the end of it, and does **not** fail. Only a
  stale row still fails.
- The reason is the failure mode, not the feature: a gate that turns red
  overnight gets the date bumped in a hurry rather than the source re-read, and
  a re-dated number nobody looked at is exactly what this mechanism was built to
  stop. A week's notice is enough to go and read the source properly.
- Found by asking: the bundled grid rows were read on 2026-09-12 and country
  rows last a month, so all 38 of them expire on 2026-10-13. Nothing is stale
  today and nothing was going to say so until the day it broke.
- `--json` now returns `{"stale": …, "expiring": …}` rather than the bare stale
  mapping. A shape change for anything parsing it.

### A run is told apart from its machine two ways, not one

- Subtracting an idle baseline assumes the rest of the machine kept doing what
  it was doing. `saggio.analyze.cpu` asks the same question without that
  assumption: it reads the machine's own processor total before the slice and
  after — `/proc/stat` on Linux, the Mach call `host_processor_info` on macOS,
  both to an ordinary user — and the slice's share of that work attributes the
  measured draw instead of subtracting a floor from it. The method Kepler uses
  for pods and GreenAlgorithms4HPC reads from a scheduler.
- **A share of processor work may only price processor energy.** Where the
  machine publishes its subsystems apart, the processor's own figure is used and
  the model records what the attributed number covers. Where one figure covers
  an accelerator, there is nothing to apply the share to and none is offered: a
  run that keeps a GPU busy on almost no processor time would be attributed
  almost none of a draw that was mostly the GPU's.
- The two answers are reported together, and a warning fires when they disagree
  by more than half again, with both numbers in it. The useful output of two
  methods that disagree is the pair, not a pick.
- Refusals rather than plausible ratios: a window too short for the counter's
  resolution, a counter that went backwards, and — the one worth having — a run
  that reports more processor time than the whole machine did, which is refused
  rather than clamped to one, because clamping would turn a sign that a counter
  is wrong into a confident number.
- `PowerReading` now carries `by_domain`: watts per subsystem where the machine
  counts them apart. Apple Silicon has always counted the processor cores, the
  graphics cores, the neural engine and the memory separately, and this package
  was adding them up and throwing the split away.
- `power_by_domain()` draws that split in the HTML report — the only figure in a
  saggio report that is measured rather than modelled, each bar read off its own
  counter. The donut of estimated shares this replaces would have been easier to
  draw and would have been a picture of an assumption.

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
