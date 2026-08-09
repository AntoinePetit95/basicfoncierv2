# Journal

## 2026-08-09 — Forme idu, identifiant court et assemblage depuis les champs

**Demande :** compléter `ref_cadastrale` avec les quatre fonctions restantes du v1.
**Fait :**
- `to_idu`, `to_short_id`, `idu_from_parts`, `short_id_from_parts`, chacune acceptant une chaîne ou une colonne. Les deux premières remplacent des fonctions **cassées** dans le v1.
- Toutes passent par la forme idu, qui sert de pivot et de point de validation unique. Les propriétés d'aller-retour sont testées : toute forme produite se décompose comme la référence d'origine.
- Primitives Arrow réorganisées en trois modules internes : `arrow_commun`, `composition_arrow`, `decomposition_arrow`.
**Fichiers :** `basicfoncierv2/ref_cadastrale.py`, `basicfoncierv2/_internal/{arrow_commun,composition_arrow,decomposition_arrow}.py`, `tests/test_ref_cadastrale.py`, `benchmarks/__main__.py`, `docs/{DECISIONS,MIGRATION}.md`
**Vérifié par :** `pytest` → 148 passed ; `ruff check .` → All checks passed ; `python -m benchmarks` → to_parts 2 312 980 lignes/s (x5,6 contre le v1), to_idu 3 380 100, to_short_id 1 015 077.
**À savoir :** `idu_from_parts` change l'ordre de ses arguments par rapport au v1. Un appel positionnel recopié tel quel produit une référence fausse **sans lever d'erreur** — c'est le piège de migration le plus dangereux à ce jour, signalé en tête de `MIGRATION.md`. `to_short_id` est trois fois plus lent que `to_idu` : il fait un aller-retour d'assemblage puis de relecture, choisi pour garantir que toute forme produite reste lisible.

## 2026-08-09 — Élargissement des bornes de dépendances

**Demande :** élargir la compatibilité pandas, dans la mesure du raisonnable.
**Fait :**
- Suite exécutée contre pandas 2.0.3, 2.1.1, 2.1.4, 2.2.3, 2.3.3, 3.0.5 et contre Python 3.10, 3.11, 3.12, dans des environnements isolés. **Aucune modification de code n'a été nécessaire.**
- `pandas>=3.0.0` devient `pandas>=2.1.4` ; `numpy` sort des dépendances d'exécution, le paquet ne l'important nulle part.
- CI passée en matrice explicite : une entrée par série mineure de pandas, plus la combinaison plancher pandas 2.1.4 + pyarrow 15.0.2, plus une entrée sans épinglage. Lint et format déplacés dans un job distinct, exécuté une seule fois.
**Fichiers :** `pyproject.toml`, `.github/workflows/tests.yml`, `docs/{DECISIONS,MIGRATION}.md`
**Vérifié par :** matrice locale — 65 passed sur chacune des six combinaisons ; `pytest`, `ruff check .` et `ruff format --check .` verts sur l'environnement du projet.
**À savoir :** pandas 2.0.3 et 2.1.1 passent aussi les tests, mais seulement si `numpy<2` est épinglé à la main — leurs métadonnées ne bornent pas numpy alors qu'ils ont été compilés contre la 1.x. Le plancher s'arrête donc à 2.1.4. `requires-python` reste `>=3.12` bien que 3.10 et 3.11 passent : c'est une décision qui n'a pas été demandée.

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
