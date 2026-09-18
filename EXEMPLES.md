# Exemples

🇫🇷 Français · [🇬🇧 EXAMPLES.md](EXAMPLES.md)

Chaque commande montrée ici est analysée par le vrai analyseur d'arguments dans la
suite de tests, et les extraits de bibliothèque dont la sortie est affichée sont
exécutés. Une option renommée ou une arithmétique qui dérive fait rougir le build.

## Sommaire

- [La version en cinq minutes](#la-version-en-cinq-minutes)
- [Partir de rien](#partir-de-rien)
- [Auditer un dépôt](#auditer-un-dépôt)
- [Mesurer au lieu de deviner](#mesurer-au-lieu-de-deviner)
- [Projeter sur un autre matériel](#projeter-sur-un-autre-matériel)
- [Ajouter une dimension à vous](#ajouter-une-dimension-à-vous)
- [Les rapports](#les-rapports)
- [Tenir la ligne en intégration continue](#tenir-la-ligne-en-intégration-continue)
- [Les catalogues](#les-catalogues)
- [La bibliothèque](#la-bibliothèque)
- [Codes de sortie](#codes-de-sortie)

## La version en cinq minutes

```bash
pip install saggio

cd votre-projet
saggio audit . --country FR -o cost_of_running.yaml
saggio render cost_of_running.yaml -f html -o cost_of_running.html
open cost_of_running.html
```

Vous avez maintenant un modèle de coût où la durée est un `TODO`, parce que rien
n'a encore été exécuté, et où tout ce qui en dérive est un `TODO` aussi. C'est
l'état correct pour un modèle que personne n'a mesuré, et le rapport le dit en
tête.

Pour le rendre réel, mesurez-le :

```bash
saggio audit . --country FR --run -o cost_of_running.yaml
```

## Partir de rien

Deux points de départ sont livrés avec le paquet.

```bash
# Tout laissé ouvert, à remplir à la main.
saggio init --template minimal -o cost_of_running.yaml

# Un exemple travaillé, avec une vraie chaîne de calcul et une note par champ.
saggio init --template annotated -o cost_of_running.yaml
```

Le minimal n'avance aucun chiffre. C'est délibéré : un squelette rempli de valeurs
par défaut plausibles raconte un mensonge qui survit jusque dans un rapport, alors
qu'un squelette rempli de `TODO` dit la vérité sur lui-même.

Vérifiez-le dès que vous l'avez modifié :

```bash
saggio validate cost_of_running.yaml
```

```
Valid: 0 errors, 1 warning.
Weakest number anywhere in the model: TODO.
```

Les avertissements ne font jamais échouer un modèle. Un modèle qui reconnaît être
incomplet est honnête, et ce paquet ne punit pas l'honnêteté.

## Auditer un dépôt

```bash
saggio audit . --country FR -o cost_of_running.yaml
```

Lire un dépôt établit ce qu'il est : ses langages, sa forme, les frameworks qu'il
importe, la quantité de travail d'une exécution complète, et quelles API payantes
il appelle. Tout est déterministe et cite la ligne d'où ça vient.

Le code qui teste un dépôt est lu à part du code qu'il exécute. Une suite écrit
des fixtures, et une fixture qui écrit `import torch` dans un fichier temporaire
n'est pas un projet qui entraîne quoi que ce soit. Un framework est compté quand
une ligne l'importe vraiment, jamais quand une ligne contient seulement son nom :
une table de noms de frameworks dans un commentaire ne détecte rien. Ce que seule
la suite importe est rapporté sous `frameworks_in_suite_only`, et un service ou un
modèle dont l'unique ligne de preuve est un fichier de test arrive avec un
`caveat` qui le dit, au lieu d'être tarifé comme faisant partie de la charge.

Un service détecté ressemble à ceci dans le modèle :

```yaml
external_services:
  - key: openai
    name: OpenAI API
    detected_at: app/handlers.py:14
    evidence: from openai import OpenAI
    pricing_source_url: https://openai.com/api/pricing/
    price_per_unit:
      value: null
      status: TODO
```

Le tarif est laissé ouvert exprès. Un tarif recopié aujourd'hui sera faux au
trimestre prochain, donc l'audit note où vit le tarif du jour au lieu de faire
semblant de le connaître.

Auditer un dépôt que vous n'avez pas cloné :

```bash
saggio audit https://github.com/quelquun/leur-projet --country FR
```

Demander à un modèle local quelle forme a le travail, si Ollama tourne :

```bash
# Activé par défaut. Le modèle classe ; il ne fournit jamais un chiffre.
saggio audit . --country FR

# Désactivé.
saggio audit . --country FR --no-llm
```

### Depuis l'environnement

Deux choses peuvent être réglées une fois pour toutes au lieu d'être passées à
chaque appel, ce qui est exactement ce que veut un conteneur ou un job
d'intégration continue :

| Variable | Ce qu'elle règle |
|---|---|
| `SAGGIO_COUNTRY` | Le pays où le code tourne, en ISO 3166-1 alpha-2. Le renseigner ainsi est une affirmation humaine : cela compte donc comme `measured`, exactement comme `--country`. |
| `SAGGIO_MODEL` | Le tag du modèle Ollama pour la classification, au lieu du premier modèle préféré installé. |
| `OLLAMA_HOST` | Où Ollama écoute, quand ce n'est pas `http://127.0.0.1:11434`. |

```bash
export SAGGIO_COUNTRY=FR
saggio audit . -o cost_of_running.yaml
```

`--country` l'emporte sur la variable, et ni l'un ni l'autre n'est jamais deviné :
sans pays d'aucun des deux côtés, les chiffres carbone et argent restent ouverts.

### Tarifer les API qu'il appelle

Un tarif est par *modèle*, pas par fournisseur : `gpt-4o` et `gpt-4o-mini` sont la
même API à un facteur huit. L'audit lit donc l'identifiant du modèle dans votre
code, avec la ligne qui le nomme, et ne cherche les tarifs que si vous le
demandez :

```bash
saggio audit . --country FR --fetch-prices -o cost_of_running.yaml
```

```yaml
models_called:
  - model: gpt-4o
    detected_at: app.py:7
    evidence: model="gpt-4o",
    provider: openai
    rates:
      input_cost_per_token:
        value: 2.5e-06
        status: estimated
        unit: USD per input token
        currency: USD
        source_kind: aggregator
        source_url: https://github.com/BerriAI/litellm
        retrieved_date: '2026-09-13'
      output_cost_per_token: {...}     # huit tarifs en tout, pour ce seul modèle
    units_per_unit_of_work:
      value: null
      status: TODO
```

Trois choses y sont voulues.

**Aucune page web n'est analysée, et aucun modèle n'est interrogé sur ce qu'une
page dit.** Un tarif sur une page marketing échoue silencieusement et faussement :
un changement de mise en page renvoie l'ancien prix barré, ou le palier
entreprise, ou le tarif d'entrée en cache au lieu du tarif d'entrée. Seules les
sources publiées *en tant que données* sont lues.

**`source_kind` dit à quelle distance le chiffre est de celui qui le fixe.**
`stated` quand un humain l'a écrit, `first-party` quand il vient de l'API de prix
du vendeur, `aggregator` quand il vient de la transcription d'un tiers. Les
fournisseurs de grands modèles ne publient pas d'API de prix : leurs tarifs sont
donc `aggregator`, et le modèle le dit au lieu de l'habiller. `saggio diff` échoue
quand la provenance d'un prix s'affaiblit, exactement comme quand un statut
s'affaiblit.

**Le tarif est connu ; l'usage ne l'est pas.** Combien de tokens consomme une
unité de travail n'est pas établi par la lecture du code : ça reste `TODO`. Le
modèle montre précisément quelle moitié manque.

Sans `--fetch-prices`, rien ne touche le réseau et l'audit produit le même modèle
que hors ligne, tarifs laissés ouverts.

## Mesurer au lieu de deviner

### Une commande à vous

```bash
saggio measure -- python train.py --steps 100
```

```
Ran: python train.py --steps 100
Exit code: 0
Wall-clock: 12.481 s
Average power: 96.3 W (measured)
     8.204 s  train.py:88(train_step)
     2.106 s  dataloader.py:41(__next__)
```

La puissance est mesurée là où la machine veut bien la dire, à partir de deux
compteurs et non d'un seul. Sous Linux avec un processeur Intel, le compteur
d'énergie du paquet donne le processeur. Sur toute machine portant une carte
NVIDIA, le pilote donne l'accélérateur sans aucun privilège, soit par un compteur
d'énergie cumulée, soit, sur les cartes qui n'en tiennent pas, par la moyenne de
relevés pris toutes les demi-secondes pendant la course. C'est l'accélérateur qui
compte : un processeur qui tire 50 W à côté d'une carte qui en tire 300 est une
machine à 350 W, et un modèle qui rapporterait les 50 W se tromperait d'un facteur
sept.

Ce qui a répondu est nommé dans le rapport, et ce qui n'a pas répondu aussi. Les
deux compteurs donnent un chiffre qui dit ce qu'il laisse de côté ; l'accélérateur
seul dit que le processeur manque ; si aucun ne répond, le rapport affiche
`not measured` et le modèle retombe sur une estimation étiquetée comme telle. Sous
macOS, aucun compteur n'est lisible sans privilèges, d'un côté comme de l'autre.

Les deux lignes sous le total sont le profil par fonction, et elles se paient.
`cProfile` facture à l'appel : une charge riche en appels peut mettre presque deux
fois plus de temps sous lui, et le temps affiché ci-dessus est celui de
l'exécution profilée. La commande le dit dans un avertissement. Quand c'est la
durée qui vous intéresse et non l'endroit où elle est passée, prenez-la sans le
profileur :

```bash
saggio measure --no-profile -- python train.py --steps 100
```

### Mettre la mesure dans le modèle

Une mesure affichée dans un terminal est un nombre que personne n'a gardé.
`--into` l'écrit dans un modèle et recalcule tout ce qui en découle :

```bash
saggio measure --into cost_of_running.yaml --units 500 -- python predict.py --n 500
```

```
  runtime: not known -> 0.0011 s, TODO -> measured
  time: not known -> 0.0011 s, TODO -> measured
  energy: not known -> 3.93e-08 kWh, TODO -> estimated
  money: not known -> 9.43e-09 USD, TODO -> estimated
  carbon: not known -> 2.2e-06 gCO2e, TODO -> estimated
  whole run: projected from the per-unit costs above
```

C'est l'étape qu'on rate à la main. Coller une durée dans le YAML laisse l'énergie,
l'argent et le carbone sur leurs anciennes valeurs, et un modèle dont l'énergie ne
correspond plus à sa durée est pire qu'un modèle qui n'avait ni l'une ni l'autre,
parce qu'il a l'air fini. Chaque chiffre ci-dessus est recalculé à partir des
hypothèses du modèle lui-même, par les fonctions qu'emploie l'audit, et le résultat
est validé avant que quoi que ce soit ne soit écrit.

`--units 500` dit que la commande a effectué cinq cents unités de travail : la
durée enregistrée est donc par unité. Quand le modèle sait déjà quelle quantité de
travail effectue une exécution complète, une projection sur cette exécution découle
des coûts unitaires.

Trois choses sont refusées plutôt qu'écrites : une commande sortie en non-zéro,
parce qu'une exécution ratée a mesuré un échec et qu'un échec n'a pas de coût par
unité de travail ; un modèle sans scénario où écrire ; et tout résultat qui ne
validerait plus. Rien n'est écrit à moitié, et un pliage qui change six nombres les
affiche tous les six.

```bash
saggio measure --into cost_of_running.yaml --scenario production -- pytest -q
```

### Une tranche du dépôt de quelqu'un d'autre

```bash
saggio consent grant
saggio audit . --country FR --run -o cost_of_running.yaml
```

L'audit exécute une tranche plafonnée de votre vrai point d'entrée. Le plafond
vient de votre propre configuration, donc la tranche couvre une part connue :

```yaml
projections:
  whole_run:
    costs:
      energy:
        method: Whole run = measured slice / 0.001.
        result:
          value: 0.0016
          unit: kWh
          status: estimated
        limits:
          - A run whose later stages differ in shape will not scale linearly.
```

Quand il n'y a pas de point d'entrée avec une taille annoncée, c'est la suite de
tests du dépôt qui est exécutée. Elle couvre une part inconnue d'une vraie charge
de travail, donc aucune projection sur l'exécution complète n'en découle, et
l'audit le dit exactement.

## Projeter sur un autre matériel

La plupart des modèles de coût sont écrits sur un portable. Projeter depuis un
portable demande de dire quelle machine la mesure représente :

```bash
saggio audit . --country FR --run \
    --source-accelerator RTX-4090 \
    --target-accelerator H100
```

```yaml
projections:
  on_other_hardware:
    source: RTX-4090
    target: H100
    runtime:
      method: Runtime on H100 = runtime on RTX-4090 / 3.32, where 3.32 is the
        memory bandwidth ratio, 3350 / 1008 GB/s.
      result:
        value: 13.79
        unit: s
        status: estimated
      bounds:
        fastest: {value: 7.65, unit: s, status: estimated}
        slowest: {value: 13.79, unit: s, status: estimated}
    power_draw:
      value: 700.0
      unit: W
      status: estimated
    costs:
      energy: {value: 0.0032, unit: kWh, status: estimated}
      money: {value: 0.00077, unit: USD, status: estimated}
      carbon: {value: 0.18, unit: gCO2e, status: estimated}
    held_constant: The country, the tariff, the grid carbon intensity and the
      datacenter overhead are the ones stated for this deployment.
```

Deux choses limitent une charge sur un accélérateur, et une projection qui n'en
connaît qu'une est optimiste par construction. Le débit arithmétique limite le
travail qui garde les unités de calcul occupées ; la bande passante mémoire limite
le travail qui passe son temps à déplacer des poids. Entre une 4090 et une H100,
ces deux rapports valent 6,0 et 3,3 : la réponse est donc un encadrement, pas un
nombre. L'estimation ponctuelle est le rapport de calcul quand la lecture a établi
que la charge est limitée par le calcul, le rapport de bande passante quand elle a
établi l'inverse, et le plus lent des deux quand elle n'a rien établi, parce que le
rapport le plus lent, c'est l'exécution la plus longue et la facture la plus lourde.

La projection va jusqu'à l'argent et au carbone, pas seulement jusqu'à une durée,
parce qu'une durée n'est pas la question posée. Elle tient le pays, le tarif et le
mix électrique constants, et elle le dit : faire tourner le travail sur un autre
accélérateur, c'est en général le faire tourner ailleurs, et c'est l'endroit qui
fixe le prix.

Le chiffre de débit vient de la colonne du catalogue correspondant à la précision
dans laquelle le travail tourne. Demandez-en une que le catalogue ne porte pas et
il refuse, plutôt que de mettre à l'échelle avec un chiffre qui parle d'une autre
arithmétique :

```bash
saggio audit . --run \
    --source-accelerator RTX-4090 --target-accelerator H100 --precision fp32
```

```
Read before trusting this model:
  - The catalogue has no peak_fp32_tflops for 'RTX-4090' and 'H100', so there is
    no fp32 ratio to scale by. Add it with `saggio catalog add gpu RTX-4090
    --field peak_fp32_tflops=...` from the vendor datasheet, or measure on the
    target.
```

## Ajouter une dimension à vous

Déclarez-la en tête du modèle, puis servez-vous-en comme d'une clé de coût
ordinaire :

```yaml
dimensions:
  - key: "egress"
    label: "Trafic sortant"
    unit: "GB"
    description: "Octets quittant le datacenter pour répondre à une requête."

scenarios:
  - name: "default"
    costs:
      egress:
        value: 0.004
        unit: "GB"
        status: "measured"
```

Rien dans le paquet n'a besoin de changer. Le validateur la tient aux mêmes règles,
le rapport lui donne une ligne, et la barrière de dérive la surveille.

Pour dire que davantage vaut mieux plutôt que pire :

```yaml
dimensions:
  - key: "throughput"
    label: "Débit"
    unit: "req/s"
    description: "Requêtes servies par seconde en régime établi."
    higher_is_worse: false
```

La barrière de dérive échoue désormais quand il *baisse*.

## Les rapports

```bash
# Pour une pull request.
saggio render cost_of_running.yaml -f md -o cost_of_running.md

# Pour tous les autres : une page autonome, hors ligne, claire et sombre, EN et FR.
saggio render cost_of_running.yaml -f html -o cost_of_running.html

# Pour un document. Demande `pip install "saggio[office]"`.
saggio render cost_of_running.yaml -f docx -o cost_of_running.docx
saggio render cost_of_running.yaml -f pdf -o cost_of_running.pdf

# À votre charte graphique.
saggio render cost_of_running.yaml -f docx -o cost_of_running.docx \
    --reference-doc assets/template.docx
```

La page HTML embarque sa propre feuille de style, son script, son logo et les
données de catalogue dont elle a besoin : elle s'ouvre sans aucun réseau. Son
panneau « et si » recalcule carbone et argent pour un autre pays dans le
navigateur, à partir de l'énergie que le modèle annonce déjà. Un modèle sans
énergie annoncée n'a pas de panneau, parce qu'un « et si » bâti sur une base
inventée serait le pire chiffre de la page.

## Tenir la ligne en intégration continue

```yaml
# .github/workflows/cout.yml
- name: Le coût d'exécution a-t-il dérivé ?
  run: |
    pip install saggio
    saggio validate cost_of_running.yaml
    saggio audit . --country FR -o /tmp/maintenant.yaml
    saggio diff cost_of_running.yaml /tmp/maintenant.yaml --threshold 10
```

`diff` échoue sur trois choses, et c'est la troisième qu'on oublie :

```bash
saggio diff avant.yaml apres.yaml
```

```
scenarios[0].costs.energy: 0.001 -> 0.0016 (+60.0%), worse
scenarios[0].costs.carbon: measured -> estimated
scenarios[0].costs.water: gone, was measured
3 change(s), 3 past the 10% gate.
```

Un chiffre qui a empiré au-delà du seuil. Un statut qui s'est affaibli, parce que
le modèle en sait désormais moins qu'avant même quand le chiffre est identique. Et
une quantité qui a disparu, parce que la façon habituelle dont un coût cesse
d'être rapporté, c'est que quelqu'un a supprimé le champ.

## Les catalogues

```bash
saggio catalog list gpu
saggio catalog list country --json
saggio catalog list service
```

Une ligne manquante est une issue normale, et l'outil nomme ce qu'il n'a pas
trouvé :

```
Read before trusting this model:
  - GPU 'NVIDIA H300' is not in the catalogue; add it with
    `saggio catalog add gpu` once you have a datasheet TDP
```

```bash
saggio catalog add gpu H300 \
    --source-url "https://www.nvidia.com/en-us/data-center/h300/" \
    --retrieved-date 2026-09-12 \
    --field tdp_w=800 \
    --field peak_bf16_tflops=2400
```

La ligne atterrit dans votre propre surcouche, sert immédiatement, et pourra être
proposée en amont plus tard. Sans source ni date elle est refusée, et c'est cette
règle qui rend les catalogues dignes de confiance.

Demander quels chiffres ont discrètement vieilli :

```bash
saggio catalog freshness   # sort en 1 si quoi que ce soit a vieilli
```

Tarifs et mix électriques périment en un mois, consommations de fiche technique en
un an. Un seuil unique se mettrait soit à râler sur un GPU, soit à laisser passer
le tarif d'électricité de l'an dernier.

## La bibliothèque

Tout ce que fait la ligne de commande, elle le fait en appelant ceci.

```python
import saggio

# Auditer un dépôt.
resultat = saggio.audit(".", options=saggio.AuditOptions(country="FR", use_llm=False))
print(resultat.report.summary())
for note in resultat.notes:
    print("-", note)

# Le rendre.
open("cout.md", "w").write(saggio.render_markdown(resultat.model))
open("cout.html", "w").write(saggio.render_html(resultat.model))
```

Valider un modèle que vous avez construit vous-même :

```python
from saggio import CostModel, validate

modele = CostModel.load("cost_of_running.yaml")
rapport = validate(modele)
if not rapport.ok:
    print(rapport.to_text())
```

Calculer une étape de la chaîne à la main :

```python
from saggio import Quantity, carbon_from_energy, energy_from_runtime

duree = Quantity(value=3600.0, unit="s", status="measured")
puissance = Quantity(value=400.0, unit="W", status="estimated")
surcout = Quantity(value=1.2, unit="ratio", status="estimated")

energie = energy_from_runtime(duree, puissance, surcout)
carbone = carbon_from_energy(energie, Quantity(value=56, unit="gCO2e/kWh", status="estimated"))

print(energie.value, energie.status)   # 0.48 estimated
print(carbone.value, carbone.status)   # 26.88 estimated
```

Le statut est `estimated` et non `measured` bien que la durée ait été mesurée,
parce que la puissance ne l'a pas été. C'est la règle du maillon faible, appliquée
par l'arithmétique elle-même.

Demander ce qu'est cette machine :

```python
from saggio import detect_machine

machine = detect_machine()
print(machine.describe())
for manque in machine.catalog_misses:
    print("-", manque)
```

Comparer deux modèles :

```python
from saggio import compare

comparaison = compare(avant, apres, threshold_percent=10.0)
for changement in comparaison.changes:
    print(changement.describe())
if not comparaison.passes():
    raise SystemExit(1)
```

## Codes de sortie

| Code | Sens |
|---|---|
| `0` | Tout a marché. |
| `1` | Le modèle ou le catalogue a échoué à ses propres règles. |
| `2` | On a demandé à la commande quelque chose qu'elle ne sait pas faire. |
| `3` | L'accord a été refusé pour quelque chose dont la commande avait besoin. |
| `4` | Une dépendance externe manque ou a échoué. |

La distinction entre `1` et `2` est celle dont l'intégration continue a besoin :
faire échouer le build sur le premier, s'arrêter et regarder la commande sur le
second.
