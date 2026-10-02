# Cost of running xberg

**This model is only as good as its weakest number, which is `TODO`.** A human must supply this before the model can be trusted.

Last updated 2026-10-02. Schema 2.1.

## Honesty

| Status | Count | Meaning |
|---|---|---|
| `estimated` | 4 | Computed from a sourced assumption or a published formula. |
| `TODO` | 54 | A human must supply this before the model can be trusted. |

## One unit of work

**one request handled end to end**

Proposed from the repository's shape, which reads as service. Confirm or replace it: every number below is per one of these, so the whole model means whatever this sentence means.

## Where it runs

|  |  |
|---|---|
| provider | on-prem |
| country | FR |
| country provenance | Stated by the caller. |
| operating system | darwin |
| logical cores | 12 |
| physical cores | 12 |
| cpu | Apple M2 Max |
| machine provenance | This describes the machine that ran the audit, not where the code runs. https://github.com/xberg-io/xberg was cloned and read here. Replace the machine, the provider and the country with the ones it actually runs on before any number below means anything about this project. |

## What one unit costs

### as-audited

One unit of work as this audit found it, on the machine it ran on.

| Dimension | Per unit | Status | Derived from | Notes |
|---|---|---|---|---|
| Money | not known | `TODO` | `scenarios[0].costs.energy`, `assumptions.electricity_price` | Needs the energy drawn and a price per kilowatt-hour. |
| Time | not known | `TODO` | `scenarios[0].runtime` | No run was measured. Measure the real command with `saggio measure`, or audit again with --run. |
| Energy | not known | `TODO` | `assumptions.machine_energy`, `assumptions.pue` | Needs the machine's own energy and the site's power usage effectiveness. |
| Carbon | not known | `TODO` | `scenarios[0].costs.energy`, `assumptions.grid_carbon_intensity` | Needs the energy drawn and the grid carbon intensity where it runs. |
| Embodied carbon | not known | `TODO` | `assumptions.hardware_embodied_carbon`, `assumptions.hardware_lifetime`, `scenarios[0].runtime` | No product carbon footprint is on file for this hardware, so the carbon of building it is open. Nobody has read one for this part; that is not the same as it having been free to build. Add an `embodied_kgco2e` to the catalogue row with the footprint's own URL and the date it was read. |
| Water | not known | `TODO` | `assumptions.machine_energy`, `assumptions.water_usage_effectiveness` | Needs the machine's energy and a published water usage effectiveness. |

## What the numbers rest on

