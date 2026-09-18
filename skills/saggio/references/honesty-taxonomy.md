# The honesty taxonomy

Every number in a cost model carries exactly one status.

| Status | Means | Write it when |
|---|---|---|
| `measured` | A counter on the machine said so. | A wattmeter, an energy counter, a clock, or a log produced this figure on the target system. |
| `estimated` | A sourced formula or a published figure said so. | It came from a datasheet, a regulator's table, a provider's report, or arithmetic over other quantities. |
| `placeholder` | The field is held open. It is not a number. | You want the shape of the model to show that this dimension exists, before anyone has filled it in. |
| `TODO` | A human has to supply it. | It cannot be established from anything available, and a person has to go and find out. |

## The weakest-link rule

A derived value may never claim to be better founded than the worst of the numbers
it came from.

A runtime you measured, multiplied by a power draw you read off a datasheet, gives
an energy figure that is `estimated`. Not `measured`, because half of it was not.
Multiply that by a grid intensity from a national table and the carbon figure is
`estimated` too. Measure the power as well and both rise to `measured` on their
own, because the rule is computed rather than declared.

This is enforced, not suggested. A quantity names its inputs:

```yaml
carbon:
  value: 0.0014
  unit: "gCO2e"
  status: "estimated"
  derived_from: ["scenarios[0].costs.energy", "assumptions.grid_carbon_intensity"]
```

and the validator follows those paths and compares. A value claiming more than its
inputs allow is an error, not a warning, because the central proposition of this
package is that a number says how far it can be trusted.

## The mistakes that matter

**Writing a plausible default.** The most common failure, and the most damaging,
because the result looks exactly like a checked number. "We have to put something
there" is the reasoning this whole taxonomy exists to refuse. Put a `TODO` there,
with a sentence saying what would close it.

**Writing zero for unknown.** "We do not know what this emits" and "this emits
nothing" are different statements, and the second one is a claim. An unresolved
country gives a `TODO` carbon figure, never a zero.

**Calling a projection a measurement.** A measured slice projected to a whole run
is `estimated`. A runtime scaled onto another accelerator is `estimated` at best.
Both are inferences about something that has not happened.

**Calling a datasheet a measurement.** A nameplate wattage is what the vendor says
the part can draw, not what your machine drew. That is `estimated`, and the note
should say it is a nameplate figure.

**Letting a language model supply a number.** A figure produced by a model is one
nobody can check. A local model may say what shape of work a repository does; it
may not say how long it takes or what it costs.

**Quoting a figure without its status.** When you report a number to a user, report
its status with it. "An estimated 0.0014 gCO2e per request" is honest. "0.0014
gCO2e per request" is a claim the model never made.

## The overall status of a model

A model is worth its weakest number, wherever that number is hiding. That is the
sentence a report leads with, and the one to lead with when summarising a model to
somebody: not the impressive figures, the weakest one.

## Provenance, beside the status

A status says how well founded a number is. It cannot say *whose* number it is,
and for a sourced figure that matters: a price read from a vendor's own price API
and the same price copied out of a community table are both, correctly,
`estimated`. So a quantity may also carry a `source_kind`:

| `source_kind` | Meaning |
|---|---|
| `stated` | A human asserted it. |
| `first-party` | Read from the vendor's own machine-readable source. |
| `aggregator` | Read from somebody else's transcription of that. |

It is ordered, and `saggio diff` fails when it weakens, exactly as it fails when
a status weakens. A number that came from the vendor last month and from a
community table this month is the same number and a worse citation.
