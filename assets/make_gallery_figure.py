"""Draw the gallery's comparison figure, in both languages, from one source.

Module summary
--------------
The gallery compares five families of cost and carbon tool on three things: the
artefact each produces, the unit its answer is per, and what it does when an
input is missing. That last column is the one the page asks you to read first,
because it decides whether a figure survives being quoted.

The figure exists in English and French, and both come out of this file. Two
hand-edited SVGs would drift the first time a row changed, and a figure that
disagrees with its translation is worse than one language's reader going
without: neither of them can tell which is right.

Nothing here is a verdict. A live metrics stream is the right artefact for a
daemon and the wrong one for a figure in a report, and the reverse holds too.
The tools behind each family, and what separates them, are in ``LANDSCAPE.md``.

Usage example
-------------
>>> rows = ROWS["en"]
>>> rows[0][0]
'saggio'
>>> len(ROWS["en"]) == len(ROWS["fr"])
True

Author
------
Warith Harchaoui
"""

from __future__ import annotations

import pathlib
from typing import Final

#: Canvas, in the house proportions: wide enough for four columns of prose
#: without any of them wrapping, which is what makes the rows scannable.
WIDTH: Final[int] = 1180
HEIGHT: Final[int] = 560

#: Okabe-Ito-adjacent hues from the house palette, one per family, carrying no
#: meaning beyond telling the rows apart: the figure is not a ranking.
BLUE, GREEN, ORANGE, PURPLE, GREY = "#007AFF", "#28CD41", "#FF9500", "#AF52DE", "#808080"

#: One entry per family: name, colour, artefact, unit, behaviour when a number
#: is missing, and whether it is this package (which is set in bold, and is the
#: only thing on the figure that distinguishes it).
ROWS: Final[dict[str, list[tuple[str, str, str, str, str, bool]]]] = {
    "en": [
        (
            "saggio",
            BLUE,
            "a committed YAML model + a report",
            "one unit of work you named",
            "writes TODO, and the report says so",
            True,
        ),
        (
            "Episode trackers",
            GREEN,
            "a CSV log of the run that just ended",
            "one episode, however long it was",
            "emits a number anyway",
            False,
        ),
        (
            "Power daemons",
            PURPLE,
            "a live metrics stream, per process",
            "a moment, continuously",
            "the series has a gap",
            False,
        ),
        (
            "Calculators",
            ORANGE,
            "one answer to a form you filled in",
            "the hypothetical you described",
            "the field is required",
            False,
        ),
        (
            "Spend tools",
            GREY,
            "a dashboard or a pull-request comment",
            "a bill, or a plan you have not run",
            "the line is absent from the bill",
            False,
        ),
    ],
    "fr": [
        (
            "saggio",
            BLUE,
            "un modèle YAML commité + un rapport",
            "une unité de travail que vous nommez",
            "écrit TODO, et le rapport le dit",
            True,
        ),
        (
            "Traceurs d'épisode",
            GREEN,
            "un journal CSV de l'exécution finie",
            "un épisode, quelle qu'en soit la durée",
            "émet un nombre quand même",
            False,
        ),
        (
            "Démons de puissance",
            PURPLE,
            "un flux de métriques, par processus",
            "un instant, en continu",
            "la série a un trou",
            False,
        ),
        (
            "Calculateurs",
            ORANGE,
            "une réponse à un formulaire rempli",
            "l'hypothèse que vous avez décrite",
            "le champ est obligatoire",
            False,
        ),
        (
            "Outils de dépense",
            GREY,
            "un tableau de bord ou un commentaire de PR",
            "une facture, ou un plan non exécuté",
            "la ligne est absente de la facture",
            False,
        ),
    ],
}

#: Everything around the rows, per language.
TEXT: Final[dict[str, dict[str, str]]] = {
    "en": {
        "title": "What each kind of tool hands you",
        "subtitle": "And what it does when an input is missing — the column that decides "
        "whether a figure can be quoted.",
        "family": "Tool family",
        "artefact": "The artefact it produces",
        "unit": "Its answer is per",
        "missing": "When a number is missing",
        "foot1": "Families, not products: the named tools behind each row, with what "
        "separates them, are in LANDSCAPE.md. None of these rows is a verdict "
        "on quality —",
        "foot2": "a live metrics stream is the right artefact for a daemon and the wrong "
        "one for a figure in a report, and the reverse holds too.",
        "alt": "Five families of cost and carbon tool compared on the artefact they "
        "produce, the unit their answer is per, and what each does when an input "
        "is missing.",
    },
    "fr": {
        "title": "Ce que chaque sorte d'outil vous rend",
        "subtitle": "Et ce qu'il fait quand un apport manque — la colonne qui décide "
        "si un chiffre peut être cité.",
        "family": "Famille d'outils",
        "artefact": "L'artefact qu'il produit",
        "unit": "Sa réponse porte sur",
        "missing": "Quand un nombre manque",
        "foot1": "Des familles, pas des produits : les outils de chaque ligne, et ce qui "
        "les sépare, sont dans PAYSAGE.md. Aucune de ces lignes n'est un verdict "
        "de qualité —",
        "foot2": "un flux de métriques est le bon artefact pour un démon et le mauvais "
        "pour un chiffre dans un rapport, et l'inverse vaut aussi.",
        "alt": "Cinq familles d'outils de coût et de carbone comparées sur l'artefact "
        "qu'elles produisent, l'unité à laquelle leur réponse se rapporte, et ce "
        "que chacune fait quand un apport manque.",
    },
}

