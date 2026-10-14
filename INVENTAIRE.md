# Ranger ces chiffres dans un bilan GES

🇫🇷 Français · [🇬🇧 INVENTORY.md](INVENTORY.md)

Cette page s'adresse à celui qui doit **déclarer** les chiffres, pas à celui qui
les a produits. Elle dit sur quelle ligne d'un bilan d'émissions de gaz à effet
de serre se range chacun des nombres de cet outil, ce qu'il donne à un
vérificateur, et — c'est la moitié vraiment utile — ce qu'il ne donne pas et ne
fera pas semblant de donner.

## L'écart que cela comble

Une équipe technique transmet un nombre à une équipe RSE : *« entraîner ce
modèle émet 40 kgCO2e »*. Trois questions suivent immédiatement, et d'ordinaire
aucune n'a de réponse.

1. **À qui est cette émission ?** Scope 2 si la machine est à vous, scope 3
   catégorie 1 si vous l'avez louée. Même code, même kilowattheure, et ce n'est
   pas la même entreprise qui le déclare.
2. **Comment a-t-il été obtenu ?** Une mesure, un chiffre constructeur, un
   coefficient publié, ou l'estimation de quelqu'un — et les quatre ne se valent
   pas devant un commissaire aux comptes.
3. **Par quelle méthode ?** Pour le scope 2 il y en a deux, toutes deux exigées,
   et une moyenne de réseau n'en est qu'une.

Cet outil répond aux trois dans l'artefact lui-même, parce qu'il ne produit
jamais un nombre sans elles. `saggio scopes cost_of_running.yaml` imprime les
réponses ; chaque rapport rendu les porte dans une section à part.

## Quel scope, et pourquoi

Le GHG Protocol tranche le scope avec un seul fait : **qui achète l'électricité
et possède la machine.** Ce fait est déjà dans le modèle, sous
`deployment.provider`, et le catalogue des fournisseurs le note sous
`operated_by`.

| Où ça tourne | L'électricité | Le matériel |
|---|---|---|
| Votre serveur, votre portable | **Scope 2** | **Scope 3, catégorie 2** — biens d'équipement |
| AWS, GCP, Azure, OCI, un cloud GPU | **Scope 3, catégorie 1** — biens et services achetés | **Scope 3, catégorie 1** — même ligne |
| Un fournisseur que personne n'a classé | *aucun scope* — posé en question, jamais deviné | *aucun scope* |

Trois conséquences, et chacune est une erreur que les équipes commettent
couramment.

**Le cloud n'est pas votre scope 2.** Vous avez acheté un service.
L'électricité est le scope 2 du fournisseur et le matériel son scope 3
catégorie 2 ; les deux vous parviennent comme un service acheté, en catégorie 1.
Le déclarer en scope 2 le compte deux fois avec la publication du fournisseur.

**Le matériel que vous possédez est un bien d'équipement, pas un bien acheté.**
La norme sépare la catégorie 1 de la catégorie 2 selon que l'actif dure plus
d'un an. Un serveur dure — ce qui est aussi la raison pour laquelle l'empreinte
est amortie sur le travail qu'il fait plutôt qu'imputée en une fois l'année de
l'achat.

**Un fournisseur que le catalogue ne classe pas n'obtient aucun scope.** Pas de
valeur par défaut, pas d'approximation au plus proche. Les deux réponses
diffèrent par *quelle entité juridique déclare l'émission*, et une mauvaise a
exactement l'air aussi propre qu'une bonne.

## Scope 2 : on ne vous donne qu'une moitié d'une paire exigée

