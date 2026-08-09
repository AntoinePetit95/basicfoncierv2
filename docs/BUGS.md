# Bugs

## Ouverts

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
