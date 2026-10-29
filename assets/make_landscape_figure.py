"""Draw the landscape pages' figure: the four links of the question, and who answers each.

Module summary
--------------
``LANDSCAPE.md`` and ``PAYSAGE.md`` score eighteen tools against ten criteria,
which is the right shape for comparing them and the wrong shape for the thing a
newcomer actually needs to see: that the question *"what does running this code
cost"* has four links, that no tool in the table answers all four, and that this
package is weakest at exactly the link the measurement tools are built for.

A table of stars cannot say that, because a reader has to hold ten columns in
their head to notice it. The figure says it in one pass, and it says it against
this package rather than for it: one of the four links carries a ``TODO`` pill.

Written here rather than drawn by hand for the reason the other figures are:
two hand-edited files drift the first time a row changes, and a figure that
disagrees with its translation leaves nobody able to say which is right. The
style -- the palette, the cards, the status pills -- is read from
``make_readme_figures``, so this figure and the front pages' figures are one
document.

Usage example
-------------
>>> svg = draw("fr")
>>> svg.startswith("<svg")
True
>>> "CEEMS" in svg
True

Author
------
Warith Harchaoui
"""

from __future__ import annotations

import pathlib
import sys
from typing import Final

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from make_readme_figures import (
    MARGIN,
    WIDTH,
    card,
    column_head,
    connector,
    head,
    title_block,
)

