# Tous les sigles de ce dépôt, écrits en entier

🇫🇷 Français · [🇬🇧 GLOSSARY.md](GLOSSARY.md)

La règle que cette page sert : **nulle part un sigle qui ne soit explicité et
expliqué avant d'être employé.** Chaque page explicite ceux sur lesquels elle
s'appuie, dès leur première apparition, parce qu'un lecteur qui arrive sur une
page n'a pas lu les autres. Celle-ci rassemble tout le vocabulaire, que lit un
test de contrat : un sigle qu'une page emploie sans l'expliciter fait échouer la
construction ; un sigle défini ici que nulle page n'emploie en est retiré.

Certains sont français, d'autres anglais, quelques-uns ni l'un ni l'autre —
`ISO` ne sont pas les initiales de l'Organisation internationale de
normalisation, ce qui est signalé plus bas où le sigle paraît.

## Déclaration et comptabilité

| Sigle | En entier | Ce que c'est |
|---|---|---|
| **GHG** | Greenhouse Gas | le GHG Protocol, la norme de comptabilité d'entreprise qui répartit les émissions en scopes 1, 2 et 3 |
| **GES** | gaz à effet de serre | le terme français pour *greenhouse gas* |
| **CSRD** | Corporate Sustainability Reporting Directive | la directive européenne qui oblige les grandes entreprises à publier des informations de durabilité |
| **ESRS** | European Sustainability Reporting Standards | les normes qui disent ce que doit contenir un rapport CSRD ; E1 est celle du climat |
| **EFRAG** | European Financial Reporting Advisory Group | l'organisme qui rédige les ESRS |
| **RSE** | responsabilité sociétale des entreprises | ce qu'on appelle en anglais *corporate social responsibility* |
| **SCI** | Software Carbon Intensity | la spécification de la Green Software Foundation pour énoncer le carbone d'un logiciel par unité de travail |
| **PUE** | power usage effectiveness | l'énergie totale d'un centre de données divisée par celle que tirent ses ordinateurs : 1,0 serait un bâtiment qui ne coûte rien à refroidir |
| **WUE** | water usage effectiveness | efficacité d'usage de l'eau : litres d'eau par kilowattheure d'énergie informatique, comptés sur site — l'eau ayant servi à produire cette électricité en est exclue. [EAU.md](EAU.md) dit ce que le chiffre affirme et ce qu'il n'affirme pas |
| **prélèvement** | — | l'eau sortie d'une rivière, d'une nappe ou d'un réseau. À ne pas confondre avec la consommation |
| **consommation** | — | la part prélevée qui ne retourne pas au milieu dont elle venait — évaporée, pour l'essentiel. Déplacée plutôt que détruite, d'où l'importance du lieu et de la saison plus que du litre |
| **déconcentration** | — | la fraction de boucle purgée parce que les sels laissés par l'évaporation s'y sont concentrés. La petite part réellement dégradée |
| **PCF** | empreinte carbone produit | le chiffre publié par un fabricant pour le carbone de la fabrication d'une unité |
| **ACV** | analyse du cycle de vie | la comptabilisation de l'impact d'un produit, de la matière première à la fin de vie |
| **AIB** | Association of Issuing Bodies | l'organisme européen qui publie le mix résiduel d'électricité |
| **PPA** | power purchase agreement | un contrat d'achat d'électricité auprès d'un producteur nommé, l'un des instruments sur lesquels repose un chiffre market-based |
| **ADEME** | Agence de la transition écologique | l'agence française de l'environnement, qui publie des facteurs d'émission |
| **AFNOR** | Association française de normalisation | l'organisme français de normalisation |
| **BCE** | Banque centrale européenne | dont ce paquet lit les taux publiés pour une conversion de devise |

## Organismes de normalisation et citations juridiques

| Sigle | En entier | Ce que c'est |
|---|---|---|
| **ISO** | Organisation internationale de normalisation | dont le sigle n'est pas celui de son nom : il vient du grec *isos*, égal. ISO 14067 est la norme d'empreinte carbone, ISO 8601 le format de date, ISO 4217 les codes de devise, ISO 3166-1 les codes de pays |
| **IEC** | Commission électrotechnique internationale | qui copublie plusieurs de ces normes |
| **UE** | Union européenne | — |
| **IA** | intelligence artificielle | — |
| **GPAI** | intelligence artificielle à usage général | le terme du règlement européen sur l'IA pour un modèle qui n'est pas bâti pour une seule tâche ; l'annexe XI en est l'exigence de documentation technique |
| **CELEX** | — | le système d'identifiants de l'Union européenne pour ses textes juridiques |

