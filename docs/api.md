# The library

Everything `import saggio` gives you, grouped the way `__all__` groups it. This
page is in English only, because it is the docstrings and the docstrings are in
English. [`LISEZMOI.md`](LISEZMOI.md) is the French map of the documentation.

**This page is generated.** The names come from `__all__`, the summaries are the
first line of each object's own docstring, and `docs/sync_api.py --check` fails
the build when the two have drifted. Edit the docstring, then run
`python docs/sync_api.py`.

The command line reaches nothing the library does not, so anything the `saggio`
command can do is reachable from here. [`../EXAMPLES.md`](../EXAMPLES.md) shows
these in use; the full parameter documentation is in the docstrings themselves,
which `help()` will show you.


## The model and its rules

| Name | What it is for |
|---|---|
| `CostModel` | A parsed cost model, with the context needed to read and write it. |
| `Quantity` | One number with its unit, honesty status, provenance, and derivation. |
| `Dimension` | One measurable axis of the cost of running a unit of work. |
| `DimensionRegistry` | An ordered collection of the dimensions one cost model reports. |
| `CANONICAL_DIMENSIONS` | `money`, `time`, `energy`, `carbon`, `embodied_carbon`, `water` |
| `SCHEMA_VERSION` | `'2.1'` |
| `MEASURED` | `'measured'` |
| `ESTIMATED` | `'estimated'` |
| `PLACEHOLDER` | `'placeholder'` |
| `TODO` | `'TODO'` |
| `weakest(*statuses: 'str \| None') -> 'str \| None'` | Return the weakest of several statuses, ignoring the missing ones. |
| `validate(model: 'CostModel \| dict[str, Any]') -> 'Report'` | Validate a cost model and return the accumulated verdict. |
| `overall_status(model: 'CostModel \| dict[str, Any]') -> 'str \| None'` | Return the weakest status anywhere in a model. |
| `Report` | An accumulated verdict: every issue a check found, in order. |
| `Issue` | One thing a check found, at one place in the model. |


## Facts about the world

| Name | What it is for |
|---|---|
| `Catalog` | One catalogue: its bundled rows, overlaid with the user's own. |
| `add_row(kind: 'str', row: 'dict[str, Any]', *, overlay: 'Path \| None' = None) -> 'Path'` | Add a row to the user's overlay, refusing one with no provenance. |
| `stale_report(*, overlay: 'Path \| None' = None, today: 'date \| None' = None) -> 'dict[str, list[str]]'` | Return the keys of every catalogue row that is past its refresh date. |


## Estimation

| Name | What it is for |
|---|---|
| `DeploymentContext` | The resolved answer to "where does this run, and what does that cost". |
| `MachineProfile` | What the tool knows about the machine a measurement was taken on. |
| `detect_machine(*, overlay: 'Path \| None' = None) -> 'MachineProfile'` | Inspect the local machine and match it against the power catalogue. |
| `node_power(*, cpu_key: 'str \| None', physical_cores: 'int', memory_gb: 'float', gpu_key: 'str \| None' = None, accelerator_count: 'int' = 0, usage_factor: 'float \| None' = None, overlay_catalog: 'Catalog \| None' = None) -> 'Quantity'` | Estimate what a machine draws under load, from its parts. |
| `it_energy_from_runtime(runtime: 'Quantity', power: 'Quantity') -> 'Quantity'` | Return the energy the machine itself draws over a runtime. |
| `energy_from_runtime(runtime: 'Quantity', power: 'Quantity', pue: 'Quantity') -> 'Quantity'` | Return facility energy directly from runtime, power, and overhead. |
| `carbon_from_energy(energy: 'Quantity', intensity: 'Quantity') -> 'Quantity'` | Return the grid emissions for an amount of facility energy. |
| `water_from_energy(it_energy: 'Quantity', effectiveness: 'Quantity') -> 'Quantity'` | Return the cooling water for an amount of machine energy. |
| `money_from_energy(energy: 'Quantity', price: 'Quantity') -> 'Quantity'` | Return what an amount of facility energy costs. |
| `tree_months(carbon: 'Quantity') -> 'Quantity'` | Restate a carbon figure as months of sequestration by one mature tree. |
| `car_km(carbon: 'Quantity', region: 'str' = 'EU') -> 'Quantity'` | Restate a carbon figure as kilometres driven in an average passenger car. |
| `flight_fraction(carbon: 'Quantity', route: 'str' = 'paris-london') -> 'Quantity'` | Restate a carbon figure as a fraction of a reference flight. |
| `equivalences(carbon: 'Quantity') -> 'dict[str, Quantity]'` | Return the full set of restatements for one carbon figure. |
| `Observation` | One run, of a known size, that took a known time. |
| `Projection` | The result of a projection: a number, its method, and its limits. |
| `ScalingFit` | A measured power law, or a refusal to report one. |
| `embodied_carbon(*, embodied: 'Quantity', lifetime: 'Quantity', runtime: 'Quantity', resource_share: 'Quantity \| None' = None) -> 'Quantity'` | Return the manufacturing carbon one unit of work is answerable for. |
| `fit_power_law(observations: 'list[Observation] \| tuple[Observation, ...]', *, minimum_r_squared: 'float' = 0.95, status: 'str' = 'measured') -> 'ScalingFit'` | Fit ``seconds = a * size ** b`` and say how well it fits. |
| `project_to_completion(measured: 'Quantity', *, fraction: 'float', scaling: 'ScalingFit \| None' = None) -> 'Projection'` | Project a measured slice of a run to the whole of it. |
| `software_carbon_intensity(*, operational: 'Quantity', embodied: 'Quantity') -> 'Quantity'` | Return the SCI score: operational plus embodied, per unit of work. |
| `project_to_machine(*, runtime: 'Quantity', source_key: 'str', target_key: 'str', precision: 'str' = 'bf16', compute_bound: 'bool \| None' = None, overlay_catalog: 'Catalog \| None' = None) -> 'Projection'` | Project a runtime measured on one accelerator onto another. |
| `project_to_processor(*, runtime: 'Quantity', source_key: 'str', target_key: 'str', parallelism: 'float \| None' = None, overlay_catalog: 'Catalog \| None' = None) -> 'Projection'` | Project a runtime measured on one processor onto another. |


