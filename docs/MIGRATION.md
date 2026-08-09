# Migrer de `basicfoncier` vers `basicfoncierv2`

> **Toutes les fonctions du v1 ont leur équivalent, et leurs noms sont figés.** Les
> écarts de comportement qui subsistent sont volontaires et listés sous chaque tableau :
> il s'agit dans tous les cas de résultats faux du v1 corrigés, ou de refus explicites là
> où le v1 se taisait. Une seule entrée reste à trancher, `utils.adresse.adresse`, hors
> périmètre cadastral.
> Ce fichier est mis à jour dans la même tâche que toute création, tout renommage ou toute
> suppression d'une fonction publique (CLAUDE.md §5).

> ⚠️ **Piège d'appel positionnel.** `idu_from_parts` et `short_id_from_parts` prennent
> désormais leurs arguments dans l'ordre `(insee, com_abs, section, numero)`. Le v1 les
> prenait dans l'ordre `(insee, section, numero, com_abs)`. **Un appel positionnel recopié
> tel quel produit une référence fausse sans lever d'erreur.** Relisez chaque appel.

`basicfoncier` reste publié et fonctionnel. Aucune version de ce paquet ne sera retirée ni modifiée : la migration est volontaire et peut se faire module par module.

## Ce qui change

1. **Un seul nom par concept.** Le niveau `vectorized_functions.for_pandas.functions` disparaît. La même fonction accepte une `str` ou une `Series` et renvoie le même type.
2. **Plus d'échec silencieux.** Le v1 attrape toute exception et renvoie `NA` ; une colonne pouvait se remplir de valeurs manquantes sans qu'aucune erreur ne remonte. Le v2 lève une erreur métier explicite, la tolérance aux valeurs invalides devant être demandée par l'appelant.
3. **Vectorisation réelle.** Le v1 utilise `np.vectorize`, c'est-à-dire une boucle Python. Le v2 opère nativement sur la colonne entière.
4. **`pyarrow` devient une dépendance.** Le v2 demande `pandas>=2.1.4`, `pyarrow>=15.0` et Python 3.12 ; chaque série mineure de pandas jusqu'à la 3.0 est vérifiée par la CI. Si vous êtes épinglé sur pandas 2.0.x, la migration demande d'abord de passer en 2.1.4 — voir [DECISIONS.md](DECISIONS.md) pour le détail.

## Correspondance des fonctions

### Références cadastrales

| v1 | v2 | Note |
|---|---|---|
| `ref_cadastrales.idu_from_parts` | `ref_cadastrale.idu_from_parts` | livré — **ordre des arguments changé**, voir l'avertissement en tête |
| `ref_cadastrales.short_id_from_parts` | `ref_cadastrale.short_id_from_parts` | livré — même changement d'ordre |
| `ref_cadastrales.ref_parcelle_to_parts` | `ref_cadastrale.to_parts` | livré. Ordre figé : `(insee, com_abs, section, numero)` |
| `ref_cadastrales.ref_parcelle_to_idu` | `ref_cadastrale.to_idu` | livré — **cassée dans le v1**, voir plus bas |
| `ref_cadastrales.ref_parcelle_to_short_id` | `ref_cadastrale.to_short_id` | livré — **cassée dans le v1**, voir plus bas |
| `vectorized_functions.for_pandas.functions.*` | *(supprimé)* | passer une `Series` à la fonction du même nom |

**Le module des références cadastrales est complet.** Trois différences de comportement en plus du changement d'ordre :

- **Alsace-Moselle.** `to_short_id` y renvoie la forme idu inchangée : les sections y étant numériques, une référence raccourcie ne serait plus décomposable. Le v1 la raccourcissait quand même, produisant des identifiants que sa propre fonction de lecture rejette.
- **Zéros de la section.** Le v1 retire *tous* les zéros de la section (`section.replace("0", "")`), ce qui transforme aussi `A0` en `A`. Le v2 ne retire que les zéros de tête.
- **Blancs de fin.** Une référence suivie d'un saut de ligne — `"780480000H0011\n"`, ce que produit une lecture de fichier texte mal découpée — est refusée. Le v1 l'acceptait. Si vos données en contiennent, appliquez `.str.strip()` avant l'appel : le v2 refuse de deviner.

### Tous les territoires sont couverts

La Corse (`2A`, `2B`), l'outre-mer (`97x`, `98x`) et l'Alsace-Moselle (`57`, `67`, `68`) sont reconnus par les deux modules, sur toutes les formes de référence :

