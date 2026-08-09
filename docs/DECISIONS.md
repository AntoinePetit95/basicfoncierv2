# Décisions

## 2026-08-09 — Nouveau paquet `basicfoncierv2` dans un dépôt séparé

**Contexte :** `basicfoncier` est publié sur PyPI et sert de dépendance à d'autres programmes EF. Il doit rester intact, mais son API et ses performances ne conviennent plus.
**Retenu :** un dépôt indépendant `basicfoncierv2`, avec son propre versioning et sa propre publication. Le v1 n'est plus touché ; la continuité est assurée par `docs/MIGRATION.md`.
**Écarté :** un second paquet dans le dépôt du v1 (un seul workflow de publication pour deux paquets, et tout commit touche le dépôt en production) ; une branche v2 (le socle EF interdit les commits sur `main`, et une branche durablement divergente n'est pas un paquet distinct).

## 2026-08-09 — Vectorisation native pandas/pyarrow, zéro boucle Python

**Contexte :** le v1 expose ses fonctions « vectorisées » via `np.vectorize`, qui n'est pas une vectorisation : c'est une boucle Python avec un appel de fonction par ligne. C'est le coût dominant sur une colonne de plusieurs centaines de milliers de parcelles.
**Retenu :** implémentation native — décomposition des références par regex vectorisée (`.str.extract`), recomposition par `.str.zfill` et concaténation, superficies par arithmétique entière numpy. Chaînes en `string[pyarrow]`. `pyarrow` devient une dépendance d'exécution.
**Écarté :** numpy pur en dtype `object` (portable et sans dépendance nouvelle, mais les opérations sur chaînes y restent nettement plus lentes qu'en Arrow) ; numba ou Cython (le travail est majoritairement du traitement de chaînes, où ils aident peu, et ils ajoutent une chaîne de compilation à la publication) ; conserver `np.vectorize` (n'attaque pas la cause).

## 2026-08-09 — Une fonction par concept, acceptant scalaire ou Series

**Contexte :** le v1 impose de choisir entre `basicfoncier.ref_cadastrales.ref_parcelle_to_idu` et `basicfoncier.vectorized_functions.for_pandas.functions.ref_parcelle_to_idu`. Deux chemins d'import pour un même concept, et le second avale silencieusement les erreurs.
**Retenu :** un seul nom public par concept. La fonction accepte une `str` ou une `Series` et renvoie le même type. Le niveau `vectorized_functions.for_pandas` disparaît.
**Écarté :** deux espaces de noms explicites `scalaire` / `series` (honnête sur le coût, mais reconduit le défaut principal du v1 : l'appelant doit choisir) ; un accessor DataFrame `df.foncier.…` (idiomatique, mais lie la bibliothèque à pandas et complique l'usage sur une valeur unique).

## 2026-08-09 — pytest, ruff et CI de test

**Contexte :** le v1 n'a ni linter, ni formateur, ni job de test en CI ; son unique workflow GitHub Actions publie sur PyPI sans avoir rien vérifié. Le mode autonome du socle EF n'a de filet que si la suite de tests existe et tourne.
**Retenu :** `pytest` pour les tests, `ruff` pour lint et format, un job GitHub Actions lançant les tests à chaque push. Dépendances de développement uniquement : elles n'atteignent pas les consommateurs du paquet.
**Écarté :** `unittest` de la stdlib seul (zéro dépendance, mais paramétrage et fixtures nettement plus verbeux, et pas de mesure de couverture) ; pytest sans CI (rien ne garantit alors qu'un push ne casse pas la suite).
