# Le gabarit de rapport

🇫🇷 Français · [🇬🇧 README.md](README.md)

Tout ce dont le rapport HTML est fait, sous forme de fichiers plutôt que de
chaînes citées dans du Python : une coquille, une feuille de style, un script,
une table de traduction et un logo.

```
report.html   la coquille du document, avec les jetons que le rendu remplit
report.css    toute l'apparence : palette, mise en page, règles d'impression, les deux thèmes
report.js     le sélecteur de thème, le sélecteur de langue, le recalcul « et si »
i18n.yaml     chaque chaîne affichée, un bloc par langue
logo.png      incorporé en URI data:, pour que la page n'ait besoin d'aucun réseau
sync.py       recopie tout cela dans le paquet qui le livre
```

## Pourquoi ils vivent ici

Le rendu lit ses ressources via `importlib.resources`, qui ne sait aller que dans
le paquet : une copie se trouve donc dans
`saggio/data/report/`, et c'est elle que la roue livre. Ce
dossier-ci est l'original ; la copie est l'artefact.

On édite ici, puis :

```bash
python reporting/sync.py           # recopier dans le paquet
python reporting/sync.py --check   # code de retour non nul si les deux diffèrent
```

Un test de contrat lance cette vérification : éditer la copie packagée par erreur
fait échouer le build au lieu de partir en livraison sans bruit.

## La coquille, et ses jetons

`report.html` ne contient aucun contenu propre. Le rendu remplace chaque jeton et
incorpore le reste, et c'est ce qui fait de la page finie un fichier unique qui
s'ouvre hors ligne.

| Jeton | Ce qu'on y met |
|---|---|
| `{{LANG}}` | L'étiquette BCP 47 du document, `en` aujourd'hui |
| `{{TITLE}}` | Le titre du rapport, déjà échappé |
| `{{LOGO}}` | Une URI `data:`, servant de favicon et d'icône dans la barre |
| `{{STYLE}}` | Le contenu de `report.css` |
| `{{LANGUAGES}}` | Un `<option>` par langue trouvée dans `i18n.yaml` |
| `{{BODY}}` | Les sections rendues |
| `{{PROJECT_URL}}` | Lié depuis le pied de page |
| `{{DATA}}` | Le modèle en JSON, que le script lit pour recalculer dans le navigateur |
| `{{SCRIPT}}` | Le contenu de `report.js` |

La substitution est un remplacement de texte, pas un `str.format` : la feuille de
style et le script sont pleins d'accolades à eux. Un jeton non rempli lève une
erreur, parce qu'un rapport contenant un `{{BODY}}` littéral serait pire qu'un
échec.

## S'en servir pour ses propres rapports

Le trio est volontairement neutre : aucun chiffre dedans, aucune formulation
propre à ce projet au-delà du décor, et aucun framework. `report.css` est une
feuille de style avec des propriétés personnalisées sur `:root`, `report.js` est
un script sans aucun import.

Pour produire des rapports d'une autre forme, copiez `report.html`, `report.css`
et `report.js` ailleurs et remplissez les jetons vous-même, dans le langage que
vous voulez. Gardez-les tous et la page garde ses propriétés : autonome,
imprimable, claire et sombre, traduite.

Ce qu'on change en premier :

- **La palette**, ce sont les propriétés personnalisées en haut de `report.css`.
  Les couleurs de statut (`--measured`, `--estimated`, `--placeholder`, `--todo`)
  portent du sens : gardez-les distinguables pour un lecteur daltonien, et gardez
  le statut écrit à côté de la couleur, comme le fait déjà la page.
- **Les chaînes**, c'est `i18n.yaml`, indexé sur les attributs `data-i18n` du
  balisage. Un nouveau code de langue au premier niveau ajoute une langue ; le
  sélecteur se construit à partir de ce que contient le fichier.
- **Le décor**, c'est le `<nav>` et le `<footer>` de `report.html`. Rien dans le
  script n'en dépend, sauf `#theme-toggle` et `#language-picker`.

## Ce qu'on ne change pas sans y penser

La page avance des chiffres, donc elle porte les règles qui les rendent lisibles :
chaque valeur montre son statut, et chaque valeur dérivée montre d'où elle vient.
Enlevez ces colonnes et la page s'affiche toujours, mais elle ne dit plus jusqu'où
on peut lui faire confiance, ce qui est la seule raison d'être de ce rapport.