```python
to_parts("2A0040000H0011")  # ('2A004', '000', '0H', '0011')
to_short_id("2B0330000C0302")  # '2B033C302'
to_parts("972150000C0302")  # ('97215', '000', '0C', '0302')
```

### Superficies

| v1 | v2 | Note |
|---|---|---|
| `superficie.superficie_ha` | `superficie.to_hectares` | livré |
| `superficie.superficie_ha_a_ca` | `superficie.to_ha_a_ca` | livré — arrondit au m² le plus proche au lieu de tronquer |
| `superficie.superficie_from_str` | `superficie.from_ha_a_ca` | livré — **corrige un résultat faux du v1**, voir plus bas |

```python
from basicfoncierv2.superficie import from_ha_a_ca, to_ha_a_ca, to_hectares

to_ha_a_ca(11_320)  # '1 ha 13 a 20 ca'
from_ha_a_ca("1 ha 13 a 20 ca")  # 11320
to_hectares(11_320)  # 1.132
```

**Deux différences de comportement :**

- **Lecture par motif.** Le v1 retire les lettres une à une et suppose donc que les ares et les centiares sont écrits sur deux chiffres : `superficie_from_str("1 a 5 ca")` y vaut 15 au lieu de 105. Le v2 lit le format ; il accepte les espaces multiples et les composantes non complétées, et **refuse** ce qu'il ne sait pas lire au lieu de renvoyer un nombre faux. Détail dans [BUGS.md](BUGS.md).
- **Superficies négatives.** Le v1 les formatait sans broncher. Le v2 lève `SuperficieInvalide`, ou pose une valeur manquante si vous passez `invalide="manquant"`.

### Communes

| v1 | v2 | Note |
|---|---|---|
| `utils.communes_departements_regions.code_dep_from_com_insee` | `commune.to_departement` | livré |
| `utils.communes_departements_regions.code_com_from_com_insee` | `commune.to_code_commune` | livré |
| `utils.communes_departements_regions.com_insee_from_code_dep_code_com` | `commune.insee_from_parts` | livré — **corrige un résultat faux du v1** outre-mer |
| `utils.communes_departements_regions.com_insee_com_arrdt_from_insee` | `commune.to_commune_et_arrondissement` | livré — renvoie un `DataFrame` sur une colonne |

```python
from basicfoncierv2.commune import (
    insee_from_parts,
    to_code_commune,
    to_commune_et_arrondissement,
    to_departement,
)

to_departement("97215")  # '972'
to_code_commune("97215")  # '15'
insee_from_parts("972", "15")  # '97215'  (le v1 renvoyait '9715')
to_commune_et_arrondissement("75107")  # ('75056', '107')  (le v1 renvoyait '75100')
```

**Cinq différences de comportement :**

- **⚠️ Codes commune de Paris et Lyon.** `to_commune_et_arrondissement` rend désormais le code Insee **réel** de la commune. Pour Marseille, rien ne change (`13055`). Pour Paris et Lyon, la valeur produite change :

  | Ville | v1 | v2 | Le code du v1 existe-t-il ? |
  |---|---|---|---|
  | Paris | `75100` | `75056` | non |
  | Lyon | `69300` | `69123` | non |
  | Marseille | `13055` | `13055` | oui |

  **Si vos traitements stockent, exportent ou joignent sur ces valeurs, elles changeront.** `75100` et `69300` sont absents du répertoire Insee : aucune jointure avec un référentiel officiel ne pouvait aboutir. Pour retrouver l'ancien comportement le temps d'une migration : `serie.replace({"75056": "75100", "69123": "69300"})`.

- **Recomposition outre-mer.** Le v1 tronquait le code département à deux caractères, produisant un code de quatre caractères : `("972", "15")` y donnait `9715`. Le v2 complète le code commune à la largeur restante et valide le résultat. Détail dans [BUGS.md](BUGS.md).
- **Codes département validés.** `insee_from_parts` refuse un code département mal formé au lieu de le compenser par le remplissage du code commune : `("7", "048")` lève `CodeInseeInvalide` au lieu de renvoyer `"70048"`. Si vous construisez vos codes département par un calcul, vérifiez qu'il produit bien `"07"` et non `"7"`.
- **Codes Insee validés.** Le v1 vérifiait la longueur par une assertion — désactivable à l'exécution, et muette sur la cause. Le v2 lève `CodeInseeInvalide` en nommant le code fautif. La Corse (`2A`, `2B`) est reconnue explicitement.
- **Arrondissements sur une colonne.** `to_commune_et_arrondissement` renvoie un `DataFrame` aux colonnes `insee_commune` et `arrondissement`, là où le v1 renvoyait un couple de tableaux.

