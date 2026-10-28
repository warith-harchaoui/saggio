# Le film

Quatre-vingt-quatre secondes sur ce à quoi sert ce paquet, en anglais et en
français, servies depuis la page d'accueil de
[deraison.ai/saggio](https://deraison.ai/saggio).

Un film est le pire endroit où mettre un chiffre. La prose d'un fichier
README se relit ; un nombre gravé dans une image-clé, non, et il reste faux
en silence. Chaque compte que ce film énonce est donc déclaré dans
`claims.yaml`, à côté de l'endroit du code qui le tranche, et
`make-film verify` échoue dès que le code et le film cessent d'être d'accord.

## Les pièces

| Fichier | Ce qu'il porte |
|---|---|
| `script.yaml` | Ce que le film dit et montre, scène par scène, dans les deux langues. Le contenu. |
| `claims.yaml` | Chaque chiffre énoncé, le fichier qui le tranche, et comment lire ce fichier. Écrit à la main ; relu en diff. |
| `lexicon/` | Comment la voix prononce les mots qu'elle raterait autrement. |
| `film.yaml` | Le contrat vérifiable que lit `make-film`. Généré : ne pas éditer. |
| `composition/` | Une page autonome par langue. `seek(t)` est une fonction pure du temps : le moteur de rendu peut demander n'importe quelle image et obtenir les mêmes pixels. |
| `narration/` | Un fichier audio par scène et par langue, et les durées mesurées dessus. Les coupes en découlent au lieu d'être saisies. |

## Le refabriquer

Quatre étapes, dans cet ordre. Chacune lit ce que la précédente a écrit.

```bash
python film/narrate_film.py          # la voix, via sprezzature-audio
python film/compose.py               # les deux compositions, calées sur cette voix
python film/make_spec.py             # film.yaml : les affirmations et les durées dérivées
python film/render_film.py           # les images, puis deux films MPEG-4 (MP4) dans film/out/
```

Puis les parties qu'une fonction porte, et les quatre contrôles :

```bash
make-film captions film/film.yaml --lang fr --out film/out/what-it-costs.fr.vtt
make-film poster film/out/what-it-costs.fr.mp4 --out film/out/what-it-costs.fr.jpg --at 49.2

make-film verify film/film.yaml --root .                 # les chiffres tiennent-ils encore
make-film scan film/composition/index.fr.html --spec film/film.yaml   # ce qui est à l'écran et que nul n'a déclaré
make-film pitch film/film.yaml --duration 84.37          # le problème, puis la solution, puis l'idée
make-film prose film/film.yaml --lang fr                 # les tics de machine nommés
sprezzature-audio-audit film/out/what-it-costs.fr.vtt --line-chars 58
```

`--line-chars 58` plutôt que les 42 de Netflix : 58 est la largeur à laquelle
le rédacteur de sous-titres de `sprezzature-video` coupe une ligne, donc c'est
le nombre qui gouverne réellement ce fichier. Les deux cues encore jugées
rapides tiennent au débit de la voix sur une scène, ce que l'aide de l'audit
appelle une raison de déplacer le seuil plutôt qu'un défaut.

## Le rendu

Les images sont capturées avec Playwright et assemblées avec ffmpeg plutôt que
par Hyperframes. `sprezzature-video` nomme les deux comme moteurs de rendu
derrière la même couture, et la page qui publie ce film fonctionne hors ligne
sans étape de construction propre : la chaîne de dépendances la plus courte
était celle à prendre.
