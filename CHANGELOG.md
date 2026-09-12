# Changelog

This project follows [semantic versioning](https://semver.org/). The cost-model
schema is versioned separately, in its own `schema_version` field: within a major
line it only grows, so a model written today keeps validating against every later
release of that line.

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
