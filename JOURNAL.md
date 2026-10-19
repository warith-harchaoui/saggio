# Journal des versions

🇫🇷 Français · [🇬🇧 CHANGELOG.md](CHANGELOG.md)

Ce projet suit le [versionnage sémantique](https://semver.org/). Le schéma du
modèle de coût est versionné à part, dans son propre champ `schema_version` : à
l'intérieur d'une ligne majeure il ne fait que grandir, si bien qu'un modèle
écrit aujourd'hui continue de valider contre toutes les versions suivantes de
cette ligne.

## Non publié

### Mesuré ce que sprezzature apporterait au rapport web, avant de refondre quoi que ce soit

- **Le gate structurel d'accessibilité ne trouve rien.**
  `sprezzature-accessibility-lint` applique vingt règles statiques au HTML
  produit : le rapport obtient **0 constat**, et le tableau de bord aussi. Quoi
  qu'une refonte apporterait, ce n'est pas cela.
- **L'audit de contraste a trouvé quatre échecs réels, et ce sont les quatre
  pires que cette palette pouvait avoir.** `--ink-faint` était à 3,55:1 contre
  la page, sous les 4,5:1 qu'exige WCAG AA à cette taille — et il colore `th`,
  `td.unknown`, `.muted` et les étiquettes du panneau what-if. Autrement dit :
  **la couleur qui signale qu'une valeur est incertaine était la plus difficile
  à lire de la page.** Le badge `estimated` était à 4,21:1 sur son propre fond,
  même faute au même endroit.
- Corrigé en déplaçant quatre valeurs, teinte et saturation conservées :
  `#86867c` → `#707068` (clair), `#82806f` → `#8c8a78` (sombre), `#9a6a12` →
  `#936511`. Résolu contre la surface **sunken** et non contre la page, parce
  que c'est le plus sombre des trois fonds que cette couleur rencontre — un
  premier calcul calé sur la page passait là et échouait encore à 4,28:1 sur
  une carte sunken.
- Un test fixe le plancher à 4,5:1 et lit la feuille de style livrée plutôt
  qu'une copie des valeurs ; remettre `#86867c` le fait échouer.
- **Et un constat sur le linter plutôt que sur ce paquet.** Le site publié
  obtient 260 constats `aria-hidden-interactive`, tous le motif d'ancre de titre
  `<a href="#id" aria-hidden="true" tabindex="-1">#</a>`. Ce motif est correct :
  c'est `tabindex="-1"` qui rend l'ancre non focalisable, ce que la règle existe
  précisément pour exiger. Sondé avec un fichier de deux lignes — la règle tire
  avec et sans le `tabindex`, elle ne le regarde donc pas. Les 260 sont un seul
  faux positif.

### Un curseur machine sur le rapport web, et des durées qu'un lecteur peut tenir

- Le rapport HTML recalculait déjà un modèle ailleurs : deux curseurs, le pays
  et le fournisseur. Il en a un troisième, **la machine** — et celui-là est
  d'une autre nature. Changer de pays remet une valeur à l'échelle ; changer de
  machine la **recalcule**, parce que l'énergie est le temps multiplié par la
  puissance et que seule la puissance a bougé.
- **Et cela change ce que la valeur est.** La puissance de ce modèle peut être
  une lecture de compteur ; chaque ligne de catalogue est une plaque
  signalétique. Dès qu'une autre machine est choisie, la note sous le panneau le
  dit : *« at its datasheet rating of 350 W. That rating is estimated, not
  measured: these figures are no longer this machine's. »* Un panneau qui
  laisserait une plaque signalétique porter le statut d'une mesure serait le
  pire chiffre de la page.
- Le défaut est la constante du rapport statique, et c'est la seule option qui
  puisse être une mesure. Vingt-cinq accélérateurs et six processeurs sont
  proposés à côté, chacun avec la valeur à laquelle il sera calculé. Une ligne
  processeur énonce des watts par cœur et un nombre de cœurs : les deux facteurs
  sont multipliés ici et voyagent avec la valeur.
- **`1,087e+04 s`, ce sont trois heures et une minute**, et un paquet dont
  l'argument est qu'une valeur doit être lisible n'avait rien à faire d'imprimer
  la première écriture. Les durées se lisent désormais comme on les dit —
  `3 h 1 min (10870.4 s)`, `27.2 ms`, `250 ns` — avec les secondes exactes
  conservées à côté des longues, parce que qui vérifie le rapport contre le
  modèle a besoin du nombre que le modèle porte. Les deux rapports les écrivent
  pareil, et un test l'exige.

### Lire l'empreinte produit d'un constructeur, et refuser de deviner

- La version précédente soutenait qu'il ne devait exister **aucun** verbe lisant
  un PCF, parce que la valeur énoncée vaut pour une carte de base alors que
  l'unité de ce catalogue est un accélérateur, et que le diviseur est sur une
  autre page. C'était une raison de le construire soigneusement, pas de le
  refuser — et le dessin qui le rend sûr était déjà écrit dans le refus
  lui-même.
- `saggio catalog read-pcf <url>` va chercher le document, en extrait le texte
  et **montre son raisonnement** : la phrase dont vient la valeur, la ligne dont
  vient le diviseur, et l'arithmétique entre les deux. Puis il imprime un
  brouillon de ligne et s'arrête.
- **Il retombe sur les valeurs commitées sans qu'on les lui souffle.** Lancé sur
  les deux documents que ce paquet cite, il lit 1 312 et 2 274 kgCO2e pour les
  cartes HGX H100 et HGX B200, trouve `Form Factor 8x …` sur une autre page, et
  produit 164,0 et 284,25 — les valeurs qu'un humain avait mises au catalogue un
  mois plus tôt, à la main.
- **Trois refus le rendent sûr.** Une valeur doit venir d'une *phrase* :
  l'analyseur fait de l'OCR, donc un diagramme en barres devient du texte comme
  le reste, et une valeur relevée sur un graphique est la seule chose que ce
  paquet refuse de porter. Une valeur de carte sans facteur de forme est
  **refusée**, pas divisée par une supposition. Et rien n'est écrit — il n'y a
  pas de `--into`, parce qu'une ligne de catalogue est une affirmation que
  quelqu'un fait et que celui qui la fait est celui à qui l'on peut demander
  pourquoi. Le brouillon ne porte d'ailleurs aucune `key` : un document ne sait
  pas comment ce catalogue nomme les choses.
- L'`embodied_scope` du brouillon est écrit pour lui, et satisfait le contrat
  ajouté à la version précédente : il commence par nommer une unité et énonce la
  division.
- Cinq surfaces, comme la règle l'exige : la bibliothèque, la ligne de commande,
  `POST /catalog/read-pcf`, l'outil agent qui en dérive, et les deux livres de
  recettes. La route est **fermée sauf si `SAGGIO_API_ALLOW_FETCH` est
  positionné** — aller chercher une adresse choisie par le client est le risque
  que le clonage est, barré à part parce qu'un exploitant qui laisse le serveur
  lire un PDF n'a pas pour autant accepté qu'il clone un dépôt.
- L'analyseur est un extra optionnel, `pip install 'saggio[pcf]'`. Les trois
  dépendances d'exécution restent trois, et le verbe dit quoi installer au lieu
  d'échouer sur un import trois cadres plus bas.

### Pourquoi il n'existe aucun verbe qui lit une empreinte produit

- La liste de travail portait depuis octobre l'idée d'un verbe qui lirait le PDF
  de PCF d'un constructeur et **proposerait** une ligne de catalogue à valider
  par un humain. Les deux documents que ce paquet cite déjà ont été ouverts et
  dépouillés à la main pour savoir si c'est une bonne idée. Ce n'en est pas une,
  et la raison est arithmétique, pas affaire de goût.
- Les deux fiches énoncent leur valeur dans une prose qu'un analyseur trouverait
  du premier coup : *« the carbon footprint from cradle-to-gate for one HGX H100
  GPU baseboard is 1,312 kg CO₂e »*, et 2 274 pour la HGX B200. **L'unité de ce
  catalogue est un accélérateur.** Le diviseur est sur une autre page, dans un
  tableau de spécifications disant *« Form Factor: 8x NVIDIA H100 SXM »*, et
  savoir qu'il faut diviser vient du schéma, pas du document.
- Une ligne portant `embodied_kgco2e: 1312` sous la clé `H100` serait **fausse
  d'un facteur huit et paraîtrait impeccable** — vraie URL constructeur, vraie
  date, nombre réellement imprimé dans le document. C'est la pire sortie que ce
  paquet puisse produire. Lire le nombre est la moitié facile ; savoir ce qu'est
  une unité de destination, et écrire qu'on a divisé, est la moitié qui doit
  être faite par quelqu'un à qui l'on peut demander pourquoi.
- Les deux valeurs commitées ont été confrontées à leurs documents pendant que
  la question se tranchait : 164,0 est 1312/8 et 284,25 est 2274/8, et les deux
  lignes le disaient déjà dans leur propre `embodied_scope`.
- **Cette discipline était une convention, elle est désormais une règle.** Toute
  ligne énonçant une empreinte doit porter une portée, une source et une date,
  et la portée doit *commencer par nommer une unité* — `One SXM 40GB card…`,
  `One of the eight GPUs on an HGX H100 baseboard…`. Huit lignes portent une
  empreinte aujourd'hui et les huit passent ; retirer une portée fait échouer la
  suite.
- `CONTRIBUTING.md` / `CONTRIBUER.md` disent tout cela là où quelqu'un qui
  s'apprête à ajouter une ligne le lira.

### Un règlement qui publie des chiffres en retour, et le TODO eau qu'il ferme

- Les notes de travail annonçaient que le dispositif européen de déclaration
  transformerait les `TODO` PUE et WUE en lignes de catalogue avec provenance.
  **La moitié était fausse**, et le rapport le dit lui-même : *« All data have
  been anonymised to avoid disclosing personal, company, or location-specific
  details pursuant to Article 5(5) of Delegated Regulation (EU) 2024/1364. »*
  Il n'y a aucune valeur par installation à mettre où que ce soit, et il n'y en
  aura pas.
- Ce qui **est** publié vaut à l'échelle de l'Union, et mérite d'être pris.
  [COM(2026) 500 final](https://data.consilium.europa.eu/doc/document/ST-13443-2026-INIT/en/pdf)
  du 21 septembre 2026 donne pour 2024 un **PUE de 1,36**, pondéré par l'énergie
  sur les 681 centres dont la valeur a passé le contrôle qualité, et un **WUE de
  0,58** L/kWh sur les 458 ayant déclaré une consommation d'eau non nulle. Les
  deux forment le fournisseur `on-prem-eu`.
- **Cela ferme un `TODO` que chaque modèle auto-hébergé porte depuis la première
  version.** L'eau restait ouverte parce que *« On-premises publishes no water
  usage effectiveness »*. Pour une salle dans l'Union, cette phrase n'est plus
  vraie, et un audit UE mesuré ferme désormais cinq dimensions sur sept au lieu
  de quatre.
- La ligne porte ce que le rapport dit de **lui-même** : environ 36 % seulement
  des centres concernés ont déclaré, 70,1 % de ce qu'ils ont déclaré a passé le
  contrôle qualité, et la moyenne WUE exclut les salles à refroidissement sec,
  donc la surestime. Une ligne de catalogue se lit à la place du document dont
  elle vient : les limites du document doivent voyager avec elle.
- **Les moyennes nationales sont refusées**, et la raison est la règle du paquet
  lui-même. Elles existent dans le rapport — de 1,15 à 1,66 — mais seulement en
  étiquettes sur un diagramme en barres, et la Commission signale les quatre
  États membres comptant moins de trois installations déclarantes comme
  possiblement non représentatifs. Recopier une valeur depuis un graphique est
  la façon dont un nombre cesse de pouvoir dire d'où il vient.
- La page de la Commission pour ce rapport redirige vers EUR-Lex, qui sert un
  corps vide à tout ce qui n'est pas un navigateur. La citation est la copie du
  Conseil, document identique, qui répond 200 — choisie pour la raison qui avait
  fait déplacer la citation Ember deux versions plus tôt : une source qu'un
  lecteur ne peut pas atteindre n'est pas une source.

### Deux refus tranchés, deux qui n'en étaient pas, et une affirmation fausse

- **La page d'accueil contredisait chaque modèle mesuré, depuis douze
  versions.** `LISEZMOI.md` rangeait la capacité au repos parmi ce que le paquet
  ne compte jamais ; `examples/render.yaml` et `examples/request.yaml` disent
  l'inverse depuis que la liste d'exclusions a cessé d'être une constante —
  *« Idle capacity is inside these figures, not outside them. »* La même phrase
  était fausse dans `README.md`.
- **Aucune sonde ne pouvait le voir.** Ce n'est ni un chiffre, ni un calcul, ni
  un lien : les trois vérifications de prose et le vérificateur de liens
  passaient à côté. Une nouvelle lie les deux : une page ne peut pas ranger
  dans ses exclusions un sujet qu'un modèle commité déclare dedans. Visant
  l'**énumération** et non la page — la première version interdisait le mot
  partout et aurait empêché la page d'expliquer la nuance.
- Les deux pages disent désormais le vrai, plus intéressant que le faux : la
  capacité au repos est exclue quand la puissance est une plaque signalétique et
  **dedans** quand elle a été lue sur les compteurs de la machine. Une liste
  d'exclusions identique dans les deux cas serait fausse dans l'un des deux.
- **Refusé nommément : la surveillance continue.** Chaque valeur ici est par
  unité de travail et un démon n'en a pas ; il devrait répartir un flux entre ce
  qui se trouvait tourner, c'est-à-dire l'attribution mesurée il y a deux
  itérations comme la moins reproductible des trois — 67 % à 190 % sur cinq
  exécutions contre 8 % à 49 % pour le total au compteur. Une valeur dont on ne
  sait pas borner l'écart ne peut pas dire jusqu'où on peut lui faire confiance.
- **Refusé nommément : lire une facture cloud.** Une facture énonce de l'argent
  pour un compte sur un mois, et la répartir entre des unités de travail demande
  une clé que personne ne publie. Ce qui est permis est dit à côté du refus :
  relever la valeur soi-même et l'enregistrer avec `source_kind: stated`, qui a
  une **meilleure** provenance que le tarif `aggregator` du catalogue.
- **Deux entrées de la liste de travail n'étaient pas des refus.** Les
  dimensions supplémentaires sont acceptées — le registre les prend, le modèle
  annoté livre `egress`, et un test de contrat l'exerce. Une sixième surface a
  une procédure documentée dans `USING.md`. Les deux étaient portées comme des
  refus dans des notes privées que personne n'avait confrontées au code.

### Ce que vaut une étendue de cinq exécutions, exactement

- `--repeat 5` enregistre une étendue et rien ne disait ce qu'une étendue
  **est**. Le module disait que ce n'était pas un intervalle de confiance ; la
  porte disait qu'un mouvement était « inside the noise the models measured »,
  ce qui laisse entendre que le bruit a été mesuré. Un lecteur devait deviner,
  et ce qu'une largeur invite à deviner, c'est « borne ».
- Ce n'est pas une borne, et le chiffre est exact. Pour **n'importe quelle**
  distribution continue, la prochaine exécution tombe hors de l'étendue des `n`
  précédentes avec probabilité **2 / (n + 1)** — parmi `n + 1` tirages
  échangeables chacun a la même chance d'être le plus grand, donc le nouveau est
  un maximum inédit avec probabilité `1/(n+1)`, un minimum inédit de même, et il
  ne peut être les deux. Aucune forme supposée, aucune ajustée. Vérifié sur des
  tirages normaux, exponentiels et uniformes, 200 000 essais chacun : 0,3334,
  0,3329, 0,3337 contre 0,3333 prédit à n = 5.
- **Cinq exécutions sont dépassées par un travail inchangé une fois sur
  trois**, et le levier est dans l'arithmétique : pour diviser la surprise par
  deux, doublez à peu près les exécutions.
- Dit là où ça compte, pas seulement sur une page. Les notes d'une quantité se
  terminent par *« A range from 5 runs is not a bound: the next run lands
  outside it about one time in 3… »*. Et `saggio diff`, quand il excuse un
  mouvement tombé dans un intervalle, ajoute désormais *« a 5-run range,
  exceeded by unchanged work one time in 3 »* — une porte qui excuse doit dire à
  quelle fréquence l'excuse est fausse.
- Un intervalle bâti sur deux étendues rapporte le **plus petit** des deux
  comptes d'exécutions : un produit n'est pas mieux fondé que son facteur le
  plus faible.
- Cela tranche aussi la façon dont le résultat de l'itération précédente peut
  être cité. Les trois attributions ont gardé leur **classement** sur trois
  séries indépendantes ; le **facteur** entre elles, non — d'environ quatre à
  environ quinze. Un classement survit à une étendue large ; un rapport de deux
  étendues, non, et les pages citent le classement.

### Quelle attribution ce paquet emploie, décidé sur des mesures et non par goût

- Une puissance mesurée a trois lectures, et le paquet portait les trois sans
  dire laquelle il assumait : le total au compteur, la part du domaine
  processeur, et le total moins le plancher au repos. `MESURER.md` terminait
  cette section par *« laquelle des deux a sa place dans un modèle de coût
  n'est pas tranché ici »* depuis neuf versions.
- **C'est tranché, et ce sont les chiffres qui ont tranché.** Les trois ont été
  mesurées côte à côte sur cinq exécutions d'une même commande, trois fois :

  | | Étendue sur cinq exécutions | Écart |
  |---|---|---|
  | Le total au compteur | 15,25 W à 23,16 W | 49 % |
  | Attribué par le travail processeur | 3,209 W à 3,646 W | **13 %** |
  | Puissance active, total moins plancher | 1,64 W à 9,83 W | **190 %** |

- **La soustraction est refusée nommément.** C'est une petite différence entre
  deux lectures qui bougent chacune : elle hérite des deux et ne garde presque
  rien du signal — cinq à quinze fois moins reproductible que l'une ou l'autre
  de ses entrées sur les trois séries. **L'attribution par domaine s'est
  révélée la valeur la plus stable des trois**, plus stable que le total dont
  elle dérive, parce qu'un compteur de domaine ne bouge pas quand autre chose
  se réveille sur la machine. Ce n'était pas le résultat attendu.
- **Les coûts utilisent toujours le total au compteur**, et la page dit
  pourquoi : c'est le seul qu'un compteur ait produit, et substituer une valeur
  modélisée mettrait une estimation sous un champ qui dit `measured`. Ce qui
  changerait cela est énoncé pour qu'on puisse le contester — la part de
  domaine ne tarife que l'énergie *processeur* et sous-estimerait toute charge
  avec accélérateur.
- L'affirmation est vérifiable depuis le fichier. `measurement.spread`
  enregistre désormais ce que le **plancher** et la **part attribuée** ont fait
  sur les exécutions, à côté du temps et du total qu'il gardait déjà. Sans ces
  deux-là, la comparaison sur laquelle repose la décision n'était pas
  re-dérivable d'un modèle commité — le même défaut que les quatre précédents :
  une valeur que l'exécution produit et que le fichier n'obtient pas.
- `examples/render.yaml` remesuré pour les porter ; les quatre pages qui citent
  ses chiffres ont péri à l'instant même, et le contrat écrit il y a deux
  itérations l'a dit avant tout commit.

### L'ajustement qu'un modèle enregistre peut être vérifié contre les preuves posées à côté

- Un bloc de mise à l'échelle conserve les tailles et les secondes sur
  lesquelles il a été ajusté, *« pour qu'un lecteur refasse le calcul plutôt que
  de croire l'exposant sur parole »*. Le lecteur ne pouvait pas. `y = a · x^b`
  demande les deux nombres, et seul `b` était un champ : le coefficient
  n'apparaissait **que dans la phrase de méthode** — la même forme que le
  diviseur des projections une itération plus tôt, un cran plus bas. Son propre
  docstring dit qu'il sert *« à refaire le calcul, et à peu près à rien
  d'autre »*.
- `measurement.scaling.coefficient` est désormais écrit, et deux contrats s'en
  servent : l'ajustement doit reproduire chaque observation enregistrée à côté
  de lui, et les deux nombres épelés par la phrase de méthode doivent être ceux
  que portent les champs. Les deux sabotages tirent — déplacer le coefficient,
  ou déplacer une observation.
- Rétro-rempli dans `walkthrough/5-run.yaml` en **réajustant les observations du
  fichier lui-même** avec l'estimateur du paquet, pas en recopiant la phrase. Le
  réajustement retombe sur l'exposant enregistré à neuf décimales et sur le R²
  enregistré exactement, ce qui prouve que c'est l'ajustement qui a produit le
  bloc. Il prédit les trois observations à 1,2 %, 2,5 % et 1,2 % près.

### Une règle mesurée puis rejetée : « tout champ doit atteindre le fichier »

- Trois itérations ont trouvé le même défaut — une valeur que l'objet tient et
  que le fichier n'obtient pas (`measure --json`, `marginal_watts`,
  `fraction_completed`) — donc le réflexe était un contrat sur chaque classe
  sérialisable. Il a d'abord été mesuré, comme les deux itérations précédentes
  l'ont enseigné.
- **Par le nom : 47 champs sur 111 (42 %) n'apparaissent jamais comme clé.**
  Presque tous sont des renommages — `Spread.values` s'écrit `runs`,
  `SliceResult.baseline` devient `idle_watts`, `MachineProfile` devient tout le
  bloc `deployment`.
- **Par l'atteignabilité de la valeur : 24 sur 105 (23 %)**, sous le seuil —
  mais chacun a dû être trié à la main, et tous sauf un se sont révélés faux
  positifs ou omissions délibérées. `ServiceHit.pricing_source_url` et les
  champs de source de `RateTable` atteignent bien le fichier, par un autre
  chemin.
- La règle générale n'est donc pas livrée : un contrat qui exige un verdict
  humain à chaque signalement n'est pas un contrat. Ce qui est livré, c'est le
  seul vrai défaut qu'elle a trouvé, et une vérification assez précise pour être
  exacte.

### Le diviseur dont dépend tout coût projeté est désormais une valeur, pas une phrase

- Un modèle portait la taille de la course en `analysis.total_work.stated_as :
  '400000'` — une **chaîne de caractères** — et la fraction par laquelle les
  projections divisent nulle part. Tout coût projeté de ce dépôt reposait sur un
  nombre qui n'apparaissait qu'à l'intérieur d'une phrase de méthode.
- Deux nombres que le code détenait déjà atteignent le fichier :
  `total_work.units` à côté du jeton littéral que la source écrit, et
  `measurement.fraction_completed`, que `SliceResult` a toujours connu et n'a
  jamais consigné. Le même défaut deux fois — une valeur que l'objet tient et
  que le fichier n'obtient pas — et le même que `measure --json` perdant son
  attribution ou `marginal_watts` ne vivant qu'en prose.
- Un contrat exige que le diviseur énoncé par une méthode soit une valeur que le
  modèle porte, et que les deux s'accordent. Il a tiré sur chaque modèle muni
  d'une projection.
- **Il a aussi tranché une divergence au lieu de la masquer.**
  `walkthrough/5-run.yaml` divise par `0,001` alors que son `total_work` annonce
  400 000, un facteur 400 d'écart. Les deux ont raison et mesurent des choses
  différentes : 400 000 est la course entière, `0,001` la part que la tranche a
  couverte — et la commande du même bloc a lancé `--num_samples 400`, soit
  exactement 400 000 × 0,001. Le champ manquant était la part de la tranche, pas
  un nombre faux.
- Le rapport nomme le nouveau champ (*« share of the whole run this slice
  covered »*), et les deux valeurs sont déclarées sous la règle du nombre nu
  avec la raison pour laquelle elles ne sont pas des coûts.

### Ce qu'une machine dit pouvoir mesurer, face à ce qu'elle a mesuré

- `saggio power` rapporte quels compteurs répondent. La suite prend une vraie
  tranche sur chaque plateforme. **Rien ne comparait les deux.** Si IOReport
  cessait de répondre demain, le rapport dirait `absent`, la tranche reviendrait
  sans mesure, tous les tests passeraient encore, et chaque valeur deviendrait
  une estimation en silence. Deux tests échouent désormais dans ce cas, et ce
  sont les seuls d'ici dont le verdict dépend de la machine en dessous.
- Ils prennent des branches opposées par construction, et les deux ont été
  exercées : sur cette machine Apple Silicon les compteurs répondent et une
  lecture sans mesure échoue ; dans un conteneur Linux sans powercap la lecture
  doit être *absente* **et** porter une raison, et une valeur produite quand
  même échoue. Saboté en faisant taire `PowerMeter.stop` sur une machine qui
  sait mesurer : le rapport dit oui, l'exécution dit non, la sonde tombe.
- **Une correction sur ce que ce dépôt croyait de lui-même.** Les notes de
  travail affirmaient depuis octobre que « le chemin de mesure n'est exercé que
  sur ce portable ; la CI ne mesure rien ». C'était faux. La CI exécute toute la
  suite, y compris les trois tests `slow` qui lancent un vrai sous-processus,
  sur Linux et sur macOS à chaque push, et imprime `saggio power` avant eux. Ce
  qui manquait n'était pas l'exécution — c'était ce qui *vérifie* le résultat
  contre ce que la machine prétendait.
- Confirmé à part en exécutant tout le chemin mesuré — `audit --run`,
  `validate`, `render`, `next` — dans un conteneur Linux : les refus se lisent
  correctement, le modèle valide, la puissance est `estimated` depuis la plaque
  signalétique avec la raison ARM/conteneur énoncée, et le consentement est
  refusé net quand il n'y a pas de terminal pour le demander.

### Suivre chaque lien que le dépôt demande à un lecteur de suivre

- L'argument de ce paquet est qu'une valeur dit d'où elle vient, et une source
  qu'un lecteur ne peut pas atteindre est une valeur qui ne le dit plus. **Rien
  ne vérifiait les liens.** `docs/check_links.py` suit les 208 — les pages, et
  les lignes de catalogue à côté des nombres dont elles répondent — et trie les
  réponses au lieu de les réduire à un succès ou un échec.
- **Il a trouvé une citation qui avait déménagé.** La ligne de tarification
  Gemini du catalogue de services pointait vers `ai.google.dev/pricing`, que
  Google redirige désormais vers `ai.google.dev/gemini-api/docs/pricing`. Mise à
  jour dans le catalogue et dans les deux modèles d'exemple qui l'avaient
  recopiée. Une redirection est rapportée à part d'un refus pour exactement
  cette raison : le document est toujours là et la citation ne pointe plus
  dessus.
- **Et quatre pages portaient une source inventée sur le domaine d'un vrai
  constructeur.** La recette d'ajout d'une ligne de catalogue utilisait
  `nvidia.com/en-us/data-center/h300/` pour une carte graphique qui n'existe
  pas. Une citation inventée sur un vrai domaine est indiscernable d'une
  citation périmée, ce qui est le pire qu'une citation puisse être. Les liens
  d'illustration vivent désormais sur un domaine réservé à la documentation, et
  le vérificateur les saute **par règle** plutôt que par une liste.
- Le dépôt d'exemple de la recette d'audit est maintenant un dépôt qu'un lecteur
  peut réellement auditer (`github.com/karpathy/nanoGPT`, que la galerie mesure
  déjà) au lieu d'un espace réservé qui renvoie 404.
- Un 403 de Legifrance, de ResearchGate ou d'Intel est un filtre anti-robot, pas
  un document mort, et seul un serveur affirmant n'avoir aucun document de ce
  nom fait échouer la vérification. Dix-neuf liens répondent ainsi aujourd'hui
  et aucun n'est cassé.
- C'est un script de maintenance et non un test, pour la raison qui vaut pour
  `docs/sync_api.py` : une suite qui échoue parce que le serveur de quelqu'un
  est lent apprend aux gens à ignorer la suite. Un test de contrat vérifie
  seulement que son collecteur voit toujours les pages **et** les lignes de
  catalogue.

### Une arithmétique écrite en prose doit être une arithmétique qui tombe juste

- Trois endroits détaillent un calcul et posent la réponse à côté, et rien ne
  vérifiait que les mots donnent la réponse : une note de plaque signalétique
  (*« 12 cores x 4.0 W + 96 GB x 0.3725 W/GB »*), la méthode d'une projection
  (*« Whole run = measured slice / 2.5e-06. »*) et un tableau de comparaison sur
  une page. Le nouveau contrat analyse chacun et exige que ça tombe juste.
- **Il a trouvé quatre valeurs fausses dans la démonstration pas à pas
  commitée.** `3-measured.yaml` et `5-run.yaml` projetaient toutes deux une
  exécution complète dont l'**argent** était faux d'un facteur 1,15 et le
  **carbone** d'un facteur 0,736, alors que leur temps et leur énergie étaient
  justes. Les facteurs nomment la cause : un tarif d'électricité rafraîchi de
  0,240 à 0,276 USD/kWh, et une intensité réseau rafraîchie à 41,2 gCO2e/kWh.
  Les coûts unitaires ont été recalculés contre le nouveau catalogue et les
  projections sont restées en arrière — dans l'exemple pédagogique du dépôt
  lui-même, sur plusieurs versions.
- Elles sont recalculées depuis la **méthode que chaque modèle énonce**,
  appliquée à son **propre coût de tranche actuel**. Rien d'inventé : la phrase
  était déjà là et la valeur à côté avait cessé d'en découler.
- Le contrôle des projections est aussi ce qui lit la seule grandeur dont dépend
  tout coût projeté. Un modèle porte `analysis.total_work.stated_as` comme la
  chaîne `'400000'` et la fraction nulle part : tant que le diviseur n'est pas
  un champ, ce test est la seule chose qui le lit comme un nombre.
- La première version s'arrêtait à la première dimension fautive et rapportait
  `money` sur deux modèles dont le `carbon` était faux aussi. Elle collecte
  désormais : une sonde qui cache la moitié de ce qu'elle a trouvé est une
  demi-sonde.
- Sabotages, les quatre déclenchent : une valeur projetée déplacée, la réponse
  d'un tableau déplacée, une soustraction stockée déplacée, une phrase déplacée.

### Une phrase qu'un modèle porte doit être celle que ses propres chiffres produisent

- Les pages sont vérifiées contre les modèles, les modèles contre le schéma — et
  une phrase *à l'intérieur* d'un modèle n'était vérifiée contre rien. C'est là
  que vivait la faute de l'itération #7 : une note appelant « médiane de cinq
  exécutions » une valeur qui n'en est pas une.
- `measurement.power_note` doit désormais être exactement ce que `baseline_note()`
  écrit à partir des `idle_watts` et `marginal_watts` du modèle lui-même, et
  chaque avertissement que l'écart enregistré impose doit être un avertissement
  que le fichier porte. Les deux phrases sont passées dans des fonctions qui
  lisent un bloc stocké, pour que l'écrivain et la vérification ne puissent pas
  diverger. Trois sabotages, trois échecs : changer la soustraction stockée,
  changer la phrase, élargir l'écart sans toucher à l'avertissement.
- **`measurement.marginal_watts` est désormais stocké.** La soustraction était
  énoncée en prose — *« Subtracting it gives 3.6 W »* — et conservée nulle part :
  le nombre sur lequel la phrase repose n'était pas un champ, dans un paquet dont
  la règle est qu'une valeur est un champ. Un second test de contrat vérifie que
  la puissance stockée moins le plancher stocké **est** la marge stockée.
- Toujours en prose seule, et dit plutôt que laissé de côté : le diviseur sur
  lequel repose toute projection. `method` dit *« Whole run = measured slice /
  2.5e-06 »* et les notes disent *« a slice covering 0.00025% of the run »*,
  tandis que `analysis.total_work.stated_as` porte `'400000'` comme **chaîne de
  caractères**. Trois énoncés d'une seule grandeur, dont aucun n'est un nombre
  que le schéma puisse voir.

### Le dépôt refuse un nombre nu ; il n'a jamais rien refusé à une phrase

- Quatre itérations Ralph de suite, la faute qui comptait était dans de la
  prose, et seule celle portant sur un *nombre* a été attrapée par une machine :
  un identifiant Legifrance inventé, une affirmation fausse selon laquelle ce
  paquet attribue la puissance « comme Kepler », une note appelant « médiane de
  cinq exécutions » une valeur qui n'en est pas une, et un `derived_from` qui
  n'était pas une dérivation — la dernière attrapée par le validateur, les trois
  premières par une lecture humaine.
- Écrire la sonde a révélé que **quatre pages commitées étaient périmées depuis
  deux itérations**. `GALERIE.md` annonçait **21,3 W** pour le modèle `render`
  trois lignes au-dessus d'un paragraphe donnant son plancher à 13,8 W et la
  valeur portée à 17,4 W — une contradiction dans un seul paragraphe. La
  comparaison avec Kepler dans `MEASURING.md` / `MESURER.md` citait encore une
  part, un total, un plancher et un domaine processeur d'une mesure remplacée
  depuis, et sa conclusion était fausse d'un facteur 2,7.
- **La convention désormais tenue** : dans une section qui nomme un modèle
  commité, une valeur écrite en **gras** est une affirmation que le modèle la
  porte. Une valeur qui n'est pas celle du modèle — une plaque signalétique, un
  seuil, un chiffre tiré d'un article — s'écrit sans gras. La règle est donc
  déclarée dans la page, par la façon de l'écrire, et non dans une liste de
  chaînes connues qui se périmerait dans le sens qui cache la faute.
- Une seconde règle, plus stricte, pour les nombres qu'un lecteur rencontre en
  premier : une ligne de tableau qui lie un modèle doit citer la valeur de ce
  modèle **à cette unité et à ce statut**. Saboter un chiffre, et séparément
  saboter `mesuré` en `estimé`, la fait échouer à chaque fois.
- La comparaison avec Kepler est recalculée, et gagne ce que la version périmée
  cachait : **le facteur n'est pas une constante.** La mesure actuelle donne
  3,01 W contre 0,72 W, un facteur quatre ; la précédente — trois fois moins au
  repos — donnait 2,65 W contre 1,68 W, un facteur 1,58. Plus la machine est
  occupée, plus la soustraction retire et moins le compteur de domaine retire :
  les deux méthodes divergent donc le plus quand un lecteur a le plus besoin
  qu'elles s'accordent.
- **Ce que cela ne sait toujours pas attraper**, dit franchement : une phrase
  qui affirme quelque chose sur le monde plutôt que sur un nombre. « C'est ainsi
  que Kepler répartit un nœud » passerait encore aujourd'hui.

### La porte de dérive lit désormais le bruit que les modèles ont mesuré

- `saggio diff` arbitrait une publication à dix pour cent contre des nombres
  dont le bloc de mesure disait qu'ils bougent de cent. **Il avait la preuve
  dans les deux fichiers qu'il comparait et n'en lisait aucune.** Deux mesures
  à cinq exécutions d'un code inchangé, l'une après l'autre sur un portable,
  faisaient échouer six changements ; elles n'en font plus échouer **aucun**,
  avec huit rapportés comme tenant dans les étendues que les deux modèles ont
  eux-mêmes enregistrées.
- Elle échoue toujours quand la preuve dit que quelque chose a bougé : le même
  modèle neuf contre un plus ancien mesuré *une seule fois* échoue, parce que
  cette valeur unique tombe hors de l'étendue couverte par les cinq exécutions.
- L'intervalle d'une valeur dérivée est le produit de ceux dont elle dérive,
  trouvé en remontant `derived_from` — exact tant que chaque étape est
  proportionnelle à ses entrées, ce qui est la façon dont tout coût d'un modèle
  est construit. Une valeur qui n'atteint aucune étendue mesurée n'a pas
  d'intervalle et reste arbitrée comme avant.
- **Les intervalles n'excusent jamais que le seuil.** Un statut affaibli, une
  provenance affaiblie, une unité ou une devise changée, une quantité supprimée
  échouent quel que soit le bruit.
- Excusé **visiblement** : la ligne nomme les deux étendues et le résumé les
  compte — une publication laissée passer par un intervalle de cent pour cent
  doit montrer l'intervalle au lecteur. La surface JSON porte `within_noise`,
  `noise_before`, `noise_after` et `excused_by_noise`.
- **Ce que cela ne peut pas attraper, dit dans les deux livres de recettes.**
  Une régression est attrapée par la dimension mesurée serré. Une charge deux
  fois plus lente échoue sur `costs.time` et sur le temps projeté, tandis que
  ses lignes carbone, argent et énergie sont excusées — un intervalle de
  puissance de 109 % avale un mouvement de 100 %. La porte est aveugle là où
  la preuve l'est, ce qui est voulu et reste une limite : une régression qui
  augmente la puissance sans toucher au temps passerait.
- **L'intervalle d'une projection est relié dans le code, pas dans le modèle.**
  Donner un `derived_from` à une projection a été essayé d'abord et le
  validateur l'a refusé avec la bonne raison — *states 18000000.0 but does not
  follow from scenarios[0].costs.time* — parce qu'une projection divise par une
  fraction que personne n'a nommée. `derived_from` affirme qu'une valeur
  **suit arithmétiquement** de ses entrées ; un intervalle n'a besoin que de la
  **proportionnalité**, la seule chose qu'une division par une constante
  soutienne réellement. L'affirmation la plus forte aurait été fausse dans onze
  modèles commités.

### Une seule exécution ne borne rien, et les deux figures ne se comportent pas pareil

- `saggio measure --repeat N` exécute la commande N fois et rapporte l'écart.
  Sur le modèle vedette de ce paquet, cinq exécutions de la même commande sur
  une machine à une minute d'intervalle : le **temps a bougé de 15 %**
  (1,326 s à 1,538 s) et la **puissance mesurée de 109 %** (16,13 W à
  37,36 W). Le temps est une propriété du travail ; la puissance est une
  propriété de la pièce, parce qu'un compteur mesure la machine et que l'une
  des cinq a attrapé autre chose qui se réveillait. Les deux portaient le même
  mot, `measured`.
- **Aucun cinquième état n'a été inventé.** En inventer un avant d'avoir mesuré
  ce qu'il décrirait est la façon dont le problème a commencé. Ce qui est
  ajouté est un nombre à côté du nombre : `measurement.repeats`,
  `measurement.spread`, et une phrase dans les notes de chaque quantité que les
  répétitions bornent.
- Le modèle porte **une exécution réelle** — celle dont le temps était médian —
  et non une médiane assemblée champ par champ : l'énergie d'un modèle est son
  temps multiplié par sa puissance, et des médianes prises sur des exécutions
  différentes énonceraient un couple qui n'a jamais eu lieu. Ce qui veut dire
  aussi que la puissance que porte un modèle n'est **pas** la puissance médiane
  de la série, et ses notes le disent au lieu de l'appeler une médiane qu'elle
  n'est pas.
- Une quantité mesurée une seule fois le dit désormais (*« Measured once, so
  nothing here bounds how far a second run would move it »*). Le silence passe
  pour de la stabilité, et la puissance est la figure qui ne l'est pas.
- Un écart supérieur à 10 % — le seuil sur lequel `saggio diff` arbitre une
  publication — fait l'objet d'un avertissement.
- **Aucun profil par fonction n'est pris quand `--repeat` dépasse un.** Le
  profileur change ce qui est chronométré : une série avec une exécution
  profilée au milieu d'exécutions ordinaires rapporterait un écart que le
  profileur y aurait mis. Trouvé en l'exécutant : la première version profilait
  l'exécution numéro un et laissait les quatre autres tranquilles.
- Le validateur a refusé les nouveaux champs à la première écriture —
  `measurement.repeats: is a bare number; wrap it in a quantity so it carries
  an honesty status` — ce qui est la règle qui fonctionne. Ils sont désormais
  déclarés exemptés, avec la raison : un statut est une propriété de la
  provenance d'un nombre et un écart une propriété de sa stabilité ; confondre
  les deux les perdrait toutes les deux.
- `examples/render.yaml` remesuré avec `--repeat 5` ; ses cinq exécutions sont
  dans le fichier. Rien n'a été écarté pour que l'écart paraisse plus petit.
- Un test de contrat neuf : un temps ou une puissance `measured` doit énoncer de
  combien une seconde exécution le déplacerait. Il a tiré sur trois modèles le
  jour où il a été écrit.

### Un modèle qui disait exclure la capacité au repos, tout en tarifant la machine entière

- Tout modèle écrit par ce paquet portait la ligne *« Idle capacity. This is the
  cost of one unit of work, not of being ready. »* dans ses `exclusions`. Pour un
  modèle bâti sur une plaque signalétique, c'est vrai. Pour un modèle dont la
  puissance a été **lue sur les compteurs de cette machine**, c'est faux, et
  trois modèles commités le prouvaient : `examples/walkthrough/5-run.yaml`
  tarifait son unité de travail à **31,9 W** alors que son propre bloc de mesure,
  trois champs plus haut, enregistrait **2,9 W** comme part attribuable. Un
  facteur onze, dans un seul fichier.
- La liste des exclusions n'est plus une constante. `saggio audit --run` écrit
  la ligne vraie de la valeur qu'il vient d'obtenir, et `saggio measure --into`
  **réécrit** celle qu'il vient de rendre fausse — en nommant le plancher que la
  machine tirait, la part de travail processeur qu'était l'exécution, et en
  admettant que les coûts n'utilisent ni l'un ni l'autre.
- Un `power_draw` mesuré énonce désormais **ses deux** frontières. Celle du
  matériel (quels compteurs ont répondu, quel silicium ils voient) y était déjà ;
  celle de la charge — *« This is the whole machine's draw, not this run's
  alone »* — n'y était pas, et sans elle un lecteur prend la valeur pour celle de
  l'exécution.
- Trois tests de contrat sur chaque modèle commité : aucun ne peut prétendre
  exclure le repos pendant que sa puissance est `measured` ; la ligne sur le
  repos doit être celle que le paquet écrirait aujourd'hui, régénérée depuis le
  bloc de mesure du modèle lui-même ; et une puissance mesurée doit nommer sa
  frontière de charge. Le premier a tiré sur quatre modèles le jour où il a été
  écrit.
- `saggio measure --json` émettait une charge utile listée à la main qui perdait
  l'attribution que la même commande venait de calculer — l'avertissement citait
  une part de travail processeur qu'aucun champ du JSON ne portait. Il émet
  désormais la table qu'un modèle reçoit, et la sortie texte imprime la valeur
  attribuable à côté de la soustraction de ligne de base, au lieu de la seule
  moitié qui flatte.
- `examples/render.yaml` a été remesuré pour qu'un modèle de la galerie porte le
  bloc : **21,3 W** pendant la tranche, **9,9 W** avant elle, **2,65 W**
  attribuables à partir d'une part de 14,7 %. Temps 0,0277 s, carbone
  1,01e-05 gCO2e. `examples/request.yaml` conserve ses valeurs, que
  [`FRONTIERES.md`](FRONTIERES.md) cite.
- [`MEASURING.md`](MEASURING.md) / [`MESURER.md`](MESURER.md) affirmait que ce
  paquet attribue la puissance *« comme Kepler »*. C'est faux. Kepler v0.10
  divise la puissance **active** — le total moins la ligne de base au repos —
  par la part
  ([formule](https://sustainable-computing.io/kepler/usage/power-attribution/)) ;
  ce paquet multiplie la part par **le compteur propre du domaine processeur**.
  Sur `examples/render.yaml`, cela donne 1,68 W contre 2,65 W, **un facteur 1,58
  à partir de la même mesure**. La page énonce désormais les deux et n'en choisit
  aucune.
- [`LANDSCAPE.md`](LANDSCAPE.md) / [`PAYSAGE.md`](PAYSAGE.md) : le manque « rien
  n'est attribué à un processus » dit maintenant ce qui *est* enregistré, et que
  les coûts utilisent toujours la valeur entière.
- **Les deux rapports rendaient le bloc de mesure en imprimant chaque scalaire
  et en sautant tout ce qui était imbriqué.** Trois champs sont imbriqués, et
  tous trois étaient ceux dont un lecteur a besoin : la part qui justifie à elle
  seule la valeur attribuable imprimée juste au-dessus, les compteurs qui ont
  répondu, et la répartition par sous-système — la seule répartition mesurée du
  rapport. Le rapport Markdown, commité à côté de chaque modèle de la galerie,
  n'en montrait aucun, et les scalaires qu'il montrait arrivaient sans unité
  (`attributed watts | 2.65`). Les deux rapports prennent désormais des lignes
  étiquetées d'une seule fonction, et un test de contrat échoue quand un champ
  du bloc n'atteint pas la page.

### La ligne énergie d'un dossier au titre du règlement IA

- L'annexe XI impose au fournisseur d'un modèle d'IA à usage général de
  documenter sa **consommation énergétique connue ou estimée**, et là où elle
  n'est pas connue elle autorise une estimation **à partir du calcul utilisé** —
  c'est-à-dire la méthode de ce paquet, inscrite dans la loi. Applicable depuis
  le **2 août 2026** (jusqu'à 3 % du chiffre d'affaires mondial ou 15 M€) ; les
  modèles mis sur le marché avant le 2 août 2025 ont jusqu'au **2 août 2027**.
- [`ANNEX-XI.md`](ANNEX-XI.md) / [`ANNEXE-XI.md`](ANNEXE-XI.md) met l'exigence
  en regard de ce qu'un modèle de coût porte déjà, ligne à ligne, et dit tout
  aussi explicitement ce qu'il ne fait pas : ce n'est pas un dossier, il couvre
  une unité de travail sur une machine, et il documente l'énergie et non le
  reste de l'annexe.
- La méthodologie s'écrit encore. La Commission a consulté entre avril et juin
  2026 sur la mesure de l'énergie de l'IA, l'AI Office doit publier une
  synthèse, et des actes délégués pourront fixer les méthodes « en vue de
  permettre une documentation comparable et vérifiable ». Ces deux mots sont le
  cahier des charges de ce paquet, et la page dit ce qu'il fait déjà pour
  chacun.

### Une page sur les frontières, parce que deux industriels viennent de le prouver

- Google a publié **0,03 gCO2e** pour un prompt Gemini médian et Mistral
  **1,14 gCO2e** pour une réponse de quatre cents jetons. Environ trente-huit
  fois d'écart, et aucun n'esquive : l'un compte l'électricité d'un contrat et
  la capacité au repos réservée pour vous servir, l'autre la moyenne du réseau
  et les usines.
- [`BOUNDARIES.md`](BOUNDARIES.md) / [`FRONTIERES.md`](FRONTIERES.md) prend un
  modèle commité — `examples/request.yaml`, mesuré — et montre ce que son
  chiffre devient sous quatre frontières. Deux sont calculées ; **deux sont
  refusées**, chacune nommant ce qu'elle demanderait.
- L'arithmétique est celle du paquet, sur les chiffres de son propre catalogue.
  Amortir l'empreinte ISO 14067 de NVIDIA pour une HGX H100 sur le même temps
  d'exécution donne un terme de fabrication **de trois à six fois
  l'électricité**, la seule durée de vie du matériel faisant varier la réponse
  d'un facteur deux. Un chiffre qui omet la fabrication n'est pas un chiffre
  prudent : c'est un autre chiffre.

### Le verbe pour la personne qui tient quinze champs ouverts

- Un audit revient avec tous les coûts ouverts, chaque champ portant une phrase
  sur ce qui le résoudrait, et rien ne disant par lequel commencer. Les champs
  ne sont pas indépendants : sur l'un des modèles de la galerie, **une question
  ferme cinq nombres** et quarante-six ne ferment qu'elles-mêmes. Qui travaille
  de haut en bas passe l'après-midi sur celles qui ne débloquent rien.
- `saggio next cost_of_running.yaml` les classe, et le classement est de
  l'arithmétique et non une opinion : une grandeur nomme ses entrées dans
  `derived_from`, donc lire ces arêtes à l'envers dit exactement quelles autres
  grandeurs deviendraient calculables, cascade comprise.
- **Aucune question n'est inventée et rien de dérivé n'est demandé.** Chaque
  ligne est un champ que le modèle tient déjà ouvert, cité dans la phrase que
  le modèle a déjà écrite pour lui, et un champ que ce paquet calcule lui-même
  n'est jamais soumis à un humain : ce serait lui demander de faire
  l'arithmétique, sans provenance.
- Un champ qui ne ferme rien d'autre reste listé. « Ne ferme que lui-même » est
  la description honnête d'un chiffre d'eau ou d'un facteur d'émission
  contractuel, pas une raison de le cacher.
- `saggio.next_questions` et `saggio.questions_payload` dans la bibliothèque,
  `POST /next` sur la surface HTTP, et donc un outil qu'un agent peut appeler.

## 1.5.0 — 2026-10-17

Trois façons de plus d'atteindre le même moteur, et la première version où *à
qui est cette émission* trouve sa réponse sur chaque surface plutôt que sur une
seule. Rien ici ne casse : chaque nom public se résout comme avant, le schéma
est inchangé, et les deux nouvelles surfaces arrivent en extra que
l'installation par défaut ne porte pas.

### Deux défauts que la construction de la version a trouvés, et que la suite ne pouvait pas trouver

- Installer la roue dans un environnement vide est le seul test qui résout les
  dépendances comme le fait un utilisateur, et c'est celui que ce paquet n'avait
  jamais lancé pour la nouvelle surface. Il a échoué du premier coup, à l'import,
  avant d'avoir servi la moindre requête.
- **`fastapi-mcp` demande `mcp>=1.12` sans borne supérieure**, et appelle
  `Server(name, description)` avec deux arguments positionnels. `mcp` 2.0 a rendu
  tout ce qui suit le nom accessible par mot-clé seulement : une résolution
  fraîche installe donc une bibliothèque de protocole que l'adaptateur ne peut
  pas importer. C'est une `TypeError` à l'import et non un conflit de
  dépendances, si bien que rien dans le résolveur ne proteste et que rien, dans
  un environnement de développement qui détient déjà une copie plus ancienne, ne
  s'en aperçoit. Les deux extras portent maintenant `mcp>=1.12,<2`, borné ici
  parce que le paquet qui devrait le borner ne le fait pas et que celui-ci est ce
  qu'un utilisateur installe.
- **Le serveur de protocole annonçait un paragraphe comme version.** Le second
  paramètre de ce même constructeur est la version : un client qui listait ses
  serveurs montrait donc toute la description de l'application là où va une
  version, et un agent à qui l'on demande quelle version lui a répondu aurait
  cité de la prose. La version est remise après construction, et un test l'y
  maintient.

### Le catalogue a été relu pour cette version, pas redaté

- Les quatre colonnes rafraîchissables ont interrogé leurs sources le jour de la
  version : le jeu de données annuel publié d'Ember pour les trente-huit figures
  carbone, GlobalPetrolPrices pour les tarifs, la base de l'IANA pour les
  soixante-quatre fuseaux horaires, Boavizta pour les quatre empreintes de
  processeur. **Rien n'a bougé au-delà de la précision propre du catalogue**, et
  les dates disent maintenant que quelqu'un a regardé.
- Cela compte à cause de ce à quoi ressemble l'alternative. Les lignes étaient à
  seize jours de la fin de leur fenêtre, et une fenêtre qui se referme peu après
  une version est une invitation à pousser une date plutôt qu'à lire une source,
  ce qui est le seul résultat que tout le mécanisme de fraîcheur existe pour
  empêcher.

### Deux manques dans les livres de recettes, et les contrôles qui les surveillent

- `scopes` est sorti il y a deux versions, répond à la question autour de
  laquelle celle-ci est bâtie, et n'apparaissait dans **aucun des deux livres de
  recettes**. `machine` n'y avait jamais été non plus. Les deux y sont
  désormais, dans les deux langues, avec ce que chacun imprime et pourquoi.
- Le contrôle qui l'aurait attrapé : **chaque verbe que connaît l'analyseur
  d'arguments doit être montré dans les deux livres de recettes**. Les pages
  promettent chaque commande qu'un lecteur est censé taper, et rien ne
  confrontait cette promesse à l'analyseur qui les définit.
- Un second contrôle, né de la même forme de défaut : **une version imprimée
  dans la prose doit être celle qui est installée**. `python -m saggio
  --version` est documenté avec sa réponse à côté, et cette réponse se périme à
  la version suivante, à l'endroit même où un lecteur va voir quelle version il
  a.

### Les notes de version existent dans l'autre langue

- Ce fichier est publié en flux Atom sur le site : un lecteur français qui
  s'abonnait aux notes de version recevait donc de l'anglais.
  [`CHANGELOG.md`](CHANGELOG.md) a maintenant ce jumeau, ses huit versions
  comprises, et le site construit **`fr/feed.atom`** à partir de lui, avec son
  titre propre et ses identités d'entrées propres.
- Les deux moitiés portent les mêmes titres de version exprès : un seul
  constructeur lit l'une ou l'autre, et une version qui existerait dans une
  langue et pas dans l'autre serait une version annoncée à moitié.

### Trois portes de plus, vers le même moteur

- La bibliothèque et la ligne de commande atteignent tous ceux qui installent un
  paquet Python, ce qui n'est pas la personne qui doit déclarer le chiffre. Il
  existe désormais une **surface HTTP**, `pip install "saggio[api]"` et
  `uvicorn saggio.api.app:app`, avec des routes pour valider, placer, produire un
  rapport, comparer, lire les catalogues et auditer un dépôt.
- Une **surface d'agent** s'appuie sur la même application :
  `uvicorn saggio.api.mcp:app` sert des outils Model Context Protocol sur `/mcp`.
  Ils sont engendrés à partir du document OpenAPI de l'application : le nom d'un
  outil est l'identifiant de la route, sa description est la docstring de la
  route. Rien n'est écrit deux fois, et c'est pourquoi rien ne peut dériver
  jusqu'à un agent annonçant à quelqu'un le mauvais scope.
- **Deux refus tiennent à la forme de la surface HTTP plutôt qu'à ses
  réglages.** Il n'existe aucune route pour mesurer : mesurer exécute le code
  d'un dépôt avec les permissions du serveur, et à travers un réseau il n'y a
  personne à qui demander un consentement. Et `/audit` ne clone rien tant que
  l'exploitant n'a pas posé `SAGGIO_API_ALLOW_CLONE` ; éteinte, la route répond
  ce qu'il faudrait.
- `placed_model` est nouveau dans la bibliothèque. Le placement d'un modèle
  entier était assemblé dans la commande `scopes`, où les autres surfaces ne
  pouvaient l'atteindre qu'en le recopiant, et une copie qui dérive, c'est ce
  paquet qui se contredit sur la ligne d'inventaire où va un chiffre. Un test
  exige maintenant que la route renvoie exactement ce que renvoie la
  bibliothèque, champ par champ.
- Un `Dockerfile` et un `docker-compose.yml` livrent les deux surfaces avec
  l'interrupteur de clonage éteint, un système de fichiers en lecture seule,
  aucune capacité et un utilisateur non privilégié.
- [`USING.md`](USING.md) et [`UTILISER.md`](UTILISER.md) disent à quoi sert
  chacune des cinq surfaces, ce qu'aucune n'a le droit de faire, et comment en
  ajouter une sixième.

### Le skill restait muet pour la moitié des gens à qui il était destiné

- Sa description se déclenchait pour un ingénieur qui dit « cost per request » et
  pas pour l'équipe RSE qui pose la même question avec ses mots à elle : quel
  scope, quelle méthode, ce que le vérificateur doit voir. Les deux vocabulaires
  sont maintenant dans la description, dans les deux langues, sous le plafond
  publié de 1024 caractères.
- Le mode d'emploi ne mentionnait jamais `scopes`, le seul verbe qui répond au
  second lecteur. C'est désormais une étape à part entière, avec le refus du
  market-based et le fait que l'eau n'a pas de scope.
- Une référence à lui, `references/inventory.md`, sur ce qu'un agent peut et ne
  peut pas dire aux personnes qui déclarent le chiffre.
- Les évaluations ont gagné une section **triggering**. Tous leurs cas testaient
  un skill déjà chargé ; savoir s'il se charge est la première chose qui peut
  échouer et rien ne la surveillait.
- [`TRIGGERS.md`](TRIGGERS.md) refusait la *comptabilité carbone
  organisationnelle* en bloc, ce qui avalait la question voisine à laquelle il
  répond. Un bilan complet reste le métier de quelqu'un d'autre ; où se range la
  ligne du logiciel dans ce bilan n'est pas la même question et ne partage plus
  son refus.
- Cette page n'avait pas non plus de moitié française, ce qui, pour le public
  qu'on venait d'élargir, était la mauvaise moitié à faire manquer.
  [`DECLENCHEURS.md`](DECLENCHEURS.md) la complète, en portant exprès les deux
  vocabulaires : une équipe française qui la lit voit encore les formulations
  anglaises que ses propres ingénieurs taperont.

### macOS est de retour dans la barrière, et il a trouvé quelque chose dès sa première exécution

- Presque tout le code de compteurs de puissance de ce paquet est propre à
  macOS, et aucun job d'intégration continue n'en avait lu une ligne depuis que
  la matrice avait été réduite à une seule. Une régression dans `IOReport`
  serait partie en production et aurait été trouvée par un utilisateur. Le
  runner est en Apple Silicon, c'est-à-dire le matériel pour lequel ce code
  existe.
- Il avait été retiré parce qu'il était rouge. Ce qui le rendait rouge a été
  corrigé ensuite, dans un autre commit, sans que personne revienne vérifier :
  des tests qui encodaient la machine d'un développeur plutôt que le produit. Le
  remettre n'a rien coûté d'autre que de regarder.
- `workflow_dispatch`, pour qu'une modification de la barrière puisse s'essayer
  sur sa propre branche. Une modification d'intégration continue qui ne peut se
  tester qu'en la fusionnant est une modification que personne ne teste ;
  celle-ci était fausse à sa première exécution et juste à la seconde, sur une
  branche.
- Chaque exécution imprime `saggio power` avant la suite, pour qu'un compteur qui
  cesse de répondre le dise avec ses propres mots plutôt qu'à travers le test qui
  se trouve le remarquer.

### `TZ=Japan` était silencieusement ignoré au profit du portable

- La première exécution macOS a échoué sur une assertion disant qu'un nom de
  fuseau horaire contient une barre oblique. Un runner d'intégration continue est
  réglé sur **UTC**, ce qu'aucun portable de développeur n'est, et la suite
  n'avait jamais tourné dans un endroit qui l'était.
- L'assertion était la plus petite moitié. `UTC`, `GMT`, `Japan`, `Singapore`,
  `Israel` et `EST5EDT` sont tous de vraies entrées de la base de fuseaux
  horaires et aucun ne contient de barre oblique : le lecteur **jetait donc le
  `TZ` que quelqu'un avait délibérément posé** et utilisait le fuseau de la
  machine à la place. Poser `TZ=Japan` sur un portable à Paris ne vous donnait
  pas le Japon ; cela vous donnait la France, silencieusement, avec une intensité
  carbone française dans un fichier que quelqu'un allait citer.
- La barre oblique n'était pas davantage une preuve dans l'autre sens : une
  chaîne de *règle* `TZ` POSIX peut en contenir une et ne nomme aucun fuseau, et
  `TZ=/etc/passwd` était renvoyé comme un nom de fuseau parce qu'il contient une
  barre oblique.
- Les trois sources — la variable d'environnement, le lien symbolique
  `/etc/localtime`, la bibliothèque standard — posent maintenant la même question
  à la **base de fuseaux horaires**, via `zoneinfo`. Sans réseau et sans
  dépendance : ce sont les fichiers vers lesquels `/etc/localtime` pointe déjà.
- Un nom que le catalogue ne liste pas donne toujours **aucun pays plutôt qu'un
  autre**. `Japan` est un nom de compatibilité que la base conserve et le
  catalogue liste `Asia/Tokyo`, donc le pays reste ouvert, ce qui est la bonne
  réponse et tout l'enjeu : avant le correctif, il se résolvait là où le
  développeur était assis.

### Un chiffre dit maintenant sur quelle ligne d'un bilan GES il se range

- Le fossé que cela comble est celui qui sépare les deux personnes qui doivent se
  mettre d'accord : une équipe technique produit un chiffre carbone, et une
  équipe RSE ne peut pas le déclarer, parce que *à qui est cette émission* est
  une question à laquelle le chiffre ne répondait jamais. Déclaré en scope 2
  alors que la machine était louée, il double-compte contre la publication du
  fournisseur ; laissé de côté, il manque, simplement.
- Le GHG Protocol tranche par un seul fait — **qui achète l'électricité et
  possède la machine** — et ce fait était déjà dans chaque modèle, sous
  `deployment.provider`. Le catalogue des fournisseurs l'enregistre maintenant
  comme `operated_by`, si bien que la règle est une donnée et non du code :
  possédez la machine et l'électricité est votre **scope 2** et le matériel votre
  **scope 3 catégorie 2** ; louez-la et les deux sont du **scope 3
  catégorie 1**, puisque vous avez acheté un service.
- `saggio scopes model.yaml` imprime le placement, la raison, et la norme qui le
  tranche. `--json` pour une chaîne de traitement. Chaque rapport produit —
  Markdown, HTML, Word, PDF — porte la même chose dans une section à lui, dans
  les deux langues.
- Un fournisseur que personne n'a classé n'obtient **aucun scope** plutôt que la
  supposition la plus proche. Les deux réponses diffèrent par l'entité juridique
  qui déclare l'émission, et une mauvaise réponse a exactement l'air aussi propre
  qu'une bonne.
- L'énergie est placée pour ce qu'elle est : la donnée d'activité *à partir de
  laquelle* un chiffre de scope est calculé, pas une émission. L'eau n'a pas de
  scope, parce que ce n'est pas un gaz à effet de serre. Les deux le disent en
  une phrase, parce qu'un « sans objet » dans un rapport se lit comme un oubli.

### Le chiffre de scope 2 dit de laquelle des deux méthodes il relève

- Une moyenne de réseau **est** la méthode location-based, par définition. Le GHG
  Protocol exige que le scope 2 soit déclaré des deux façons partout où des
  instruments contractuels existent, et la norme européenne amendée énonce la
  même paire. Ce paquet en portait une et ne disait pas laquelle.
- Il le dit maintenant, et nomme la moitié manquante : un chiffre market-based
  vient d'un facteur propre au fournisseur, des instruments que vous détenez, ou
  du mix résiduel de votre marché, et aucun des trois ne se déduit d'une moyenne
  de réseau. Il ne rapporte donc ni chiffre market-based ni zéro : une liste de
  courses plutôt qu'une impasse.

### L'autre moitié du scope 2 est maintenant un chiffre, pas une excuse

- La section ci-dessus nommait la moitié manquante et s'arrêtait là. Une liste de
  courses vaut mieux qu'une impasse, mais une équipe RSE qui la lit doit encore
  quitter l'outil, calculer le second nombre ailleurs, et réconcilier deux
  documents. Le scope 2 est exigé **des deux façons** ; une moitié était un
  manque fonctionnel vêtu d'une bonne explication.
- `carbon_market_based` est désormais une dimension canonique, calculée depuis
  `assumptions.market_carbon_intensity` — **le seul fait que l'organisation est
  la seule à détenir.** Énoncez le facteur et la figure apparaît à côté de la
  location-based, à partir de la même énergie, étiquetée de la méthode qui l'a
  produite et surveillée contre la dérive de la même façon. N'énoncez rien et la
  liste de courses s'imprime comme avant. Rien n'est jamais dérivé d'une moyenne
  de réseau, qui est l'autre méthode par définition.
- **Elle est tenue à une règle de provenance plus stricte que tout le reste du
  modèle.** Un `source_url` manquant ailleurs est un avertissement ; ici c'est
  une **erreur**. Tout autre nombre a une source qu'un lecteur partage et une
  commande de rafraîchissement qui la relit. Celui-ci n'a ni l'une ni l'autre :
  personne d'autre que vous ne détient le contrat, et rien ici ne peut aller
  regarder — sans son document, il est donc invérifiable par construction. Une
  `retrieved_date` manquante est un avertissement, parce qu'un facteur contractuel
  est réénoncé chaque année.
- **Un chiffre market-based seul fait l'objet d'un avertissement.** C'est la
  moitié qu'un contrat peut améliorer, et publiée sans sa compagne elle se lit
  mieux que la déclaration ne l'est. Le placement location-based, en regard,
  cesse de dire que la paire est cassée dès qu'elle est entière — et la phrase
  qui le remplace dit la seule chose qu'une paire entière invite à mal
  comprendre : le nombre market-based ne remplace pas l'autre, parce qu'un
  contrat ne change pas quels électrons le réseau a livrés.
- **Sur du matériel loué, aucune ligne n'est écrite.** La paire vit à
  l'intérieur du scope 2 ; sur la machine d'un fournisseur, l'électricité est le
  scope 2 du fournisseur et la paire est à lui de la publier. Ce qui vous
  parvient est un service acheté en catégorie 1, où la norme ne trace aucune
  paire de ce genre. Un audit là-bas ne laisse personne avec un `TODO` qui ne
  pourra jamais devenir vrai — et un modèle déplacé chez un fournisseur après
  coup s'entend dire pourquoi sa ligne a perdu son scope, en toutes lettres.
- **La projection sur un autre matériel garde les méthodes que le scénario
  porte**, pour la même raison que l'eau est projetée : une dimension qui
  disparaît entre deux tableaux du même rapport a l'air d'une réponse plutôt que
  d'un oubli. La phrase qui dit ce qui a été tenu constant nomme désormais le
  facteur contractuel comme l'hypothèse la moins susceptible de survivre au
  déplacement — un contrat de fourniture se signe pour un site.
- **La traduction en kilomètres dit quelle figure elle a traduite**, mais
  seulement là où il y en a deux. Elle a toujours traduit le nombre
  location-based, ce qui était sans ambiguïté tant qu'il était le seul carbone de
  la page ; à côté d'une figure qui peut en différer d'un facteur dix, ce ne
  l'était plus, et cette ligne est celle qu'un non-spécialiste lit vraiment.
- Trouvé en câblant tout cela : la commande `scopes` décidait quelles émissions
  non placées expliquer à partir de **sa propre copie à deux éléments** de la
  liste des émissions, si bien que le refus le plus précis que ce paquet écrive
  ne s'imprimait nulle part.

### `INVENTORY.md` / `INVENTAIRE.md`

- La page pour qui déclare plutôt que pour qui mesure : la correspondance des
  scopes et pourquoi, ce que la taxonomie de statuts et le contrat de provenance
  donnent à un vérificateur, et six choses que cet outil ne couvre pas — pas de
  parc informatique, un facteur market-based à partir duquel il calcule mais
  qu'il n'inventera jamais, pas de fin de vie, aucune compensation déduite, un
  chiffre cloud qui est un modèle et non une facture, et un petit catalogue.
- Les règles contre lesquelles elle est écrite, vérifiées le 2026-10-14 plutôt
  que rappelées de mémoire : les trois documents du GHG Protocol, la [directive
  (UE) 2026/470](https://eur-lex.europa.eu/eli/dir/2026/470/oj/eng) et ce que
  l'Omnibus a fait au périmètre de la CSRD, la renumérotation de l'exigence GES
  de E1-6 à E1-8 dans les ESRS amendées, et le *bilan GES* réglementaire français
  de l'article L. 229-25, qui est une obligation distincte avec son propre dépôt.
- **Une citation de cette page était inventée et a été attrapée avant de
  partir.** L'identifiant Legifrance de l'article L. 229-25 avait été écrit de
  mémoire plutôt que lu, et pointait vers un autre article. Trouvé en essayant de
  le suivre. La règle que ce paquet applique à son catalogue s'applique à sa
  prose.

### `LANDSCAPE.md` couvre l'autre côté de la pièce

- Les outils qu'une équipe RSE a déjà, que le tableau de comparaison ne note
  délibérément pas : les plateformes de comptabilité carbone qui sont le système
  de référence d'un bilan entier et ne savent pas lire votre code, Boavizta —
  dont l'API calcule déjà quatre des empreintes de processeur de ce catalogue et
  dont la moitié GPU est refusée nommément — l'Impact Framework de la Green
  Software Foundation, et Climatiq.

### Trente-huit lignes carbone citaient un lien qui montrait une erreur au lecteur

- Chaque ligne de réseau citait `api.ember-energy.org/v1/carbon-intensity/yearly`.
  Interrogé sans clé, ce point d'entrée répond **HTTP 403** et
  `{"detail":"No API key set"}`. Chaque chiffre carbone du catalogue — et des
  onze modèles d'exemple commités, et des onze rapports qui en sont issus —
  portait donc une citation qui ne montrait aucun nombre à qui la suivait, dans
  un paquet dont toute la proposition est qu'une figure dit d'où elle vient et
  peut être vérifiée là.
- Les lignes citent maintenant le [jeu de données annuel publié par
  Ember](https://ember-energy.org/data/yearly-electricity-data/) : la même
  série, en CC-BY-4.0, sans clé, et une page qui s'ouvre. Le point d'entrée est
  toujours nommé — dans l'en-tête du catalogue et dans le module — là où le
  nommer relève de la provenance de la méthode et non d'une invitation à aller
  voir.
- **La suite avait déjà un test pour exactement ce défaut**, écrit quand quatre
  lignes de processeur citaient un point d'entrée qui répond au lecteur avec le
  mauvais nombre. On lui avait donné une URL et parlé de celle-là, si bien que
  celle d'Ember est restée dans trente-huit lignes pendant trois itérations, en
  passant le test. La règle est désormais
  `ENDPOINTS_A_READER_CANNOT_FOLLOW`, déclarée par les modules qui détiennent les
  points d'entrée, et elle est vérifiée sur les exemples autant que sur le
  catalogue — la surface que la première version n'a jamais regardée, et où le
  défaut avait été recopié vingt-deux fois.
- `STANDARDS.md` avait *décrit* ce défaut et s'en était convaincu : la réponse
  d'Ember était « peu utile mais vraie ». Elle n'est pas vraie. Une citation
  affirme que la figure est vérifiable là, et rien n'est vérifiable derrière un
  403.

### Un rafraîchissement lit maintenant Ember sans clé, et dit laquelle des deux moitiés a répondu

- `saggio catalog refresh grid --column carbon` lit par défaut le jeu de données
  publié. Une clé reste utilisée quand on en offre une, et l'exécution imprime
  laquelle des deux a répondu plutôt que de le laisser déduire du fait que ça a
  marché.
- Ce n'est pas la substitution que ce module refuse. Celle qui est refusée est
  une *mesure différente* portant les mêmes unités — l'intensité **de cycle de
  vie** d'Our World in Data là où cette colonne contient les émissions
  **d'exploitation** — et ce refus est intact. Le jeu de données d'Ember a été
  confronté à l'API pays par pays avant d'être adopté : 36 des 38 concordaient à
  mieux d'un demi pour cent, trente à mieux d'un dixième, plusieurs à trois
  décimales.
- Pourquoi cela compte au-delà du confort : une colonne que seul un détenteur
  d'identifiants peut relire est une colonne qu'on cesse de relire, et ce qui se
  passe à la place est que quelqu'un pousse la date. C'est le seul résultat que
  tout ce mécanisme existe pour empêcher.
- `--api-key` et `EXAMPLES.md` / `EXEMPLES.md` disaient qu'une clé était
  nécessaire. Les deux disent maintenant ce qui est vrai, et `--year` dit que
  l'année la plus récente n'est pas la même année pour tous les pays.

### Le chiffre 2022 de l'Ukraine partait estampillé 2025

- Les deux pays qui ne concordaient *pas* dans cette vérification sont la partie
  intéressante. L'**Ukraine** correspondait à la valeur **2022** d'Ember à trois
  décimales — 250,5 contre 250,525 — alors que sa ligne disait
  `carbon_data_year: 2025`.
- La cause tenait en une ligne. Le rafraîchissement prenait l'année de données la
  plus récente parmi les trente-huit pays et l'apposait sur chaque ligne. Ember
  publie la plupart des pays jusqu'en 2025 et l'Ukraine seulement jusqu'en 2022 :
  la seule ligne que la source n'avait pas rattrapée revendiquait donc une
  actualité qu'elle n'avait pas. Rien dans le nombre ne pouvait le montrer :
  250,5 est une intensité sans relief, et l'estampille était le seul endroit où
  l'écart de trois ans allait jamais apparaître.
- Chaque ligne porte désormais **sa propre** année de données, et un
  rafraîchissement nomme les pays que la source n'a pas rattrapés au lieu de les
  enfouir dans un maximum.
- La **Belgique** était l'autre : 125,8 en fichier contre 151,3 publié, une
  révision de 20 % à la hausse à l'intérieur de la fenêtre de fraîcheur d'un
  mois. Pas un défaut : un rappel que la fenêtre est une borne supérieure sur
  l'ancienneté, pas une garantie d'exactitude. Les chiffres de huit pays ont
  bougé à cette relecture et les huit sont maintenant à jour.

### Un TPU v4 a une empreinte, et quatre autres TPU n'en ont délibérément pas

- Google a publié une ACV du berceau à la sortie d'usine de cinq générations de
  TPU ([arXiv:2502.01671](https://arxiv.org/abs/2502.01671), ISO 14040/14044) :
  le premier chiffre de fabrication d'un accélérateur d'IA venu de ceux qui l'ont
  conçu, modélisé à partir du nœud, de la taille de puce et du rendement que
  personne à l'extérieur ne détient. Son tableau 1 sépare les émissions propres à
  l'accélérateur de celles du processeur hôte et du centre de données, ce qui est
  la frontière que les autres lignes d'accélérateur de ce catalogue utilisent
  déjà.
- `TPU-v4` porte **366,0 kgCO2e** par puce, HBM comprise, hôte et bâtiment exclus
  et nommés. La huitième empreinte du catalogue, et le quatrième accélérateur.
- Le même article donne v4i, v5e, v6e et v5p, et ils ne sont **pas** ajoutés. Il
  ne publie aucun chiffre de puissance du genre que chaque ligne porte ici :
  `tdp_w` est une valeur de fiche technique et ce que l'article contient est une
  moyenne mesurée sur une flotte en production. Un meilleur nombre pour estimer
  l'énergie, une grandeur différente, et mettre l'un sous le nom de l'autre
  ferait dire deux choses à la colonne.
- Une petite confirmation qui vaut d'être notée : la spécification du v4 donnée
  par l'article — 275 TFLOP/s BF16, 32 Gio — est ce que la ligne disait déjà
  d'après la documentation de Google. Deux lectures de la même pièce qui
  concordent sont la seule raison de croire que l'empreinte appartient à cette
  ligne.

### Six pages citaient un décompte du catalogue et rien ne le vérifiait

- « Trois accélérateurs sur 25 lignes et quatre processeurs sur 12 » apparaît
  dans `README.md`, `LISEZMOI.md`, `STANDARDS.md`, `NORMES.md`, `LANDSCAPE.md` et
  `PAYSAGE.md`. Ajouter une ligne à `hardware.yaml` rend les six fausses d'un
  coup, et aucun test ne regardait — la même forme que la préface de version qui
  disait « vingt et une entrées » au-dessus de vingt-trois.
- Un test de contrat lit maintenant les décomptes dans la prose, dans les deux
  langues et les deux formulations, et les compare au catalogue. `CHANGELOG.md`
  en est exempté exprès : ses anciennes entrées disent *sept empreintes* et
  doivent continuer de le dire, parce qu'elles décrivent une version où c'était
  vrai.

### Trois tests atteignaient le réseau et l'un d'eux passait grâce à ça

- Trouvé en changeant la fonction que le rafraîchissement carbone appelle. Un
  test qui bouchonnait le chemin de l'API laissait le chemin sans clé libre de
  télécharger le vrai fichier de trente mégaoctets — et **tombait d'accord avec
  lui**, parce que le vrai chiffre pour la France se trouvait être le nombre que
  le test avait écrit.
- Les deux chemins sont bouchonnés ensemble désormais, par un seul utilitaire,
  pour qu'aucune branche ne puisse atteindre une socket quelle que soit celle que
  l'environnement choisit.

### Un fichier Word et un PDF disent ce qui les a produits, et quand

- Le bloc de titre d'un `docx` et d'un `pdf` nomme maintenant **saggio** comme
  auteur et porte la date de production du document. Avant cela, les deux étaient
  vides : un lecteur tenant le PDF n'avait aucun moyen de savoir s'il avait été
  écrit par une personne ou engendré, ni quand.
- La date n'est délibérément **pas** celle qui figure déjà dans le corps. *Dernière
  mise à jour* est un fait sur le modèle — quand quelqu'un y a changé un nombre
  pour la dernière fois — et le bloc de titre est un fait sur le fichier. Un
  document produit aujourd'hui depuis un modèle intouché depuis juin énonce les
  deux, et c'est tout l'enjeu : un chiffre périmé ne doit pas acquérir une date
  d'apparence fraîche en étant exporté à nouveau. Un test tient les deux
  séparées.
- `--author` met un autre nom sur un livrable client, `--generated` énonce la
  date mot pour mot (`2026-Q2`, `remis le 14 mars`), et ne passer aucun auteur
  retire la ligne sans emporter la date avec elle.

### La conversion peut recevoir l'ordre de refuser le réseau

- Trouvé en lisant ce que le convertisseur fait vraiment : depuis sa 2.5.0, il
  va chercher un gabarit de marque en HTTP dès qu'aucun document de référence
  n'est donné. C'est un défaut d'usage agréable et surprenant : un rendu échoue
  dans un train, et deux rendus d'un même modèle peuvent différer parce qu'un
  gabarit a bougé.
- Ni l'un ni l'autre n'est un défaut, et ni l'un ni l'autre n'était déclaré.
  `--offline` refuse maintenant toute étape qui touche au réseau, et le
  comportement sans l'option est écrit plutôt que laissé à découvrir.

## 1.4.2 — 2026-10-04

La première version publiée sur un index de paquets, et celle dont la longue
description y fonctionne.

### Le logo d'en-tête pointe vers un hôte qui sert des images

- `README.md` est la longue description, et un index la rend donc comme page du
  projet. Son logo d'en-tête était une balise HTML `<img>` à source **relative**,
  qui sur un index se résout contre le domaine de l'index et ne montre rien.
- La passe de liens absolus de la 1.4.1 était passée à côté, parce que le
  contrôle qui avait trouvé ceux-là lisait la syntaxe de lien Markdown et qu'une
  balise `<img>` n'est pas de la syntaxe de lien Markdown. Le contrat lit
  maintenant toutes les formes qu'une référence peut prendre — lien, `src`,
  `href`, et l'écriture par référence.
- Les images cachent un second piège : sur la forge, `blob/` répond une page
  HTML et seul l'hôte brut répond les octets de l'image. Les deux ont été
  mesurés — 225 Ko de `text/html` contre 3,2 Mo d'`image/png` — avant de choisir,
  parce qu'une réécriture vers `blob/` aurait été absolue et toujours cassée.
- C'est une version séparée plutôt qu'une correction repliée dans la 1.4.1 parce
  que la longue description est cuite dans les métadonnées : la livrer sous ce
  numéro aurait mis sur l'index un contenu que la balise `1.4.1` ne contient pas.
  C'est le défaut que la 1.4.1 elle-même avait été taillée pour cesser de
  répéter.

### Une balise malformée dont aucun moteur de rendu ne s'est plaint

- La réparation ci-dessus est partie une fois avec la balise abîmée : un
  guillemet égaré, les attributs qui le précédaient disparus. Elle était correcte
  à l'écriture et correcte au rendu ; elle ne l'était pas au moment d'être
  indexée, et rien entre les deux n'a regardé à nouveau.
- À savoir pour qui se repose sur `twine check` : le moteur de rendu a
  **accepté** la balise malformée sans un mot et a silencieusement jeté les
  attributs qu'il ne savait pas lire. La page aurait rendu un logo simplement
  mal fichu, sans qu'aucun outil nulle part ne signale de faute.

## 1.4.1 — 2026-10-04

Une version qui contient ce que ses notes décrivent, ce que la 1.4.0 ne faisait
pas.

### La 1.4.0 avait été étiquetée avant le travail que ses notes revendiquaient

- L'étiquette avait été posée sur un commit dont l'intégration continue
  **échouait**, et les deux sections qui ouvraient ses notes décrivaient des
  commits arrivés après elle. Quiconque installait cette étiquette n'avait ni
  l'un ni l'autre.
- Rien n'a été déplacé ni réécrit pour le cacher : l'étiquette reste où elle est,
  les deux sections descendent ici pour se tenir à côté des commits qu'elles
  décrivent, et cette entrée dit ce qui s'est passé. Un projet qui demande à
  chaque figure de déclarer jusqu'où on peut lui faire confiance n'a pas le droit
  de repointer discrètement une version.
- Sa propre préface l'avait déjà remarqué, sans que personne la lise : elle
  annonçait vingt et une entrées et en portait vingt-trois. Déplacer les deux qui
  ne lui appartenaient pas rend la phrase vraie plutôt que d'avoir à la corriger.

### Une mesure n'est pas promise sur une machine qui ne peut pas en prendre

- Le parcours de bout en bout de `--run` exigeait qu'un temps d'exécution revienne
  **mesuré**. Cela tient sur un portable, où la tranche s'exécute vraiment, et
  cela a échoué sur le runner d'intégration continue, où rien ne pouvait
  consentir à exécuter le code de quelqu'un et où le temps est resté ouvert. Le
  runner avait raison.
- Laisser un temps d'exécution ouvert est la bonne réponse sur une machine qui ne
  peut pas, ou n'a pas le droit de, mesurer. Le parcours vérifie maintenant la
  promesse qui tient dans les deux cas : un temps mesuré porte un nombre positif
  et une note nommant ce qui a été chronométré, et un temps ouvert ne porte aucun
  nombre.
- Il prend **les deux** branches exprès plutôt que celle que la machine offre :
  une fois avec l'entrée standard fermée et un répertoire personnel à lui, ce
  qui est la façon dont un job planifié et un conteneur l'invoquent et qu'aucun
  consentement ne peut atteindre, et une fois normalement.

### Les liens du README survivent à une republication

- Quatorze liens de `README.md` étaient relatifs. C'est aussi la longue
  description du paquet, et un index la rend sur son propre domaine, où
  `](EXAMPLES.md)` se résout vers une page qui n'a jamais été là. Chacun d'eux
  fonctionne dans un clone et sur la forge ; ils n'auraient cassé que sur la
  seule surface que personne ne regarde.
- Ils sont absolus désormais, et un test de contrat refuse un lien relatif dans
  ce seul fichier. Les autres documents gardent les leurs : ils sont lus là où ils
  vivent, où un lien relatif est celui qui survit à un fork.
- Trouvé en construisant la roue, en l'installant dans un environnement vide hors
  du dépôt, et en y lançant les parcours — ce qui a aussi confirmé que les douze
  fichiers de catalogue et de gabarit partent bien, et que le script de console
  rapporte la version que les métadonnées déclarent.

### Moins de tests, davantage de fonctionnels, et un job deux fois plus court

- **2 174 cas deviennent 1 701**, sans que rien cesse d'être vérifié. Trois
  règles de catalogue étaient paramétrées sur les 111 lignes et une règle de
  documentation sur les 152 commandes : 333 et 152 cas disant chacun la même
  phrase à propos d'une clé différente. Rassemblées, chacune devient un test qui
  parcourt tout et **nomme tous les fautifs dans un seul échec**, ce dont a
  besoin celui qui les corrige, plutôt que la ligne où pytest s'est arrêté.
- **Huit parcours fonctionnels** ajoutés, à travers la ligne de commande telle
  qu'un shell l'exécute : démarrer un modèle, auditer puis rendre puis lire,
  faire échouer un modèle menteur, transformer un temps ouvert en temps mesuré,
  faire échouer une barrière de dérive, produire un rapport HTML qui ne va rien
  chercher, distinguer une erreur d'usage d'un verdict par le code de sortie, et
  rapporter la fraîcheur pour le job hebdomadaire. Tout le fichier tourne en
  **11 secondes**, et vider le validateur ou aplatir un code de sortie fait
  échouer le parcours qui porte son nom.
- **`python -m saggio` fonctionne désormais.** Le paquet avait un script de
  console et pas de `__main__`, et répondait donc *« 'saggio' is a package and
  cannot be directly executed »*, ce qui se lit comme un outil cassé plutôt que
  comme un fichier manquant. Trouvé parce que les tests fonctionnels doivent
  exécuter *cet* arbre de travail plutôt que ce qui traîne dans le PATH.
- Le job lance `pytest -n auto`. Tous les tests tournent toujours ; ils sont
  répartis sur les cœurs du runner. **144 secondes à 53** en local, et cela reste
  court à mesure que la suite grandit, ce qui est la seule façon qu'une barrière
  reste quelque chose qu'on attend.

### Un test qui ne tournait que sur le Python de l'auteur

- Le contrat ajouté dans cette version pour tenir `pyproject.toml` contre
  `__version__` attrapait `tomllib`, qui **est arrivé en 3.11**. Ce paquet
  supporte 3.10, et l'intégration continue tourne en 3.10 précisément parce que
  c'est la version la plus susceptible de refuser quelque chose. Elle a refusé
  ceci, sur le commit qui l'ajoutait : vert sur un portable en 3.13, rouge au
  plancher de la plage supportée.
- Il lit la version avec une expression étroite désormais, cantonnée à la table
  `[project]`, pour qu'une version épinglée pour une dépendance plus bas ne
  puisse pas être prise pour celle du paquet. Vérifié en 3.10 et en 3.13 avant
  d'être poussé.

## 1.4.0 — 2026-10-04

Vingt et une entrées accumulées sous le titre précédent avant que quiconque
s'arrête pour tailler une version. Rien ici ne casse quoi que ce soit. Deux
affirmations de la 1.3.0 ont été corrigées au passage, et ces corrections sont
décrites ci-dessous plutôt que repliées discrètement dans le texte plus haut :
*Une dérivation est vérifiée* n'était close que pour les formes contre
lesquelles elle avait été testée, et la provenance du catalogue était honnête
par ligne avant de l'être par colonne.

### Le catalogue de réseaux est d'un seul millésime, d'une seule source

- Les 38 intensités nationales sont rafraîchies depuis l'API d'Ember, année de
  données 2025. Chaque ligne porte désormais ses propres `carbon_source_url`,
  `carbon_retrieved_date` et `carbon_data_year` plutôt que d'hériter de ceux de
  la ligne : la figure carbone et le tarif à côté d'elle ne viennent pas du même
  endroit et ne bougent pas ensemble.
- Confronter d'abord les anciens chiffres à la série complète d'Ember, année par
  année, pour confirmer que le catalogue avait simplement un an de retard, a
  montré qu'il n'en avait pas. Les valeurs commitées correspondaient le mieux à
  des années Ember éparpillées de 2000 à 2025, et **huit pays ne correspondaient
  à aucune année d'Ember à 8 % près**. La Suède était à 13 gCO2e/kWh là où le
  chiffre le plus bas qu'Ember ait jamais publié pour elle est 34,91. Chaque
  ligne citait Ember. Un `source_url` qui ne contient pas le nombre posé à côté
  de lui est exactement l'échec contre lequel ce paquet existe.
- `DeploymentContext.grid_intensity` lit la provenance du carbone plutôt que
  celle de la ligne. Sans cela, il rapportait un chiffre d'API lu aujourd'hui
  sous l'URL et la date d'une page web lue le mois dernier — une fausse
  provenance introduite par le commit même qui corrigeait les nombres.
- `saggio catalog refresh grid` envoyait `is_aggregate_series`, qui n'est pas un
  paramètre de cette API ; le schéma publié l'écrit `is_aggregate_entity`. Les
  paramètres de requête inconnus sont ignorés plutôt que refusés, si bien que le
  filtre que le code croyait poser n'a jamais été posé.
- Les deux modèles du parcours guidé avaient une figure carbone dérivée de
  l'ancienne intensité. La vérification arithmétique ajoutée dans cette même
  version les a attrapés tous les deux, nommément et avec la bonne réponse à
  côté, ce pour quoi elle a été écrite.

### Une section Sources qui n'est que la plupart des sources

- `STANDARDS.md` et `NORMES.md` citaient **trois sources dans leur corps que la
  liste des sources ne nommait pas** : l'article du modèle paramétrique, son jeu
  de données, et la méthode d'empreinte de processeur que les quatre lignes de
  CPU désignent. Les trois avaient été ajoutées à la page en deux jours sans que
  personne retourne à la liste.
- Un lecteur qui vérifie la liste et n'y trouve rien sur les empreintes de
  processeur en conclut qu'elles ne reposent sur rien, ce qui est pire que pas de
  liste du tout. Corrigé dans les deux langues, et tenu par un test de contrat
  qui échoue en nommant l'URL.
- Deux adresses de la spécification SCI répondent toutes les deux et aucune ne
  redirige vers l'autre : elles sont donc déclarées comme une même source plutôt
  que devinées telles — une règle qui devinerait cacherait de vrais oublis
  derrière une heuristique.
- Trouvé en regardant la page rendue plutôt qu'en lisant le Markdown.

### Une dérivation qui tourne en rond est signalée

- L'auto-référence directe était attrapée ; **un cycle passant par un
  intermédiaire ne l'était pas**. Deux hypothèses se dérivant l'une de l'autre
  validaient proprement, sans erreur ni avertissement. La règle du maillon faible
  suppose qu'une chaîne peut être remontée jusqu'à un fait, et un cycle n'a pas
  de fond : le paquet calculait un statut à partir de rien et l'énonçait aussi
  sûrement que le reste de la page.
- Trouvé par une sonde adverse contre des formes non essayées aux tours
  précédents, et confirmé en imprimant le rapport entier plutôt qu'en le
  filtrant. Les cycles de deux, trois et cinq pas sont maintenant signalés, y
  compris un atteint depuis l'extérieur et deux cycles distincts dans un même
  modèle, et le message nomme le cycle **dans l'ordre où un lecteur le
  suivrait**.
- Un losange, une longue chaîne honnête et une entrée nommée deux fois restent
  silencieux : un parcours qui marquerait un nœud *visité* plutôt qu'*en cours de
  visite* appellerait cycle tous les losanges.

### Une citation qu'un lecteur suit ne doit pas lui montrer un autre nombre

- `source_url` existe pour qu'un lecteur puisse vérifier la figure posée à côté.
  Deux des sources sont des API, et elles répondent différemment à un lecteur et
  à un programme : Ember renvoie `{"detail":"No API key set"}`, peu utile mais
  vrai, tandis que **Boavizta renvoie 19,0 kgCO2e** — la valeur par défaut pour
  une puce non nommée, et la figure exacte que ce paquet refuse à l'import.
  Quatre lignes de processeur la citaient, si bien que quiconque cliquait voyait
  un nombre sans rapport avec le processeur de cette ligne.
- Ces lignes citent désormais la page qui explique la méthode, et nomment le
  point d'entrée qui les a calculées dans leur portée, où c'est de la provenance
  et non une invitation. Un test de contrat refuse ce point d'entrée dans tout
  champ qu'un lecteur suit, et le remettre fait échouer le test en nommant la
  ligne.
- **Introduit par le commit qui a séparé la provenance par colonne** : les champs
  ont été rendus honnêtes et les liens n'ont jamais été suivis comme un lecteur
  les suit.

### Les empreintes incorporées sont recoupées avec un jeu de données indépendant

- Le jeu de données que la version précédente attendait a été publié :
  [Zenodo 10.5281/zenodo.20321644](https://doi.org/10.5281/zenodo.20321644),
  CC-BY-4.0, 174 cartes NVIDIA de 2013 à 2024, issu de
  [arXiv:2607.01258](https://arxiv.org/abs/2607.01258). Il a été récupéré et la
  comparaison a été faite.
- **A100 : 127,6 ici, 123,2 là-bas — 3,4 % d'écart.** Deux méthodes ne partageant
  aucune entrée — un démontage avec analyse élémentaire primaire, et un modèle
  paramétrique partant de la surface de puce et de la mémoire — qui tombent aussi
  près, c'est la meilleure preuve disponible que la seule figure non issue d'un
  constructeur du catalogue est à peu près juste.
- **H100 : 164,0 ici, 196,5 là-bas — 19,8 % d'écart.** L'article l'explique
  lui-même : il estime la mémoire plus haut que NVIDIA, depuis une autre base
  d'analyse de cycle de vie, et le processeur et la carte plus bas. La figure du
  constructeur est conservée — vérifiée par un tiers sous ISO 14067, sur la pièce
  exacte — et `STANDARDS.md` dit maintenant qu'une estimation indépendante
  crédible la place un cinquième plus haut, parce qu'un lecteur qui cite 164
  mérite de le savoir.
- Le jeu de données est une **vérification, pas une source**, pour la même raison
  qu'Eurostat vérifie les tarifs au lieu de les fournir. Rien dans le catalogue
  n'en vient.
- L'appariement s'est fait sur des **noms de produits exacts**. La première
  tentative appariait sur des sous-chaînes et mariait `L4` avec `L40`, `T4` avec
  `T400` et `P100` avec `Quadro GP100` — le même échec d'appariement approximatif
  que ce paquet a refusé à Boavizta deux versions plus tôt, presque répété à la
  main.

### La sortie Word et PDF est testée sans Word ni moteur PDF

- `report/office.py` **56 % → 100 %**, le dernier module du paquet qui était
  notablement bas. Tout ce qui s'y trouve et qui n'est pas une garde d'une ligne
  se passe autour d'un sous-processus, et rien de tout cela ne s'exécute si
  `md2star` et Pandoc ne sont pas installés : sur la plupart des machines, et sur
  le runner, toute la conversion ne s'exécutait donc jamais.
- Un `md2star` de remplacement est écrit à la place : un vrai exécutable qui
  prend les vraies options, écrit un vrai fichier ou échoue comme le vrai échoue.
  Le sous-processus est réel et l'arithmétique est celle qui est livrée.
- Tenu désormais : le gabarit maison atteint le convertisseur sous
  `--reference-doc` et est absent quand aucun n'est donné ; le Markdown de
  travail est nettoyé ; le répertoire de sortie est créé plutôt qu'exigé ; un
  convertisseur bloqué est abandonné en le nommant et en disant au bout de
  combien de secondes ; et **un échec qui ne dit rien produit quand même un
  message**. Ce dernier point n'est pas hypothétique : le code porte un
  commentaire disant qu'une fin de sortie vide avait un jour fait planter le
  messager au lieu de le laisser délivrer son message, et retirer la garde
  reproduit l'`IndexError` exact.

### Les échantillonneurs sont testés, fils d'exécution et sous-processus compris

- `power/graphics.py` **65 % → 100 %** et `power/accelerator.py` **69 % → 86 %**.
  Les deux abritent un échantillonneur, et un échantillonneur est la seule chose
  de ce paquet dont personne ne peut vérifier l'arithmétique en la regardant :
  un fil, un fichier et une moyenne.
- Rien n'est simulé. Les tests graphiques écrivent un vrai fichier de capteur et
  **changent son contenu pendant que le fil tourne**, ce qui est ce qui prouve
  que la figure est une moyenne et non la dernière lecture. Les tests
  d'accélérateur écrivent un **`nvidia-smi` de remplacement** — un vrai
  exécutable qui imprime ce que le vrai imprime, pour les mêmes options — et
  laissent le vrai sous-processus, le vrai fichier de journal et l'arithmétique
  livrée faire le reste.
- Quatre affirmations qui n'étaient vérifiées nulle part, et que des tests
  portant leur nom tiennent désormais : la figure est une **moyenne**, pas la
  dernière ni la plus haute lecture ; un échantillon illisible est **sauté**,
  jamais compté comme un zéro ; un nœud à deux cartes tire **deux fois** la
  puissance d'une carte ; et une moyenne faite de trop peu de lectures n'est
  **pas une figure du tout** plutôt qu'une figure maigre. Chacune a été vérifiée
  en la cassant exprès et en regardant le bon test échouer.
- **Un test avait tort et le code avait raison** : il attendait que
  l'échantillonneur d'accélérateur saute `[N/A]` dans un flux, alors qu'une carte
  qui répond `[N/A]` annule la requête *avant* qu'aucun échantillonneur démarre.
  Le remplaçant répond maintenant séparément à une requête ponctuelle et à un
  flux, ce que fait aussi un vrai pilote quand une carte sort d'un flux auquel
  elle répondait un instant plus tôt.
- La durée est scrutée, jamais dormie : un test réglé sur la vitesse d'une
  machine échoue sur une autre sans que personne puisse rien en faire. Les deux
  fichiers ont été relancés plusieurs fois pour chercher de l'instabilité avant
  d'être commités.

### La détection du matériel est exercée sur du matériel que cette machine n'est pas

- `machine.py` **72 % → 98 %** et `capability.py` **78 % → 87 %**. Presque
  chaque branche de la détection est une branche qui ne correspond *pas* : un
  processeur que personne n'a catalogué, deux accélérateurs différents dans une
  même machine, une machine qu'on ne peut pas inspecter du tout. Rien de cela
  n'arrive sur le portable d'un développeur ni sur un runner, si bien que les
  chemins qui comptent le plus pour quelqu'un au matériel inhabituel étaient les
  moins exercés.
- Rien n'est simulé. Chaque test fournit le dictionnaire que `hardware_info()`
  renvoie réellement, **pris d'un appel vivant** plutôt qu'imaginé, et laisse le
  vrai code le lire. Le premier jet passait les noms de GPU comme des chaînes ;
  le code lit des tables de correspondance, et l'échec l'a dit.
- Une arborescence hwmon graphique est construite comme le noyau en publie une,
  ce qui relève aussi la sonde de capacités : un compteur qui se lit, un capteur
  que cet utilisateur n'a pas le droit de lire, et un nœud appartenant à un
  ventilateur plutôt qu'à une carte. **Absent et bloqué sont deux réponses
  différentes** — les confondre enverrait quelqu'un chercher du matériel qu'il a
  déjà.
- **Un commentaire de la détection énonçait un mécanisme qui n'existe pas.** Il
  disait qu'une surcouche pouvait retirer les lignes de processeur génériques, et
  la branche en dessous était écrite pour cela. Une surcouche fusionne *par
  dessus* le catalogue livré : elle peut ajouter ou remplacer une ligne, jamais
  en supprimer une. Le commentaire dit maintenant ce qui est vrai, la branche est
  atteinte par le seul chemin qui l'atteint, et un test de contrat garde les
  lignes de repli dans le catalogue — elles sont faciles à supprimer en faisant
  le ménage, parce que rien ne les nomme à part le repli qui en a besoin.

### Les commandes de rafraîchissement sont testées sur la moitié qu'un utilisateur voit

- `commands.py` était à **73 %**, pas aux 76 % que l'évaluation revendiquait, et
  l'ombre se concentrait dans les quatre gestionnaires ajoutés le même
  après-midi : `_refresh_embodied` couvert à 46 %, `catalog_refresh` à 73 %,
  `_check_timezones` à 79 %. Le téléchargement était bouchonné et testé ; **ce
  qu'un utilisateur lit vraiment ne l'était pas**.
- Neuf tests le couvrent désormais : ce que chaque commande imprime, chaque refus
  qu'elle nomme, l'URL de recoupement que le rafraîchissement des tarifs doit
  porter, la ligne `Read-only` qui empêche un lecteur de croire que le catalogue
  a déjà bougé, et la seconde étape délibérée qui écrit. 73 % → **83 %**.
- Parmi eux, le seul cas où un rafraîchissement *échoue* au lieu de rapporter :
  une liste de fuseaux horaires qui n'a pas été confirmée n'est pas estampillée,
  et le test exige que le fichier soit identique octet pour octet ensuite.
- **`commands.py` n'a pas été découpé**, et c'est une décision plutôt qu'un
  oubli. Les quatre fichiers découpés cette semaine mêlaient chacun des
  préoccupations sans rapport ; celui-ci n'en a qu'une — implémenter les verbes —
  et il est long parce que la ligne de commande en a beaucoup. Découper une liste
  plate de vingt-deux gestionnaires ajouterait de la plomberie d'import et un
  cinquième tour de valse des cibles de patch pour aucun gain de comportement. La
  couverture était le défaut ; la longueur est cosmétique.

### Le rafraîchissement, c'est quatre sources, donc quatre modules

- `refresh.py` avait atteint 1 213 lignes, parti de 424 le matin même. Les trois
  sources ajoutées en un seul après-midi y étaient chacune entrées sans que
  personne regarde ce que le fichier devenait — nommé dans la version précédente
  plutôt que corrigé en douce, et corrigé ici.
- Quatre modules, un par source : `carbon` (Ember), `tariffs` (le prix et son
  recoupement Eurostat), `timezones` (IANA), `embodied` (empreintes de
  processeur). Ils ne partagent **rien** : pas une constante, pas un utilitaire,
  pas un type d'enregistrement. Chacun détient les trois mêmes choses — ce que la
  source a dit, comment la lui demander, comment écrire la réponse dans un
  catalogue — et chacun porte la raison pour laquelle c'est cette source-là
  plutôt qu'une plus commode.
- **Le témoin était aveugle à son premier essai**, et c'est la partie qui vaut
  d'être gardée. Saboter la comparaison de noms de puces — retirer le tiret bas
  des caractères qu'elle ignore — n'a rien changé à ce que la référence mesurait,
  parce qu'aucun cas de la sonde n'utilisait de tiret bas. La sonde a été élargie
  pour exercer chaque séparateur séparément, et c'est seulement alors qu'elle a
  attrapé le sabotage. Une référence qui ne peut pas échouer ne prouve rien, et
  celle-ci ne le pouvait pas tant qu'on ne le lui avait pas demandé.
- Onze cibles de patch réacheminées encore, la quatrième fois en trois
  refactorisations : un test qui importe le paquet ne peut pas patcher une
  liaison qui vit dans un sous-module.
- Le plus long fichier du paquet est maintenant `html.py`, à 1 168 lignes.

### Le wattmètre est un paquet, et le dernier fichier long a disparu

- `power.py` faisait 1 227 lignes : 28 constantes et 20 symboles couvrant quatre
  interfaces matérielles différentes. Désormais `saggio/analyze/power/`, neuf
  modules, découpés selon **d'où vient l'énergie** plutôt que selon la nature de
  chaque symbole — ce qui est la structure que le problème a vraiment, puisque
  chaque interface a ses unités, son mode d'échec et sa portée propres :
  `tables`, `sysfs`, `rapl`, `accelerator`, `graphics`, `soc`, `reading`,
  `meter`.
- **Comportement identique**, contre une référence capturée avant la première
  coupe et validée d'abord en divisant une figure par deux exprès et en
  confirmant qu'elle s'en apercevait.
- La leçon du monkeypatch pour la troisième fois, et plus coûteuse ici : **28
  cibles de patch** dans trois fichiers de test, nommant toutes
  `saggio.analyze.power.<x>` pour des noms qui vivent maintenant dans des
  sous-modules. Un patch sur la ré-exportation du paquet n'atteint pas le module
  qui a importé le nom. Parmi elles, une que j'avais écrite moi-même la semaine
  passée.
- Les trois fichiers que l'évaluation nommait sont faits : `auditor.py` 1 319 →
  9 modules, `static.py` 1 649 → 10, `power.py` 1 227 → 9. Les trois ont été
  vérifiés de la même façon, et **la méthode vaut plus que le résultat** :
  capturer ce que la chose fait avant d'y toucher, prouver que la capture peut
  échouer, puis découper sur l'arbre syntaxique plutôt qu'à la main.
- **Le message de commit de celui-ci en revendiquait trop**, et la correction a
  sa place ici plutôt que dans un force-push. Il disait qu'aucun fichier du
  paquet ne dépassait mille lignes. Cinq le font : `refresh.py` 1 213,
  `html.py` 1 168, `commands.py` 1 151, `run.py` 1 117, `markdown.py` 1 001.
- Pire, **`refresh.py` est passé de 424 lignes à 1 213 aujourd'hui, de cette
  main** : le rafraîchissement des prix, la vérification des fuseaux et le
  lecteur de carbone incorporé, chacun ajouté sans regarder ce que le fichier
  devenait. Trois fichiers longs découpés pendant qu'un quatrième devenait le
  plus long du paquet. Il est sur la liste maintenant, mesuré plutôt que rappelé
  de mémoire.

### Deux exemples de plus, et les deux défauts qu'ils ont trouvés

- La galerie gagne **detectron2**, le premier exemple lu comme de
  l'**inférence** — l'archétype qui compte le plus pour qui tarife une requête,
  et celui que les six précédents n'exerçaient jamais — et **xberg**
  (anciennement Kreuzberg), un moteur d'intelligence documentaire dont le cœur
  est en Rust : 2 278 fichiers Rust, 435 Java, 400 C#, 391 Kotlin et 143 Python.
  **Tous les autres exemples ici sont en Python**, c'est donc la prétention à la
  largeur démontrée sur un dépôt qui aurait pu la mettre en défaut.
- **La règle de détection des suites de tests avait une forme Python et
  JavaScript** : `tests/`, `test_*.py`, `*.test.ts`. Rust met ses tests dans un
  *fichier* nommé `tests.rs`, si bien que dix identifiants de modèles nommés
  `test-model` et `mock-model` sont arrivés sans la moindre réserve. Elle
  reconnaît maintenant une suite quelle que soit la langue dans laquelle elle est
  écrite — et refuse `latest.rs`, `contest.py` et `protest.go`, qu'un premier
  essai plus lâche avait ramassés avant qu'une sonde l'attrape.
- **Un exemple n'est pas non plus la charge de travail.** Le paquet refusait déjà
  de prendre la durée d'un entraînement dans une configuration d'évaluation ; le
  même raisonnement n'avait jamais été appliqué à ce que le code *appelle*. Un
  modèle nommé dans `examples/` ou `benchmarks/` porte désormais une réserve qui
  le dit. Auditer vLLM est ce qui l'a montré : 333 identifiants de modèles dans
  150 fichiers, 127 d'entre eux venant de ces répertoires. Le signal est passé de
  152 identifiants sans réserve à 17.
- vLLM lui-même n'est **pas livré** : son modèle fait 162 Ko, dont 95 % sont une
  liste que personne ne lira. Le constat est dans la galerie, le fichier n'y est
  pas, et la page le dit plutôt que de laisser passer l'omission.
- **Un défaut nommé plutôt que caché** : Rust garde ses tests unitaires à
  l'intérieur du fichier qu'ils testent, dans un bloc `#[cfg(test)] mod tests`.
  Une détection au niveau du fichier ne voit pas dedans, si bien que des
  fixtures apparaissent encore à côté des vrais `openai/gpt-4o` et
  `anthropic/claude-sonnet-4-20250514` que xberg appelle réellement.

### Le lecteur statique est un paquet lui aussi

- `static.py` faisait 1 649 lignes — le registre en annonçait 1 584, encore une
  figure périmée — réparties sur 27 symboles et **26 constantes éparpillées dans
  le fichier**, certaines au-dessus de la première fonction, d'autres entre les
  deux dernières. Cet éparpillement était l'essentiel du problème : un lecteur
  qui demande « pourquoi a-t-il décidé cela » demande presque toujours après une
  table, et devait partir à la chasse.
- Désormais `saggio/analyze/static/`, dix modules, le plus gros à 350 lignes :
  `tables`, `walking`, `findings`, `languages`, `archetype`, `worksize`,
  `calls`, `running`, `read`. Chaque chemin d'import se résout comme avant.
- Les tables vivent ensemble et à l'écart du code qui lit avec elles.
  `FRAMEWORK_PATTERNS` est construite plutôt qu'écrite, donc la petite fonction
  qui la construit s'y trouve aussi : elle fabrique une table plutôt que d'en
  lire une.
- **Vérifié contre une référence de comportement**, et la référence a été
  vérifiée elle-même : casser un détecteur exprès la changeait, ce qui est ce qui
  prouve qu'un témoin n'est pas aveugle. Après le découpage, la seule différence
  sur quinze sondes était le décompte de fichiers Python de ce dépôt, 94 → 103 :
  les dix modules ajoutés moins celui retiré, c'est-à-dire le lecteur rapportant
  correctement un dépôt qui a changé plutôt qu'un lecteur qui a changé.
- La première passe d'extraction coupait l'en-tête au premier `def` et perdait
  toutes les constantes en dessous. Refaite sur l'**arbre syntaxique**, qui
  trouve une affectation de premier niveau où qu'elle soit, avec une assertion
  que rien n'est resté sans place.
- Quatre doctests de plus rendus autonomes, la même leçon que pour l'auditeur :
  un exemple qui s'appuie sur l'espace de noms de son module casse à l'instant où
  le module bouge.

### Le job de fraîcheur prévient avant l'échéance, pas après

- Le job planifié lançait `saggio catalog freshness` tout court. Cela imprime
  « chaque ligne du catalogue est dans sa fenêtre de rafraîchissement » tous les
  lundis jusqu'à la semaine où les lignes expirent, et échoue seulement alors :
  **un avertissement après l'échéance**, ce qui n'est aucun avertissement pour
  une figure que quelqu'un s'apprête à citer. Il passe maintenant `--within 21` :
  quatre lundis de préavis, chacun portant la commande de rafraîchissement déjà
  imprimée à côté.
- Il n'échoue toujours **pas** sur une ligne qui ne fait qu'expirer, et cela a
  été laissé tel quel délibérément. Une barrière qui passe au rouge du jour au
  lendemain fait pousser la date dans l'urgence plutôt que relire la source, ce
  qui est le seul résultat que tout ce mécanisme existe pour empêcher. Expirer
  est un rappel ; être périmé est un défaut ; confondre l'un dans l'autre casse
  le mécanisme dans un sens ou dans l'autre.
- Deux tests de contrat tiennent les deux moitiés, et retirer l'option ou la
  raccourcir en dessous de deux exécutions hebdomadaires fait échouer celui qui
  porte son nom.

### L'auditeur est un paquet, pas un fichier à sept métiers

- `auditor.py` faisait 1 319 lignes portant sept préoccupations sans rapport, ce
  qui rendait la seule question avec laquelle un lecteur arrive — d'où vient *ce*
  nombre — répondable seulement en lisant le tout. C'est maintenant
  `saggio/auditor/`, neuf modules, le plus gros à 331 lignes : `paths`,
  `options`, `naming`, `blocks`, `assumptions`, `measuring`, `projections`,
  `build`.
- **La surface publique n'a pas bougé.** `from saggio.auditor import audit,
  AuditOptions, AuditResult, audit_git_url, repository_name` se résout exactement
  comme avant, parce que le fichier est devenu un paquet du même nom.
- **La sortie n'a pas bougé non plus**, et cela a été vérifié plutôt que
  supposé : une référence de trois audits, de l'utilitaire de nommage de dépôt et
  du rendu en ligne de commande a été capturée avant la première coupe et
  comparée après chaque étape. Identique octet pour octet du début à la fin.
- Les constantes de chemins pointés ont perdu leur tiret bas initial. Un nom
  privé à un module était la bonne orthographe tant qu'il y avait un module ;
  maintenant que six d'entre eux partagent ces chemins, le tiret bas décrirait
  l'ancienne forme.
- Deux choses qu'un découpage casse, qu'une suite de tests attrape et qu'un
  lecteur ne verrait pas : les **imports privés** (`_projections` déplacé vers le
  module qui le possède) et les **cibles de monkeypatch** (25 d'entre elles,
  nommant maintenant le module qui *cherche le nom* plutôt que celui qui le
  définit, car c'est là que le patch doit se faire une fois le nom importé).
- Et une que `ruff` ne peut pas attraper : `--fix` a retiré des imports utilisés
  uniquement par des **doctests**, parce que F401 lit du code et qu'un exemple
  dans une docstring n'est pas du code tant qu'il ne tourne pas. Six exemples ont
  été rendus autonomes plutôt que laissés à s'appuyer sur l'espace de noms de
  leur module, ce qui est précisément ce qui les rendait fragiles.
- `audit` lui-même est toujours long, et délibérément : c'est une recette
  linéaire, et découper une recette en étapes appelées une fois chacune fait
  sauter le lecteur d'un endroit à l'autre pour reconstituer un ordre qu'on était
  déjà en train de lui donner. La docstring du paquet le dit.
- `examples/saggio.yaml` est régénéré. Sa note de carbone incorporé disait encore
  que l'empreinte d'un processeur « n'est pas encore dans le catalogue », ce qui
  avait cessé d'être vrai à la version précédente.

### La galerie compare, sans faire semblant que les nombres se comparent

- La galerie montrait la sortie d'un outil sur six dépôts et ne disait rien des
  alternatives, qui pour bien des tâches sont la meilleure réponse. Elle porte
  maintenant **le même travail, vu par les autres outils** : cinq familles —
  traceurs d'épisodes, démons de puissance, calculateurs, outils de dépense, et
  celui-ci — avec l'artefact que chacun produit, l'unité à laquelle sa réponse
  se rapporte, et **ce que chacun fait quand une entrée manque**.
- Cette dernière colonne est la comparaison. saggio écrit `TODO` ; les traceurs
  d'épisodes sortent un nombre quand même ; la série d'un démon a un trou ; le
  champ d'un calculateur est obligatoire ; un outil de dépense n'a simplement pas
  de ligne. **Aucun de ces comportements n'est un défaut** — un démon qui
  arrêterait le monde pour poser une question serait un mauvais démon — et la
  page le dit, parce que cette colonne est la raison pour laquelle les outils ne
  sont pas interchangeables, pas un tableau de scores.
- Ce qu'elle refuse de faire, c'est de les classer par leur sortie. Une figure
  CodeCarbon pour un entraînement et une figure saggio pour une inférence ne sont
  pas deux mesures d'une même chose, pas plus que les six modèles de la galerie
  ne se comparent entre eux.
- Une SVG écrite à la main porte la comparaison ; le tableau à côté porte les
  outils nommés et leurs liens, de sorte que les deux font deux métiers
  différents plutôt que de dire deux fois la même chose. Les deux versions
  linguistiques sortent d'un seul générateur,
  `assets/make_gallery_figure.py`, parce que deux SVG éditées à la main divergent
  dès qu'une ligne change et qu'une figure en désaccord avec sa traduction ne
  laisse personne en mesure de dire laquelle a raison.
- Quatre tests de contrat la tiennent : tout outil nommé dans la comparaison doit
  être un outil que `LANDSCAPE.md` a réellement étudié, la réserve sur les
  nombres incomparables ne peut pas être retirée, chaque langue doit montrer sa
  propre figure, et une figure éditée à la main au lieu d'être régénérée échoue
  en étant nommée.
- `LANDSCAPE.md` / `PAYSAGE.md` disaient **« Pas de carbone incorporé »**, ce qui
  avait cessé d'être vrai quelques versions plus tôt. Une auto-évaluation périmée
  est pire que rien quand c'est la page d'où l'on tire une comparaison : elle
  énonce désormais ce qui est implémenté et à quel point c'est maigrement
  catalogué.

### La promesse du carbone incorporé rencontre son catalogue

- Le README offrait les quatre termes d'ISO/IEC 21031. L'arithmétique les avait ;
  le catalogue avait **trois empreintes sur 25 lignes d'accélérateurs et aucune
  sur 12 processeurs**, si bien que la plupart des vraies machines recevaient un
  `TODO`. Les deux moitiés sont traitées : le catalogue est étendu là où il peut
  honnêtement l'être, et la promesse énonce désormais sa propre couverture au
  lieu d'en laisser supposer davantage.
- `saggio catalog refresh hardware --column embodied` lit les empreintes de
  processeurs chez [Boavizta](https://doc.api.boavizta.org/Explanations/components/cpu/),
  une API ouverte sans clé au-dessus d'une base de tailles de puces alimentée par
  la foule. **Quatre processeurs sur douze** sont acceptés ; les huit autres sont
  refusés nommément, avec la raison.
- Deux gardes, les deux gagnées en sondant la source plutôt qu'en lui faisant
  confiance :
  - Elle répond à propos d'une puce qu'on ne lui a pas demandée. Interrogée sur
    un **Apple M4 Max, elle renvoie un Apple M1 Max** — quatre générations plus
    tôt — et ne le dit nulle part dans sa réponse. Trois lignes Apple auraient
    porté une figure de M1 Max.
  - Elle répond pour une taille de puce qu'elle n'a pas en comblant avec une
    moyenne de famille. Interrogée sur une puce nommée `banana chip 9000`, elle
    renvoie **19,0 kgCO2e** sans un mot. L'empreinte est fonction de la puce, si
    bien qu'une puce par défaut donne une empreinte par défaut portant le nom de
    la puce. Deux lignes Xeon en auraient porté une.
- La moitié accélérateurs de cette API est **refusée franchement et en toutes
  lettres** : interrogée sur n'importe quel GPU par son nom, elle répond
  575,1 kgCO2e — le même nombre pour une GTX 1080 Ti, une A100 et une H100,
  parce qu'elle ne détient qu'un archétype nommé « Large GPU ». C'est trois fois
  et demie la figure vérifiée de NVIDIA pour une H100.
- L'auditeur se rabat de l'accélérateur sur le processeur. Son ancienne note
  disait que l'empreinte d'un processeur « n'est pas encore dans le catalogue »,
  ce qui a cessé d'être vrai le jour où quatre y sont entrées : une machine dont
  la seule puce est connue aurait continué de rapporter `TODO` pendant que la
  figure dormait dans le fichier à côté. Une puce générique par défaut rapporte
  toujours `TODO`, parce que l'empreinte d'un défaut est elle aussi un défaut.
- `STANDARDS.md` / `NORMES.md` portent les sept figures dans un tableau, tiennent
  les deux forces d'affirmation séparées plutôt que de les moyenner en un seul
  mot, et listent les huit refus avec leurs raisons. Le README dit que le
  catalogue est incomplet et pourquoi, au lieu de le laisser découvrir.

### Chaque colonne d'une ligne de réseau dit d'où elle vient, et tourne à son propre rythme

- Le même défaut une troisième fois. Le carbone citait Ember, ce qui était juste.
  Le tarif citait Ember, qui ne publie aucun tarif. La **liste de fuseaux
  horaires citait Ember aussi**, qui ne publie pas davantage de fuseaux. Le
  `source_url` au niveau de la ligne couvrait ce que personne n'avait regardé, et
  il a disparu : il ne reste aucune source au niveau de la ligne, parce que ne
  couvrir rien en particulier est exactement la façon dont il mentait.
- `saggio catalog refresh grid --column timezones` confronte les noms à la [base
  de fuseaux horaires de l'IANA](https://data.iana.org/time-zones/tzdb/zone1970.tab)
  et estampille la version à laquelle chaque ligne correspondait —
  `timezones_tzdb_version: "2026e"`. Elle **vérifie plutôt qu'elle ne remplace** :
  la base dit quels fuseaux existent, pas lesquels un pays utilise au sens où ce
  catalogue l'entend, et le catalogue porte délibérément des noms de
  compatibilité comme `Europe/Kiev` et `Asia/Calcutta`, parce que c'est ce qu'une
  vraie machine rapporte. Les 64 fuseaux en fichier sont confirmés. Un fuseau
  publié sous aucun nom fait échouer la commande plutôt que d'être corrigé.
  `--column all` fait les trois en une passe.
- `COLUMN_STALE_AFTER_DAYS` donne à une colonne sa propre fenêtre là où elle
  diffère de celle de son type de ligne. C'est la raison pour laquelle
  `STALE_AFTER_DAYS` était une table dès le départ, appliquée un niveau plus bas :
  une ligne de réseau porte maintenant trois colonnes de trois sources à trois
  vitesses. Sous une horloge unique, la ligne devenait périmée tous les mois à
  cause d'une liste de fuseaux que personne n'avait besoin de relire, ce qui
  apprend à un mainteneur à redater plutôt qu'à relire.
- Trois contrats de provenance généralisés d'un `source_url` par ligne à un par
  colonne, ce qui est une affirmation plus forte qu'avant : chaque nombre a une
  source, pas chaque ligne.

### Une intégration continue qui peut passer au vert

- Le workflow n'était plus passé depuis **vingt-cinq exécutions d'affilée**. Une
  barrière toujours rouge n'est pas une barrière : personne ne la lit, personne
  ne la répare, et la seule fois où elle attrape quelque chose de vrai elle a
  l'air des vingt-quatre fois où elle n'avait rien attrapé.
- Quatre jobs deviennent un : Linux, Python 3.10 — le plancher de
  `requires-python`, donc la version la plus susceptible de refuser quelque
  chose. Toute la suite, `ruff check` et `ruff format --check` y passent, vérifié
  avant de pousser plutôt que découvert dans un journal.
- Ce que cela coûte figure dans l'en-tête du workflow plutôt que laissé à
  remarquer : macOS n'est plus exercé en intégration continue, et seul le
  plancher de la plage de versions est lancé. Le test de contrat qui épinglait la
  matrice à `SUPPORTED_PLATFORMS` vérifie désormais l'invariant qui avait attrapé
  le vrai bug — aucun job ne doit tourner là où le paquet refuse de s'importer —
  au lieu d'une forme de matrice qui prétendait aussi, discrètement, que
  l'intégration continue couvrait toutes les plateformes.
- La dérive de formatage qui le faisait échouer : `ruff format` n'avait jamais
  été dans la boucle locale, seulement `ruff check`. Quatre fichiers n'étaient
  pas formatés.

### La colonne des tarifs reçoit une source qui publie des tarifs

- Chaque ligne citait une URL pour toute la ligne. L'intensité carbone venait
  d'Ember ; le tarif à côté n'en venait pas et ne pouvait pas en venir — cette
  page publie la production, les émissions, la capacité et la demande, et **aucun
  prix**. Trente-huit lignes portaient un `source_url` qui ne contenait pas le
  nombre posé à côté. Le défaut date du premier commit et était invisible
  jusqu'à ce que séparer la provenance du carbone laisse le tarif seul avec une
  citation qui n'avait jamais parlé de lui.
- `saggio catalog refresh grid --column price` relit les tarifs chez
  [GlobalPetrolPrices](https://www.globalpetrolprices.com/electricity_prices/),
  qui publie un prix résidentiel par kilowattheure — énergie, distribution,
  transport et toutes taxes — pour chaque pays, dans un seul tableau et une seule
  monnaie. `--column both` fait les deux en une passe.
- Chaque colonne porte maintenant `*_source_url`, `*_retrieved_date`, et la
  période que la figure décrit : `carbon_data_year: 2025`,
  `price_collected: "Q3 2026"`. Le jour où un nombre a été lu n'est pas la
  période qu'il couvre.
- [Eurostat](https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/nrg_pc_204?format=JSON&lang=EN&nrg_cons=KWH2500-4999&tax=I_TAX&currency=EUR&unit=KWH&lastTimePeriod=1)
  est l'organisme qui fait davantage autorité pour l'Europe et il a été lu —
  comme **vérification**, non comme source. Il publie en euros et pour l'Europe
  seulement : le prendre aurait signifié une deuxième source pour le taux de
  change, une conversion qui se périme chaque jour, et dix-huit lignes
  incomparables avec les vingt autres. Converties au [taux de référence de la
  BCE](https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml), les deux
  concordent à une médiane de 7 % sur les dix-huit pays que les deux couvrent et
  divergent de plus de 15 % pour six — Finlande, Roumanie, Pologne, Norvège,
  Suède, Italie — ce qui est une différence de méthode, pas une erreur chez l'un
  ou l'autre. Les trois URL sont dans la source pour que la comparaison puisse
  être refaite.
- `DeploymentContext.electricity_price` lit la provenance propre du tarif et
  nomme la période de collecte.
- Trois tests de contrat tiennent la ligne désormais : chaque colonne cite une
  source à elle et dit quand elle a été lue ; les deux colonnes ne peuvent jamais
  partager une URL, car cela voudrait dire que l'une est garantie par une page
  qui ne la publie pas ; et les URL en fichier sont celles que le
  rafraîchissement écrirait. Remettre le défaut d'origine fait échouer le premier
  en le nommant.
- Les deux modèles du parcours guidé avaient une figure monétaire dérivée de
  l'ancien tarif. La vérification arithmétique les a attrapés tous les deux, avec
  la bonne réponse à côté.

### Les tests cessent de réénoncer ce que le paquet rafraîchit

- Sept tests ont échoué au rafraîchissement, chacun parce qu'il avait recopié un
  nombre du catalogue dans une assertion au lieu de le lire. Un paquet dont
  l'argument est qu'il rafraîchit ses propres faits ne peut pas avoir une suite
  qui casse quand il le fait : le rafraîchissement se lisait comme une
  régression.
- Chacun affirme désormais ce que son propre nom revendique. Les tests d'audit et
  de contexte comparent au catalogue ; le test norvégien vérifie que la Norvège
  se résout tout court, ce qui est la garde contre un YAML lisant `NO` comme
  faux ; le test de rapport JSON bouchonne une valeur très éloignée de tout ce
  que le catalogue pourrait porter, plutôt qu'une valeur plausible qui ne passait
  que jusqu'à ce que le catalogue la rattrape.
- Trois doctests montrent maintenant l'unité, le statut et le fait qu'un
  `source_url` accompagnait la figure, plutôt que la figure. Un exemple qui
  réénonce un nombre rafraîchissable est faux dès la première fois que quelqu'un
  lance la commande de rafraîchissement que ce paquet livre.

## 1.3.0 — 2026-10-02

### Une dérivation est vérifiée, pas seulement déclarée

- `derived_from` n'achetait qu'une vérification de statut et rien d'autre. Une
  valeur pouvait nommer correctement ses entrées et énoncer un nombre éloigné de
  quatre ordres de grandeur de leur produit, et valider. C'était la pire forme
  que le manque pouvait prendre : un nombre faux portant une dérivation correcte
  se lit comme *mieux* fondé que tout le reste de la page.
- `saggio.model.derivation` recalcule la valeur à partir de ses entrées, par
  **unités** plutôt que par nom de champ. Chaque unité est analysée en une
  échelle et un jeu de dimensions de base — joules, secondes, grammes
  d'équivalent CO₂, litres, octets, et toute monnaie qu'un modèle nomme. `W`
  vaut `J/s`, `kWh` vaut 3 600 000 joules, `gCO2e/kWh` vaut des grammes sur des
  joules avec le facteur replié dedans. Rien n'est un cas particulier : des
  secondes multipliées par des watts donnent une énergie parce qu'un watt *est*
  un joule par seconde.
- Le **produit vient d'abord**, et là où il tombe sur l'unité énoncée, c'est la
  lecture retenue : une dérivation multiplie sauf si elle ne peut pas. Là où le
  produit manque, chaque entrée est aussi essayée comme diviseur, parce qu'une
  dérivation peut diviser — amortir une empreinte incorporée sur une durée de vie
  est une division, et le modèle nomme la durée de vie parmi ses entrées tout
  pareil.
- Exactement un arrangement atteignant l'unité signifie que la relation est sans
  ambiguïté, et plus de 1 % d'écart est une **erreur**. Plusieurs arrangements
  signifient que les unités ne peuvent pas dire lequel était visé, donc aucune
  réponse unique n'est revendiquée — mais une valeur ne correspondant à **aucun**
  d'eux reste une erreur, parce qu'elle est fausse sous toutes les lectures.
  C'est ce qui clôt le cas à trois entrées, où une figure de carbone incorporé
  fausse de cinq ordres de grandeur passait avec une liste d'entrées parfaitement
  correcte à côté.
- Une unité qu'aucun arrangement ne peut produire — une durée multipliée par un
  nombre sans unité donne une durée, jamais une masse de dioxyde de carbone — est
  une **erreur** aussi, moins coûteuse à établir, et décidable quel que soit le
  nombre d'entrées.
- Là où une unité en jeu est inconnue du paquet, le validateur ne dit **rien**.
  Le silence est la réponse honnête à « je ne peux pas savoir », ici comme
  partout ailleurs.
- Il a trouvé un nombre faux dès sa première exécution, dans une fixture de test
  nommée `sound_model` : 0,05 kWh là où 3 600 s à 100 W font 0,1. Les neuf
  modèles d'exemple commités sont passés, avant comme après l'élargissement de la
  règle.

### `measured` doit dire ce qui l'a mesuré

- `estimated` doit nommer une source ; `measured`, le statut plus fort, ne
  demandait rien. Une valeur qui le revendique doit désormais être dérivée,
  porter une note, ou se trouver dans un modèle muni d'un bloc `measurement`.
- Et un bloc `measurement` ne se porte garant que de **ce qu'une exécution peut
  réellement observer** : des durées, de l'énergie, de la puissance et des
  octets. Il ne produit ni l'intensité carbone d'un réseau ni une facture cloud.
  Le laisser se porter garant de chaque valeur `measured` du fichier était la
  même erreur dans un endroit plus discret : une figure carbone marquée
  `measured`, sans rien au monde qui ait pu la mesurer, héritant de la stature
  d'un chronomètre parce que le fichier en contenait un. Une valeur hors de ce
  qu'une exécution observe doit maintenant s'attribuer elle-même ; un coût lu sur
  une facture est une vraie mesure, et le dire dans `notes` est tout ce que la
  règle demande.
- Une unité que le paquet ne reconnaît pas reçoit le bénéfice du doute. Affirmer
  que l'instrument de quelqu'un ne peut pas exister reviendrait à inventer une
  règle sur son domaine.
- Un **avertissement** du début à la fin, pas une erreur : quelqu'un peut
  vraiment l'avoir mesuré avec son propre wattmètre, et refuser son modèle
  reviendrait à refuser la vérité.

### Rupture

- `import saggio` lève une exception sur une plateforme qui n'est ni Linux ni
  macOS. Windows est hors périmètre délibérément ; voir `MEASURING.md`.
- `saggio catalog freshness --json` renvoie `{"stale": …, "expiring": …}` plutôt
  que la seule table des périmés.

### La galerie démontre une mesure

- Compté avant ce changement : **0 mesuré, 24 estimés, 144 TODO** sur les six
  exemples commités. Toute la proposition du paquet est que `measured` veut dire
  qu'un compteur l'a dit, et l'artefact le plus visible qu'il livre n'en
  démontrait rien.
- Le parcours guidé a été relancé et le démontre désormais. Sa puissance vient
  d'un compteur plutôt que d'une fiche technique, ce que le diff rapporte dans la
  ligne qui vaut d'être lue deux fois :
  `assumptions.power_draw: 83.76 -> 31.1047 (-62.9%), estimated -> measured`. La
  plaque signalétique se trompait d'un facteur deux et demi.
- Avec la puissance mesurée, `machine_energy` monte à `measured` tout seul — ses
  deux entrées le sont — tandis que l'énergie du **bâtiment** reste `estimated`,
  parce que la surcharge du centre de données est encore une hypothèse. La règle
  du maillon faible se calculant elle-même, en quatre étapes, dans un fichier
  commité.
- Une cinquième étape, `5-run.yaml` : `saggio audit --run --scaling-steps 3` en
  une commande, avec un **exposant d'échelle mesuré de 0,687 à R² = 0,999**.
  C'est aussi une mauvaise nouvelle sur la mesure, et c'est l'intérêt :
  l'exposant dit que la tranche est surtout du démarrage de Python, donc une
  projection à partir d'elle surestimerait l'exécution, et l'outil le dit au lieu
  de projeter quand même.
- Le parcours guidé ouvre la grille de la galerie du site, où la figure
  d'honnêteté montre désormais un segment `measured` vert au lieu de six barres
  d'estimation et de TODO.
- Le `num_samples` de la charge de travail jouet passe de 5 000 à 400 000, avec
  la raison dans le fichier : à un millième de cinq mille, trois tranches
  séparées d'un facteur quatre s'arrondissent à deux, et la charge était trop
  petite pour démontrer quelque chose que l'outil sait faire.

### Un seul script sans ambiguïté est un point d'entrée

- `find_entrypoint` connaissait quatre noms — `train.py`, `main.py`, `run.py`,
  `benchmark.py` — et ne renvoyait rien pour un dépôt dont l'unique script
  s'appelle autrement. La charge jouet du parcours guidé en était un : une taille
  de travail énoncée, un fichier exécutable, et « il n'y avait rien de sûr à
  exécuter ».
- Il se rabat maintenant sur le seul fichier Python à la racine qui s'exécute
  lui-même, quand il y en a exactement un. Deux n'est pas sans ambiguïté et
  renvoie toujours rien : une tranche du mauvais script mesure la mauvaise chose,
  et le lecteur n'aurait aucun moyen de s'en apercevoir d'après le nombre.

### L'intégration continue lançait deux jobs qui ne pouvaient qu'échouer

- La matrice du workflow listait encore `windows-latest` après l'exclusion de
  Windows, et son commentaire d'en-tête disait encore « les trois systèmes
  d'exploitation que ce paquet prétend supporter ». Puisque `import saggio` y
  lève désormais une exception, les deux jobs Windows échouaient à la collecte.
  Le balayage qui avait exclu Windows cherchait dans `*.md`, `*.py`, `*.toml` et
  `*.yaml` ; le workflow est en `.yml`.
- Corrigé, et épinglé : un test de contrat met `SUPPORTED_PLATFORMS` en regard
  des runners de la matrice et échoue quand ils divergent, et un second refuse
  une plateforme exclue dans toute ligne `os:` ou `runs-on:`. Une liste de
  plateformes supportées qui vit dans deux fichiers a besoin d'un test, pas d'une
  convention.

### Un catalogue peut être relu depuis la source qu'il cite

- `saggio catalog refresh grid` demande à Ember ce que le réseau de chaque pays a
  émis et l'imprime en regard de ce que le catalogue détient. **En lecture
  seule** : une commande qui réécrit trente-huit figures sourcées sur une
  invocation nue est une commande que quelqu'un lance par accident, et le diff
  qu'elle laisse ressemble exactement à un diff que quelqu'un a vérifié.
  `--write CHEMIN` est la seconde étape délibérée.
- Elle a besoin d'une clé d'API Ember gratuite et ne **substitue rien**. Our
  World in Data publie une série dérivée d'Ember par un CSV stable et sans clé,
  et c'est la mauvaise série : ses propres métadonnées l'appellent intensité
  carbone *de cycle de vie* alors que cette colonne contient des émissions
  *d'exploitation*. La prendre aurait changé ce que veut dire chaque modèle
  commité, silencieusement. Le refus nomme le raccourci et la raison, pour que la
  prochaine personne qui le cherche trouve la raison d'abord.
- Elle écrit une seule colonne. L'intensité carbone reçoit ses propres
  `carbon_source_url`, `carbon_retrieved_date` et `carbon_data_year` ; le prix et
  les fuseaux de la ligne venaient d'ailleurs et gardent la provenance de la
  ligne. Le fichier est édité ligne à ligne plutôt que relu et réécrit par un
  sérialiseur YAML, ce qui aurait perdu l'en-tête, le regroupement, et le
  commentaire expliquant qu'un `NO` non quoté est le booléen faux et sort la
  Norvège du catalogue.
- Un pays pour lequel la source ne répond pas est laissé tel quel et nommé. Rien
  n'est interpolé, reporté ou moyenné.
- **Une ligne est désormais aussi fraîche que son nombre le plus vieux.** Les
  lignes portent plus d'une date depuis que ceci et les empreintes incorporées
  sont arrivés, donc `is_stale` et `expiring_report` prennent la plus ancienne de
  toutes les `*_retrieved_date` plutôt que seulement celle de la ligne. Ce
  changement a immédiatement fait échouer un test qui épinglait la fraîcheur à un
  jour codé en dur que le catalogue avait dépassé ; le test mesure maintenant
  depuis le jour où la ligne la plus récente a été lue, ce qui est vrai quand
  qu'il tourne.
- Trouvé par le test écrit pour le trouver : cinq des trente-huit clés de pays
  n'avaient pas de code ISO 3166-1 alpha-3 en fichier et auraient été
  silencieusement impossibles à rafraîchir.

### Windows est hors périmètre, définitivement

- **Les plateformes supportées sont Linux et macOS**, énoncées dans les
  classificateurs d'empaquetage, dans les deux README, et dans une seule
  constante, `saggio.analyze.capability.SUPPORTED_PLATFORMS`. `import saggio` sur
  autre chose lève une `ImportError` portant la raison, plutôt que de
  fonctionner à moitié ou d'échouer trois imports plus loin sur un module de la
  bibliothèque standard absent.
- La raison, dite une fois plutôt que de quatre façons : Windows ne publie aucun
  compteur d'énergie de processeur neutre vis-à-vis des constructeurs à un
  processus non privilégié — l'Energy Meter Interface n'existe que là où un
  fabricant l'a implémentée et seulement à travers un pilote, et les chiffres par
  application de `powercfg` sont un modèle de batterie et non un compteur — aucun
  total de temps processeur à l'échelle de la machine que ce paquet puisse lire,
  et aucune comptabilité de ressources POSIX pour un processus fils. Chacun seul
  serait survivable ; ensemble, ils veulent dire que chaque nombre que ce paquet
  existe pour produire y serait une estimation.
- Les accommodements partent avec. `capability.probe()` perd sa branche Windows
  et `_windows_interface()` disparaît ; `power.unavailable_reason()` perd son cas
  Windows ; `run.py` importe `resource` comme n'importe quel autre module
  standard au lieu de garder un import qui ne pouvait échouer que sur une
  plateforme maintenant exclue.
- La documentation cesse de le traiter comme un manque. Windows quitte le tableau
  des interfaces de `MEASURING.md` / `MESURER.md` et devient une déclaration de
  périmètre en dessous, et la liste « là où c'est le plus faible » de
  `LANDSCAPE.md` / `PAYSAGE.md` dit désormais « deux plateformes, pas trois » :
  plus étroit que ses voisins, et étroit exprès. L'Energy Meter Interface reste
  dans les sources, comme la preuve de l'exclusion plutôt que comme une capacité.

### La barrière de fraîcheur prévient avant d'échouer

- `saggio catalog freshness --within JOURS` nomme les lignes encore dans leur
  fenêtre de rafraîchissement mais près de sa fin, et n'échoue **pas**. Seule une
  ligne périmée fait encore échouer.
- La raison est le mode d'échec, pas la fonctionnalité : une barrière qui passe
  au rouge du jour au lendemain fait pousser la date dans l'urgence plutôt que
  relire la source, et un nombre redaté que personne n'a regardé est exactement
  ce que ce mécanisme a été bâti pour empêcher. Une semaine de préavis suffit
  pour aller lire la source convenablement.
- Trouvé en posant la question : les lignes de réseau livrées avaient été lues le
  2026-09-12 et les lignes de pays durent un mois, donc les 38 expirent le
  2026-10-13. Rien n'est périmé aujourd'hui et rien n'allait le dire avant le
  jour où ça casse.
- `--json` renvoie désormais `{"stale": …, "expiring": …}` plutôt que la seule
  table des périmés. Un changement de forme pour tout ce qui l'analyse.

### Une exécution est distinguée de sa machine de deux façons, pas d'une

- Soustraire une base au repos suppose que le reste de la machine a continué de
  faire ce qu'il faisait. `saggio.analyze.cpu` pose la même question sans cette
  hypothèse : il lit le total processeur de la machine elle-même avant la tranche
  et après — `/proc/stat` sous Linux, l'appel Mach `host_processor_info` sous
  macOS, les deux accessibles à un utilisateur ordinaire — et la part de ce
  travail revenant à la tranche attribue la puissance mesurée au lieu de lui
  soustraire un plancher. La méthode que Kepler utilise pour les pods et que
  GreenAlgorithms4HPC lit depuis un ordonnanceur.
- **Une part de travail processeur ne peut tarifer que de l'énergie de
  processeur.** Là où la machine publie ses sous-systèmes séparément, la figure
  propre du processeur est utilisée et le modèle enregistre ce que le nombre
  attribué couvre. Là où une seule figure couvre un accélérateur, il n'y a rien à
  quoi appliquer la part et aucune n'est offerte : une exécution qui occupe un
  GPU sur presque aucun temps processeur se verrait attribuer presque rien d'une
  consommation qui était surtout celle du GPU.
- Les deux réponses sont rapportées ensemble, et un avertissement se déclenche
  quand elles divergent de plus de la moitié en plus, avec les deux nombres
  dedans. La sortie utile de deux méthodes qui divergent est la paire, pas un
  choix.
- Des refus plutôt que des rapports plausibles : une fenêtre trop courte pour la
  résolution du compteur, un compteur qui a reculé, et — celui qui vaut la peine
  — une exécution qui rapporte plus de temps processeur que la machine entière,
  refusée plutôt que ramenée à un, parce que la ramener transformerait un signe
  qu'un compteur est faux en un nombre assuré.
- `PowerReading` porte maintenant `by_domain` : des watts par sous-système là où
  la machine les compte à part. Apple Silicon a toujours compté séparément les
  cœurs du processeur, les cœurs graphiques, le moteur neuronal et la mémoire, et
  ce paquet les additionnait en jetant la répartition.
- `power_by_domain()` dessine cette répartition dans le rapport HTML, la seule
  figure d'un de ces rapports qui soit mesurée plutôt que modélisée, chaque barre
  lue sur son propre compteur. Le camembert de parts estimées qu'elle remplace
  aurait été plus facile à dessiner et aurait été l'image d'une hypothèse.

## 1.2.0 — 2026-10-01

### Le carbone du matériel lui-même, et la norme qu'il complète

- Une nouvelle dimension canonique, `embodied_carbon` : ce qu'a émis la
  fabrication du matériel, amorti sur la part de sa vie qu'une unité de travail a
  réservée. Fabriquer une carte de base HGX H100 émet 1 312 kgCO2e avant qu'elle
  calcule quoi que ce soit, et un modèle qui ne rapportait que l'électricité
  affirmait que cette figure valait zéro.
- `saggio.embodied_carbon` implémente le `M = TE × TS × RS` de la spécification
  Software Carbon Intensity, et `saggio.software_carbon_intensity` assemble
  `(E × I + M) par R` — en refusant quand l'une des deux moitiés est ouverte,
  parce que rapporter l'une d'elles sous le nom d'une norme la sous-estimerait
  avec l'autorité de la norme.
- Trois empreintes sourcées dans le catalogue, chacune lue dans son propre
  document primaire et portant sa frontière en toutes lettres : A100 à
  127,6 kgCO2e d'après une ACV par démontage, H100 à 164,0 et B200 à 284,25
  d'après les empreintes carbone produit ISO 14067 de NVIDIA, toutes deux un
  huitième d'une carte de base. Une pièce sans ligne donne un `TODO` disant que
  personne n'a lu d'empreinte pour elle, ce qui n'est pas la même chose que
  d'avoir été gratuite à fabriquer.
- **La durée de vie part ouverte, exprès.** Chacune de ces empreintes va du
  berceau à la sortie d'usine et exclut la phase d'usage : le constructeur a
  donné le numérateur et retenu le dénominateur.
  `assumptions.hardware_lifetime` est un `TODO` jusqu'à ce qu'un humain
  l'énonce ; les chiffres publiés se groupent entre trois et six ans et cette
  seule plage fait varier la réponse d'un facteur deux.
- L'amortissement se fait en temps calendaire, comme la spécification le
  définit, si bien qu'une carte inactive la moitié de sa vie facture cette moitié
  à personne. Chaque figure le dit, parce que l'alternative courante donne un
  nombre plus grand et n'est pas ce que la norme dit.
- `STANDARDS.md` et `NORMES.md` sont la nouvelle page bilingue : les quatre
  termes, d'où vient chacun, et — la moitié d'une déclaration de conformité qui
  vaut d'être lue — exactement là où ce n'est *pas* conforme. Plus ce que
  demande l'annexe XI du règlement européen sur l'IA, qui est moins : de
  l'énergie plutôt que des émissions, pas de carbone incorporé du tout, et une
  publication au régulateur plutôt qu'au public.

### La base au repos cesse de coûter ce qu'elle ne peut pas acheter

- Une machine qui ne publie aucun compteur n'attend plus une seconde pour le
  découvrir. `PowerMeter.reads_anything()` répond d'après les lectures
  d'ouverture que le wattmètre a déjà prises, si bien que `measure_for` saute le
  sommeil et renvoie le même « non mesuré » qu'il aurait renvoyé une seconde plus
  tard. Demandé au wattmètre plutôt qu'à `saggio.analyze.capability.probe()`, qui
  lance `nvidia-smi` et n'a rien à faire sur le chemin de chaque exécution
  mesurée.
- `saggio audit --baseline SECONDES`, comme `saggio measure`, et
  `AuditOptions.baseline_seconds` derrière. On ne pouvait pas dire à un audit de
  sauter une seconde dont il n'a pas besoin, ni à une série d'échelle non plus ;
  les deux le peuvent maintenant. Une série d'échelle prenait déjà **une** base
  pour toute l'échelle plutôt qu'une par barreau, et le fait toujours.

### Le paysage, relu contre ce qui est sorti

- `LANDSCAPE.md` et `PAYSAGE.md` : l'autocritique s'était périmée dans le sens
  qui flatte, ce qui est le pire sens pour une page dont la prémisse est
  l'honnêteté. « Rien sur macOS ni Windows » et « pas de mesure de puissance
  GPU » étaient vrais quand ils ont été écrits et ne le sont plus : ils sont
  remplacés par les manques qui restent — rien n'est attribué à un *processus*,
  Windows ne publie toujours aucun compteur accessible sans privilèges, et un
  compteur n'est pas la prise murale : l'écart avec un wattmètre physique est une
  pente d'environ 1,17 qui varie d'un nœud à l'autre, pas une constante que
  quiconque pourrait rajouter.
- Une note bouge, et seulement parce que quelque chose de vérifiable est sorti :
  **Mesure la puissance** passe de trois étoiles à quatre. Pas cinq, parce que la
  cinquième est l'attribution par processus et que Scaphandre, PowerAPI et Kepler
  l'ont.
- L'entrée de Kepler note son passage en 2026 d'eBPF à `/proc` et `/sys`,
  abandonnant `CAP_BPF` et `CAP_SYSADMIN`. Celle de CodeCarbon note le prix
  mesuré de son échantillonnage : de 5,4 % à 46,8 % de surcoût en temps à 1 kHz
  dans une étude de 2026 sur les outils fondés sur RAPL, ce qui plaide pour son
  intervalle par défaut plutôt que contre l'outil.
- La carte de positionnement est régénérée depuis le tableau rafraîchi. Les axes
  ressortent en *Efficace ↔ Transparent* (55 %) et *Accessible ↔ Robuste*
  (25 %), 80 % ensemble, et le placement raconte la même histoire qu'avant — ce
  qui est l'intérêt de régénérer plutôt que de redessiner.

### Les diagrammes portent de la couleur

- Le diagramme Mermaid d'`ANALYSIS.md` et d'`ANALYSE.md` est coloré avec le jeu
  sûr pour les déficiences de vision des couleurs d'Okabe et Ito, la palette que
  les rapports et le site utilisent déjà : bleu pour ce qui est lu, vert pour ce
  qui est exécuté, la réponse retenue en aplat, le refus en pointillés vermillon.
  Chaque couleur se tient à côté d'une étiquette écrite, de sorte qu'elle porte
  de l'emphase et jamais le sens à elle seule.

### La projection sur l'exécution entière cesse de supposer le travail uniforme

- `saggio audit --scaling-steps N` lance la tranche à N tailles séparées d'un
  facteur quatre au lieu d'une seule, et ajuste `secondes = a × taille^b` par
  moindres carrés sur des axes log-log. La projection vers l'exécution entière
  devient `tranche / fraction ** exposant`, ce qui est la division qu'elle a
  toujours été quand l'exposant vaut un et ce qui diffère d'un facteur mille
  quand le travail est quadratique et que la tranche en valait un millième.
- L'exposant est `measured`, sur les tailles qui ont été exécutées et nulle part
  ailleurs : il résume des lectures d'horloge, comme le font des watts tirés d'un
  compteur d'énergie sur une durée. La projection reste `estimated`, parce qu'une
  mesure de quelque chose de plus petit n'a jamais été une mesure de ceci. Le R²
  et chaque exécution utilisée par l'ajustement voyagent avec lui dans
  `measurement.scaling`, pour qu'un lecteur puisse refaire l'arithmétique au lieu
  de croire l'exposant sur parole.
- Les refus sont l'essentiel. Moins de trois tailles — deux points ajustent une
  droite exactement et n'excluent rien — une plage de tailles sous un facteur
  quatre, une taille ou une durée qui n'a pas de logarithme, ou un ajustement
  expliquant moins de 95 % de la variation : chacun renvoie un refus nommant ce
  qui le lèverait.
- Un ajustement dont l'exposant sort *négatif* est refusé aussi, et séparément de
  la qualité de l'ajustement, parce qu'une droite descendante passant par trois
  points s'ajuste magnifiquement et ne veut rien dire. Le travail ne rétrécit pas
  quand il y en a davantage : de plus grandes exécutions qui finissent plus tôt
  disent autre chose que le travail ayant décidé des durées — un démarrage qui
  domine chaque barreau, un cache qui chauffe, un autre processus sur la machine
  — et le refus le dit et suggère `saggio power`. Zéro reste une réponse : un
  coût constant a cette tête-là. Trouvé par le test d'audit échouant sur une
  machine occupée par un autre travail, où l'exposant est sorti à -0,08 et où le
  validateur l'a rejeté comme un coût négatif, faisant échouer l'audit entier au
  lieu de laisser une figure ouverte.
- Un ajustement aussi mauvais change une réponse plutôt que d'en retenir une. Il
  veut dire que la tranche n'est pas représentative de l'exécution dont elle a
  été taillée, donc le bloc de l'exécution entière n'est pas écrit du tout et la
  raison parvient au lecteur. Avoir mesuré l'échelle et échoué reste distinct de
  n'avoir jamais regardé : sans l'option, la projection garde l'hypothèse
  linéaire et l'enregistre, et enregistre désormais aussi que rien ne l'a
  vérifiée.
- L'échelle est peu coûteuse exprès. Son barreau du haut est la tranche qui
  aurait été exécutée de toute façon, et les barreaux en dessous y ajoutent un
  quart et un seizième, si bien que la série coûte environ 1,3 fois la tranche
  seule. Elle tourne sans le profileur, parce que cProfile facture à l'appel et
  ajusterait sa propre courbe de croissance ; le marché est qu'il n'y a pas de
  chemin chaud nommé, et en échange chaque figure de coût vient d'une exécution
  non profilée plutôt que gonflée.
- Nouveau : `saggio.estimate.scaling` (`Observation`, `ScalingFit`,
  `fit_power_law`), `saggio.analyze.static.scaling_ladder`,
  `saggio.analyze.run.run_scaling_series`, et un mot-clé `scaling` sur
  `project_to_completion`. Exportés au niveau supérieur. `EXAMPLES.md` et
  `EXEMPLES.md` montrent la commande, le YAML et les refus ; `ANALYSIS.md` et
  `ANALYSE.md` enregistrent pourquoi c'était le seul changement qui valait la
  peine.

### Ce qu'on peut demander à la lecture du code, et à son exécution

- `ANALYSIS.md` et `ANALYSE.md` : l'enquête derrière la division du travail que
  fait le paquet entre la passe statique et la passe mesurée. Ce que l'analyse
  statique de bornes de coût (COSTA, RaML, KoAT) et l'analyse statique d'énergie
  (consommation énergétique au pire cas sur un jeu d'instructions) exigent
  réellement, pourquoi ni l'une ni l'autre n'atteint un dépôt Python sur une
  machine munie d'un accélérateur, et à quoi l'analyse statique sert vraiment
  ici.
- Les refus sont argumentés plutôt qu'affirmés, et le principal est désormais
  sourcé : les métriques statiques de source prédisent l'énergie mesurée avec un
  R² proche de zéro à elles seules, qui monte à 0,46 une fois le temps
  d'exécution ajouté. Une figure de complexité cyclomatique ne peut donc jamais
  apparaître dans un modèle de coût, sous aucun statut, parce qu'elle aurait
  exactement l'air d'un nombre vérifié.
- Le versant empirique est la moitié utile. La méthode de trend-prof — exécuter
  sur des tailles couvrant des ordres de grandeur, ajuster `y = a·x^b`,
  rapporter la qualité de l'ajustement — transformerait l'hypothèse permanente de
  `project_to_completion`, selon laquelle le travail est uniforme, en un exposant
  mesuré, en se servant d'une taille de travail que la passe statique lit déjà.
  Enregistré comme le seul changement qui vaille la peine.
- La discipline de mesure que le paquet suit déjà est maintenant adossée à ses
  sources : l'écart entre un compteur et la prise murale n'est pas un décalage
  constant (pentes de régression de 1,17 et 1,18, variables d'un nœud à l'autre),
  et un échantillonneur qui scrute à 1 kHz déforme le temps mural que chaque
  figure en aval multiplie.
- `skills/saggio/references/code-analysis.md` est la forme courte qu'un agent
  applique : quelles analyses ont le droit de produire un nombre et sous quel
  statut, et lesquelles ne l'ont jamais.

### macOS mesure la puissance désormais, et ne demande de mot de passe à personne

- `saggio.analyze.apple` lit les compteurs d'énergie propres à une puce Apple
  Silicon via `IOReport`, en utilisateur ordinaire. Cœurs du processeur, cœurs
  graphiques, moteur neuronal et mémoire, sous forme de compteurs monotones dans
  des unités que la bibliothèque étiquette elle-même, si bien qu'une mesure est
  une différence entre deux lectures plutôt qu'une moyenne d'échantillons. Chaque
  Mac de l'histoire de ce paquet rapportait `not measured` et se rabattait sur
  une fiche technique ; c'était une limite du code, pas de macOS.
- Les figures portent ce qu'elles sont : le modèle d'énergie propre à la puce
  plutôt qu'un wattmètre sur le rail d'alimentation, et l'avertissement d'Apple
  disant qu'elles ne se comparent pas d'une machine à l'autre. Ce qui est vrai du
  RAPL d'Intel aussi, sur toute pièce qui n'est pas une puce serveur Haswell.

### Les compteurs Linux sont lus par leur nom, et la mémoire à côté n'est plus perdue

- Les zones powercap sont lues par le nom que chaque zone se donne plutôt que par
  la forme de son répertoire. C'est ce qui distingue un paquet processeur de la
  zone `psys` qui le contient déjà — désormais préférée quand elle est présente,
  jamais ajoutée aux paquets — et de la zone `dram` à côté, dont l'énergie n'est
  **pas** comprise dans la figure du paquet et manquait donc à chaque lecture que
  ce paquet a jamais prise sur une machine qui la publie.
- Les zones `amd-rapl` sont lues comme les `intel-rapl`. `intel-rapl-mmio`, qui
  est le même paquet par une seconde interface, est toujours laissé tranquille.
- Un compteur qui a passé son plafond une fois pendant une exécution est déroulé
  grâce à son `max_energy_range_uj` publié au lieu d'annuler la mesure, et la
  figure porte la puissance au-dessus de laquelle cette récupération aurait été
  fausse. Un compteur qui a été *remis à zéro* plutôt qu'enroulé est toujours
  refusé.
- Là où NVIDIA n'est pas la carte présente, les pilotes `amdgpu`, `i915` et `xe`
  de Linux sont lus via sysfs — un compteur de microjoules accumulés là où le
  pilote en tient un, des watts instantanés échantillonnés là où il n'en tient
  pas. Aucun outil constructeur, aucun privilège.

### `saggio power` dit ce que cette machine vous laissera lire, et ne l'ouvre jamais pour vous

- Un nouveau verbe rapporte chaque interface d'énergie pertinente pour cette
  plateforme dans l'un de quatre états : `reads`, `blocked`, `root-only`,
  `absent`. La distinction est l'essentiel. Un compteur absent et un compteur
  présent mais fermé pour vous sont deux situations différentes, et « n'a pas pu
  mesurer la puissance » ne disait au lecteur rien sur quoi agir.
- `blocked` est le seul état qui a un remède, et le remède est imprimé plutôt
  qu'exécuté, avec à côté la raison pour laquelle le compteur est fermé : Linux
  garde `energy_uj` réservé à root depuis la 5.10 parce que l'échantillonner
  assez vite permet de retrouver ce que d'autres processus calculent —
  CVE-2020-8694, l'attaque PLATYPUS. Rouvrir un canal auxiliaire publié sur une
  machine partagée est un jugement, et il reste celui du lecteur.
- Rien dans ce paquet n'escalade : pas de `sudo`, pas d'invite de mot de passe,
  pas de repli discret vers un outil qui en demanderait un. `powermetrics` et le
  contrôleur de carte mère sont nommés comme `root-only` et laissés tranquilles.
- `saggio power --seconds N` mesure la machine elle-même pendant N secondes, pour
  que les compteurs puissent être vus à l'œuvre avant qu'une exécution en
  dépende — et pour qu'un lecteur rencontre tôt le fait qu'un compteur à
  l'échelle de la machine mesure la machine et non son programme.
- `saggio power --json` imprime la même chose sous forme de données, y compris
  les chemins de fichiers exacts qui seraient lus.

### Une exécution peut être projetée sur un autre processeur, à partir de ce qui a été mesuré

- `project_to_processor` met à l'échelle un temps d'exécution mesuré d'un
  processeur à un autre. Un processeur a deux vitesses qui ne bougent pas
  ensemble — un fil sur un cœur, et tous les cœurs occupés à la fois — si bien
  qu'une pièce à nombreux cœurs lents gagne la seconde et perd la première, et
  les deux vitesses sont les deux bouts d'une fourchette plutôt qu'un nombre.
- Quel bout s'applique est mesuré, pas supposé. `SliceResult.cores_busy()` est le
  rapport des secondes-processeur aux secondes d'horloge murale : proche de un,
  l'exécution suit le rapport mono-fil et une cible à nombreux cœurs la rend
  *plus lente* ; proche du nombre de cœurs de la machine, elle suit le rapport de
  débit ; entre les deux rien n'est tranché et le bout le plus lent est cité.
- Le catalogue gagne `cores` sur les lignes de processeur dont les notes
  l'énonçaient déjà, et les deux colonnes de score que la projection lit. Les
  scores partent vides exprès : un processeur ne publie aucune figure de pic qui
  vaille la peine de servir d'échelle, et le refus explique donc comment en tirer
  un d'un résultat publié, le diviser par le nombre de sockets du système, et
  enregistrer de quel test il s'agissait. Un score d'un test n'est jamais divisé
  par le score d'un autre : c'est refusé nommément.

### Une mesure a désormais un plancher sous elle

- Un compteur mesure la machine, pas votre programme. `saggio measure` observe la
  machine pendant une seconde avant que la tranche démarre et rapporte trois
  figures : ce que la machine a tiré pendant l'exécution, ce qu'elle tirait au
  repos avant, et la différence — qui est la seule des trois qui parle de la
  tranche. `--baseline 0` la saute sur une machine qu'on sait silencieuse.
- La soustraction suppose que le reste de la machine a continué de faire ce qu'il
  faisait, et cette hypothèse est écrite dans le modèle à côté du nombre plutôt
  que laissée au lecteur à fournir. Le plancher lui-même est enregistré comme
  `measurement.idle_watts`, diagnostique à la manière de `cpu_seconds` plutôt que
  comme un coût.
- Deux cas sont dits à voix haute au lieu d'être soustraits en silence. Une
  machine qui tire déjà plus de la moitié du total est signalée comme occupée,
  avec les deux nombres dans l'avertissement. Une machine devenue *plus
  silencieuse* pendant la tranche ne donne aucune figure marginale : ce qui
  tournait d'autre s'est arrêté, donc la base n'a jamais été le plancher de cette
  tranche et rien n'en découle.

### Une page sur la mesure, dans les deux langues

- `MEASURING.md` / `MESURER.md` : quels compteurs existent sur chaque
  plateforme, lesquels cette machine vous laissera lire, *vous*, ce que chacun
  couvre et laisse dehors, ce qu'il advient du nombre ensuite, et comment
  vérifier n'importe laquelle de ces affirmations à la main. Chaque affirmation
  pointe vers l'interface qu'elle décrit — les ABI powercap et hwmon du noyau, la
  documentation sysfs de `xe`, NVML, l'Energy Meter Interface de Microsoft,
  Redfish — et la raison pour laquelle le compteur Linux est fermé pointe vers
  l'attaque qui l'a fermé.
- Deux tests de contrat parcourent maintenant chaque page Markdown du dépôt
  plutôt que la seule carte de la documentation : un lien relatif qui ne pointe
  nulle part fait échouer la construction, et un lien vers un titre de section
  qui n'existe plus aussi. Une table des matières pourrit parce qu'un titre a été
  reformulé en dessous d'elle, et c'est maintenant attrapé plutôt que remarqué.

## 1.1.0 — 2026-09-18

### Le carbone est réénoncé dans des termes qu'un lecteur peut ressentir

- `saggio.estimate.equivalences` réénonce une figure carbone des trois façons que
  l'article Green Algorithms emploie, avec ses propres coefficients : des mois de
  séquestration par un arbre mature (11 kg de CO2 par an), des kilomètres en
  voiture particulière moyenne (175 g/km en Europe, 251 aux États-Unis), et une
  fraction d'un vol de référence (Paris–Londres, New York–San Francisco,
  New York–Melbourne). Une équivalence est une reformulation, pas une nouvelle
  mesure : elle hérite du statut du carbone plafonné à `estimated`, et une figure
  carbone ouverte donne une équivalence ouverte. Rien ne devient plus convaincant
  en étant converti en arbres.
- Les deux rapports portent maintenant la ligne de la taille ressentie sous
  chaque scénario et chaque projection dont le carbone est connu. Une figure
  inférieure à un kilogramme par unité est réénoncée par million d'unités, et la
  phrase le dit. La version HTML traduit ses étiquettes, si bien que le rapport
  français parle de mois-arbre.

### Les rapports ont gagné le panneau vedette du calculateur, et une vue d'équipe

- La carte « et si » du rapport HTML se termine par *comment le lieu déplace le
  carbone* : une barre d'intensité de réseau par pays, échantillonnées dans le
  catalogue pour que les réseaux les plus propres et les plus sales ancrent
  toujours l'échelle, le pays du modèle dans la couleur d'accent. SVG en ligne
  écrite à la main sur les jetons de la page elle-même, avec sa polarité
  énoncée.
- `saggio dashboard model.yaml [model.yaml ...]` rend chaque modèle commité sur
  une page autonome. Elle ouvre sur la seule comparaison honnête entre projets —
  la part de chaque modèle qui est mesurée, estimée ou encore ouverte — et dit
  franchement que les lignes de coût, chacune rapportée à sa propre unité de
  travail, ne se comparent pas entre elles.
- Le rapport HTML gagne la section de mesure que le Markdown avait toujours eue :
  la commande, le chemin chaud, et les avertissements qui nuancent chaque nombre
  au-dessus.

### L'estimation de puissance accepte un facteur d'usage

- `node_power(usage_factor=...)` met à l'échelle les termes du processeur et de
  l'accélérateur par le facteur d'usage des cœurs de Green Algorithms, jamais le
  terme de mémoire, parce que la mémoire consomme du fait d'être peuplée plutôt
  que du fait d'être occupée. Le défaut reste celui de l'article : la pleine
  consommation nominale quand rien n'a mesuré l'utilisation.

### Un audit de tout le paquet, et ce qu'il a refermé

Trois passes de revue vérifiées par exécution ont couvert chaque module, et
chaque constat est arrivé avec un test de non-régression. Ceux qu'un utilisateur
aurait pu rencontrer :

- Un `TODO` ou un `placeholder` qui faisait passer une valeur en fraude ne peut
  plus servir à calculer : `is_known()` veut maintenant dire un nombre fini sous
  un statut qui y a droit, si bien que les estimateurs, les projections et les
  équivalences laissent le résultat ouvert au lieu de blanchir la valeur. Le
  validateur voit aussi les nombres cachés dans les champs propres d'une
  grandeur, rejette NaN et l'infini, nomme les valeurs typées en chaîne, avertit
  sur le `YYYY-MM-DD` littéral du gabarit, et signale les fautes de scénario aux
  indices du document lui-même.
- Une tranche arrivée à expiration met maintenant fin à tout l'arbre de processus
  qu'elle a engendré, pas seulement à l'enfant direct ; sa sortie standard ne
  s'accumule plus sans borne dans la mémoire de l'auditeur ; le temps processeur
  de l'enfant est enregistré. Le lecteur RAPL ne double-compte plus les
  sous-zones de paquet, et la figure échantillonnée de l'accélérateur multiplie
  par le nombre de cartes au lieu de rapporter un nœud à huit cartes à la
  puissance d'une seule.
- Les tailles de travail écrites `6e5` sont lues en entier, pas comme leur
  mantisse ; une taille mise en commentaire ne prime plus sur la vraie ; un dépôt
  cloné dans un répertoire nommé `build` est quand même lu ; `openai_agents` ne
  correspond plus à `openai`.
- Une surcouche de catalogue partielle met à jour ses colonnes au lieu d'effacer
  celles qu'elle n'a pas réénoncées ; une clé `NO` non quotée est refusée à voix
  haute ; une `retrieved_date` dans le futur se lit comme périmée ; la table de
  prix de l'agrégateur est récupérée une fois par processus au lieu d'une fois
  par modèle détecté.
- `diff` fait échouer la barrière sur un changement d'unité ou de monnaie même à
  nombre égal ; `fold` refuse un modèle invalide d'emblée et écrit la ligne
  d'énergie sur laquelle ses dérivations d'argent et de carbone reposent ;
  `total_money` refuse un montant sans monnaie à côté d'une monnaie ; les temps
  d'exécution, puissances, tarifs et intensités négatifs sont refusés pour les
  erreurs de signe qu'ils sont.
- `saggio catalog` sans action sort en erreur d'usage, ce qu'elle est ; une URL
  hostile ne peut pas casser un tableau Markdown ; une ligne de catalogue
  malformée ne peut pas faire tomber la page HTML ; le tableau de bord, le
  tableau des projections et les contrôles des barres se traduisent tous.

### Une mesure peut entrer dans un modèle sans être retapée

- `saggio measure --into MODELE` écrit le temps d'exécution mesuré dans un modèle
  de coût et recalcule tout ce qui en dérive : l'énergie de la machine, celle du
  bâtiment, l'argent et le carbone, par les mêmes fonctions que celles de
  l'audit. C'est l'étape que les gens rataient à la main, et jusqu'ici il n'y
  avait aucun autre moyen de la faire : coller un temps d'exécution dans le YAML
  laissait l'énergie, l'argent et le carbone sur leurs anciennes valeurs, et un
  modèle dont l'énergie ne correspond plus à son temps d'exécution est pire qu'un
  modèle qui n'avait ni l'une ni l'autre, parce qu'il a l'air fini.
- `--units N` dit combien d'unités de travail la commande a accomplies, pour que
  la figure enregistrée soit par unité. Quand le modèle énonce déjà le travail
  qu'accomplit une exécution entière, une projection sur l'exécution entière
  suit, portant l'hypothèse sur laquelle elle repose : qu'une unité de travail est
  l'une des choses que le dépôt compte.
- Une figure de puissance que la machine a réellement mesurée remplace
  l'estimation du catalogue, et une lecture qui n'a rien mesuré laisse
  l'estimation tranquille plutôt que de remplacer un nombre sourcé par du
  silence.
- Trois choses sont refusées plutôt qu'écrites : une commande sortie en erreur,
  parce qu'une exécution ratée a mesuré un échec et qu'un échec n'a pas de coût
  par unité de travail ; un modèle sans scénario où écrire ; et tout résultat qui
  ne validerait plus. Rien n'est écrit à moitié, et chaque figure qui a bougé est
  imprimée.

### Trois défauts que la galerie a exposés, corrigés

- **Une annotation de type n'est plus lue comme un modèle appelé.** Auditer
  Whisper rapportait un modèle nommé `Whisper`, tiré de
  `model: "Whisper", mel: Tensor` dans une signature de fonction. Python n'a pas
  de clés de dictionnaire non quotées, donc un deux-points après un nom nu est
  une annotation ; JavaScript, TypeScript et Go en ont, et là la même ligne est
  vraiment un modèle qu'on choisit. Le détecteur sait maintenant quelle langue il
  lit.
- **Une chaîne en cours de construction n'est plus lue comme un modèle qu'on
  nomme.** Auditer FastAPI rapportait un modèle nommé `Body_`, tiré de
  `model_name = "Body_" + name` dans ses propres entrailles. Un littéral avec une
  concaténation, une interpolation ou un appel de formatage contre lui est un
  fragment, pas un nom.
- **Une configuration d'entraînement prime désormais sur une configuration
  d'évaluation.** Auditer DINOv2 prenait la durée d'un entraînement dans
  `configs/eval/`, parce que la règle était alphabétique à rang égal et qu'`eval`
  se classe avant `train`. Un dépôt qui sépare les deux dit laquelle une vraie
  exécution lit. Les noms de répertoires en décident, jamais le nom propre du
  fichier, et le désaccord est signalé dans les deux cas.

### Une galerie, avec les fichiers dedans

- `GALLERY.md` et `GALERIE.md` présentent six modèles de coût que ce paquet a
  produits, commités sous `examples/` avec le rapport rendu à côté de chacun :
  nanoGPT, Whisper, DINOv2, FastAPI, Airflow, et ce dépôt. Chacun nomme la
  commande qui le régénère. « Relisible dans une pull request » était une
  affirmation sans pièce à conviction.
- `examples/walkthrough/` fait passer un petit dépôt par quatre étapes, dans
  l'ordre où travaille un mainteneur : l'audit sans rien exécuter, un vrai
  `saggio measure` sur une tranche, la mesure repliée dedans et une exécution
  entière projetée à partir d'elle, et ce que `diff` rapporte entre la première
  et la troisième. La troisième étape est écrite par un script commité et
  ré-exécutable qui appelle les fonctions exportées du paquet, de sorte que ses
  nombres viennent de l'arithmétique de saggio plutôt que de qui a tapé le
  fichier, et un test de contrat vérifie que le script la reproduit toujours.
- Les pages de la galerie disent ce qui ne va pas dans leurs propres fichiers.
  Deux faux positifs sont nommés avec la ligne de preuve qui les a produits : une
  annotation de type `model:` dans le `decoding.py` de Whisper, et le
  `model_name = "Body_" + name` de FastAPI. De même pour la règle de préséance
  des tailles de travail qui a fait prendre à DINOv2 son nombre d'époques dans
  une configuration d'évaluation plutôt que d'entraînement.
- Un modèle bâti depuis un clone enregistre désormais
  `deployment.machine_provenance`, disant que le processeur, le nombre de cœurs
  et le système d'exploitation sont ceux de la machine qui audite et non ceux de
  là où le code tourne. Lire un modèle d'un cadre d'entraînement et prendre les
  chiffres d'un portable pour ceux d'un cluster emporterait cette erreur dans
  chaque nombre d'énergie en dessous.

### Projeter sur un autre accélérateur est une fourchette, et elle atteint un coût

- Le catalogue porte `memory_gb`, et une projection sur une carte plus petite que
  celle d'où vient la mesure le dit avant que le nombre serve : 80 Go de travail
  mesuré ne tiennent pas sur une carte de 24 Go, et une réponse arithmétique pour
  une exécution qui ne démarrerait pas est pire qu'un avertissement. C'est un
  avertissement plutôt qu'un refus parce que rien ici ne sait quelle part de la
  carte l'exécution a réellement utilisée. Les lignes Apple ne portent pas de
  `memory_gb` exprès : leur mémoire est unifiée avec l'hôte et choisie par
  machine, c'est donc une propriété d'un portable, pas d'une pièce.
- Deux choses limitent une charge de travail sur un accélérateur : le débit
  arithmétique et la bande passante mémoire. La projection ne connaissait que la
  première, ce qui la rendait optimiste par construction. Elle lit maintenant les
  deux, et le catalogue porte `memory_bandwidth_gbps` pour chaque accélérateur
  qu'il contient. Entre une A100 et une H100, les deux rapports valent 3,2 et
  2,2 ; ne rapporter que le premier sous-estimait d'un tiers la facture d'une
  exécution limitée par la mémoire.
- Le résultat est une fourchette. L'estimation ponctuelle est le rapport de
  calcul quand la lecture a établi que le travail est limité par le calcul, le
  rapport de bande passante quand elle a établi l'inverse, et le plus lent des
  deux quand elle n'a rien établi, parce que le rapport le plus lent donne
  l'exécution la plus longue et la facture la plus grosse. Les deux bouts
  figurent au dossier sous `bounds`. Une pièce dont le catalogue ne porte pas la
  bande passante se projette quand même, et dit que la figure est une borne
  supérieure sur l'accélération plutôt qu'une fourchette autour d'elle.
- La projection atteint l'énergie, l'argent et le carbone sur la carte cible au
  lieu de s'arrêter à une durée, chaque figure nommant les nombres projetés d'où
  elle vient plutôt que les nombres locaux dont elle ne vient pas. Elle énonce
  dans le modèle que le pays, le tarif, l'intensité du réseau et la surcharge du
  centre de données sont ceux déclarés pour ce déploiement, parce que déplacer du
  travail sur un autre accélérateur signifie d'ordinaire le déplacer ailleurs.
- La précision est désormais une question de catalogue plutôt qu'un mur. Chaque
  précision nomme la colonne qui cite un débit pour elle, et un refus dit quelle
  colonne manque pour quelle pièce et comment l'ajouter. FP16 et BF16 partagent
  une colonne, et la projection le dit au lieu de substituer l'une à l'autre en
  silence.
- Les deux rapports montrent tout cela. La page HTML n'avait aucune section de
  projections, alors que ses traductions portaient déjà un titre pour elle, et le
  rendu Markdown ne connaissait que la forme d'une projection sur l'exécution
  entière : chaque coût projeté était donc jeté sans un mot. Les deux rendent
  maintenant les figures et la fourchette.

### L'outil entier est désormais exécuté contre des dépôts qui ont la forme de dépôts

- Une famille de tests d'intégration audite quatre dépôts qui ressemblent à de
  vrais — un projet d'entraînement en Python, un service en TypeScript, un outil
  en ligne de commande en Go, et un manuel qui ne fait que parler de cadres
  logiciels — chacun avec une suite de tests, un README nommant des technologies
  qu'il n'utilise pas, et une arborescence vendorisée. Les assertions portent sur
  la réponse entière : ce qui a été trouvé, et tout autant ce qui ne l'a pas été.
- L'un d'eux audite ce dépôt. C'est la garde contre le défaut ci-dessus, qu'une
  suite de cinq cents tests unitaires au vert n'avait pas attrapé, parce
  qu'aucun d'eux ne lançait l'outil contre quelque chose ayant la forme de code
  pour lire la réponse.
- La forme d'un dépôt Go doit revenir `unknown` plutôt que devinée, ce qui est la
  réponse que ce paquet existe pour donner.

### La suite de tests n'est plus prise pour la charge de travail

- Un cadre logiciel est maintenant détecté par une ligne qui l'importe, pas par
  un fichier qui contient son nom. Auditer ce dépôt rapportait quatorze cadres,
  de PyTorch à Spark, parce que sa propre table de détecteurs et ses propres
  fixtures écrivent ces noms. Il en rapporte un désormais, et celui-là est un nom
  de programme cité dans la table de détecteurs elle-même.
- Le code qui teste un dépôt est lu à part du code qu'il exécute. Les fichiers
  propres à la charge de travail sont lus en premier et décident de ce que l'audit
  rapporte ; les cadres que seule la suite importe sont listés sous
  `frameworks_in_suite_only` ; un service ou un modèle dont la seule ligne de
  preuve est un fichier de test porte un `caveat` qui le dit. La forme de la
  charge de travail n'est plus décidée par un fichier qui existe pour en tester
  une.
- Une taille de travail énoncée dans un test se classe sous toutes les tailles
  que la charge énonce, et ne compte plus comme un désaccord avec elles. Une
  suite dit `max_iters = 100` pour qu'un test finisse ; ce n'est pas une
  contradiction de la vraie configuration, et le rapporter comme telle enterrait
  les contradictions qui comptent.

### L'accélérateur est mesuré, pas supposé

- La puissance vient maintenant de deux compteurs au lieu d'un. À côté du
  compteur de paquet Intel sous Linux, on demande au pilote NVIDIA ce que la
  carte tire, sans privilèges, sous Linux comme sous Windows : le compteur
  d'énergie accumulée là où la carte en tient un, sinon la moyenne de lectures
  prises toutes les demi-secondes pendant la durée de l'exécution. Sur les
  charges pour lesquelles ce paquet existe, la carte représente l'essentiel de la
  consommation de la machine, et un modèle ne rapportant que le processeur se
  trompait d'un facteur plusieurs.
- Une mesure nomme désormais quels compteurs ont répondu, dans `power_sources`,
  et la phrase de portée dit ce que la figure laisse dehors : le processeur quand
  seule la carte a répondu, la carte quand seul le processeur l'a fait, et le
  reste de la machine dans les deux cas. Deux modèles mesurés sur des frontières
  différentes ne peuvent plus être pris pour deux modèles de la même.
- Une carte qui répond `[N/A]` annule la requête plutôt que de contribuer la
  moitié de la puissance d'une machine, un compteur de pilote qui a reculé ne
  donne rien, et moins de deux lectures ne font pas une moyenne. Dans chaque cas
  la figure reste `estimated` et dit pourquoi.

### La documentation est vérifiée comme bilingue

- Chaque page écrite dans les deux langues est désormais vérifiée comme une
  paire : les deux moitiés existent, chacune pointe vers l'autre, et les deux
  montrent les mêmes commandes avec les mêmes options. Une page écrite une seule
  fois est listée avec la raison pour laquelle elle l'est, et une nouvelle page
  qui n'est ni l'un ni l'autre fait échouer la construction. À la moitié
  française manquait discrètement une invocation de `diff` et elle portait une
  date de relecture différente pour la même ligne de catalogue ; les deux sont
  corrigées.

### Renommé en saggio

- Le projet, le paquet, la commande et l'import sont tous `saggio`, là où ils
  étaient `running-code-cost-helper` et l'alias `rcch`. *Saggio* est l'italien
  pour l'essai d'un métal, pour un essai écrit, et pour judicieux ; le README dit
  pourquoi les trois conviennent. Rien n'avait été publié sous l'ancien nom,
  donc aucune version ne le porte et aucun import n'a jamais à être maintenu en
  état de marche.

### Les pièces du rapport sont sorties du paquet

- La coquille de document du rapport HTML est maintenant un fichier,
  `reporting/report.html`, avec des jetons nommés que le rendu remplit, plutôt
  qu'une f-string à l'intérieur de `report/html.py`. La feuille de style, le
  script, les traductions et le logo ont déménagé dans `reporting/` à côté, de
  sorte que tout ce dont le rapport est fait est écrit dans le type de fichier
  que c'est.
- `reporting/sync.py` les recopie dans `saggio/data/report/`, qui est ce que la
  roue livre, et `--check` signale la divergence sans écrire. Un test de contrat
  le lance, de sorte qu'éditer la copie empaquetée par erreur fait échouer la
  construction.
- Un jeton que le rendu ne remplit pas lève désormais une exception, parce qu'un
  rapport contenant un `{{BODY}}` littéral serait pire qu'un échec.
- Rien n'a changé dans la page rendue : le même document en sort.
- Une valeur que le rendu substitue n'est plus elle-même scrutée à la recherche
  de jetons. La coquille est remplie en une passe, si bien qu'un modèle dont les
  notes contiendraient `{{SCRIPT}}` ne peut plus voir ce texte remplacé par le
  script du rapport.

### Des prix lus, pas grattés

- `saggio audit --fetch-prices` cherche ce que facturent réellement les API qu'un
  dépôt appelle. Rien n'analyse une page tarifaire et rien ne demande à un modèle
  de langue ce qu'elle dit : un prix lu sur une page marketing échoue
  silencieusement et faussement, en renvoyant l'ancien chiffre barré, le palier
  entreprise, ou le tarif d'entrée mise en cache au lieu du tarif d'entrée. Seules
  les sources publiées *en tant que données* sont lues. Désactivé par défaut,
  parce que c'est la seule partie d'un audit qui atteint le réseau au-delà d'un
  modèle local.
- Un prix se rapporte à un modèle, pas à un fournisseur : la passe statique
  trouve donc maintenant les identifiants de modèles que le code nomme —
  `model="gpt-4o"` et ses orthographes — et cite la ligne qui les nomme. Un
  modèle détenu dans une variable n'est pas deviné, parce que savoir ce qu'elle
  contient supposerait d'exécuter le programme.
- Un modèle est facturé sur plusieurs axes à la fois. `gpt-4o` publie huit
  tarifs, et tous sont enregistrés, chacun comme une grandeur avec son unité, sa
  monnaie, son statut, sa source et sa date. Une clé de tarif pour laquelle cette
  version n'a pas de nom lisible garde l'orthographe de la source plutôt que
  d'être renommée en silence.
- C'est le tarif qui devient connu ; l'usage, non. Combien de jetons une unité de
  travail dépense n'est pas quelque chose que lire un dépôt établit : cela reste
  `TODO` et le modèle montre quelle moitié manque.

### La provenance, à côté du statut d'honnêteté

- Une grandeur peut porter `source_kind` : `stated`, `first-party` ou
  `aggregator`. Le statut ne pouvait pas l'exprimer — le prix publié par un
  fournisseur lui-même et sa transcription par une communauté sont tous deux, à
  juste titre, `estimated` — et la différence est exactement le genre de chose que
  ce paquet existe pour rendre visible.
- `saggio diff` échoue quand la provenance d'un prix s'affaiblit, comme il échoue
  déjà quand un statut s'affaiblit. Le même nombre venu d'une moins bonne
  citation est une régression.
- **Schéma 2.1.** `source_kind` sur une grandeur et `models_called` au niveau
  supérieur, tous deux optionnels et additifs, si bien que tout modèle en 2.0
  valide sans changement.

### Corrigé

- `saggio diff` plantait avec une `TypeError` dès qu'une grandeur gagnait ou
  perdait son nombre, ce qui est le changement le plus ordinaire qui soit :
  auditer un dépôt, obtenir un `TODO`, le mesurer, et comparer. Un côté sans
  nombre se lit maintenant `no number`, dans les deux sens, et la barrière fait
  toujours échouer l'exécution qui repart d'une mesure vers un champ ouvert.
- Une machine munie d'un accélérateur que le catalogue ne sait pas nommer ne
  reçoit plus une figure de puissance d'où l'accélérateur a discrètement disparu.
  Plusieurs centaines de watts s'évanouissaient d'une somme qui continuait de
  s'appeler le total de plaque de cette machine ; la figure est maintenant un
  `TODO` nommant la ligne à ajouter.
- Une tranche exécutée avec le profileur par fonction attaché le dit. `cProfile`
  facture à l'appel, si bien qu'une charge riche en appels peut prendre près du
  double sous lui, et c'est ce temps mural gonflé que chaque figure d'énergie, de
  carbone et d'argent en aval multiplie. L'avertissement nomme `--no-profile`.
- Un dépôt qui énonce sa taille à plusieurs endroits, sous plusieurs clés, ne
  reçoit plus une phrase de conflit prétendant qu'une figure « a été utilisée »
  alors que rien ne l'a lue. Seule la clé que la lecture a effectivement retenue
  le dit ; les autres disent quelle figure a servi à la place.
- Un fichier de test à l'intérieur de `.venv`, `node_modules` ou d'une autre
  arborescence vendorisée ne compte plus comme une suite de tests de ce dépôt, ce
  qui est ce qui faisait proposer à l'audit d'exécuter les tests de quelqu'un
  d'autre.
- `total_money` ne renvoie plus un `TODO` portant un nombre, ce dont le
  validateur lui-même s'inquiétait. Une somme à laquelle il manque un terme n'est
  pas le total : le nombre est donc retiré et ce à quoi les termes connus
  s'élèvent est conservé dans les notes. **Cela change un contrat public** : les
  appelants qui lisaient `.value` sur un total partiel lisent maintenant `None`.
- Le validateur signale une déclaration de dimension qui entre en collision avec
  une dimension intégrée ou avec une déclaration antérieure. Le registre a
  toujours écarté celle qui entrait en collision ; jusqu'ici il le faisait sans un
  mot, laissant le modèle dire une chose et l'outil en lire une autre.

### Renommé

- Les deux variables d'environnement gardaient le nom du projet mort. Ce sont
  maintenant `SAGGIO_COUNTRY` et `SAGGIO_MODEL`, là où elles étaient
  `RUNNING_CODE_COST_COUNTRY` et `RUNNING_CODE_COST_MODEL`. Rien n'avait été
  publié sous l'ancien nom, donc les anciennes orthographes ne sont pas
  maintenues en état de marche.
- Le module de catalogue pointait vers un `saggio.catalog.contribute` qui
  n'existe pas. Il nomme `add_row` et `saggio catalog add`, qui existent.

### Documentation

- `docs/` contient une carte de chaque document du dépôt, en anglais et en
  français, et `docs/api.md` : la référence de la bibliothèque, une ligne par nom
  dans `__all__`, écrite à partir des docstrings par `docs/sync_api.py`. Un test
  de contrat lance `--check`, de sorte que la référence ne peut pas diverger du
  paquet.
- Les deux variables d'environnement sont documentées, dans les deux livres de
  recettes, à côté d'`OLLAMA_HOST`. Elles faisaient partie de la surface publique
  et n'apparaissaient dans aucun document.
- Les livres de recettes disent ce que coûte le profil par fonction, et nomment
  `--no-profile`.
- `saggio machine` est montré dans les deux README, qui listaient tous les autres
  verbes.
- L'environnement conda installait les dépendances du paquet mais jamais le
  paquet, si bien que `conda env create` laissait un lecteur sans commande
  `saggio`. Deux tests de contrat le surveillent désormais, et surveillent les
  fichiers `requirements*.txt` en regard de `pyproject.toml`.
- Le README anglais montrait le logo à ses 1 254 pixels pleins là où le français
  le montrait à 120.

### Intégration continue

- Le déclencheur de poussée surveillait `main` alors que la branche par défaut du
  dépôt est `master`, si bien qu'aucune poussée n'a jamais lancé les
  vérifications. Il surveille les deux.

## 1.0.0 — 2026-09-13

Première version.

### Le modèle

- **Schéma 2.0.** Un modèle de coût est un fichier YAML où chaque nombre vit dans
  une *grandeur* : une valeur avec son unité, sa monnaie quand c'est de l'argent,
  son statut d'honnêteté, sa provenance, et les chemins des nombres dont elle est
  dérivée.
- **La règle du maillon faible est générale.** Parce qu'une grandeur nomme ses
  entrées dans `derived_from`, le validateur résout ces chemins et applique la
  règle à ce qu'il y trouve. Une dimension inventée par un projet est vérifiée
  exactement aussi soigneusement que le carbone, sans aucun changement dans ce
  paquet.
- **Chaque nombre vit dans une grandeur.** Le validateur parcourt tout le fichier
  et signale tout nombre hors d'une grandeur, sauf sur une courte liste de
  chemins structurels que le schéma nomme. Un bloc dont cette version n'a jamais
  entendu parler ne peut pas faire passer une figure sous les règles d'honnêteté.
- **Les dimensions sont porteuses.** Les coûts sont indexés par dimension dans
  une table `costs`, et un projet déclare ses propres dimensions en tête du
  modèle. Le validateur, les deux rapports et la barrière de dérive lisent tous
  le registre.
- **L'argent dit quel argent.** Une valeur sur une dimension monétaire porte une
  monnaie ISO 4217, pour qu'un rapport n'additionne jamais des dollars et des
  euros.

### Découvrir ce que les choses coûtent

- `audit` lit un dépôt : langages, forme de la charge de travail, cadres
  logiciels, travail accompli par une exécution complète, et quelles API payantes
  il appelle, avec la ligne qui le prouve.
- `audit --run` exécute une tranche plafonnée du vrai point d'entrée après un
  consentement explicite demandé une seule fois, la chronomètre, lit le compteur
  de puissance de la machine là où le système d'exploitation en offre un, et
  profile où le temps est passé.
- La part de l'exécution complète que représente la tranche est lue dans la
  configuration du dépôt lui-même, si bien que la projection sur l'exécution
  entière est de l'arithmétique et non une supposition.
- Quand deux fichiers ne s'accordent pas sur la taille d'une exécution, l'audit
  signale le désaccord au lieu de le trancher en silence.
- `--source-accelerator` énonce la machine pour laquelle une mesure vaut, ce qui
  est ce qui rend possible, tout simplement, de projeter d'un portable vers un
  accélérateur de centre de données.
- La projection d'une machine à l'autre tient compte de la précision : elle
  refuse une précision pour laquelle le catalogue ne cite pas de débit, et dit
  laquelle.
- Un modèle local, via Ollama, est interrogé sur la forme du travail et sur rien
  d'autre. Tout ce qu'il renvoie de numérique est jeté avant d'atteindre le
  modèle.

### Les catalogues

- Matériel, réseaux, fournisseurs, instances et services, sous forme de YAML
  porteurs de provenance livrés dans la roue et extensibles par utilisateur au
  moyen d'une surcouche.
- Une ligne ne peut pas être ajoutée sans un `source_url` et une
  `retrieved_date`.
- La péremption correspond au fait : les tarifs et les mix électriques expirent en
  un mois, les puissances de fiches techniques en un an, et une ligne qui
  n'affirme aucun nombre n'expire jamais.
- `catalog freshness` sort en erreur quand quelque chose est périmé, pour qu'un
  job planifié puisse poser la question.

### Les rapports

- Du Markdown pour une pull request, et une page HTML autonome pour tous les
  autres : hors ligne, en clair et en sombre, en anglais et en français, avec un
  panneau qui recalcule le modèle pour un autre pays dans le navigateur.
- La feuille de style, le script et les traductions sont des fichiers,
  empaquetés avec la roue et lus via `importlib.resources`.
- La figure de dérivation est dessinée à partir des arêtes `derived_from` du
  modèle lui-même, si bien qu'elle montre l'arithmétique qu'un modèle fait
  vraiment.
- Word et PDF via `md2star`, en extra optionnel.

### Rester honnête

- `diff` échoue sur un coût qui a empiré au-delà d'un seuil, sur un statut qui
  s'est affaibli même quand le nombre n'a pas bougé, et sur une grandeur qui a
  disparu.
- `validate` renvoie un verdict avec un chemin et une phrase pour chaque
  problème, et les avertissements ne font jamais échouer un modèle : un modèle
  qui admet qu'il est incomplet est honnête.

### Les surfaces

- Une bibliothèque, et une ligne de commande qui en est un adaptateur mince.
  Chaque verbe passe par une fonction publique, si bien que la ligne de commande
  ne peut rien faire qu'un appelant de la bibliothèque ne puisse pas.
- Un skill d'agent sous `skills/`.
