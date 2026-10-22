# Putting these numbers in a Greenhouse Gas (GHG) inventory

[🇫🇷 INVENTAIRE.md](INVENTAIRE.md) · 🇬🇧 English

This page is for the person who has to **file** the figures, not the one who
produced them. It says which line of a corporate greenhouse-gas inventory each
of this tool's numbers belongs on, what it gives an assurance provider, and —
the half that is actually useful — what it does not give you and will not
pretend to.

## The gap this closes

An engineering team hands a sustainability team a number: *"training this model
emits 40 kgCO2e."* Three questions follow immediately, and ordinarily none of
them has an answer.

1. **Whose emission is it?** Scope 2 if the machine is yours, scope 3 category 1
   if you rented it. Same code, same kilowatt-hour, different company reports it.
2. **How was it arrived at?** A measurement, a vendor figure, a published
   coefficient, or somebody's guess — and the four are not interchangeable in
   front of an auditor.
3. **Which method?** For scope 2 there are two, both required, and a grid
   average is only one of them.

This tool answers all three in the artefact itself, because it never produces a
number without them. `saggio scopes cost_of_running.yaml` prints the answers;
every rendered report carries them in a section of its own.

## Which scope, and why

The GHG Protocol settles the scope with one fact: **who buys the electricity and
owns the machine.** That fact is already in the model, as
`deployment.provider`, and the providers catalogue records it as `operated_by`.

| Where it runs | The electricity | The hardware |
|---|---|---|
| Your own server, your own laptop | **Scope 2** | **Scope 3, category 2** — capital goods |
| Amazon Web Services (AWS), Google Cloud Platform (GCP), Azure, Oracle Cloud Infrastructure (OCI), a graphics processing unit (GPU) cloud | **Scope 3, category 1** — purchased goods and services | **Scope 3, category 1** — same line |
| A provider nobody classified | *no scope* — stated as a question, never guessed | *no scope* |

Three things follow from that table, and each is a thing teams routinely get
wrong.

**Cloud compute is not your scope 2.** You bought a service. The electricity is
the provider's scope 2 and the hardware is its scope 3 category 2; both reach
you as one purchased service, in category 1. Filing it as scope 2 double-counts
it against your provider's own disclosure.

**Hardware you own is capital goods, not purchased goods.** The standard splits
category 1 from category 2 on whether the asset lasts more than a year. A server
does — which is also why the footprint is amortised across the work it does
rather than charged once in the year it was bought.

**A provider the catalogue does not classify gets no scope at all.** Not a
default, not the nearest guess. The two answers differ by *which legal entity
reports the emission*, and a wrong one looks exactly as tidy as a right one.

## Scope 2: both halves, and which one is yours to state

