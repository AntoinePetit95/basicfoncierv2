# Journal

## 2026-08-09 — Chemin rapide par découpe directe sur la forme idu

**Demande :** exploiter la marge de vitesse identifiée à la tâche précédente.
**Fait :**
- La décomposition se fait désormais en deux temps : normalisation vers la forme idu, puis découpe à positions fixes. Une référence déjà canonique n'est plus analysée par extraction, seulement reconnue.
- Deux formes de quatorze caractères qui n'étaient pas couvertes sont maintenant testées et rejetées : sans lettre de section hors Alsace-Moselle, et avec lettre de section en Alsace-Moselle. La seconde aurait été acceptée à tort par une découpe fixe naïve.
- Licence corrigée en Unlicense — MIT avait été posée par défaut.
**Fichiers :** `basicfoncierv2/_internal/{motifs,decomposition_arrow}.py`, `tests/test_ref_cadastrale.py`, `LICENSE`, `pyproject.toml`, `docs/DECISIONS.md`
**Vérifié par :** `pytest` → 65 passed ; `ruff check .` → All checks passed ; `python -m benchmarks` → 2,2 à 2,5 millions de lignes/s contre environ 500 000 pour le v1, soit **x4,5 à x4,9** selon les exécutions (contre x2,1 avant). La CI a tourné en vert sur la branche précédente.
**À savoir :** le gain dépend de la proportion de références déjà en forme idu. Mesuré sur une colonne composée uniquement de formes courtes, le débit tombe à 819 277 lignes/s, soit environ 15 % de moins que l'implémentation précédente — contrepartie assumée, voir `docs/DECISIONS.md`.

## 2026-08-09 — Squelette du paquet et décomposition des références cadastrales

**Demande :** poser le squelette du paquet et livrer la décomposition de référence cadastrale de bout en bout, vectorisée.
**Fait :**
- `pyproject.toml`, paquet `basicfoncierv2`, CI de test, benchmarks. Dépôt privé `AntoinePetit95/basicfoncierv2` créé, `main` poussé.
- `ref_cadastrale.to_parts` : une seule fonction, chaîne ou `Series`, décomposition par `pyarrow.compute.extract_regex` sans boucle Python. Erreur métier explicite sur donnée invalide, valeurs manquantes seulement si l'appelant les demande.
- 44 tests, dont la non-régression du bug d'ordre hérité du v1 : les régimes général et Alsace-Moselle placent désormais la commune absorbée au même rang.
**Fichiers :** `pyproject.toml`, `basicfoncierv2/{__init__,erreurs,ref_cadastrale}.py`, `basicfoncierv2/_internal/{motifs,decomposition_arrow}.py`, `tests/test_ref_cadastrale.py`, `benchmarks/`, `.github/workflows/tests.yml`, `docs/{DECISIONS,MIGRATION}.md`
**Vérifié par :** `pytest` → 44 passed ; `ruff check .` → All checks passed ; `ruff format --check .` → 17 files already formatted ; `python -m benchmarks` → 926 107 lignes/s contre 435 126 pour le v1, soit x2,1.
**À savoir :** le gain mesuré est très inférieur à la prévision consignée dans `docs/DECISIONS.md`, corrigée depuis. Le coût est entièrement dans les deux passes de regex ; un chemin rapide par découpes fixes sur la forme idu ramènerait le total de 1 117 ms à ~290 ms. C'est la tâche suivante. La CI n'a jamais tourné : la branche n'est pas poussée.

## 2026-08-09 — Amorçage du socle EF sur un dépôt neuf

**Demande :** mettre en place un espace de travail propre pour la création de `basicfoncierv2`, successeur de `basicfoncier` à API simplifiée, tests intégrés et exécution vectorisée sur colonnes pandas.
**Fait :**
- Audit en lecture seule de `basicfoncier` v1 : inventaire de l'API publique, état des tests (une seule assertion réelle sur ~15 fonctions), découverte d'un bug bloquant sur `ref_parcelle_to_parts`.
- Création du dépôt `basicfoncierv2` et installation du socle EF : `CLAUDE.md`, `docs/{JOURNAL,BUGS,DECISIONS,VOCABULAIRE,MIGRATION}.md`, commande `/revue`.
- Quatre décisions structurantes prises et consignées : dépôt séparé, vectorisation pandas/pyarrow, API unifiée scalaire/Series, outillage pytest + ruff + CI.
**Fichiers :** `CLAUDE.md`, `README.md`, `.gitignore`, `.claude/commands/revue.md`, `docs/*`
**Vérifié par :** aucune commande — aucun code applicatif écrit à ce stade. Le bug du v1 a été reproduit par exécution directe dans le dépôt v1 (lecture seule).
**À savoir :** le dépôt v1 n'a reçu aucune modification de code. Le paquet `basicfoncierv2` lui-même n'existe pas encore : ni `pyproject.toml`, ni arborescence source, ni tests. C'est l'objet de la première tâche.
