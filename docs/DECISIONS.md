# Décisions

## 2026-08-09 — Plancher de compatibilité à pandas 2.1.4

**Contexte :** `pandas>=3.0.0` avait été déclaré parce que c'était la seule version testée. C'est une borne dure : elle exclut tout consommateur épinglé sur pandas 2.x. La suite a donc été exécutée contre chaque série mineure, dans des environnements isolés.

**Constaté :** les 65 tests passent sans aucune modification du code de pandas 2.0.3 à 3.0.5, et de Python 3.10 à 3.12. Le code n'est pas le facteur limitant.

**Retenu :** `pandas>=2.1.4`, `pyarrow>=15.0`, et une matrice de CI qui vérifie chaque série mineure plus la combinaison plancher.

**Pourquoi 2.1.4 et pas 2.0.3 :** pandas 2.0.3 et 2.1.1 ont été compilés contre numpy 1.x sans que leurs métadonnées ne bornent numpy. Une installation neuve leur associe numpy 2.x et échoue à l'import sur `ValueError: numpy.dtype size changed`. Ces versions ne fonctionnent qu'en épinglant `numpy<2` à la main. Déclarer un plancher qui n'est atteignable qu'au prix d'un piège serait une fausse compatibilité ; 2.1.4 est la plus ancienne version dont la résolution par défaut aboutit seule.

**numpy retiré des dépendances :** le paquet ne l'importe nulle part — pandas s'en charge. Il passe dans l'extra `dev`, où les benchmarks l'utilisent réellement. La borne `numpy>=2.0` qui figurait auparavant était de surcroît fausse : pandas 2.1.4 s'installe avec numpy 1.26.4.

**Non tranché — le plancher Python.** `requires-python` reste `>=3.12`, faute de mandat. La suite passe pourtant sur Python 3.10 et 3.11 (vérifié). Abaisser cette borne n'élargirait pas la couverture pandas — 2.0.x reste écarté pour la raison ci-dessus — mais ouvrirait le paquet aux projets restés sur ces versions de Python.

## 2026-08-09 — Normaliser puis découper, plutôt qu'extraire

**Contexte :** la première implémentation ne tenait que x2,1 contre le v1, et le profil montrait que la totalité du coût venait de l'extraction par expression régulière (740 ms sur 1 117 ms pour un million de références).
**Retenu :** deux temps. Une référence déjà de forme idu est *reconnue* par un simple test de forme — `match_substring_regex`, qui ne capture rien — puis découpée à positions fixes. Seules les autres sont reconstruites par extraction. L'opération chère ne porte plus que sur une minorité de lignes.
**Écarté :** l'extraction sur toute la colonne (mesurée x2,1) ; une validation par noyaux de classes de caractères plutôt que par motif (plusieurs noyaux à enchaîner, gain incertain) ; la découpe à positions fixes sans validation préalable — elle accepterait des chaînes de quatorze caractères qui ne sont pas des idu, en particulier en Alsace-Moselle où une section alphabétique est invalide.

**Mesuré :** **x4,5 à x4,9** selon les exécutions — 2,2 à 2,5 millions de lignes/s contre environ 500 000 pour le v1.

**Contrepartie assumée :** sur une colonne composée *uniquement* de formes courtes, le test de forme échoue à chaque ligne et ne sert à rien : le débit tombe à 819 277 lignes/s, environ 15 % de moins que l'implémentation précédente. Le pari est que les fichiers fonciers sont massivement en forme idu. S'il s'avérait faux sur un usage réel, c'est cette décision qu'il faudrait rouvrir.

## 2026-08-09 — Nouveau paquet `basicfoncierv2` dans un dépôt séparé

