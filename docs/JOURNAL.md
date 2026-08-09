# Journal

## 2026-08-09 — Arrondissements municipaux de Paris, Lyon et Marseille

**Demande :** traiter un cas particulier jamais implémenté — le code Insee de la commune n'est pas celui que porte la référence cadastrale à Paris, Lyon et Marseille. Sourcer les codes d'arrondissement à l'Insee, et appliquer une conversion asymétrique : concaténation aveugle à la construction, détection de l'arrondissement à la lecture.
**Fait :**
- Codes vérifiés au Code officiel géographique : les trois plages du v1 étaient **exactes** (Paris `75101`-`75120`, Lyon `69381`-`69389`, Marseille `13201`-`13216`). Seuls deux codes commune étaient faux.
- `COMMUNES_A_ARRONDISSEMENTS` passe à `75056` / `69123` / `13055`. `to_commune_et_arrondissement("75107")` rend `("75056", "107")`.
- La référence cadastrale n'est pas touchée : `to_parts("75107000CR0002")` rend `insee="75107"`, et `to_idu` la restitue à l'identique.
- Avertissements en docstring sur `idu_from_parts`, `short_id_from_parts` et `insee_from_parts` : rien dans leurs arguments ne permet de deviner l'arrondissement, elles concatènent.
- 19 tests ajoutés, dont la couverture complète des trois plages, leurs bornes voisines (`75100`, `75121`, `69380`, `69390`, `13217`), et la parcelle du pilier Ouest de la tour Eiffel de bout en bout.

**Fichiers :** `basicfoncierv2/_internal/insee.py`, `basicfoncierv2/{commune,ref_cadastrale}.py`, `tests/test_commune.py`, `docs/{BUGS,DECISIONS,MIGRATION,VOCABULAIRE}.md`
**Vérifié par :** `pytest` → 473 passed (454 avant) ; `ruff check .` → All checks passed ; `ruff format --check .` → clean.
**À savoir :**
- **Changement de valeurs produites.** `75100` → `75056` et `69300` → `69123`. Tout traitement EF qui stocke ou joint sur ces codes verra ses sorties changer. Signalé en tête de la section Communes de `docs/MIGRATION.md`, avec le `replace` qui rétablit l'ancien comportement le temps d'une migration.
- Cela tranche la question que `docs/BUGS.md` laissait ouverte depuis la livraison du module `commune`, et renverse la décision « Reprendre telle quelle la table d'arrondissements du v1 ». J'avais eu raison de ne pas trancher seul : la réponse ne se déduisait pas du code, seulement du métier — et elle allait plus loin que la table, puisque le cas lui-même n'avait jamais été implémenté.
- L'asymétrie entre les deux sens est délibérée et documentée : l'information « quel arrondissement » est présente dans un code d'arrondissement et absente d'un code commune.

## 2026-08-09 — Correction des cinq blocages de la revue indépendante

**Demande :** corriger les constats de la revue lancée en agents indépendants.
**Fait :** cinq blocages, chacun précédé de son test de non-régression.
- **Corse rejetée par `ref_cadastrale`** — deux définitions du code Insee coexistaient, l'une connaissant `2A`/`2B` et l'autre non. Elles sont fusionnées en un fragment unique partagé. `to_parts("2A0040000H0011")` fonctionne, dans toutes les formes et sur les deux chemins.
- **Colonne Arrow fragmentée** — `pd.read_parquet(dtype_backend="pyarrow")` rend une colonne en plusieurs morceaux, que `replace_with_mask` refuse. Recollage à l'entrée par `appel.en_colonne_arrow`, utilisé par tous les sites de conversion.
- **Superficie négative fractionnaire** — le signe est désormais lu avant l'arrondi, sinon `-0,4` devenait `'0 ca'` sur une colonne alors que le scalaire le refusait.
- **Département tronqué** — `insee_from_parts("7", "048")` renvoyait `"70048"` : le remplissage du code commune compensait la lettre manquante. Un motif de département dédié est validé avant toute recomposition.
- **Saut de ligne final** — `fullmatch` remplace `match` sur les trois modules, et la classe de blancs de `MOTIF_HA_A_CA` est écrite en clair : le `$` et le `\s` de `re` ne couvrent pas la même chose que ceux de RE2.

Trois défauts de contrat d'appel corrigés au passage : une colonne `object` contenant des entiers était acceptée, une colonne de booléens passait pour numérique, et un `numpy.int64` était refusé comme superficie. Le code mort `decomposition_arrow.decomposer` est supprimé.