Les intensités carbone ici sont des moyennes nationales de réseau, lues chez
[Ember](https://ember-energy.org/data/yearly-electricity-data/). Une moyenne de
réseau **est** la méthode *location-based*, par définition — elle ne porte aucun
ajustement pour un quelconque instrument contractuel.

Le chiffre *market-based* est un autre nombre, et le [Scope 2 Guidance](https://ghgprotocol.org/scope-2-guidance)
du GHG Protocol exige les deux partout où des instruments contractuels existent.
Dans les normes européennes la paire est explicite : le scope 2 brut se publie
*location-based et market-based*.

Cet outil ne produira pas le chiffre market-based, parce qu'il ne se dérive pas
d'une moyenne de réseau. Il se construit à partir de l'une de trois choses, par
ordre de préférence :

1. le facteur d'émission propre de votre fournisseur, pour le contrat que vous
   avez ;
2. les instruments contractuels que vous détenez — garanties d'origine, RECs,
   un PPA ;
3. à défaut des deux, le **mix résiduel** de votre marché, qui existe précisément
   pour que l'électricité non revendiquée ne soit pas comptée comme propre par
   défaut.

Les rapports disent donc que leur chiffre est location-based, et que l'autre
manque et pourquoi. C'est une liste de courses plutôt qu'un refus : si vous
détenez un facteur fournisseur, enregistrez-le comme votre propre dimension et
cet outil le validera, le rendra et le surveillera exactement comme le carbone.

## Ce qu'un vérificateur obtient

Une assurance modérée est surtout un exercice de documentation, et c'est là
qu'un tableur de chiffres carbone échoue le plus durement. Chaque grandeur ici
porte quatre choses, imposées plutôt qu'encouragées :

| | |
|---|---|
| **Un statut** | `measured`, `estimated`, `placeholder` ou `TODO`. Un chiffre dérivé ne peut jamais se prétendre mieux fondé que son entrée la plus faible, et le validateur rejette un modèle qui s'y essaie. |
| **Sa provenance** | Une URL et la date à laquelle quelqu'un l'a lue — sur une page qu'un lecteur peut réellement ouvrir, ce qui est vérifié. |
| **Sa dérivation** | Les entrées dont il vient, nommées, l'arithmétique étant recalculée à partir d'elles et refusée si elle ne se recoupe pas à un pour cent près. |
| **Une fenêtre de fraîcheur** | Chaque colonne de catalogue périme à son propre rythme, et le garde-fou fait échouer une construction qui livrerait un chiffre que personne n'a relu. |

Deux conséquences à énoncer clairement à un vérificateur.

**La déclaration sur les estimations est déjà écrite.** On demande à un
déclarant de dire quelle part de son inventaire repose sur des estimations
plutôt que sur des relevés. Chaque nombre ici le dit de lui-même ;
`saggio scopes --json` les compte.

**Un chiffre ouvert reste ouvert.** Un pays que personne n'a renseigné donne un
`TODO`, pas un zéro. Un fournisseur qui ne publie aucun chiffre d'eau donne un
`TODO`, pas un chiffre plausible. Rien ici ne comblera un trou par une moyenne
en la laissant se lire comme une mesure — c'est le mode de défaillance qui rend
un chiffre carbone invérifiable, et celui que toute cette conception existe pour
empêcher.

## Là où cela ne suffit pas

La moitié utile de toute revendication de conformité est celle qui échoue.

- **Ce n'est pas votre empreinte informatique.** Cela couvre le calcul pour une
  unité de travail. Ni postes de travail, ni transit réseau, ni stockage au
  repos, ni bureaux, ni déplacements. Un modèle de coût logiciel est une entrée
  d'un bilan, pas un bilan.
- **Pas de scope 2 market-based**, comme ci-dessus.
- **Pas de fin de vie, ni de comptabilité biogénique ou d'absorptions.** Les
  empreintes matérielles publiées vont du berceau à la sortie d'usine et
  excluent la phase d'usage et l'élimination ; cet outil rapporte ce qu'elles
  couvrent et pas un gramme de plus. Rien n'est compensé contre des absorptions
  ou des crédits, ce qui est aussi ce que les normes exigent : du brut.
- **Le scope 3 catégorie 1 d'un cloud est un modèle, pas une facture.** Là où
  votre fournisseur publie un chiffre par client, c'est ce chiffre qui fait foi
  et celui-ci qui est un recoupement. La plupart ne publient rien à cette
  finesse, ce qui est la raison de le calculer.
- **Le catalogue matériel est petit**, délibérément. Huit empreintes sont
  livrées et tout le reste rapporte `TODO` avec une phrase disant que personne
  n'en a lu une — ce qui n'est pas la même chose que sa fabrication aurait été
  gratuite. [`NORMES.md`](NORMES.md)
  en donne le tableau et les refus.
- **Ce n'est pas une opinion d'assurance**, et aucun outil ne l'est.

## Les règles contre lesquelles ceci est écrit

Les dates et la numérotation bougent ; celles-ci ont été vérifiées le
2026-10-14.

**GHG Protocol.** Le [Corporate Standard](https://ghgprotocol.org/corporate-standard)
définit les scopes, le [Scope 3 Standard](https://ghgprotocol.org/corporate-value-chain-scope-3-standard)
les quinze catégories, et le [Scope 2 Guidance](https://ghgprotocol.org/scope-2-guidance)
l'obligation de double déclaration. Le Scope 2 Guidance est lui-même en révision.

**CSRD, après l'Omnibus.** La [directive (UE) 2026/470](https://eur-lex.europa.eu/eli/dir/2026/470/oj/eng)
a été publiée le 26 février 2026 et est entrée en vigueur le 18 mars 2026. Elle
restreint fortement la population déclarante — en gros, les entreprises
au-dessus de 1 000 salariés et 450 M€ de chiffre d'affaires net — et reporte les
vagues suivantes. La vague 1 est inchangée. **Si vous lisez ceci pour savoir si
vous êtes assujetti, lisez la directive et demandez à vos conseils ; cette page
est la documentation d'un outil, pas un conseil.**

**ESRS E1, et sa renumérotation.** Les scopes 1, 2 et 3 bruts relevaient de
l'exigence de publication **E1-6** ; dans les normes amendées chaque exigence à
partir d'E1-2 se décale de deux, et la même publication devient **E1-8**. Son
texte énonce la paire sur laquelle cette page insiste : scope 2 *location-based
et market-based*.

**En France, à part.** Le bilan d'émissions de gaz à effet de serre de
l'[article L. 229-25 du code de l'environnement](https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000039369665)
est une obligation propre, avec son propre dépôt, publié sur
[bilans-ges.ademe.fr](https://bilans-ges.ademe.fr/). Depuis le décret
n° 2022-982 il couvre les émissions indirectes significatives — le scope 3 —
pour les organisations concernées, et c'est là qu'un chiffre logiciel de ce
genre se rangerait.

## Le faire

```bash
# Où va chaque coût de ce modèle, et pourquoi.
saggio scopes cost_of_running.yaml

# La même chose, pour une chaîne qui la lit.
saggio scopes cost_of_running.yaml --json

# Un rapport qui porte le rangement à côté des chiffres.
saggio render cost_of_running.yaml -f html -o cost_of_running.html

# Un document, pour un fichier qui part chez un vérificateur.
saggio render cost_of_running.yaml -f docx -o cost_of_running.docx
```

Le scope se lit sur le fournisseur : un modèle qui n'en nomme aucun se le voit
dire, plutôt que d'être rangé au jugé. Pour classer un fournisseur à vous,
donnez à sa ligne de catalogue `operated_by: self` ou `operated_by: vendor`.

## Sources

- [GHG Protocol Corporate Standard](https://ghgprotocol.org/corporate-standard) · [Corporate Value Chain (Scope 3) Standard](https://ghgprotocol.org/corporate-value-chain-scope-3-standard) · [Scope 2 Guidance](https://ghgprotocol.org/scope-2-guidance)
- [Directive (UE) 2026/470](https://eur-lex.europa.eu/eli/dir/2026/470/oj/eng) — la directive Omnibus I modifiant la CSRD.
- [ESRS E1 amendée par l'EFRAG](https://www.efrag.org/sites/default/files/media/document/2025-12/November_2025_ESRS_E1.pdf) — où l'exigence GES est renumérotée et la paire location-based / market-based réaffirmée.
- [Article L. 229-25 du code de l'environnement](https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000039369665) · [bilans-ges.ademe.fr](https://bilans-ges.ademe.fr/) — le bilan GES réglementaire français et son dépôt.
- [Base Empreinte de l'ADEME](https://base-empreinte.ademe.fr/) — la base de facteurs d'émission française, pour les chiffres que cet outil ne porte pas.
- [Données annuelles d'électricité d'Ember](https://ember-energy.org/data/yearly-electricity-data/) — les intensités réseau d'ici, location-based par construction.

---

[`NORMES.md`](NORMES.md)
fait le même exercice face à la norme Software Carbon Intensity.
[`MESURER.md`](MESURER.md)
dit d'où vient le chiffre d'énergie.
[`PAYSAGE.md`](PAYSAGE.md)
situe cet outil parmi ceux qui répondent à des questions voisines.
