# Five ways to reach one engine

[🇫🇷 UTILISER.md](UTILISER.md) · 🇬🇧 English

A cost model is produced by an engineer and read by somebody else: a
sustainability team that has to file it, a finance reviewer who has to budget
against it, an auditor who has to believe it. Most of those readers will never
install a Python package, and some of them will ask the question in French to an
agent rather than to a terminal.

So the engine is reachable five ways, and this page is what each one is for.

## The rule the five follow

**The library is the engine. Everything else is an adapter.** A surface parses a
request, calls one public function, and formats what comes back. That is the
whole of its job.

Two consequences, and both are checked by tests rather than left to discipline:

- **A surface may do nothing the library cannot.** Anything it could do on its
  own would be a capability every library caller is locked out of, reachable only
  by whoever happened to pick the right door.
- **Two surfaces may not answer the same question differently.** The placement of
  a figure in a greenhouse-gas inventory was assembled inside the command line
  once, where the other surfaces could only have reached it by copying. It now
  lives in `placed_model`, and a test asserts that the HTTP route returns exactly
  what the library returns, field for field. A package that disagreed with itself
  about which line a number goes on would have no business settling the question
  at all.

## 1. The library

For a script, a notebook, a test, or another package.

```python
import saggio

result = saggio.audit(".", options=saggio.AuditOptions(run=False, country="FR"))
print(saggio.overall_status(result.model))
print(saggio.placed_model(result.model)["placements"])
```

Everything the other four surfaces do is in `saggio.__all__`, and a test fails
the build if a name in it stops existing. The reference is
[`docs/api.md`](docs/api.md), generated from the docstrings.

## 2. The command line

For a person at a terminal, and for continuous integration, which is the same
caller with no hands.

```bash
pip install saggio
saggio audit . --country FR --run -o cost_of_running.yaml
saggio scopes cost_of_running.yaml
saggio render cost_of_running.yaml -f html -o cost_of_running.html
saggio diff cost_of_running.yaml /tmp/now.yaml --threshold 10
```

This is the only surface that will run your code, and only with consent recorded
once by a person who was asked. That is not an accident of where the feature
landed: measuring executes a slice of a repository with the permissions of
whoever started the process, and a terminal is the one place there is somebody to
ask.

## 3. The HTTP API

For a browser, an internal service, a reporting pipeline, or a reader who should
not have to install anything.

```bash
pip install "saggio[api]"
uvicorn saggio.api.app:app --host 127.0.0.1 --port 8000
```

The interactive documentation is then at `/docs`, and the routes are:

| Route | What it answers |
|---|---|
| `GET /health` | Which version is running, and what this deployment will refuse. |
| `POST /validate` | Does this model obey the rules, including the weakest-link rule? |
| `POST /next` | Which open field would close the most numbers, and what would it close? |
| `POST /scopes` | Which line of a greenhouse-gas inventory does each figure go on? |
| `POST /render` | The report, as Markdown or as a self-contained HTML page. |
| `POST /diff` | What moved between two models, and did it pass the gate? |
| `GET /catalog` and `GET /catalog/{name}` | The facts the package carries, each row with the source it was read from. |
| `GET /freshness` | Which figures nobody has re-read inside their own window. |
| `POST /audit` | Read a repository and return the model it implies. |

A model is posted either as `cost_model`, a parsed document, or as `yaml_text`,
the contents of a `cost_of_running.yaml` file. Both give the same answer, which
is also a test.

**Two refusals are built into this surface rather than configured on it.**

It never runs a repository's code. There is no route for measuring at all, so
there is nothing to misconfigure and nothing to confine.

It clones nothing unless the operator allowed it. `POST /audit` fetches an
address a client chose, which is a real capability with real consequences, so it
is off unless `SAGGIO_API_ALLOW_CLONE` says otherwise. Off, the route answers
with what it would take instead of with a stack trace.

In a container, both surfaces at once, with the clone switch off, a read-only
filesystem and no capabilities:

```bash
docker compose up --build
```

## 4. The agent protocol

For a colleague who asks the question in their own words, in their own language,
to an agent rather than to a terminal. This is the surface a sustainability team
actually uses.

```bash
uvicorn saggio.api.mcp:app --host 127.0.0.1 --port 8000
# an agent connects to http://127.0.0.1:8000/mcp
```

The tools are generated from the application's own OpenAPI document. A tool's
name is the route's identifier, its description is the route's docstring, and its
arguments are the request model's fields. Nothing is written twice, so nothing
can drift: a hand-written wrapper would be a second description of the same
endpoint, free to disagree with the first, and the disagreement would surface as
an agent confidently telling somebody the wrong scope.

The refusals come with it. There is no tool for measuring, because there is no
route for it.

