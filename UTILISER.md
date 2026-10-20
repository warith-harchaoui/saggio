# Cinq façons d'atteindre un même moteur

🇫🇷 Français · [🇬🇧 USING.md](USING.md)

Un modèle de coût est produit par une personne qui code et lu par quelqu'un
d'autre : une équipe RSE qui doit le déclarer, un contrôle de gestion qui doit
budgéter dessus, un auditeur qui doit y croire. La plupart de ces lectrices et
lecteurs n'installeront jamais un paquet Python, et certains poseront la question
en français à un agent plutôt qu'à un terminal.

Le moteur s'atteint donc par cinq surfaces, et cette page dit à quoi sert
chacune.

## La règle que les cinq suivent

**La bibliothèque est le moteur. Tout le reste est un adaptateur.** Une surface
lit une requête, appelle une fonction publique, met en forme ce qui revient.
C'est tout son travail.

Deux conséquences, vérifiées par des tests plutôt que laissées à la discipline :

- **Une surface ne peut rien faire que la bibliothèque ne sache pas faire.** Ce
  qu'elle ferait seule serait une capacité interdite à tous ceux qui appellent la
  bibliothèque, accessible seulement à qui a choisi la bonne porte.
- **Deux surfaces ne peuvent pas répondre différemment à la même question.** Le
  placement d'un chiffre dans un inventaire de gaz à effet de serre a été
  assemblé un temps à l'intérieur de la ligne de commande, où les autres surfaces
  ne pouvaient l'atteindre qu'en le recopiant. Il vit maintenant dans
  `placed_model`, et un test exige que la route HTTP renvoie exactement ce que
  renvoie la bibliothèque, champ par champ. Un paquet qui se contredirait sur la
  ligne où va un chiffre n'aurait aucune raison de trancher la question.

## 1. La bibliothèque

Pour un script, un notebook, un test, un autre paquet.

```python
import saggio

result = saggio.audit(".", options=saggio.AuditOptions(run=False, country="FR"))
print(saggio.overall_status(result.model))
print(saggio.placed_model(result.model)["placements"])
```

Tout ce que font les quatre autres surfaces est dans `saggio.__all__`, et un test
casse la construction si un nom de cette liste cesse d'exister. La référence est
[`docs/api.md`](docs/api.md), engendrée à partir des docstrings.

## 2. La ligne de commande

Pour une personne devant un terminal, et pour l'intégration continue, qui est le
même appelant sans les mains.

```bash
pip install saggio
saggio audit . --country FR --run -o cost_of_running.yaml
saggio scopes cost_of_running.yaml
saggio render cost_of_running.yaml -f html -o cost_of_running.html
saggio diff cost_of_running.yaml /tmp/now.yaml --threshold 10
```

C'est la seule surface qui exécutera votre code, et seulement avec un
consentement enregistré une fois par quelqu'un à qui on l'a demandé. Ce n'est pas
un hasard de rangement : mesurer exécute une tranche d'un dépôt avec les
permissions de qui a lancé le processus, et un terminal est le seul endroit où il
y a quelqu'un à qui demander.

## 3. L'API HTTP

Pour un navigateur, un service interne, une chaîne de reporting, ou un lecteur
qui ne devrait rien avoir à installer.

```bash
pip install "saggio[api]"
uvicorn saggio.api.app:app --host 127.0.0.1 --port 8000
```

La documentation interactive est alors en `/docs`, et les routes sont :

| Route | Ce qu'elle répond |
|---|---|
| `GET /health` | Quelle version tourne, et ce que ce déploiement refuse. |
| `POST /validate` | Ce modèle respecte-t-il les règles, dont celle du maillon faible ? |
| `POST /next` | Quel champ ouvert fermerait le plus de nombres, et lesquels ? |
| `POST /scopes` | Sur quelle ligne d'un inventaire de gaz à effet de serre va chaque chiffre ? |
| `POST /render` | Le rapport, en Markdown ou en page HTML autonome. |
| `POST /diff` | Ce qui a bougé entre deux modèles, et si la barrière tient. |
| `GET /catalog` et `GET /catalog/{name}` | Les faits que le paquet porte, chaque ligne avec la source d'où elle vient. |
| `GET /freshness` | Les chiffres que personne n'a relus dans leur propre fenêtre. |
| `POST /audit` | Lire un dépôt et renvoyer le modèle qu'il implique. |

