# La ligne énergie d'un dossier au titre du règlement sur l'intelligence artificielle (IA)

🇫🇷 Français · [🇬🇧 ANNEX-XI.md](ANNEX-XI.md)

Cette page s'adresse au fournisseur d'un modèle d'IA (intelligence artificielle) à usage général qui doit
écrire quelle a été la consommation énergétique de son modèle. Elle dit quelle
part de cette phrase ce paquet traite, quelle part il ne traite pas, et ce que
la Commission est encore en train d'écrire. **Les dates et la numérotation
bougent ; celles-ci ont été vérifiées le 2026-10-18, et ceci est la
documentation d'un outil, pas un conseil juridique.**

## Ce que le règlement demande, et la phrase autour de laquelle ce paquet est bâti

L'annexe XI impose au fournisseur d'un modèle d'IA à usage général de
documenter, parmi beaucoup d'autres choses, les ressources de calcul utilisées
pour entraîner le modèle et sa **consommation énergétique connue ou estimée**.
Là où la consommation n'est pas connue, le règlement autorise explicitement une
estimation **à partir du calcul utilisé**.

Cette autorisation est toute la méthode de ce paquet, inscrite dans la loi : la
puissance multipliée par le temps donne l'énergie, et là où la puissance n'a
jamais été mesurée, un chiffre sourcé prend sa place, étiqueté comme une
estimation et non comme une lecture.

**Les dates, parce qu'elles sont la raison de s'y mettre maintenant.** Le devoir
de documentation s'applique aux modèles mis sur le marché depuis le 2 août 2025.
La Commission peut faire appliquer le chapitre relatif aux modèles à usage
général depuis le **2 août 2026**, avec des amendes allant jusqu'à 3 % du
chiffre d'affaires annuel mondial ou 15 millions d'euros. Les modèles mis sur le
marché avant le 2 août 2025 ont jusqu'au **2 août 2027**.

## Ce qui reste à écrire, et pourquoi cela compte

La méthodologie n'est pas figée. La Commission a mené entre avril et juin 2026
une consultation ciblée sur **la mesure de la consommation énergétique et des
émissions des modèles et systèmes d'IA**, adressée aux organisations qui les
développent et les déploient. L'AI Office doit en publier une synthèse agrégée,
et le règlement habilite la Commission à adopter des actes délégués précisant
les méthodes de mesure et de calcul **« en vue de permettre une documentation
comparable et vérifiable »** — un dispositif d'étiquetage énergétique étant cité
comme issue possible.

Deux mots de cette formule sont tout le cahier des charges de ce paquet.
*Comparable* veut dire que la frontière et l'unité doivent voyager avec le
chiffre, sans quoi deux dossiers ne se lisent pas l'un contre l'autre —
[`FRONTIERES.md`](FRONTIERES.md) montre ce qui arrive quand ce n'est pas le cas.
*Vérifiable* veut dire que quelqu'un d'autre que l'auteur doit pouvoir le
contrôler, ce à quoi servent une URL (Uniform Resource Locator) de source, une date de lecture et une
dérivation recalculable.

## Ce que ce paquet donne à un déclarant, ligne à ligne

| Ce que demande l'annexe XI | Ce que porte un modèle de coût | Où |
|---|---|---|
| Les ressources de calcul utilisées | la machine, son processeur et son accélérateur, les cœurs, le temps mesuré | `deployment`, `measurement` |
| La consommation énergétique connue | une figure marquée `measured`, avec le compteur qui l'a produite nommé | `scenarios[].costs.energy` |
| La consommation énergétique estimée | la même figure marquée `estimated`, nommant l'hypothèse de puissance d'où elle vient | `derived_from` |
| Une estimation à partir du calcul utilisé | la chaîne Green Algorithms, sourcée à l'article | `assumptions.power_draw`, `assumptions.pue` |
| Quelque chose qu'un lecteur peut vérifier | une URL de source, la date de lecture, et une dérivation recalculée à la validation | chaque grandeur |
| Quelle part de l'exécution complète c'est | l'exposant d'échelle, mesuré sur plusieurs tailles, avec sa qualité d'ajustement | `measurement.scaling` |

La part d'un dossier qui repose sur des estimations plutôt que sur des lectures
— ce qu'un processus d'assurance demande en premier — est comptée et non
affirmée : `saggio scopes --json` la rapporte, parce que chaque nombre dit déjà
ce qu'il est.

## Ce qu'il ne fait pas, dit franchement

- **Ce n'est pas un dossier, et ce n'est pas un conseil.** Savoir si tel modèle
  est assujetti, et ce que l'annexe XI exige d'autre, relève du règlement et de
  vos conseils. Ce paquet produit un artefact dont une ligne a besoin.
- **Il couvre une unité de travail sur une machine.** Un entraînement sur un
  cluster n'est couvert que si la mesure a eu lieu sur ce cluster ; sinon les
  chiffres décrivent la machine qui a fait la lecture, et le modèle le dit dans
  `deployment.machine_provenance`.
- **Il documente l'énergie, pas le reste de l'annexe.** Les données, le droit
  d'auteur, les choix de conception et les évaluations sont ailleurs dans le
  même document, pas ici.
- **Il n'inclut pas le carbone incorporé dans la ligne énergie, parce que le
  règlement ne le demande pas.** La question énergétique du règlement est plus
  étroite que la spécification Software Carbon Intensity que ce paquet
  implémente : un modèle qui satisfait SCI répond à l'annexe XI avec de la
  marge, l'inverse n'est pas vrai. [`NORMES.md`](NORMES.md) a la comparaison.

## Ce qu'un fournisseur en ferait concrètement

Mesurer une tranche représentative sur le matériel où le modèle tourne vraiment,
avec `saggio audit --run --scaling-steps 3` pour que la projection sur
l'exécution complète porte un exposant mesuré plutôt qu'une hypothèse. Commiter
le modèle à côté du code. Le relancer à chaque version, et laisser `saggio diff`
casser la construction quand une figure bouge : un devoir de documentation
satisfait une fois et jamais relu est exactement le mode d'échec que tout le
mécanisme de fraîcheur de ce paquet existe pour empêcher.

## Sources

- [Exigences d'efficacité énergétique au titre du règlement IA](https://www.whitecase.com/insight-alert/energy-efficiency-requirements-under-eu-ai-act) — le devoir énergie de l'annexe XI, les dates et les sanctions.
- [Consultation ciblée sur la mesure de la consommation énergétique et des émissions des modèles d'IA](https://digital-strategy.ec.europa.eu/en/consultations/targeted-consultation-measuring-energy-consumption-and-emissions-ai-models-and-systems) — ce que la Commission a demandé, et ce qu'elle compte en faire.
- [SCI pour l'IA et la conformité au règlement IA](https://greensoftware.foundation/policy/research/sci-ai-eu-ai-act/) — la mise en correspondance par la Green Software Foundation.
- [Annexe XI — documentation technique de l'intelligence artificielle à usage général (GPAI)](https://artificialintelligenceact.eu/ai-act-explorer/) — le texte lui-même.
