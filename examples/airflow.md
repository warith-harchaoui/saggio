# Cost of running airflow

**This model is only as good as its weakest number, which is `TODO`.** A human must supply this before the model can be trusted.

Last updated 2026-10-01. Schema 2.1.

## Honesty

| Status | Count | Meaning |
|---|---|---|
| `estimated` | 4 | Computed from a sourced assumption or a published formula. |
| `TODO` | 82 | A human must supply this before the model can be trusted. |

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
| machine provenance | This describes the machine that ran the audit, not where the code runs. https://github.com/apache/airflow was cloned and read here. Replace the machine, the provider and the country with the ones it actually runs on before any number below means anything about this project. |

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
| `electricity_price` | 0.24 USD | `estimated` | [source](https://ember-energy.org/data/electricity-data-explorer/), read 2026-09-12 | Indicative tariff for France. |
| `grid_carbon_intensity` | 56 gCO2e/kWh | `estimated` | [source](https://ember-energy.org/data/electricity-data-explorer/), read 2026-09-12 | Annual average for France. |
| `water_usage_effectiveness` | not known | `TODO` | — | On-premises publishes no water usage effectiveness. Leave this open rather than inventing a figure. |
| `hardware_embodied_carbon` | not known | `TODO` | — | No accelerator was identified, so the carbon of building one is not this model's to carry. A processor's own footprint is not in the catalogue yet; it is excluded rather than assumed to be zero. |
| `hardware_lifetime` | not known | `TODO` | — | How long this hardware stays in service, which only you know. The published footprints are cradle-to-gate and exclude the use phase, so none of them states a lifespan. Reported figures cluster between three and six years; choosing within that range moves the embodied carbon by a factor of two, which is why this is asked rather than assumed. |
| `machine_energy` | not known | `TODO` | — | Needs both a runtime and an average power draw. |

## Services this code pays for

Prices are not copied into this model. An API price copied today is wrong by next quarter, so the report says where the current one lives and leaves the figure open until somebody reads it.

| Service | Found at | Evidence | Per unit | Where to price it |
|---|---|---|---|---|
| Anthropic API | `providers/anthropic/src/airflow/providers/anthropic/operators/agent.py:36` | `from anthropic.types.beta import BetaManagedAgentsSession` | not known | [prices](https://www.anthropic.com/pricing) |
| AWS (boto3) | `dev/breeze/src/airflow_breeze/utils/publish_docs_to_s3.py:26` | `import boto3` | not known | [prices](https://aws.amazon.com/pricing/) |
| Cohere API | `providers/cohere/src/airflow/providers/cohere/operators/rerank.py:28` | `from cohere.core.request_options import RequestOptions` | not known | [prices](https://cohere.com/pricing) |
| Google Cloud | `providers/google/src/airflow/providers/google/cloud/sensors/pubsub.py:27` | `from google.cloud import pubsub_v1` | not known | [prices](https://cloud.google.com/pricing) |
| Google Gemini API | `providers/google/src/airflow/providers/google/cloud/hooks/gen_ai.py:26` | `from google import genai` | not known | [prices](https://ai.google.dev/pricing) |
| OpenAI API | `providers/openai/src/airflow/providers/openai/hooks/openai.py:26` | `from openai import OpenAI` | not known | [prices](https://openai.com/api/pricing/) |
| SendGrid API | `providers/sendgrid/src/airflow/providers/sendgrid/utils/emailer.py:28` | `import sendgrid` | not known | [prices](https://sendgrid.com/en-us/pricing) |

## Models this code calls

A rate is not a cost. These are what the vendor charges per unit; how many of those units one unit of work spends is the open half, and reading the code cannot establish it.

### `claude-sonnet-4-6` — found at `dev/skill-evals/eval.py:301`

_No published rate was found for this model._

### `claude-opus-4-8` — found at `providers/anthropic/src/airflow/providers/anthropic/example_dags/example_batch.py:33`

_No published rate was found for this model._

### `openai:gpt-5` — found at `providers/common/ai/src/airflow/providers/common/ai/get_provider_info.py:155`

_No published rate was found for this model._

### `azure:gpt-5` — found at `providers/common/ai/src/airflow/providers/common/ai/get_provider_info.py:181`

_No published rate was found for this model._

### `bedrock:us.anthropic.claude-opus-4-5` — found at `providers/common/ai/src/airflow/providers/common/ai/get_provider_info.py:211`

_No published rate was found for this model._

### `google-cloud:gemini-2.5-flash` — found at `providers/common/ai/src/airflow/providers/common/ai/get_provider_info.py:281`

_No published rate was found for this model._

### `openai:gpt-5-mini` — found at `providers/common/ai/src/airflow/providers/common/ai/example_dags/example_llm_fallback.py:27`

_No published rate was found for this model._

### `anthropic:claude-haiku-4-5-20251001` — found at `providers/common/ai/src/airflow/providers/common/ai/example_dags/example_llm_fallback.py:33`

_No published rate was found for this model._

### `embed-english-v3.0` — found at `providers/common/ai/src/airflow/providers/common/ai/example_dags/example_llamaindex_hook.py:129`

_No published rate was found for this model._

### `typesafe:jev-1.13.0` — found at `providers/common/ai/src/airflow/providers/common/ai/example_dags/example_llm_branch.py:113`

_No published rate was found for this model._

### `anthropic:claude-sonnet-5` — found at `providers/common/ai/src/airflow/providers/common/ai/example_dags/example_llm_batch.py:109`

_No published rate was found for this model._

### `openai:gpt-4.1-mini` — found at `providers/common/ai/src/airflow/providers/common/ai/example_dags/example_llm_batch.py:170`

_No published rate was found for this model._

### `old` — found at `scripts/tests/ci/prek/test_check_ui_field_behaviour_matches_hook.py:119`

_No published rate was found for this model._

### `new` — found at `scripts/tests/ci/prek/test_check_ui_field_behaviour_matches_hook.py:120`

_No published rate was found for this model._

### `gpt-test` — found at `scripts/tests/ci/prek/test_skill_eval.py:79`

_No published rate was found for this model._

### `text-embedding-3-small` — found at `providers/openai/tests/system/openai/example_openai.py:81`

_No published rate was found for this model._

### `gpt-6-astra` — found at `providers/openai/tests/system/openai/example_openai_agent.py:39`

_No published rate was found for this model._

### `gpt-4o-mini` — found at `providers/openai/tests/system/openai/example_trigger_batch_operator.py:65`

_No published rate was found for this model._

### `test_model` — found at `providers/openai/tests/unit/openai/operators/test_openai.py:70`

_No published rate was found for this model._

### `text-embedding-ada-002-v2` — found at `providers/openai/tests/unit/openai/hooks/test_openai.py:105`

_No published rate was found for this model._

### `text-embedding-ada-002` — found at `providers/weaviate/tests/system/weaviate/example_weaviate_openai.py:77`

_No published rate was found for this model._

### `claude-haiku-4-5` — found at `providers/anthropic/tests/unit/anthropic/operators/test_batch.py:150`

_No published rate was found for this model._

### `test-model` — found at `providers/common/ai/tests/unit/common/ai/conftest.py:88`

_No published rate was found for this model._

### `test` — found at `providers/common/ai/tests/unit/common/ai/test_observability.py:109`

_No published rate was found for this model._

### `gpt-4o` — found at `providers/common/ai/tests/unit/common/ai/operators/test_agent.py:2814`

_No published rate was found for this model._

### `jev-1.13.0` — found at `providers/common/ai/tests/unit/common/ai/operators/test_llm.py:381`

_No published rate was found for this model._

### `claude-sonnet-5` — found at `providers/common/ai/tests/unit/common/ai/operators/test_llm_branch.py:689`

_No published rate was found for this model._

### `gpt-5` — found at `providers/common/ai/tests/unit/common/ai/operators/test_llm_batch.py:149`

_No published rate was found for this model._

### `gpt-x` — found at `providers/common/ai/tests/unit/common/ai/durable/test_task_state_store.py:118`

_No published rate was found for this model._

### `anthropic:claude-opus-5` — found at `providers/common/ai/tests/unit/common/ai/batch/test_anthropic.py:205`

_No published rate was found for this model._

### `someone-elses-model` — found at `providers/common/ai/tests/unit/common/ai/batch/test_anthropic.py:241`

_No published rate was found for this model._

### `anthropic:claude-3-opus` — found at `providers/common/ai/tests/unit/common/ai/batch/test_openai.py:287`

_No published rate was found for this model._

### `fake:model` — found at `providers/common/ai/tests/unit/common/ai/batch/test_results.py:241`

_No published rate was found for this model._

### `anthropic:claude-3-7-sonnet` — found at `providers/common/ai/tests/unit/common/ai/hooks/test_langchain.py:109`

_No published rate was found for this model._

### `other-model` — found at `providers/common/ai/tests/unit/common/ai/hooks/test_langchain.py:282`

_No published rate was found for this model._

### `openai:gpt-4o` — found at `providers/common/ai/tests/unit/common/ai/hooks/test_langchain.py:304`

_No published rate was found for this model._

### `openai:gpt-5.6-sol` — found at `providers/common/ai/tests/unit/common/ai/hooks/test_pydantic_ai.py:121`

_No published rate was found for this model._

### `anthropic:claude-opus-4-6` — found at `providers/common/ai/tests/unit/common/ai/hooks/test_pydantic_ai.py:186`

_No published rate was found for this model._

### `bedrock:us.anthropic.claude-v2` — found at `providers/common/ai/tests/unit/common/ai/hooks/test_pydantic_ai.py:230`

_No published rate was found for this model._

### `openai:llama3` — found at `providers/common/ai/tests/unit/common/ai/hooks/test_pydantic_ai.py:248`

_No published rate was found for this model._

### `foo` — found at `providers/common/ai/tests/unit/common/ai/hooks/test_pydantic_ai.py:383`

_No published rate was found for this model._

### `openai:gpt-4` — found at `providers/common/ai/tests/unit/common/ai/hooks/test_pydantic_ai.py:419`

_No published rate was found for this model._

### `gpt-4` — found at `providers/common/ai/tests/unit/common/ai/hooks/test_pydantic_ai.py:427`

_No published rate was found for this model._

### `gemini-2.5-flash` — found at `providers/common/ai/tests/unit/common/ai/hooks/test_pydantic_ai.py:446`

_No published rate was found for this model._

### `us.anthropic.claude-opus-4-6-v1:0` — found at `providers/common/ai/tests/unit/common/ai/hooks/test_pydantic_ai.py:468`

_No published rate was found for this model._

### `bedrock:us.anthropic.claude-opus-4-6-v1:0` — found at `providers/common/ai/tests/unit/common/ai/hooks/test_pydantic_ai.py:490`

_No published rate was found for this model._

### `google-vertex:gemini-2.5-flash` — found at `providers/common/ai/tests/unit/common/ai/hooks/test_pydantic_ai.py:564`

_No published rate was found for this model._

### `openi:gpt-5` — found at `providers/common/ai/tests/unit/common/ai/hooks/test_pydantic_ai.py:595`

_No published rate was found for this model._

### `groq:llama-4` — found at `providers/common/ai/tests/unit/common/ai/hooks/test_pydantic_ai.py:616`

_No published rate was found for this model._

### `gpt-5-nano` — found at `providers/common/ai/tests/unit/common/ai/hooks/test_pydantic_ai.py:737`

_No published rate was found for this model._

### `claude-opus-4-5` — found at `providers/common/ai/tests/unit/common/ai/hooks/test_pydantic_ai.py:850`

_No published rate was found for this model._

### `anthropic:claude-1` — found at `providers/common/ai/tests/unit/common/ai/hooks/test_pydantic_ai.py:1111`

_No published rate was found for this model._

### `anthropic:claude-2` — found at `providers/common/ai/tests/unit/common/ai/hooks/test_pydantic_ai.py:1114`

_No published rate was found for this model._

### `openai:nonexistent-model` — found at `providers/common/ai/tests/unit/common/ai/hooks/test_pydantic_ai.py:1406`

_No published rate was found for this model._

### `azure:gpt-4o` — found at `providers/common/ai/tests/unit/common/ai/hooks/test_pydantic_ai.py:1473`

_No published rate was found for this model._

### `google:gemini-2.5-flash` — found at `providers/common/ai/tests/unit/common/ai/hooks/test_pydantic_ai.py:1736`

_No published rate was found for this model._

### `custom-value` — found at `providers/common/ai/tests/unit/common/ai/hooks/test_llamaindex.py:185`

_No published rate was found for this model._

### `text-embedding-3-large` — found at `providers/common/ai/tests/unit/common/ai/hooks/test_llamaindex.py:213`

_No published rate was found for this model._

### `base` — found at `providers/google/tests/system/google/cloud/translate/example_translate.py:49`

_No published rate was found for this model._

### `provisioned_model_arn` — found at `providers/amazon/tests/unit/amazon/aws/sensors/test_bedrock.py:94`

_No published rate was found for this model._

### `model_name` — found at `providers/amazon/tests/unit/amazon/aws/operators/test_sagemaker_model.py:77`

_No published rate was found for this model._

### `s3://your-bucket-name/model.tar.gz` — found at `providers/amazon/tests/unit/amazon/aws/operators/test_sagemaker_model.py:91`

_No published rate was found for this model._

### `test_model_arn` — found at `providers/amazon/tests/unit/amazon/aws/operators/test_bedrock.py:531`

_No published rate was found for this model._

### `rerank-v3.5` — found at `providers/cohere/tests/unit/cohere/operators/test_rerank.py:37`

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
