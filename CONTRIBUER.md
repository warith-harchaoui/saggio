# Contribuer

🇫🇷 Français · [🇬🇧 CONTRIBUTING.md](CONTRIBUTING.md)

Merci de regarder. Les contributions les plus utiles à ce projet sont petites et
précises, et deux d'entre elles ne demandent pas une ligne de Python.

## Les deux contributions les plus faciles, et les plus précieuses

### Une ligne de catalogue

Le paquet ne peut pas connaître tous les accélérateurs, tous les réseaux
électriques nationaux, toutes les API payantes. Quand il en croise un qu'il ne
connaît pas, il le dit, par son nom :

```
GPU 'NVIDIA H300' is not in the catalogue; add it with
`saggio catalog add gpu` once you have a datasheet TDP
```

L'ajouter, c'est une commande et une pull request :

```bash
saggio catalog add gpu H300 \
    --source-url "https://www.nvidia.com/en-us/data-center/h300/" \
    --retrieved-date 2026-09-13 \
    --field tdp_w=800 \
    --field peak_bf16_tflops=2400
```

Cela l'écrit dans votre propre surcouche, où elle fonctionne immédiatement. Pour
la proposer en amont, recopiez la ligne dans le fichier correspondant sous
`saggio/data/` et ouvrez une pull request.

**Une ligne sans source ni date ne sera pas fusionnée.** Non par formalisme, mais
parce qu'un catalogue de chiffres non sourcés est du folklore, et que ce paquet
existe pour être l'inverse de ça. Mettez le lien : la fiche technique du
constructeur, la page du régulateur, le rapport de durabilité de l'hébergeur.
« Tout le monde sait qu'un A100 fait 400 watts » n'est pas une source.

### Un chiffre qui est faux

Si une valeur de `saggio/data/` est fausse ou a vieilli, dites-le, et dites ce
qu'elle devrait être et où vous l'avez lu. Les corrections sont ce qu'il y a de
plus précieux ici, et elles sont les bienvenues même sans correctif.

## Modifier le code

```bash
git clone https://github.com/warith-harchaoui/saggio
cd saggio
pip install -e ".[dev]"

pytest                   # toute la suite, y compris chaque exemple de docstring
ruff check .
ruff format --check .
```

Les trois doivent passer. La suite de tests exécute les doctests en plus des
tests : un exemple de docstring qui cesse d'être vrai fait échouer le build, et
c'est précisément pour ça qu'on les écrit.

### Ce qu'une modification doit apporter

**Un test qui échoue sans elle.** Pour un bug, un test qui le reproduit. Pour une
fonctionnalité, un test qui fige le comportement voulu. Une pull request sans test
est une affirmation que personne ne pourra vérifier plus tard.

**Des docstrings dans le style du fichier que vous modifiez.** Chaque fonction,
privées comprises, porte une docstring au format NumPy avec un exemple exécutable.
[`CODING.md`](CODING.md) dit pourquoi et en montre la forme.

**Un commentaire qui dit pourquoi, là où le pourquoi n'est pas évident.** Le code
de ce dépôt explique son raisonnement là où ce raisonnement n'était pas forcé.
Gardez cette habitude ; un commentaire qui redit ce que fait la ligne suivante est
pire que pas de commentaire.

**Rien qui devine.** C'est la seule règle qui fera renvoyer une pull request quelle
que soit la qualité du reste. Si un chiffre ne peut pas être établi, la réponse est
un `TODO` avec une phrase disant ce qui le résoudrait — jamais une valeur par
défaut plausible, jamais un zéro. « Il faut bien mettre quelque chose » est
exactement le raisonnement que ce paquet est bâti pour refuser.

## Où vivent les choses

```
model/       Ce qu'un modèle de coût veut dire. Aucune E/S, aucun réseau, aucun
             sous-processus. Une modification ici est une modification du schéma ;
             dites-le dans la pull request.
catalog/     Les faits sourcés et la règle de provenance.
estimate/    Des faits et des mesures vers des chiffres.
analyze/     Lire un dépôt, en exécuter une tranche, interroger un modèle local.
auditor.py   Tout le travail.
report/      Markdown, HTML, Word, PDF. Il assemble ; il n'écrit pas.
cli/         L'analyse des arguments et l'affichage, et rien d'autre.
reporting/   Ce dont le rapport HTML est fait : la coquille du document avec les
             jetons que le rendu remplit, la feuille de style, le script, les
             traductions. Des fichiers de leur propre nature, pas des chaînes
             Python.
```

Les dépendances ne pointent que dans un sens : `cli` peut importer `report`,
`report` peut importer `model`, et rien dans `model` n'importe quoi que ce soit
au-dessus. Une modification qui demande une exception à cela est une modification
qui demande d'abord une conversation.

`reporting/` est hors du paquet parce que ses fichiers s'éditent comme une feuille
de style, un script et une coquille HTML, pas comme du Python. Le rendu les lit via
`importlib.resources`, qui n'atteint que l'intérieur du paquet : une copie vit donc
dans `saggio/data/report/`, et c'est elle que la roue livre. Modifiez les
originaux, puis :

```bash
python reporting/sync.py
```

Un test de contrat lance `python reporting/sync.py --check` : une modification
faite dans la copie empaquetée fait échouer le build au lieu d'être livrée.

`docs/api.md` fonctionne pareil, dans l'autre sens : il est écrit *à partir* des
docstrings plutôt qu'à côté d'elles. Changez une signature publique ou la première
ligne d'une docstring publique, puis :

```bash
python docs/sync_api.py
```

Un test de contrat lance `python docs/sync_api.py --check` : une référence qui a
dérivé du paquet fait échouer le build au lieu d'induire un lecteur en erreur.

## Modifier le schéma

Le schéma du modèle de coût est versionné séparément du paquet. Dans une même
ligne majeure il ne fait que grandir : un modèle écrit l'an dernier continue de
valider.

- Ajouter un champ facultatif : très bien, incrémentez le mineur.
- Ajouter un champ obligatoire, en renommer un, ou changer ce qu'une valeur veut
  dire : c'est un incrément majeur, et il lui faut une raison qui vaille de casser
  tous les modèles déjà versionnés.

Si vous ajoutez un champ, ajoutez-le aussi au gabarit annoté, pour qu'un lecteur le
rencontre avec une phrase disant à quoi il sert.

## Signaler quelque chose

Une issue est surtout utile avec le modèle qui montre le problème.
`cost_of_running.yaml` est du YAML simple et sans risque à coller ; vérifiez
d'abord que le vôtre ne porte rien de confidentiel, car un modèle peut nommer des
services internes et des chemins de dépôt.

Pour tout ce qui a une dimension de sécurité, écrivez à l'adresse indiquée dans
`pyproject.toml` plutôt que d'ouvrir une issue publique.

## Licence

En contribuant, vous acceptez que votre contribution soit publiée sous la licence
[BSD 3-Clause](LICENSE), la même que le reste du projet.