The carbon intensities here are national grid averages, read from
[Ember](https://ember-energy.org/data/yearly-electricity-data/). A grid average
*is* the **location-based** method, by definition — it carries no adjustment for
any contractual claim.

The **market-based** figure is a different number, and the GHG Protocol's
[Scope 2 Guidance](https://ghgprotocol.org/scope-2-guidance) requires both
wherever contractual instruments exist in your market. Under the European
standards the same pair is explicit: gross scope 2 is disclosed
*location-based and market-based*.

**This tool will never derive the market-based figure from a grid average**,
because it does not follow from one. That number is built from one of three
things, in descending order of preference:

1. your supplier's own emission factor for the contract you are on;
2. the contractual instruments you hold — guarantees of origin, RECs, a PPA (power purchase agreement);
3. failing both, your market's **residual mix** — in Europe the one the
   [Association of Issuing Bodies publishes](https://www.aib-net.org/facts/european-residual-mix),
   which exists precisely so that unclaimed electricity is not counted as clean
   by default.

What the tool does instead is carry the second figure as a dimension of its own,
`carbon_market_based`, computed from the one fact only you hold. An audit of a
machine you operate ships `assumptions.market_carbon_intensity` **open**, with
that shopping list in its notes. State the factor — with the document it comes
from and the date you read it — and the figure is computed from the same energy
as the first, placed beside it, labelled with the method that produced it, and
drift-gated the same way. Leave it open and the reports print the shopping list
rather than a plausible number.

This is the row `saggio audit` writes on a machine you operate, unfilled:

```yaml
assumptions:
  market_carbon_intensity:
    value: null
    status: TODO
    unit: gCO2e/kWh
    source_url: ''
    notes: 'The emission factor of the electricity you contracted for, which no
      catalogue can hold: it is a property of your contract, not of your country.
      [...] Leaving it open is a complete answer; a zero because the electricity
      is ''green'' is not one.'
```

Replace the `null` with the factor your document states, the empty `source_url`
with that document, and the `TODO` with `estimated` or `measured`. Nothing else
has to change: the figure, its derivation and its placement follow.

A number that comes from a contract rather than from a catalogue is checkable in
a different way from everything else here, and three rules follow:

- **It needs its document, as an error.** A missing `source_url` elsewhere is a
  warning. Here it fails validation: nobody but you holds that contract, and
  nothing in this tool can go and read it — so without the supplier statement,
  certificate or residual-mix publication behind it, the figure is unverifiable
  by construction.
- **It is never published alone.** A market-based figure with no location-based
  one beside it is warned about. It is the half a contract can improve, and on
  its own it reads better than the disclosure actually is.
- **It does not exist on rented hardware.** The pair lives inside scope 2 and
  nowhere else. On a vendor's machine the electricity is the vendor's scope 2
  and the pair is the vendor's to disclose; what reaches you is one purchased
  service in category 1, where the standard draws no such pair. The audit writes
  no row there, so nobody is left holding a `TODO` that can never become true.

Neither figure replaces the other, and the reports say so on the page: a
contract changes what you are accountable for, not which electrons the grid
delivered.

## What an assurance provider gets

Limited assurance is mostly a documentation exercise, and it is the part a
spreadsheet of carbon figures fails hardest. Every quantity here carries four
things, enforced rather than encouraged:

| | |
|---|---|
| **A status** | `measured`, `estimated`, `placeholder`, or `TODO`. A derived figure may never claim to be better founded than its weakest input, and the validator fails a model that tries. |
| **Its provenance** | A Uniform Resource Locator (URL) and the date somebody read it — on a page a reader can actually open, which is checked. |
| **Its derivation** | The inputs it came from, named, with the arithmetic re-computed from them and refused when it does not reconcile to within a percent. |
| **A freshness window** | Each catalogue column goes stale on its own schedule, and the gate fails a build that ships a figure nobody has re-read. |

Two consequences worth stating plainly to an auditor.

**The estimation disclosure is already written.** A filer is asked to say how
much of an inventory rests on estimates rather than readings. Every number here
says so for itself; `saggio scopes --json` counts them.

**An open figure stays open.** A country nobody stated gives a `TODO`, not a
zero. A provider that publishes no water figure gives a `TODO`, not a plausible
one. Nothing in this tool will fill a gap with an average and let it read like a
measurement — which is the failure mode that makes a carbon figure
unverifiable, and the one this whole design exists to prevent.

## Where this is not enough

The useful half of any conformance claim is the part that fails.

- **It is not your IT (information technology) footprint.** It covers compute for one unit of work. No
  employee devices, no network transit, no storage at rest, no office, no travel.
  A software cost model is one input to an inventory, not an inventory.
- **The market-based factor is yours, not ours.** The tool computes the figure,
  places it, and holds it to a stricter provenance rule than anything else in
  the model — but it will not invent the factor. No catalogue here carries a
  residual mix or a supplier factor, and the freshness gate cannot re-read your
  contract when it is restated next year.
- **No end of life, and no biogenic or removal accounting.** The published
  hardware footprints are cradle-to-gate and exclude the use phase and disposal;
  this tool reports what they cover and not a gram more. Nothing is netted
  against removals or credits, which is also what the standards require: gross.
- **Scope 3 category 1 for cloud is a model, not an invoice.** Where your
  provider publishes a per-customer figure, that figure is the primary source
  and this one is a cross-check. Most publish nothing at that granularity, which
  is the reason to compute it at all.
- **The hardware catalogue is small**, deliberately. Eight footprints ship and
  everything else reports `TODO` with a sentence saying nobody has read one —
  which is not the same as the hardware having been free to build.
  [`STANDARDS.md`](STANDARDS.md)
  has the table and the refusals.
- **It is not an assurance opinion**, and no tool is one.

## The rules this is written against

Dates and numbering move; these were checked on 2026-10-14.

**GHG Protocol.** The [Corporate Standard](https://ghgprotocol.org/corporate-standard)
defines the scopes, the [Scope 3 Standard](https://ghgprotocol.org/corporate-value-chain-scope-3-standard)
the fifteen categories, and the [Scope 2 Guidance](https://ghgprotocol.org/scope-2-guidance)
the dual-reporting requirement. The Scope 2 Guidance is itself under revision.

**CSRD (Corporate Sustainability Reporting Directive), after the Omnibus.** The European Union's [Directive (EU) 2026/470](https://eur-lex.europa.eu/eli/dir/2026/470/oj/eng)
was published on 26 February 2026 and entered into force on 18 March 2026. It
narrows the reporting population sharply — broadly, undertakings above 1,000
employees and €450m net turnover — and defers the later waves. Wave 1 is
unchanged. **If you are reading this to decide whether you are in scope, read
the directive and ask your advisers; this page is a tool's documentation, not
advice.**

**ESRS (European Sustainability Reporting Standards) E1, and its renumbering.** Gross scopes 1, 2 and 3 were disclosure
requirement **E1-6**; in the amended standards each requirement from E1-2 shifts
by two, so the same disclosure becomes **E1-8**. Its text spells out the pair
this page keeps insisting on: scope 2 *location-based and market-based*.

**France, separately.** The *bilan d'émissions de gaz à effet de serre* under
[article L. 229-25 of the code de l'environnement](https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000039369665)
is its own obligation with its own filing, published on
[bilans-ges.ademe.fr](https://bilans-ges.ademe.fr/). Since décret n° 2022-982 it
covers significant indirect emissions — scope 3 — for the organisations it
applies to, which is where a software figure of this kind would land.

## Doing it

```bash
# Where every cost in this model goes, and why.
saggio scopes cost_of_running.yaml

# The same, for a pipeline that reads it.
saggio scopes cost_of_running.yaml --json

# A report that carries the placement alongside the figures.
saggio render cost_of_running.yaml -f html -o cost_of_running.html

# A document, for a file that goes to an auditor.
saggio render cost_of_running.yaml -f docx -o cost_of_running.docx
```

The scope is read from the provider, so a model that does not name one is told
so rather than placed by guesswork. To classify a provider of your own, give its
catalogue row `operated_by: self` or `operated_by: vendor`.

## Sources

- [GHG Protocol Corporate Standard](https://ghgprotocol.org/corporate-standard) · [Corporate Value Chain (Scope 3) Standard](https://ghgprotocol.org/corporate-value-chain-scope-3-standard) · [Scope 2 Guidance](https://ghgprotocol.org/scope-2-guidance)
- [Directive (EU) 2026/470](https://eur-lex.europa.eu/eli/dir/2026/470/oj/eng) — the Omnibus I directive amending the CSRD.
- [ESRS E1 as amended by the European Financial Reporting Advisory Group (EFRAG)](https://www.efrag.org/sites/default/files/media/document/2025-12/November_2025_ESRS_E1.pdf) — where the GHG disclosure requirement is renumbered and the location-based / market-based pair is restated.
- [Article L. 229-25, code de l'environnement](https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000039369665) · [bilans-ges.ademe.fr](https://bilans-ges.ademe.fr/) — the French regulatory GHG report and where it is filed.
- [Base Empreinte, from the Agence de la transition écologique (ADEME)](https://base-empreinte.ademe.fr/) — the French emission-factor database, for the figures this tool does not carry.
- [Ember's yearly electricity data](https://ember-energy.org/data/yearly-electricity-data/) — the grid intensities here, location-based by construction.
- [The AIB's European Residual Mix](https://www.aib-net.org/facts/european-residual-mix) — the market-based factor of last resort, for electricity no instrument claims. This tool carries none of it: the figure is yours to state.

---

[`STANDARDS.md`](STANDARDS.md)
is the same exercise against the Software Carbon Intensity standard.
[`MEASURING.md`](MEASURING.md)
is where the energy figure comes from.
[`LANDSCAPE.md`](LANDSCAPE.md)
places this among the tools that answer nearby questions.