## Reading and running a repository

| Name | What it is for |
|---|---|
| `RepositoryReading` | Everything reading the repository, without running it, established. |
| `read_repository(path: 'str \| Path', *, overlay: 'Path \| None' = None) -> 'RepositoryReading'` | Read a repository and return everything the static pass established. |
| `SliceResult` | What happened when a slice of the repository was run. |
| `run_slice(command: 'Sequence[str]', *, working_directory: 'str \| Path \| None' = None, timeout_seconds: 'float' = 300.0, fraction_completed: 'float \| None' = None, profile: 'bool' = True, baseline_seconds: 'float' = 1.0) -> 'SliceResult'` | Run a command, time it, measure what it drew, and see where the time went. |


## The whole job

| Name | What it is for |
|---|---|
| `AuditOptions` | What the caller wants the audit to do. |
| `AuditResult` | The model an audit produced, and the evidence behind it. |
| `audit(path: 'str \| Path', *, options: 'AuditOptions \| None' = None, origin: 'str \| None' = None) -> 'AuditResult'` | Build a cost model for a repository. |
| `audit_git_url(url: 'str', *, options: 'AuditOptions \| None' = None) -> 'AuditResult'` | Clone a public repository into a temporary directory and audit it. |
| `repository_name(url: 'str') -> 'str'` | Return the repository's own name, as its clone URL spells it. |
| `Fold` | What folding a measurement into a model did, or why it did nothing. |
| `compare(before: 'CostModel \| dict[str, Any]', after: 'CostModel \| dict[str, Any]', *, threshold_percent: 'float' = 10.0) -> 'Comparison'` | Compare two cost models quantity by quantity. |
| `fold_measurement(model: 'CostModel', *, seconds: 'float', units: 'float' = 1.0, power: 'PowerReading \| None' = None, scenario: 'str \| None' = None, command: 'str \| None' = None) -> 'Fold'` | Write a measured runtime into a model and recompute what follows from it. |
| `Comparison` | Everything that differs between two cost models. |
| `Change` | One quantity that is not the same in both models. |


## Reports

| Name | What it is for |
|---|---|
| `render_markdown(model: 'CostModel \| dict[str, Any]') -> 'str'` | Render a cost model as a Markdown report. |
| `render_html(model: 'CostModel \| dict[str, Any]', *, overlay: 'Any' = None) -> 'str'` | Render a cost model as one self-contained HTML page. |
| `render_office(model: 'CostModel \| dict[str, Any]', output: 'str \| Path', *, output_format: 'str' = 'docx', reference_document: 'str \| Path \| None' = None) -> 'Path'` | Render a cost model to Word or PDF. |
| `render_dashboard(models: 'list[CostModel \| dict[str, Any]]') -> 'str'` | Render several cost models as one self-contained HTML page. |
| `template_text(name: 'str' = 'minimal') -> 'str'` | Return a template's YAML text. |
| `template_mapping(name: 'str' = 'minimal') -> 'dict[str, Any]'` | Return a template already parsed. |
| `template_names() -> 'tuple[str, ...]'` | Return the available template names. |
| `TEMPLATES` | `minimal`, `annotated` |
| `DEFAULT_TEMPLATE` | `'minimal'` |

---

Generated from the docstrings by `docs/sync_api.py`. saggio 1.4.1.
