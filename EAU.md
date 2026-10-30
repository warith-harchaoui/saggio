# L'eau

🇫🇷 Français · [🇬🇧 WATER.md](WATER.md)

Un paquet qui compte ce que coûte du code rend cinq chiffres, et l'un des cinq
étonne : des litres. Cette page dit pourquoi. Elle concède aussi les deux
objections qu'un lecteur attentif soulève tout de suite — l'eau de
refroidissement n'est pas détruite, et elle ne revient pas forcément
imbuvable. Les deux sont justes. La comptabilité garde quand même un sens, et
la vraie raison est plus intéressante que le slogan.

## Pourquoi un paquet qui mesure du calcul parle-t-il d'eau

Un centre de données est un bâtiment dont le métier est de transformer de
l'électricité en chaleur, puis de se débarrasser de la chaleur. Pour sortir
cette chaleur d'une salle, il y a deux voies : dépenser plus d'électricité dans
des groupes froids, ou évaporer de l'eau. L'évaporation revient bien moins cher,
parce que vaporiser un kilogramme d'eau emporte environ six cents fois plus de
chaleur que réchauffer ce même kilogramme d'un degré.

L'eau n'est donc pas un effet de bord du calcul. C'est l'une des deux factures
qu'une salle peut payer pour évacuer la chaleur que votre travail a produite, et
**une salle au chiffre d'eau très bas est peut-être simplement une salle qui
paie l'autre facture.** Les salles en refroidissement sec existent : presque pas
d'eau, davantage d'électricité. Cet arbitrage est la chose la plus importante à
comprendre ici, et c'est pourquoi ce paquet ne montre jamais un chiffre d'eau
sans l'énergie et l'efficacité d'usage de l'énergie à côté. Un chiffre d'eau lu
seul récompense exactement la mauvaise conception.

## Ce que le chiffre mesure

Le **WUE** (*water usage effectiveness*, efficacité d'usage de l'eau) est le
nombre de litres par kilowattheure consommé par les machines elles-mêmes. C'est un rapport défini sur
site : il compte l'eau que le bâtiment a déplacée et **exclut l'eau qui a servi
à produire l'électricité que le bâtiment a achetée.** Cette exclusion n'est pas
mince : les centrales thermiques évaporent de l'eau dans leurs propres tours, et
les retenues des barrages s'évaporent par leur surface. Le chiffre qui
l'inclurait est une autre grandeur, parfois notée WUEsource, et ce paquet ne la
rend pas.

Les chiffres d'ici sont par unité de travail : les litres affichés valent
`énergie machine × WUE`, ramenés à une invocation, une requête, un
entraînement — ce que vous avez nommé comme unité.

## « Mais l'eau n'est pas perdue »

C'est juste, et le mot employé par la discipline est précisément celui qui
sème la confusion.

La comptabilité de l'eau distingue le **prélèvement** de la **consommation**. Le
prélèvement, c'est ce qu'on sort d'une rivière, d'une nappe ou d'un réseau. La
consommation, c'est la part qui ne retourne pas au milieu dont elle venait. Le
refroidissement par évaporation consomme l'essentiel de ce qu'il prélève, et
*consommer ne veut pas dire détruire.* L'eau part en vapeur, rejoint
l'atmosphère et retombe en pluie ailleurs. Rien n'est anéanti ; le cycle de
l'eau est fermé, il l'a toujours été.

Ce que le chiffre mesure n'est donc pas une perte mais un **déplacement, dans
l'espace et dans le temps.** Le litre a quitté ce bassin-ci, cet été-là, pour
tous ceux qui y puisaient aussi : la ferme en aval, le réservoir de la commune,
le débit minimum de la rivière elle-même. Il revient en pluie au-dessus d'un
océan neuf cents kilomètres plus loin et quatre jours plus tard, ce qui
n'arrange personne dans la file d'attente d'ici.

C'est aussi pourquoi un chiffre d'eau sans lieu attaché ne veut presque rien
dire. Un litre en Irlande et un litre en Arizona sont le même litre et pas du
tout le même événement. **Ce paquet rend des litres et le pays, et se refuse
délibérément à les pondérer par la rareté locale.** Les pondérations de rareté
existent et sont sérieuses, mais en choisir une, c'est choisir un jugement de
valeur, et un chiffre pondéré ne se dépondère pas chez celui qui le lira
ensuite. Le litre brut et le lieu se recombinent toujours après coup.
L'inverse, non.

## « Et elle ne revient pas forcément non potable »

Juste aussi, et la chimie va dans le sens contraire de l'intuition courante.

L'évaporation est une distillation. Ce qui sort d'une tour de refroidissement
est de la vapeur d'eau pure ; les sels et les minéraux dissous restent derrière.
La part évaporée n'est donc pas dégradée du tout — c'est l'eau la plus propre du
bâtiment. Elle est simplement ailleurs.

