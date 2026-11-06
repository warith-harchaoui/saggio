# Le film

Quatre-vingt-dix secondes sur ce à quoi sert ce paquet, en anglais et en
français, en paysage, en portrait et en carré, servies depuis la page
d'accueil de [deraison.ai/saggio](https://deraison.ai/saggio).

C'est un film Sprezzature. Il suit l'ordre de tous les films de cette suite,
celui de Guy KAWASAKI : ce que c'est, le problème, la solution, la recette,
le plus bel exemple, puis la demande. Contrairement aux films de la suite, il
n'affiche pas le nom de ces étapes en haut de l'image. Le générateur de la
suite le dessine
lui-même, `brag-output/build_films.py` : il ressemble à ces films parce que
le même code le fabrique.

Un film est le pire endroit où mettre un chiffre. La prose d'un fichier
README se relit ; un nombre gravé dans une image, non, et il reste faux en
silence. Chaque chiffre que ce film énonce est donc déclaré dans
`claims.yaml`, à côté de l'endroit du code qui le tranche, et
`make-film verify` échoue dès que le code et le film cessent d'être d'accord.

## Les pièces

| Fichier | Ce qu'il contient |
|---|---|
| `script.yaml` | Ce que le film dit et montre, scène par scène, dans les deux langues. Le contenu. |
| `claims.yaml` | Chaque chiffre énoncé, le fichier qui le tranche, et comment lire ce fichier. Écrit à la main ; relu en diff. |
| `lexicon/` | Comment la voix prononce les mots qu'elle raterait autrement. |
| `narration/` | Une piste par langue, ses repères, et `measured.json` : quand chaque phrase commence et s'arrête. |
| `film.yaml` | Le contrat vérifiable que lit `make-film`. Généré : ne pas éditer. |
| `hf/` | Un projet HyperFrames par langue et par format. Généré, non versionné. |

## Le refabriquer

Il faut le dépôt Sprezzature à côté de celui-ci (`~/sprezzature`, ou
`SPREZZATURE_FILMS` pointé sur son dossier `brag-output`), Node pour
HyperFrames, et ffmpeg.

```bash
python film/narrate_film.py          # la voix, via sprezzature-audio
python film/compose.py               # six projets, coupés sur cette voix
python film/make_spec.py             # film.yaml : les affirmations et les durées mesurées
python film/render_film.py           # six films, affiches et sous-titres dans film/out/
```

Chaque étape lit ce que la précédente a écrit ; aucun temps n'est saisi à la
main.

- **La voix** est celle que `speaker-helper` choisit pour chaque langue, la
  même question que posent les films de la suite : les deux séries parlent
  d'une seule voix. Chaque langue se lit en un appel, une phrase par segment,
  ce qui rend un repère par phrase sur l'audio produit. Chatterbox tire au
  sort, et il arrive qu'une phrase s'emballe ; une phrase lue à moins de la
  moitié du débit médian de sa langue renvoie toute la langue à la lecture.
- **Les coupes** tombent dans le silence entre la dernière phrase d'une scène
  et la première de la suivante, sur le temps de musique le plus proche quand
  il tombe dans ce silence. Chaque apparition dans une scène arrive sur la
  phrase qui la nomme. Un texte qui dépasse quatre-vingt-dix secondes allonge
  le film : la voix n'est jamais coupée.
- **Les sous-titres** sortent de `make-film captions`, à partir du texte et
  de ces repères : ils disent ce que dit la voix, phrase pour phrase, dès
  qu'elle commence, et restent affichés pendant le silence qui suit. Ils voyagent en piste WebVTT séparée et ne sont
  jamais incrustés dans l'image : le lecteur les propose, le spectateur les
  active.

Puis les contrôles :

```bash
make-film verify film/film.yaml --root .                 # les chiffres tiennent-ils encore
make-film scan film/hf/saggio-fr-landscape/index.html --spec film/film.yaml
make-film pitch film/film.yaml --duration 90             # le problème, la solution, puis l'idée
make-film prose film/film.yaml --lang fr                 # les tics de machine nommés
sprezzature-audio-audit film/out/what-it-costs.en.vtt --line-chars 58
sprezzature-audio-audit film/out/what-it-costs.fr.vtt --line-chars 58 --cps 20
```

`--cps 20` sur la piste française : le français dépense plus de caractères
pour la même phrase, si bien que le plafond de 17 caractères par seconde,
chiffre de Netflix pour l'anglais, signale une piste qu'un lecteur français
suit parfaitement.

## Le rendu

`render_film.py` rend chaque projet avec les options des films Sprezzature :
en 4K, la mise en page de chaque format à quatre fois plus de pixels, en flux
plutôt qu'en images stockées, pour qu'un film ne réclame pas soixante
gigaoctets de disque. Chaque film est ensuite mesuré, durée et taille
d'image : un rendu interrompu laisse un film trop court, un rendu périmé
laisse l'ancien.
