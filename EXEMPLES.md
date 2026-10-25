# Exemples

🇫🇷 Français · [🇬🇧 EXAMPLES.md](EXAMPLES.md)

Chaque commande montrée ici est analysée par le vrai analyseur d'arguments dans
la suite de tests ; les extraits de bibliothèque dont la sortie est affichée
sont exécutés. Une option renommée ou une arithmétique qui dérive fait rougir le
build.

## Sommaire

- [La version en cinq minutes](#la-version-en-cinq-minutes)
- [Partir de rien](#partir-de-rien)
- [Auditer un dépôt](#auditer-un-dépôt)
- [Mesurer au lieu de deviner](#mesurer-au-lieu-de-deviner)
- [Projeter sur un autre matériel](#projeter-sur-un-autre-matériel)
- [Ajouter une dimension à vous](#ajouter-une-dimension-à-vous)
- [Les rapports](#les-rapports)
- [À quelle question répondre en premier](#à-quelle-question-répondre-en-premier)
- [Sur quelle ligne d'un bilan va chaque coût](#sur-quelle-ligne-dun-bilan-va-chaque-coût)
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
n'a encore été exécuté, comme tout ce qui en dérive. C'est l'état correct pour
un modèle que personne n'a mesuré, et le rapport le dit en tête.

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

Lire un dépôt établit ce qu'il est : ses langages, sa forme, les frameworks
qu'il importe, la quantité de travail d'une exécution complète, quelles API
(interface de programmation applicative) payantes il appelle. Tout est
déterministe et cite la ligne d'où ça vient.

Le code qui teste un dépôt est lu à part du code qu'il exécute. Une suite écrit
des fixtures ; une fixture qui écrit `import torch` dans un fichier temporaire
n'est pas un projet qui entraîne quoi que ce soit. Un framework est compté quand
une ligne l'importe vraiment, jamais quand une ligne contient seulement son nom
: une table de noms de frameworks dans un commentaire ne détecte rien. Ce que
seule la suite importe est rapporté sous `frameworks_in_suite_only`, et un
service ou un modèle dont l'unique ligne de preuve est un fichier de test arrive
avec un `caveat` qui le dit, au lieu d'être tarifé comme faisant partie de la
charge.

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
saggio audit https://github.com/karpathy/nanoGPT --country FR
```

Demander à un modèle local quelle forme a le travail, si Ollama tourne :

```bash
# Activé par défaut. Le modèle classe ; il ne fournit jamais un chiffre.
saggio audit . --country FR

# Désactivé.
saggio audit . --country FR --no-llm
```

### Dans la langue du lecteur

Cette phrase est le seul morceau d'un modèle de coût qui soit écrit plutôt que
lu : c'est donc le seul qui puisse arriver dans une langue que personne n'a
demandée.

```bash
saggio audit . --country FR --language fr -o cost_of_running.yaml
```

Le même dépôt, le même modèle local, les deux langues côte à côte :

```yaml
# --language en (par défaut)
analysis:
  evidence_source: static + llm:qwen3-vl:8b
  workload_kind: command-line-tool
  confidence: low
  dominant_operation: media processing
  reasoning: The repository primarily uses ffmpeg for media processing, which is
    compute-bound.
  prose_language: en

# --language fr
analysis:
  evidence_source: static + llm:qwen3-vl:8b
  workload_kind: command-line-tool
  confidence: low
  dominant_operation: traitement de médias
  reasoning: L'outil utilise ffmpeg pour traiter des médias, ce qui est intensif
    en calcul.
  prose_language: fr
```

`workload_kind` ne bouge pas, ce qui est le but : il est comparé à un ensemble
fermé, donc jamais traduit, tandis que `prose_language` enregistre la langue
demandée. La phrase reste de la prose à faible confiance produite par un modèle,
jamais un chiffre — `confidence: low` et `evidence_source` le disent sur la
ligne elle-même.

`saggio audit --help` liste les langues. En ajouter une, c'est deux fichiers de
traduction et pas une ligne de code ; `saggio.languages()` est ce sur quoi
chaque surface est bâtie.

### Depuis l'environnement

Deux choses peuvent être réglées une fois pour toutes au lieu d'être passées à
chaque appel, ce qui est exactement ce que veut un conteneur ou un job
d'intégration continue :

| Variable | Ce qu'elle règle |
|---|---|
| `SAGGIO_COUNTRY` | Le pays où le code tourne, en code à deux lettres de l'Organisation internationale de normalisation (ISO 3166-1 alpha-2). Le renseigner ainsi est une affirmation humaine : cela compte donc comme `measured`, exactement comme `--country`. |
| `SAGGIO_MODEL` | Le tag du modèle Ollama pour la classification, au lieu du premier modèle préféré installé. |
| `OLLAMA_HOST` | Où Ollama écoute, quand ce n'est pas `http://127.0.0.1:11434`. |

```bash
export SAGGIO_COUNTRY=FR
saggio audit . -o cost_of_running.yaml
```

`--country` l'emporte sur la variable ; ni l'un ni l'autre n'est jamais deviné :
sans pays d'aucun des deux côtés, les chiffres carbone et argent restent
ouverts.

### Tarifer les API qu'il appelle

Un tarif est par *modèle*, pas par fournisseur : `gpt-4o` et `gpt-4o-mini` sont
la même API à un facteur huit. L'audit lit donc l'identifiant du modèle dans
votre code, avec la ligne qui le nomme, puis ne cherche les tarifs que si vous
le demandez :

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

**Aucune page web n'est analysée. Aucun modèle n'est interrogé sur ce qu'une
page dit.** Un tarif sur une page marketing échoue silencieusement et faussement
: un changement de mise en page renvoie l'ancien prix barré, ou le palier
entreprise, ou le tarif d'entrée en cache au lieu du tarif d'entrée. Seules les
sources publiées *en tant que données* sont lues.

**`source_kind` dit à quelle distance le chiffre est de celui qui le fixe.**
`stated` quand un humain l'a écrit, `first-party` quand il vient de l'API de
prix du vendeur, `aggregator` quand il vient de la transcription d'un tiers. Les
fournisseurs de grands modèles ne publient pas d'API de prix : leurs tarifs sont
donc `aggregator`, ce que le modèle dit au lieu de l'habiller. `saggio diff`
échoue quand la provenance d'un prix s'affaiblit, exactement comme quand un
statut s'affaiblit.

**Le tarif est connu ; l'usage ne l'est pas.** Combien de tokens consomme une
unité de travail n'est pas établi par la lecture du code : ça reste `TODO`. Le
modèle montre précisément quelle moitié manque.

Sans `--fetch-prices`, rien ne touche le réseau et l'audit produit le même modèle
que hors ligne, tarifs laissés ouverts.

## Mesurer au lieu de deviner

### Ce que cette machine accepte de vous dire

Avant qu'une mesure vaille quoi que ce soit, il faut savoir ce qu'est la
machine, ce qu'elle accepte de dire, et à qui.

```bash
# Ce qu'est cette machine : processeur, cœurs, mémoire, accélérateur, plateforme.
saggio machine

# Et ce que ses compteurs d'énergie vous diront.
saggio power
```

`machine` est ce que l'audit lit quand il écrit une hypothèse de puissance,
imprimé à part pour qu'une figure inattendue puisse être remontée jusqu'à la
pièce d'où elle vient. `--json` pour une chaîne de traitement.

```
[reads] Linux powercap (RAPL)
    covers: the processor package and its memory
    Zones answering: dram, package-0, package-1.

[reads] NVIDIA driver (nvidia-smi)
    covers: the whole accelerator board
    The board keeps an accumulated energy counter, which is read exactly.

[absent] Linux graphics driver (amdgpu, i915, xe)
    covers: the graphics device
    No graphics device here publishes a power sensor through sysfs.

[root-only] Baseboard controller (IPMI, DCMI, Redfish)
    covers: the whole node, including fans, storage, and the power supply's losses
    ...
```

Quatre états, un seul étant une question qui vous revient. `absent` est une
propriété de la machine, pas un échec. `root-only` est un compteur que ce paquet
refuse d'aller chercher, délibérément. `reads` ne demande rien à personne.
`blocked` est le cas intéressant : le compteur est là et il vous est fermé — ce
qui, sous Linux, est le défaut depuis la 5.10, parce que l'échantillonner assez
vite permet de reconstituer ce que calculent les autres processus : l'attaque
PLATYPUS, inscrite au catalogue Common Vulnerabilities and Exposures sous
CVE-2020-8694. Le remède est donc affiché plutôt qu'exécuté, avec sa raison à
côté :

```
[blocked] Linux powercap (RAPL)
    covers: the processor package, and the memory where a zone exists for it
    2 zone(s) are here and closed to you. Linux has kept this counter root-only
    since 5.10 on purpose: sampled fast enough it leaks what other processes are
    computing (CVE-2020-8694, the PLATYPUS attack). Opening it to a group is a
    judgement about who shares this machine, which is why it is printed here
    rather than done for you.
    to open it: Until the next reboot:  sudo chmod a+r /sys/class/powercap/*/energy_uj
        Across reboots, a udev rule that touches the energy files and nothing else.
```

Rien ici n'escalade. Pas de `sudo`, pas de demande de mot de passe, pas de repli
silencieux sur un outil qui en réclamerait un. Rouvrir un canal auxiliaire publié
sur une machine que vous partagez peut-être est une décision : elle reste la
vôtre.

Pour voir les compteurs fonctionner avant qu'une exécution en dépende, demandez
une mesure de la machine elle-même :

```bash
saggio power --seconds 2
```

```
Over 2s this machine drew 27.2 W (54.3 J) through system-on-chip, memory.
```

Ce chiffre est celui de la *machine*, pas de votre programme : tout ce qui tourne
par ailleurs y est. Un portable qui tire 27 W sans rien faire pour vous, c'est
exactement pourquoi une tranche chronométrée sur une machine occupée n'est pas le
coût propre de cette tranche — et pourquoi chaque chiffre imprimé ici dit ce
qu'il couvre.

### Une commande à vous

```bash
saggio measure -- python train.py --steps 100
```

```
Ran: python train.py --steps 100
Exit code: 0
Wall-clock: 12.481 s
Average power: 96.3 W (measured)
  machine at rest before it: 18.7 W
  added by this slice: 77.6 W
     8.204 s  train.py:88(train_step)
     2.106 s  dataloader.py:41(__next__)
```

Trois chiffres de puissance, parce qu'un compteur mesure la *machine* et non
votre programme. La machine est observée une seconde avant le début de la
tranche ; la différence est ce que la tranche a ajouté. Sur un portable avec un
navigateur et un indexeur qui tournent, cette différence est le seul des trois
chiffres qui mérite d'être cité.

La soustraction suppose quelque chose que personne n'a vérifié — que le reste de
la machine a continué à faire ce qu'il faisait — donc l'hypothèse est écrite
dans le modèle à côté du nombre. Deux cas sont dits à voix haute plutôt que
soustraits : une machine qui tirait déjà plus de la moitié du total est signalée
comme occupée ; une machine devenue *plus calme* pendant la tranche ne donne
aucun chiffre marginal, parce que ce qui tournait par ailleurs s'est arrêté et
que la ligne de base n'a jamais été le plancher de cette tranche.

Sur une machine que vous savez calme, passez outre et gagnez la seconde :

```bash
saggio measure --baseline 0 -- python train.py --steps 100
```

Un audit prend le même réglage ; une série de mise à l'échelle prend **une**
ligne de base pour toute l'échelle plutôt qu'une par barreau — les barreaux
s'enchaînent sur la même machine, trois lignes de base mesureraient trois fois
le même repos :

```bash
saggio audit . --country FR --run --baseline 0 --scaling-steps 3 -o cost_of_running.yaml
```

**L'ajustement qu'elle écrit se vérifie sur ses propres preuves.** Le bloc
conserve les tailles et les secondes sur lesquelles il a été ajusté, l'exposant
comme quantité et — depuis qu'il a cessé de ne vivre que dans la phrase de
méthode — le coefficient, le `a` de `y = a · x^b`. Avec les quatre, un lecteur
refait le calcul :

```
taille  25 : l'ajustement prédit 0,072682 s, 0,073587 s observé   (1,2 %)
taille 100 : l'ajustement prédit 0,188343 s, 0,183739 s observé   (2,5 %)
taille 400 : l'ajustement prédit 0,488059 s, 0,494136 s observé   (1,2 %)
```

Un test de contrat fait exactement cela sur chaque modèle commité. Un second
exige que les deux nombres épelés par la phrase de méthode soient ceux que
portent les champs. Avant que le coefficient soit un champ, les observations
étaient conservées pour une vérification que personne ne pouvait faire.

































































Sur une machine qui ne publie aucun compteur, il n'y a rien à passer : la ligne de
base rend « non mesuré » immédiatement au lieu de regarder pendant une seconde un
instrument qui n'existe pas.

La puissance est mesurée à partir des compteurs que cette machine publie — ceux
que `saggio power` vient d'énumérer. Sous Linux, c'est l'arborescence powercap :
chaque paquet, la zone `psys` de préférence aux paquets qu'elle contient, la
zone mémoire à côté, dont l'énergie n'est *pas* dans le chiffre du paquet. Sur
un Mac Apple Silicon, ce sont les compteurs de la puce : cœurs du processeur,
cœurs graphiques, moteur neuronal et mémoire, lus sans mot de passe. Sur toute
machine portant une carte NVIDIA, le pilote répond, soit par un compteur
d'énergie cumulée, soit, sur les cartes qui n'en tiennent pas, par la moyenne de
relevés pris toutes les demi-secondes pendant la course ; quand ce n'est pas
NVIDIA qui est présent, les pilotes `amdgpu`, `i915` et `xe` de Linux publient
la même chose par sysfs, à un utilisateur ordinaire.

C'est en général l'accélérateur qui compte : un processeur qui tire 50 W à côté
d'une carte qui en tire 300 est une machine à 350 W, si bien qu'un modèle qui
rapporterait les 50 W se tromperait d'un facteur sept.

Ce qui a répondu est nommé dans le rapport, et ce qui n'a pas répondu aussi. Les
deux compteurs donnent un chiffre qui dit ce qu'il laisse de côté ; l'accélérateur
seul dit que le processeur manque ; si aucun ne répond, le rapport affiche
`not measured` et le modèle retombe sur une estimation étiquetée comme telle. Un
compteur qui a franchi son plafond une fois pendant la course est déplié par sa
plage publiée, et le chiffre porte la puissance au-delà de laquelle ce
redressement aurait été faux.

Les deux lignes sous le total sont le profil par fonction, et elles se paient.
`cProfile` facture à l'appel : une charge riche en appels peut mettre presque
deux fois plus de temps sous lui. Le temps affiché ci-dessus est celui de
l'exécution profilée. La commande le dit dans un avertissement. Quand c'est la
durée qui vous intéresse et non l'endroit où elle est passée, prenez-la sans le
profileur :

```bash
saggio measure --no-profile -- python train.py --steps 100
```

### De combien une seconde exécution la déplacerait-elle ?

Une exécution dit ce qui s'est passé une fois. Elle ne dit pas si cela se
reproduirait. La galerie de ce paquet prouve que les deux figures ne se
comportent pas pareil :

```bash
saggio measure --repeat 5 --units 50 -- python render_fifty.py
```

```
Runs: 5
Wall-clock: 1.381 s (median of 5; 1.326-1.538 s)
Average power: 17.4 W (median of 5; 16.1-37.4 W)
```

**Le temps a bougé de 15 %, la puissance de 109 %.** Le temps est une propriété
du travail ; la puissance est une propriété de la pièce, parce qu'un compteur
mesure la machine et que l'une de ces cinq exécutions a attrapé autre chose qui
se réveillait.

Avec `--into`, le modèle porte l'exécution dont le temps était médian — une
exécution réelle plutôt qu'une médiane assemblée champ par champ, parce que
l'énergie d'un modèle est son temps multiplié par sa puissance et que mélanger
des exécutions énoncerait un couple qui n'a jamais eu lieu. L'étendue est
inscrite à côté, dans le bloc de mesure et dans les notes de chaque quantité
qu'elle borne. Une valeur mesurée une seule fois le dit, plutôt que de laisser
un silence passer pour de la stabilité.

Aucun profil par fonction n'est pris quand `--repeat` dépasse un : le profileur
change ce qui est chronométré ; une série avec une exécution profilée au milieu
d'exécutions ordinaires rapporterait un écart que le profileur y aurait mis. Une
fois pour le profil, plusieurs fois pour l'écart.

































































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

C'est l'étape qu'on rate à la main. Coller une durée dans le YAML (YAML Ain't
Markup Language) laisse l'énergie, l'argent et le carbone sur leurs anciennes
valeurs ; un modèle dont l'énergie ne correspond plus à sa durée est pire qu'un
modèle qui n'avait ni l'une ni l'autre, parce qu'il a l'air fini. Chaque chiffre
ci-dessus est recalculé à partir des hypothèses du modèle lui-même, par les
fonctions qu'emploie l'audit, et le résultat est validé avant que quoi que ce
soit ne soit écrit.

`--units 500` dit que la commande a effectué cinq cents unités de travail : la
durée enregistrée est donc par unité. Quand le modèle sait déjà quelle quantité de
travail effectue une exécution complète, une projection sur cette exécution découle
des coûts unitaires.

Une analyse est rarement exécutée une seule fois. Dites combien de fois la vôtre
tourne vraiment — réglage, débogage, relances — dans
`assumptions.pragmatic_scaling_factor` (le terme du papier Green Algorithms ;
ses exemples vont de 11 à 180). Le pliage suivant projette `repeated_runs` :
l'exécution complète multipliée par ce facteur, dérivée des deux pour que le
validateur surveille l'arithmétique. Le facteur est l'estimation de l'équipe ;
rien ici n'en invente un, et un facteur encore marqué `TODO` donne une
projection aux chiffres ouverts plutôt qu'absents, pour que le rapport montre la
question.

Trois choses sont refusées plutôt qu'écrites : une commande sortie en non-zéro,
parce qu'une exécution ratée a mesuré un échec et qu'un échec n'a pas de coût
par unité de travail ; un modèle sans scénario où écrire ; et tout résultat qui
ne validerait plus. Rien n'est écrit à moitié : un pliage qui change six nombres
les affiche tous les six.

```bash
saggio measure --into cost_of_running.yaml --scenario production -- pytest -q
```

### Une tranche du dépôt de quelqu'un d'autre

```bash
saggio consent grant
saggio audit . --country FR --run -o cost_of_running.yaml
```

`consent grant` affiche les conditions en entier avant d'enregistrer quoi que ce
soit — quatre paragraphes commençant par *« Pour mesurer ce que ce code coûte à
l'exécution, il faut l'exécuter. »* — puis dit où la décision est allée, pour que
vous puissiez supprimer ce fichier et la révoquer. Il prend `--language` comme
l'audit :

```bash
saggio consent grant --language fr
```

La décision enregistrée dit à quelles conditions on a consenti, et dans quelle
langue elles ont été lues :

```json
{
  "granted": true,
  "decided_on": "2026-10-19",
  "tool": "saggio",
  "language": "fr",
  "terms_version": "38ba4eeae6ee"
}
```

Si les conditions sont un jour reformulées, cette empreinte cesse de
correspondre et la question est posée à nouveau, avec une ligne disant pourquoi
— un oui à un texte n'est pas un oui à un autre. Reformuler une *traduction* ne
change rien : l'empreinte est prise sur la formulation anglaise, qui est celle
d'origine.

Sur un terminal, l'audit pose lui-même la même question, dans la même langue :
`consent grant` ne sert donc que là où il n'y a personne à qui demander.

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
tests du dépôt qui est exécutée. Elle couvre une part inconnue d'une vraie
charge de travail, donc aucune projection sur l'exécution complète n'en découle,
ce que l'audit dit exactement.

### Mesurer comment le travail croît, au lieu de le supposer

La projection ci-dessus divise par `0,001` parce que la tranche couvrait un
millième de l'exécution. C'est juste quand le travail est uniforme. Quand il ne
l'est pas, c'est faux d'une *puissance* et non d'une marge : une étape
quadratique en la taille du lot transforme un millième d'exécution en un
millionième de son coût, et la projection sous-estime la facture de trois ordres
de grandeur avec exactement l'assurance d'une projection correcte.

Rien ne vérifiait cette hypothèse. `--scaling-steps` la vérifie :

```bash
saggio audit . --country FR --run --scaling-steps 3 -o cost_of_running.yaml
```

Trois tranches sont exécutées au lieu d'une, à des tailles espacées d'un facteur
quatre, la plus grande étant la tranche qui aurait été exécutée de toute façon.
Les deux en dessous ajoutent environ un tiers au temps — un quart et un seizième
du barreau supérieur — et en échange l'exposant cesse d'être une hypothèse :

```yaml
measurement:
  scaling:
    method: "Least squares of log(seconds) on log(size) over 3 runs: seconds = 0.0001 × size^2.000."
    reading: The work grew faster than the size, by a power of 2.00. Doubling the job
      multiplies the cost by 4.00 rather than by 2, so a projection that divided by
      the size ratio would understate the whole run.
    exponent:
      value: 2.0
      unit: exponent
      status: measured
      notes: Fitted over 3 runs of sizes 37 to 600, R² = 1.000.
    r_squared: 1.0
    observations:
      - {size: 37.0, seconds: 0.1369}
      - {size: 150.0, seconds: 2.25}
      - {size: 600.0, seconds: 36.0}
```

L'exposant est `measured`, parce qu'il résume trois lectures d'horloge, de la
même manière que des watts tirés d'un compteur d'énergie sur une durée sont une
mesure. Ce qu'il n'est *pas*, c'est une loi : il est `measured` **sur les
tailles qui ont été exécutées** ; chaque projection qui l'utilise dit de combien
elle est allée au-delà.

La projection qui suit divise par `0,001^2,000` plutôt que par `0,001`, ce qui sur
cette charge fait un facteur mille :

```yaml
projections:
  whole_run:
    description: What the whole run would cost, projected from the slice that was
      measured and from the exponent by which its cost was measured to grow with
      the size of the job.
    costs:
      energy:
        method: "Whole run = measured slice / 0.001^2.000. Least squares of log(seconds) on log(size) over 3 runs: …"
        result:
          value: 1.6
          unit: kWh
          status: estimated
          notes: Projected from a slice covering 0.1% of the run, with a measured
            scaling exponent of 2.000.
        limits:
          - The exponent holds between sizes 37 and 600, and the whole run is about
            6e+05 at the same scale, which is 1e+03 times the largest size actually run.
```

#### Quand elle refuse, et pourquoi c'est la réponse utile

Une mesure qui revient en disant *je ne peux pas savoir* vaut mieux qu'un
exposant que personne ne peut vérifier. La série refuse donc dans quatre
situations, chaque refus nommant ce qui le lèverait :

| Situation | Pourquoi | Ce qu'elle dit |
|---|---|---|
| Moins de trois tailles ont abouti | Deux points ajustent exactement une droite, donc n'excluent rien | Elle en demande trois, et dit pourquoi deux ne valent pas les deux tiers d'une réponse |
| Les tailles couvrent moins d'un facteur quatre | Sur une plage étroite, tous les exposants s'ajustent à peu près aussi bien | Elle nomme le rapport obtenu et celui qu'il faudrait |
| Une taille ou une durée n'est pas strictement positive | Une loi de puissance s'ajuste sur des logarithmes | Elle dit qu'une exécution trop courte pour l'horloge demande une tranche *plus grande* |
| L'ajustement explique moins de 95 % de la variation | Les tranches ne mesurent pas un comportement cohérent | Elle nomme le R² et les causes habituelles — un cache qui chauffe, un planning qui change de forme, une machine occupée |

La dernière compte le plus, parce que c'est celle qui change une réponse. Quand
l'ajustement est aussi mauvais, le constat est que **la tranche n'est pas
représentative de l'exécution dont elle a été coupée** : une projection faite
malgré tout affirmerait une proportionnalité que les exécutions disponibles
contredisent. Le bloc whole_run n'est donc pas écrit du tout, la raison remonte
au lecteur sous forme de note, et le refus est consigné dans le modèle :

```yaml
measurement:
  scaling:
    refused: true
    exponent:
      status: TODO
      notes: A power law explains only 0.42 of the variation across 3 runs, below
        the 0.95 required. The slices are not measuring one consistent behaviour …
```

Avoir mesuré la mise à l'échelle et échoué n'est pas la même chose que n'avoir
jamais regardé. Le modèle distingue les deux : sans `--scaling-steps`, la
projection garde l'hypothèse linéaire et la consigne comme une hypothèse ; avec,
une charge inajustable n'obtient aucune projection.

Deux choses encore avant de l'utiliser. Une série de mise à l'échelle s'exécute
**sans le profileur**, parce que `cProfile` facture à l'appel et injecterait sa
propre courbe de croissance dans l'ajustement — il n'y a donc pas de chemin
chaud dans le modèle ; en échange chaque chiffre de coût provient d'une
exécution non profilée plutôt que gonflée. Et un dépôt dont la taille annoncée
est trop petite pour être coupée en trois tailles distinctes retombe sur une
tranche unique et le dit.

La méthode n'est pas neuve. C'est celle de [Goldsmith, Aiken et Wilkerson,
*Measuring Empirical Computational
Complexity*](https://theory.stanford.edu/~aiken/publications/papers/fse07.pdf)
(FSE 2007) — exécuter sur des tailles étalées sur plusieurs ordres de grandeur,
ajuster une loi de puissance, rapporter la qualité de l'ajustement — avec les
refus de ce paquet attachés. [`ANALYSE.md`](ANALYSE.md) est l'étude de cette
littérature et de ce que les autres approches peuvent ou ne peuvent pas donner.

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

Deux choses limitent une charge sur un accélérateur ; une projection qui n'en
connaît qu'une est optimiste par construction. Le débit arithmétique limite le
travail qui garde les unités de calcul occupées ; la bande passante mémoire
limite le travail qui passe son temps à déplacer des poids. Entre une 4090 et
une H100, ces deux rapports valent 6,0 et 3,3 : la réponse est donc un
encadrement, pas un nombre. L'estimation ponctuelle est le rapport de calcul
quand la lecture a établi que la charge est limitée par le calcul, le rapport de
bande passante quand elle a établi l'inverse, et le plus lent des deux quand
elle n'a rien établi, parce que le rapport le plus lent, c'est l'exécution la
plus longue et la facture la plus lourde.

La projection va jusqu'à l'argent et au carbone, pas seulement jusqu'à une
durée, parce qu'une durée n'est pas la question posée. Elle tient le pays, le
tarif et le mix électrique constants, et elle le dit : faire tourner le travail
sur un autre accélérateur, c'est en général le faire tourner ailleurs ; et c'est
l'endroit qui fixe le prix.

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

Rien dans le paquet n'a besoin de changer. Le validateur la tient aux mêmes
règles, le rapport lui donne une ligne, la barrière de dérive la surveille.

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

# Quel nom figure dessus, et quelle date il revendique.
saggio render cost_of_running.yaml -f pdf -o annexe.pdf \
    --author "Acme SAS" --generated "2026-T2"

# Aucun accès réseau pendant la conversion.
saggio render cost_of_running.yaml -f docx -o cost_of_running.docx --offline
```

Le bloc de titre du Word et du PDF (Portable Document Format) nomme **saggio** comme auteur et porte la date
de production du document. Ce n'est pas la date du corps : *Last updated* dit
quand quelqu'un a modifié un nombre du modèle, le bloc de titre dit quand ce
fichier-ci a été fabriqué. Un PDF produit aujourd'hui depuis un modèle inchangé
depuis juin affiche les deux, et c'est tout l'intérêt : un chiffre périmé ne doit
pas se refaire une fraîcheur en étant réexporté.

`--author` met un autre nom sur un livrable client ; `--generated` écrit la date
telle quelle (`2026-T2`, `remis le 14 mars`). Les deux valent par défaut ce qui a
réellement produit le fichier, et quand.

`--offline` compte plus qu'il n'y paraît. Le convertisseur va chercher un gabarit
de document en HTTP (HyperText Transfer Protocol) dès qu'aucun `--reference-doc` n'est donné : sans ce drapeau,
un rendu exige une connexion et deux rendus d'un même modèle peuvent différer
parce que le gabarit a bougé. Ce n'est pas un défaut ; cela ne doit pas être tu.

La page HTML (HyperText Markup Language) embarque sa propre feuille de style, son script, son logo et les
données de catalogue dont elle a besoin : elle s'ouvre sans aucun réseau. Son
panneau « et si » recalcule carbone et argent pour un autre pays dans le
navigateur, à partir de l'énergie que le modèle annonce déjà. Un modèle sans
énergie annoncée n'a pas de panneau, parce qu'un « et si » bâti sur une base
inventée serait le pire chiffre de la page.

Partout où un rapport montre un chiffre de carbone connu, une ligne en dessous le
restitue en termes qu'un lecteur peut ressentir — mois-arbre, kilomètres en
voiture européenne moyenne, fraction d'un vol de référence — avec les
coefficients de Green Algorithms. La restitution ne gagne jamais en confiance :
un chiffre ouvert reste ouvert.

### La page d'équipe

```bash
# Tous les modèles commités, côte à côte, sur une page autonome.
saggio dashboard examples/nanoGPT.yaml examples/whisper.yaml examples/fastapi.yaml -o dashboard.html
```

Le dashboard ouvre sur la seule comparaison honnête entre projets : la part de
chaque modèle qui est mesurée, estimée, ou encore ouverte, dessinée en une barre
empilée par projet, toutes sur la même échelle de cent pour cent. Le tableau des
coûts suit, par unité de travail propre à chaque projet, sous une ligne disant
clairement que ces lignes ne se comparent pas entre elles — l'unité de l'un est
une requête, celle de l'autre un entraînement complet.

## À quelle question répondre en premier

Un audit revient avec quinze champs ouverts, chacun disant ce qui le résoudrait.
Aucun ne dit par lequel commencer. Ils ne sont pas indépendants non plus.

```bash
saggio next cost_of_running.yaml
saggio next cost_of_running.yaml --json
```

```
54 number(s) open. 1 question(s) would close 5 of them.

  +5  scenarios[0].runtime  [TODO]
      No run was measured. Measure the real command with `saggio measure`, or
      audit again with --run.
      closes: assumptions.machine_energy, scenarios[0].costs.carbon,
      scenarios[0].costs.energy, scenarios[0].costs.money,
      scenarios[0].costs.time

46 more are waiting on you and close only themselves:
  assumptions.hardware_embodied_carbon
  ...
```

Le classement est de l'arithmétique, pas une opinion. Une grandeur nomme ses
entrées dans `derived_from` ; lire ces arêtes à l'envers dit quelles autres
grandeurs deviendraient calculables ; la cascade se compte exactement. **Aucune
question n'est inventée** : chaque ligne est un champ que le modèle tient déjà
ouvert, cité dans la phrase que le modèle a déjà écrite pour lui.

Un champ qui ne ferme rien reste listé, parce que « ne ferme que lui-même » est
la description honnête du chiffre d'eau ou du facteur d'émission contractuel.
Les deux valent la peine ; aucun des deux ne débloque autre chose.

## Sur quelle ligne d'un bilan va chaque coût

La question que posent les personnes qui déclarent le chiffre, qui n'est pas
celle à laquelle répondent les personnes qui le produisent.

```bash
# Où va chaque coût, pourquoi, et la norme qui tranche.
saggio scopes cost_of_running.yaml

# La même chose en données, pour une chaîne de reporting.
saggio scopes cost_of_running.yaml --json

# Un modèle qui porte plus d'un scénario.
saggio scopes cost_of_running.yaml --scenario cold
```

La commande ne calcule rien. Chaque nombre est déjà dans le modèle ; ce qui
s'ajoute est le scope, la phrase qui le justifie, un décompte de la solidité des
figures placées — qui est la part d'estimation qu'un déclarant doit publier,
déjà écrite.

Le scope tient à un seul fait que le modèle énonce, `deployment.provider` :
possédez la machine et l'électricité est votre scope 2 et le matériel votre
scope 3 catégorie 2 ; louez-la et les deux vous parviennent en scope 3
catégorie 1, puisque vous avez acheté un service. Un fournisseur que le
catalogue ne classe pas n'obtient **aucun scope** plutôt que la supposition la
plus proche.

Deux réponses sont des refus. Ils comptent davantage que les placements. Une
figure de scope 2 **market-based** n'est jamais dérivée ici, parce qu'aucune
moyenne de réseau ne l'implique ; énoncez `assumptions.market_carbon_intensity`
avec le document d'où elle vient et la figure est calculée et placée à côté de
la location-based. Et **l'eau n'a pas de scope**, parce que ce n'est pas un gaz
à effet de serre.

[`INVENTAIRE.md`](INVENTAIRE.md) est la forme longue, pour la personne qui doit
déclarer plutôt que pour celle qui a mesuré.

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

`diff` échoue sur trois choses. C'est la troisième qu'on oublie :

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

**Et une quatrième chose sur laquelle il n'échoue plus.** Quand les deux modèles
portent un écart `--repeat`, un mouvement qui tient dans les étendues qu'ils ont
chacun mesurées n'est pas la preuve que quelque chose a changé, et la porte le
dit au lieu d'échouer :

```
scenarios[0].costs.carbon: 8.27e-06 -> 1.85e-05 (+123.6%), inside the noise both
  models measured: 7.342e-06 to 1.973e-05, then 1.759e-05 to 1.915e-05, worse
11 change(s), 0 past the 10% gate. 8 inside the noise the models measured.
```

Ce sont deux mesures à cinq exécutions d'un **code inchangé**, l'une après
l'autre sur un portable. Avant que la porte sache lire l'écart, elle en faisait
échouer six. Elle échoue toujours quand la preuve dit que quelque chose a
bougé : le même modèle neuf contre un plus ancien mesuré **une seule fois**
échoue, parce que cette valeur unique tombe hors de l'étendue que les cinq
exécutions ont couverte.

L'intervalle d'une valeur dérivée est le produit des intervalles dont elle
dérive, trouvé en remontant `derived_from` — exact tant que chaque étape est
proportionnelle à ses entrées, ce qui est la façon dont tout coût d'un modèle
est construit. Une valeur qui n'atteint aucune étendue mesurée n'a pas
d'intervalle et reste arbitrée comme avant : rien ne change pour un modèle qui
n'a rien répété. Et les intervalles n'excusent jamais que le seuil : un statut
affaibli, une provenance affaiblie ou une quantité supprimée échouent quel que
soit le bruit.

**Ce que cela ne peut pas attraper, dit franchement.** Une régression est
attrapée par la dimension qui a été mesurée serré. Une charge rendue deux fois
plus lente fait échouer la porte sur `costs.time` et sur le temps projeté — mais
ses lignes carbone, argent et énergie sont *excusées*, parce qu'un intervalle de
puissance de 109 % avale un mouvement de 100 %. C'est la porte aveugle là
précisément où la preuve est aveugle, ce qui est le comportement voulu et reste
une limite à connaître : **une régression qui augmente la puissance sans toucher
au temps** — du code qui se met à utiliser l'accélérateur, par exemple — passerait
une porte bâtie sur une mesure de puissance bruitée. Mesurez sur une machine
calme si vous voulez un intervalle de puissance assez serré pour arbitrer dessus.

































































































































## Les catalogues
### Lire l'empreinte produit d'un constructeur

```bash
saggio catalog read-pcf https://images.nvidia.com/aem-dam/Solutions/documents/HGX-H100-PCF-Summary.pdf
```

```
Read: https://images.nvidia.com/…/HGX-H100-PCF-Summary.pdf
  the document says: carbon footprint from cradle-to-gate for one HGX H100 GPU
                     baseboard is 1,312 kg CO2e
  and, elsewhere in it: Form Factor 8x NVIDIA H100 SXM
  so one of 8: 1312 / 8 = 164 kgCO2e

A row you may accept, reject, or correct — nothing has been written:

embodied_kgco2e: 164.0
embodied_scope: 'One of the 8 on an HGX H100 GPU baseboard: 1312 kgCO2e
  cradle-to-gate for the whole of it, divided by 8. …'
embodied_source_url: https://images.nvidia.com/…/HGX-H100-PCF-Summary.pdf
embodied_retrieved_date: '2026-10-19'
```

**Le raisonnement est la sortie.** La valeur est page 3, le diviseur page 1, et
savoir qu'il faut diviser vient du schéma de ce catalogue et non du document —
le verbe montre donc les deux moitiés et l'arithmétique entre elles au lieu de
tendre un nombre.

**Trois choses qu'il ne fera pas.** Il ne prendra pas une valeur qui n'est pas
dans une phrase : l'analyseur fait de l'OCR (reconnaissance optique de
caractères), donc un diagramme en barres devient du texte comme le reste — et
une valeur relevée sur un graphique est la seule chose que ce paquet refuse de
porter. Il ne divisera pas par un nombre que personne n'a écrit — un document
donnant une valeur de carte de base sans dire combien de puces elle porte est
**refusé**, pas deviné. Et il n'écrit pas : il n'y a pas de `--into`.

Il demande un analyseur de documents, absent de l'installation par défaut :
`pip install 'saggio[pcf]'`. Les cinq dépendances d'exécution sont délibérées.

En HTTP, la même lecture est sur `POST /catalog/read-pcf`, **fermée sauf si
`SAGGIO_API_ALLOW_FETCH` est positionné** — aller chercher une adresse choisie
par le client est le même risque que cloner, barré à part parce qu'un exploitant
qui laisse le serveur lire un PDF n'a pas pour autant accepté qu'il clone un
dépôt.

































































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
    --source-url "https://example.invalid/nvidia-h300-datasheet" \
    --retrieved-date 2026-09-12 \
    --field tdp_w=800 \
    --field peak_bf16_tflops=2400
```

La ligne atterrit dans votre propre surcouche, sert immédiatement, et pourra
être proposée en amont plus tard. Sans source ni date elle est refusée : c'est
cette règle qui rend les catalogues dignes de confiance.

Demander quels chiffres ont discrètement vieilli :

```bash
saggio catalog freshness   # sort en 1 si quoi que ce soit a vieilli
```

Tarifs et mix électriques périment en un mois, consommations de fiche technique en
un an. Un seuil unique se mettrait soit à râler sur un GPU (graphics processing unit), soit à laisser passer
le tarif d'électricité de l'an dernier.

Quand quelque chose périme vraiment, il y a de quoi y répondre au lieu de
redater :

```bash
saggio catalog refresh grid
```

En lecture seule. Elle affiche ce que dit la source aujourd'hui face à ce que
tient le catalogue, sans rien écrire. `--write saggio/data/grid.yaml` est le
second geste, délibéré. `--column` choisit quoi relire — `carbon` par défaut,
`price`, ou `both` — parce que les deux colonnes ne viennent pas du même endroit
et ne bougent pas ensemble :

```bash
saggio catalog refresh grid --column price
saggio catalog refresh grid --column both --write saggio/data/grid.yaml
```

Chaque colonne porte son `*_source_url`, son `*_retrieved_date`, la période que
le chiffre décrit — `carbon_data_year: 2025`, `price_collected: "Q3 2026"`. La
date à laquelle un nombre a été *lu* n'est pas la période qu'il décrit ; une
ligne qui ne noterait que la première laisserait un chiffre de 2019 passer pour
celui d'aujourd'hui.

**Et la période est par ligne, pas par fichier.** Ember ne publie pas tous les
pays jusqu'à la même année : la plupart vont à 2025, la série ukrainienne s'arrête
en 2022. Un millésime unique apposé sur tout le catalogue, c'est ainsi que le
chiffre ukrainien de 2022 a été livré comme un chiffre de 2025 — un nombre banal
sous une estampille qui était le seul endroit où l'écart de trois ans pouvait
apparaître. Un rafraîchissement nomme désormais les pays que la source n'a pas
rattrapés.

**La colonne carbone** vient du [jeu de données annuel publié par
Ember](https://ember-energy.org/data/yearly-electricity-data/), sous CC (Creative Commons)-BY-4.0 et
sans aucune clé. Une clé dans `EMBER_API_KEY` ou `--api-key` fait lire l'API
d'Ember à la place — la même série par son interface machine — et l'exécution
imprime laquelle des deux a répondu. Les lignes citent la page dans les deux cas,
parce que sans clé l'API répond à un lecteur par un HTTP 403 plutôt que par le
chiffre, et une citation que personne ne peut suivre n'est pas une citation.

Rien d'autre n'est substitué. Il existe une alternative tentante — Our World in
Data publie une série *dérivée* d'Ember par un CSV (comma-separated values)
stable, sans clé — et elle est fausse : sa propre métadonnée l'appelle intensité
carbone *de cycle de vie*, là où cette colonne est l'émission *opératoire*.
Échanger l'une contre l'autre changerait en silence le sens de chaque modèle
commité, sans rien changer à la confiance qu'il inspire. La commande refuse et
le dit, plutôt que de le faire discrètement. Le jeu publié par Ember n'est pas
cet échange, et il a été recoupé pays par pays avec l'API avant d'être adopté
plutôt que supposé équivalent.

**La colonne fuseaux** est vérifiée plutôt que remplacée, par rapport à la [base
de données des fuseaux de l'Internet Assigned Numbers Authority
(IANA)](https://data.iana.org/time-zones/tzdb/zone1970.tab) qui définit ces noms
— celle que livre chaque système d'exploitation, dans le domaine public, et
versionnée : la ligne note donc la version à laquelle elle correspond
(`timezones_tzdb_version: "2026e"`) et pas seulement le jour où quelqu'un a
regardé. La liste n'est pas réécrite : la base dit quels fuseaux existent, pas
lesquels un pays utilise au sens où ce catalogue l'entend, et le catalogue porte
exprès des noms de compatibilité comme `Europe/Kiev` ou `Asia/Calcutta` parce
que c'est ce qu'une vraie machine rapporte. Un fuseau que la base ne publie sous
aucun nom fait échouer la commande au lieu d'être corrigé : c'est une question,
pas une correction.

Chaque colonne a aussi son horloge. Un tarif et un mix électrique bougent tous
les mois ; une liste de fuseaux est publiée quelques fois par an. La redemander
tous les mois apprendrait à redater plutôt qu'à relire — l'habitude même que
tout ce mécanisme de fraîcheur existe pour empêcher.

**La colonne tarif** vient de
[GlobalPetrolPrices](https://www.globalpetrolprices.com/electricity_prices/), qui
publie un prix résidentiel au kilowattheure — énergie, distribution, transport et
toutes taxes — pour chaque pays dans une seule table et une seule monnaie. Cette
table est écrite par un script plutôt que servie, donc le rafraîchissement rend
la page dans un navigateur sans interface ; sans navigateur installé, il le dit
et s'arrête au lieu de deviner.

L'institution qui fait le plus autorité en Europe est [Eurostat](https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/nrg_pc_204?format=JSON&lang=EN&nrg_cons=KWH2500-4999&tax=I_TAX&currency=EUR&unit=KWH&lastTimePeriod=1), qui
a été lue — comme **contre-test**, pas comme source. Elle publie en euros et
pour l'Europe seulement : la retenir aurait imposé une seconde source pour le
taux de change, une conversion qui périme chaque jour, et dix-huit lignes
incomparables avec les vingt autres. Converties au [taux de référence de la
Banque centrale européenne](https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml), les deux concordent à 7 % en médiane sur les dix-huit pays couverts
par les deux, et divergent de plus de 15 % pour six : Finlande, Roumanie,
Pologne, Norvège, Suède et Italie. C'est une différence de méthode, pas une
erreur de l'une ou de l'autre — Eurostat moyenne un semestre par tranche de
consommation, l'autre est un relevé. Les trois URL (Uniform Resource Locator)
sont dans le code, pour que la comparaison puisse être refaite.

Un pays pour lequel la source ne répond pas est laissé tel quel et nommé. Rien
n'est interpolé, reporté ni moyenné.

**Ce qu'a trouvé la première vraie exécution.** Avant d'écrire quoi que ce soit,
les chiffres rafraîchis ont été confrontés à la série Ember complète, année par
année, pour confirmer que le catalogue avait simplement une année de retard. Ce
n'était pas le cas. Les valeurs commitées correspondaient à des années Ember
éparpillées de 2000 à 2025. Huit pays ne correspondaient à aucune année Ember à
8 % près — la Suède était à 13 gCO2e/kWh là où le plus bas chiffre jamais publié
par Ember pour elle est 34,91. Chaque ligne citait pourtant Ember. Un
`source_url` qui ne contient pas le chiffre qu'il accompagne est exactement la
faute que ce paquet existe pour dénoncer, et elle était dans ses propres données
jusqu'à ce que `saggio catalog refresh grid` remplace l'ensemble par un seul
millésime 2025 vérifiable.

Sept tests ont alors cassé, tous parce qu'ils avaient recopié une valeur du
catalogue dans une assertion au lieu de la lire. Un paquet dont l'argument est
qu'il rafraîchit ses propres faits ne peut pas avoir une suite qui casse quand il
le fait — le rafraîchissement se lisait comme une régression. Ils vérifient
désormais ce que leur nom annonce.

Elle dit aussi ce qui est *sur le point* de périmer, sans faire échouer :

```bash
saggio catalog freshness --within 14
```

> expiring country: 38 row(s) go stale in 12 day(s) — AE, AT, AU, BE, BR, CA and
> 32 more. Re-read the source now rather than re-dating it later.

Cet avertissement existe pour une raison. Une barrière qui vire au rouge du jour
au lendemain fait redater la ligne dans l'urgence au lieu de faire relire la
source ; un nombre redaté que personne n'a regardé est exactement ce que tout ce
mécanisme a été bâti pour empêcher. Une semaine de préavis — `--within 0` le
désactive — suffit à aller lire Ember correctement.

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

print(energie.value, energie.status)  # 0.48 estimated
print(carbone.value, carbone.status)  # 26.88 estimated
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
