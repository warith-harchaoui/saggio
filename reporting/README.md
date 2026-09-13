# The report template

[🇫🇷 LISEZMOI.md](LISEZMOI.md) · 🇬🇧 English

Everything the HTML report is made of, as files rather than as strings quoted
inside Python: a shell, a stylesheet, a script, a translation table and a logo.

```
report.html   the document shell, with the tokens the renderer fills
report.css    the whole look: palette, layout, print rules, both colour schemes
report.js     the theme toggle, the language picker, the what-if recomputation
i18n.yaml     every string the page shows, one block per language
logo.png      inlined as a data: URI, so the page needs no network
sync.py       copies these into the package that ships them
```

## Why they live here

The renderer reads its assets through `importlib.resources`, which can only
reach inside the package, so a copy sits at
`saggio/data/report/` and that copy is what the wheel ships.
This directory is the original; the copy is the artefact.

Edit here, then:

```bash
python reporting/sync.py           # copy into the package
python reporting/sync.py --check   # non-zero if the two ever differ
```

A contract test runs the check, so editing the packaged copy by mistake fails
the build instead of quietly shipping.

## The shell, and its tokens

`report.html` holds no content of its own. The renderer replaces each token and
inlines the rest, which is what makes the finished page a single file that opens
offline.

| Token | What is put there |
|---|---|
| `{{LANG}}` | BCP 47 tag for the document, currently `en` |
| `{{TITLE}}` | The report's title, already escaped |
| `{{LOGO}}` | A `data:` URI, used as the favicon and in the bar |
| `{{STYLE}}` | The contents of `report.css` |
| `{{LANGUAGES}}` | One `<option>` per language found in `i18n.yaml` |
| `{{BODY}}` | The rendered sections |
| `{{PROJECT_URL}}` | Linked from the footer |
| `{{DATA}}` | The model as JSON, which the script reads to recompute in-browser |
| `{{SCRIPT}}` | The contents of `report.js` |

Substitution is plain text replacement, not `str.format`, because the stylesheet
and the script are full of braces of their own. A token left unfilled raises:
a report with a literal `{{BODY}}` in it would be worse than a failure.

## Using it for your own reports

The trio is deliberately neutral. There are no numbers in it, no project's
wording beyond the chrome, and no framework: `report.css` is a stylesheet with
custom properties at `:root`, `report.js` is one script with no imports.

To render reports of your own shape, copy `report.html`, `report.css` and
`report.js` somewhere and substitute the tokens yourself, in whatever language
you like. Keep all of them and the page keeps its properties: self-contained,
printable, light and dark, translated.

What to change first:

- **The palette** is the custom properties at the top of `report.css`. The
  status colours (`--measured`, `--estimated`, `--placeholder`, `--todo`) carry
  meaning, so keep them distinguishable for a colourblind reader, and keep the
  written status beside the colour as the page already does.
- **The strings** are `i18n.yaml`, keyed to the `data-i18n` attributes in the
  markup. A new top-level language code adds a language; the picker is built
  from whatever the file contains.
- **The chrome** is the `<nav>` and `<footer>` in `report.html`. Nothing in the
  script depends on them except `#theme-toggle` and `#language-picker`.

## What not to change without thinking

The page states numbers, so it carries the rules that make them readable:
every value shows its status, and every derived value shows what it came from.
Remove those columns and the page still renders, but it no longer says how far
anything in it can be trusted, which is the only reason this report exists.