**Contexte :** `basicfoncier` est publié sur PyPI et sert de dépendance à d'autres programmes EF. Il doit rester intact, mais son API et ses performances ne conviennent plus.
**Retenu :** un dépôt indépendant `basicfoncierv2`, avec son propre versioning et sa propre publication. Le v1 n'est plus touché ; la continuité est assurée par `docs/MIGRATION.md`.
**Écarté :** un second paquet dans le dépôt du v1 (un seul workflow de publication pour deux paquets, et tout commit touche le dépôt en production) ; une branche v2 (le socle EF interdit les commits sur `main`, et une branche durablement divergente n'est pas un paquet distinct).

## 2026-08-09 — Vectorisation native pandas/pyarrow, zéro boucle Python

**Contexte :** le v1 expose ses fonctions « vectorisées » via `np.vectorize`, qui n'est pas une vectorisation : c'est une boucle Python avec un appel de fonction par ligne. C'est le coût dominant sur une colonne de plusieurs centaines de milliers de parcelles.
**Retenu :** implémentation native — décomposition des références par regex vectorisée (`.str.extract`), recomposition par `.str.zfill` et concaténation, superficies par arithmétique entière numpy. Chaînes en `string[pyarrow]`. `pyarrow` devient une dépendance d'exécution.
**Écarté :** numpy pur en dtype `object` (portable et sans dépendance nouvelle, mais les opérations sur chaînes y restent nettement plus lentes qu'en Arrow) ; numba ou Cython (le travail est majoritairement du traitement de chaînes, où ils aident peu, et ils ajoutent une chaîne de compilation à la publication) ; conserver `np.vectorize` (n'attaque pas la cause).

**Mesuré le 2026-08-09, à la première implémentation** (`python -m benchmarks`, 1 million de références) : **x2,1**, et non « un à deux ordres de grandeur » comme annoncé au moment de la décision. Cette prévision était fausse — `np.vectorize` tient 435 000 lignes/s, bien mieux que supposé.

Le profil montre que le coût est intégralement dans les deux passes de `extract_regex` (740 ms sur 1 117 ms). La marge restante est identifiée et chiffrée : sur la forme idu à 14 caractères, la décomposition par découpes fixes coûte 155 ms et sa validation 117 ms, soit environ 290 ms au lieu de 1 117 ms — de l'ordre de x8 contre le v1. La décision reste valide, mais le gain visé ne sera atteint qu'avec ce chemin rapide.

## 2026-08-09 — Une fonction par concept, acceptant scalaire ou Series

**Contexte :** le v1 impose de choisir entre `basicfoncier.ref_cadastrales.ref_parcelle_to_idu` et `basicfoncier.vectorized_functions.for_pandas.functions.ref_parcelle_to_idu`. Deux chemins d'import pour un même concept, et le second avale silencieusement les erreurs.
**Retenu :** un seul nom public par concept. La fonction accepte une `str` ou une `Series` et renvoie le même type. Le niveau `vectorized_functions.for_pandas` disparaît.
**Écarté :** deux espaces de noms explicites `scalaire` / `series` (honnête sur le coût, mais reconduit le défaut principal du v1 : l'appelant doit choisir) ; un accessor DataFrame `df.foncier.…` (idiomatique, mais lie la bibliothèque à pandas et complique l'usage sur une valeur unique).

## 2026-08-09 — pytest, ruff et CI de test

**Contexte :** le v1 n'a ni linter, ni formateur, ni job de test en CI ; son unique workflow GitHub Actions publie sur PyPI sans avoir rien vérifié. Le mode autonome du socle EF n'a de filet que si la suite de tests existe et tourne.
**Retenu :** `pytest` pour les tests, `ruff` pour lint et format, un job GitHub Actions lançant les tests à chaque push. Dépendances de développement uniquement : elles n'atteignent pas les consommateurs du paquet.
**Écarté :** `unittest` de la stdlib seul (zéro dépendance, mais paramétrage et fixtures nettement plus verbeux, et pas de mesure de couverture) ; pytest sans CI (rien ne garantit alors qu'un push ne casse pas la suite).