## 5. The skill

For Claude, or any agent that reads
[Agent Skills](https://code.claude.com/docs/en/skills). It lives in
[`skills/saggio/`](skills/saggio/SKILL.md) and it is not a wrapper around the
other four: it is the method, written down. Which question to ask before
auditing, which numbers an agent may never write from memory, how to report a
figure with its status, and when to say that another tool is the right answer.

Its triggers are the part most worth getting right, because a skill that does not
load is a skill that does not exist. [`TRIGGERS.md`](TRIGGERS.md) lists the
phrasings that should reach it, in both the engineer's vocabulary and the
sustainability team's, and the ones that should not. The evals beside the skill
pin both halves.

## What a surface may not do

- **Invent a capability.** If it is worth having, it is worth having in the
  library, where every caller can reach it.
- **Keep its own copy of a payload.** The shape a surface returns is the shape
  the library produced.
- **Lower a refusal.** A number the library will not state is not a number an
  HTTP route may state, and a consent the command line asks for is not a consent
  a server may assume.

## What a surface may decide for itself

- **Presentation.** A table for a terminal, JSON for a program, a page for a
  browser, a sentence for an agent.
- **Which capabilities it offers at all.** The HTTP surface offers no measuring,
  because over a network there is nobody to ask for consent.
- **What a deployment allows.** Cloning is the operator's decision, taken in the
  environment rather than in the code.

## The language all five answer in

A reader's language is not presentation, and the two halves of it are not the
same problem.

**The interface.** Every label on the HTML report comes from one translation
file, and the page carries a language button built from whatever that file
contains, so a reader switches language in their browser with no network and no
second file to ship.

**The prose.** One sentence of a cost model is not read from a file: a local
model is asked what shape of work the repository does, and it writes the answer
into the `analysis` block. That sentence is the one thing that can arrive in the
wrong language, and the surfaces take the language the same way:

```bash
saggio audit . --country FR --language fr -o cost_of_running.yaml
```

```python
saggio.audit(".", options=saggio.AuditOptions(country="FR", language="fr"))
```

**The question.** Before an audit runs a line of somebody's code it asks, and it
asks in the same language: a person who cannot read the terms has not been asked.
`saggio consent grant --language fr` prints them too, and the recorded decision
says which terms were agreed to and in which language they were read.

**Every route that answers with prose takes a `language` field**, from one
definition, for the same reason the command line attaches `--language` to every
verb from one place: a surface that offers a language on some of its routes and
not others is a surface a caller has to remember the shape of. The agent tools
are generated from those routes, so seven of them take the argument without
anybody having written it twice. The four that do not — health, the two
catalogue readers, the freshness report — answer with data rather than prose.
`saggio.languages()` is what all of them are built from — so a
GUI offering a picker asks the library rather than hard-coding a list that goes
stale. A tag nothing is written in falls back to English and says so in the
notes, because an audit must not fail over a language.

**The engine's own sentences are moving into a message catalogue**, module by
module, so that `--language fr` renders them too rather than only the furniture.
`saggio/data/messages/*.yaml` holds them, one file per language; a sentence names
its arguments in braces so each language can put the numbers where its own
grammar wants them. Contract tests refuse a key the code asks for and nothing
answers, a key one language has and another does not, wording nothing reaches,
and a translation that renames an argument. Where the inventory placements had
moved on 2026-10-19 — the first module — **11% of a static report** came out in
French.

**What the button alone does not switch, measured.** It exchanges **5.4%** of the
visible text on a rendered report. The structure moves:
headings, column names, the what-if labels, the equivalence sentences. The
substance does not: the notes, the methods, the caveats and the refusals are
written where the measurement happens, which was **709 prose literals of four
words or more across 51 modules** when it was counted on 2026-10-19, only 8% of
them under `report/`. Saying "the
report is bilingual" would be a claim nobody established. The *documentation* is
bilingual, page for page; a rendered report is a French frame around English
evidence.

**A language is not a country.** `--language fr` says how to write a sentence
and nothing about where the code runs: French is written on a dozen different
grids, and reading `--country FR` out of it would put a number in the model that
nobody established.

**Adding a language** means adding a top-level code to two files —
`reporting/i18n.yaml` for the labels and `saggio/data/prompts.yaml` for the
instruction — and nothing else. A contract test refuses a language that only
one of them has: a page a colleague reads in their language with a sentence
generated inside it in another is one deliverable in two languages.

## Adding a sixth

Write the function in the library first, with its docstring example. Then the
adapter, which should be short enough to read in one screen. Then the contract
test that says the new surface answers what the library answers. If the adapter
is growing logic, the logic is in the wrong place, and the fix is to move it down
rather than to test it twice.
