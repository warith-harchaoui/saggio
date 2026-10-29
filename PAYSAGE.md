# Paysage

🇫🇷 Français · [🇬🇧 LANDSCAPE.md](LANDSCAPE.md)

Les autres outils du domaine « combien coûte l'exécution de ce code », avec le
cas où chacun est le meilleur choix. Les notes vont de ⭐ (1) à ⭐⭐⭐⭐⭐ (5),
attribuées au regard du travail de *cet* outil-ci : **un modèle de coût
versionné, relisible, par unité de travail, sur plusieurs dimensions, où chaque
chiffre dit jusqu'où on peut lui faire confiance**. Un outil conçu pour un autre
travail n'est pas pénalisé d'être bon à ce travail-là ; la note ne dit que
l'adéquation à cette niche.

Une étoile vaut par rapport à la cohorte du tableau et à la date qui le suit.
Cette page ne le disait pas, jusqu'à ce qu'une notation de même forme portant
sur des modèles d'intelligence artificielle (IA) — l'[AI Energy Score](https://huggingface.github.io/AIEnergyScore/),
qui réétalonne ses propres étoiles environ deux fois par an — rende l'omission
évidente en l'énonçant dès ses premières lignes.

Dix-huit outils, dix critères. Les lignes ajoutées à ce tour ont été lues le
2026-10-29 ; les autres l'ont été le 2026-10-01. Les projets bougent ; si
quelque chose ici a vieilli, [dites-le](CONTRIBUTING.md).

## Vue d'ensemble

| | Modèle par unité | Provenance sur chaque chiffre | Multi-dimension | Artefact versionné | Mesure la puissance | La charge, pas la machine | Estime sans exécuter | Barrière de dérive | Rapports lisibles | Hors ligne |
| --- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **saggio** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| CodeCarbon | ⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐ | ⭐ | ⭐⭐⭐ | ⭐⭐⭐ |
| Calculateur Green Algorithms | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐ | ⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐ | ⭐⭐⭐ | ⭐ |
| Scaphandre | ⭐ | ⭐⭐ | ⭐ | ⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐ | ⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ |
| PowerAPI / pyJoules | ⭐⭐ | ⭐⭐ | ⭐ | ⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐ | ⭐ | ⭐ | ⭐⭐⭐⭐⭐ |
| JoularJX / PowerJoular | ⭐⭐ | ⭐⭐ | ⭐ | ⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐ | ⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ |
| Kepler | ⭐ | ⭐⭐ | ⭐⭐ | ⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ | ⭐ | ⭐⭐ | ⭐⭐⭐⭐ |
| CEEMS | ⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐ | ⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ |
| eco2AI | ⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐ | ⭐ | ⭐⭐ | ⭐⭐⭐ |
| carbontracker | ⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐ | ⭐⭐ | ⭐⭐ |
| EcoLogits | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐ | ⭐ | ⭐⭐⭐⭐ | ⭐⭐ | ⭐ | ⭐⭐ | ⭐⭐⭐ |
| EnergiBridge | ⭐ | ⭐⭐ | ⭐ | ⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐ | ⭐ | ⭐ | ⭐⭐⭐⭐⭐ |
| Green Metrics Tool / Eco-CI | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| Cloud Carbon Footprint | ⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐ | ⭐ | ⭐⭐ | ⭐⭐⭐ | ⭐ | ⭐⭐⭐⭐ | ⭐ |
| Carbonifer | ⭐⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ |
| Infracost | ⭐⭐⭐ | ⭐⭐⭐ | ⭐ | ⭐⭐⭐ | ⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐ |
| OpenCost / Kubecost | ⭐⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐ | ⭐ | ⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ | ⭐ |
| Consoles de facturation cloud | ⭐ | ⭐⭐⭐⭐ | ⭐ | ⭐ | ⭐ | ⭐⭐ | ⭐ | ⭐⭐ | ⭐⭐⭐⭐ | ⭐ |

**La colonne neuve est la sixième, et cet outil y est bon dernier, à égalité.**
Tous les autres critères demandent ce qui sort ; celle-là demande de quoi le
chiffre est le chiffre. Un compteur mesure du matériel : une valeur qu'on y lit
emporte tout ce que la machine faisait par ailleurs. Scaphandre, JoularJX,
Kepler et CEEMS séparent la charge de la machine — par processus, par méthode,
par conteneur, par travail soumis — et ce paquet ne le fait pas : il énonce
l'encadrement et refuse de choisir dedans. La colonne est là parce qu'un tableau
qui ne noterait que ce que cet outil réussit ne vaudrait pas la peine d'être
dessiné.

Le tableau classe ; il n'explique pas. Ce qu'un lecteur doit voir d'abord, c'est
que la question a quatre maillons dans un ordre fixe, qu'aucun outil de cette
page ne les tient tous les quatre, et que ce paquet est le plus faible
précisément au maillon pour lequel les outils de mesure existent.

<p align="center">
  <img src="assets/landscape-links.fr.svg" alt="La question « combien coûte l'exécution de ce code » dessinée en quatre maillons dans l'ordre : ce qui a tourné et en quelle quantité, ce qu'il a tiré, ce que cela coûte, et par quoi et sur quoi cela repose. Sous chaque maillon figurent les outils qui y répondent le mieux — le dépôt et les lecteurs de plan pour le premier, les mesureurs de puissance pour le deuxième, les catalogues sourcés pour le troisième, presque personne pour le quatrième — et une pastille disant ce que vaut la réponse de ce paquet : measured, TODO, estimated, measured. Aucun outil de la page ne tient les quatre maillons." width="900">
</p>

## La carte

Le même tableau, dessiné. [standpoint](https://github.com/warith-harchaoui/standpoint)
passe une analyse en composantes principales sur les dix notes et dispose chaque
outil le long des deux directions qui les distinguent vraiment, en orientant la
carte pour que saggio soit en haut à droite. Deux axes gardent un peu plus des
sept dixièmes de ce qui sépare ces dix-huit outils : 50 % horizontalement, 21 %
verticalement.

Les noms d'axes sont la lecture que la machine fait des saturations, et les deux
versions linguistiques de cette page ne les nomment pas de la même manière —
*Autonomie ↔ Transparence* ici, *Controlled ↔ Transparent* en face — parce que
chacune a été nommée dans sa langue à partir des mêmes nombres, plutôt que
traduite de l'autre. Ce que disent les saturations est plus simple que l'une ou
l'autre paire. Plus on
va à **droite**, plus l'outil produit des réponses sourcées, versionnées, par
unité de travail, qu'un lecteur peut vérifier. Plus on va à **gauche**, plus il
mesure la puissance en direct et l'attribue à quelque chose de plus petit que la
machine entière. Plus on **monte**, plus il mesure et garde ce qu'il a mesuré,
hors ligne, sur du matériel qui vous appartient. Plus on **descend**, plus c'est
quelque chose qu'on pointe vers une facture ou un formulaire.

<p align="center">
  <img src="assets/landscape.fr.png" alt="Carte de positionnement des dix-huit outils le long de deux composantes principales. L'axe horizontal va des outils qui mesurent la puissance en direct, à gauche, à ceux qui produisent des réponses sourcées par unité de travail qu'un lecteur peut vérifier, à droite ; l'axe vertical va des outils qu'on pointe vers une facture ou un formulaire, en bas, à ceux qui mesurent hors ligne sur du matériel qui vous appartient et gardent ce qu'ils ont mesuré, en haut. saggio occupe le coin en haut à droite." width="720">
</p>

Les distances sont celles du tableau, pas une opinion : deux outils sont voisins
parce que leurs lignes de notes le sont. Rien ici n'est une seconde copie de ces
lignes — c'est la faute que ce dépôt attrape sans cesse dans ses propres
pages : [`assets/make_landscape_map.py`](assets/make_landscape_map.py) lit les
étoiles sur cette page, les compte, et écrit le tableau numérique dont la carte
est tirée. Après une modification du tableau ci-dessus, régénérez les deux :

```bash
python assets/make_landscape_map.py
standpoint assets/landscape.en.csv -r saggio -o assets --stem landscape --model qwen3:8b
standpoint assets/landscape.fr.csv -r saggio -o assets --stem landscape.fr --model qwen3:8b
```

Puis commitez les `assets/landscape.fr.png` et `assets/landscape.fr.svg`
rafraîchis, ainsi que les deux fichiers `landscape.yaml`, qui portent chaque
coordonnée : un placement se discute, il ne se croit pas sur parole.

## Ce que cette page a pris aux autres

Une page de paysage qui n'explique que pourquoi tout le reste convient moins
bien est une publicité. Ce tour-ci est allé chercher l'inverse. Six choses en
sont revenues : deux ont changé cette page, une a changé ce qu'elle mesure, deux
étaient consignées comme des refus et sont désormais construites, et la dernière
est un vocabulaire que ce paquet devra apprendre.

Les deux qui ont été construites sont la raison de relire cette section. Les
deux refus étaient réels, et tous deux plus larges qu'il ne fallait : chacun
cachait une chose étroite qui ne se fait effectivement pas, à l'intérieur d'une
chose large qui se fait. Les choses étroites restent refusées, et elles sont
nommées plus bas.

### Pris : une note dit à quelle cohorte et à quelle date elle se rapporte

L'[AI Energy Score](https://huggingface.github.io/AIEnergyScore/) — Hugging
Face, Salesforce, Cohere et l'université Carnegie Mellon — note les modèles
d'une à cinq étoiles en wattheures pour mille requêtes, mesurés sur dix tâches
et sur une seule génération d'accélérateur, et dit dès ses premières lignes
qu'une étoile vaut par rapport aux autres modèles du même classement et que
l'échelle entière est réétalonnée environ deux fois par an. Le tableau d'étoiles
en tête de cette page a exactement la même propriété et ne le disait pas. Il le
dit maintenant.

### Pris : la question de ce dont le chiffre est le chiffre

[Scaphandre](https://github.com/hubblo-org/scaphandre),
[JoularJX](https://github.com/joular/joularjx),
[Kepler](https://sustainable-computing.io/) et
[CEEMS](https://github.com/ceems-dev/ceems) répondent tous à une question sur
laquelle cette page ne notait personne : un compteur mesure du matériel, alors
de quel travail ce chiffre est-il le chiffre ? JoularJX attribue la puissance
jusqu'à la méthode Java ; CEEMS le fait par travail soumis sur un
supercalculateur. C'est désormais la sixième colonne, et ce paquet y est bon
dernier à égalité. Auparavant, le manque était énoncé en prose au bas de cette
page et n'était noté nulle part, ce qui est la façon confortable de porter une
faiblesse.

### Pris, et construit : une fourchette au lieu d'un point

[EcoLogits](https://github.com/genai-impact/ecologits) ne choisit pas un nombre
quand la taille du modèle derrière une interface fermée est inconnue. Il renvoie
un `RangeValue`, un `min` et un `max`, documentés comme un intervalle
d'approximation à 95 %, avec les deux causes de l'écart nommées : la taille du
modèle, et la régression qui en tient lieu.

C'était consigné ici comme refusé, pour une raison qui s'est révélée être la
mauvaise. Elle confondait deux choses : *porter* un intervalle, qui ne coûte
rien à maintenir, et *livrer un catalogue* de régressions propres à chaque
fournisseur, qui est un engagement permanent. Seule la seconde posait problème.

La première est donc construite. Une quantité peut porter `low` et `high` à côté
de sa valeur, et la règle qui rend la chose utile est celle que le statut avait
déjà : **une valeur dérivée ne peut pas sur-résoudre les nombres d'où elle
vient.** Un chiffre carbone calculé depuis une intensité connue à un cinquième
près n'est pas un nombre unique, et le validateur le refuse désormais comme une
erreur, après avoir fait passer les coins de chaque intervalle d'entrée par les
mêmes arrangements qu'il emploie déjà pour recalculer la valeur. Plus large que
ce que les entrées imposent est un jugement de modélisation, et c'est permis ;
plus étroit est une prétention que personne n'a gagnée.

[`examples/uncertainty.yaml`](examples/uncertainty.yaml) est un modèle livré qui
fait exactement cela, et retirer l'intervalle de son chiffre carbone le fait
échouer.

Ce qui reste refusé est la chose étroite : une table embarquée de régressions
d'énergie par fournisseur. Elles ne sont honnêtes que tant que quelqu'un les
tient à jour, ce qui est un engagement de maintenance plutôt qu'une
fonctionnalité. Énoncez la fourchette, ou notez-la — voir la section suivante —
et la machinerie la porte jusqu'au bout.

### Pris, et construit : la qualité des données comme vecteur noté

L'analyse du cycle de vie (ACV) a résolu le problème que quatre statuts
résolvent ici, et l'a résolu plus finement. La
[matrice de pedigree d'ecoinvent](https://doi.org/10.1007/s11367-014-0759-5)
note chaque donnée sur des axes nommés — fiabilité de la source, complétude,
ancienneté, proximité géographique et technologique — puis convertit ces notes
en un facteur d'incertitude : le chiffre porte alors une distribution plutôt
qu'une étiquette.

C'était refusé au motif que la conversion est étalonnée empiriquement sur une
base de données que ce paquet n'a pas. Lire la source correctement a défait ce
motif. La **table de transformation est publiée** — Frischknecht et Jungbluth
2004, page 46 — et la **formule** aussi, page 44. Les deux sont désormais
implémentées ici telles que publiées, et un modèle peut noter une quantité sur
les cinq indicateurs et recevoir l'intervalle qu'ils donnent.

Ce qui n'est effectivement pas transposable tient en un nombre :
l'**incertitude de base**, qui vient dans la source d'une table indexée par
genre de flux industriel. Ces lignes ne décrivent pas ces dimensions-ci ; elle
doit donc être énoncée, et tant qu'elle ne l'est pas, les notes ne produisent
aucun intervalle — ce qui est la réponse que ce paquet donne déjà à un pays que
personne n'a nommé.

**Et la source a livré un refus, qui est la part qui valait le voyage.** Deux
cases de la table publiée sont vides : corrélation géographique à quatre,
corrélation technologique à deux. Une case vide n'est pas 1,00. La matrice ne
définit aucun mode de ce genre, et un modèle qui en note un est désormais une
erreur, et non un chiffre discrètement gratifié d'un bénéfice du doute que la
source n'a jamais accordé. C'est la doctrine de ce paquet, rencontrée dans
l'article de quelqu'un d'autre.

### Pris : dire quel facteur de confusion on a tenu fixe

Le [classement ML.ENERGY](https://ml.energy/leaderboard/) compare chaque modèle
dans sa propre configuration à énergie minimale, et dit pourquoi en une ligne :
pour que les différences de modèle et de tâche ne soient pas confondues avec
celles d'utilisation du matériel. L'article compagnon de 2026 mesure ce que vaut
ce facteur de confusion — l'utilisation de l'accélérateur déplace à elle seule
l'énergie d'inférence d'un facteur trois à cinq
([arXiv:2601.22076](https://arxiv.org/abs/2601.22076)). Une projection d'ici est
un rapport entre deux fiches techniques, et les limites imprimées avec elle
nomment désormais ce qui est tenu fixe, au lieu de laisser le lecteur supposer
que rien ne l'est.

### Un vocabulaire que ce paquet devra apprendre

La Green Software Foundation rédige des
[conventions sémantiques pour le carbone dans OpenTelemetry](https://github.com/Green-Software-Foundation/sci-otel) :
un nom convenu pour l'énergie, pour l'intensité du réseau électrique, pour le
carbone incorporé et pour l'unité fonctionnelle, afin que les quatre termes de
la spécification Software Carbon Intensity (SCI) voyagent comme de la télémétrie
plutôt que comme un rapport. Ce paquet écrit ces quatre mêmes termes sous ses
propres noms de champs, dans son propre fichier YAML (YAML Ain't Markup
Language). Rien n'a encore à changer, et quelque chose changera.

## Les projets

### [CodeCarbon](https://codecarbon.io/)

L'outil le plus connu du domaine, et le bon premier choix lorsque ce qu'on veut,
c'est une ligne de Python qui enregistre les émissions d'un entraînement pendant
qu'il tourne. Il suit CPU (central processing unit), GPU (graphics processing
unit) et mémoire via RAPL (Running Average Power Limit) et `nvidia-smi`, cherche
une intensité carbone régionale, puis écrit un CSV (comma-separated values).

Ce qui diffère : CodeCarbon mesure un *épisode*. Il répond « qu'a émis cette
exécution », pas « que coûte une requête », et sa sortie est un journal plutôt
qu'un artefact relu. Son échantillonnage est grossier par conception, à un prix
mesuré : une étude 2026 d'outils fondés sur RAPL sondant à 1 kHz situe le
surcoût en temps de CodeCarbon entre 5,4 % et 46,8 % — ce qui plaide pour son
intervalle par défaut, pas contre l'outil. Il produit un chiffre que les entrées
le justifient ou non, ce qui est le bon choix pour de la télémétrie et le
mauvais pour un chiffre que quelqu'un citera dans un rapport. **Prenez
CodeCarbon pour mesurer passivement des entraînements. Prenez celui-ci pour un
chiffre par unité que vous êtes prêt à défendre.**

### [Green Algorithms](https://www.green-algorithms.org/)

Le calculateur derrière la méthode qu'implémente ce paquet, issu de
l'[article de 2021](https://doi.org/10.1002/advs.202100707). Excellent pour une
estimation ponctuelle d'un calcul déjà fait ou pas encore fait, sans aucune
instrumentation. Bien sourcé et clairement expliqué.

Ce qui diffère : c'est un formulaire web, donc sa réponse vit dans un onglet de
navigateur plutôt que dans votre dépôt. Il ne mesure pas, ne compare pas les
versions, ne lit pas votre code. **Prenez le calculateur pour une estimation
rapide. Prenez celui-ci quand l'estimation doit vivre à côté du code et être
revérifiée au trimestre prochain.**

### [Scaphandre](https://github.com/hubblo-org/scaphandre) et [PowerAPI](https://powerapi.org/) / [pyJoules](https://github.com/powerapi-ng/pyJoules)

De la vraie mesure de puissance. Scaphandre est un agent qui expose la puissance
par processus à Prometheus ; PowerAPI et pyJoules donnent des lectures RAPL fines
depuis Python. Tous deux mesurent bien mieux que ce paquet, qui lit le compteur du
paquet processeur autour d'une tranche bornée et rien de plus.

Ce qui diffère : ils produisent des watts, pas des coûts. Pas d'intensité carbone,
pas de tarif, pas d'unité de travail, pas de provenance, pas de rapport.
**Prenez Scaphandre ou PowerAPI quand il vous faut une mesure de puissance
continue et sérieuse. Injectez le résultat dans un modèle comme celui-ci quand il
doit vouloir dire quelque chose pour un lecteur.**

### [JoularJX](https://github.com/joular/joularjx) et [PowerJoular](https://github.com/joular/powerjoular)

De la mesure de puissance à l'échelle du code source. PowerJoular mesure un
processus ; JoularJX est un agent Java, sans aucune modification du programme,
qui rapporte la puissance de chaque méthode appelée pendant qu'il tourne, puis
l'énergie totale de chacune à la sortie. Il lit RAPL via powercap sous Linux,
`powermetrics` sous macOS, un pilote sous Windows, et un modèle de puissance
ajusté sur un Raspberry Pi.

Ce qui diffère : l'attribution la plus fine de ce tableau, et aucun modèle de
coût au bout. Pas d'intensité carbone, pas de tarif, pas d'unité de travail, pas
de statut sur une ligne. **Prenez JoularJX quand la question est de savoir
quelle méthode coûte cher.** C'est aussi la réponse la plus nette à la sixième
colonne — un chiffre attribué à une méthode est un chiffre attribué au travail —
et c'est précisément ce que ce paquet ne fait pas.

### [Kepler](https://sustainable-computing.io/)

Attribution de puissance et de carbone pour des charges Kubernetes, depuis les
compteurs matériels, exportée vers Prometheus. Fort sur son terrain. En 2026 il a
réécrit sa collecte pour lire `/proc` et `/sys` au lieu d'eBPF (extended Berkeley
Packet Filter), abandonnant les `CAP_BPF` et `CAP_SYSADMIN` dont il avait
besoin — la même direction de moindre
privilège que prend ce paquet quand il imprime le remède pour un compteur réservé
à root au lieu d'acquérir les droits de le lire.

Ce qui diffère : c'est de l'infrastructure de cluster. Il répond « quels pods
consomment en ce moment », pas « que coûte une unité de travail », et il lui
faut un cluster pour répondre à quoi que ce soit. **Prenez Kepler pour une
flotte en production. Prenez celui-ci pour une base de code.**

### [CEEMS](https://github.com/ceems-dev/ceems)

Le Compute Energy and Emissions Monitoring Stack
([arXiv:2412.07290](https://arxiv.org/abs/2412.07290)) : l'énergie et les
émissions par travail de calcul, indifféremment sous l'ordonnanceur SLURM
(Simple Linux Utility for Resource Management), sous OpenStack et sous
Kubernetes, avec les métriques d'accélérateur à côté de celles du processeur et
du profilage eBPF continu sous les deux. Il tourne sur le supercalculateur Jean
Zay à un rythme d'environ vingt-cinq mille travaux par jour, et ce qui mérite
d'être noté, c'est que personne parmi ceux qui soumettent ces travaux n'a rien
changé pour être mesuré.

Ce qui diffère : c'est l'instrument d'une plateforme, installé une fois par qui
exploite la grappe, et qui répond pour tous les travaux qui y passent. Celui-ci
est l'instrument d'un dépôt, installé par qui a écrit le code, et qui répond
pour une unité de travail. **Prenez CEEMS quand vous exploitez les machines.**
Les deux se rejoignent le jour où un centre de calcul veut dire à un
utilisateur ce qu'a coûté une exécution de son code : c'est une phrase que ce
paquet écrit et que CEEMS n'écrit pas.

### [eco2AI](https://github.com/sb-ai-lab/Eco2AI) et [carbontracker](https://github.com/lfwa/carbontracker)

Deux traceurs à décorateur pour l'entraînement de modèles, proches d'esprit de
CodeCarbon. `carbontracker` prédit en plus l'empreinte d'une exécution complète à
partir de ses premières époques, ce qui est exactement l'idée de la projection sur
l'exécution complète de ce paquet.

Ce qui diffère : comme CodeCarbon. En forme d'épisode, en forme de journal,
muets sur la solidité de tel ou tel chiffre. **Prenez-les pour de la télémétrie
d'entraînement.**

### [EcoLogits](https://github.com/genai-impact/ecologits)

Instrumente les appels à six fournisseurs de modèles génératifs — Anthropic,
Cohere, Google GenAI, Hugging Face Hub, Mistral AI, OpenAI — et attache à chacun
une valeur d'énergie et une valeur de gaz à effet de serre. Licence Mozilla
Public License 2.0.

C'est le seul outil d'ici qui traite la question que ce paquet pose à propos
d'un appel d'interface payant, et il la traite mieux : ce paquet chiffre un tel
appel en argent, depuis un tarif publié, et ne dit rien de son énergie.

**L'idée à prendre.** Quand la taille du modèle derrière une interface fermée
est inconnue, EcoLogits ne choisit pas un nombre : il renvoie un `RangeValue`,
un `min` et un `max`, documentés comme un intervalle d'approximation à 95 %,
avec l'inconnue nommée — la taille du modèle, et la régression qui en tient
lieu. Elle est exposée plus haut, sous
[ce que cette page a pris aux autres](#pris-et-construit-une-fourchette-au-lieu-dun-point),
avec la raison pour laquelle elle est consignée plutôt que construite.

Ce qui diffère : pas d'unité de travail au-delà de l'appel, pas d'artefact
versionné, pas de barrière de dérive, et la valeur s'arrête à la porte du
fournisseur. **Prenez EcoLogits quand l'interface générative *est* le coût.
Prenez celui-ci quand elle n'est qu'une ligne d'un modèle qui doit aussi rendre
compte de la machine où tourne le code appelant.**

### [EnergiBridge](https://github.com/tdurieux/EnergiBridge)

Enveloppe n'importe quelle commande et journalise puissance, fréquence,
température, usage processeur et graphique, mémoire, dans un fichier de valeurs
séparées par des virgules. Processeurs Intel, AMD et M ; Linux, macOS **et
Windows**. Licence MIT.

Il mérite d'être nommé ici justement parce qu'il atteint la plateforme que ce
paquet refuse. Il y arrive en livrant un pilote en mode noyau sous Windows —
celui de LibreHardwareMonitor — ce qui répond à la question que
[`MESURER.md`](MESURER.md) laisse ouverte : Windows est mesurable, au prix de
l'installation d'un pilote. Ce prix est la raison pour laquelle ce paquet dit
encore non plutôt que de fonctionner à moitié, et nommer qui le paie est plus
utile que de répéter que la chose est impossible.

Ce qui diffère : il produit une trace, pas un modèle. Pas d'intensité carbone,
pas de tarif, pas d'unité de travail, pas de provenance sur une ligne, pas de
rapport. **Prenez EnergiBridge pour obtenir une trace de puissance sur une
machine que ce paquet ne lira pas. Faites entrer ce qu'il a mesuré dans un
modèle d'ici quand la trace doit vouloir dire quelque chose pour un lecteur.**

### [Green Metrics Tool](https://github.com/green-coding-solutions/green-metrics-tool) et [Eco-CI](https://github.com/green-coding-solutions/eco-ci-energy-estimation)

Le plus proche voisin du tableau ci-dessus, et celui qui a passé la première
version de cette page dans la mauvaise moitié. Green Metrics Tool mesure
l'énergie et le carbone d'une exécution logicielle décrite comme une
configuration dans un fichier, puis *publie* ce qu'il a mesuré. Eco-CI est la
moitié qui vit dans une chaîne d'intégration, et elle répond par une estimation
là précisément où ce paquet répond par un refus : sur un exécuteur hébergé où
aucun compteur d'énergie n'est lisible, elle estime depuis l'usage processeur
contre une courbe de puissance ajustée, et étiquette le résultat comme une
estimation.

Ce qui diffère : l'artefact est une exécution publiée, pas un modèle commité. Il
vous dira ce qu'a tiré cette construction-ci, avec sa propre réserve imprimée à
côté, et il ne vous dira pas ce que coûte une requête du service qui en sort, ni
ne tiendra un chiffre ouvert là où une entrée manque. **Prenez Green Metrics
Tool quand la chose à surveiller est une construction, et quand la mesure doit
être publique.** Ce qu'il publie est décrit plus bas, sous
[où ce domaine publie ses mesures](#où-ce-domaine-publie-ses-mesures) : c'est la
base de preuves publique la plus complète du domaine.

### [Cloud Carbon Footprint](https://www.cloudcarbonfootprint.org/)

Lit vos données de facturation cloud et en estime les émissions, avec un bon
tableau de bord et une méthodologie publiée et défendable.

Ce qui diffère : il part de la facture, donc il ne peut décrire que ce que vous
avez déjà dépensé, à la granularité du compte. Il ne peut pas dire ce que coûte une
inférence, ni quoi que ce soit avant que vous ayez exécuté la chose. **Prenez-le
pour du reporting organisationnel sur la dépense cloud. Prenez celui-ci pour des
décisions d'ingénierie sur une base de code.**

### [Infracost](https://www.infracost.io/)

Ce qui ressemble le plus à ce projet en esprit, dans un autre domaine. Il lit du
Terraform, estime ce que coûtera l'infrastructure avant qu'elle soit appliquée,
puis commente la différence sur votre pull request. La barrière de dérive ici
est la même idée.

Ce qui diffère : Infracost chiffre une infrastructure déclarée, pas du code
exécuté. Il ne parle que d'argent, et répond « combien coûtera cette pile par
mois », pas « que coûte une unité de travail sur cinq dimensions ». **Prenez
Infracost pour l'infrastructure as code. Les deux répondent à deux moitiés de la
même question et cohabitent très bien.**

### [Carbonifer](https://github.com/carboniferio/carbonifer)

Le frère carbone d'Infracost, et la preuve que la forme se généralise :
`carbonifer plan` lit les mêmes fichiers Terraform et estime les émissions d'une
infrastructure qui n'existe pas encore, de sorte qu'une région ou une taille
d'instance se discute avant que quoi que ce soit soit provisionné.

Ce qui diffère : la même frontière qu'Infracost. Il chiffre une infrastructure
déclarée et non du code exécuté, et son unité est l'heure-machine et non l'unité
de travail. **Prenez Carbonifer pour comparer deux plans.** À eux deux, ils sont
la preuve la plus nette de ce tableau que la barrière de dérive d'ici n'est pas
une idée originale : c'est leur idée, pointée vers un dépôt au lieu d'un plan.

### [FOCUS](https://focus.finops.org/) et l'économie à l'unité

Pas un outil, et pas de note : un schéma et un vocabulaire. La FinOps Open Cost and
Usage Specification normalise les données de facturation d'un fournisseur à
l'autre — la version 1.4 a été ratifiée en juin 2026 — et le cadre de la FinOps
Foundation nomme, du côté de l'argent, la primitive sur laquelle ce paquet est
bâti : un coût unitaire est un coût attribué divisé par une métrique métier, un
coût par client, par transaction, par sortie réussie.

Ce qui diffère : il normalise le numérateur, qui est la facture, et vous laisse
le dénominateur. Or le dénominateur est toute la difficulté de ce paquet — ce
qu'*est* une unité de travail, et combien une exécution en a accompli — et c'est
la part que personne d'autre ne peut vous tendre. **Lisez FOCUS quand plusieurs
factures doivent être comparées.** Les deux moitiés s'emboîtent.

### [OpenCost](https://www.opencost.io/) et Kubecost

Allocation de coûts en temps réel pour Kubernetes, par namespace, charge et label.
La réponse standard à « quelle équipe dépense quoi » sur un cluster.

Ce qui diffère : de l'allocation d'une facture déjà engagée, pas un modèle d'unité
de travail. L'argent d'abord, le carbone en supplément. **Prenez OpenCost pour de
la refacturation interne.**

### Consoles de facturation cloud

AWS (Amazon Web Services) Cost Explorer, GCP (Google Cloud Platform) Billing, Azure Cost Management. Font autorité sur ce qui
vous a été facturé, ce qui est exactement une dimension d'une question, après coup.
**Prenez-les quand la question est « pourquoi la facture était-elle si grosse ».**

## L'autre côté de la pièce : ce qu'une équipe de responsabilité sociétale des entreprises (RSE) a déjà

Les outils ci-dessus répondent à une question d'ingénierie. Ceux qui doivent
*déclarer* un chiffre carbone en utilisent un tout autre jeu, dont aucun ne
figure dans le tableau en tête de page — délibérément, parce que les noter à
l'aune de la niche de cet outil serait une comparaison peu flatteuse sur une
question qu'ils ne cherchent pas à traiter.

### Les plateformes de comptabilité carbone

[Normative](https://normative.io/), [Greenly](https://greenly.earth/),
[Sweep](https://www.sweep.net/), [Persefoni](https://www.persefoni.com/) et
[Watershed](https://watershed.com/) sont le système de référence du bilan d'une
organisation entière : tous les scopes, toutes les catégories, le processus de
double matérialité, dans plusieurs cas le dépôt balisé lui-même.

Ce qui les distingue : aucune ne lit votre code. Le chiffre d'un logiciel est
une *entrée* qu'elles ne peuvent pas produire ; ce qui leur parvient à la place
est d'ordinaire une facture cloud divisée par quelque chose. **Servez-vous-en
pour déclarer. Servez-vous de celui-ci pour produire la ligne logicielle qui
leur manque** — [`INVENTAIRE.md`](INVENTAIRE.md) dit de quelle ligne il s'agit.

### Où ce domaine publie ses mesures

Pas des outils entre lesquels choisir, et pour la plupart pas notés plus haut :
ce sont les endroits où ce domaine met ses *preuves*, bons à connaître parce
qu'ils fixent ce qu'un lecteur attend d'une page de chiffres. Lu le 2026-10-18.

**[Green Metrics Tool](https://github.com/green-coding-solutions/green-metrics-tool) et [Energy-ID](https://www.green-coding.io/products/energy-id/)**, par
Green Coding Solutions, noté dans le tableau ci-dessus, où il est décrit comme
un outil. Ce qu'il *publie* a sa place ici : des [pages
de statistiques](https://metrics.green-coding.io/) par exécution, des vues
chronologiques qui suivent un projet de commit en commit, des vues de
comparaison, une interface de programmation applicative (API) publique et des
badges d'intégration continue. Energy-ID est la base de données à côté : elle
évalue des logiciels libres, des outils en ligne de commande et des primitives
de langage sur des machines fixes, et publie une fiche par tâche, chacune
énonçant la machine et portant la réserve dans ses propres mots : *« absolute
numbers shown here are not to be taken as ground truth »*. C'est la base de
preuves publique la plus complète du domaine, et ce qui ressemble le plus à une
galerie chez ces outils.

**[Le classement ML.ENERGY](https://ml.energy/leaderboard/)** — l'énergie du machine learning (ML) —
par l'initiative ML.ENERGY du Michigan ([arXiv:2505.06371](https://arxiv.org/abs/2505.06371)).
L'énergie d'inférence de modèles génératifs, mesurée plutôt que modélisée : la
version 3.0 rapporte 46 modèles sur 7 tâches, 1 858 configurations sur des GPU
NVIDIA H100 et B200. Ce qui rend ses lignes comparables est ce qu'elle tient
constant : elle compare la *configuration à énergie minimale* de chaque modèle,
pour s'en tenir aux différences de modèle et de tâche « without being confounded
by hardware utilization differences ». Un résultat à en retenir : les tâches de
raisonnement coûtent environ **vingt-cinq fois** l'énergie par réponse d'une
conversation textuelle ordinaire, un terme bien plus grand que tout ce qu'un
outil qui lit du code peut voir.

Son article compagnon de 2026, [*Where Do the Joules Go?*](https://arxiv.org/abs/2601.22076),
mesure le facteur de confusion que le classement tient fixe : l'utilisation de
l'accélérateur déplace à elle seule l'énergie d'inférence d'un facteur trois à
cinq sur les mêmes 1 858 configurations, et une vidéo coûte parfois plus de cent
fois une image. Deux de ces trois termes sont invisibles à tout outil qui lit un
dépôt.

**[L'AI Energy Score](https://huggingface.github.io/AIEnergyScore/)**, par
Hugging Face, Salesforce, Cohere et l'université Carnegie Mellon. La même forme
d'étoiles que le tableau en tête de cette page, portant sur des modèles plutôt
que sur des outils : dix tâches généralistes, une énergie mesurée sur une seule
génération d'accélérateur, rapportée en wattheures pour mille requêtes, une note
d'une à cinq étoiles, et un classement qui couvre 166 modèles. Deux de ses
décisions méritent d'être copiées par quiconque publie une note. Les étoiles
valent explicitement par rapport à la cohorte notée, de sorte que personne ne
peut en citer une comme un absolu. Et le réétalonnage suit un calendrier annoncé,
environ deux fois par an, ce qui est la seule façon honnête de tenir une échelle
comparative pendant que le domaine bouge dessous.

**[Les études de cas Software Carbon Intensity (SCI) de la Green Software Foundation](https://sci-guide.greensoftware.foundation/CaseStudies/)**.
Onze publiées, par CAST, UBS, NTT DATA, Microsoft, AFAS et d'autres, chacune un
chiffre SCI déclaré pour une vraie application. L'index porte l'organisation, une
phrase et un lien ; le chiffre, l'unité fonctionnelle et la frontière sont dans
le document lié. C'est le catalogue de référence de *ce à quoi ressemble un
chiffre déclaré*, qui est une autre question que celle de l'outil qui l'a
produit.

### Les normes ont bougé deux fois pendant l'écriture

Les deux sont en amont de tous les outils du tableau, et aucune n'est un outil.

**[SCI for AI](https://greensoftware.foundation/standards/sci-ai/) a été
ratifiée en décembre 2025.** Elle étend la méthode Software Carbon Intensity —
déjà une norme de l'Organisation internationale de normalisation (ISO) et de la
Commission électrotechnique internationale (IEC), ISO/IEC 21031:2024 — au cycle
de vie d'un système d'intelligence artificielle : intensité du réseau
électrique locale, émissions incorporées du matériel, unité fonctionnelle
normalisée pour que deux systèmes se comparent, et aucune compensation. Ce sont
les quatre termes que ce paquet calcule ; [`NORMES.md`](NORMES.md) dit où il s'y
conforme et où il s'en écarte délibérément.

**Le carbone est proposé comme signal de plein droit dans OpenTelemetry.** Le
travail [sci-otel](https://github.com/Green-Software-Foundation/sci-otel) de la
Green Software Foundation rédige des conventions sémantiques pour l'énergie,
l'intensité carbone, le carbone incorporé et l'unité fonctionnelle, et remet le
plan au groupe de spécification d'OpenTelemetry. S'il aboutit, le domaine
obtient un vocabulaire unique et les noms de champs du YAML de ce paquet en
deviennent un dialecte.

### [Electricity Maps](https://www.electricitymaps.com/) et [WattTime](https://watttime.org/)

D'où vient une intensité carbone. WattTime publie un signal *marginal* — les
émissions de la centrale qui répond à une unité de demande supplémentaire — au
pas de cinq minutes. Electricity Maps publie un signal *moyen*, horaire, et a
**retiré son propre signal marginal** en 2025, en disant publiquement qu'elle ne
pouvait pas se porter garante de la véracité ni de la vérifiabilité d'un tel
signal.

Ce retrait est la chose la plus utile de cette page pour quiconque construit un
outil comme celui-ci. Un fournisseur a retiré un produit du marché parce qu'il
ne pouvait pas défendre le chiffre : c'est le geste que fait ce paquet quand il
écrit `TODO` au lieu d'une valeur plausible, à une échelle bien plus petite. Le
catalogue d'ici porte des intensités moyennes et dit lesquelles.

### [Carbonlog](https://www.cnaught.com/blog/how-to-actually-measure-the-carbon-footprint-of-ai-code)

Lancé en mars 2026 par CNaught : un greffon qui suit l'énergie et les émissions
d'une séance de code écrite avec un assistant, à mesure, ventilées par modèle et
par projet, calculées depuis les valeurs par requête publiées par
[Jegham et ses collègues](https://arxiv.org/abs/2505.09598) plutôt que depuis un
compteur — il n'y a aucun compteur à lire, puisque l'inférence a eu lieu sur la
machine de quelqu'un d'autre.

Il est ici parce qu'il mesure le seul coût que ce paquet ne peut
structurellement pas voir : non pas ce que coûte l'exécution de votre code, mais
ce qu'a coûté son écriture. Les deux sont réels, et rien dans ce tableau ne les
additionne.

### [Boavizta](https://boavizta.org/en/tools)

Une association qui publie données et outils ouverts sur l'impact
environnemental des équipements numériques : `BoaviztAPI` pour les équipements et
les instances cloud, `Datavizta` pour explorer les empreintes des constructeurs,
`cloud-scanner` pour lire un usage AWS réel, `e-footprint` pour modéliser un
service numérique entier. Multicritère plutôt que carbone seul — énergie primaire
et épuisement des ressources abiotiques à côté du potentiel de réchauffement.

Ce paquet en dépend déjà : les quatre empreintes processeur du catalogue sont
calculées par `BoaviztAPI`, dont la moitié GPU est **refusée nommément** parce
qu'elle répond un archétype unique pour toutes les cartes. L'usage comme le
refus sont exposés dans [`NORMES.md`](NORMES.md).

Ce qui les distingue : Boavizta modélise un inventaire d'*équipements* — tant
d'instances, pendant tant de temps. Celui-ci modélise une *unité de travail issue
d'un dépôt*. Les deux se rejoignent au milieu et aucun ne remplace l'autre.
**Boavizta pour poser une empreinte sur un parc. Celui-ci pour en poser une sur
une requête.**

### [Impact Framework](https://if.greensoftware.foundation/)

La chaîne pilotée par manifeste de la Green Software Foundation : des greffons
convertissent des métriques observables en impacts environnementaux, ce qui en
fait le véhicule par lequel la spécification SCI est habituellement mise en
œuvre.

Ce qui le distingue : c'est un graphe de calcul que l'on configure, pas un
artefact commité portant un contrat de provenance. Un manifeste dit comment un
chiffre a été calculé ; il ne refuse pas d'en produire un quand les entrées ne le
justifient pas. **IF pour composer une chaîne entre plusieurs outils. Celui-ci
quand la sortie doit être défendue.**

### [Climatiq](https://www.climatiq.io/)

Une API de facteurs d'émission : on envoie des données d'activité, on reçoit des
émissions, contre une base de facteurs maintenue.

Ce qui la distingue : elle répond *quel est le facteur*, pas *qu'a fait ce code*.
Elle se place en amont d'un outil comme celui-ci plutôt qu'à côté.

## Là où celui-ci est le plus faible

Autant être honnête sur les manques, puisque c'est toute la prémisse de l'outil.

- **Les coûts tarifent toujours la machine, pas le processus.** Chaque compteur
  ici mesure du *matériel* : la puissance que porte un modèle de coût contient
  le navigateur d'à côté. Deux séparations sont désormais enregistrées auprès
  d'elle — le plancher au repos que la machine tirait avant, la part du temps
  processeur de la machine revenant à l'exécution, appliquée au compteur propre
  du processeur — et un modèle mesuré énonce les deux dans la phrase attachée à
  sa figure de puissance. Ce qui n'a pas changé, c'est le nombre que les coûts
  utilisent : le nombre entier. Scaphandre, PowerAPI, Kepler et CEEMS vont plus
  loin et modélisent une consommation par processus, par conteneur et par
  travail soumis, et JoularJX va plus loin encore en attribuant la puissance à
  une méthode ; ce paquet enregistre l'encadrement et refuse de choisir à
  l'intérieur. Sur une machine partagée, c'est toujours le manque qui compte le
  plus — raison pour laquelle il est désormais la sixième colonne du tableau
  plus haut, et non une phrase ici en bas.
- **Deux plateformes, pas trois.** Linux et macOS, qui lisent toutes deux de
  vrais compteurs — zones powercap par leur nom, `IOReport` sur Apple Silicon,
  NVML (NVIDIA Management Library) et les interfaces sysfs `amdgpu` / `i915` / `xe` pour l'accélérateur.
  Windows est hors périmètre plutôt qu'inachevé : il n'offre aucun compteur
  d'énergie processeur sans privilèges, aucun total de temps processeur machine,
  et aucune comptabilité POSIX (Portable Operating System Interface) des ressources — chaque chiffre y serait une
  estimation. Plus étroit que les outils au-dessus dans ce tableau, et étroit à
  dessein — mais le dessein se conteste, et Eco-CI le conteste : sur un
  exécuteur hébergé sans compteur lisible, elle estime depuis l'usage processeur
  contre une courbe de puissance ajustée et étiquette la réponse comme une
  estimation, ce qui est défendable quand on dispose d'un vocabulaire qui a un
  mot pour `estimated`. Le refus d'ici tient sur une affirmation plus étroite :
  une estimation est honnête quand le modèle qui la porte est publié et ajusté à
  la machine, et aucun modèle de ce genre n'a été ajusté pour les machines
  Windows que ce paquet rencontrerait.
- **Un compteur n'est pas la prise murale.** Ventilateurs, stockage, réseau et
  alimentation sont hors RAPL et hors NVML par construction, et l'écart n'est pas
  une constante qu'on pourrait rajouter : mesuré face à des wattmètres physiques,
  c'est une pente d'environ 1,17, variable d'un nœud à l'autre. Chaque chiffre ici
  est le périmètre qu'il nomme, jamais la machine.
- **Pas de suivi continu.** Une tranche bornée, une fois. Si vous voulez une série
  temporelle, ce n'est pas la bonne forme d'outil.
- **Le carbone incorporé est implémenté et à peine catalogué.** L'arithmétique est
  là — les quatre termes de la norme conjointe de l'Organisation internationale
  de normalisation et de la Commission électrotechnique internationale,
  ISO/IEC 21031, amortis en temps calendaire — et huit
  empreintes aussi : quatre accélérateurs sur 25 lignes et quatre processeurs sur
  12. Tout le reste rapporte `TODO`. La durée de vie reste à vous, parce que
  combien de temps une carte reste en service est un fait sur un parc et non sur
  une pièce. Voir [`NORMES.md`](NORMES.md) pour le tableau et les huit refus.
- **Les catalogues sont petits.** Ils couvrent les accélérateurs courants et les
  grands réseaux électriques. Au-delà, vous tomberez sur un manque, et l'outil vous
  dira quelle ligne ajouter.
- **La projection entre machines est un rapport de fiches techniques.** Le débit
  crête n'est pas un benchmark. Les gains réels sont plus petits, et la projection
  le dit dans ses limites plutôt que dans une note de bas de page.

## Là où il vaut la peine d'être choisi

Quand le chiffre doit survivre à une contestation. Quand quelqu'un va mettre une
empreinte carbone par requête dans un document client, ou un coût par exécution
dans un budget, puis qu'on lui demandera six mois plus tard d'où ça vient. C'est
le cas que ces outils, pour la plupart, ne servent pas : ils produisent des
chiffres ; celui-ci produit des chiffres qui viennent avec leur propre piste
d'audit et qui refusent d'exister quand il faudrait les inventer.

C'est aussi le seul outil de ce tableau qui *mesure comment le coût croît avec
la taille du travail* : trois tranches de tailles différentes, un exposant
ajusté, une qualité d'ajustement, un refus net de projeter quand l'ajustement
dit que les tranches ne mesurent pas un comportement cohérent. Tous les autres
ici projettent au prorata des tailles, ou ne projettent pas.
