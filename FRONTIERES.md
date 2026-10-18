# La frontière est la réponse

🇫🇷 Français · [🇬🇧 BOUNDARIES.md](BOUNDARIES.md)

Deux entreprises ont publié en 2026 un chiffre carbone pour une inférence, et
les deux chiffres sont séparés de plus d'un ordre de grandeur.

| | Chiffre | Frontière | Méthode |
|---|---|---|---|
| [Google, prompt texte Gemini médian](https://cloud.google.com/blog/products/infrastructure/measuring-the-environmental-impact-of-ai-inference) | 0,24 Wh, **0,03 gCO2e**, 0,26 mL d'eau | accélérateur, hôte, surcharge du centre de données **et capacité machine au repos** | électricité **market-based** |
| Mistral, réponse moyenne de 400 jetons | **1,14 gCO2e** | l'infrastructure de service **et la fabrication du matériel** | **location-based**, AFNOR Frugal AI |

Environ un facteur trente-huit, et **aucune des deux n'esquive**. L'une compte
l'électricité qu'un contrat a payée et la capacité réservée pour vous servir ;
l'autre compte la moyenne du réseau et les usines. Elles répondent à deux
questions différentes qui partagent une phrase.

C'est toute la proposition de ce paquet, démontrée par quelqu'un d'autre : **un
chiffre sans sa frontière n'est pas un chiffre.** Cette page prend un modèle
commité dans ce dépôt et montre ce que son nombre devient sous chaque frontière
— y compris les deux qu'il refuse de produire, et ce que chaque refus
demanderait.

## Le modèle

[`examples/request.yaml`](examples/request.yaml) : une requête `/scopes` traitée
de bout en bout, mesurée sur un Apple M2 Max en France, deux cents requêtes dans
un seul interpréteur.

```bash
saggio scopes examples/request.yaml
saggio next examples/request.yaml
```

Mesuré : un temps d'exécution de 0,0038534 s et une machine tirant **17,98 W**,
lus au compteur et non sur la fiche technique que le paquet aurait supposée,
laquelle annonce 83,76 W.

## La même requête, sous quatre frontières

| Frontière | Carbone par requête | Statut |
|---|---|---|
| Le processeur et sa mémoire seuls, location-based | 7,93e-07 gCO2e | **calculé** |
| Plus la surcharge du bâtiment (PUE 1,5), location-based — *le défaut de ce paquet* | 1,19e-06 gCO2e | **calculé** |
| Plus un contrat, market-based — *la forme de Google* | — | **refusé** : demande `assumptions.market_carbon_intensity` |
| Plus la fabrication du matériel — *la forme AFNOR* | — | **refusé** : demande une empreinte pour cette machine et une durée de vie |

Les deux premières ne diffèrent que par la surcharge du centre de données :
**50 %**, à partir d'une seule hypothèse. C'est le petit bout de l'échelle.

## Ce que ferait la fabrication, sur du matériel que le catalogue connaît

Ce portable n'a aucune empreinte carbone produit publiée, donc la quatrième
ligne ci-dessus reste ouverte plutôt que devinée. Mais le catalogue porte le
chiffre ISO 14067 de NVIDIA pour une HGX H100, **164,0 kgCO2e** par huitième de
carte, vérifié par un tiers et lu le 2026-10-01. Amorti sur les mêmes
0,0038534 s d'exécution :

| Durée de vie du matériel | Carbone incorporé par requête | Face à l'opérationnel 1,19e-06 |
|---|---|---|
| 3 ans | 6,68e-06 gCO2e | **5,6×** |
| 4 ans | 5,01e-06 gCO2e | **4,2×** |
| 6 ans | 3,34e-06 gCO2e | **2,8×** |

Relisez. Sur du matériel de centre de données, **la fabrication domine une
requête courte de trois à six fois l'électricité** — et la durée de vie seule,
que personne hors de votre parc ne peut vous dire, **fait varier la réponse d'un
facteur deux**. Un chiffre qui l'omet n'est pas un chiffre prudent : c'est un
autre chiffre.

Les durées de vie publiées se groupent entre trois et six ans, et c'est
pourquoi ce paquet n'en choisit aucune pour vous et tient
`assumptions.hardware_lifetime` ouvert jusqu'à ce que quelqu'un l'énonce.

## Cinq questions à poser à tout chiffre publié

Avant de comparer deux nombres pour la même charge de travail, posez ce que la
paire ci-dessus rend incontournable :

1. **Quelle est l'unité ?** Un prompt, une réponse de quatre cents jetons, une
   requête, un entraînement. Aucune ne se convertit dans l'autre.
2. **Où s'arrête la frontière ?** Accélérateur, hôte, bâtiment, capacité au
   repos, usines, fin de vie.
3. **Quelle méthode de scope 2 ?** Location-based suit le réseau, market-based
   suit un contrat. Elles peuvent différer d'un facteur dix et les deux sont
   exigées.
4. **La fabrication est-elle dedans ?** Sur des requêtes courtes, c'est
   généralement le terme le plus gros.
5. **Mesuré ou modélisé, et par quoi ?** Un compteur, une fiche technique, une
   moyenne de flotte, un coefficient publié.

Chaque rapport que ce paquet produit répond aux cinq sur sa propre page, ce qui
est la seule raison pour laquelle ses nombres peuvent être posés à côté de ceux
de quelqu'un d'autre.

## Sources

- [Measuring the environmental impact of AI inference](https://cloud.google.com/blog/products/infrastructure/measuring-the-environmental-impact-of-ai-inference) — les chiffres par prompt de Google et la frontière qu'ils couvrent.
- [Empreinte carbone produit de la HGX H100](https://images.nvidia.com/aem-dam/Solutions/documents/HGX-H100-PCF-Summary.pdf) — les 164,0 kgCO2e que cette page amortit, ISO 14067, vérifiés par un tiers.
- [Scope 2 Guidance](https://ghgprotocol.org/scope-2-guidance) — pourquoi les deux méthodes sont exigées.
- [`NORMES.md`](NORMES.md) — les quatre termes, et là où ce paquet n'est délibérément pas conforme.
- [`INVENTAIRE.md`](INVENTAIRE.md) — sur quelle ligne d'un inventaire va chaque chiffre.