_COLUMNS: Final[tuple[int, int, int, int]] = (44, 268, 596, 858)
_FIRST_ROW: Final[int] = 196
_ROW_HEIGHT: Final[int] = 62


def _escape(text: str) -> str:
    """Return text safe to drop between SVG tags.

    Examples
    --------
    >>> _escape("a & b < c")
    'a &amp; b &lt; c'
    """
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def draw(lang: str) -> str:
    """Return the figure as SVG, in one language.

    Parameters
    ----------
    lang : str
        ``"en"`` or ``"fr"``.

    Returns
    -------
    str
        A standalone SVG: Roboto, light and dark aware through an embedded
        ``prefers-color-scheme`` block, and labelled for a reader who cannot
        see it.

    Examples
    --------
    >>> svg = draw("fr")
    >>> svg.startswith("<svg")
    True
    >>> "prefers-color-scheme" in svg
    True
    >>> "Démons de puissance" in svg
    True
    """
    words = TEXT[lang]
    rows = ROWS[lang]
    x_name, x_art, x_unit, x_miss = _COLUMNS
    out: list[str] = []
    add = out.append

    add(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" '
        f'viewBox="0 0 {WIDTH} {HEIGHT}" role="img" aria-labelledby="gt gd" '
        f'font-family="Roboto, -apple-system, Helvetica, Arial, sans-serif">'
    )
    add(f'<title id="gt">{_escape(words["title"])}</title>')
    add(f'<desc id="gd">{_escape(words["alt"])}</desc>')
    add(
        "<style>"
        ".paper{fill:#FFFFFF}.ink{fill:#1A1A1A}.muted{fill:#6B6B6B}.rule{stroke:#E4E4E4}"
        ".h{font-size:15px;font-weight:600;letter-spacing:.01em}"
        ".k{font-size:11.5px;font-weight:600;letter-spacing:.09em;text-transform:uppercase}"
        ".b{font-size:14px}.t{font-size:26px;font-weight:700;letter-spacing:-.01em}"
        ".s{font-size:14.5px}.n{font-size:12.5px}"
        "@media (prefers-color-scheme: dark){"
        ".paper{fill:#141414}.ink{fill:#F2F2F2}.muted{fill:#9A9A9A}.rule{stroke:#2E2E2E}"
        ".chip{fill-opacity:.26}}"
        "</style>"
    )
    add(f'<rect class="paper" width="{WIDTH}" height="{HEIGHT}"/>')
    add(f'<text class="t ink" x="{x_name}" y="56">{_escape(words["title"])}</text>')
    add(f'<text class="s muted" x="{x_name}" y="84">{_escape(words["subtitle"])}</text>')
    for x, key in ((x_name, "family"), (x_art, "artefact"), (x_unit, "unit"), (x_miss, "missing")):
        add(f'<text class="k muted" x="{x}" y="146">{_escape(words[key])}</text>')
    add(f'<line class="rule" x1="{x_name}" y1="160" x2="{WIDTH - 44}" y2="160" stroke-width="1"/>')

    for index, (name, colour, artefact, unit, missing, is_us) in enumerate(rows):
        y = _FIRST_ROW + index * _ROW_HEIGHT
        if index:
            add(
                f'<line class="rule" x1="{x_name}" y1="{y - 32}" x2="{WIDTH - 44}" '
                f'y2="{y - 32}" stroke-width="1"/>'
            )
        add(f'<rect x="{x_name}" y="{y - 19}" width="4" height="24" rx="2" fill="{colour}"/>')
        add(
            f'<text class="h ink" x="{x_name + 16}" y="{y}" '
            f'font-weight="{"700" if is_us else "600"}">{_escape(name)}</text>'
        )
        add(f'<text class="b muted" x="{x_art}" y="{y}">{_escape(artefact)}</text>')
        add(f'<text class="b muted" x="{x_unit}" y="{y}">{_escape(unit)}</text>')
        add(
            f'<rect class="chip" x="{x_miss - 10}" y="{y - 21}" width="300" height="29" '
            f'rx="8" fill="{colour}" fill-opacity="0.13"/>'
        )
        add(f'<text class="b ink" x="{x_miss}" y="{y}">{_escape(missing)}</text>')

    foot = _FIRST_ROW + len(rows) * _ROW_HEIGHT + 4
    add(
        f'<line class="rule" x1="{x_name}" y1="{foot - 30}" x2="{WIDTH - 44}" '
        f'y2="{foot - 30}" stroke-width="1"/>'
    )
    add(f'<text class="n muted" x="{x_name}" y="{foot}">{_escape(words["foot1"])}</text>')
    add(f'<text class="n muted" x="{x_name}" y="{foot + 19}">{_escape(words["foot2"])}</text>')
    add("</svg>")
    return "\n".join(out) + "\n"


def main() -> None:
    """Write both figures next to this file."""
    here = pathlib.Path(__file__).resolve().parent
    for lang, name in (("en", "gallery-families.svg"), ("fr", "gallery-families.fr.svg")):
        (here / name).write_text(draw(lang), encoding="utf-8")
        print(f"assets/{name}")


if __name__ == "__main__":
    main()
