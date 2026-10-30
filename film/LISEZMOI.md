# Le film

Quatre-vingt-douze secondes sur ce à quoi sert ce paquet, en anglais et en
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
make-film poster film/out/what-it-costs.fr.mp4 --out film/out/what-it-costs.fr.jpg --at 74.88

make-film verify film/film.yaml --root .                 # les chiffres tiennent-ils encore
make-film scan film/composition/index.fr.html --spec film/film.yaml   # ce qui est à l'écran et que nul n'a déclaré
make-film pitch film/film.yaml --duration 91.76          # le problème, puis la solution, puis l'idée
make-film prose film/film.yaml --lang fr                 # les tics de machine nommés
sprezzature-audio-audit film/out/what-it-costs.en.vtt --line-chars 58
sprezzature-audio-audit film/out/what-it-costs.fr.vtt --line-chars 58 --cps 20
```

Les deux pistes ressortent propres, et les deux commandes diffèrent exprès.

`--line-chars 58` plutôt que les 42 de Netflix : 58 est la largeur à laquelle
le rédacteur de sous-titres de `sprezzature-video` coupe une ligne, donc c'est
le nombre qui gouverne réellement ce fichier.

`--cps 20` sur la piste française, et rien sur l'anglaise. Le montage anglais
tient sous le plafond de 17 caractères par seconde que l'audit applique par
défaut, le chiffre de Netflix pour un public adulte : il tourne à 15,5 en
moyenne et culmine à 16,6. Le montage français n'y tient pas, et à 17 l'audit
rend quarante-sept constats sur cinquante-cinq sous-titres. Ce n'est pas ce
script. Le montage français tourne à 17,7 caractères par seconde et ne dépasse
jamais 19,9 ; le français dépense plus de caractères pour la même phrase, donc
un plafond étalonné sur l'anglais signale une piste qu'un lecteur français suit
très bien. L'aide de l'audit dit elle-même que ses valeurs par défaut sont des
conventions et non des lois, et que chacune est un signal : c'est la licence
employée ici — 20 est donc le plafond que ce maximum mesuré réclame, écrit
plutôt que le signal supprimé, et la personne suivante peut le contester.

Le seul constat qui était un vrai défaut a été corrigé plutôt que reclassé :
un sous-titre tenait **d'exécution,** seul pendant 0,755 seconde, parce que
la ligne se coupait au milieu du syntagme. L'appel à l'action français tient
maintenant en trois phrases courtes, et chacune a son souffle.

Deux autres portes méritent d'être passées, et l'une des deux ne peut pas
répondre ici :

```bash
make-film assets film/film.yaml --tree . --repo .   # un clone peut-il refabriquer
make-film calque film/film.yaml --from en --to fr   # le second montage est-il une traduction
```

`assets` rend 9 sur 9 : rien de ce dont ce film est fait n'existe seulement sur
la machine qui l'a fabriqué.

`calque` donne 0,89 à ce film et continuera de le faire. Elle compare les deux
montages position par position sur le nombre de phrases que porte une ligne et
les chiffres qu'elle contient — or la narration d'ici est découpée à une phrase
par ligne et ne contient aucun chiffre, si bien que 26 lignes anglaises sur 27
et 25 françaises sur 25 se réduisent au même `(1, ())`. Elle compare deux suites
quasi constantes, ce que sa propre documentation exclut : *un film dont chaque
ligne est une phrase sans chiffre obtiendra un score élevé et peut être
parfaitement composé.* Le score ne dit rien de ce français-là. Il faut lire les
deux montages côte à côte, ce que la porte demande de toute façon.

## Le rendu

Les images sont capturées avec Playwright et assemblées avec ffmpeg plutôt que
par Hyperframes. `sprezzature-video` nomme les deux comme moteurs de rendu
derrière la même couture, et la page qui publie ce film fonctionne hors ligne
sans étape de construction propre : la chaîne de dépendances la plus courte
était celle à prendre.

Les images déjà présentes sur le disque sont conservées : un rendu mort à
l'image 900 repart de l'image 900. Cela ne tient que si la page est restée la
même, et une fois ce ne fut pas le cas : en refabriquant un montage français
remonté, le script a repris 2139 images du montage précédent, n'a tiré que les
63 que le plus long ajoutait, et a assemblé un film qui se lisait, affichait une
durée plausible et montrait l'ancien script pendant quatre-vingt-neuf secondes.
Aucune porte d'ici ne lit les pixels : aucune ne pouvait l'attraper. Les images
portent désormais l'empreinte de leur composition dans
`frames/<langue>/.composition` et sont jetées quand celle-ci change — si un
rendu annonce bien moins d'images prises que d'images sur le disque, c'est ce
nombre-là qu'il faut regarder.