Les sels restés derrière se concentrent dans la boucle à chaque passage. Laissés
tels quels, ils entartreraient et encrasseraient les échangeurs ; on purge donc
une fraction de la boucle pour la remplacer — la **déconcentration** — et cette
fraction-là, *elle*, est dégradée : plus salée qu'à l'entrée, et porteuse des
biocides et antitartres qui ont empêché la boucle de se peupler. C'est un volume
bien plus petit que la part évaporée, et c'est la part qui pose réellement un
problème de rejet.

Le résumé honnête tient donc en trois faits, qu'aucun chiffre unique ne porte :

| La part | Ce qu'elle devient | Dégradée ? |
|---|---|---|
| Évaporée — l'essentiel | Quitte le bassin en vapeur pure | Non. Déplacée, pas abîmée. |
| Purge — le reste | Rejetée, concentrée, traitée | Oui, et c'est la petite part. |

Et un troisième fait, qui n'est à aucun bout de ce tableau : **ce qu'on a
prélevé au départ.** C'est celui qui compte le plus et dont on parle le moins.

Une grande partie de l'eau de refroidissement est de l'**eau potable** — traitée
aux normes de l'eau de boisson sur fonds publics, puis évaporée pour refroidir
des serveurs. L'autre voie est l'eau recyclée ou les eaux grises, et les
exploitants qui la prennent le disent en général. La question d'équité sur l'eau
des centres de données se joue donc à la prise d'eau et non au rejet : pas
« l'ont-ils abîmée » mais « ont-ils bu le réseau de la ville pour le faire ».

Lisez le WUE comme **la quantité d'eau que cette salle a déplacée**, jamais
comme *la quantité d'eau que cette salle a gâchée*. Il ne connaît pas la
différence, et aucun chiffre unique ne la connaît.

## Ce que ce paquet fait, et ce qu'il refuse

Il rend des litres par unité de travail, avec le pays attaché, dérivés d'une
efficacité d'usage de l'eau publiée et de l'énergie mesurée.

**Il n'invente jamais une efficacité d'usage de l'eau.** La plupart des
exploitants n'en publient aucune, et le champ reste ouvert — `TODO` plutôt que
zéro, parce que zéro est une affirmation et une absence n'en est pas une. Une
salle réellement en refroidissement sec a un WUE de zéro et doit le dire
exprès ; une salle dont l'exploitant n'a rien publié est inconnue, et les deux
ne doivent pas se ressembler dans un rapport.

Là où une issue existe, le refus la nomme. Une salle auto-exploitée dans un État
membre de l'Union européenne relève de l'obligation de déclaration de la
directive efficacité énergétique refondue, et la Commission publie une moyenne
européenne à partir de ce que les exploitants déclarent — portée ici par le
fournisseur `on-prem-eu`. Le `TODO` d'une telle salle pointe vers cette ligne et
ne la prend toujours pas, parce qu'une moyenne européenne sur les salles qui ont
déclaré peut n'avoir aucun rapport avec la vôtre, et que la substituer sans
qu'on le demande serait ce paquet choisissant une hypothèse à votre place. La
seule chose qu'il refuse partout ailleurs, il la refuse ici aussi.

**Ce qu'il ne modélise pas**, dit pour que personne ne suppose le contraire :
l'eau de production de l'électricité, la pondération par la rareté locale, la
charge thermique rendue à une rivière par un refroidissement en circuit ouvert,
et l'eau contenue dans la fabrication du matériel. Quatre absences, nommées
plutôt que silencieusement mises hors champ.

## D'où viennent les chiffres

| Chiffre | Source |
|---|---|
| La définition de l'efficacité d'usage de l'eau | The Green Grid, qui a défini le rapport |
| `on-prem-eu`, 0,58 L/kWh | [COM(2026) 500 final](https://data.consilium.europa.eu/doc/document/ST-13443-2026-INIT/en/pdf), première évaluation de la Commission au titre de l'article 12 de la directive efficacité énergétique refondue — moyenne européenne sur les 458 centres ayant déclaré une eau supérieure à zéro, ce qui exclut les salles en refroidissement sec et surestime donc la salle courante |
| Les chiffres des fournisseurs de nuage | La page de durabilité de chaque exploitant, citée ligne par ligne dans `saggio/data/providers.yaml` |

Chacun est au catalogue avec son adresse et la date de lecture, et chacun
périme. `saggio catalog freshness` dit lesquels.

Voir aussi [NORMES.md](NORMES.md) pour l'obligation de déclaration derrière la
ligne européenne, et [FRONTIERES.md](FRONTIERES.md) pour ce que ce paquet se
refuse à modéliser.
