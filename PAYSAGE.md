# Paysage

🇫🇷 Français · [🇬🇧 LANDSCAPE.md](LANDSCAPE.md)

Les autres outils du domaine « combien coûte l'exécution de ce code », avec le
cas où chacun est le meilleur choix. Les notes vont de ⭐ (1) à ⭐⭐⭐⭐⭐ (5),
attribuées au regard du travail de *cet* outil-ci : **un modèle de coût
versionné, relisible, par unité de travail, sur plusieurs dimensions, où chaque
chiffre dit jusqu'où on peut lui faire confiance**. Un outil conçu pour un autre
travail n'est pas pénalisé d'être bon à ce travail-là ; la note ne dit que
l'adéquation à cette niche.

Chiffres vérifiés le 2026-10-01. Les projets bougent ; si quelque chose ici a
vieilli, [dites-le](CONTRIBUTING.md).

## Vue d'ensemble

| | Modèle par unité | Provenance sur chaque chiffre | Multi-dimension | Artefact versionné | Mesure la puissance | Estime sans exécuter | Barrière de dérive | Rapports lisibles | Hors ligne |
| --- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **saggio** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| CodeCarbon | ⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ | ⭐ | ⭐ | ⭐⭐⭐ | ⭐⭐⭐ |
| Calculateur Green Algorithms | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐ | ⭐ | ⭐⭐⭐⭐⭐ | ⭐ | ⭐⭐⭐ | ⭐ |
| Scaphandre | ⭐ | ⭐⭐ | ⭐ | ⭐ | ⭐⭐⭐⭐⭐ | ⭐ | ⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ |
| PowerAPI / pyJoules | ⭐⭐ | ⭐⭐ | ⭐ | ⭐ | ⭐⭐⭐⭐⭐ | ⭐ | ⭐ | ⭐ | ⭐⭐⭐⭐⭐ |
| Kepler | ⭐ | ⭐⭐ | ⭐⭐ | ⭐ | ⭐⭐⭐⭐ | ⭐⭐ | ⭐ | ⭐⭐ | ⭐⭐⭐⭐ |
| eco2AI | ⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐⭐ | ⭐ | ⭐ | ⭐⭐ | ⭐⭐⭐ |
| carbontracker | ⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐ | ⭐⭐ | ⭐⭐ |
| EcoLogits | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐ | ⭐ | ⭐⭐ | ⭐ | ⭐⭐ | ⭐⭐⭐ |
| EnergiBridge | ⭐ | ⭐⭐ | ⭐ | ⭐ | ⭐⭐⭐⭐⭐ | ⭐ | ⭐ | ⭐ | ⭐⭐⭐⭐⭐ |
| Cloud Carbon Footprint | ⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐ | ⭐ | ⭐⭐⭐ | ⭐ | ⭐⭐⭐⭐ | ⭐ |
| Infracost | ⭐⭐⭐ | ⭐⭐⭐ | ⭐ | ⭐⭐⭐ | ⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐ |
| OpenCost / Kubecost | ⭐⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐ | ⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ | ⭐ |
| Consoles de facturation cloud | ⭐ | ⭐⭐⭐⭐ | ⭐ | ⭐ | ⭐ | ⭐ | ⭐⭐ | ⭐⭐⭐⭐ | ⭐ |

## La carte

Le même tableau, dessiné. [standpoint](https://github.com/warith-
harchaoui/standpoint) passe une analyse en composantes principales sur les neuf
notes et dispose chaque outil le long des deux directions qui les distinguent
vraiment, en orientant la carte pour que saggio soit en haut à droite. Deux axes
gardent environ les trois quarts de ce qui sépare ces outils : 55 %
horizontalement, 25 % verticalement. Les noms d'axes sont la lecture que la
machine fait des loadings ; ce que les loadings disent est plus simple : plus on
va à **droite**, plus l'outil produit des réponses sourcées, versionnées, par
unité de travail ; plus on va à **gauche**, plus il mesure la puissance en
direct. Plus on **monte**, plus il tourne sur votre propre machine et la lit ;
plus on **descend**, plus c'est quelque chose qu'on pointe vers une facture ou
un formulaire.

<p align="center"> <img src="assets/landscape.png" alt="Carte de positionnement
des quatorze outils le long de deux composantes principales, saggio en haut à
droite" width="720"> </p>

Les distances sont celles du tableau, pas une opinion : deux outils sont voisins
parce que leurs lignes de notes le sont. Après une mise à jour du tableau,
régénérez avec `standpoint <table> -r saggio --model qwen3:8b` et commitez les
`assets/landscape.png` et `assets/landscape.svg` rafraîchis.

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

### [Kepler](https://sustainable-computing.io/)

Attribution de puissance et de carbone pour des charges Kubernetes, depuis les
compteurs matériels, exportée vers Prometheus. Fort sur son terrain. En 2026 il a
réécrit sa collecte pour lire `/proc` et `/sys` au lieu d'eBPF, abandonnant les
`CAP_BPF` et `CAP_SYSADMIN` dont il avait besoin — la même direction de moindre
privilège que prend ce paquet quand il imprime le remède pour un compteur réservé
à root au lieu d'acquérir les droits de le lire.

