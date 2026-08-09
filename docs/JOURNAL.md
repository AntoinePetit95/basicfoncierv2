# Journal

## 2026-08-09 — Amorçage du socle EF sur un dépôt neuf

**Demande :** mettre en place un espace de travail propre pour la création de `basicfoncierv2`, successeur de `basicfoncier` à API simplifiée, tests intégrés et exécution vectorisée sur colonnes pandas.
**Fait :**
- Audit en lecture seule de `basicfoncier` v1 : inventaire de l'API publique, état des tests (une seule assertion réelle sur ~15 fonctions), découverte d'un bug bloquant sur `ref_parcelle_to_parts`.
- Création du dépôt `basicfoncierv2` et installation du socle EF : `CLAUDE.md`, `docs/{JOURNAL,BUGS,DECISIONS,VOCABULAIRE,MIGRATION}.md`, commande `/revue`.
- Quatre décisions structurantes prises et consignées : dépôt séparé, vectorisation pandas/pyarrow, API unifiée scalaire/Series, outillage pytest + ruff + CI.
**Fichiers :** `CLAUDE.md`, `README.md`, `.gitignore`, `.claude/commands/revue.md`, `docs/*`
**Vérifié par :** aucune commande — aucun code applicatif écrit à ce stade. Le bug du v1 a été reproduit par exécution directe dans le dépôt v1 (lecture seule).
**À savoir :** le dépôt v1 n'a reçu aucune modification de code. Le paquet `basicfoncierv2` lui-même n'existe pas encore : ni `pyproject.toml`, ni arborescence source, ni tests. C'est l'objet de la première tâche.
