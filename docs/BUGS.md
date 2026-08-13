# Bugs

## Défauts hérités de `basicfoncier` v1

**Aucun de ces défauts n'affecte `basicfoncier`** : ils sont tous corrigés ici. Ils
restent consignés parce que quiconque migre doit savoir que ses données produites peuvent
être fausses depuis plus longtemps qu'il ne le croit.

> **Le dépôt du v1 est destiné à être supprimé** — voir [CHANTIERS.md](CHANTIERS.md). Le
> code fautif est donc recopié ci-dessous, à l'état du commit `7f2d199`, avec son chemin
> d'origine. Sans cette copie, ces constats deviendraient des affirmations sans source
> vérifiable le jour où le dépôt disparaîtra.

### `com_insee_from_code_dep_code_com` tronque l'outre-mer

**Symptôme :** la recomposition ramène le code département à deux caractères (`code_dep[:2]`) avant de concaténer. En métropole c'est sans effet ; outre-mer, où le département tient sur trois caractères, il en manque un au résultat.

**Reproduction** (dans le dépôt v1) :

```
com_insee_from_code_dep_code_com("972", "15")  → "9715"   au lieu de "97215"
com_insee_from_code_dep_code_com("78", "048")  → "78048"  (correct)
```

L'aller-retour est donc rompu outre-mer : décomposer `97215` donne `("972", "15")`, que recomposer ne redonne pas `97215`.

**Code d'origine** — `basicfoncier/utils/communes_departements_regions.py`, lignes 30 à 40 :

```python
def com_insee_from_code_dep_code_com(code_dep: str, code_com: str) -> str:
    """
    Renvoie le code insee d'une commune d'après les codes département et commune
    :param code_dep: le code département sur 2 ou 3 chiffres (outre-mer)
    :param code_com: le code commune sur 3 ou 2 chiffres (outre-mer)
    :return: dode insee commune sur 5 chiffres
    """
    if len(code_dep) == 3:
        code_dep = code_dep[:2]

    return code_dep + code_com
```

La docstring annonce pourtant le cas outre-mer, « 2 ou 3 chiffres » : le code le connaît et le supprime.

**Traitement dans le v2 :** `commune.insee_from_parts` complète le code commune à la largeur que lui laisse le département — 3 caractères en métropole, 2 outre-mer — et valide le résultat. L'aller-retour est testé comme propriété sur tous les territoires.

### `superficie_from_str` se trompe sur les écritures non complétées

**Symptôme :** la lecture retire les lettres une à une (`replace(" ", "").replace("a", "").replace("c", "").replace("h", "")`) puis convertit le reste en entier. Cela ne fonctionne que si les ares et les centiares sont écrits sur deux chiffres.

**Reproduction** (dans le dépôt v1) :

```
superficie_from_str("1 ha 0 a 3 ca")  → 103    au lieu de 10 003
superficie_from_str("1 a 5 ca")       → 15     au lieu de 105
superficie_from_str("1 ha 13 a 20 ca") → 11 320  (correct : composantes complétées)
```

**Portée réelle :** les sorties de `superficie_ha_a_ca` sont complétées, donc l'aller-retour interne au v1 est juste. Le défaut se déclenche sur des données venues d'ailleurs — et il y en a dans les fixtures du v1 lui-même (`tests/test_vectorized.py` contient `'1 ha  0 a  3 ca'`, `'1 a 5 ca'`).

**Code d'origine** — `basicfoncier/superficie.py`, lignes 29 à 35 :

```python
def superficie_from_str(sup_string: str) -> int:
    """
    Récupère la valeur en m² depuis une superficie formatée en "_ ha __ a __ ca"
    :param sup_string: chaîne de caractères
    :return: int
    """
    return int(sup_string.replace(" ", "").replace("a", "").replace("c", "").replace("h", ""))
```

**Aggravation :** comme pour le bug de décomposition, le wrapper pandas attrape l'exception dans un `except:` nu. Ici il n'y a même pas d'exception : la valeur fausse passe silencieusement.

**Traitement dans le v2 :** `superficie.from_ha_a_ca` lit par motif et non par suppression de lettres. Les écritures non complétées sont testées explicitement, et une écriture illisible lève une erreur au lieu de produire un nombre.

### Ordre de tuple incohérent dans `ref_parcelle_to_parts`

**Symptôme :** `ref_parcelle_to_parts` renvoie `(insee, com_abs, section, numero)` dans sa branche générale, mais `(insee, section, numero, com_abs)` dans sa branche Alsace-Moselle. Ses deux appelants, `ref_parcelle_to_idu` et `ref_parcelle_to_short_id`, dépaquettent l'ancien ordre.

