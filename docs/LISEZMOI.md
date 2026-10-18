# Documentation

🇫🇷 Français · [🇬🇧 README.md](README.md)

Où chercher, et à quelle question chaque document répond. Tout est écrit à la
main sauf [`api.md`](api.md), qui est dérivé des docstrings.

## Commencer ici

| Document | La question à laquelle il répond |
|---|---|
| [`../LISEZMOI.md`](../LISEZMOI.md) | Qu'est-ce que c'est, et pourquoi est-ce bâti ainsi ? |
| [`../EXEMPLES.md`](../EXEMPLES.md) | Comment je fais ce pour quoi je suis venu ? |
| [`../GALERIE.md`](../GALERIE.md) | Que dit-il vraiment sur de vrais dépôts ? |
| [`../DECLENCHEURS.md`](../DECLENCHEURS.md) | Est-ce le bon outil pour ce que je demande ? |
| [`../UTILISER.md`](../UTILISER.md) | Comment l'atteindre depuis un script, un terminal, un navigateur, un agent ou Claude ? |
| [`../PAYSAGE.md`](../PAYSAGE.md) | Que vaut-il face à CodeCarbon, Scaphandre et les autres ? |
| [`../MESURER.md`](../MESURER.md) | Quels compteurs cette machine me laissera-t-elle lire, et que couvrent-ils ? |
| [`../ANALYSE.md`](../ANALYSE.md) | Lire le code, ou l'exécuter, peut-il dire sa complexité et son coût ? |
| [`../NORMES.md`](../NORMES.md) | Quelle norme est-ce, et quelle part n'est pas encore satisfaite ? |
| [`../FRONTIERES.md`](../FRONTIERES.md) | Pourquoi deux chiffres publiés pour une inférence diffèrent de trente-huit fois, et ce que devient le mien sous chaque frontière ? |
| [`../INVENTAIRE.md`](../INVENTAIRE.md) | Sur quelle ligne d'un bilan GES ces chiffres se rangent-ils, et que ne couvrent-ils pas ? |

## Référence

| Document | La question à laquelle il répond |
|---|---|
| [`api.md`](api.md) | Que me donne `import saggio` ? (en anglais) |
| [`../skills/saggio/references/schema.md`](../skills/saggio/references/schema.md) | Que peut contenir un modèle de coût ? (en anglais) |
| [`../skills/saggio/references/honesty-taxonomy.md`](../skills/saggio/references/honesty-taxonomy.md) | Que veulent dire exactement les quatre statuts ? (en anglais) |
| [`../skills/saggio/references/green-algorithms.md`](../skills/saggio/references/green-algorithms.md) | D'où vient l'arithmétique ? (en anglais) |
| [`../skills/saggio/references/code-analysis.md`](../skills/saggio/references/code-analysis.md) | Quelles analyses ont le droit de produire un nombre ? (en anglais) |
| [`../skills/saggio/references/inventory.md`](../skills/saggio/references/inventory.md) | Que peut dire un agent aux personnes qui doivent déclarer le chiffre ? (en anglais) |
| [`../JOURNAL.md`](../JOURNAL.md) | Qu'est-ce qui a changé, et est-ce que ça me concerne ? |

Le schéma et la taxonomie vivent sous `skills/` parce qu'un agent les lit aussi,
et qu'une seule copie partagée par deux lecteurs ne peut pas diverger d'elle-même.

## Travailler sur le paquet

| Document | La question à laquelle il répond |
|---|---|
| [`../CONTRIBUER.md`](../CONTRIBUER.md) | Comment j'ajoute une ligne de catalogue, ou un test ? |
| [`../CODING.md`](../CODING.md) | Dans quel style ce dépôt est-il écrit ? (en anglais) |
| [`../reporting/LISEZMOI.md`](../reporting/LISEZMOI.md) | Comment je change l'allure d'un rapport ? |

## Régénérer la page d'API

```bash
python docs/sync_api.py            # l'écrire
python docs/sync_api.py --check    # signaler la dérive, sortir en 1, ne rien écrire
```

Un test de contrat lance `--check` : une docstring modifiée sans régénérer la
page fait échouer le build au lieu de livrer une référence périmée.