Un modèle s'envoie soit en `cost_model`, document déjà analysé, soit en
`yaml_text`, le contenu d'un fichier `cost_of_running.yaml`. Les deux donnent la
même réponse, ce qui est aussi un test.

**Deux refus sont bâtis dans cette surface plutôt que configurés dessus.**

Elle n'exécute jamais le code d'un dépôt. Il n'existe aucune route pour mesurer,
donc rien à mal configurer et rien à confiner.

Elle ne clone rien sans que l'exploitant l'ait permis. `POST /audit` va chercher
une adresse choisie par le client, ce qui est une vraie capacité avec de vraies
conséquences : elle est donc éteinte sauf si `SAGGIO_API_ALLOW_CLONE` dit le
contraire. Éteinte, la route répond ce qu'il faudrait faire, pas une trace de
pile.

En conteneur, les deux surfaces à la fois, l'interrupteur de clonage éteint, le
système de fichiers en lecture seule et aucune capacité :

```bash
docker compose up --build
```

## 4. Le protocole d'agent

Pour une collègue qui pose la question avec ses mots, dans sa langue, à un agent
plutôt qu'à un terminal. C'est la surface qu'une équipe RSE utilise vraiment.

```bash
uvicorn saggio.api.mcp:app --host 127.0.0.1 --port 8000
# un agent se connecte sur http://127.0.0.1:8000/mcp
```

Les outils sont engendrés à partir du document OpenAPI de l'application. Le nom
d'un outil est l'identifiant de la route, sa description est la docstring de la
route, ses arguments sont les champs du modèle de requête. Rien n'est écrit deux
fois, donc rien ne peut dériver : une enveloppe écrite à la main serait une
seconde description du même point d'entrée, libre de contredire la première, et
la contradiction se verrait sous la forme d'un agent annonçant posément le
mauvais scope.

Les refus viennent avec. Il n'y a pas d'outil pour mesurer, puisqu'il n'y a pas
de route pour cela.

## 5. Le skill

