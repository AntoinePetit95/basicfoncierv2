# Bugs

## Ouverts

### Hérité de `basicfoncier` v1 — `superficie_from_str` se trompe sur les écritures non complétées

**Périmètre :** défaut du v1. **Il n'est pas corrigé ici** — le v1 est intouchable (CLAUDE.md §5). Consigné parce que le v2 réimplémente cette lecture et parce que la migration doit prévenir les utilisateurs.

**Symptôme :** la lecture retire les lettres une à une (`replace(" ", "").replace("a", "").replace("c", "").replace("h", "")`) puis convertit le reste en entier. Cela ne fonctionne que si les ares et les centiares sont écrits sur deux chiffres.

**Reproduction** (dans le dépôt v1) :

```
superficie_from_str("1 ha 0 a 3 ca")  → 103    au lieu de 10 003
superficie_from_str("1 a 5 ca")       → 15     au lieu de 105
superficie_from_str("1 ha 13 a 20 ca") → 11 320  (correct : composantes complétées)
```

**Portée réelle :** les sorties de `superficie_ha_a_ca` sont complétées, donc l'aller-retour interne au v1 est juste. Le défaut se déclenche sur des données venues d'ailleurs — et il y en a dans les fixtures du v1 lui-même (`tests/test_vectorized.py` contient `'1 ha  0 a  3 ca'`, `'1 a 5 ca'`).

**Aggravation :** comme pour le bug de décomposition, le wrapper pandas attrape l'exception dans un `except:` nu. Ici il n'y a même pas d'exception : la valeur fausse passe silencieusement.

**Traitement dans le v2 :** `superficie.from_ha_a_ca` lit par motif et non par suppression de lettres. Les écritures non complétées sont testées explicitement, et une écriture illisible lève une erreur au lieu de produire un nombre.

### Hérité de `basicfoncier` v1 — ordre de tuple incohérent dans `ref_parcelle_to_parts`

**Périmètre :** défaut du v1. **Il n'est pas corrigé ici** — le v1 est intouchable (CLAUDE.md §5). Consigné parce que le v2 réimplémente ces fonctions et ne doit pas reproduire le défaut, et parce que la migration doit prévenir les utilisateurs.

**Symptôme :** `ref_parcelle_to_parts` renvoie `(insee, com_abs, section, numero)` dans sa branche générale, mais `(insee, section, numero, com_abs)` dans sa branche Alsace-Moselle. Ses deux appelants, `ref_parcelle_to_idu` et `ref_parcelle_to_short_id`, dépaquettent l'ancien ordre.

**Reproduction** (dans le dépôt v1, à l'état du commit `7f2d199`) :

```
ref_parcelle_to_idu("972150000C0302")      → "972150302000000C"   # faux, 16 caractères
ref_parcelle_to_short_id("972150000C0302") → ValueError: invalid literal for int(): '0C'
```

**Aggravation :** les wrappers de `vectorized_functions/for_pandas/_nullable.py` attrapent l'exception dans un `except:` nu et renvoient `NA`. En usage pandas, la fonction **échoue silencieusement** : la colonne se remplit de `NA` sans qu'aucune erreur ne remonte.

**Origine :** commit `7f2d199` « Changed reference cadastrales order : insee, com_abs, section, numero », qui a changé l'ordre de retour d'une branche sans mettre à jour l'autre branche ni les appelants. Aucun test ne couvrait ces fonctions.

**Conséquences pour le v2 :**
1. L'ordre canonique retenu est celui des docstrings et du dernier commit : **`(insee, com_abs, section, numero)`**.
2. Le premier test écrit sur la décomposition doit couvrir une référence Alsace-Moselle *et* une référence générale, et vérifier que les deux respectent le même ordre.
3. Aucun `except:` nu. Une donnée invalide donne une valeur manquante **explicitement demandée par l'appelant**, jamais un silence par défaut.
4. À signaler dans `docs/MIGRATION.md` : un utilisateur du v1 peut avoir des colonnes entièrement à `NA` sans le savoir.

## Résolus

*(aucun)*
