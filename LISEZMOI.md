<p align="center">
  <img src="assets/logo.png" alt="saggio" width="120">
</p>

# saggio

🇫🇷 Français · [🇬🇧 README.md](README.md)

**Combien coûte l'exécution de votre code ?** L'argent, le temps, l'énergie, le
carbone, l'eau, et toute autre dimension que vous décidez de suivre, par unité de
travail, chaque chiffre disant jusqu'où on peut lui faire confiance.

La réponse est un fichier YAML que vous versionnez à côté du code, et des rapports
qui en sont tirés. Le fichier se relit dans une pull request, les rapports se
lisent par des gens qui n'ouvriront jamais un terminal, et ni l'un ni l'autre n'a
le droit d'avancer un chiffre sans dire d'où il vient.

```bash
pip install saggio

saggio audit . --country FR --run -o cost_of_running.yaml
saggio render cost_of_running.yaml -f html -o cost_of_running.html
```

## L'idée

Chaque chiffre porte un **statut** :

| Statut | Ce que ça veut dire |
|---|---|
| `measured` | Un compteur de la machine l'a dit. |
| `estimated` | Une formule sourcée ou un chiffre publié l'a dit. |
| `placeholder` | Le champ est tenu ouvert. Ce n'est pas un nombre. |
| `TODO` | Quelqu'un doit le remplir avant qu'on puisse faire confiance au modèle. |

Et chaque chiffre dérivé nomme les chiffres dont il vient :

```yaml
costs:
  carbon:
    value: 0.0014
    unit: "gCO2e"
    status: "estimated"
    derived_from: ["scenarios[0].costs.energy", "assumptions.grid_carbon_intensity"]
```

De là découle la **règle du maillon faible**, et le validateur la fait respecter :
une valeur dérivée ne peut jamais prétendre être mieux fondée que la pire de ses
entrées. Mesurez la durée et l'énergie devient mesurée toute seule. Laissez le pays
non renseigné et le chiffre carbone reste ouvert, parce que personne ne le connaît
encore.

Trois propriétés en découlent, et ce sont elles qui justifient le dessin :

- **Rien ne peut se cacher.** Le validateur parcourt tout le fichier. Un nombre
  hors d'une quantité est une erreur, où qu'il soit et dans quel bloc que ce soit,
  donc un bloc supplémentaire ne peut pas faire passer un chiffre sous la règle.
- **La règle est générale.** Puisque la dérivation est une donnée et non du code,
  une dimension que vous avez inventée ce matin est vérifiée aussi soigneusement
  que le carbone.
- **Rien n'est inventé.** Un pays non résolu donne un `TODO`, pas un zéro. Un
  hébergeur qui ne publie aucun chiffre d'eau donne un `TODO`, pas un chiffre
  plausible. Une exécution qui a échoué ne se projette sur rien du tout.

## Ce que l'outil fait

**Il lit votre dépôt.** Langages, forme de la charge de travail, frameworks,
quantité de travail d'une exécution complète, quelles API payantes vous appelez et
à quelle ligne. Tout est déterministe, tout cite sa preuve.

**Il en exécute une tranche, si vous l'autorisez.** Avec `--run`, et après votre
accord donné une fois, il lance une tranche plafonnée de votre vrai point
d'entrée, la chronomètre, lit les compteurs d'énergie que la machine publie à un
utilisateur ordinaire, et profile où le temps est passé. Sous Linux, c'est
l'arborescence powercap, zone mémoire comprise, et le capteur du pilote
graphique ; sur un Mac Apple Silicon, ce sont les compteurs de la puce elle-même,
lus sans mot de passe ; sur toute machine dotée d'une carte NVIDIA, c'est le
pilote. `saggio power` dit lesquels répondent ici, et affiche ce qu'il faudrait
pour ouvrir les autres — sans jamais les ouvrir lui-même. La part du travail que
couvre la tranche est lue dans votre propre configuration : projeter sur une
exécution complète relève donc de l'arithmétique, pas de la devinette.

