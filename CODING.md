# How this repository is written

Style rules that a linter can check are in `pyproject.toml` and are not repeated
here. This file is about the ones it cannot.

## Every project is a teaching artefact

The code is read far more often than it is written, and someone reading it is
usually trying to decide whether to trust a number it produced. So examples,
docstrings, types, and tests are part of the public contract, not decoration
around it.

## Docstrings

**NumPy style, on everything.** Every module, class, function, and method,
including the private ones. A leading underscore says who the intended audience is,
not that the quality bar is lower; a private helper with a surprising rule in it is
exactly where a reader will be standing when they need the explanation.

**Every docstring carries a runnable example.** They run in the test suite, so an
example that stops being true fails the build. This is what stops documentation
drifting away from the code it documents.

```python
def weakest(*statuses: str | None) -> str | None:
    """Return the weakest of several statuses, ignoring the missing ones.

    This is the engine of the weakest-link rule. A derived quantity may claim at
    most the status returned here for the quantities it was computed from.

    Parameters
    ----------
    *statuses : str or None
        Input statuses. ``None`` entries are skipped, so a caller can pass the
        status of an optional input without special-casing it.

    Returns
    -------
    str or None
        The weakest status present, or ``None`` when every argument was ``None``.

    Examples
    --------
    >>> weakest("measured", "estimated")
    'estimated'
    >>> weakest(None, None) is None
    True
    """
```

**Module docstrings say what the module is for and why it exists**, in the order
Summary, Module summary, Usage example, Author. A module whose summary is
"utilities" is a module that has not decided what it is.

## Types

Full annotations on every signature, every class attribute, and every
module-level constant. `from __future__ import annotations` at the top of every
file.

## Comments

**Comment the why, never the what.** A comment restating the next line is noise
that will go stale. A comment explaining why the obvious approach was not taken is
the most valuable line in the file.

```python
# The type check comes first because an unhashable value, such as a list that a
# hand-edited YAML file put where a status belongs, would otherwise raise from
# the membership test instead of being reported as the fault it is.
return isinstance(status, str) and status in ALLOWED_STATUSES
```

**Every magic number is a named constant with a sentence.** If the sentence is
hard to write, the number is probably a guess, and this package does not ship
guesses.

## Tests

**Every function is tested, private ones included.** The test name says what is
being checked, in a sentence:

```python
def test_an_unknown_label_ranks_below_todo() -> None:
    # A typo must never let a derived value claim more confidence than it earned.
    assert status_strength("typoed") < status_strength(TODO)
```

**A test that asserts a behaviour nobody chose is worse than no test.** Pin what
the code is for, not what it happens to do.

**A test must never touch the machine it runs on.** Anything that would write to
the user's config directory, their catalogue overlay, or their consent record
takes an injectable path, and every test passes a temporary one. A test that
changed what the person running it had agreed to would be a test that broke their
machine to check a package.

## Prose, in code and out of it

The documentation, the error messages, and the reports are written in the same
voice, and they follow the same rules.

**Say what to do about it.** An error message that names the problem and stops is
half an error message:

> `GPU 'NVIDIA H300' is not in the catalogue; add it with
> `running-code-cost-helper catalog add gpu` once you have a datasheet TDP`

**No jargon where a word will do.** "Power usage effectiveness" the first time,
with what it means; "overhead" after that.

**No machine tells.** No sentence built as "it's not just X, it's Y". No
rhetorical triples for their own sake. No em dashes used as a connector where a
comma or a full stop is the honest punctuation. Write the sentence a careful
colleague would write.

**Reconstructible.** A reader should be able to rebuild the reasoning from what is
written, not just be told the conclusion. That is the same standard the cost models
are held to, applied to the prose.

## The rule that outranks the others

**Never invent a number.** Not in the code, not in a template, not in a catalogue,
not in an example. If it cannot be established, it is a `TODO` with a sentence
saying what would resolve it. Every other rule here is in service of that one.