## Les machines et leurs compteurs

| Sigle | En entier | Ce que c'est |
|---|---|---|
| **CPU** | central processing unit | le processeur |
| **GPU** | graphics processing unit | une carte graphique ou un accélérateur |
| **TPU** | — | le Tensor Processing Unit de Google, un nom plutôt qu'une catégorie |
| **RAPL** | Running Average Power Limit | le compteur d'énergie intégré d'Intel et d'AMD, d'où vient un chiffre de puissance sous Linux |
| **NVML** | NVIDIA Management Library | l'interface qui rapporte la puissance d'un accélérateur NVIDIA |
| **IPMI** | Intelligent Platform Management Interface | le canal de gestion hors bande d'un serveur, qui peut rapporter la puissance du châssis entier |
| **DCMI** | Data Center Manageability Interface | une extension d'IPMI qui normalise cette lecture de puissance |
| **MSR** | model-specific register | un registre de processeur lu directement, et non par le noyau |
| **ABI** | application binary interface | le contrat entre un programme et le noyau ou une bibliothèque qu'il appelle |
| **ISA** | instruction set architecture | le jeu d'instructions qu'un processeur implémente |
| **DRAM** | dynamic random-access memory | la mémoire principale de la machine |
| **HBM** | mémoire à haute bande passante | la mémoire empilée à côté du die d'un accélérateur |
| **FLOP** | floating-point operation | une opération arithmétique sur un nombre décimal ; le TFLOP/s en compte mille milliards par seconde |
| **ARM** | — | l'architecture de processeur, aujourd'hui un nom d'entreprise plutôt qu'un sigle |
| **POSIX** | Portable Operating System Interface | la norme qui fait qu'une commande se comporte pareil sous Linux et macOS |
| **CVE** | Common Vulnerabilities and Exposures | le catalogue public des failles de sécurité, chacune avec un identifiant |

## Logiciel et formats

| Sigle | En entier | Ce que c'est |
|---|---|---|
| **API** | interface de programmation applicative | la surface qu'un programme offre à un autre |
| **CLI** | interface en ligne de commande | — |
| **GUI** | interface graphique | — |
| **HTTP** | HyperText Transfer Protocol | le protocole dont est faite une requête web |
| **HTML** | HyperText Markup Language | le langage dans lequel une page web est écrite |
| **URL** | Uniform Resource Locator | une adresse web |
| **YAML** | YAML Ain't Markup Language | le format de fichier dans lequel sont écrits les modèles et catalogues de ce paquet |
| **JSON** | JavaScript Object Notation | un format de données lisible par une machine |
| **CSV** | comma-separated values | un tableau en texte brut |
| **SVG** | Scalable Vector Graphics | une image décrite en formes plutôt qu'en pixels |
| **PDF** | Portable Document Format | — |
| **AST** | abstract syntax tree | un programme analysé sous forme d'arbre, ce qui permet de lire du source sans l'exécuter |
| **OCR** | reconnaissance optique de caractères | lire du texte sur une image |
| **CI** | intégration continue | la construction automatique qui tourne à chaque modification |
| **BSD** | Berkeley Software Distribution | la famille de licences permissives sous laquelle ce paquet est publié |
| **CC** | Creative Commons | la famille de licences ; CC BY en est la licence avec attribution |
| **RFC** | Request for Comments | la série de documents qui définit les normes de l'internet |
| **WCAG** | Web Content Accessibility Guidelines | la norme d'accessibilité ; AA en est le niveau de conformité intermédiaire |
| **CLDR** | Common Locale Data Repository | la base du consortium Unicode qui recense comment chaque langue écrit nombres, dates et noms |
| **IANA** | Internet Assigned Numbers Authority | qui publie la base des fuseaux horaires |
| **UTC** | temps universel coordonné | la référence de temps de chaque horodatage ici |
| **JIT** | just-in-time | compiler un programme pendant qu'il tourne plutôt qu'avant |
| **JVM** | Java Virtual Machine | — |
| **IR** | intermediate representation | la forme interne d'un programme dans un compilateur, entre source et code machine |