#: The four links, per language. Each carries the question it asks, what it
#: needs before it can be answered, who in the table answers it best, and the
#: status this package's own answer to it deserves -- which is the only
#: self-assessment on the figure, and the reason it is worth drawing.
LINKS: Final[dict[str, dict[str, object]]] = {
    "en": {
        "title": "One question, four links, and nobody answers all four",
        "subtitle": "Every tool on this page answers part of “what does running this code "
        "cost” and hands the rest on. Reading left to right is reading the order the work "
        "has to happen in; the pill under each link is what this package's own answer to it is "
        "worth, including the one it has to refuse.",
        "heads": ("THE LINK", "ANSWERED BEST BY", "AND HERE"),
        "rows": (
            {
                "question": "What ran, and how much of it?",
                "needs": "A named unit of work, and a count of how many a full run performs.",
                "who": "The repository itself. Green Metrics Tool describes the run as a file; "
                "Infracost and Carbonifer read a plan.",
                "mine": "reads your code, then runs a capped slice once you agree",
                "status": "measured",
            },
            {
                "question": "What did it draw?",
                "needs": "A counter, and a rule for sharing a machine several things are using.",
                "who": "Scaphandre, PowerAPI, JoularJX, Kepler, CEEMS, EnergiBridge — per "
                "process, per method, per container, per job.",
                "mine": "reads the machine's counter; will not split it per process",
                "status": "TODO",
            },
            {
                "question": "What does that cost?",
                "needs": "A tariff, a grid intensity, a water figure, a hardware footprint.",
                "who": "Green Algorithms, Boavizta, Climatiq, Electricity Maps, Cloud Carbon "
                "Footprint — the sourced catalogues.",
                "mine": "sourced catalogues, and a held-open field where none publishes",
                "status": "estimated",
            },
            {
                "question": "Per what, and how well founded?",
                "needs": "A committed artefact somebody can open in a pull request and disagree "
                "with.",
                "who": "Almost nobody. A filed Software Carbon Intensity (SCI) figure, and this.",
                "mine": "every number carries its status and the numbers it came from",
                "status": "measured",
            },
        ),
        "foot": (
            "The pills are this package's own four statuses, used on itself. The second link is "
            "the one it refuses: a counter meters hardware, so the figure it reads is the "
            "machine's and not the run's, and it says so rather than dividing by something "
            "plausible. That refusal is the sixth column of the table above, where five other "
            "tools score higher.",
        ),
        "alt": "The question “what does running this code cost” drawn as four links in "
        "order: what ran and how much of it, what it drew, what that costs, and per what and how "
        "well founded. Under each link are the tools that answer it best — the repository "
        "and the plan readers for the first, the power meters for the second, the sourced "
        "catalogues for the third, almost nobody for the fourth — and a pill saying what "
        "this package's own answer is worth: measured, TODO, estimated, measured. No tool on the "
        "page answers all four links.",
    },
    "fr": {
        "title": "Une question, quatre maillons, et personne ne les tient tous les quatre",
        "subtitle": "Chaque outil de cette page répond à une part de «\u202fcombien coûte "
        "l'exécution de ce code\u202f» et passe le reste. Lire de gauche à droite, c'est lire "
        "l'ordre dans lequel le travail doit se faire ; la pastille sous chaque maillon dit ce "
        "que vaut la réponse de ce paquet, y compris celle qu'il doit refuser.",
        "heads": ("LE MAILLON", "QUI Y RÉPOND LE MIEUX", "ET ICI"),
        "rows": (
            {
                "question": "Qu'est-ce qui a tourné, et combien\u202f?",
                "needs": "Une unité de travail nommée, et le compte de celles qu'une exécution "
                "complète accomplit.",
                "who": "Le dépôt lui-même. Green Metrics Tool décrit l'exécution dans un "
                "fichier ; Infracost et Carbonifer lisent un plan.",
                "mine": "lit votre code, puis exécute une tranche bornée si vous y consentez",
                "status": "measured",
            },
            {
                "question": "Qu'a-t-il tiré\u202f?",
                "needs": "Un compteur, et une règle de partage pour une machine que plusieurs "
                "choses utilisent.",
                "who": "Scaphandre, PowerAPI, JoularJX, Kepler, CEEMS, EnergiBridge — par "
                "processus, par méthode, par conteneur, par travail.",
                "mine": "lit le compteur de la machine ; refuse de le découper par processus",
                "status": "TODO",
            },
            {
                "question": "Qu'est-ce que cela coûte\u202f?",
                "needs": "Un tarif, une intensité carbone, une valeur d'eau, une empreinte "
                "matérielle.",
                "who": "Green Algorithms, Boavizta, Climatiq, Electricity Maps, Cloud Carbon "
                "Footprint — les catalogues sourcés.",
                "mine": "des catalogues sourcés, et un champ tenu ouvert là où rien n'est publié",
                "status": "estimated",
            },
            {
                "question": "Par quoi, et sur quoi cela repose-t-il\u202f?",
                "needs": "Un artefact commité que quelqu'un peut ouvrir dans une pull request et "
                "contester.",
                "who": "Presque personne. Un chiffre Software Carbon Intensity (SCI) déclaré, et "
                "celui-ci.",
                "mine": "chaque chiffre porte son statut et les chiffres dont il vient",
                "status": "measured",
            },
        ),
        "foot": (
            "Les pastilles sont les quatre statuts de ce paquet, appliqués à lui-même. Le "
            "deuxième maillon est celui qu'il refuse : un compteur mesure du matériel, donc la "
            "valeur qu'il lit est celle de la machine et non celle de l'exécution, et il le dit "
            "plutôt que de diviser par quelque chose de plausible. Ce refus est la sixième "
            "colonne du tableau plus haut, où cinq autres outils font mieux.",
        ),
        "alt": "La question «\u202fcombien coûte l'exécution de ce code\u202f» dessinée en "
        "quatre maillons dans l'ordre : ce qui a tourné et en quelle quantité, ce qu'il a tiré, "
        "ce que cela "
        "coûte, et par quoi et sur quoi cela repose. Sous chaque maillon figurent les outils qui "
        "y répondent le mieux — le dépôt et les lecteurs de plan pour le premier, les "
        "mesureurs de puissance pour le deuxième, les catalogues sourcés pour le troisième, "
        "presque personne pour le quatrième — et une pastille disant ce que vaut la réponse "
        "de ce paquet : measured, TODO, estimated, measured. Aucun outil de la page ne tient les "
        "quatre maillons.",
    },
}

#: Horizontal room for the four columns, with a gutter wide enough for an arrow
#: between neighbours to read as a handover rather than as a join.
GUTTER: Final[float] = 24.0


def _column(index: int) -> tuple[float, float]:
    """Return the left edge and the width of one of the four columns.

    Examples
    --------
    >>> left, width = _column(0)
    >>> left == MARGIN and width > 0
    True
    """
    usable = WIDTH - 2 * MARGIN - 3 * GUTTER
    width = usable / 4
    return MARGIN + index * (width + GUTTER), width


