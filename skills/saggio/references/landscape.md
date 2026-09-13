# When another tool is the right answer

Send the user elsewhere when the question is elsewhere. The full comparison is in
the repository's [`LANDSCAPE.md`](../../../LANDSCAPE.md); this is the short form
for deciding quickly.

| The user is asking | Point them at |
|---|---|
| "Why was our AWS bill so high last month?" | Cost Explorer, GCP Billing, Azure Cost Management. This tool models a unit of work from first principles; it does not read invoices. |
| "Log the emissions of my training runs automatically." | CodeCarbon, eco2AI, or carbontracker. Passive, episode-shaped telemetry is their job. |
| "I need accurate continuous power measurement." | Scaphandre, PowerAPI, or pyJoules. They measure far better than this package does. |
| "Which pods on my cluster are drawing power?" | Kepler, or OpenCost for the money side. |
| "What will this Terraform cost per month?" | Infracost. Same idea as the drift gate here, applied to declared infrastructure. |
| "Organisational carbon reporting, all scopes." | A carbon accounting platform. Different standard, different scope. |
| "Which GPU should we buy?" | Needs embodied carbon, lifetime, and utilisation, none of which this models. |
| "A quick one-off estimate, no setup." | The Green Algorithms web calculator, which is the method this package implements. |

## When this one is the right answer

When the number has to survive being questioned. Somebody is going to put a
per-request carbon figure in a customer-facing document, or a per-run cost in a
budget, and will be asked six months later where it came from.

Also when the answer has to live in the repository, change with the code, and fail
a build when it drifts.
