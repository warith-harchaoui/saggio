# Documentation

[🇫🇷 LISEZMOI.md](LISEZMOI.md) · 🇬🇧 English

Where to look, and what each document answers. Everything here is written by
hand except [`api.md`](api.md), which is derived from the docstrings.

## Start here

| Document | The question it answers |
|---|---|
| [`../README.md`](../README.md) | What is this, and why is it built this way? |
| [`../EXAMPLES.md`](../EXAMPLES.md) | How do I do the thing I came to do? |
| [`../GALLERY.md`](../GALLERY.md) | What does it actually say about real repositories? |
| [`../TRIGGERS.md`](../TRIGGERS.md) | Is this the right tool for what I am asking? |
| [`../LANDSCAPE.md`](../LANDSCAPE.md) | How does it compare to CodeCarbon, Scaphandre, and the rest? |
| [`../MEASURING.md`](../MEASURING.md) | Which counters will this machine let me read, and what do they cover? |

## Reference

| Document | The question it answers |
|---|---|
| [`api.md`](api.md) | What does `import saggio` give me? |
| [`../skills/saggio/references/schema.md`](../skills/saggio/references/schema.md) | What may a cost model contain? |
| [`../skills/saggio/references/honesty-taxonomy.md`](../skills/saggio/references/honesty-taxonomy.md) | What do the four statuses mean, exactly? |
| [`../skills/saggio/references/green-algorithms.md`](../skills/saggio/references/green-algorithms.md) | Where does the arithmetic come from? |
| [`../CHANGELOG.md`](../CHANGELOG.md) | What changed, and does it affect me? |

The schema and taxonomy references live under `skills/` because an agent reads
them too, and one copy that two readers share cannot drift from itself.

## Working on the package

| Document | The question it answers |
|---|---|
| [`../CONTRIBUTING.md`](../CONTRIBUTING.md) | How do I add a catalogue row, or a test? |
| [`../CODING.md`](../CODING.md) | What style is this repository written in? |
| [`../reporting/README.md`](../reporting/README.md) | How do I change what a report looks like? |

## Regenerating the API page

```bash
python docs/sync_api.py            # write it
python docs/sync_api.py --check    # report drift, exit 1, write nothing
```

A contract test runs `--check`, so a docstring edited without regenerating the
page fails the build rather than shipping a stale reference.