def draw(lang: str) -> str:
    """Return the figure in one language.

    Parameters
    ----------
    lang : str
        ``"en"`` or ``"fr"``.

    Returns
    -------
    str
        A standalone SVG, drawn in the report's palette, light and dark aware,
        and labelled for a reader who cannot see it.

    Examples
    --------
    >>> "prefers-color-scheme" in draw("en")
    True
    >>> draw("fr").count("<g>") == draw("en").count("<g>")
    True
    """
    words = LINKS[lang]
    heads: tuple[str, str, str] = words["heads"]  # type: ignore[assignment]
    rows: tuple[dict[str, str], ...] = words["rows"]  # type: ignore[assignment]
    parts: list[str] = []
    top = title_block(words, parts)  # type: ignore[arg-type]

    body_top = top

    # The three bands are laid out as three rows of four, each row sized to its
    # tallest card, so the arrows between neighbours stay horizontal and the
    # French text -- reliably longer -- never pushes one column out of line.
    bands: list[tuple[str, tuple[dict[str, object], ...], float]] = [
        (
            heads[0],
            tuple(
                {
                    "heading": row["question"],
                    "notes": (row["needs"],),
                    "accent": "accent",
                }
                for row in rows
            ),
            0.0,
        ),
        (
            heads[1],
            tuple({"lines": (row["who"],), "surface": "sunken"} for row in rows),
            0.0,
        ),
        (
            heads[2],
            tuple(
                {"lines": (row["mine"],), "pills": ((row["status"], row["status"]),)}
                for row in rows
            ),
            0.0,
        ),
    ]

    cursor = body_top
    middle = 0.0
    for band_index, (label, items, _) in enumerate(bands):
        cursor += 38 if band_index else 0
        parts.append(column_head(MARGIN, cursor, label))
        cursor += 18
        # Four cards of different heights read as an unfinished row, and the
        # difference carries no meaning: it is only the length of the sentence
        # inside, which is not the same length in two languages saying the same
        # thing. So the row is measured first and every card is floored to its
        # tallest. The floor grows the box and not the padding, because padding
        # narrows the text and a card made taller that way can wrap one more
        # line and overshoot the row it was being squared with.
        tallest = max(
            card(_column(index)[0], cursor, _column(index)[1], **item)[1]  # type: ignore[arg-type]
            for index, item in enumerate(items)
        )
        for index, item in enumerate(items):
            left, width = _column(index)
            parts.append(card(left, cursor, width, floor=tallest, **item)[0])  # type: ignore[arg-type]
        if not band_index:
            middle = cursor + tallest / 2
        cursor += tallest

    # One arrow per handover, across the gutters of the first band: the links
    # are an order, and an order is the one thing four columns of cards cannot
    # say on their own.
    for index in range(3):
        left, width = _column(index)
        parts.append(
            connector(left + width + 3, middle, _column(index + 1)[0] - 4, middle, curved=False)
        )

    bottom = _footer(parts, cursor + 30, words["foot"])  # type: ignore[arg-type]
    height = int(bottom + MARGIN)
    return (
        "\n".join(
            head("landscape-links", words["title"], words["alt"], height)  # type: ignore[arg-type]
            + parts
            + ["</svg>"]
        )
        + "\n"
    )


def _footer(parts: list[str], y: float, notes: tuple[str, ...]) -> float:
    """Write the closing note, and return the bottom of it.

    A thin wrapper so the figure's footer sits at the same size and leading as
    the front pages' figures, which it does by calling theirs.

    Examples
    --------
    >>> body: list[str] = []
    >>> _footer(body, 10, ("a note",)) > 10
    True
    """
    from make_readme_figures import footer

    return footer(parts, y, notes)


def main() -> None:
    """Write both files next to this one."""
    here = pathlib.Path(__file__).resolve().parent
    for lang, name in (("en", "landscape-links.svg"), ("fr", "landscape-links.fr.svg")):
        (here / name).write_text(draw(lang), encoding="utf-8")
        print(f"assets/{name}")


if __name__ == "__main__":
    main()
