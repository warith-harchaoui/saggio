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

La puissance est mesurée là où le système veut bien la dire. Sous Linux avec un
processeur Intel, c'est le compteur d'énergie du paquet processeur. Sous macOS et
Windows, aucun compteur n'est lisible sans privilèges : le rapport affiche donc
`not measured` et le modèle retombe sur une estimation étiquetée comme telle.

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
      method: Runtime on H100 = runtime on RTX-4090 x (165 / 989) peak bf16 TFLOP/s.
      result:
        value: 7.65
        unit: s
        status: estimated
```

La mise à l'échelle est un rapport de débits crêtes, ce qui ne veut dire quelque
chose que si le travail est limité par le calcul et que la précision fait partie
de celles que le catalogue chiffre. Demandez une précision dont il ne sait pas
parler et il refuse plutôt que de deviner :

```bash
saggio audit . --run \
    --source-accelerator RTX-4090 --target-accelerator H100 --precision fp32
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
    --retrieved-date 2026-09-13 \
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