## Apprentissage, mesure et nuage

| Sigle | En entier | Ce que c'est |
|---|---|---|
| **ML** | machine learning | l'apprentissage automatique |
| **SSL** | self-supervised learning | l'apprentissage auto-supervisé, sans étiquettes — et non le protocole réseau des mêmes initiales |
| **KV** | key-value | le cache qu'un modèle de langue garde de ses propres clés et valeurs d'attention |
| **MAE** | mean absolute error | la taille moyenne de l'erreur d'une prédiction, dans l'unité prédite |
| **MAPE** | mean absolute percentage error | la même chose, en part de la valeur vraie |
| **WCET** | worst-case execution time | le temps le plus long que peut prendre un morceau de code, prouvé plutôt que mesuré |
| **WCEC** | worst-case energy consumption | la même question posée à l'énergie |
| **RMS** | read memory size | la part de son entrée qu'une routine lit réellement, taille contre laquelle une borne de coût devrait être énoncée |
| **IF** | Impact Framework | l'outil de la Green Software Foundation pour composer une chaîne de calcul d'impact environnemental |
| **AWS** | Amazon Web Services | — |
| **GCP** | Google Cloud Platform | — |
| **OCI** | Oracle Cloud Infrastructure | — |
| **ACM** | Association for Computing Machinery | la société savante qui publie beaucoup des articles cités ici |

## Ce qui n'est pas un sigle ici

Chacun avec sa raison, pour qu'on ne demande pas à une page d'expliquer un nom de fichier ou un numéro de modèle.

| Nature | Exemples | Pourquoi |
|---|---|---|
| Les noms de pages de ce dépôt | `README`, `LISEZMOI`, `STANDARDS`, `NORMES`, `ANALYSIS`, `ANALYSE`, `ANNEX`, `ANNEXE`, `JOURNAL`, `CHANGELOG`, `TRIGGERS`, `DECLENCHEURS`, `GALLERY`, `GALERIE`, `MEASURING`, `MESURER`, `USING`, `UTILISER`, `EXAMPLES`, `EXEMPLES`, `LANDSCAPE`, `PAYSAGE`, `INVENTORY`, `INVENTAIRE`, `BOUNDARIES`, `FRONTIERES`, `CONTRIBUTING`, `CONTRIBUER`, `CODING`, `SKILL` | Ce sont des noms de fichiers, en capitales parce que le fichier s'appelle ainsi. |
| Noms de produits et de modèles | `H100`, `A100`, `B200`, `M1`, `M2`, `M4`, `HGX`, `SXM`, `SXM4`, `SXM5`, `GTX`, `EPYC`, `NVIDIA`, `CUDA`, `LLVM`, `XMOS`, `PCRE`, `PHP`, `SAGGIO` | Un nom, et non un sigle qu'un lecteur doit décoder. `SXM` et `HGX` sont des formats de carte NVIDIA, que le fabricant lui-même n'explicite pas. |
| Outils et lieux de publication, dans une citation | `PLATYPUS`, `OSACA`, `OTAWA`, `IACA`, `COSTA`, `SPEED`, `C4B`, `SHAP`, `FSE`, `ICS`, `OSDI`, `PLDI`, `TECS`, `ISSCC`, `SCOPES`, `SCP` | Chacun est accolé à un lien vers l'article ou l'outil, où va le lecteur. L'abréviation d'un lieu de publication dans une citation est un usage savant, non du jargon. |
| Entreprises nommées dans une liste citée | `CAST`, `UBS`, `NTT`, `DATA`, `AFAS` | Des noms d'entreprises. « NTT DATA » est le nom de l'entreprise. |
| Unités, codes et identifiants | `GB`, `KB`, `MB`, `CO2`, `CO`, `EUR`, `USD`, `FP16`, `BF16`, `TFLOP`, `XI`, `AA`, `E1`, `F401`, `ID`, `ENERGY`, `PATH`, `ALLOW`, `CLONE`, `TODO`, et tout code de pays à deux lettres | Une unité, un symbole, un chiffre romain, un niveau de conformité, la désignation propre d'une norme, une règle de lint, un morceau de nom de produit, un morceau de nom de variable d'environnement, ou l'un des quatre statuts d'honnêteté de ce paquet — que `NORMES.md` définit. |
