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
[`TRIGGERS.md`](TRIGGERS.md) liste les formulations qui doivent l'atteindre, dans
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

## Ajouter une sixième

Écrire d'abord la fonction dans la bibliothèque, avec son exemple exécutable.
Puis l'adaptateur, assez court pour tenir sur un écran. Puis le test de contrat
qui dit que la nouvelle surface répond ce que répond la bibliothèque. Si
l'adaptateur se met à porter de la logique, cette logique est au mauvais endroit,
et le remède est de la descendre, pas de la tester deux fois.