### Paris, Lyon, Marseille : la référence cadastrale porte l'arrondissement

Le champ insee d'une référence cadastrale y désigne l'**arrondissement municipal**, jamais la commune. La parcelle du pilier Ouest de la tour Eiffel est `75107000CR0002` — `75107`, 7ᵉ arrondissement de Paris. Aucune parcelle parisienne ne porte `75056`.

**Dans le sens de la lecture, l'arrondissement est reconnaissable** : la référence reste inchangée, et le champ insee se ramène à la commune réelle quand on le demande.

```python
parts = to_parts("75107000CR0002")
parts[0]  # '75107' — la référence n'est pas modifiée
to_commune_et_arrondissement(parts[0])  # ('75056', '107')

# Sur une colonne, le même enchaînement :
parts = to_parts(df["idu"])
communes = to_commune_et_arrondissement(parts["insee"])  # insee_commune, arrondissement
```

**Dans le sens de la construction, il ne l'est pas.** Rien dans `("75", "056")` ne dit l'arrondissement : `insee_from_parts` et `idu_from_parts` concatènent sans chercher à deviner. `idu_from_parts("75056", "000", "CR", "0002")` produit une référence bien formée qui ne désigne aucune parcelle. Pour construire une référence parisienne, partez du code d'arrondissement.

Les trois plages de codes sont vérifiées au Code officiel géographique de l'Insee : Paris `75101`–`75120` (20), Lyon `69381`–`69389` (9), Marseille `13201`–`13216` (16).

### Utilitaires internes

| v1 | v2 | Note |
|---|---|---|
| `utils.string_manipulation.first_car_alpha` | *(supprimé)* | détail d'implémentation, remplacé par une regex |
| `utils.string_manipulation.first_car_numeric` | *(supprimé)* | idem |
| `utils.adresse.adresse` | *(supprimé)* | hors périmètre cadastral — voir ci-dessous |

**`adresse` n'est pas repris.** La fonction du v1 concatène un numéro et un nom de voie, en insérant une espace quand la voie n'est pas vide. Ce n'est ni cadastral ni foncier, et le maintenir dans ce paquet obligerait à le tester et à le documenter au titre d'un sujet qui n'est pas le sien. L'équivalent tient sur une ligne :

```python
# v1
adresse(numero, voie)

# v2 — sur une valeur
f"{numero} {voie}".strip()

# v2 — sur une colonne, en préservant les valeurs manquantes
(df["numero"].astype("string") + " " + df["voie"].astype("string")).str.strip()
```

## Les fonctions livrées

```python
from basicfoncierv2.ref_cadastrale import (
    idu_from_parts,
    short_id_from_parts,
    to_idu,
    to_parts,
    to_short_id,
)

to_parts("78048H11")  # ('78048', '000', '0H', '0011')
to_idu("78048H11")  # '780480000H0011'
to_short_id("780480000H0011")  # '78048H11'
idu_from_parts("78048", "000", "0H", "0011")  # '780480000H0011'
short_id_from_parts("78048", "000", "0H", "0011")  # '78048H11'

to_parts(df["idu"])  # DataFrame : insee, com_abs, section, numero
to_idu(df["ref"])  # Series
to_parts(df["idu"], invalide="manquant")  # les références illisibles deviennent <NA>
```

Trois différences à connaître avant de remplacer `ref_parcelle_to_parts` :

1. **Une `Series` en entrée donne un `DataFrame`**, pas un quadruplet de tableaux. L'index est conservé. Pour retrouver la forme du v1 : `parts.insee, parts.com_abs, parts.section, parts.numero`.
2. **Une référence illisible lève une erreur** par défaut, là où le v1 renvoyait silencieusement `NA`. Passez `invalide="manquant"` pour retrouver l'ancien comportement — mais en le sachant.
3. **Une colonne numérique est refusée** avec un message explicite : une référence stockée en entier a perdu ses zéros de tête. Le v1 renvoyait `NA` sans rien dire.

## Avertissement : deux fonctions du v1 sont cassées

Dans `basicfoncier` à l'état du commit `7f2d199`, `ref_parcelle_to_idu` renvoie une valeur fausse et `ref_parcelle_to_short_id` lève une `ValueError` — et le wrapper pandas transforme cette erreur en `NA` silencieux.

**Si vous consommez ces deux fonctions via pandas, vérifiez vos colonnes de sortie avant de migrer :** un taux de `NA` anormal indique que vos données produites sont fausses depuis la mise à jour du v1, pas depuis la migration. Détail complet dans [BUGS.md](BUGS.md).