**Fichiers :** `basicfoncierv2/{ref_cadastrale,superficie,commune}.py`, `basicfoncierv2/_internal/{appel,insee,motifs,unites,commune_arrow,decomposition_arrow,composition_arrow}.py`, `tests/test_{ref_cadastrale,superficie,commune}.py`, `.github/workflows/tests.yml`, `CLAUDE.md`, `docs/{BUGS,DECISIONS,MIGRATION}.md`
**Vérifié par :** `pytest` → 454 passed (344 avant) ; `ruff check .` → All checks passed ; `ruff format --check .` → clean ; CI verte sur les six combinaisons de la matrice ; `python -m benchmarks` → décomposition **x6,2**, lecture ha a ca **x1,7**, écriture **x2,4**, hectares **x26,7**, commune et arrondissement **x4,7** — aucune régression.
**À savoir :**
- Les quatre premiers défauts avaient la même forme : **le chemin scalaire et le chemin colonne ne se comportaient pas pareil**. Mes tests validaient chaque chemin séparément, jamais leur accord. Les nouveaux tests confrontent systématiquement les deux.
- Le défaut multi-chunk ne se déclenchait qu'en présence d'au moins une valeur empruntant le chemin lent : un plantage dépendant des données, que des tests sur colonnes courtes et homogènes ne pouvaient pas atteindre.
- `ruff` a rattrapé une faute de ma part : un test que je venais d'écrire portait le nom d'un test existant et le masquait — `pytest` restait vert en en collectant un de moins. `F811`, sans quoi je ne l'aurais pas vu.
- Le contrôle du contenu des colonnes `object` coûte 13 ms par million de lignes, mesuré, contre 500 ms pour l'opération complète.
- La CI se contentait d'afficher les versions installées : elle vérifie maintenant que l'épinglage a tenu, et échoue sinon. Une matrice de six combinaisons pouvait sans cela tester six fois la même. Le job plancher confirme `pandas 2.1.4 / pyarrow 15.0.2 / numpy 1.26.4`.
- **Le message du commit `de42ac1` annonce 471 tests : c'est faux, il y en a 454.** J'avais tronqué la sortie de `pytest` avant sa ligne de résumé et avancé un chiffre que je n'avais pas lu. C'est la comparaison avec le décompte de la CI qui l'a révélé. Le chiffre ci-dessus est le bon.

## 2026-08-09 — Module des communes, parité complète avec le v1

**Demande :** livrer `commune`, dernier module de la parité.
**Fait :**
- `to_departement`, `to_code_commune`, `insee_from_parts`, `to_commune_et_arrondissement`, chaîne ou colonne.
- `insee_from_parts` corrige un **résultat faux** du v1 outre-mer, où la recomposition tronquait le code département. L'aller-retour est testé comme propriété sur métropole, Corse et outre-mer.
- Les codes Insee sont validés par un motif au lieu d'une assertion, Corse (`2A`, `2B`) comprise.
**Fichiers :** `basicfoncierv2/commune.py`, `basicfoncierv2/_internal/{insee,commune_arrow}.py`, `basicfoncierv2/{__init__,erreurs}.py`, `tests/test_commune.py`, `benchmarks/__main__.py`, `docs/{BUGS,DECISIONS,MIGRATION}.md`
**Vérifié par :** `pytest` → 344 passed ; `ruff check .` → All checks passed ; `python -m benchmarks` → département x2,5 · code commune x1,4 · commune et arrondissement x4,7.
**À savoir :** une question métier reste ouverte et **n'est pas de mon ressort** : le v1 associe aux arrondissements de Paris et Lyon des codes commune absents du répertoire Insee (75100, 69300) alors que Marseille reçoit le sien (13055). J'ai reproduit les trois valeurs telles quelles plutôt que d'en « corriger » deux à l'aveugle. Question posée dans `docs/BUGS.md`, décision et réversibilité dans `docs/DECISIONS.md`.

## 2026-08-09 — Lecture rapide des superficies

**Demande :** accélérer `from_ha_a_ca`, plus lente que le v1 à sa livraison.
**Fait :**
- Une écriture canonique est reconnue par un simple test de forme puis découpée à positions fixes ; le motif tolérant ne porte plus que sur le reste.
- Huit tests ajoutés sur le recollage des deux chemins, dont `1 a 4 ca` : la longueur d'une forme canonique sans en être une.
**Fichiers :** `basicfoncierv2/_internal/{unites,superficie_arrow}.py`, `tests/test_superficie.py`, `docs/DECISIONS.md`
**Vérifié par :** `pytest` → 250 passed ; `ruff check .` → All checks passed ; `python -m benchmarks` → lecture 2 394 228 lignes/s contre 1 619 601 pour le v1, soit **x1,5** (x0,6 avant).
**À savoir :** le gain vient d'un test de forme à 145 ms qui remplace un motif à 1 103 ms. Sur une colonne sans aucune écriture canonique, le total reste celui de l'implémentation précédente (1 236 ms contre 1 254) : le chemin rapide ne coûte rien quand il ne sert pas.

## 2026-08-09 — Module des superficies

**Demande :** livrer `superficie` après `ref_cadastrale`.
**Fait :**
- `to_hectares`, `to_ha_a_ca`, `from_ha_a_ca`, chaîne ou colonne, avec la propriété d'aller-retour testée.
- La lecture repose sur un motif et non sur la suppression des lettres : elle corrige un **résultat faux** du v1 sur les écritures non complétées, et refuse ce qu'elle ne sait pas lire.
- Contrôles d'appel communs sortis dans `_internal/appel.py`, partagés avec `ref_cadastrale` : une seule définition de l'option `invalide`, du refus de colonne et de la conversion Arrow vers pandas.
**Fichiers :** `basicfoncierv2/superficie.py`, `basicfoncierv2/_internal/{appel,unites,superficie_arrow}.py`, `basicfoncierv2/{__init__,erreurs,ref_cadastrale}.py`, `tests/test_superficie.py`, `benchmarks/__main__.py`, `docs/{BUGS,MIGRATION}.md`
**Vérifié par :** `pytest` → 242 passed ; `ruff check .` → All checks passed ; `python -m benchmarks` → écriture x2,1 · hectares x37 · **lecture x0,6**.
**À savoir :** la lecture `ha a ca` est **plus lente que le v1**. Le profil est sans ambiguïté : le motif coûte 1 103 ms sur 1 254, dont 512 pour les `\s*` qui rendent la lecture tolérante aux espaces multiples — tolérance nécessaire, les données du v1 en contiennent. Un motif à espaces uniques descend à 591 ms. La piste est donc la même que pour les références : reconnaître la forme canonique d'abord, ne recourir au motif tolérant que pour le reste. C'est la tâche suivante recommandée.

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