Ce qui diffère : c'est de l'infrastructure de cluster. Il répond « quels pods
consomment en ce moment », pas « que coûte une unité de travail », et il lui
faut un cluster pour répondre à quoi que ce soit. **Prenez Kepler pour une
flotte en production. Prenez celui-ci pour une base de code.**

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
lieu. C'est la règle du maillon faible de ce paquet atteinte par un autre
chemin, et c'est la forme qu'une dimension `api_energy` devrait prendre ici.
Consignée dans [`FRONTIERES.md`](FRONTIERES.md) plutôt que construite : la
fourchette n'est honnête que tant que quelqu'un tient les régressions à jour.

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
figure dans le tableau en tête de page — délibérément, parce que les noter
contre la niche de cet outil serait une comparaison peu flatteuse sur une
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

Pas des outils entre lesquels choisir, et pas notés plus haut : ce sont les
endroits où ce domaine met ses *preuves*, bons à connaître parce qu'ils fixent
ce qu'un lecteur attend d'une page de chiffres. Lu le 2026-10-18.

**[Green Metrics Tool](https://github.com/green-coding-solutions/green-metrics-
tool) et [Energy-ID](https://www.green-coding.io/products/energy-id/)**, par
Green Coding Solutions. L'outil mesure l'énergie et le carbone d'une exécution
logicielle par configuration-as-code, puis publie ce qu'il a mesuré : des [pages
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

**[Les études de cas Software Carbon Intensity (SCI) de la Green Software Foundation](https://sci-guide.greensoftware.foundation/CaseStudies/)**.
Onze publiées, par CAST, UBS, NTT DATA, Microsoft, AFAS et d'autres, chacune un
chiffre SCI déclaré pour une vraie application. L'index porte l'organisation, une
phrase et un lien ; le chiffre, l'unité fonctionnelle et la frontière sont dans
le document lié. C'est le catalogue de référence de *ce à quoi ressemble un
chiffre déclaré*, qui est une autre question que celle de l'outil qui l'a
produit.

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
  utilisent : le nombre entier. Scaphandre, PowerAPI et Kepler vont plus loin et
  modélisent une consommation par processus et par conteneur ; ce paquet
  enregistre l'encadrement et refuse de choisir à l'intérieur. Sur une machine
  partagée, c'est toujours le manque qui compte le plus. - **Deux plateformes,
  pas trois.** Linux et macOS, qui lisent toutes deux de vrais compteurs — zones
  powercap par leur nom, `IOReport` sur Apple Silicon, NVML (NVIDIA Management
  Library) et les interfaces sysfs `amdgpu` / `i915` / `xe` pour l'accélérateur.
  Windows est hors périmètre plutôt qu'inachevé : il n'offre aucun compteur
  d'énergie processeur sans privilèges, aucun total de temps processeur machine,
  et aucune comptabilité POSIX (Portable Operating System Interface) des
  ressources — chaque chiffre y serait une estimation. Plus étroit que les
  outils au-dessus dans ce tableau, et étroit à dessein. - **Un compteur n'est
  pas la prise murale.** Ventilateurs, stockage, réseau et alimentation sont
  hors RAPL et hors NVML par construction, et l'écart n'est pas une constante
  qu'on pourrait rajouter : mesuré face à des wattmètres physiques, c'est une
  pente d'environ 1,17, variable d'un nœud à l'autre. Chaque chiffre ici est le
  périmètre qu'il nomme, jamais la machine. - **Pas de suivi continu.** Une
  tranche bornée, une fois. Si vous voulez une série temporelle, ce n'est pas la
  bonne forme d'outil. - **Le carbone incorporé est implémenté et à peine
  catalogué.** L'arithmétique est là — les quatre termes de la norme conjointe
  de l'Organisation internationale de normalisation et de la Commission
  électrotechnique internationale, ISO/IEC 21031, amortis en temps calendaire —
  et huit empreintes aussi : quatre accélérateurs sur 25 lignes et quatre
  processeurs sur 12. Tout le reste rapporte `TODO`. La durée de vie reste à
  vous, parce que combien de temps une carte reste en service est un fait sur un
  parc et non sur une pièce. Voir [`NORMES.md`](NORMES.md) pour le tableau et
  les huit refus. - **Les catalogues sont petits.** Ils couvrent les
  accélérateurs courants et les grands réseaux électriques. Au-delà, vous
  tomberez sur un manque, et l'outil vous dira quelle ligne ajouter. - **La
  projection entre machines est un rapport de fiches techniques.** Le débit
  crête n'est pas un benchmark. Les gains réels sont plus petits, et la
  projection le dit dans ses limites plutôt que dans une note de bas de page.

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
