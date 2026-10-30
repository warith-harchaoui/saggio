# Water

🇬🇧 English · [🇫🇷 EAU.md](EAU.md)

A package that counts what code costs reports five things, and one of them
surprises people: litres. This page is why, and it is also the page that
concedes the two objections a careful reader raises immediately — that cooling
water is not destroyed, and that it does not necessarily come back undrinkable.
Both are correct. The accounting is still worth doing, and the reason is more
interesting than the slogan.

## Why a package about compute reports water at all

A datacentre is a building whose job is to turn electricity into heat and then
get rid of the heat. There are two ways to move heat out of a room: spend more
electricity on chillers, or evaporate water. Evaporation is far cheaper,
because turning a kilogram of water into vapour carries away about six hundred
times more heat than warming that same kilogram by one degree.

So water is not a side effect of computing. It is one of the two bills a room
can pay to shed the heat your job made, and **a room with a very low water
figure may simply be a room paying the other bill.** Dry-cooled halls exist;
they use almost no water and more electricity. That trade is the single most
important thing to understand here, and it is why this package never shows a
water figure without the energy and power usage effectiveness beside it. A
water number read alone will reward exactly the wrong design.

## What the number is

**WUE — water usage effectiveness** — is litres of water per kilowatt-hour of
energy drawn by the computers themselves. It is a ratio defined on-site, which
means it counts the water the building moved and **excludes the water used to
generate the electricity the building bought.** That exclusion is not small:
thermal power stations evaporate water in their own cooling towers, and
reservoirs behind hydroelectric dams evaporate from their surface. A figure
that includes it is a different quantity, sometimes written WUEsource, and this
package does not report it.

This repository's figures are per unit of work, so the litres you see are
`machine energy × WUE`, divided down to one invocation, one request, one
training run — whatever you named your unit to be.

## "But the water is not lost"

Correct, and the word the field uses is the one that causes the confusion.

Water accounting distinguishes **withdrawal** from **consumption**. Withdrawal
is what you take out of a river, an aquifer or a municipal main. Consumption is
the part that does not go back into the body it came from. Evaporative cooling
consumes most of what it withdraws, and *consumption here does not mean
destruction.* The water leaves as vapour, joins the atmosphere, and falls again
as rain somewhere. Nothing is annihilated; the hydrological cycle is closed and
always was.

What the number measures is therefore not loss but **relocation, in place and
in time.** The litre is gone from this basin, this summer, for everyone else
who was drawing on it — the farm downstream, the town's reservoir, the river's
own minimum flow. It comes back as rain over an ocean nine hundred kilometres
away and four days later, which helps nobody who was queuing for it here.

That is also why a water figure without a place attached is close to
meaningless. A litre in Ireland and a litre in Arizona are the same litre and
not remotely the same event. **This package reports litres and the country, and
deliberately does not weight them by local scarcity.** Scarcity weightings
exist and are respectable, but choosing one is choosing a value judgement, and
a weighted figure cannot be un-weighted by whoever reads it later. The
unweighted litre and the place can always be combined afterwards. The reverse
is not true.

## "And it does not necessarily come back non-potable"

Also correct, and the chemistry runs the opposite way from most people's
intuition.

Evaporation is distillation. What leaves a cooling tower is pure water vapour;
the dissolved salts and minerals stay behind. So the evaporated share is not
degraded at all — it is the cleanest water in the building. It is simply
somewhere else.

The salts that stayed behind concentrate in the circulating loop with every
pass. Left alone, they would scale and foul the heat exchangers, so a fraction
of the loop is bled off and replaced — **blowdown** — and that fraction *is*
degraded: saltier than what came in, and usually carrying the biocides and
anti-scalants that kept the loop from growing things. It is a far smaller
volume than the evaporated share, and it is the part that actually has an
effluent problem.

So the honest summary is three facts, none of which one number can hold:

| The share | What happens to it | Is it degraded? |
|---|---|---|
| Evaporated — the bulk | Leaves the basin as pure vapour | No. Relocated, not ruined. |
| Blowdown — the remainder | Discharged, concentrated, treated | Yes, and it is the small part. |

And a third fact that sits at neither end of that table: **what was drawn in
the first place.** It is the one that matters most and gets discussed least.

A great deal of cooling water is **potable water** — treated to drinking
standard at public expense and then evaporated to cool servers. The alternative
is reclaimed water or greywater, and operators who use it generally say so. The
equity question about datacentre water is therefore usually at the intake and
not at the outfall: not *"did they ruin it"* but *"did they drink the town's
supply to do it"*.

Read WUE as **how much water this room moved**, never as *how much water this
room ruined*. It does not know the difference, and neither does any single
number.

## What this package does, and what it refuses

It reports litres per unit of work, with the country attached, derived from a
published water usage effectiveness and the measured energy.

**It never invents a water usage effectiveness.** Most operators publish none,
and the field is left open — `TODO` rather than zero, because zero is a claim
and absence is not. A room that is genuinely dry-cooled has a WUE of zero and
should say so on purpose; a room whose operator never published is unknown, and
the two must not look alike in a report.

Where a way out exists, the refusal names it. A self-run room inside a European
Union Member State is covered by the reporting duty in the recast Energy
Efficiency Directive, and the Commission publishes a Union-wide average from
what operators report — carried here as the `on-prem-eu` provider. The `TODO`
for such a room points at that row and still does not take it, because a
Union-wide average over the rooms that reported may be nothing like yours, and
substituting it unasked would be this package choosing an assumption on your
behalf. The one thing it refuses to do everywhere else, it also refuses here.

**What it does not model**, stated so nobody assumes otherwise: water used to
generate the electricity, local scarcity weighting, the thermal load returned
to a river by once-through cooling, and the water embodied in manufacturing the
hardware. Four absences, named rather than silently scoped out.

## Where the figures come from

| Figure | Source |
|---|---|
| The definition of water usage effectiveness | The Green Grid, which defined the ratio |
| `on-prem-eu`, 0.58 L/kWh | [COM(2026) 500 final](https://data.consilium.europa.eu/doc/document/ST-13443-2026-INIT/en/pdf), the Commission's first assessment under Article 12 of the recast Energy Efficiency Directive — a Union-wide average over the 458 data centres that reported water above zero, which excludes dry-cooled rooms and therefore overstates the typical one |
| Cloud providers' figures | Each operator's own sustainability page, cited per row in `saggio/data/providers.yaml` |

Every one of them is in the catalogue with its address and the date it was read,
and every one goes stale. `saggio catalog freshness` says which.

See also [STANDARDS.md](STANDARDS.md) for the reporting duty behind the
European row, and [BOUNDARIES.md](BOUNDARIES.md) for what this package declines
to model.
