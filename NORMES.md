# La norme que c'est, et la part qui lui manque encore

🇫🇷 Français · [🇬🇧 STANDARDS.md](STANDARDS.md)

Il existe une norme internationale pour ce que produit ce paquet, et elle existe
depuis 2024. La spécification **Software Carbon Intensity** —
[ISO/IEC 21031:2024](https://greensoftware.foundation/standards/sci/), écrite par
la Green Software Foundation — demande des émissions *par unité fonctionnelle de
travail*, avec la frontière déclarée, sans compensation, et avec une intensité
carbone liée au lieu.

Ce n'est pas une forme à laquelle ce paquet a été adapté. C'est la forme dans
laquelle il a été bâti, avant que personne ici n'ait lu la spécification : un
modèle de coût est par unité de travail par construction, la frontière est
écrite à côté de chaque nombre, rien ne peut être soustrait au titre d'un achat,
et l'intensité du réseau vient de là où le code tourne vraiment. Trois des
quatre termes de la spécification étaient déjà là.

Le quatrième manquait, et c'était le coûteux.

## Les quatre termes

```
SCI = (E × I + M) par R
```

| Terme | Ce que c'est | D'où il vient ici |
|---|---|---|
| **E** | L'énergie tirée par l'exécution | Mesurée sur les compteurs de la machine quand elle veut bien les donner, estimée depuis une puissance sourcée sinon. Voir [`MESURER.md`](MESURER.md). |
| **I** | L'intensité carbone de cette électricité | `assumptions.grid_carbon_intensity`, depuis le catalogue de réseaux, par pays, liée au lieu. |
| **M** | Le carbone émis pour fabriquer le matériel | `scenarios[].costs.embodied_carbon`. Nouveau, et le sujet de cette page. |
| **R** | L'unité fonctionnelle | `unit_of_work`. La première chose qu'un audit demande et celle par laquelle tout le reste est divisé. |

`E × I` est la dimension `carbon` que ce paquet a toujours rapportée. `M` est la
dimension `embodied_carbon` à côté. Le score est leur somme, et
`saggio.software_carbon_intensity` les additionne — en refusant quand l'une des
deux moitiés est ouverte, parce que rapporter l'une d'elles sous le nom d'une
norme la sous-estimerait avec l'autorité de la norme.

## M, et ce que coûte son absence

Fabriquer une carte mère HGX H100 émet **1 312 kgCO2e** avant qu'elle n'ait
calculé quoi que ce soit. Un modèle de coût qui ne rapporte que l'électricité
n'est pas silencieux là-dessus : il affirme que ce chiffre est zéro.

La spécification définit

```
M = TE × TS × RS
```

les émissions incorporées totales du matériel, fois la part de sa vie que
l'exécution a réservée, fois la part du matériel qu'elle a réservée. Sur une
heure d'une H100 pour une vie de quatre ans, cela fait 164 kg × 1 h / 35 064 h
× 1 ≈ **4,7 gCO2e** — peu face aux ~400 Wh que la même exécution tire, pas rien,
et surtout pas zéro.

Sept empreintes sont livrées dans le catalogue — **trois accélérateurs sur 25
lignes, quatre processeurs sur 12** — chacune lue à sa source primaire et portant
sa frontière en toutes lettres à côté du nombre :

| Pièce | kgCO2e par appareil | Frontière | Source |
|---|---|---|---|
| A100 (SXM 40 Go) | 127,6 | Du berceau à la sortie d'usine, ACV par démontage avec analyse élémentaire primaire | [arXiv:2509.00093](https://arxiv.org/abs/2509.00093) |
| H100 | 164,0 | Une des huit d'une carte mère HGX H100 : 1 312 kg ÷ 8, ISO 14067, revue par un tiers | [Résumé PCF NVIDIA](https://images.nvidia.com/aem-dam/Solutions/documents/HGX-H100-PCF-Summary.pdf) |
| B200 | 284,25 | Une des huit d'une carte mère HGX B200 : 2 274 kg ÷ 8, même méthode | [Résumé PCF NVIDIA](https://images.nvidia.com/aem-dam/Solutions/documents/HGX-B200-PCF-Summary.pdf) |
| EPYC 7742 | 40,66 | Du berceau à la sortie d'usine, depuis un die de 1 600 mm² | [Boavizta](https://doc.api.boavizta.org/Explanations/components/cpu/) |
| EPYC 9654 | 33,98 | Du berceau à la sortie d'usine, depuis un die de 1 261 mm² | [Boavizta](https://doc.api.boavizta.org/Explanations/components/cpu/) |
| Core i9-13900K | 14,2 | Du berceau à la sortie d'usine, depuis un die de 257 mm² | [Boavizta](https://doc.api.boavizta.org/Explanations/components/cpu/) |
| Ryzen 9 7950X | 14,34 | Du berceau à la sortie d'usine, depuis un die de 264 mm² | [Boavizta](https://doc.api.boavizta.org/Explanations/components/cpu/) |

Les deux sortes de ligne ne sont pas de la même force, et le tableau les tient
séparées plutôt que de les moyenner sous un même mot. Les accélérateurs sont
publiés par le fabricant ou démontés et pesés. Les processeurs sont **calculés
depuis la taille du die par un modèle publié** — chose plus faible, et la raison
pour laquelle la méthode est liée et pas seulement le chiffre.

Les huit processeurs restants sont refusés plutôt que remplis. Quatre parce que
cette source répond à propos d'une puce qu'on ne lui a pas demandée : interrogée
sur une Apple M4 Max, elle renvoie une Apple M1 Max, quatre générations plus tôt,
sans le moindre avertissement. Deux parce que la taille de die qui a servi au
calcul est une moyenne de famille et non celle de cette puce, ce qui fait de
l'empreinte une moyenne de famille portant le nom de la puce. Deux sont des
valeurs par défaut du catalogue, dont l'empreinte serait un défaut aussi.

Les accélérateurs ne peuvent pas être remplis ainsi du tout. La même source,
interrogée sur n'importe quel GPU par son nom, répond 575,1 kgCO2e — le même
nombre pour une GTX 1080 Ti, une A100 et une H100, parce qu'elle ne tient qu'un
archétype nommé « Large GPU ». C'est trois fois et demie le chiffre vérifié de
NVIDIA pour une H100, et il arrive portant le nom de modèle demandé. Le
rafraîchissement le refuse nommément et dit pourquoi.

Une pièce sans ligne donne un `TODO`, avec une phrase disant que personne n'a lu
d'empreinte pour elle — ce qui n'est pas la même chose que sa fabrication aurait
été gratuite.

## Là où ce n'est pas conforme, et pourquoi

La moitié utile d'une déclaration de conformité, c'est la part qui échoue.

**La durée de vie est la vôtre, et elle est livrée ouverte.** Chacune de ces
empreintes s'arrête à la sortie d'usine et exclut explicitement la phase
d'usage. Le fabricant a donné le numérateur et retenu délibérément le
dénominateur, parce que la durée de service d'une carte est un fait sur une
flotte et non sur une pièce. `assumptions.hardware_lifetime` est donc un `TODO`
tant que vous ne l'énoncez pas. Les chiffres publiés se groupent entre trois et
six ans, et choisir dans cette plage déplace la réponse d'un facteur deux — ce
qui est précisément pourquoi la question est posée au lieu d'être supposée.

**La fin de vie est exclue, parce que les sources l'excluent.** Les empreintes
s'arrêtent à la porte de l'usine. Recyclage et mise au rebut sont réels et ne
sont pas dans ces nombres, et le rapport le dit au lieu de laisser l'omission
passer pour un zéro.

**La carte, la mémoire, le réseau et le stockage ne sont pas comptés.** Ils ont
tous dû être fabriqués aussi. Aucun n'est au catalogue, donc aucun n'est dans le
chiffre, et le chiffre dit quelle pièce il couvre. Le processeur est compté
désormais, là où il y en a un au fichier, et seulement là : une machine avec
accélérateur rapporte l'accélérateur, une machine sans en rapporte son
processeur si cette puce est connue, et sinon rapporte `TODO`. Rien n'est
additionné entre pièces, parce qu'aucune source ici n'en couvre deux sous une
même frontière.

**L'amortissement est en temps calendaire, pas en temps occupé.** La
spécification définit la part de temps comme la durée sur la durée de vie
attendue : une carte inactive la moitié de sa vie n'impute cette moitié à
personne. L'alternative courante — charger tout l'incorporé sur les heures qui
ont travaillé — donne un nombre plus grand et n'est pas ce que dit la norme. Ce
paquet suit la norme, et chaque chiffre qu'il produit porte une note disant
quelle convention il a employée.

Trois exigences de la spécification qui étaient déjà vraies ici, et qu'il vaut
la peine de nommer parce que ce sont celles que les outils ratent le plus
souvent : **aucune compensation** n'est soustraite nulle part ; l'intensité est
**liée au lieu**, depuis l'endroit où le code tourne, jamais un instrument de
marché ; et la **frontière est déclarée** sur chaque quantité plutôt qu'en note
de bas de page.

## Ce que demandent les réglementations, qui est moins

Le [règlement européen sur l'IA](https://digital-strategy.ec.europa.eu/en/faqs/guidelines-obligations-general-purpose-ai-providers)
oblige les fournisseurs de modèles d'IA à usage général à documenter, à l'annexe
XI, les ressources de calcul employées pour l'entraînement et la **consommation
d'énergie connue ou estimée** du modèle. Quand elle n'est pas connue, le texte
permet explicitement une estimation à partir du calcul utilisé — ce qui est,
presque mot pour mot, le métier de ce paquet. Le non-respect expose à des
amendes jusqu'à 15 M€ ou 3 % du chiffre d'affaires mondial ; les modèles mis sur
le marché avant le 2 août 2025 ont jusqu'au 2 août 2027.

Il demande moins que SCI, de trois façons qu'il vaut la peine de connaître : il
porte sur l'énergie plutôt que sur les émissions, il **ignore entièrement le
carbone incorporé**, et la divulgation va au régulateur plutôt qu'au public. Un
modèle qui satisfait SCI satisfait l'annexe XI avec de la marge ; l'inverse est
faux.

La Green Software Foundation a cartographié l'un sur l'autre dans
[SCI for AI and EU AI Act environmental compliance](https://greensoftware.foundation/policy/research/sci-ai-eu-ai-act/).

## Le faire

```bash
saggio audit . --country FR --run -o cost_of_running.yaml
```

L'audit écrit `assumptions.hardware_embodied_carbon` depuis le catalogue et
`assumptions.hardware_lifetime` comme un chiffre ouvert. Renseignez la durée de
vie, et `embodied_carbon` se résout avec tout ce qui en dérive :

```yaml
assumptions:
  hardware_lifetime:
    value: 4.0
    unit: "years"
    status: "estimated"
    notes: "Cycle de renouvellement de la flotte, d'après nos propres achats."
```

Laissez-la ouverte et le chiffre incorporé reste ouvert, le score SCI reste
ouvert avec lui, et le rapport dit lequel des quatre termes manque. C'est tout
le propos : une norme qu'on satisfait à moitié, en sachant exactement quelle
moitié.

## Sources

- [Spécification Software Carbon Intensity](https://sci.greensoftware.foundation/), ISO/IEC 21031:2024 · [SCI for AI](https://greensoftware.foundation/standards/sci-ai/)
- [Résumé PCF NVIDIA HGX H100](https://images.nvidia.com/aem-dam/Solutions/documents/HGX-H100-PCF-Summary.pdf) · [HGX B200](https://images.nvidia.com/aem-dam/Solutions/documents/HGX-B200-PCF-Summary.pdf) — ISO 14067, revue par un tiers, du berceau à la sortie d'usine.
- *More than Carbon: Cradle-to-Grave environmental impacts of GenAI training on the NVIDIA A100 GPU*, [arXiv:2509.00093](https://arxiv.org/abs/2509.00093).
- [Lignes directrices UE pour les fournisseurs de modèles à usage général](https://digital-strategy.ec.europa.eu/en/faqs/guidelines-obligations-general-purpose-ai-providers) · [SCI for AI et conformité au règlement IA](https://greensoftware.foundation/policy/research/sci-ai-eu-ai-act/)
- [Green Algorithms](https://doi.org/10.1002/advs.202100707) — l'arithmétique opérationnelle, extraite dans [`skills/saggio/references/green-algorithms.md`](skills/saggio/references/green-algorithms.md).

---

[`MESURER.md`](MESURER.md) dit d'où vient E. [`ANALYSE.md`](ANALYSE.md) dit ce
qu'on peut demander à la lecture et à l'exécution du code. [`PAYSAGE.md`](PAYSAGE.md)
situe tout cela parmi les outils qui répondent à des questions voisines.
