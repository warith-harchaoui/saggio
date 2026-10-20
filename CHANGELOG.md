# Changelog

[🇫🇷 JOURNAL.md](JOURNAL.md) · 🇬🇧 English

This project follows [semantic versioning](https://semver.org/). The cost-model
schema is versioned separately, in its own `schema_version` field: within a major
line it only grows, so a model written today keeps validating against every later
release of that line.

## Unreleased

### Refreshing a catalogue, in the reader's language, and the two sentences that stay English

The four refresh modules and the verbs that print them — grid, hardware,
tariffs, timezones — held the last English prose outside the hardware half of
`extrapolate.py` and the API's route descriptions. Fifty-two keys: twenty-one
for what the sources answer and refuse, thirty-one for what the command prints.
`catalog/refresh/` and `cli/commands.py` have no reader-facing English left.

**Two sentences stay English on purpose, and now say why in the code.**
`embodied_scope` is written *into* a catalogue file: a reader opens the file,
not the terminal of whoever last ran the refresh, and a data file in the
language of its last writer is a worse artefact than an English one.
`OPERATING_EMISSIONS` defines what the carbon column means, is read by whoever
maintains the catalogue, and nothing prints it — a definition, not output. Both
carry a comment stating the boundary, because the next person to sweep for
English strings will find them and should find the reason with them.

**A constant cannot be in the reader's language.** `GPU_REFUSAL` was a module
constant holding a paragraph; a constant is fixed at import and the language is
chosen after. It is `accelerators_refused()` now, following
`missing_key_message()`, which took that shape first in the same package for
the same reason. This is the same wall the API's route descriptions are behind —
there, the descriptions are argparse's to own, so it stays a real limit.

Two faults reading the output caught, both pre-existing:

- `1 countries`. The other headings in this verb already said `zone(s)` and
  `processor(s)`; the two country headings now say `country(ies)`.
- `collected March 2026` became *relevé en March 2026* in French. The month is
  scraped from the page and is English for every reader, so neither language
  puts a preposition in front of it now — a colon does the work.

Every figure these verbs print goes through the decimal separator in force:
footprints, tariffs, intensities. `575.1 kgCO2e` reads `575,1 kgCO2e` in French,
inside the paragraph that refuses it.

### The hardware half of a projection, and the three French faults English never had

`project_to_machine` and `project_to_processor` held the last English prose in
`estimate/extrapolate.py` — forty-seven strings, now none. Forty-four catalogue
keys: twenty for the accelerator projection, nineteen for the processor, three
the two share because they say the same thing, and two shared with the slice
projection that was already translated (`Refused.`, and the runtime that carries
no number).

Not a translation but a rewrite, because the sentences were assembled from
fragments. A phrase naming where a ratio came from — *the slower of the two
ratios (the memory bandwidth ratio, 3350 / 1555 GB/s)* — is built in one place
and embedded in four others, and English does not care what is embedded in what.
French does, and reading the output caught three faults no check could have:

- **`pris de` + `le plus lent…`** is not French: `de` + `le` contracts to `du`.
  The host sentence now says `d'après`, which takes any article unchanged —
  the fix is to pick a preposition that does not inflect, not to inflect it.
- **`les mêmes taille de lot et parallélisme`** does not agree. Each noun
  carries its own determiner now.
- **`toute la course`** for *every part of the run* is a weaker claim than the
  one being made: that no stage of it falls short of the ratio.

Two refusals changed shape to be translatable at all. `'A100' and 'H100' not in
the catalogue` joined its keys with a conjunction, which is a word; they are now
named after a colon and joined with a comma, the way every other list in this
package already was. The `and` was the only translated conjunction in the
codebase, and there is none now.

Four fragments did not become arguments, because a bare noun phrase dropped into
a sentence is where the above goes wrong: *single-threaded* and *all-core
throughput* each got their own whole sentence in both of the two places they
appear. Eight keys instead of four, and no grammar assembled at runtime.

Every number the two functions print now goes through the decimal separator in
force: ratios, core counts, memory sizes, throughputs. `2.15x` reads `2,15x` in
French, as the rest of the report already did.

### Three things a machine can check in a translation, and the one fault they found

No test reads a French sentence and judges it — a human reviewer is still owed
one. These are the defects a machine *can* find, measured over some five hundred
and twenty entries before any of them became a gate:

| Check | Hits |
|---|---|
| a translation under four fifths of the English length | **1**, a real one |
| identical to the English | 12, all of them legitimate |
| French punctuation spaced the English way | 1, a false positive (`https:`) |

The real one: `cli.help.scopes.scenario` said *"which scenario to place"* in
French where the English says *"which scenario's **costs** to place"*. A dropped
clause in a help line, invisible to every check that existed — the keys matched,
the arguments matched, the language was French. Only the **length** gave it away.

- The twelve identical entries are an allow-list with the reason attached:
  `Dimension`, `Notes`, `Provenance`, `Source`, `GHG Protocol`, `Service`,
  `Projections`, `Machine` are the same word in French; `Scope 2
  (location-based)` is the standard's own wording; `bar.language.*` are
  deliberately written in the language they offer. A thirteenth identical entry
  now fails, because a forgotten translation is the likeliest translation defect
  there is and the hardest to see by reading.
- The spacing check guards URLs, times and ratios — the guard is what the first
  version lacked, and `https:` was its only finding.
- Three sabotages confirm all three: a clause removed, a sentence left in
  English, a colon with no space before it.

### The HTML page reads the table too, and eleven headings stop carrying their own copy

`_heading(level, text, key)` took both the words and the key, so eleven headings
held a second copy of wording the translation table already had — the same fault
as the twenty-nine in the markdown report, one layer in. The helper ignores the
text when a key is given now, and the two section helpers that passed a title
beside a key no longer take one.

With them, every sentence the page kept to itself while the markdown report read
it from the catalogue: the services and models ledes, the scenario with no
costs, the projection headings and the bracket note, the profile table, the
rate nobody published, the what-if machine's own two labels, the derivation
figure's caption, and the page title.

- **An emphasis moved out of a sentence.** `_This scenario states no costs yet._`
  carried markdown's underscores *inside the translated string*, which the HTML
  page could not use. The catalogue holds the sentence; the markdown renderer
  adds its own emphasis.
- **A key in the wrong table, caught by a test.** `column.why` went into the
  message catalogue and onto a `<th data-i18n>`, where the page's script
  resolves against the *label* table — so the button would have blanked the
  column. The contract test that compares a key's wording to the text beneath it
  found it immediately.
- The button now switches **5.4%** of a report, and the docs say the share and
  **nothing else**: they used to pin the two character counts as well, which
  churn on every edit anywhere in the report and had me chasing a figure my own
  changes kept moving. Three numbers to keep true where one says the thing.

### What this machine will let you read, and what each counter covers

Two modules whose sentences a reader meets before any figure: the probe behind
`saggio power`, and the boundary each counter carries into the model beside its
own number.

- **The probe** (`analyze/capability.py`): eight interfaces, each with what it
  covers, what state it is in and why — including the one that explains why
  Linux keeps the processor counter root-only (CVE-2020-8694) and prints the
  remedy rather than performing it. The **interface names keep the product's own
  spelling** — powercap, IOReport, nvidia-smi — because renaming a kernel
  interface would leave a reader with nothing to search for; only the words
  around them move.
- **What a counter covers** (`analyze/power/tables.py`): the eleven boundary
  sentences that end up in a model file — the package-only undercount, the
  accelerator board read exactly or sampled, the memory counter that replaces an
  estimate, the wrap recovered and the wattage above which it would not have
  been.
- Eleven module constants became functions, and `RAPL_SCOPE_NOTE` with them.
  The shell lines in the remedy are **not** translated and never will be: a
  command is typed, not read.

### The README says what the i18n does and where it stops

Rewritten rather than patched, because the paragraph had gone out of date twice
over: it still said "adding a language is two files" when there are three, and
it described the language button as the whole of what a language does.

What it says now, and every number in it is measured: `--language` on every verb
and on every HTTP route that answers with prose; figures written the way the
language writes them; four hundred sentences in translation files. And the two
limits, which matter more than the feature — **a model carries the sentences it
was written with**, so 48% of a static report's text comes from the file itself
whatever you ask for, and the language button switches the page's furniture,
4.9%, while asking for the report in a language gives 29.4% of it in French (on
2026-10-19, a share that grows as the catalogue does; the date is there because
the number moves).

### Projecting a slice onto a whole run, in the reader's language

The half of `estimate/extrapolate.py` that every gallery model carries: the two
refusals, the linear projection with its two assumptions and three limits, the
scaled one with its measured exponent, and the sentence that says how far past
the measured sizes the whole run sits.

The hardware half — projecting a runtime from one accelerator or processor onto
another — is **not** done, and it is the one piece of this chantier that is a
rewrite rather than a translation: its fifty-odd pieces are spliced around
values by concatenation, and whole sentences with named arguments are a
different shape of code. Left for its own iteration rather than hurried.

### `--help` in the reader's language, which needed reading the argument twice

Eighty-five help sentences into the catalogue, and a problem of order to solve
first: **`--help` is rendered from strings the parser already holds, and the
parser is built before anything is parsed.** So the language is read off the
arguments by hand, once, before the parser exists — `requested_language()` —
falling back to `SAGGIO_LANGUAGE` for a container that states it once.

- `saggio --language fr audit --help` reads in French, and so does
  `saggio audit --help --language fr`: the pre-scan does not care where the
  option sits.
- **Two spellings, one of them winning.** The option is on the top-level parser
  *and* on every verb, and the per-verb one is declared with
  `default=argparse.SUPPRESS`. That is not a flourish: a default there is
  written into the namespace before the verb is parsed, so it would overwrite a
  global `--language fr` with the authored language every time the verb's own
  was absent. A contract test pins the suppression and both spellings, including
  which wins when both are given — the nearer word to the thing it describes.
- Keys are derived from the parser that owns the option, so a reader of the YAML
  can tell which `--help` a sentence belongs to: `cli.help.audit.country` is the
  country option of `saggio audit`, `cli.help.catalog.refresh.json` the `--json`
  of `saggio catalog refresh`.

- **And the two tests that were missing.** Converting the clone refusal I wrote
  `raise HTTPException(...) if request.language == DEFAULT_LANGUAGE else None`,
  which raises nothing at all for a French caller. I caught it by rereading the
  line; nothing in the suite would have, because no test asked a refusal for a
  language. Both gates have one now, and a sabotage confirms they fall when the
  language context around the `raise` is removed.

### A language on every route that answers with prose

The command line has had `--language` on every verb since the catalogue existed.
The HTTP surface had it on **one route**, `/audit`, for the local model's
sentence — while `/validate`, `/scopes`, `/next`, `/render`, `/diff` and
`/catalog/read-pcf` all answer with prose that now follows the language in
force, and had no way to ask for one.

- One field definition, four request models, six routes, each handler running
  inside the language its request named.
- **The agent tools come with it**: they are generated from the routes, so seven
  of the eleven now take a `language` argument without anybody writing it twice.
  The four that do not answer with data rather than prose — the version, the two
  catalogue readers, the freshness report.
- **The two refusals answer in the caller's language too.** "This deployment
  does not clone repositories… it is off unless SAGGIO_API_ALLOW_CLONE is set"
  is the sentence a caller reads most often from this surface, and it was the
  one sentence in it that could not be read in French.

### What the verbs print, and zero as each language counts it

- **Every line the daily verbs print** (`cli/commands.py`): `init`'s next step,
  `validate`'s weakest number, `scopes` with its dual-reporting note and the
  sentence a filer needs, `next`'s arithmetic of what closes what, `measure`'s
  power lines — the floor, what the slice added, what is attributable and the
  share it rests on — `audit`'s two warnings, and `measure --into`'s refusal to
  fold a failed run.
- **The validator's verdict** (`model/results.py`): `Valide : 0 erreur, 0
  avertissement.` The severity labels go with it, and the column width is
  computed from the longest label **this language has**, so the paths stay
  aligned where the word is longer.
- **Zero is not plural in every language.** *0 errors* is plural in English;
  *0 erreur* is singular in French. That is a property of the language, not a
  rule the code can hold, so it is a key like every other wording —
  `number.plural.zero` — and `saggio.i18n.plural()` reads it.

### Numbers written the way the language writes them, and the validator's 55 refusals

- **`17.4 W` in English, `17,4 W` in French.** Warith's call, against my own
  first answer, which was to keep the point everywhere; the argument I gave for
  it — that two reports stay comparable — was not one, because a machine reading
  a figure reads the model file, where it is a float either way. A report is for
  people.

  One function does it: `saggio.i18n.number()` takes an **already formatted**
  figure and moves the separator **between two digits and nowhere else**. That
  narrowness is the point — a pass over a rendered page would have rewritten
  `2026-10-18`, `schema 2.1`, `example.invalid` and every dotted field path. The
  key lives with the page's labels rather than with the engine's sentences,
  because both halves need it: the renderer writes a figure server-side, and the
  what-if panel recomputes in the browser. A contract test pins that the script
  reads the same key the renderer reads, so the two formatters cannot disagree.
- **Every refusal the validator makes** (`model/validate.py`), 55 of them:
  the schema versions, the required blocks, every quantity rule, the derivation
  rules — the circle, the unit that cannot come from its inputs, the arithmetic
  that does not follow — the dimension declarations, the scenarios, the
  market-based pair. Each one follows the field's own path, so it begins
  mid-phrase; the French keeps that shape, because the path is the subject and a
  translation that repeated it would read twice.
- Converted by matching **AST source segments** rather than hand-typed copies:
  the literals sit at four different indentations, and a patch that guesses one
  of them fails halfway through a file. Five of them turned out to have tails I
  had paraphrased from memory; the catalogue now carries the authored wording,
  which is the one a test can check.

### The spread, the embodied half, and the odds a reader can hold

- **What repeating a measurement says** (`analyze/repeat.py`): the sentence that
  bounds how far a figure would move again, the wide-spread warning, and
  `2/(n+1)` put as *"one time in 3"* rather than a decimal — in French too,
  because a reader counts occasions in whatever language they count in.
- **The embodied half and the SCI score** (`estimate/embodied.py`): the calendar
  amortisation the standard defines, the four reasons the figure stays open, and
  the refusal to publish half an SCI under the standard's name.
- `MEASURED_ONCE` and `_SPREAD_LABELS` were constants; a constant holds one
  language. They are `measured_once()` and a catalogue family now.

### What an audit writes, in the language it was asked in

Three modules whose sentences are composed while the measurement happens and
**written into the model file**, which is the half of the catalogue that does
not change how an existing report reads: a model carries the sentences it was
written with. Running the audit in French is what produces a French model.

- **How every quantity was computed** (`estimate/energy.py`): the six method
  lines — facility energy, carbon, the market-based twin, water, money, the
  total — and the twelve refusals beside them, each of which says what is
  missing rather than returning a zero.
- **What the figures rest on** (`auditor/assumptions.py`): the hardware
  lifetime that moves embodied carbon by a factor of two, the market-based
  factor nobody else can check, the two reasons an embodied figure stays open,
  what a measured power and runtime are.
- **Where the code runs** (`estimate/context.py`): seventeen sentences, every
  one of them about a catalogue row that is there or is not — the country stated
  or inferred, the tariff standing in, the water effectiveness nobody
  publishes, the instance shape nobody named.

### The measurement block, the honesty statuses, and the static report's own prose

Three more modules into the catalogue, in the order of how much of a report they
write. A static report renders **26.9%** French now, up from 11% when the
catalogue held one module.

- **What a power figure covers** (`analyze/power/boundary.py`): the whole-machine
  sentence, the floor, the attributable share, the twelve row labels of a
  measurement block, the counters, the spread. And the two **recognisers** that
  read prose back — the fold has to know whether an exclusion line is about idle
  capacity, and whether it says idle is in or out — now check **every language**
  rather than English. A line written during a French audit was invisible to
  them, which is the defect the fold exists to prevent, one translation away.
- **What each honesty status means** (`model/taxonomy.py`): `STATUS_MEANING` was
  a mapping, and a mapping holds one language. It is `status_meaning(status)`
  now, and the markdown report's private copy of it is gone — there were two.
- **The static report's own prose** (`report/markdown.py`): the title, the
  weakest-link sentence, the date line, the three section ledes, the projection
  headings, the profile table, the warning heading, the footer. Twenty
  sentences.

### The static report's structure, in the reader's language — and 29 duplicated strings

`render_markdown` had **fourteen headings and every table header written out in
English**, while the HTML report's translation file already held the same words
for the same sections. Twenty-nine strings were a second copy, free to drift,
and nobody had noticed because both copies were English.

- The markdown report reads the **same table** the HTML page embeds, so the two
  reports cannot word one section differently again. Every heading and every
  table header of a static report now comes out in the language asked for:
  `saggio render model.yaml --language fr`.
- Both renderers were also writing the same table headers independently —
  `Assumption`, `Value`, `Status`, `Provenance`, `Notes` in one, the same five in
  the other, neither translated. They share seven new keys now.
- **A defect the unification found.** The projections table carried
  `i18n_keys=["column.dimension", "column.value", …]` while the server wrote
  `["", "Value", …]`: pressing the language button wrote **"Dimension" into a
  deliberately blank header** and relabelled a whole-run figure **"Per unit"**,
  which is the one thing a column header must not do. The page looked right
  until somebody pressed the button, and nothing tested that. A contract test
  now reads every `data-i18n` node on both pages and fails when its key's
  English wording is not the text the server wrote.
- The share the button switches went from 4.8% to **4.9%** — three more tables —
  and a static report is **14%** French, from the inventory module and this one.

### A message catalogue, so the engine can say what it says in another language

The decision was Warith's, after the measurement in the entry above: a full
catalogue rather than a narrowed promise. This is the mechanism and the first
module.

- **`saggio/data/messages/*.yaml`, one file per language.** A sentence names its
  arguments in braces — `{dimension}`, `{method}` — so each language puts the
  figures where its own grammar wants them, which is the whole difference
  between a catalogue and a concatenation.
- **`say("key", **arguments)` reads the language in force**, held in a
  `ContextVar` that the command line sets around every verb. A parameter would
  have had to be threaded through every function that composes a sentence
  between the edge and the measurement, across dozens of modules, and the one
  that was forgotten would have been the defect.
- **`--language` is on every verb, from one definition**, attached by walking
  the sub-parsers rather than written out sixteen times: a verb added later gets
  it without anybody remembering to.
- **Four contract tests**, because a catalogue rots quietly: a key the code asks
  for that nothing answers (which renders as `[the.key]` in a report rather than
  crashing), a key one language has and another does not, wording nothing in the
  package reaches, and a translation that renames or drops an argument.
- **First module: where a cost lands in a greenhouse-gas inventory.** Twenty-four
  sentences, including the scope labels and the dual-reporting note the Scope 2
  Guidance turns on. `saggio scopes examples/render.yaml --language fr` reads in
  French; **11% of a static report** comes out in French from this module alone.
- The five sentence constants it used to export — `LOCATION_BASED`,
  `MARKET_BASED_MISSING` and their neighbours — are functions now
  (`location_based()`, `market_based_missing()`, …). A constant holds one
  language by construction, and leaving one beside the catalogue would have been
  a second way to get the sentence that ignores the language.

### Consent asked in a language the reader has, and two defects in the asking

The one place in this package where a translation is not a convenience: before
an audit runs a line of somebody else's code, it asks, and somebody who cannot
read what they are agreeing to has not been asked. The terms now live in the
translation file with the rest of what this package says, and
`saggio audit --language fr` and `saggio consent grant --language fr` show them
in French.

- **`saggio consent grant` recorded consent without ever showing the terms.**
  Eleven lines of wording — *"There is no sandbox. Anything the program can do,
  it will be able to do."* — displayed by the interactive question and by
  nothing else. The verb wrote `granted: true` and printed, at the default
  verbosity, **absolutely nothing**: its only output was an info log, invisible
  unless `-v`. And the cookbook recommends it as the first step of measuring
  somebody else's repository. It prints the terms first now, then says where the
  decision went, both at normal verbosity.
- **The record did not say what had been agreed to.** `granted: true`,
  `decided_on`, `tool`. Nothing about which wording answered. That is latent
  rather than live — the terms have not changed since the first commit, which is
  checkable with `git log -S` — but a `true` that outlives the text it answered
  is consent to whatever the text says next. The record now carries
  `terms_version`, a digest of the **English** terms, and `language`, the one
  they were read in.
- **A digest of the authored wording, deliberately.** Rewording a translation
  for fluency says the same thing and must revoke nobody; editing the English
  says something else and must revoke everybody. So the version follows the
  English whatever language was shown, and a record whose digest no longer
  matches is asked again *with a line saying the terms changed* — otherwise it
  reads as a tool that forgot the answer. A record from before the field existed
  counts as no, which costs one extra question, once, on a terminal where there
  is somebody to ask.
- **The word that grants it is the word of the language shown** — `oui` under
  the French terms — and the English `yes` is accepted too. The deliberateness
  comes from typing a whole word, not from which language it is in: somebody who
  reads the French terms and types the English yes has not pressed a key by
  accident, and refusing them would be a usability bug dressed as a safety
  feature.
- Contract tests on the wording itself, because it is the most load-bearing
  prose here: every language states the terms in **the same number of
  paragraphs** as the English (a hurried translation truncates, and every other
  check would pass), the word is one lowercase word, the question names
  `{word}` rather than spelling it out a second time, and every sentence about
  the record names `{path}` — because deleting that file is how consent is
  revoked.

- **And the honest size of what that does not cover, measured.** Pressing the
  report's language button exchanges **929 of the 19,337 characters** of visible
  text on a rendered report — **4.8%**. The structure switches; the substance
  does not, because an audit's prose is composed where the measurement happens:
  **709 prose literals of four words or more across 51 modules** on
  2026-10-19, only 8% of them under `report/`. The docs say so now in both
  languages, and a contract test recomputes the share from the page and fails if
  what they say stops being true — in either direction.

### Asked in the reader's language, after measuring what actually works

`USING.md` has promised an agent surface for "a colleague who asks in their own
words, in their own language" since the surface existed, and the report's labels
have always come from a translation file. But **one sentence of a cost model is
written rather than read**: a local model is asked what shape of work the
repository does, and it writes the answer into the `analysis` block. The prompt
never mentioned a language, so that sentence was always English, inside a report
somebody was reading in French.

- **Measured before building anything.** Two local models (`qwen3-vl:8b`,
  `gemma3:12b`), two seeds each, this repository's own summary:

  | how the model was asked | prose came back in French |
  |---|---|
  | English prompt + one sentence asking for French | **4/4** |
  | the prompt translated to French, asking nothing | **0/4** |
  | French prompt + the same sentence | **4/4** |

  The obvious move — translate the prompt — does nothing at all. A model answers
  in English unless it is *asked*, and asking works whichever language the
  asking is written in. So the prompt body stays in one language in the code,
  where it can be got right once, and what a translator adds is the request.
- **The language is now taken the same way by all five surfaces.** `saggio audit
  --language fr`, `AuditOptions(language=...)`, a `language` field on `POST
  /audit`, the same argument on the agent tool — generated from the route, so it
  could not have been forgotten — and `saggio.languages()` for anything building
  a picker, so a GUI asks the library instead of hard-coding a list that goes
  stale.
- **The closed set of workload kinds is never translated.** Those values are
  matched literally on the way back in, so a translated `training` would be
  discarded as an unrecognised answer: the model would have been asked a question
  whose right answer this package rejects. A contract test reads the offered set
  out of the built prompt, in every language.
- **`prose_language` is recorded beside the sentence.** An English sentence in a
  French model file is otherwise indistinguishable from a bug, and a French one
  in an English file from a model wandering off on its own.
- **A tag nothing is written in falls back to English and says so in the notes**,
  next to every other missing catalogue row. An audit must not fail over a
  language, and it must not silently answer in one nobody asked for.
- **Two translation files, one loader.** `saggio/i18n.py` reads both and answers
  for the package as a whole: a language counts as available only when the
  labels *and* the prompt have it. A contract test refuses a language only one of
  them has. The easy argument for two files does not hold and is not used — the
  prompt table is 375 bytes, 0.30% of a rendered page. What keeps them apart is
  that a label is free text and the prompt sentence is load-bearing.
- **A language is not a country**, stated in the skill where an agent will read
  it: `--language fr` says how to write a sentence and nothing about which grid
  the code runs on, and reading `--country FR` out of it would put a number in
  the model that nobody established.

- **The static half of pressing the language button.** The script replaces the
  text of every `data-i18n` node from the table; a key with no entry is not an
  error anywhere — the node keeps the English it was rendered with, so the page
  half-switches and looks like it worked. A contract test renders both pages and
  checks every key on them has a wording in every language: **37 keys on a
  report, 14 on the dashboard, none missing**. Removing one French wording fails
  it.

### Two defects found by running the thing rather than reading the diff

- **The dashboard's language control was broken by the commit before this one.**
  The report's control became a button reading a comma-separated
  `data-languages` attribute; the dashboard went on filling the same shell with
  `<option>` markup, so it rendered `data-languages="<option value="`. Two
  renderers, one template, one of them updated. Both ask the library now, and a
  contract test renders both pages and compares the attribute.
- **`docs/sync_api.py` described a cached function by its repr**, which carries a
  memory address — so the generated reference page would have differed on every
  run, failing its own `--check` for a reason nobody reading the diff could
  explain. It unwraps `__wrapped__` now and documents the real signature.

### The formatter's gate was red on master, and is in the suite now

`ruff format --check .` exited 1 over **nine files**, every one of them last
touched the same day by this project's own iterations. Ruff is pinned exactly in
`[dev]`, so the version failing locally is the version failing in continuous
integration: the build was red and nobody looked, because the routine before a
commit here is the test suite and the formatter was not in it. Two contract tests
run `ruff format --check .` and `ruff check .` now, so the gate fails where
somebody is already looking.

### Two toggles and a star, where a reader's hand already is

- **The theme control is a button showing the theme it would give you**, not a
  `<select>` listing three words: 🌛 while the page is light, 🌞 while it is
  dark. One press, no menu, and the glyph says which way it goes.
- **A flag button switches language** — 🇬🇧 / 🇫🇷 — beside it. A flag is not a
  language, so the accessible name says it in words, and a language code with
  no flag in the table falls back to its own letters rather than borrowing a
  country that does not speak it.
- **Built from whatever `i18n.yaml` contains**, not hard-coded to two. The
  translation file promises that adding a top-level language code is enough;
  a two-state toggle wired to `en`/`fr` would have quietly broken that promise,
  so the button cycles through the languages the file actually has.
- **`⭐ on GitHub`** beside them, linking to the project, translated like
  everything else in the bar.
- Both emoji buttons carry an `aria-label` **in the static HTML** as well as
  from the script: a button whose only content is an emoji has no accessible
  name at all, and the page is readable before the script runs.
  `sprezzature-accessibility-lint` on the rendered report: **0 findings**.

### Measured what sprezzature would bring to the web report, before rebuilding anything

- **The structural a11y gate finds nothing.** `sprezzature-accessibility-lint`
  runs twenty static rules over the generated HTML: the report scores **0
  findings**, and so does the dashboard. Whatever a rewrite would be for, it is
  not that.
- **The contrast audit found four real failures, and they are the worst four
  the palette could have had.** `--ink-faint` was 3.55:1 against the page,
  below the 4.5:1 WCAG AA asks for text at that size — and it colours `th`,
  `td.unknown`, `.muted` and the what-if labels. That is to say: **the colour
  marking a figure as uncertain was the hardest one on the page to read.** The
  `estimated` badge was 4.21:1 against its own background, the same fault in
  the same place.
- Fixed by moving four values, hue and saturation held: `#86867c` → `#707068`
  (light), `#82806f` → `#8c8a78` (dark), `#9a6a12` → `#936511`. Solved against
  the **sunken** surface rather than the page, because that is the darkest of
  the three backgrounds the colour sits on — a first attempt calibrated on the
  page passed there and still failed at 4.28:1 on a sunken card.
- A test pins the floor at 4.5:1 and reads the shipped stylesheet rather than a
  copy of the values; putting `#86867c` back fails it.
- **And a finding about the linter rather than this package.** The published
  site scores 260 `aria-hidden-interactive` findings, every one of them the
  heading-permalink pattern `<a href="#id" aria-hidden="true" tabindex="-1">#</a>`.
  That pattern is correct: `tabindex="-1"` is what makes the anchor
  unfocusable, which is the condition the rule exists to enforce. Probed with a
  two-line file — the rule fires with and without the `tabindex`, so it does
  not look at it. All 260 are one false positive.

### A machine cursor on the web report, and durations a reader can hold

- The HTML report already recomputed a model somewhere else: two cursors,
  country and provider. It now has a third, **the machine** — and that one is
  different in kind. Changing the country rescales a figure; changing the
  machine **recomputes** it, because energy is runtime times power and only the
  power moved.
- **And it changes what the figure is.** This model's own power may be a
  counter reading; every catalogue row is a datasheet rating. The moment a
  different machine is chosen the note under the panel says so: *"at its
  datasheet rating of 350 W. That rating is estimated, not measured: these
  figures are no longer this machine's."* A panel that let a nameplate wear a
  measurement's status would be the worst number on the page.
- The default is the static report's own constant, and it is the only option
  there that may be a measurement. Twenty-five accelerators and six processors
  are offered beside it, each with the rating it will be computed at. A
  processor row states watts per core and a core count, so the two factors are
  multiplied here and both travel with the figure.
- **`1.087e+04 s` is three hours and one minute**, and a package whose argument
  is that a figure should be legible had no business printing the first
  spelling. Durations now read as a reader says them — `3 h 1 min (10870.4 s)`,
  `27.2 ms`, `250 ns` — with the exact seconds kept beside the long ones,
  because somebody checking the report against the model needs the number the
  model holds. Both reports spell them the same way, and a test says so.

### Reading a vendor's product carbon footprint, and refusing to guess

- The previous release argued there should be **no** verb that reads a PCF,
  because the figure a document states is for a baseboard while this
  catalogue's unit is one accelerator, and the divisor is on another page. That
  was a reason to build it carefully, not a reason to refuse — and the design
  that makes it safe was already written down in the refusal itself.
- `saggio catalog read-pcf <url>` fetches the document, extracts its text, and
  **shows its working**: the sentence the figure came from, the line the divisor
  came from, and the arithmetic between them. Then it prints a draft row and
  stops.
- **It lands on the committed numbers without being told them.** Run against
  the two documents this package cites, it reads 1,312 and 2,274 kgCO2e for the
  HGX H100 and HGX B200 baseboards, finds `Form Factor 8x …` on another page,
  and produces 164.0 and 284.25 — the figures a human put in the catalogue a
  month earlier, by hand.
- **Three refusals make it safe.** A figure must come from a *sentence*: the
  parser is an OCR engine, so a bar chart becomes text like everything else,
  and a number lifted off a chart is the one thing this package will not carry.
  A board figure with no form factor is **refused**, not divided by a guess.
  And nothing is written — there is no `--into`, because a catalogue row is a
  claim somebody makes and the person making it is the one who can be asked
  why. The draft also carries no `key`: a document does not know what this
  catalogue calls things.
- The draft's `embodied_scope` is written for it, and satisfies the contract
  added last release: it begins by naming one unit and states the division.
- Five surfaces, as the rule requires: the library, the command line, `POST
  /catalog/read-pcf`, the agent tool that derives from it, and both cookbooks.
  The route is **off unless `SAGGIO_API_ALLOW_FETCH` is set** — fetching an
  address the client chose is the hazard cloning is, gated separately because
  an operator who will let the server read a PDF has not thereby agreed to let
  it clone a repository.
- The parser is an optional extra, `pip install 'saggio[pcf]'`. The three
  runtime dependencies stay three, and the verb says what to install rather
  than failing on an import three frames deep.

### Why there is no verb that reads a product carbon footprint

- The working list has carried, since October, the idea of a verb that reads a
  vendor's PCF PDF and **proposes** a catalogue row for a human to accept. The
  two documents this package already cites were opened and worked through by
  hand to find out whether that is a good idea. It is not, and the reason is
  arithmetic rather than taste.
- Both summaries state their figure in prose a parser would find on the first
  try: *"the carbon footprint from cradle-to-gate for one HGX H100 GPU
  baseboard is 1,312 kg CO₂e"*, and 2,274 for the HGX B200. **This catalogue's
  unit is one accelerator.** The divisor sits on a different page, in a spec
  table reading *"Form Factor: 8x NVIDIA H100 SXM"*, and the knowledge that a
  division is needed at all comes from the schema rather than from the
  document.
- A row carrying `embodied_kgco2e: 1312` under the key `H100` would be **wrong
  by a factor of eight and would look impeccable** — real vendor URL, real
  date, a number genuinely printed in the document. That is the worst output
  this package can produce. Reading the number is the easy half; knowing what
  one unit of the destination is, and writing down that you divided, is the
  half that has to be done by somebody who can be asked why.
- Both committed figures were verified against their documents while this was
  being settled: 164.0 is 1312/8 and 284.25 is 2274/8, and both rows already
  said so in their own `embodied_scope`.
- **That discipline was a convention and is now a rule.** Every row stating a
  footprint must carry a scope, a source and a date, and the scope must *begin
  by naming one unit* — `One SXM 40GB card…`, `One of the eight GPUs on an HGX
  H100 baseboard…`. Eight rows carry a footprint today and all eight pass;
  removing a scope makes the suite fail.
- `CONTRIBUTING.md` / `CONTRIBUER.md` say all of this where somebody about to
  add a row will read it.

### A regulation that publishes numbers back, and the water TODO it closes

- The working notes said the EU data centre reporting scheme would turn the PUE
  and WUE `TODO`s into catalogue rows with provenance. **Half of that was
  wrong**, and the report says so itself: *"All data have been anonymised to
  avoid disclosing personal, company, or location-specific details pursuant to
  Article 5(5) of Delegated Regulation (EU) 2024/1364."* There is no
  facility-level figure to put anywhere, and there will not be.
- What **is** published is Union-wide, and it is worth having.
  [COM(2026) 500 final](https://data.consilium.europa.eu/doc/document/ST-13443-2026-INIT/en/pdf)
  of 21 September 2026 gives a 2024 **PUE of 1.36**, energy-weighted over the
  681 data centres whose figure passed the quality review, and a **WUE of
  0.58** L/kWh over the 458 that reported water above zero. Both are now the
  `on-prem-eu` provider.
- **It closes a `TODO` that every self-run model has carried since the first
  release.** Water was permanently open because *"On-premises publishes no
  water usage effectiveness"*. For a room inside the Union that sentence is no
  longer true, and a measured EU audit now closes five of seven dimensions
  instead of four.
- The row carries what the report says about **itself**: only about 36% of the
  data centres in scope reported at all, 70.1% of what they reported passed the
  quality review, and the WUE average excludes dry-cooled rooms and so
  overstates the typical one. A catalogue row is read instead of the document
  it came from, so the document's own limits have to travel with it.
- **National averages are refused**, and the reason is the package's own rule.
  They exist in the report — 1.15 to 1.66 — but only as labels on a bar chart,
  and the Commission flags the four Member States with fewer than three
  reporting facilities as possibly unrepresentative. Transcribing a figure off
  a chart is how a number stops being able to say where it came from.
- The Commission's own page for the report redirects to EUR-Lex, which serves
  an empty body to anything that is not a browser. The citation is the Council's
  copy of the identical document, which answers 200 — chosen for the same reason
  the Ember citation was moved two releases ago: a source a reader cannot reach
  is not a source.

### Two refusals decided, two that were never refusals, and a claim that was false

- **The headline page contradicted every measured model, for twelve releases.**
  `README.md` listed idle capacity among what the package never counts;
  `examples/render.yaml` and `examples/request.yaml` have said the opposite
  since the exclusions list stopped being a constant — *"Idle capacity is
  inside these figures, not outside them."* The same sentence was wrong in
  `LISEZMOI.md`.
- **No sonde could see it.** It is not a figure, not an arithmetic and not a
  link, so the three prose checks and the link checker all looked past it. A
  new one binds the two: a page may not list among its exclusions a subject a
  committed model says is inside. Aimed at the **enumeration**, not the page —
  the first version banned the phrase outright and would have forbidden the
  page from explaining the nuance.
- Both pages now say the true thing, which is more interesting than the false
  one: idle capacity is excluded when the power is a nameplate rating and
  **inside** when it was read off this machine's counters. An exclusions list
  that read the same either way would be false in one of the two cases.
- **Refused by name: continuous monitoring.** Every figure here is per unit of
  work and a daemon has no unit of work; it would have to split a stream across
  whatever happened to be running, which is the attribution measured two
  iterations ago as the least reproducible of three — 67% to 190% across five
  runs against 8% to 49% for the metered total. A number whose spread cannot be
  bounded cannot say how far it can be trusted.
- **Refused by name: reading a cloud invoice.** A bill states money for an
  account over a month, and splitting it across units of work needs a key
  nobody publishes. What is allowed is said beside the refusal: read the figure
  yourself and record it with `source_kind: stated`, which is **better**
  provenance than the `aggregator` tariff the catalogue would otherwise use.
- **Two entries on the working list were not refusals at all.** Extra
  dimensions are accepted — the registry takes them, the annotated template
  ships `egress`, and a contract test exercises it. A sixth surface has a
  documented procedure in `USING.md`. Both had been carried as refusals in
  private notes that nobody had checked against the code.

### What a range of five runs is worth, exactly

- `--repeat 5` records a range and nothing said what a range *is*. The module
  said it was not a confidence interval; the gate said a movement was "inside
  the noise the models measured", which sounds like the noise was measured. A
  reader was left to guess, and the guess a width invites is "bound".
- It is not a bound, and the figure is exact. For **any** continuous
  distribution the next run falls outside the range of the `n` before it with
  probability **2 / (n + 1)** — among `n + 1` exchangeable draws each is
  equally likely to be the largest, so the new one is a fresh maximum with
  probability `1/(n+1)`, a fresh minimum with the same, and cannot be both. No
  shape assumed, none fitted. Checked against normal, exponential and uniform
  draws over 200 000 trials each: 0.3334, 0.3329, 0.3337 against a predicted
  0.3333 at n = 5.
- **Five runs are exceeded by unchanged work one time in three**, and the lever
  is in the arithmetic: to halve the surprise, roughly double the runs.
- Said where it matters rather than only on a page. A quantity's notes end
  *"A range from 5 runs is not a bound: the next run lands outside it about one
  time in 3, whatever the shape of the variation, and nothing need have changed
  for it to."* And `saggio diff`, when it excuses a movement for landing inside
  a band, now adds *"a 5-run range, exceeded by unchanged work one time in 3"*
  — a gate that excuses something should say how often the excuse is wrong.
- A band built from two ranges reports the **thinner** of the two run counts: a
  product is no better founded than its weakest factor.
- This also settles how the previous iteration's result may be quoted. The
  three attributions kept their **ranking** across three independent series;
  the **factor** between them did not, moving from about four to about fifteen.
  A ranking survives a wide range; a ratio of two ranges does not, and the
  pages quote the ranking.

### Which attribution this package uses, decided on measurements rather than taste

- A measured power figure has three readings and the package carried all three
  without saying which it stood behind: the metered total, the share of the
  processor domain, and the total minus the idle floor. `MEASURING.md` ended
  that section with *"which of the two belongs in a cost model is not settled
  here"* for nine releases.
- **It is settled now, and the numbers settled it.** The three were measured
  side by side over five runs of one command, three separate times:

  | | Range over five runs | Spread |
  |---|---|---|
  | The metered total | 15.25 W to 23.16 W | 49% |
  | Attributed by processor work | 3.209 W to 3.646 W | **13%** |
  | Active power, total minus floor | 1.64 W to 9.83 W | **190%** |

- **The subtraction is refused by name.** It is a small difference between two
  readings that each move, so it inherits both and keeps almost none of the
  signal — five to fifteen times less reproducible than either input across the
  three series. **The domain attribution turned out to be the steadiest figure
  of the three**, steadier than the metered total it derives from, because a
  domain counter does not move when something else on the machine wakes up.
  That was not the expected result.
- **The costs still use the metered total**, and the page says why: it is the
  only one a meter produced, and substituting a modelled figure would put an
  estimate under a field that says `measured`. What would change that is
  stated so it can be argued with — the domain share prices *processor* energy
  alone and would understate any accelerator workload.
- The claim is checkable from the file. `measurement.spread` now records what
  the **floor** and the **attributed share** did across the runs, beside the
  runtime and the total it already kept. Without those two the comparison the
  decision rests on could not be redone from a committed model — the same
  defect as the four before it: a figure the run produced and the file never
  got.
- `examples/render.yaml` re-measured to carry them; the four pages quoting its
  figures went stale the moment it was, and the contract from two iterations
  ago said so before anything was committed.

### The fit a model records can now be checked against the evidence beside it

- A scaling block keeps the sizes and seconds it was fitted over, *"so a reader
  can redo the arithmetic rather than take the exponent on trust"*. The reader
  could not. `y = a · x^b` needs both numbers, and only `b` was a field: the
  coefficient appeared **only inside the method sentence** — the same shape as
  the projection divisor one iteration ago, one level down. Its own docstring
  says it is *"useful for redoing the arithmetic and not much else"*.
- `measurement.scaling.coefficient` is written now, and two contracts use it:
  the fit must reproduce every observation recorded beside it, and the two
  numbers the method sentence spells must be the two the fields carry. Both
  sabotages fire — move the coefficient, or move an observation.
- Backfilled into `walkthrough/5-run.yaml` by **refitting the file's own
  observations** with the package's estimator, not by transcribing the
  sentence. The refit lands on the recorded exponent to nine digits and the
  recorded R² exactly, which is what says it is the fit that produced the
  block. It predicts the three observations to within 1.2%, 2.5% and 1.2%.

### A rule measured and rejected: "every field must reach the file"

- Three iterations found the same defect — a figure the object holds and the
  file never gets (`measure --json`, `marginal_watts`, `fraction_completed`) —
  so the obvious move was a contract over every serialisable class. It was
  measured first, as the last two iterations taught.
- **Name matching: 47 of 111 fields (42%) never appear as a key.** Almost all
  are renames — `Spread.values` is written as `runs`, `SliceResult.baseline` as
  `idle_watts`, `MachineProfile` becomes the whole `deployment` block.
- **Value reachability: 24 of 105 (23%)**, under the threshold — but every one
  had to be triaged by hand, and all but one turned out to be a false positive
  or a deliberate omission. `ServiceHit.pricing_source_url` and `RateTable`'s
  source fields do reach the file, by another path.
- So the general rule is not shipped: a contract needing a human verdict on
  each hit is not a contract. What is shipped is the one real defect it found,
  and a check that is specific enough to be exact.

### The divisor every projected cost turns on is a figure now, not a sentence

- A model held the run size as `analysis.total_work.stated_as: '400000'` — a
  **string** — and the fraction the projections divide by nowhere at all. Every
  projected cost in this repository rested on a number that appeared only
  inside a method sentence.
- Two numbers the code already had now reach the file: `total_work.units`
  beside the literal token the source spells it with, and
  `measurement.fraction_completed`, which `SliceResult` has always known and
  never wrote down. The same defect twice — a figure the object holds and the
  file never gets — and the same one as `measure --json` dropping its
  attribution and `marginal_watts` living only in prose.
- A contract requires the divisor a method states to be a figure the model
  carries, and the two to agree. It fired on every model with a projection.
- **It also settled a discrepancy rather than papering over one.**
  `walkthrough/5-run.yaml` divides by `0.001` while its `total_work` says
  400 000, a factor of 400 apart. Both are right and they measure different
  things: 400 000 is the whole run, `0.001` is the share the slice covered —
  and the command in the same block ran `--num_samples 400`, which is exactly
  400 000 × 0.001. The missing field was the slice's share, not a wrong number.
- The report names the new field (*"share of the whole run this slice
  covered"*), and both figures are declared under the bare-number rule with
  the reason they are not costs.

### What a machine says it can measure, against what it measured

- `saggio power` reports which counters answer. The suite takes a real slice on
  every platform. **Nothing compared the two.** If IOReport stopped answering
  tomorrow, the report would say `absent`, the slice would come back unmeasured,
  every test would still pass, and every figure would quietly become an
  estimate. Two tests now fail in that case, and they are the only ones here
  whose verdict depends on the machine underneath them.
- They take opposite branches by design, and both were run that way: on this
  Apple Silicon machine the counters answer and an unmeasured reading fails; in
  a Linux container with no powercap the reading must be *absent* **and** carry
  a reason, and a figure produced anyway fails. Sabotaged by silencing
  `PowerMeter.stop` on a machine that can measure: report says yes, run says no,
  the sonde fails.
- **A correction to something this repository believed about itself.** The
  working notes have said since October that "the measurement path is exercised
  only on this laptop; CI measures nothing". That was wrong. CI runs the whole
  suite, including the three `slow` tests that spawn a real subprocess, on
  Linux and macOS on every push, and prints `saggio power` before them. What
  was missing was not the running — it was anything that *checked* the result
  against what the machine claimed.
- Confirmed separately by running the full measured path — `audit --run`,
  `validate`, `render`, `next` — inside a Linux container: the refusals read
  correctly, the model validates, the power is `estimated` from the nameplate
  with the ARM/container reason stated, and consent is refused outright when
  there is no terminal to ask on.

### Following every link the repository asks a reader to follow

- The argument of this package is that a figure says where it came from, and a
  source a reader cannot reach is a figure that no longer does. **Nothing
  checked the links.** `docs/check_links.py` follows all 208 of them — the
  pages, and the catalogue rows beside the numbers they vouch for — and sorts
  the answers instead of reducing them to pass or fail.
- **It found a citation that had moved.** The service catalogue's Gemini
  pricing row pointed at `ai.google.dev/pricing`, which Google now redirects to
  `ai.google.dev/gemini-api/docs/pricing`. Updated in the catalogue and in the
  two example models that had copied it. A redirect is reported apart from a
  refusal for exactly this reason: the document is still there and the citation
  is no longer pointing at it.
- **And four pages carried an invented source on a real vendor's domain.** The
  recipe for adding a catalogue row used
  `nvidia.com/en-us/data-center/h300/` for a graphics card that does not exist.
  A made-up citation on a real domain is indistinguishable from a stale one,
  which is the worst a citation can be. Illustrative links now live on a domain
  reserved for documentation, and the checker skips those **by rule** rather
  than by a list.
- The audit recipe's example repository is now one a reader can actually audit
  (`github.com/karpathy/nanoGPT`, which the gallery already measures) instead of
  a placeholder that 404s.
- A 403 from Legifrance, ResearchGate or Intel is a robot filter, not a dead
  document, and only a server stating it holds no such document fails the run.
  Nineteen links answer that way today and none of them is broken.
- It is a maintenance script and not a test, for the reason `docs/sync_api.py`
  is: a suite that fails because somebody's server is slow teaches people to
  ignore the suite. A contract test checks only that its collector still sees
  both the pages and the catalogue rows.

### An arithmetic written in prose must be an arithmetic that works

- Three places spell out a calculation and put the answer beside it, and nothing
  checked that the words give the answer: a nameplate note (*"12 cores x 4.0 W +
  96 GB x 0.3725 W/GB"*), a projection's method (*"Whole run = measured slice /
  2.5e-06."*), and a comparison table on a page. The new contract parses each
  and requires it to come out.
- **It found four wrong figures in the committed walkthrough.** Both
  `3-measured.yaml` and `5-run.yaml` projected a whole run whose **money** was
  out by 1.15x and whose **carbon** was out by 0.736x, while their time and
  energy were right. The factors name the cause: an electricity tariff
  refreshed from 0.240 to 0.276 USD/kWh, and a grid intensity refreshed to
  41.2 gCO2e/kWh. The per-unit costs were recomputed against the new catalogue
  and the projections were left behind — in the repository's own teaching
  example, through several releases.
- They are recomputed from each model's **own stated method** applied to its
  **own current slice cost**. Nothing was invented: the sentence was already
  there and the figure beside it had stopped following from it.
- The projection check is also what reads the one quantity every projected cost
  turns on. A model holds `analysis.total_work.stated_as` as the string
  `'400000'` and the fraction nowhere, so until the divisor becomes a field,
  this test is the only thing that reads it as a number.
- The first version of the check stopped at the first bad dimension and
  reported `money` on two models whose `carbon` was wrong too. It collects now:
  a sonde that hides half of what it found is half a sonde.
- Sabotages, all four firing: a projected value moved, a table's answer moved,
  a stored subtraction moved, a sentence moved.

### A sentence a model carries must be the sentence its own numbers produce

- The pages are checked against the models, the models against the schema — and
  a sentence *inside* a model was checked against nothing. That is where
  iteration #7's fault lived: a note calling a figure the median of five runs
  when it is not.
- `measurement.power_note` must now equal what `baseline_note()` writes from
  that model's own `idle_watts` and `marginal_watts`, and every warning the
  recorded spread obliges must be a warning the file carries. Both sentences
  moved into functions that read a stored block, so the writer and the check
  cannot drift apart. Three sabotages, three failures: changing the stored
  subtraction, changing the sentence, and widening the spread without touching
  the warning.
- **`measurement.marginal_watts` is now stored.** The subtraction was stated in
  prose — *"Subtracting it gives 3.6 W"* — and kept nowhere, so the number the
  sentence turns on was not a field, in a package whose rule is that a figure
  is a field. A second contract test checks the stored power minus the stored
  floor **is** the stored marginal.
- Still prose-only, and said rather than quietly left: the divisor every
  projection turns on. `method` reads *"Whole run = measured slice / 2.5e-06"*
  and the notes say *"a slice covering 0.00025% of the run"*, while
  `analysis.total_work.stated_as` holds `'400000'` as a **string**. Three
  statements of one quantity, none of them a number the schema can see.

### The repository refuses a bare number; it has never refused a sentence

- Four Ralph iterations running, the fault that mattered was in prose, and only
  the one about a *number* was caught by a machine: an invented Legifrance
  identifier, a false claim that this package attributes power "the way Kepler
  does", a note calling a figure the median of five runs when it is not, and a
  `derived_from` that was not a derivation — the last caught by the validator,
  the first three by a human reading.
- Writing the sonde found that **four committed pages had been stale for two
  iterations**. `GALLERY.md` said the render model drew **21.3 W** three lines
  above a paragraph giving its floor as 13.8 W and the figure it carries as
  17.4 W — a self-contradiction in one paragraph. The Kepler comparison in
  `MEASURING.md` / `MESURER.md` still quoted a share, a total, a floor and a
  processor domain from a measurement that had been replaced, and its headline
  conclusion was wrong by a factor of 2.7.
- **The convention now enforced**: inside a section that names a committed
  model, a figure written in **bold** is a claim that the model carries it. A
  figure that is not the model's own — a nameplate rating, a threshold, a
  figure from a paper — is written without bold. The rule is declared in the
  page, by how it is written, rather than in a list of known-bad strings that
  would go stale in the direction that hides the fault.
- A second and stricter rule for the numbers a reader meets first: a table row
  linking one model must quote that model's value **at that unit and that
  status**. Sabotaging a digit, and separately sabotaging `measured` to
  `estimated`, each makes it fail.
- The Kepler comparison is re-derived, and gained something the stale version
  hid: **the factor is not a constant.** The current measurement gives 3.01 W
  against 0.72 W, a factor of four; the earlier one — a third as idle — gave
  2.65 W against 1.68 W, a factor of 1.58. The busier the machine, the more the
  subtraction removes and the less the domain counter does, so the two methods
  diverge furthest exactly when a reader most needs them to agree.
- **What this still cannot catch**, said plainly: a sentence making a claim
  about the world rather than about a number. "This is how Kepler splits a
  node" would pass today.

### The drift gate now reads the noise the models measured

- `saggio diff` gated a release at ten per cent against numbers whose own
  measurement block said they move by a hundred. **It had the evidence in both
  files it was comparing and read neither.** Two five-run measurements of
  unchanged code, one after the other on one laptop, used to fail six changes;
  they now fail **none**, with eight reported as inside the ranges the two
  models themselves recorded.
- It still fails when the evidence says something moved. The same new model
  against an older one measured *once* fails, because that single value sits
  outside the range the five runs spanned.
- A derived figure's band is the product of the bands it derives from, found by
  walking `derived_from` backwards — exact while each step is proportional to
  its inputs, which is how every cost in a model is built. A figure that
  reaches no measured range gets no band and is gated exactly as before, so
  nothing changes for a model that repeated nothing.
- **The bands only ever excuse the threshold.** A weakened status, a weakened
  provenance, a changed unit or currency, or a deleted quantity still fails
  whatever the noise says.
- Excused *visibly*: the line names both ranges, and the summary counts them —
  a release waved through by a hundred-per-cent band should show the reader the
  band. The JSON surface carries `within_noise`, `noise_before`, `noise_after`
  and `excused_by_noise`.
- **What this cannot catch, said in both cookbooks.** A regression is caught
  through whichever dimension was measured tightly. A workload made twice as
  slow fails on `costs.time` and on the projected time, while its carbon,
  money and energy lines are excused — a 109% power band swallows a 100%
  move. The gate is blind exactly where the evidence is, which is intended
  and still a limitation: a regression that raises the power without
  touching the runtime would pass.
- **A projection's band is linked in code, not in the model.** Giving a
  projection a `derived_from` was tried first and the validator refused it
  with the right reason — *states 18000000.0 but does not follow from
  scenarios[0].costs.time* — because a projection divides by a fraction nobody
  named. `derived_from` claims a value **follows arithmetically** from its
  inputs; a band needs only **proportionality**, which is the weaker claim a
  division by a constant actually supports. The stronger claim would have been
  false in eleven committed models.

### One run bounds nothing, and the two figures do not behave the same way

- `saggio measure --repeat N` runs the command N times and reports the spread.
  On this package's own gallery model, five runs of the same command on one
  machine a minute apart: the **runtime moved 15%** (1.326 s to 1.538 s) and
  the **measured power moved 109%** (16.13 W to 37.36 W). The runtime is a
  property of the work; the wattage is a property of the room, because a
  counter meters the machine and one of the five caught something else waking
  up. Both carried the same word, `measured`.
- **No fifth status was invented.** Inventing one before measuring the thing it
  would describe is how the problem started. What is added is a number beside
  the number: `measurement.repeats`, `measurement.spread`, and a sentence in
  the notes of every quantity the repeats bound.
- The model carries **one real run** — the one whose runtime was the median —
  and not a median assembled per field: a model's energy is its runtime times
  its power, and medians from different runs would state a pair that never
  occurred together. Which also means the power a model carries is *not* the
  middle power of the series, and its notes say so rather than calling it a
  median it is not.
- A quantity measured once now says so (*"Measured once, so nothing here bounds
  how far a second run would move it"*). Silence reads as stability, and the
  power is the figure that is not stable.
- A spread wider than 10% — the threshold `saggio diff` gates a release on — is
  warned about rather than left to a reader to notice.
- **No function-level profile is taken when `--repeat` is above one.** The
  profiler changes what is being timed, so a series with one profiled run among
  plain ones would report a spread the profiler put there. Found by running it:
  the first draft profiled run one and left the other four alone.
- The validator refused the new fields on first write — `measurement.repeats:
  is a bare number; wrap it in a quantity so it carries an honesty status` —
  which is the rule working. They are now declared exempt, with the reason: a
  status is a property of a number's provenance and a spread is a property of
  its stability, and collapsing the two would lose both.
- `examples/render.yaml` re-measured with `--repeat 5`; its five runs are in
  the file. Nothing was discarded to make the spread look smaller.
- One new contract test: a `measured` runtime or power must state how far a
  second run would move it. It fired on three models when written.

### A model that said idle capacity was excluded, while pricing the whole machine

- Every model this package writes carried the line *"Idle capacity. This is the
  cost of one unit of work, not of being ready."* in its `exclusions`. For a
  model built from a nameplate rating that is true. For a model whose power was
  **read off this machine's own counters** it is false, and three committed
  models proved it: `examples/walkthrough/5-run.yaml` priced its unit of work at
  **31.9 W** while its own measurement block, three fields above, recorded
  **2.9 W** as the attributable share. A factor of eleven, inside one file.
- The exclusions list is no longer a constant. `saggio audit --run` writes the
  line that is true of the figure it just obtained, and `saggio measure --into`
  **rewrites** the line it has just falsified — naming the floor the machine was
  drawing, the share of processor work the run was, and admitting that the costs
  below use neither.
- A measured `power_draw` now states **both** of its boundaries. The hardware
  one (which counters answered, what silicon they see) was always there; the
  workload one — *"This is the whole machine's draw, not this run's alone"* —
  was not, and without it a reader takes the figure for the run's own.
- Three contract tests over every committed model: none may claim idle is
  excluded while its power is `measured`; the idle line must be the one the
  package would write today, regenerated from that model's own measurement
  block; and a measured wattage must name its workload boundary. The first
  fired on four models when it was written.
- `saggio measure --json` emitted a hand-listed payload that dropped the
  attribution the same command had just computed — the warning quoted a share
  of processor work that no field of the JSON carried. It now emits the mapping
  a model is given, and the text output prints the attributable figure beside
  the baseline subtraction instead of only the half that flatters.
- `examples/render.yaml` was re-measured so a gallery model carries the block:
  **21.3 W** during the slice, **9.9 W** before it, **2.65 W** attributable from
  a 14.7% share. Runtime 0.0277 s, carbon 1.01e-05 gCO2e. `examples/request.yaml`
  keeps its figures, which [`BOUNDARIES.md`](BOUNDARIES.md) cites.
- [`MEASURING.md`](MEASURING.md) / [`MESURER.md`](MESURER.md) said this package
  attributes power *"the way Kepler does"*. It does not. Kepler v0.10 divides
  **active** power — the total minus the idle baseline — by the share
  ([formula](https://sustainable-computing.io/kepler/usage/power-attribution/));
  this package multiplies the share by the **processor domain's own counter**.
  On `examples/render.yaml` that is 1.68 W against 2.65 W, **a factor of 1.58
  from the same measurement**. The page now states both and picks neither.
- [`LANDSCAPE.md`](LANDSCAPE.md) / [`PAYSAGE.md`](PAYSAGE.md): the "nothing is
  attributed to a process" gap now says what *is* recorded, and that the costs
  still use the whole figure.
- **Both reports rendered the measurement block by printing every scalar and
  skipping anything nested.** Three fields are nested, and all three were the
  ones a reader needs: the share that is the entire justification for the
  attributed figure printed above it, which counters answered, and the
  per-subsystem split — the only measured split in the report. The Markdown
  report, committed beside every model in the gallery, showed none of them, and
  the scalars it did show arrived without units (`attributed watts | 2.65`).
  Both reports now take labelled rows from one function, and a contract test
  fails when a field of the block never reaches the page.

### The energy line of an EU AI Act filing

- Annex XI makes a provider of a general-purpose AI model document its **known
  or estimated energy consumption**, and where it is not known it permits an
  estimate **from the compute used** — which is this package's method, written
  into law. Enforceable since **2 August 2026** (up to 3% of worldwide turnover
  or €15 million); models placed before 2 August 2025 have until **2 August
  2027**.
- [`ANNEX-XI.md`](ANNEX-XI.md) / [`ANNEXE-XI.md`](ANNEXE-XI.md) maps the
  requirement onto what a cost model already carries, line by line, and is
  equally explicit about what it does not do: it is not a filing, it covers one
  unit of work on one machine, and it documents energy rather than the rest of
  the annex.
- The methodology is still being written. The Commission consulted between
  April and June 2026 on measuring AI energy, the AI Office is to publish a
  summary, and delegated acts may set methods "with a view to allowing for
  comparable and verifiable documentation". Those two words are this package's
  design brief, so the page says what it already does about each.

### A page about boundaries, because two companies just proved the point

- Google published **0.03 gCO2e** for a median Gemini prompt and Mistral
  **1.14 gCO2e** for a four-hundred-token response. Roughly thirty-eight times
  apart, and neither is evasive: one counts a contract's electricity and the
  idle capacity reserved to serve you, the other counts the grid average and
  the factories.
- [`BOUNDARIES.md`](BOUNDARIES.md) / [`FRONTIERES.md`](FRONTIERES.md) takes one
  committed model — `examples/request.yaml`, measured — and shows what its
  figure becomes under four boundaries. Two are computed; **two are refused**,
  each naming what it would need.
- The arithmetic is the package's own, on the catalogue's own figures. Amortise
  NVIDIA's ISO 14067 footprint for an HGX H100 over the same runtime and the
  manufacturing term is **three to six times the electricity**, with the
  hardware lifetime alone moving the answer by a factor of two. A figure that
  leaves manufacturing out is not a conservative figure; it is a different one.

### The verb for the person holding fifteen open fields

- An audit comes back with every cost open, each field carrying a sentence
  about what would resolve it, and nothing saying which to answer first. The
  fields are not independent: on one of the gallery's own models, **one
  question closes five numbers** and forty-six close only themselves. A reader
  working top to bottom spends the afternoon on the ones that unlock nothing.
- `saggio next cost_of_running.yaml` ranks them, and the ordering is arithmetic
  rather than opinion: a quantity names its inputs in `derived_from`, so
  reading those edges backwards says exactly which other quantities would
  become computable, cascade included.
- **It invents no questions and asks for nothing derived.** Every line is a
  field the model already holds open, quoted in the sentence the model already
  wrote for it, and a field this package computes itself is never put to a
  human — that would be asking them to do the arithmetic, unprovenanced.
- A field that closes nothing else is still listed. *Closes only itself* is the
  honest description of a water figure or a contracted emission factor, not a
  reason to hide either.
- `saggio.next_questions` and `saggio.questions_payload` in the library,
  `POST /next` on the HTTP surface, and therefore a tool an agent can call.

## 1.5.0 — 2026-10-17

Three more ways to reach the same engine, and the first release in which *whose
emission is this* is answered on every surface rather than on one. Nothing here
breaks: every public name resolves as it did, the schema is unchanged, and the
two new surfaces arrive as an extra the default install does not carry.

### Two defects the release build found, which the suite could not

- Installing the wheel into an empty environment is the only test that resolves
  dependencies the way a user does, and it is the one this package had never
  run for the new surface. It failed on the first attempt, at import, before
  serving a single request.
- **`fastapi-mcp` asks for `mcp>=1.12` with no upper bound**, and calls
  `Server(name, description)` with two positional arguments. `mcp` 2.0 made
  everything after the name keyword-only, so a fresh resolve installs a protocol
  library the adapter cannot import: a `TypeError` at import time rather than a
  dependency conflict, which means nothing in the resolver objects and nothing
  in a development environment that already holds an older copy ever notices.
  Both extras now carry `mcp>=1.12,<2`, bounded here because the package that
  should bound it does not and this one is what a user installs.
- **The protocol server was reporting a paragraph as its version.** That same
  constructor's second parameter is the version, so a client listing its servers
  showed the application's whole description where a version belongs, and an
  agent asked which version answered it would have quoted prose. The version is
  put back after construction, and a test holds it there.

### The catalogue was re-read for this release, not re-dated

- All four refreshable columns asked their sources on release day: Ember's
  published yearly dataset for the thirty-eight carbon figures,
  GlobalPetrolPrices for the tariffs, the IANA database for the sixty-four
  timezones, Boavizta for the four processor footprints. **Nothing moved by more
  than the catalogue's own precision**, and the dates now say that somebody
  looked.
- It matters because of what the alternative looks like. The rows were sixteen
  days from the end of their window, and a window that closes shortly after a
  release is an invitation to bump a date rather than read a source, which is
  the one outcome the whole freshness mechanism exists to prevent.

### Two gaps in the cookbooks, and the checks that now watch for them

- `scopes` shipped two releases ago, answers the question this release is built
  around, and appeared in **neither cookbook**. `machine` had never been in them
  either. Both are in now, in both languages, with what each prints and why.
- The check that would have caught it: **every verb the parser knows must be
  shown in both cookbooks**. The pages promise every command a reader is
  expected to type, and nothing compared that promise against the parser that
  defines them.
- A second check, from the same shape of defect: **a version printed in prose
  must be the installed one**. `python -m saggio --version` is documented with
  its answer beside it, and that answer goes stale on the next release, in the
  one place a reader looks to find out which version they have.

### The release notes exist in the other language

- This file is published as an Atom feed on the site, so a French reader
  subscribing to release notes was handed English. [`JOURNAL.md`](JOURNAL.md) is
  the twin, all eight releases of it, and the site builds **`fr/feed.atom`** from
  it with its own title and its own entry identities.
- The two halves carry the same version headings on purpose: one builder reads
  either, and a release that existed in one language and not the other would be
  a release only half announced.

### Three more ways in, over the same engine

- The library and the command line reach everybody who installs a Python
  package, which is not the person who has to file the figure. There is now an
  **HTTP surface**, `pip install "saggio[api]"` and
  `uvicorn saggio.api.app:app`, with routes for validating, placing, rendering,
  comparing, reading the catalogues and auditing a repository.
- An **agent surface** sits on the same application: `uvicorn saggio.api.mcp:app`
  serves Model Context Protocol tools at `/mcp`. They are generated from the
  application's own OpenAPI document, so a tool's name is the route's identifier
  and its description is the route's docstring. Nothing is written twice, which
  is why nothing can drift into an agent telling somebody the wrong scope.
- **Two refusals are in the shape of the HTTP surface rather than in its
  settings.** There is no route for measuring at all: it executes a repository's
  code with the server's permissions, and over a network there is nobody to ask
  for consent. And `/audit` clones nothing unless the operator sets
  `SAGGIO_API_ALLOW_CLONE`; off, it answers with what it would take.
- `placed_model` is new in the library. The whole-model placement was assembled
  inside the `scopes` command, where the other surfaces could only have reached
  it by copying, and a copy that drifted would be this package disagreeing with
  itself about which line of an inventory a figure goes on. A test now asserts
  that the route returns exactly what the library returns, field for field.
- A `Dockerfile` and a `docker-compose.yml` ship both surfaces with the clone
  switch off, a read-only filesystem, no capabilities and a non-root user.
- [`USING.md`](USING.md) and [`UTILISER.md`](UTILISER.md) say what each of the
  five surfaces is for, what none of them may do, and how to add a sixth.

### The skill stayed silent for half the people it was written for

- Its description fired for an engineer who says "cost per request" and not for
  the sustainability team asking the same question in its own words: which
  scope, which method, what the auditor needs to see. Both vocabularies are now
  in the description, in both languages, inside the published 1024-character
  ceiling.
- The workflow never mentioned `scopes`, the one verb that answers the second
  reader. It is now a step of its own, with the market-based refusal and the
  fact that water has no scope.
- A reference of its own, `references/inventory.md`, for what an agent may and
  may not say to the people who file the figure.
- The evals gained a **triggering** section. Every case in them tested a skill
  that had already loaded; whether it loads at all is the first thing that can
  fail and nothing was watching it.
- [`TRIGGERS.md`](TRIGGERS.md) refused *organisational carbon accounting*
  wholesale, which swallowed the adjacent question it does answer. A whole
  inventory is still somebody else's job; where the software's own figure
  belongs in one is not the same question and no longer shares its refusal.
- That page also had no French half, which for the audience it was just widened
  to reach was the wrong half to be missing. [`DECLENCHEURS.md`](DECLENCHEURS.md)
  is it, carrying both vocabularies on purpose: a French team reading it still
  sees the English phrasings its own engineers will type.


### macOS is back in the gate, and it found something on its first run

- Nearly all of this package's power-counter code is macOS-only, and no CI job
  had read a line of it since the matrix was cut to one. A regression in
  `IOReport` would have shipped and been found by a user. The runner is Apple
  Silicon, which is the hardware that code is for.
- It was dropped because it was red. What made it red was fixed afterwards, in a
  different commit, without anybody going back to check — tests that encoded a
  developer's machine rather than the product. Bringing it back cost nothing but
  the look.
- `workflow_dispatch`, so a change to the gate can be tried on its own branch. A
  CI change that can only be tested by merging it is a CI change nobody tests;
  this one was wrong on its first run and right on its second, on a branch.
- Each run prints `saggio power` before the suite, so a counter that stops
  answering says so in its own words rather than through whichever test happens
  to notice.

### `TZ=Japan` was being silently ignored in favour of the laptop

- The first macOS run failed on an assertion that a timezone name contains a
  slash. A CI runner is set to **UTC**, which no developer's laptop is, and the
  suite had never run anywhere that was.
- The assertion was the smaller half. `UTC`, `GMT`, `Japan`, `Singapore`,
  `Israel` and `EST5EDT` are all real entries in the timezone database and none
  of them has a slash, so the reader **discarded the `TZ` somebody had
  deliberately set** and used the machine's own zone instead. Setting
  `TZ=Japan` on a laptop in Paris did not get you Japan; it got you France,
  silently, with a French grid intensity in a file somebody would quote.
- The slash was never evidence in the other direction either: a POSIX `TZ`
  *rule* string can contain one and names no zone, and `TZ=/etc/passwd` was
  returned as a timezone name because it has a slash in it.
- All three sources — the environment variable, the `/etc/localtime` symlink,
  the standard library — now ask the **timezone database** the same question,
  through `zoneinfo`. No network and no dependency: those are the files
  `/etc/localtime` already points into.
- A name the catalogue does not list still gives **no country rather than
  another one**. `Japan` is a compatibility name the database keeps and the
  catalogue lists `Asia/Tokyo`, so the country stays open — which is the right
  answer and the whole point: before the fix it resolved to wherever the
  developer was sitting.

### A number now says which line of a GHG inventory it goes on

- The gap this closes is the one between the two people who have to agree: an
  engineering team produces a carbon figure, and a sustainability team cannot
  file it, because *whose emission is it* is a question the figure never
  answered. Filed as scope 2 when the machine was rented, it double-counts
  against the provider's own disclosure; left out, it is simply missing.
- The GHG Protocol settles it with one fact — **who buys the electricity and
  owns the machine** — and that fact was already in every model as
  `deployment.provider`. The providers catalogue now records it as
  `operated_by`, so the rule is data rather than code: own the machine and the
  electricity is your **scope 2** and the hardware your **scope 3 category 2**;
  rent it and both are **scope 3 category 1**, because you bought a service.
- `saggio scopes model.yaml` prints the placement, the reason, and the standard
  that settles it. `--json` for a pipeline. Every rendered report — Markdown,
  HTML, Word, PDF — carries the same in a section of its own, in both languages.
- A provider nobody classified gets **no scope at all** rather than the nearest
  guess. The two answers differ by which legal entity reports the emission, and
  a wrong one looks exactly as tidy as a right one.
- Energy is placed as what it is: the activity datum a scope figure is computed
  *from*, not an emission. Water has no scope, because it is not a greenhouse
  gas. Both say so in a sentence, because "not applicable" in a report reads as
  an omission.

### The scope 2 figure says which of the two methods it is

- A grid average **is** the location-based method, by definition. The GHG
  Protocol requires scope 2 to be reported both ways wherever contractual
  instruments exist, and the amended European standard spells out the same pair.
  This package carried one of them and said nothing about which.
- It now says so, and names the missing half: a market-based figure comes from a
  supplier-specific factor, from the instruments you hold, or from your market's
  residual mix, and none of the three is derivable from a grid average. So it
  reports neither a market-based number nor a zero — a shopping list rather than
  a dead end.

### The other half of scope 2 is now a figure, not an apology

- The section above named the missing half and stopped there. A shopping list is
  better than a dead end, but a sustainability team reading it still has to
  leave the tool, compute the second number somewhere else, and reconcile two
  documents. Scope 2 is required **both ways**; half of it was a feature gap
  wearing a good explanation.
- `carbon_market_based` is a canonical dimension now, computed from
  `assumptions.market_carbon_intensity` — **the one fact only the organisation
  holds.** State the factor and the figure appears beside the location-based
  one, from the same energy, labelled with the method that produced it and
  drift-gated the same way. State nothing and the shopping list prints as
  before. Nothing is ever derived from a grid average, which is the other method
  by definition.
- **It is held to a stricter provenance rule than anything else in the model.**
  A missing `source_url` elsewhere is a warning; here it is an **error**. Every
  other number has a source a reader shares and a refresh command that re-reads
  it. This one has neither: nobody but you holds the contract, and nothing here
  can go and look — so without its document it is unverifiable by construction.
  A missing `retrieved_date` is a warning, because a contract factor is restated
  every year.
- **A market-based figure alone is warned about.** It is the half a contract can
  improve, and published without its companion it reads better than the
  disclosure is. The location-based placement, correspondingly, stops saying the
  pair is broken once it is whole — and the sentence that replaces it says the
  one thing a whole pair invites getting wrong: the market-based number does not
  replace the other, because a contract does not change which electrons the grid
  delivered.
- **On rented hardware no row is written at all.** The pair lives inside
  scope 2; on a vendor's machine the electricity is the vendor's scope 2 and the
  pair is the vendor's to disclose. What reaches you is one purchased service in
  category 1, where the standard draws no such pair. An audit there leaves
  nobody holding a `TODO` that can never become true — and a model moved to a
  vendor after the fact is told why its row lost its scope, in words.
- **The projection onto other hardware keeps whichever methods the scenario
  carries**, for the same reason water is projected: a dimension that vanishes
  between two tables of the same report looks like an answer rather than an
  omission. The sentence saying what was held constant now names the contracted
  factor as the assumption least likely to survive the move — a supply contract
  is signed for a site.
- **The restatement in kilometres says which figure it restated**, but only
  where there are two. It has always restated the location-based number, which
  was unambiguous while it was the only carbon on the page; beside a figure that
  can differ from it tenfold it was not, and that line is the one a
  non-specialist actually reads.
- Found while wiring it up: the `scopes` command decided which unplaced
  emissions to explain from its **own two-item copy** of the emissions list, so
  the most specific refusal this package writes printed nowhere.

### `INVENTORY.md` / `INVENTAIRE.md`

- The page for the person who files rather than the one who measures: the scope
  mapping and why, what the status taxonomy and the provenance contract give an
  assurance provider, and six things this tool does not cover — no IT estate, a
  market-based factor it computes from but will never invent, no end of life, no
  netting against removals, a cloud figure that is a model rather than an
  invoice, and a small catalogue.
- The rules it is written against, checked on 2026-10-14 rather than recalled:
  the three GHG Protocol documents, [Directive (EU)
  2026/470](https://eur-lex.europa.eu/eli/dir/2026/470/oj/eng) and what the
  Omnibus did to the CSRD population, the renumbering of the GHG disclosure from
  E1-6 to E1-8 in the amended ESRS, and the French regulatory *bilan GES* under
  article L. 229-25, which is a separate obligation with its own filing.
- **A citation in that page was invented and caught before it shipped.** The
  Legifrance article identifier for L. 229-25 was written from memory rather
  than read, and pointed at a different article. Found by trying to follow it.
  The rule this package applies to its catalogue applies to its prose.

### `LANDSCAPE.md` covers the other side of the room

- The tools a sustainability team already has, which the comparison table
  deliberately does not score: the carbon accounting platforms that are the
  system of record for a whole inventory and cannot read your code, Boavizta —
  whose API already computes four of this catalogue's processor footprints and
  whose GPU half is refused by name — the Green Software Foundation's Impact
  Framework, and Climatiq.

### Thirty-eight carbon rows cited a link that showed a reader an error

- Every grid row cited `api.ember-energy.org/v1/carbon-intensity/yearly`. Asked
  without a key, that endpoint answers **HTTP 403** and
  `{"detail":"No API key set"}`. So every carbon figure in the catalogue —
  and in the eleven committed example models, and the eleven reports rendered
  from them — carried a citation that showed whoever followed it no number at
  all, in a package whose entire proposition is that a figure says where it
  came from and can be checked there.
- The rows now cite [Ember's published yearly
  dataset](https://ember-energy.org/data/yearly-electricity-data/): the same
  series, CC-BY-4.0, no key, and a page that opens. The endpoint is still named
  — in the catalogue header and in the module — where naming it is provenance
  of method rather than an invitation to go and look.
- **The suite already had a test for exactly this fault**, written when four
  processor rows were found citing an endpoint that answers a reader with the
  wrong number. It was handed one URL and told about that one, so Ember's sat in
  thirty-eight rows for three iterations, passing it. The rule is now
  `ENDPOINTS_A_READER_CANNOT_FOLLOW`, declared by the modules that hold the
  endpoints, and it is checked over the examples as well as the catalogue — the
  surface the first version never looked at, and where the defect had been
  copied twenty-two times.
- `STANDARDS.md` had *described* this defect and argued itself out of it:
  Ember's answer was "unhelpful but true". It is not true. A citation claims the
  figure is checkable there, and nothing is checkable at a 403.

### A refresh now reads Ember without a key, and says which half answered

- `saggio catalog refresh grid --column carbon` reads the published dataset by
  default. A key is still used when one is offered, and the run prints which of
  the two answered rather than leaving it to be inferred from whether it worked.
- This is not the substitution this module refuses. The refused one is a
  *different measure* wearing the same units — Our World in Data's **lifecycle**
  intensity where this column is **operating** emissions — and that refusal is
  intact. Ember's own dataset was checked against the API country by country
  before being adopted: 36 of the 38 agreed to better than half a percent,
  thirty of them to better than a tenth, several to three decimal places.
- Why it matters beyond convenience: a column only a credential-holder can
  re-read is a column that stops being re-read, and what happens instead is that
  somebody bumps the date. That is the one outcome this whole mechanism exists
  to prevent.
- `--api-key` and `EXAMPLES.md` / `EXEMPLES.md` said a key was required. Both now
  say what is true, and `--year` says that the most recent year is not the same
  year for every country.

### Ukraine's 2022 figure had been shipping as a 2025 one

- The two countries that did *not* agree in that check are the interesting part.
  **Ukraine** matched Ember's **2022** value to three decimal places — 250.5
  against 250.525 — while its row said `carbon_data_year: 2025`.
- The cause was one line. The refresh took the newest data year across all
  thirty-eight countries and stamped it on every row. Ember publishes most
  countries to 2025 and Ukraine only to 2022, so the one row the source had not
  caught up on claimed a currency it did not have. Nothing about the number
  could show it: 250.5 is an unremarkable intensity, and the stamp was the only
  place the three-year gap was ever going to appear.
- Each row now carries **its own** data year, and a refresh names the countries
  the source has not caught up on rather than burying them in a maximum.
- **Belgium** was the other: 125.8 on file against 151.3 published, a 20% upward
  revision inside the one-month freshness window. Not a defect — a reminder that
  the window is an upper bound on staleness, not a guarantee of accuracy. Eight
  countries' figures moved on this re-read and all eight are now current.

### A TPU v4 has a footprint, and four other TPUs deliberately do not

- Google published a cradle-to-gate LCA of five TPU generations
  ([arXiv:2502.01671](https://arxiv.org/abs/2502.01671), ISO 14040/14044) — the
  first manufacturing figure for an AI accelerator from the people who designed
  it, modelled from the node, die size and yield nobody outside has. Its Table 1
  separates the accelerator's own emissions from the host processor's and the
  datacenter's, which is the boundary this catalogue's other accelerator rows
  already use.
- `TPU-v4` carries **366.0 kgCO2e** per chip, HBM included, host and building
  excluded and named. The eighth footprint in the catalogue, and the fourth
  accelerator.
- The same paper gives v4i, v5e, v6e and v5p, and they are **not** added. It
  publishes no power figure of the kind every row here carries: `tdp_w` is a
  datasheet rating and what the paper has is a measured mean across a production
  fleet. A better number for estimating energy, a different quantity, and
  putting one under the other's name would make the column mean two things.
- A small confirmation worth recording: the paper's own specification for the
  v4 — 275 TFLOP/s BF16, 32 GiB — is what the row already said from Google's
  documentation. Two readings of the same part agreeing is the only reason to
  believe the footprint belongs to this row.

### Six pages quoted a count of the catalogue and nothing checked it

- "Three accelerators out of 25 rows and four processors out of 12" appears in
  `README.md`, `LISEZMOI.md`, `STANDARDS.md`, `NORMES.md`, `LANDSCAPE.md` and
  `PAYSAGE.md`. Adding one row to `hardware.yaml` falsifies all six at once,
  and no test looked — the same shape as the release preface that said
  "twenty-one entries" above twenty-three.
- A contract test now reads the counts out of the prose, in both languages and
  both phrasings, and compares them with the catalogue. `CHANGELOG.md` is
  exempt on purpose: its old entries say *seven footprints* and should go on
  saying so, because they describe a release where that was true.

### Three tests were reaching the network and one of them passed because of it

- Found while changing which function the carbon refresh calls. A test that
  stubbed the API path left the keyless path free to download the real
  thirty-megabyte file — and then **agreed with it**, because the real figure
  for France happened to be the number the test had written down.
- Both paths are stubbed together now, through one helper, so neither branch can
  reach a socket whichever one the environment selects.

### A Word file and a PDF say what made them, and when

- The title block of a `docx` and a `pdf` now names **saggio** as the author and
  carries the date the document was produced. Before this, both were blank:
  a reader holding the PDF had no way to tell whether it had been written by a
  person or generated, nor when.
- The date is deliberately **not** the one already in the body. *Last updated*
  is a fact about the model — when somebody last changed a number in it — and
  the title block is a fact about the file. A document produced today from a
  model untouched since June states both, which is the whole point: a stale
  figure must not acquire a fresh-looking date by being exported again. A test
  holds the two apart.
- `--author` puts a different name on a client deliverable, `--generated`
  states the date verbatim (`2026-Q2`, `submitted 14 March`), and passing no
  author at all drops the line without dropping the date with it.

### The conversion can be told to refuse the network

- Found while reading what the converter actually does: since its 2.5.0 it
  fetches a branded template over HTTP whenever no reference document is given.
  That is a pleasant default and a surprising one — a render fails on a train,
  and two renders of one model can differ because a template moved.
- Neither is a defect, and neither was declared. `--offline` now refuses every
  network-touching step, and the behaviour without it is written down rather
  than left to be discovered.

## 1.4.2 — 2026-10-04

The first release published to a package index, and the one whose long
description works there.

### The header logo points at a host that serves images

- `README.md` is the long description, so an index renders it as the project
  page. Its header logo was an HTML `<img>` with a **relative** source, which
  on an index resolves against the index's own domain and shows nothing.
- The round of absolute links in 1.4.1 walked past it, because the check that
  found those read Markdown link syntax and an `<img>` tag is not Markdown link
  syntax. The contract now reads every form a reference can take — link, `src`,
  `href`, and the reference-style spelling.
- Images carry a second trap: on the forge, `blob/` answers with an HTML page
  and only the raw host answers with the image bytes. Both were measured —
  225 KB of `text/html` against 3.2 MB of `image/png` — before choosing, because
  a rewrite to `blob/` would have been absolute and still broken.
- This is a separate release rather than a correction folded into 1.4.1
  because the long description is baked into the metadata: shipping it under
  that number would have put content on the index that the `1.4.1` tag does not
  contain. That is the defect 1.4.1 itself was cut to stop repeating.

### A malformed tag that no renderer complained about

- The repair above went out once with the tag mangled — a stray quote, the
  attributes before it gone. It was correct when written and correct when
  rendered; it was not correct when it was staged, and nothing in between
  looked again.
- Worth knowing for anyone relying on `twine check`: the renderer **accepted**
  the malformed tag without a word and silently dropped the attributes it could
  not parse. The page would have rendered a logo that simply looked wrong, with
  no tool anywhere reporting a fault.

## 1.4.1 — 2026-10-04

A release that contains what its notes describe, which 1.4.0 did not.

### 1.4.0 was tagged before the work its notes claimed

- The tag was cut at a commit whose continuous integration **failed**, and the
  two sections that opened its notes described commits that landed after it.
  Anybody installing that tag got neither.
- Nothing has been moved or rewritten to hide that: the tag stays where it is,
  the two sections move down here to sit beside the commits they describe, and
  this entry says what happened. A project that asks every figure to declare how
  far it can be trusted does not get to quietly re-point a release.
- Its own preface had already noticed, without anybody reading it: it announced
  twenty-one entries and carried twenty-three. Moving the two that did not
  belong to it makes the sentence true rather than having to edit it.

### A measurement is not promised on a machine that cannot take one

- The end-to-end journey for `--run` asserted that a runtime comes back
  **measured**. That holds on a laptop, where the slice really does run, and it
  failed on the continuous-integration runner, where nothing could consent to
  executing somebody's code and the runtime stayed open. The runner was right.
- Leaving a runtime open is the correct answer on a machine that cannot or may
  not measure. The journey now checks the promise that holds either way: a
  measured runtime carries a positive number and a note naming what was timed,
  and an open one carries no number at all.
- It takes **both** branches on purpose rather than whichever the machine
  offers — once with standard input closed and a home directory of its own,
  which is how a scheduled job and a container invoke this and which no consent
  can reach, and once normally.

### The README's links survive being republished

- Fourteen links in `README.md` were relative. It is also the package's long
  description, and an index renders that on its own domain, where
  `](EXAMPLES.md)` resolves to a page that was never there. Every one of them
  works in a checkout and on the forge; they would only have broken on the one
  surface nobody looks at.
- They are absolute now, and a contract test refuses a relative link in that
  one file. The other documents keep theirs: they are read where they live,
  where a relative link is the one that survives a fork.
- Found by building the wheel, installing it into an empty environment outside
  the repository, and running the journeys against it — which also confirmed
  that all twelve catalogue and template files ship, and that the console
  script reports the version the metadata declares.

### Fewer tests, more of them functional, and a job half as long

- **2,174 cases become 1,701**, with nothing stopped being checked. Three
  catalogue rules were parametrised over all 111 rows and one documentation
  rule over all 152 commands — 333 and 152 cases each saying the same sentence
  about a different key. Collapsed, each is one test that walks everything and
  **names every offender in one failure**, which is what somebody fixing them
  needs rather than whichever row pytest stopped at.
- **Eight functional journeys** added, through the command line as a shell runs
  it: start a model, audit then render then read, fail a lying model, turn an
  open runtime into a measured one, fail a drift gate, produce an HTML report
  that reaches for nothing, tell a usage error from a verdict by exit code, and
  report freshness for the weekly job. The whole file runs in **11 seconds**,
  and gutting the validator or collapsing an exit code fails the journey named
  for it.
- **`python -m saggio` now works.** The package had a console script and no
  `__main__`, so it answered *"'saggio' is a package and cannot be directly
  executed"* — which reads as a broken tool rather than a missing file. Found
  because the functional tests need to run *this* working tree rather than
  whatever is on the PATH.
- The job runs `pytest -n auto`. Every test still runs; it is spread across the
  runner's cores. **144 seconds to 53** locally, and it stays short as the suite
  grows — which is the only way a gate remains one somebody waits for.

### A test that only ran on the author's Python

- The contract added in this release to hold `pyproject.toml` against
  `__version__` reached for `tomllib`, which **arrived in 3.11**. This package
  supports 3.10, and continuous integration runs 3.10 precisely because it is
  the version most likely to refuse something. It refused this, on the commit
  that added it — green on a 3.13 laptop, red on the floor of the range.
- It reads the version with a narrow expression now, scoped to the `[project]`
  table so a version pinned for a dependency further down cannot be mistaken
  for the package's own. Checked on both 3.10 and 3.13 before being pushed.


## 1.4.0 — 2026-10-04

Twenty-one entries that accumulated under the previous heading before anybody
stopped to cut a release. Nothing here is breaking. Two of 1.3.0's own claims
were corrected along the way, and those corrections are described below rather
than quietly folded into the text above: *A derivation is checked* was closed
only for the shapes it had been tested against, and the catalogue's provenance
was honest per row before it was honest per column.


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

### A Sources section that is merely most of the sources

- `STANDARDS.md` and `NORMES.md` cited **three sources in their body that the
  Sources list did not name**: the parametric-model paper, its dataset, and the
  processor-footprint method the four CPU rows point at. All three were added
  to the page over two days without anybody going back to the list.
- A reader who checks the list and finds nothing about the processor footprints
  concludes they rest on nothing, which is worse than no list at all. Fixed in
  both languages, and held by a contract test that fails naming the URL.
- Two addresses for the SCI specification both answer and neither redirects, so
  they are declared the same source rather than inferred to be — a rule that
  guessed would hide real omissions behind a heuristic.
- Found by looking at the rendered page rather than by reading the Markdown.

### A derivation that goes in a circle is reported

- Direct self-reference was caught; **a circle through an intermediate was
  not**. Two assumptions deriving from each other validated clean, with no
  error and no warning. The weakest-link rule assumes a chain can be walked
  back to a fact, and a circle has no bottom: the package computed a status out
  of nothing and stated it as confidently as the rest of the page.
- Found by an adversarial probe against shapes not tried in earlier rounds, and
  confirmed by printing the entire report rather than filtering it. Circles of
  two, three and five steps are reported now, including one reached from
  outside and two separate circles in one model, and the message names the
  circle **in the order a reader would follow it**.
- A diamond, a long honest chain and one input named twice stay silent — a walk
  that marked a node *visited* rather than *being visited* would call every
  diamond a circle.

### A citation a reader follows must not show them a different number

- `source_url` exists so a reader can check the figure beside it. Two of the
  sources are APIs, and they answer a reader differently from a program: Ember
  returns `{"detail":"No API key set"}`, unhelpful but true, while **Boavizta
  returns 19.0 kgCO2e** — the default for an unnamed chip, and the exact figure
  this package refuses on import. Four processor rows cited it, so anybody who
  clicked saw a number with nothing to do with that row's processor.
- Those rows now cite the page explaining the method, and name the endpoint
  they were computed by in their scope, where it is provenance rather than an
  invitation. A contract test refuses that endpoint in any field a reader
  follows, and putting it back fails by row name.
- **Introduced by the commit that split provenance per column** — the fields
  were made honest and the links were never followed as a reader.

### The embodied figures are cross-checked against an independent dataset

- The dataset the last release was waiting on has been published:
  [Zenodo 10.5281/zenodo.20321644](https://doi.org/10.5281/zenodo.20321644),
  CC-BY-4.0, 174 NVIDIA cards from 2013 to 2024, from
  [arXiv:2607.01258](https://arxiv.org/abs/2607.01258). It was fetched and the
  comparison run.
- **A100: 127.6 here, 123.2 there — 3.4% apart.** Two methods sharing no inputs
  — a teardown with primary elemental analysis, and a parametric model from die
  area and memory — landing that close is the best evidence available that the
  one non-vendor figure in the catalogue is about right.
- **H100: 164.0 here, 196.5 there — 19.8% apart.** The paper explains it itself:
  it estimates memory higher than NVIDIA does, from a different life-cycle
  database, and the processor and board lower. The vendor figure is kept —
  third-party verified under ISO 14067, about the exact part — and
  `STANDARDS.md` now says a credible independent estimate puts it a fifth
  higher, because a reader quoting 164 deserves to know that.
- The dataset is a **check, not a source**, for the same reason Eurostat checks
  the tariffs rather than supplying them. Nothing in the catalogue comes from it.
- Matching was done on **exact product names**. The first attempt matched on
  substrings and paired `L4` with `L40`, `T4` with `T400` and `P100` with
  `Quadro GP100` — the same fuzzy-match failure this package refused from
  Boavizta two releases ago, nearly repeated by hand.

### Word and PDF output is tested without Word or a PDF engine

- `report/office.py` **56% → 100%**, the last module in the package that was
  notably low. Everything in it that is not a one-line guard happens around a
  subprocess, and none of it runs unless `md2star` and Pandoc are installed — so
  on most machines, and on the cloud runner, the whole conversion never executed.
- A stand-in `md2star` is written instead: a real executable taking the real
  flags, writing a real file or failing the way the real one fails. The
  subprocess is real and the arithmetic is the shipped arithmetic.
- Held now: the house template reaches the converter as `--reference-doc` and is
  absent when none was given; the scratch Markdown is cleaned up; the output
  directory is created rather than demanded; a hung converter is given up on by
  name and by seconds; and **a failure that says nothing still produces a
  message**. That last one is not hypothetical — the code carries a comment
  saying an empty tail once crashed the messenger instead of delivering it, and
  removing the guard reproduces the exact `IndexError`.

### The samplers are tested, threads and subprocesses and all

- `power/graphics.py` **65% → 100%** and `power/accelerator.py` **69% → 86%**.
  Both hold a sampler, and a sampler is the one thing in this package whose
  arithmetic nobody can check by looking: a thread, a file, and a mean.
- Nothing is mocked. The graphics tests write a real sensor file and **change
  its contents while the thread is running**, which is what proves the figure is
  a mean rather than the last reading. The accelerator tests write a **stand-in
  `nvidia-smi`** — a real executable that prints what the real one prints, for
  the same flags — and let the real subprocess, the real log file and the
  shipped arithmetic do the rest.
- Four claims that were asserted nowhere before, and are now held by tests named
  for them: the figure is a **mean**, not the last or the highest reading; an
  unreadable sample is **skipped**, never counted as a zero; a two-board node
  draws **twice** one board's power; and a mean of too few readings is **no
  figure at all** rather than a thin one. Each was verified by breaking it on
  purpose and watching the right test fail.
- **One test was wrong and the code was right**: it expected the accelerator
  sampler to skip `[N/A]` in a stream, but a board answering `[N/A]` voids the
  query *before* any sampler starts. The stand-in now answers a one-shot query
  and a stream separately, which is also what a real driver does when a board
  drops out of a stream it was answering a moment ago.
- Timing is polled, never slept: a test tuned to one machine's speed fails on
  another for no reason anybody can act on. Both files were run repeatedly to
  check for flakiness before being committed.

### The hardware detection is exercised on hardware this machine is not

- `machine.py` **72% → 98%** and `capability.py` **78% → 87%**. Almost every
  branch in the detection is one that does *not* match — a processor nobody has
  catalogued, two different accelerators in one box, a machine that cannot be
  inspected at all — and none of those happen on a developer's laptop or a cloud
  runner, so the paths that matter most to somebody with unusual hardware were
  the least exercised.
- Nothing is mocked. Each test supplies the dictionary `hardware_info()` really
  returns, **taken from a live call** rather than imagined, and lets the real
  code read it. The first draft passed GPU names as strings; the code reads
  mappings, and the failure said so.
- A graphics hwmon tree is built the way the kernel publishes one, which also
  lifts the capability probe: a counter that reads, a sensor this user may not
  read, and a node belonging to a fan rather than a card. **Absent and blocked
  are different answers** — collapsing them would send somebody looking for
  hardware they already have.
- **A comment in the detection stated a mechanism that does not exist.** It said
  an overlay could remove the generic processor rows, and the branch below it
  was written for that. An overlay merges *over* the bundled catalogue: it can
  add or override a row, never delete one. The comment now says what is true,
  the branch is reached the one way it is reachable, and a contract test keeps
  the fallback rows in the catalogue — they are easy to delete while tidying,
  because nothing names them except the fallback that needs them.

### The refresh commands are tested on the half a user sees

- `commands.py` was at **73%**, not the 76% the assessment claimed, and the
  shadow was concentrated in the four handlers added that same afternoon:
  `_refresh_embodied` at 46% covered, `catalog_refresh` at 73%,
  `_check_timezones` at 79%. The fetching was stubbed and tested; **what a user
  actually reads was not**.
- Nine tests cover it now: what each command prints, every refusal it names, the
  cross-check URL the tariff refresh has to carry, the `Read-only` line that
  stops a reader believing the catalogue already moved, and the deliberate
  second step that writes. 73% → **83%**.
- Among them the one case where a refresh *fails* rather than reports: a
  timezone list that did not check out is not stamped, and the test asserts the
  file is byte-identical afterwards.
- **`commands.py` was not split**, and that is a decision rather than an
  omission. The four files split this week each mixed unrelated concerns; this
  one has a single concern — implement the verbs — and is long because the CLI
  has many. Splitting a flat list of twenty-two handlers would add import
  plumbing and a fifth round of patch-target churn for no behavioural gain. The
  coverage was the defect; the length is cosmetic.

### The refresh is four sources, so it is four modules

- `refresh.py` reached 1,213 lines, from 424 that morning. The three sources
  added over a single afternoon each went in without anyone looking at what the
  file was becoming — named in the previous release rather than quietly fixed,
  and fixed here.
- Four modules, one per source: `carbon` (Ember), `tariffs` (the price and its
  Eurostat cross-check), `timezones` (IANA), `embodied` (processor footprints).
  They share **nothing**: no constant, no helper, no record type. Each holds the
  same three things — what the source said, how to ask it, how to write the
  answer into a catalogue — and each carries the reason it is that source rather
  than a more convenient one.
- **The witness was blind on its first try**, and that is the part worth keeping.
  Sabotaging the chip-name comparison — dropping the underscore from the
  characters it ignores — changed nothing the baseline measured, because none of
  the probe cases used an underscore. The probe was widened to exercise each
  separator on its own, and only then did it catch the sabotage. A baseline that
  cannot fail proves nothing, and this one could not until it was asked to.
- Eleven patch targets routed again, the fourth time in three refactors: a test
  importing the package cannot patch a binding that lives in a submodule.
- Longest file in the package is now `html.py` at 1,168.

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

## 1.3.0 — 2026-10-02

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
- `power_by_domain()` draws that split in the HTML report, the only figure in
  one of these reports that is measured rather than modelled, each bar read off
  its own counter. The donut of estimated shares this replaces would have been easier to
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