**Reproduction** (dans le dépôt v1, à l'état du commit `7f2d199`) :

```
ref_parcelle_to_idu("972150000C0302")      → "972150302000000C"   # faux, 16 caractères
ref_parcelle_to_short_id("972150000C0302") → ValueError: invalid literal for int() with base 10: '0C'
```

**Portée réelle, mesurée par exécution** — ce n'est pas un cas limite, c'est le cas normal. Seule l'Alsace-Moselle en réchappe :

| Entrée | `ref_parcelle_to_idu` | `ref_parcelle_to_short_id` |
|---|---|---|
| `78048000AB0011` (métropole) | `78048001100000AB` — faux, 16 caractères | `ValueError` |
| `78048AB11` (forme courte) | `78048001100000AB` — faux | `ValueError` |
| `2A004000AB0011` (Corse) | `2A004001100000AB` — faux | `ValueError` |
| `97213000AB0011` (outre-mer) | `97213001100000AB` — faux | `ValueError` |
| `57463000120011` (Alsace-Moselle) | `57463000120011` — **correct** | `574631211` |

Hors Alsace-Moselle, une référence **déjà** en forme idu n'est donc pas rendue telle quelle : elle ressort déformée. Et l'Alsace-Moselle, seule à réchapper, est le cas particulier : la branche fautive est celle qui couvre tout le reste du territoire.

**Code d'origine** — `basicfoncier/ref_cadastrales.py`, fonction `ref_parcelle_to_parts` (lignes 35 à 74). Seuls les deux `return` et leur garde sont reproduits : **lignes 44 à 48**, puis **ligne 74**. Recopié tel quel, sans annotation ; les `[…]` marquent ce qui est omis. Le bloc n'est pas balisé `python` : ce n'est pas du code exécutable, mais un extrait troué.

```
[…] lignes 35 à 43 : signature, docstring, ligne vide

    # Alsace-Moselle : code uniquement numérique.
    if ref.startswith('57') or ref.startswith('67') or ref.startswith('68'):
        assert len(ref) == 14
        assert ref.isnumeric()
        return ref[0:5], ref[8:10], ref[10:], ref[5:8]

[…] lignes 49 à 73 : découpe de la branche générale

    return com_insee.zfill(5), com_abs.zfill(3), section.zfill(2), numero.zfill(4)
```

Les deux `return` de la même fonction ne suivent pas le même ordre. Le premier rend `(insee, section, numero, com_abs)`, le second `(insee, com_abs, section, numero)` — la docstring, elle, n'annonce que le second. Le v1 ne commente ni l'un ni l'autre : c'est la lecture des découpes qui le montre.

Les deux appelants (`ref_cadastrales.py:84` et `:95`) dépaquettent `com_insee, section, numero, com_abs` — l'ordre de la branche Alsace-Moselle. C'est donc la branche **générale** qui est lue de travers, à chaque appel.

À noter aussi : la validation d'une donnée venue de l'extérieur y est faite par `assert`. Le paquet v1 ne contient **aucun** `raise` ; ses neuf validations sont toutes des assertions. Lancé avec `-O`, il ne valide donc plus rien.

**Aggravation :** les wrappers de `vectorized_functions/for_pandas/_nullable.py` attrapent l'exception dans un `except:` nu et renvoient `NA`. En usage pandas, la fonction **échoue silencieusement** : la colonne se remplit de `NA` sans qu'aucune erreur ne remonte.

**Origine :** commit `7f2d199` « Changed reference cadastrales order : insee, com_abs, section, numero », qui a changé l'ordre de retour d'une branche sans mettre à jour l'autre branche ni les appelants. Aucun test ne couvrait ces fonctions.

**Conséquences pour le v2 :**
1. L'ordre canonique retenu est celui des docstrings et du dernier commit : **`(insee, com_abs, section, numero)`**.
2. Le premier test écrit sur la décomposition doit couvrir une référence Alsace-Moselle *et* une référence générale, et vérifier que les deux respectent le même ordre.
3. Aucun `except:` nu. Une donnée invalide donne une valeur manquante **explicitement demandée par l'appelant**, jamais un silence par défaut.
4. Signalé dans [MIGRATION.md](MIGRATION.md) : un utilisateur du v1 peut avoir des colonnes entièrement à `NA` sans le savoir.

## Défauts ouverts

### 2026-08-12 — Les colonnes `category` sont refusées

**Symptôme :** une colonne au dtype `category` — la forme pandas d'un encodage par dictionnaire, et celle que produit la lecture d'un Parquet encodé — est rejetée par la validation de type.

**Reproduction :**

```python
commune.to_departement(codes.astype("category"))
# TypeError: la colonne de codes Insee doit contenir des chaînes,
#            reçu une colonne de type category.
superficie.to_ha_a_ca(contenances.astype("category"))
# TypeError: la colonne de superficies doit contenir des nombres, ...
```

`str` et `string[pyarrow]` passent sans difficulté ; seul `category` est refusé.

**Portée :** aucune donnée fausse produite — le refus est franc et le message est clair. C'est une gêne d'usage, pas une erreur de calcul. L'appelant peut contourner par `.astype(str)`, au prix d'une conversion qui défait précisément l'encodage.

**Ce qui le rend gênant :** ces colonnes sont celles où la bibliothèque serait la plus rapide. Sur une colonne de codes Insee déjà encodée, le calcul mesuré passe de **185,9 ms à 11,1 ms** — colonne « Entrée déjà encodée » du tableau de [DECISIONS.md](DECISIONS.md), entrée du 2026-08-12. La bibliothèque refuse donc son meilleur cas.

**Traitement prévu :** unité 2 du chantier 1.1.0, voir [CHANTIERS.md](CHANTIERS.md).

## Questions tranchées et défauts corrigés dans le v2

### 2026-08-09 — Tranché : les codes commune de Paris et Lyon du v1 sont faux

La question posée ici — Marseille recevait son code Insee réel (`13055`) alors que Paris et Lyon recevaient `75100` et `69300`, absents du répertoire Insee — **est tranchée par le propriétaire des données : ce sont deux valeurs fausses.**

| Ville | v1 | v2 |
|---|---|---|
| Paris | `75100` | `75056` |
| Lyon | `69300` | `69123` |
| Marseille | `13055` | `13055` |

Codes vérifiés au Code officiel géographique de l'Insee, comme les trois plages d'arrondissements — Paris `75101`–`75120`, Lyon `69381`–`69389`, Marseille `13201`–`13216`, qui étaient exactes.

**Ce que la question cachait :** ce n'était pas seulement une erreur de table. Le cas Paris/Lyon/Marseille n'avait jamais été traité, ni dans le v1 ni dans le v2. Le champ insee d'une référence cadastrale y porte le code d'**arrondissement municipal**, pas celui de la commune : la parcelle du pilier Ouest de la tour Eiffel est `75107000CR0002`. Aucune parcelle parisienne ne porte `75056`. Les deux sens de conversion ne sont donc pas symétriques, et c'est voulu — voir [DECISIONS.md](DECISIONS.md).

**Conséquence pour les utilisateurs :** les valeurs produites changent pour Paris et Lyon. Signalé en tête de section dans [MIGRATION.md](MIGRATION.md), avec le `replace` qui rétablit l'ancien comportement le temps d'une migration.

**Portée réelle :** aucune donnée existante n'est touchée — le commanditaire n'a jamais traité de parcelle à Paris, Lyon ni Marseille. La reprise d'exports déjà livrés, un moment envisagée, est donc sans objet.

### 2026-08-09 — Cinq défauts du v2 trouvés par la revue indépendante

Trois relecteurs lancés en parallèle sur le code complet ont convergé sur cinq défauts que ma propre revue n'avait pas vus. Tous sont corrigés, chacun avec son test de non-régression. Le point commun des quatre premiers : **le chemin scalaire et le chemin colonne ne se comportaient pas pareil**, et seule la confrontation systématique des deux les révélait.

| Défaut | Symptôme | Correction |
|---|---|---|
| Corse rejetée | `to_parts("2A0040000H0011")` levait `ReferenceCadastraleInvalide` alors que `commune` acceptait `2A004` | fragment de motif Insee partagé entre `insee.py` et `motifs.py` |
| Colonne Arrow fragmentée | `ArrowInvalid: Mask must be array or scalar, not ChunkedArray` sur une colonne issue de `read_parquet(dtype_backend="pyarrow")` | `appel.en_colonne_arrow` recolle à l'entrée |
| Superficie négative fractionnaire | `to_ha_a_ca(-0.4)` levait, `to_ha_a_ca(pd.Series([-0.4]))` renvoyait `'0 ca'` | le signe est lu avant l'arrondi |
| Département tronqué | `insee_from_parts("7", "048")` renvoyait `"70048"` sans erreur | `MOTIF_DEPARTEMENT` validé sur les deux chemins |
| Saut de ligne final | `to_idu("780480000H0011\n")` réussissait, la colonne échouait | `fullmatch` côté Python, classe de blancs écrite en clair |

**Gravité :** les deux premiers sont des pertes de données à l'échelle d'un fichier entier — toute la Corse, ou tout un `read_parquet`. Le troisième et le quatrième produisent une valeur fausse sans rien signaler, ce que ce projet s'est justement donné pour règle de ne jamais faire.

**Portée réelle :** nulle. Le paquet n'est pas publié et aucun de ces défauts n'a atteint un utilisateur.

**Ce que la revue a aussi montré :** le défaut multi-chunk ne se déclenchait que si au moins une valeur de la colonne empruntait le chemin lent — un plantage dépendant des données, invisible aux tests écrits sur des colonnes courtes et homogènes. Les tests de mélange de formes existaient ; il leur manquait la fragmentation.

**Détail des arbitrages :** [DECISIONS.md](DECISIONS.md), cinq entrées du 2026-08-09.