Pour Claude, ou tout agent qui lit les
[Agent Skills](https://code.claude.com/docs/en/skills). Il vit dans
[`skills/saggio/`](skills/saggio/SKILL.md) et ce n'est pas une enveloppe autour
des quatre autres : c'est la méthode, écrite. Quelle question poser avant
d'auditer, quels nombres un agent ne doit jamais écrire de mémoire, comment
rapporter un chiffre avec son statut, et quand dire qu'un autre outil est la
bonne réponse.

Ses déclencheurs sont la partie qu'il vaut le plus la peine de soigner, car un
skill qui ne se charge pas est un skill qui n'existe pas.
[`DECLENCHEURS.md`](DECLENCHEURS.md) liste les formulations qui doivent l'atteindre, dans
le vocabulaire des équipes techniques comme dans celui des équipes RSE, et celles
qui ne le doivent pas. Les évaluations à côté du skill fixent les deux moitiés.

## Ce qu'une surface n'a pas le droit de faire

- **Inventer une capacité.** Si elle vaut la peine, elle vaut la peine dans la
  bibliothèque, où tout le monde l'atteint.
- **Garder sa propre copie d'une charge utile.** La forme qu'une surface renvoie
  est celle que la bibliothèque a produite.
- **Abaisser un refus.** Un nombre que la bibliothèque refuse d'écrire n'est pas
  un nombre qu'une route HTTP peut écrire, et un consentement que la ligne de
  commande demande n'est pas un consentement qu'un serveur peut supposer.

## Ce qu'une surface décide pour elle-même

- **La présentation.** Un tableau pour un terminal, du JSON pour un programme,
  une page pour un navigateur, une phrase pour un agent.
- **Quelles capacités elle offre.** La surface HTTP n'offre pas la mesure, parce
  qu'à travers un réseau il n'y a personne à qui demander un consentement.
- **Ce qu'un déploiement autorise.** Le clonage est la décision de l'exploitant,
  prise dans l'environnement plutôt que dans le code.

## La langue dans laquelle les cinq répondent

La langue d'un lecteur n'est pas de la présentation, et ses deux moitiés ne sont
pas le même problème.

**L'interface.** Chaque étiquette du rapport HTML vient d'un seul fichier de
traduction, et la page porte un bouton de langue construit depuis ce que ce
fichier contient : un lecteur change de langue dans son navigateur, sans réseau
et sans second fichier à livrer.

**La prose.** Une phrase du modèle de coût n'est pas lue dans un fichier : on
demande à un modèle local quelle forme de travail fait le dépôt, et il écrit sa
réponse dans le bloc `analysis`. C'est la seule phrase qui peut arriver dans la
mauvaise langue, et les surfaces prennent la langue de la même façon :

```bash
saggio audit . --country FR --language fr -o cost_of_running.yaml
```

```python
saggio.audit(".", options=saggio.AuditOptions(country="FR", language="fr"))
```

**La question.** Avant qu'un audit exécute une ligne du code de quelqu'un, il
demande — et il demande dans la même langue : une personne qui ne peut pas lire
les conditions n'a pas été interrogée. `saggio consent grant --language fr` les
affiche aussi, et la décision enregistrée dit à quelles conditions on a consenti
et dans quelle langue elles ont été lues.

**Chaque route qui répond par de la prose prend un champ `language`**, depuis
une seule définition, pour la même raison que la ligne de commande attache
`--language` à chaque verbe depuis un seul endroit : une surface qui propose une
langue sur certaines routes et pas sur d'autres est une surface dont il faut se
rappeler la forme. Les outils d'agent sont engendrés depuis ces routes : sept
d'entre eux prennent donc l'argument sans que personne l'ait écrit deux fois.
Les quatre autres — la santé, les deux lecteurs de catalogue, le rapport de
fraîcheur — répondent par des données, pas par de la prose.
`saggio.languages()` est ce depuis quoi tous sont construits —
une interface qui propose un sélecteur interroge donc la bibliothèque au lieu de
figer une liste qui se périme. Une étiquette dans laquelle rien n'est écrit
retombe sur l'anglais et le dit dans les notes, car un audit ne doit pas échouer
pour une histoire de langue.

**Les phrases du moteur passent dans un catalogue de messages**, module par
module, pour que `--language fr` les rende aussi et pas seulement l'ossature.
`saggio/data/messages/*.yaml` les porte, un fichier par langue ; une phrase nomme
ses arguments entre accolades, chaque langue peut donc mettre les nombres là où
sa grammaire les veut. Des tests de contrat refusent une clé que le code demande
et que rien ne fournit, une clé qu'une langue a et l'autre non, une formulation
que rien n'atteint, et une traduction qui renomme un argument. Au 2026-10-19, le
premier module passé — les placements d'inventaire — faisait sortir **11 % d'un
rapport statique** en français.

**Ce que le bouton seul ne change pas, mesuré.** Il échange **6,9 %** du texte
visible d'un rapport produit. L'ossature
bouge : titres, noms de colonnes, étiquettes du panneau what-if, phrases
d'équivalence. La substance, non : les notes, les méthodes, les mises en garde
et les refus sont écrits là où la mesure se fait, soit **209 littéraux de prose
de quatre mots ou plus dans 35 modules**, dont 4 % seulement sous `report/`. Une
seule définition, écrite dans `tests/contract/test_languages.py` et recalculée
là, pour que le compte ne puisse pas se périmer tout seul : passée sur l'arbre
qui citait 709 au départ, la même définition en compte 801 — et c'est cette
comparaison qu'un lecteur peut vérifier, 801 contre 209, et 53 modules contre
35.
Dire « le rapport est bilingue » serait une affirmation que personne n'a
établie. La *documentation* est bilingue, page pour page ; un rapport produit est
un cadre français autour de preuves anglaises.

**Une langue n'est pas un pays.** `--language fr` dit comment écrire une phrase
et rien sur l'endroit où le code tourne : le français s'écrit sur une douzaine
de réseaux électriques différents, et en déduire `--country FR` mettrait dans le
modèle un nombre que personne n'a établi.

**Ajouter une langue**, c'est ajouter un code de premier niveau à deux fichiers
— `reporting/i18n.yaml` pour les étiquettes et `saggio/data/prompts.yaml` pour
l'instruction — et rien d'autre. Un test de contrat refuse une langue que seul
l'un des deux porte : une page qu'une collègue lit dans sa langue avec, dedans,
une phrase engendrée dans une autre, c'est une seule livraison en deux langues.

## Ajouter une sixième

Écrire d'abord la fonction dans la bibliothèque, avec son exemple exécutable.
Puis l'adaptateur, assez court pour tenir sur un écran. Puis le test de contrat
qui dit que la nouvelle surface répond ce que répond la bibliothèque. Si
l'adaptateur se met à porter de la logique, cette logique est au mauvais endroit,
et le remède est de la descendre, pas de la tester deux fois.
