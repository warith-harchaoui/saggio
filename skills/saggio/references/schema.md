# The cost-model file

Schema 2.0. A plain YAML mapping, so it diffs, reviews in a pull request, and reads
without this package installed.

## A quantity

Anywhere a number appears, it appears as one of these:

```yaml
electricity_price:
  value: 0.24                                   # or null when it is not known
  unit: "USD/kWh"
  currency: "USD"                               # ISO 4217, for money only
  status: "estimated"                           # measured | estimated | placeholder | TODO
  source_url: "https://ember-energy.org/..."    # where it was read
  retrieved_date: "2026-09-13"                  # when it was read
  derived_from: ["a.path", "another.path"]      # what it was computed from
  notes: "Indicative French tariff."
```

Only `value` and `status` are always present. **A mapping with a `value` key is a
quantity**, wherever it sits, and a number outside a quantity is an error the
validator reports by path.

## The blocks

```yaml
schema_version: "2.0"
date_updated: "2026-09-13"

project:
  name: "example-service"

unit_of_work:
  name: "one inference on a median-sized request"
  description: >-
    Precise enough that two people would count the same way.
  status: "placeholder"
  out_of_scope:
    - "Training and fine-tuning."

deployment:
  provider: "on-prem"              # a providers catalogue key
  instance_type: "node-1x-h100"    # an instances catalogue key
  country: "FR"                    # ISO 3166-1 alpha-2
  country_provenance: "Stated by the maintainer."

dimensions:                        # optional, beyond the canonical five
  - key: "egress"
    label: "Network egress"
    unit: "GB"
    description: "Bytes leaving the datacenter per request."
    higher_is_worse: true          # false when more is better
    is_money: false

assumptions:                       # quantities everything else rests on
  power_draw: {...}
  pue: {...}
  electricity_price: {...}
  grid_carbon_intensity: {...}
  water_usage_effectiveness: {...}
  machine_energy: {...}

external_services:
  - key: "openai"
    detected_at: "app/handlers.py:14"
    evidence: "from openai import OpenAI"
    pricing_source_url: "https://openai.com/api/pricing/"
    price_per_unit: {...}

scenarios:
  - name: "default"
    description: "One request, model loaded, no batching."
    runtime: {...}
    costs:                         # keyed by dimension
      money: {...}
      time: {...}
      energy: {...}
      carbon: {...}
      water: {...}
      egress: {...}

projections:
  whole_run: {...}
  on_other_hardware: {...}

analysis: {...}                    # what reading the code established
measurement: {...}                 # how a measurement was taken

exclusions:
  - "Making the hardware."

provenance_rules:
  - "A derived value names its inputs and never outranks the weakest of them."
```

## The canonical dimensions

`money` (a currency), `time` (s), `energy` (kWh), `carbon` (gCO2e), `water` (L). A
project adds its own in the `dimensions` block and then uses the key in `costs`.
The validator, both reports, and the drift gate pick it up with no change to the
package.

## Rules the validator enforces

- Every number lives in a quantity. A bare number anywhere is an error, except at a
  short list of structural paths such as core counts and exit codes.
- Every `derived_from` path resolves to a quantity in the same model.
- No derived value outranks its weakest input.
- A value on a money dimension carries an ISO 4217 currency.
- A `measured` or `estimated` status carries a number; a `placeholder` or `TODO`
  does not.
- No cost is negative.
- An estimate in `assumptions` that was read somewhere carries a `source_url`
  (a warning), and its `retrieved_date` is watched for staleness.
- Within a major line the schema only grows. A newer major is refused rather than
  misread.

Warnings never fail a model. A model that admits it is incomplete is being honest.
