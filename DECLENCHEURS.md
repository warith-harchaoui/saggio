# Déclencheurs

À quoi sert `saggio`, et les formulations, commandes, fichiers et questions qui
doivent le faire venir. Écrit pour une personne qui décide si c'est le bon outil,
et pour un agent qui décide s'il invoque le
[skill](skills/saggio/SKILL.md). La version anglaise est
[TRIGGERS.md](TRIGGERS.md).

## En une phrase

Il répond à **ce que coûte l'exécution de ce code, par unité de travail, et à
quel point on peut faire confiance à cette réponse** : argent, temps, énergie,
carbone, eau, et toute dimension qu'une équipe enregistre, écrits dans un fichier
YAML (YAML Ain't Markup Language) qui vit à côté du code et rendus en rapports.

## Ce qu'il fait, et comment l'atteindre

| Intention | Commande | Bibliothèque |
|---|---|---|
| Démarrer un modèle de coût | `... init` | `template_text` |
| En vérifier un contre les règles | `... validate` | `validate` |
| Savoir à quelle question ouverte répondre d'abord | `... next` | `next_questions`, `questions_payload` |
| En construire un depuis un dépôt | `... audit` | `audit`, `audit_git_url` |
| Placer chaque chiffre dans un bilan gaz à effet de serre (GES) | `... scopes` | `placement`, `placements` |
| Mesurer une vraie commande | `... measure` | `run_slice` |
| Le rapporter pour des humains | `... render` | `render_markdown`, `render_html`, `render_office` |
| Casser un build sur une dérive | `... diff` | `compare` |
| Consulter ou étendre les faits | `... catalog` | `Catalog`, `add_row` |
| Demander ce qu'est cette machine | `... machine` | `detect_machine` |
| Autoriser ou refuser l'exécution de code | `... consent` | `require_consent` |

## Formulations qui doivent déclencher

Les deux vocabulaires comptent, et les deux figurent ici : beaucoup d'équipes
techniques posent la question en anglais pendant que les équipes de
responsabilité sociétale des entreprises (RSE) la posent en français, et c'est la
même question. Une interface de programmation applicative (API) payante revient
dans les deux vocabulaires.

**Coût d'exécution.** « Combien ça coûte de faire tourner ça ? », « coût par
inférence », « coût par requête », « coût d'un entraînement », « combien coûte ce
job », « coût par appel d'API », « unit economics de ce service », « notre coût
pour mille prédictions ». *"What does it cost to run this?", "cost per
inference", "cost per request", "cost per training run", "unit economics of this
service".*

**Énergie et puissance.** « Combien d'énergie ça consomme », « watts »,
« kilowattheures », « puissance appelée par cet entraînement », « mesurer
l'énergie de ce script », « combien d'électricité », « ce code est-il efficace ».
*"How much energy does this use", "power draw of this training run", "measure the
energy of this script".*

**Carbone et durabilité.** « Empreinte carbone de ce modèle », « CO2 par
inférence », « émissions de ce pipeline », « numérique responsable », « combien de
CO2 émet notre API », « rapport de durabilité pour ce service », « intensité
carbone du réseau », « Green Algorithms », « scope 2 de cette charge de travail ».
*"Carbon footprint of this model", "CO2 per inference", "green software", "grid
intensity".*

**Eau.** « Empreinte eau de cette charge en centre de données », « WUE (water usage effectiveness) »,
« combien d'eau de refroidissement ». *"Water footprint", "WUE".*

**Auditer une base de code.** « Audite ce dépôt sur son coût d'exécution »,
« qu'est-ce qui coûte cher dans ce code », « quelles API payantes sont
appelées », « ce que ce projet dépense par exécution », « où part le coût ».
*"Audit this repo for running cost", "which paid APIs does this call".*

**Projeter.** « Combien ça coûterait sur un H100 », « extrapole à partir de
cette exécution », « si on passait sur GCP (Google Cloud Platform) », « ce que
coûterait l'entraînement complet », « et si on tournait en Suède », « le coût à
un million de requêtes par jour ». *"What would this cost on an H100", "cost at
a million requests a day".*

**Déclarer et se conformer, qui est la même question par l'autre bout.** « Sous
quel scope tombe notre logiciel », « notre calcul en cloud, c'est du scope 2 ou du
scope 3 », « scope 3 catégorie 1 pour nos dépenses cloud », « il nous faut un
chiffre défendable pour la CSRD (Corporate Sustainability Reporting Directive) », « ESRS (European Sustainability Reporting Standards) E1 », « location-based et
market-based », « ce que le vérificateur doit voir », « empreinte carbone de notre
service », « bilan carbone du numérique », « facteur d'émission de notre
électricité », « un chiffre défendable pour le reporting extra-financier ».
*"Which scope does our software fall under", "we need a defensible figure for
CSRD", "what does the auditor need to see".*

**Rester honnête.** « Notre coût par requête a-t-il dérivé », « casse le build si
ça devient plus cher », « suivre le coût carbone en intégration continue », « ce
chiffre est-il encore vrai ». *"Has our cost per request drifted", "track the
carbon cost in CI".*

## Fichiers et artefacts qui doivent déclencher

- `cost_of_running.yaml` n'importe où dans un dépôt.
- Une demande d'en écrire un, d'en relire un, d'en mettre un à jour.
- Un rapport `cost_of_running.md` ou `.html`.
- Une section durabilité ou FinOps d'un README qui énonce un chiffre par unité.

## Formulations qui ne doivent *pas* déclencher

- **Facturation cloud.** « Pourquoi notre facture AWS (Amazon Web Services) était si élevée le mois
  dernier » est une question pour Cost Explorer. Cet outil modélise le coût d'une
  unité de travail à partir de principes premiers ; il ne lit pas de factures.
- **Observabilité en direct.** « Quel endpoint est lent en ce moment » est une
  question de traçage et de métriques. Cet outil mesure une tranche bornée, une
  fois.
- **Un bilan d'organisation complet.** Les bâtiments, les trajets, les
  déplacements professionnels, les achats, les ordinateurs portables. C'est le
  métier d'une plateforme de comptabilité carbone, et un modèle de coût pour une
  unité de travail en est une entrée, pas un substitut. La question voisine qui,
  elle, *doit* déclencher est plus étroite et mérite d'être séparée : **où la
  ligne du logiciel se range** dans ce bilan, ce à quoi `scopes` répond et que
  [`INVENTAIRE.md`](INVENTAIRE.md) explique.
- **Savoir si une organisation est assujettie.** La directive et ses conseils y
  répondent. Cet outil produit un chiffre et dit jusqu'où on peut lui faire
  confiance.
- **L'optimisation de code pour elle-même.** « Rends cette fonction plus rapide »
  est une question de profilage. Cet outil profile une tranche pour attribuer un
  coût, mais il ne réécrit pas votre code.
- **L'achat de matériel.** « Quel GPU (graphics processing unit) acheter »
  demande du carbone incorporé, une durée de vie et un taux d'utilisation, dont
  cet outil ne modélise aucun.

## Ce qu'il refusera, à voix haute

Il refuse plutôt que de deviner, et chaque refus nomme ce qui le lèverait.

- **Aucun pays énoncé.** Le carbone et l'argent restent ouverts. Il ne lit jamais
  un pays dans une locale. Une déduction par fuseau horaire est proposée et
  étiquetée comme une déduction.
- **Aucun chiffre d'eau publié.** L'eau reste ouverte. Il n'inventera pas une
  efficacité d'usage de l'eau.
- **Une précision que le catalogue ne cite pas.** Une projection d'une machine à
  une autre est refusée, en nommant la précision, parce que deux puces ne gardent
  pas le même rapport d'une précision à l'autre.
- **Une tranche qui a échoué ou a été écourtée.** Rien n'en est projeté, et le
  modèle dit pourquoi.
- **Une ligne de matériel qu'il n'a pas.** Il nomme l'appareil et la commande qui
  l'ajouterait.
- **Aucun consentement à exécuter du code.** `--run` ne fait rien et l'audit se
  poursuit sur la seule lecture. Une session sans terminal est refusée, jamais
  supposée.

## Ce que vaut un chiffre venu de cet outil

Chaque valeur porte un statut, et une valeur dérivée ne dépasse jamais sa plus
faible entrée :

- `measured` — un compteur de la machine l'a dit.
- `estimated` — une formule sourcée ou un chiffre publié l'a dit.
- `placeholder` — le champ est tenu ouvert ; ce n'est pas un nombre.
- `TODO` — un humain doit le fournir.

Si vous citez publiquement un chiffre de cet outil, citez son statut avec.
