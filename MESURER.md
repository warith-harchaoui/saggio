# Mesurer

[🇬🇧 MEASURING.md](MEASURING.md) · 🇫🇷 Français

Une puissance tirée d'une fiche technique est une supposition sur une puce. Une
puissance tirée d'un compteur est un fait sur une exécution. Cette page parle des
compteurs : lesquels existent, lesquels cette machine acceptera de *vous* laisser
lire, ce que chacun couvre réellement, et ce qu'il advient du chiffre ensuite.

Elle existe parce que « impossible de mesurer la puissance » n'est pas une
réponse. Un portable sans compteur, un serveur dont le compteur est fermé à tout
le monde sauf à root, un conteneur qui ne voit pas `/sys`, et une puce que
personne n'a appris à ce paquet à lire sont quatre situations différentes avec
quatre remèdes différents — et une seule est une question qui revient au lecteur.

## Sommaire

- [Demander d'abord à la machine](#demander-dabord-à-la-machine)
- [Ce qui répond, par plateforme](#ce-qui-répond-par-plateforme)
- [Les quatre états](#les-quatre-états)
- [La règle sur les privilèges](#la-règle-sur-les-privilèges)
- [Ce que chaque chiffre laisse de côté](#ce-que-chaque-chiffre-laisse-de-côté)
- [Du compteur au coût](#du-compteur-au-coût)
- [De cette machine à une autre](#de-cette-machine-à-une-autre)
- [Vérifier par vous-même](#vérifier-par-vous-même)
- [Sources](#sources)

## Demander d'abord à la machine

```bash
saggio power
```

Un bloc par interface, chacune dans l'un de quatre états, chacune disant ce
qu'elle couvre et pourquoi elle est dans cet état. Là où quelque chose peut être
fait, la commande qui le ferait est affichée — et pas exécutée. Voir
[EXEMPLES.md](EXEMPLES.md#ce-que-cette-machine-accepte-de-vous-dire) pour la
sortie et ce qu'il faut en conclure.

Pour voir les compteurs fonctionner avant qu'une exécution en dépende :

```bash
saggio power --seconds 2
```

Cela mesure la *machine*, pas votre programme. Sur un portable occupé, le chiffre
est surtout le travail des autres, ce qui est la première chose à savoir d'un
compteur à l'échelle de la machine.

## Ce qui répond, par plateforme

| Plateforme | Interface | Couvre | Privilège | Comment c'est lu |
|---|---|---|---|---|
| Linux | [powercap / RAPL](https://docs.kernel.org/power/powercap/powercap.html) | les paquets processeur, la zone `psys` quand elle existe, et la zone mémoire à côté | **root par défaut depuis la 5.10** | `energy_uj` cumulé, une différence par exécution |
| Linux | [hwmon `amdgpu`](https://docs.kernel.org/gpu/amdgpu/thermal.html) | la carte graphique | aucun | `power1_average` en µW, échantillonné pendant la course |
| Linux | hwmon [`i915`](https://www.kernel.org/doc/html/latest/gpu/i915.html) / [`xe`](https://github.com/torvalds/linux/blob/master/Documentation/ABI/testing/sysfs-driver-intel-xe-hwmon) | la carte graphique | aucun | `energy1_input` cumulé en µJ |
| Linux, Windows | [pilote NVIDIA](https://developer.nvidia.com/management-library-nvml), via [`nvidia-smi`](https://docs.nvidia.com/deploy/nvidia-smi/index.html) | toute la carte accélératrice | aucun | énergie cumulée quand la carte en tient, sinon puissance échantillonnée |
| macOS, Apple Silicon | `IOReport`, la bibliothèque derrière `powermetrics` | cœurs du processeur, cœurs graphiques, moteur neuronal, mémoire | **aucun** | compteurs monotones par sous-système, une différence par exécution |
| macOS | `powermetrics` | les mêmes sous-systèmes | root | non utilisé par ce paquet |
| Windows | [Energy Meter Interface](https://learn.microsoft.com/en-us/windows-hardware/drivers/powermeter/energy-meter-interface) | ce qu'un constructeur a choisi d'instrumenter | un pilote | non utilisé par ce paquet |
| Tout serveur | IPMI / DCMI / [Redfish](https://www.dmtf.org/standards/redfish) | le nœud entier, ventilateurs et pertes d'alimentation compris | identifiants du contrôleur | non utilisé par ce paquet |

Deux lignes de ce tableau méritent une phrase chacune.

**Apple Silicon.** Pendant presque toute l'histoire de ce paquet, un Mac ne
mesurait rien, et la raison affichée était que macOS ne publie la puissance que
par `powermetrics`, qui exige un mot de passe. La première moitié était fausse.
Les compteurs qu'affiche `powermetrics` viennent d'`IOReport`, qui répond à un
utilisateur ordinaire, et c'est ce que lit
[`saggio/analyze/apple.py`](saggio/analyze/apple.py). Apple ne documente ni la
bibliothèque ni les noms de canaux ; la correspondance utilisée ici a été établie
en lisant les canaux sur de vraies machines, comme le font
[macmon](https://github.com/vladkens/macmon) et ses semblables — et une puce dont
les canaux ne sont pas reconnus ne mesure rien plutôt que d'inventer.

**La zone mémoire.** Sous Linux, `dram` est une *sous-zone* d'un paquet dans
l'arborescence sysfs, mais son énergie n'est **pas** dans le chiffre de ce
paquet. Lire les zones par le nom que chacune se donne, plutôt que par la forme
de son répertoire, est ce qui rend cette différence visible — et cela signifie
qu'une machine qui publie la zone rapporte désormais une mémoire qu'elle laissait
de côté. Sur Apple Silicon, le même chiffre vient du canal `DRAM0`. Là où l'un ou
l'autre répond, la mémoire mesurée remplace le terme que
[Green Algorithms](https://doi.org/10.1002/advs.202100707) estime à partir de la
capacité installée.

## Les quatre états

| État | Ce que ça veut dire | Est-ce votre décision ? |
|---|---|---|
| `reads` | Le compteur vous répond, maintenant, sans rien demander. | Non, ça marche déjà. |
| `blocked` | Le compteur est sur cette machine et vous est fermé. | **Oui.** Le seul avec un remède. |
| `root-only` | Il n'existe que derrière des droits d'administrateur, et ce paquet n'ira pas les chercher. | Non, c'est voulu. |
| `absent` | Il n'y a rien à lire ici. | Non, c'est une propriété de la machine. |

`absent` n'est pas un échec. Une machine virtuelle dont l'hôte ne transmet pas
les compteurs, une carte ARM sans arborescence powercap, un conteneur sans
`/sys/class/powercap` monté : tous sont d'honnêtes `absent`, et le modèle de coût
retombe sur une estimation étiquetée comme telle. Un chiffre plus faible, pas un
chiffre faux.

## La règle sur les privilèges

**Rien dans ce paquet n'escalade.** Pas de `sudo`, pas de demande de mot de
passe, pas de repli silencieux sur un outil qui en réclamerait un. Un outil de
mesure qui acquiert des privilèges pour son propre compte est un problème pire
qu'une puissance estimée.

Cette règle mord sous Linux, où le compteur du processeur est `blocked` pour les
utilisateurs ordinaires sur tout noyau à partir de la 5.10. Le noyau l'a fermé
exprès : échantillonné assez vite, `energy_uj` permet de reconstituer ce que
calculent les *autres* processus — l'attaque
[PLATYPUS](https://platypusattack.com/),
[CVE-2020-8694](https://nvd.nist.gov/vuln/detail/CVE-2020-8694). `saggio power`
affiche donc le remède avec cette raison à côté, et s'arrête là :

```
to open it: Until the next reboot:  sudo chmod a+r /sys/class/powercap/*/energy_uj
    Across reboots, a udev rule that touches the energy files and nothing else:
      SUBSYSTEM=="powercap", ACTION=="add", RUN+="/bin/chmod a+r /sys%p/energy_uj"
    in /etc/udev/rules.d/99-saggio-rapl.rules.
```

En lecture seule, et seulement les fichiers d'énergie : les limites de puissance
à côté restent fermées, donc rien ici ne permet de brider ou de faire chauffer la
machine. Rouvrir un canal auxiliaire publié sur une machine que vous partagez
peut-être avec d'autres est un jugement sur qui sont ces autres, et il reste le
vôtre.

Sur un cluster partagé, la meilleure réponse est le plus souvent de ne rien
ouvrir. Votre exploitant mesure déjà des nœuds entiers par le contrôleur de
gestion, et un chiffre venu de là couvre les ventilateurs et les pertes
d'alimentation, ce qu'aucun compteur interne à la puce ne fera jamais. Un modèle
de coût peut porter ce chiffre comme une quantité `measured` avec sa propre
source ; voir [EXEMPLES.md](EXEMPLES.md#mettre-la-mesure-dans-le-modèle).

## Ce que chaque chiffre laisse de côté

Chaque lecture produite par ce paquet dit ce qu'elle couvre, dans le modèle et
dans le rapport. Les frontières méritent d'être énoncées une fois, clairement :

- **Le paquet RAPL** couvre les cœurs et l'uncore. Pas la mémoire, sauf si la
  zone `dram` a répondu aussi ; pas un accélérateur discret ; pas le stockage ;
  pas les ventilateurs ; pas les pertes propres de l'alimentation.
- **`psys`**, quand une machine le publie, couvre tout le système sur puce et
  contient déjà les paquets — il est donc utilisé *à la place* d'eux, jamais
  ajouté à eux.
- **Les compteurs Apple** couvrent les cœurs du processeur, les cœurs graphiques,
  le moteur neuronal et la mémoire. Pas l'écran, ce qui sur un portable est une
  omission considérable.
- **Un compteur d'accélérateur** couvre la carte, ce qui est la bonne frontière
  pour la carte et aucune frontière du tout pour la machine où elle est posée.
- **Aucun d'eux** n'est un ampèremètre sur le rail d'alimentation. RAPL est un
  modèle interne à la puce sur toute pièce qui n'est pas un Haswell serveur à
  régulation embarquée, et Apple dit la même chose des siens, en ajoutant qu'ils
  ne servent pas à comparer une machine à une autre. À l'intérieur d'une machine,
  sur une exécution, contre le repos de cette même machine, ils sont exactement
  le bon instrument — et c'est tout ce que ce paquet leur demande.
- **Un compteur qui a franchi son plafond** une fois pendant une longue
  exécution est déplié depuis sa plage publiée, et le chiffre porte la puissance
  au-delà de laquelle ce redressement aurait été faux. Un compteur *remis à zéro*
  plutôt que bouclé est refusé net.

## Du compteur au coût

Une puissance moyenne mesurée est le premier maillon d'une chaîne, et le reste de
la chaîne est [Green Algorithms](https://doi.org/10.1002/advs.202100707),
détaillé dans
[`skills/saggio/references/green-algorithms.md`](skills/saggio/references/green-algorithms.md) :
durée × puissance × surcoût du datacenter donne l'énergie, énergie × intensité du
réseau donne le carbone, et chaque étape nomme les nombres dont elle vient.

La mesure change le *statut* de ce qui suit, pas seulement sa valeur. Mesurez la
durée et l'énergie devient `measured` d'elle-même ; laissez le pays non renseigné
et le carbone reste ouvert, parce que personne ne le sait encore. La
[règle du maillon faible](skills/saggio/references/honesty-taxonomy.md) fait le
reste : une valeur dérivée ne peut jamais prétendre être mieux fondée que le pire
de ses éléments.

C'est aussi la forme que réclame la [spécification Software Carbon
Intensity](https://sci.greensoftware.foundation/) — ISO/IEC 21031:2024, et
[SCI for AI](https://greensoftware.foundation/standards/sci-ai/) au-dessus :
des émissions par unité fonctionnelle de travail plutôt qu'un total, avec la
frontière déclarée. Un modèle saggio est par unité de travail par construction ;
ce qu'il ne porte pas *encore*, c'est le terme incorporé — la fabrication du
matériel, que [Boavizta](https://boavizta.org/en) modélise par le bas et
qu'[EcoLogits](https://ecologits.ai/) utilise pour l'inférence. Cette absence est
un chiffre ouvert dans ce paquet, pas un zéro.

## De cette machine à une autre

Une mesure porte sur la machine où elle a été prise. Deux projections en font
autre chose, et toutes deux disent ce qu'elles ont supposé :

- **Vers une exécution complète**, depuis une tranche : division par la fraction
  que couvrait la tranche, lue dans votre propre configuration plutôt que
  devinée. Défendable tant que le travail est uniforme, et l'hypothèse est écrite
  dans le modèle.
- **Vers un autre accélérateur** : pas un échange de wattages. Une puce plus
  rapide finit plus tôt, donc elle tire plus de puissance moins longtemps. La
  projection met la durée à l'échelle du rapport des débits crête *à la précision
  dans laquelle le travail s'exécute*, et rapporte un **encadrement** plutôt
  qu'un nombre, parce que le débit arithmétique et la bande passante mémoire
  donnent des rapports différents — 3,2 et 2,2 entre un A100 et un H100 — et
  qu'une vraie exécution tombe entre les deux. Elle refuse net quand le catalogue
  n'a pas de débit pour cette précision.

Le débit crête est une donnée de fiche technique, pas un benchmark. Une vraie
exécution en atteint une fraction, et la fraction diffère selon la puce ; une
charge limitée par le stockage, par le chargeur de données ou par le processeur
hôte ne gagnera ni à l'un ni à l'autre rapport. L'encadrement le dit, et le
rapport aussi. Voir [EXEMPLES.md](EXEMPLES.md#projeter-sur-un-autre-matériel).

## Vérifier par vous-même

Une mesure que personne ne peut vérifier est difficile à défendre. Donc :

```bash
saggio power --json
```

affiche chaque interface, chaque état, et les chemins exacts qui seraient lus,
pour qu'un chiffre puisse être refait à la main — `cat` le compteur, attendre,
`cat` à nouveau, diviser. Sous macOS,
`sudo powermetrics --samplers cpu_power -n 1` est la comparaison qu'Apple
fournit ; ce paquet ne la lancera pas pour vous, et les chiffres doivent
s'accorder.

Si les compteurs d'une machine ne sont pas reconnus — une nouvelle puce Apple qui
renomme un canal, un pilote qui publie une unité inconnue — elle ne mesure rien et
le dit. Envoyer les noms de canaux suffit à ajouter la pièce ; voir
[CONTRIBUER.md](CONTRIBUER.md).

## Sources

**Interfaces noyau et pilotes**

- [Power Capping Framework](https://docs.kernel.org/power/powercap/powercap.html) — l'ABI powercap de Linux, les zones et `energy_uj`.
- [Reading RAPL energy measurements from Linux](https://web.eece.maine.edu/~vweaver/projects/rapl/) — la référence de Vince Weaver sur les domaines, les plages, et ce que RAPL mesure vraiment.
- [GPU Power/Thermal Controls and Monitoring](https://docs.kernel.org/gpu/amdgpu/thermal.html) — les attributs hwmon d'`amdgpu`.
- [`sysfs-driver-intel-xe-hwmon`](https://github.com/torvalds/linux/blob/master/Documentation/ABI/testing/sysfs-driver-intel-xe-hwmon) — l'`energy1_input` d'Intel, en microjoules.
- [Interface sysfs hwmon](https://www.kernel.org/doc/html/latest/hwmon/sysfs-interface.html) — unités et nommage pour les deux précédents.
- [NVIDIA Management Library](https://developer.nvidia.com/management-library-nvml) et [`nvidia-smi`](https://docs.nvidia.com/deploy/nvidia-smi/index.html).
- [Energy Meter Interface](https://learn.microsoft.com/en-us/windows-hardware/drivers/powermeter/energy-meter-interface) — ce que Windows offre, et à qui.
- [Redfish](https://www.dmtf.org/standards/redfish) — la façon normalisée dont un serveur rapporte sa propre consommation de nœud.

**Pourquoi le compteur Linux est fermé**

- [PLATYPUS](https://platypusattack.com/) — l'attaque qui l'a fermé.
- [CVE-2020-8694](https://nvd.nist.gov/vuln/detail/CVE-2020-8694) — l'entrée, et la réponse du noyau.

**Transformer l'énergie en coût**

- Lannelongue, Grealey & Inouye, *Green Algorithms: Quantifying the Carbon Footprint of Computation*, [doi:10.1002/advs.202100707](https://doi.org/10.1002/advs.202100707) — l'arithmétique qu'utilise ce paquet, extraite dans [`green-algorithms.md`](skills/saggio/references/green-algorithms.md).
- [Software Carbon Intensity](https://sci.greensoftware.foundation/) (ISO/IEC 21031:2024) et [SCI for AI](https://greensoftware.foundation/standards/sci-ai/) — les émissions par unité fonctionnelle, et ce qu'une déclaration doit dire.
- [Boavizta](https://boavizta.org/en) et [EcoLogits](https://ecologits.ai/) — le versant incorporé, que ce paquet laisse ouvert plutôt qu'à zéro.
- [Kepler](https://sustainable-computing.io/) — attribuer l'énergie d'un nœud à ce qui y a tourné, le problème qui commence après cette page.

---

[🇬🇧 MEASURING.md](MEASURING.md) · [LISEZMOI.md](LISEZMOI.md) · [EXEMPLES.md](EXEMPLES.md) · [PAYSAGE.md](PAYSAGE.md)
