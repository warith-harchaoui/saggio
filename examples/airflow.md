# Cost of running airflow

**This model is only as good as its weakest number, which is `TODO`.** A human must supply this before the model can be trusted.

Last updated 2026-09-14. Schema 2.1.

## Honesty

| Status | Count | Meaning |
|---|---|---|
| `estimated` | 4 | Computed from a sourced assumption or a published formula. |
| `TODO` | 51 | A human must supply this before the model can be trusted. |

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
| Water | not known | `TODO` | `assumptions.machine_energy`, `assumptions.water_usage_effectiveness` | Needs the machine's energy and a published water usage effectiveness. |

## What the numbers rest on

| Assumption | Value | Status | Provenance | Notes |
|---|---|---|---|---|
| `power_draw` | 83.76 W | `estimated` | [source](https://doi.org/10.1002/advs.202100707), read 2026-09-12 | Nameplate sum, Green Algorithms method: 12 cores x 4.0 W + 96 GB x 0.3725 W/GB |
| `pue` | 1.5 ratio | `estimated` | [source](https://www.uptimeinstitute.com/resources/research-and-reports/uptime-institute-global-data-center-survey-results-2024), read 2026-09-12 | Power usage effectiveness published by On-premises. |
| `electricity_price` | 0.24 USD | `estimated` | [source](https://ember-energy.org/data/electricity-data-explorer/), read 2026-09-12 | Indicative tariff for France. |
| `grid_carbon_intensity` | 56 gCO2e/kWh | `estimated` | [source](https://ember-energy.org/data/electricity-data-explorer/), read 2026-09-12 | Annual average for France. |
| `water_usage_effectiveness` | not known | `TODO` | — | On-premises publishes no water usage effectiveness. Leave this open rather than inventing a figure. |
| `machine_energy` | not known | `TODO` | — | Needs both a runtime and an average power draw. |

## Services this code pays for

Prices are not copied into this model. An API price copied today is wrong by next quarter, so the report says where the current one lives and leaves the figure open until somebody reads it.

| Service | Found at | Evidence | Per unit | Where to price it |
|---|---|---|---|---|
| Anthropic API | `providers/anthropic/src/airflow/providers/anthropic/operators/agent.py:36` | `from anthropic.types.beta import BetaManagedAgentsSession` | not known | [prices](https://www.anthropic.com/pricing) |
| AWS (boto3) | `dev/breeze/src/airflow_breeze/utils/publish_docs_to_s3.py:26` | `import boto3` | not known | [prices](https://aws.amazon.com/pricing/) |
| Microsoft Azure | `providers/databricks/src/airflow/providers/databricks/hooks/databricks_base.py:418` | `from azure.identity import ClientSecretCredential, ManagedIdentityCredential` | not known | [prices](https://azure.microsoft.com/en-us/pricing/) |
| Cohere API | `providers/cohere/src/airflow/providers/cohere/operators/rerank.py:28` | `from cohere.core.request_options import RequestOptions` | not known | [prices](https://cohere.com/pricing) |
| Google Cloud | `providers/google/src/airflow/providers/google/cloud/sensors/pubsub.py:26` | `from google.cloud import pubsub_v1` | not known | [prices](https://cloud.google.com/pricing) |
| Google Gemini API | `providers/google/src/airflow/providers/google/cloud/hooks/gen_ai.py:26` | `from google import genai` | not known | [prices](https://ai.google.dev/pricing) |
| OpenAI API | `providers/openai/src/airflow/providers/openai/hooks/openai.py:26` | `from openai import OpenAI` | not known | [prices](https://openai.com/api/pricing/) |
| SendGrid API | `providers/sendgrid/src/airflow/providers/sendgrid/utils/emailer.py:28` | `import sendgrid` | not known | [prices](https://sendgrid.com/en-us/pricing) |

## Models this code calls

A rate is not a cost. These are what the vendor charges per unit; how many of those units one unit of work spends is the open half, and reading the code cannot establish it.

### `claude-sonnet-4-6` — found at `dev/skill-evals/eval.py:301`

_No published rate was found for this model._

### `claude-opus-4-8` — found at `providers/anthropic/src/airflow/providers/anthropic/example_dags/example_batch.py:33`

_No published rate was found for this model._

### `openai:gpt-5.6-sol` — found at `providers/common/ai/src/airflow/providers/common/ai/get_provider_info.py:144`

_No published rate was found for this model._

### `azure:gpt-4o` — found at `providers/common/ai/src/airflow/providers/common/ai/get_provider_info.py:165`

_No published rate was found for this model._

### `bedrock:us.anthropic.claude-opus-4-5` — found at `providers/common/ai/src/airflow/providers/common/ai/get_provider_info.py:190`

_No published rate was found for this model._

### `google-cloud:gemini-2.0-flash` — found at `providers/common/ai/src/airflow/providers/common/ai/get_provider_info.py:255`

_No published rate was found for this model._

### `openai:gpt-4o` — found at `providers/common/ai/src/airflow/providers/common/ai/get_provider_info.py:341`

_No published rate was found for this model._

### `embed-english-v3.0` — found at `providers/common/ai/src/airflow/providers/common/ai/example_dags/example_llamaindex_hook.py:129`

_No published rate was found for this model._

### `anthropic:claude-haiku-4-5-20251001` — found at `providers/common/ai/src/airflow/providers/common/ai/example_dags/example_llm_retry_policy.py:25`

_No published rate was found for this model._

### `gpt-test` — found at `scripts/tests/ci/prek/test_skill_eval.py:79`

_No published rate was found for this model._

### `text-embedding-3-small` — found at `providers/openai/tests/system/openai/example_openai.py:81`

_No published rate was found for this model._

### `gpt-4o-mini` — found at `providers/openai/tests/system/openai/example_trigger_batch_operator.py:65`

_No published rate was found for this model._

### `test_model` — found at `providers/openai/tests/unit/openai/operators/test_openai.py:58`

_No published rate was found for this model._

### `text-embedding-ada-002-v2` — found at `providers/openai/tests/unit/openai/hooks/test_openai.py:102`

_No published rate was found for this model._

### `text-embedding-ada-002` — found at `providers/weaviate/tests/system/weaviate/example_weaviate_openai.py:77`

_No published rate was found for this model._

### `claude-haiku-4-5` — found at `providers/anthropic/tests/unit/anthropic/operators/test_batch.py:150`

_No published rate was found for this model._

### `test-model` — found at `providers/common/ai/tests/unit/common/ai/conftest.py:43`

_No published rate was found for this model._

### `test` — found at `providers/common/ai/tests/unit/common/ai/test_observability.py:105`

_No published rate was found for this model._

### `openai:gpt-5` — found at `providers/common/ai/tests/unit/common/ai/operators/test_agent.py:371`

_No published rate was found for this model._

### `gpt-5` — found at `providers/common/ai/tests/unit/common/ai/utils/test_logging.py:37`

_No published rate was found for this model._

### `gpt-x` — found at `providers/common/ai/tests/unit/common/ai/durable/test_task_state_store.py:118`

_No published rate was found for this model._

### `anthropic:claude-3-7-sonnet` — found at `providers/common/ai/tests/unit/common/ai/hooks/test_langchain.py:104`

_No published rate was found for this model._

### `anthropic:claude-opus-4-6` — found at `providers/common/ai/tests/unit/common/ai/hooks/test_pydantic_ai.py:151`

_No published rate was found for this model._

### `bedrock:us.anthropic.claude-v2` — found at `providers/common/ai/tests/unit/common/ai/hooks/test_pydantic_ai.py:195`

_No published rate was found for this model._

### `openai:llama3` — found at `providers/common/ai/tests/unit/common/ai/hooks/test_pydantic_ai.py:213`

_No published rate was found for this model._

### `badprovider:model` — found at `providers/common/ai/tests/unit/common/ai/hooks/test_pydantic_ai.py:490`

_No published rate was found for this model._

### `google:gemini-2.0-flash` — found at `providers/common/ai/tests/unit/common/ai/hooks/test_pydantic_ai.py:784`

_No published rate was found for this model._

### `text-embedding-3-large` — found at `providers/common/ai/tests/unit/common/ai/hooks/test_llamaindex.py:141`

_No published rate was found for this model._

### `gpt-4o` — found at `providers/common/ai/tests/unit/common/ai/hooks/test_llamaindex.py:161`

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