**Il cherche plutôt que de supposer.** Ce que consomme un GPU, ce qu'émet un
kilowattheure en Pologne, ce qu'ajoute un datacenter, où une API publie ses tarifs :
des catalogues YAML sourcés, chaque ligne portant l'URL d'où elle vient et la date
à laquelle quelqu'un l'a lue, chacune périmant selon un délai adapté à la vitesse
à laquelle ce genre de fait bouge vraiment.

**Il projette, et il dit ce qu'il a supposé.** D'une tranche mesurée à une
exécution complète. D'un accélérateur à un autre, et jusqu'à l'argent et au
carbone plutôt que de s'arrêter à une durée. Cette seconde projection est un
encadrement, pas un nombre : une charge est limitée par le débit arithmétique ou
par la bande passante mémoire, les deux rapports diffèrent de plus du double entre
une A100 et une H100, et ne rapporter que le rapport de calcul sous-estimerait la
facture d'un tiers. Il refuse net quand le catalogue n'a aucun chiffre de débit
pour la précision dans laquelle le travail tourne.

**Il écrit des rapports qui se lisent.** Du Markdown pour une pull request. Une
page HTML autonome pour tous les autres : hors ligne, clair et sombre, anglais et
français, avec un panneau qui recalcule le modèle pour un autre pays dans le
navigateur et un graphique de ce que le réseau électrique ferait au carbone
ailleurs. Word et PDF via `md2star` quand c'est un document qu'on attend. Chaque
chiffre de carbone connu est aussi restitué en termes qu'un lecteur peut
ressentir — des mois-arbre de séquestration, des kilomètres en voiture moyenne,
une fraction d'un vol Paris–Londres — avec les coefficients de
[Green Algorithms](https://doi.org/10.1002/advs.202100707), et sans gagner en
confiance au passage : un chiffre ouvert reste ouvert, et un chiffre mesuré se
lit `estimated`, parce que l'arbre est un arbre moyen.

**Il montre l'équipe, pas seulement le projet.** `saggio dashboard` rend tous les
modèles de coût commités sur une seule page. Elle ouvre sur la seule comparaison
honnête entre projets — la part de chaque modèle qui est mesurée, estimée, ou
encore ouverte — et dit clairement que les lignes de coûts, chacune par unité de
travail propre à son projet, ne se comparent pas entre elles.

**Il fait échouer votre build quand un coût dérive.** `diff` compare deux modèles
et échoue sur un coût qui a empiré au-delà d'un seuil, sur un statut qui s'est
affaibli, et sur une quantité qui a discrètement disparu.

## Installation

```bash
pip install saggio
```

Trois dépendances d'exécution, et c'est voulu.
[`os-helper`](https://pypi.org/project/os-helper/) répond à toutes les questions
sur la machine et le système, sous macOS, Linux et Windows indifféremment. PyYAML
lit les modèles et les catalogues. `platformdirs` trouve le répertoire de
configuration de l'utilisateur. Tout le reste, ce paquet le fait lui-même.

Word et PDF demandent une chose de plus, et seulement si vous les voulez :

```bash
pip install "saggio[office]"
```

Pour conda :

```bash
conda env create -f environment.yaml
conda activate env-for-saggio
```

## S'en servir

```bash
# Partir d'un exemple travaillé, ou d'un squelette où tout est laissé ouvert.
saggio init --template annotated -o cost_of_running.yaml

# Le vérifier contre le schéma et les règles d'honnêteté.
saggio validate cost_of_running.yaml

# Lire un dépôt et en écrire le modèle.
saggio audit . --country FR -o cost_of_running.yaml

# Le lire, et exécuter une tranche plafonnée pour mesurer ce qu'il coûte vraiment.
saggio audit . --country FR --run -o cost_of_running.yaml

# Ça coûterait quoi sur un H100, à partir d'une mesure prise sur un 4090 ?
saggio audit . --country FR --run \
    --source-accelerator RTX-4090 --target-accelerator H100

# Mesurer une commande à vous.
saggio measure -- python train.py --steps 100

# Cette machine, c'est quoi, et le catalogue connaît-il ses composants ?
saggio machine

# Transformer le modèle en quelque chose qui se lit.
saggio render cost_of_running.yaml -f html -o report.html

# Faire échouer le build quand un coût a dérivé.
saggio diff main.yaml branche.yaml --threshold 10
```

La bibliothèque fait la même chose sans l'affichage :

```python
import saggio

resultat = saggio.audit(".", options=saggio.AuditOptions(country="FR"))
print(resultat.report.summary())
print(saggio.render_markdown(resultat.model))
```

[`EXEMPLES.md`](EXEMPLES.md) est le livre de recettes,
[`GALERIE.md`](GALERIE.md) montre ce qu'il dit de nanoGPT, Whisper, DINOv2,
FastAPI et Airflow, fichiers commités à l'appui, [`docs/api.md`](docs/api.md)
liste tout ce que `import saggio` donne, et [`docs/`](docs/LISEZMOI.md) est la
carte du reste.

## Exécuter votre code, et ce que ça implique

Mesurer ce que coûte l'exécution d'un code, c'est l'exécuter. Il n'y a pas de bac
à sable ici et on n'en fait pas semblant : le dépôt étudié s'exécute sous votre
identité, avec vos permissions et votre accès réseau.

L'accord est donc explicite, demandé une seule fois, et enregistré là où vous
pouvez le retrouver et le révoquer :

```bash
saggio consent grant
saggio consent revoke
```

Sans lui, `--run` ne fait rien et l'audit se poursuit sur la seule lecture. Une
session sans terminal est refusée plutôt que traitée par défaut : un serveur
d'intégration ne peut jamais accepter à votre place.

## Ce que l'outil ne fait jamais

Il ne met jamais dans un fichier un chiffre que personne n'a choisi. Le pays est
indiqué par une personne, ou déduit du fuseau horaire de la machine et étiqueté
comme déduction ; il n'est jamais lu dans une locale puis écrit comme un fait.

Il n'analyse jamais une page de tarification, et ne demande jamais à un modèle ce
qu'une page raconte. Avec `--fetch-prices`, il lit des tarifs dans des sources
publiées *en tant que données*, note quel modèle le code nomme et à quelle ligne,
et estampille chaque tarif de l'endroit et de la date de lecture. Un tarif venu de
l'API de prix du vendeur et un tarif venu de la transcription d'un tiers sont tous
deux `estimated` : chacun porte donc en plus un `source_kind` qui dit lequel, et la
porte de dérive échoue quand celui-ci s'affaiblit. Sans le drapeau, rien ne touche
le réseau et le tarif reste ouvert, pointant la page où vit le chiffre du jour.

Il ne laisse jamais un modèle de langue fournir un chiffre. Un modèle local, quand
vous en avez un qui tourne, se voit demander quelle forme de travail fait votre
dépôt, et rien d'autre. Sa réponse est étiquetée du nom du modèle et marquée de
confiance faible. Chaque chiffre vient d'un fichier qu'on peut ouvrir ou d'un
compteur qu'on peut lire.

Et il ne compte jamais ce qu'il ne peut pas compter. La fabrication du matériel,
les gens, les bureaux, la capacité inutilisée : tout cela est listé comme exclu
dans le rapport, parce qu'une empreinte qui laisse discrètement de côté le plus
gros terme est pire qu'aucune empreinte.

## D'où viennent les chiffres

La méthode est celle de [Green Algorithms](https://doi.org/10.1002/advs.202100707)
(Lannelongue, Grealey et Inouye, 2021) : la puissance multipliée par le temps
donne l'énergie, l'énergie multipliée par une intensité carbone donne le carbone,
l'énergie multipliée par un tarif donne l'argent, l'énergie multipliée par un
rendement d'usage de l'eau donne l'eau.

Une distinction est tenue, et elle se perd facilement. La machine consomme une
quantité ; le bâtiment consomme cette quantité multipliée par son rendement
énergétique. Le carbone et l'argent suivent le bâtiment, parce que c'est ce que
compte le compteur. L'eau suit la machine, parce que le rendement d'usage de l'eau
se définit par kilowattheure de charge informatique et qu'utiliser le chiffre du
bâtiment compterait le refroidissement deux fois.

Consommations matérielles, intensités carbone, tarifs et rendements de datacenter
vivent dans [`saggio/data/`](saggio/data/),
une ligne chacun avec sa source et sa date. Une ligne manquante est une issue
normale, et l'outil vous dit laquelle par son nom :

```bash
saggio catalog list gpu
saggio catalog add gpu H300 \
    --source-url https://www.nvidia.com/... --retrieved-date 2026-09-12 \
    --field tdp_w=800 --field peak_bf16_tflops=2400
saggio catalog freshness   # sort en 1 quand un chiffre a vieilli
```

Une ligne ne peut pas être ajoutée sans source ni date. C'est cette règle qui rend
les catalogues dignes de confiance.

## Comment c'est agencé

```
model/      Ce qu'un modèle de coût veut dire : la taxonomie, la quantité, les
            dimensions, le schéma, la validation. Aucune E/S, aucun réseau,
            aucun sous-processus.
catalog/    Des faits sourcés sur le monde, et la règle qu'une ligne sans
            provenance n'entre pas.
estimate/   Des faits et des mesures vers des chiffres : la machine, le
            déploiement, la chaîne Green Algorithms, les projections.
analyze/    Ce qu'est un dépôt : le lire, en exécuter une tranche, et interroger
            un modèle local sur sa forme (jamais sur ses chiffres).
auditor.py  Tout le travail, dans une fonction.
diff.py     Ce qui a changé entre deux modèles, et si cela fait échouer le seuil.
templates.py  Les modèles de départ que le paquet livre.
report/     Markdown, HTML, Word, PDF.
cli/        L'analyse des arguments et l'affichage. Rien d'autre.
```

Les dépendances ne pointent que dans un sens, si bien que la ligne de commande ne
peut rien faire qu'un appelant de la bibliothèque ne puisse faire.

Les pièces du rapport HTML s'écrivent hors du paquet, dans
[`reporting/`](reporting/) : la coquille du document avec les jetons que le rendu
remplit, la feuille de style, le script, les traductions. Ce sont là une feuille
de style et un script, et non des chaînes citées dans du Python ;
`reporting/sync.py` les recopie dans le paquet qui les livre, et un test fait
échouer le build si les deux viennent à diverger. Copiez ce trio pour produire
des rapports d'une autre forme.

## Contribuer

[`CONTRIBUER.md`](CONTRIBUER.md) donne les détails. En bref : ajoutez une
ligne de catalogue avec sa source et sa date, ou un test qui fige un comportement
qui compte pour vous. [`CODING.md`](CODING.md) décrit le style de ce dépôt.

```bash
pip install -e ".[dev]"
pytest          # plus de 1000 vérifications, dont chaque exemple de chaque docstring
ruff check .
ruff format --check .
```

## Travaux voisins

[`PAYSAGE.md`](PAYSAGE.md) situe cet outil à côté de CodeCarbon, Green Algorithms,
Scaphandre, PowerAPI, Cloud Carbon Footprint et le reste du domaine, et dit
honnêtement là où chacun d'eux est le meilleur choix.

## Le nom

*Saggio*, en italien, c'est l'essai d'un métal : on prélève un échantillon, on en
détermine le titre, et le résultat est poinçonné avec le nom de qui l'a déterminé
et la date. Le mot veut dire aussi l'essai qu'on écrit, et il veut dire avisé.
Les trois sens sont le propos. Cet outil prélève une tranche plafonnée d'une
vraie exécution, dit à quel point chaque chiffre est fondé, et note d'où vient
chaque valeur et à quelle date quelqu'un l'a lue.

## Licence

[BSD 3-Clause](LICENSE). Warith Harchaoui, Ph.D.