| Assumption | Value | Status | Provenance | Notes |
|---|---|---|---|---|
| `power_draw` | 83.76 W | `estimated` | [source](https://doi.org/10.1002/advs.202100707), read 2026-09-12 | Nameplate sum, Green Algorithms method: 12 cores x 4.0 W + 96 GB x 0.3725 W/GB |
| `pue` | 1.5 ratio | `estimated` | [source](https://www.uptimeinstitute.com/resources/research-and-reports/uptime-institute-global-data-center-survey-results-2024), read 2026-09-12 | Power usage effectiveness published by On-premises. |
| `electricity_price` | 0.276 USD | `estimated` | [source](https://www.globalpetrolprices.com/electricity_prices/), read 2026-10-02 | Indicative tariff for France. Collected Q3 2026. |
| `grid_carbon_intensity` | 41.2 gCO2e/kWh | `estimated` | [source](https://api.ember-energy.org/v1/carbon-intensity/yearly), read 2026-10-02 | Annual average for France, data year 2025. |
| `water_usage_effectiveness` | not known | `TODO` | — | On-premises publishes no water usage effectiveness. Leave this open rather than inventing a figure. |
| `hardware_embodied_carbon` | not known | `TODO` | — | No product carbon footprint is on file for apple-m2-max. Add `embodied_kgco2e` to its catalogue row with the footprint's own URL and the date it was read; `saggio catalog add cpu` does the rest. |
| `hardware_lifetime` | not known | `TODO` | — | How long this hardware stays in service, which only you know. The published footprints are cradle-to-gate and exclude the use phase, so none of them states a lifespan. Reported figures cluster between three and six years; choosing within that range moves the embodied carbon by a factor of two, which is why this is asked rather than assumed. |
| `machine_energy` | not known | `TODO` | — | Needs both a runtime and an average power draw. |

## Services this code pays for

Prices are not copied into this model. An API price copied today is wrong by next quarter, so the report says where the current one lives and leaves the figure open until somebody reads it.

| Service | Found at | Evidence | Per unit | Where to price it |
|---|---|---|---|---|
| Google Gemini API | `tools/benchmark-harness/scripts/generate_markdown_gt.py:33` | `from google import genai` | not known | [prices](https://ai.google.dev/pricing) |

## Models this code calls

A rate is not a cost. These are what the vendor charges per unit; how many of those units one unit of work spends is the open half, and reading the code cannot establish it.

### `test` — found at `crates/xberg/src/llm/client.rs:733`

_No published rate was found for this model._

### `openai/gpt-4o` — found at `crates/xberg/src/llm/client.rs:752`

_No published rate was found for this model._

### `bedrock/anthropic.claude-3-sonnet-20240229-v1:0` — found at `crates/xberg/src/llm/client.rs:882`

_No published rate was found for this model._

### `vertex_ai/gemini-1.5-pro` — found at `crates/xberg/src/llm/client.rs:1764`

_No published rate was found for this model._

### `azure/gpt-4o` — found at `crates/xberg/src/llm/client.rs:1783`

_No published rate was found for this model._

### `anthropic/claude-sonnet-4-20250514` — found at `crates/xberg/src/llm/client.rs:2043`

_No published rate was found for this model._

### `openai/text-embedding-3-small` — found at `crates/xberg/src/embeddings/mod.rs:1420`

_No published rate was found for this model._

### `gpt-test` — found at `crates/xberg/src/core/split.rs:868`

_No published rate was found for this model._

### `test/model` — found at `crates/xberg/src/doctor/ocr.rs:551`

_No published rate was found for this model._

### `trusted/model` — found at `crates/xberg/src/mcp/format.rs:212`

_No published rate was found for this model._

### `caller/model` — found at `crates/xberg/src/mcp/format.rs:229`

_No published rate was found for this model._

### `openai/gpt-4o-mini` — found at `crates/xberg/src/mcp/server.rs:1326`

_No published rate was found for this model._

### `chunking-core-word-count-tokenizer` — found at `crates/xberg/src/chunking/core.rs:2059`

_No published rate was found for this model._

### `bert-base-uncased` — found at `crates/xberg/src/chunking/tokenizer_cache.rs:323`

_No published rate was found for this model._

### `model-a` — found at `crates/xberg/src/chunking/tokenizer_cache.rs:472`

_No published rate was found for this model._

### `chunking-yaml-word-count-tokenizer` — found at `crates/xberg/src/chunking/yaml_section.rs:752`

_No published rate was found for this model._

### `chunking-yaml-oversized-word-count-tokenizer` — found at `crates/xberg/src/chunking/yaml_section.rs:805`

_No published rate was found for this model._

### `example/deepseek-ocr` — found at `crates/xberg/src/candle_ocr/deepseek_ocr_backend.rs:484`

_No published rate was found for this model._

### `example/paddle` — found at `crates/xberg/src/candle_ocr/config.rs:380`

_No published rate was found for this model._

### `some-org/custom-paddleocr-vl` — found at `crates/xberg/src/candle_ocr/paddleocr_vl_backend.rs:490`

_No published rate was found for this model._

### `chunking-semantic-word-count-tokenizer` — found at `crates/xberg/src/chunking/semantic/mod.rs:591`

_No published rate was found for this model._

### `features-code-chunk-word-count-tokenizer` — found at `crates/xberg/src/core/pipeline/features.rs:1844`

_No published rate was found for this model._

### `safe` — found at `crates/xberg/src/core/config/request_security.rs:109`

_No published rate was found for this model._

### `org/splade` — found at `crates/xberg/src/core/config/sparse_embedding.rs:166`

_No published rate was found for this model._

### `{other}` — found at `crates/xberg/src/core/config/layout.rs:64`

_No published rate was found for this model._

### `cross-encoder/ms-marco-MiniLM-L6-v2` — found at `crates/xberg/src/core/config/reranker.rs:328`

_No published rate was found for this model._

### `example/model` — found at `crates/xberg/src/core/config/reranker.rs:400`

_No published rate was found for this model._

### `base` — found at `crates/xberg/src/core/config/transcription.rs:188`

_No published rate was found for this model._

### `org/colbert` — found at `crates/xberg/src/core/config/late_interaction.rs:186`

_No published rate was found for this model._

### `gpt-4o-mini` — found at `crates/xberg/src/core/config/extraction/env.rs:545`

_No published rate was found for this model._

### `gliner2_candle_bytes` — found at `crates/xberg-gliner/src/candle/model.rs:91`

_No published rate was found for this model._

### `stub/vlm` — found at `crates/xberg/tests/issue_55_image_ocr_result_fields.rs:70`

_No published rate was found for this model._

### `stub/model` — found at `crates/xberg/tests/issue_58_captioning_prepass_merge.rs:133`

_No published rate was found for this model._

### `v2` — found at `crates/xberg/tests/issue_1941_external_redaction_json_boundary.rs:52`

_No published rate was found for this model._

### `recovery-model` — found at `crates/xberg/src/extractors/pdf/ocr/tests.rs:9833`

_No published rate was found for this model._

### `synthetic-caption-model` — found at `crates/xberg/src/core/pipeline/tests.rs:1554`

_No published rate was found for this model._

### `synthetic-extraction-model` — found at `crates/xberg/src/core/pipeline/tests.rs:1582`

_No published rate was found for this model._

### `ignored` — found at `crates/xberg/src/core/config/processing/tests.rs:41`

_No published rate was found for this model._

### `sentence-transformers/all-MiniLM-L6-v2` — found at `crates/xberg/src/core/config/processing/tests.rs:171`

_No published rate was found for this model._

### `#),` — found at `crates/xberg/src/core/config/processing/tests.rs:177`

_No published rate was found for this model._

### `custom/model` — found at `crates/xberg/src/core/config/processing/tests.rs:199`

_No published rate was found for this model._

### `my-org/model` — found at `crates/xberg/src/core/config/processing/tests.rs:354`

_No published rate was found for this model._

## Not counted

- Making the hardware. Only the electricity to run it is counted.
- The people. Salaries, offices, and travel are out of scope.
- Idle capacity. This is the cost of one unit of work, not of being ready.

## Rules this model follows

- Every sourced value carries source_url and retrieved_date.
- A derived value names its inputs and never outranks the weakest of them.
- The country is stated by a human, never inferred from a developer's locale.

---

Generated by [saggio](https://github.com/warith-harchaoui/saggio).
