# Décisions

## 2026-08-09 — Un seul fragment de motif pour le code Insee, partagé entre modules

**Contexte :** la forme d'un code Insee était écrite deux fois. `_internal/insee.py` connaissait la Corse (`(?:[0-9]{2}|2[AB])[0-9]{3}`), `_internal/motifs.py` l'ignorait (`[0-9]{5}`). Conséquence : `commune.to_departement("2A004")` fonctionnait, `ref_cadastrale.to_parts("2A0040000H0011")` levait `ReferenceCadastraleInvalide` — sur une donnée que le v1 décomposait sans difficulté. Toute la Corse était perdue à la migration.

**Retenu :** `_internal/insee.py` expose `FRAGMENT_INSEE`, sans ancrage, que `motifs.py` insère dans `MOTIF_GENERAL` et `MOTIF_IDU_GENERAL`. Une seule écriture de la règle, pour les deux modules.

**Pourquoi :** ce n'est pas un oubli qu'il fallait corriger à deux endroits, c'est une duplication qu'il fallait supprimer. Corriger `motifs.py` en recopiant l'alternative aurait laissé les deux définitions libres de diverger à nouveau au prochain territoire.

**Écarté :** dériver le motif du seul module `motifs.py` (le code Insee est un concept de commune, pas de référence cadastrale : la dépendance irait à l'envers) ; garder `[0-9]{5}` en Alsace-Moselle — retenu au contraire, mais délibérément : les départements 57, 67 et 68 n'ont pas de forme corse, y admettre `2A` élargirait le motif sans raison.

## 2026-08-09 — `fullmatch` côté Python, classes de blancs écrites en clair

**Contexte :** les motifs sont partagés entre deux moteurs, RE2 (PyArrow) pour les colonnes et `re` pour les valeurs seules. Deux divergences les faisaient diverger sur les mêmes données : le `$` de `re` accepte un saut de ligne final, celui de RE2 non ; et le `\s` de `re` couvre l'espace insécable et la tabulation verticale, celui de RE2 non. `to_idu("780480000H0011\n")` réussissait donc en scalaire et échouait en colonne.

**Retenu :** côté Python, `fullmatch` partout à la place de `match` — le motif garde son `$`, seul l'appel change. Côté motif, `\s` remplacé par la classe explicite `[ \t\n\f\r]`.

**Pourquoi :** un motif unique ne garantit pas un comportement unique ; c'est le couple motif + moteur qui décide. Écrire les classes en clair rend la règle lisible sans connaître les deux moteurs, et `fullmatch` supprime la seule divergence que le motif ne pouvait pas absorber.

**Écarté :** deux jeux de motifs, un par moteur (la duplication qu'on vient de supprimer ailleurs) ; nettoyer les entrées avant de les lire (masquerait une donnée douteuse au lieu de la signaler).

## 2026-08-09 — Recoller les colonnes Arrow fragmentées à l'entrée

**Contexte :** `pd.read_parquet(dtype_backend="pyarrow")` rend des colonnes découpées en plusieurs morceaux. `pa.Array.from_pandas` rend alors un `ChunkedArray`, que `pc.replace_with_mask` refuse — noyau qui recolle justement le chemin rapide et le chemin lent. Le plantage était donc dépendant des données : il n'apparaissait que si au moins une valeur empruntait le chemin lent.

**Retenu :** un point d'entrée unique, `appel.en_colonne_arrow`, qui convertit et recolle. Tous les sites de conversion y passent.

**Pourquoi :** le format d'entrée le plus courant en production ne doit pas dépendre du contenu de la colonne pour fonctionner. Recoller une fois à l'entrée coûte un parcours et rend tous les noyaux utilisables sans précaution.

**Écarté :** éviter `replace_with_mask` (revient à renoncer au chemin rapide) ; recoller au cas par cas dans chaque noyau concerné (la prochaine utilisation du noyau suivant ramènerait le défaut).

**À savoir :** selon la version de PyArrow, `combine_chunks()` rend un `Array` (25.x) ou un `ChunkedArray` à un seul morceau (versions antérieures). Les deux formes sont ramenées à un `Array`.

## 2026-08-09 — Lire le signe d'une superficie avant de l'arrondir

**Contexte :** le chemin colonne arrondissait au mètre carré avant de chercher les valeurs négatives. `-0,4` s'arrondit à `0` : la superficie devenait valide et nulle. Le chemin scalaire, lui, la refusait. `to_ha_a_ca(-0.4)` levait une erreur, `to_ha_a_ca(pd.Series([-0.4]))` renvoyait `'0 ca'`.

**Retenu :** le masque des valeurs négatives est calculé sur les valeurs brutes, avant l'arrondi.

**Pourquoi :** l'arrondi est une mise en forme, la validation porte sur la donnée reçue. Les faire dans cet ordre était une inversion, pas un arbitrage.

**Écarté :** aligner le scalaire sur la colonne en arrondissant d'abord (ferait disparaître une donnée aberrante au lieu de la signaler).

## 2026-08-09 — Valider le code département avant de recomposer un code Insee

**Contexte :** `insee_from_parts` complète le code commune à la largeur que lui laisse le département. Si le département est tronqué, le remplissage compense : `("7", "048")` donnait `"70048"` — cinq caractères, conforme au motif d'un code Insee, et faux. Le résultat passait tous les contrôles.

**Retenu :** un motif `MOTIF_DEPARTEMENT` dédié, contrôlé sur les deux chemins avant toute recomposition, avec un message qui nomme le département et non le code recomposé.

**Pourquoi :** valider la sortie ne suffit pas quand la faute d'entrée produit une sortie bien formée. Il n'y a qu'à l'entrée que `"7"` est distinguable de `"07"`.

**Écarté :** exiger un code commune de largeur exacte (rejetterait `("78", "48")`, que le v1 acceptait et que la migration doit continuer d'accepter).

## 2026-08-09 — Inspecter le contenu d'une colonne `object`, pas seulement son dtype

**Contexte :** le garde-fou de type acceptait toute colonne `object`. Or une colonne `object` peut contenir des entiers ; Arrow les convertit alors en texte sans broncher, après que les zéros de tête ont déjà disparu. `to_parts(pd.Series([78048011], dtype=object))` produisait donc une décomposition fausse là où `pd.Series([78048011])` était correctement refusée.

**Retenu :** pour les colonnes `object` uniquement, `pd.api.types.infer_dtype(skipna=True)` décide ; seuls `string` et `empty` passent.

**Pourquoi :** mesuré à 13 ms sur un million de lignes, contre 500 ms pour l'opération complète — 2,5 %, et rien du tout sur une colonne déjà typée. Le prix d'un résultat faux est sans commune mesure.

**Écarté :** parcourir les valeurs en Python (même garantie, un ordre de grandeur plus cher) ; n'inspecter qu'un échantillon (un faux négatif silencieux, soit exactement ce qu'on cherche à supprimer).

## 2026-08-09 — Reprendre telle quelle la table d'arrondissements du v1

**Contexte :** le v1 associe à chaque jeu d'arrondissements municipaux un code commune, et ces codes ne suivent pas la même règle : Marseille reçoit son code Insee réel (13055), Paris et Lyon reçoivent des codes absents du répertoire Insee (75100 et 69300, au lieu de 75056 et 69123).

**Retenu :** reproduire les trois valeurs à l'identique, dans une table unique et nommée, et poser la question dans `docs/BUGS.md`.

**Pourquoi :** ces codes sortent de traitements EF existants. Les « corriger » changerait silencieusement des données produites, sur la seule foi de ma lecture du répertoire Insee — alors qu'il peut s'agir d'une convention interne. Le rôle d'un paquet de migration est de reproduire le comportement connu, pas de le réformer au passage.

**Écarté :** aligner Paris et Lyon sur leurs codes réels (correction plausible, conséquences invérifiables d'ici) ; lever une erreur sur ces deux communes (casserait des traitements qui fonctionnent aujourd'hui).

**Réversibilité :** la table tient dans `_internal/insee.py`. Si la réponse est « ce sont des erreurs », la correction est de deux caractères et d'une mise à jour des cas de test.

## 2026-08-09 — Lire les superficies par découpe, le motif en secours

**Contexte :** la lecture `ha a ca` était **plus lente que le v1** (x0,6). Le profil désignait un seul coupable : le motif tolérant coûtait 1 103 ms sur 1 254, dont 512 pour les `\s*` qui acceptent les espaces multiples. Cette tolérance est nécessaire — les données du v1 en contiennent — donc la retirer était exclu.

**Retenu :** le même schéma que pour les références. Une écriture canonique est *reconnue* par `match_substring_regex` (145 ms, aucune capture), puis découpée à positions fixes comptées depuis la fin. Trois formes seulement, que la longueur suffit à distinguer sans ambiguïté — aucune écriture canonique ne tombe entre les plages 4-5, 9-10 et 15 et plus. Le motif tolérant ne porte plus que sur les lignes non reconnues.

**Écarté :** `extract_regex` avec un motif canonique nommé (581 ms mesurés, contre 400 pour la découpe, et il aurait fallu fusionner six groupes en trois) ; un découpage par `utf8_split_whitespace` (377 ms pour le seul découpage, et `list_element` échoue dès que les listes n'ont pas toutes la même longueur) ; un motif strict unique, qui aurait cassé la lecture des données du v1.

**Mesuré :** lecture **x1,5** contre le v1 — 2 394 228 lignes/s contre 1 619 601, là où le v2 était à x0,6.

**Contrepartie, mesurée elle aussi :** sur une colonne sans **aucune** écriture canonique, le total est de 1 236 ms contre 1 254 pour l'implémentation précédente. Le test de forme et les découpes inutiles se paient donc à peu près exactement ce que le motif économise sur un jeu plus court. Le chemin rapide ne coûte rien quand il ne sert pas — c'est ce qui rend le pari sans risque, contrairement à celui pris sur les références, qui perd 15 % dans son cas défavorable.

## 2026-08-09 — La forme idu comme pivot de tout le module

**Contexte :** cinq fonctions publiques manipulent la même référence sous trois formes — champs séparés, idu, identifiant court. Six conversions possibles, donc six occasions de diverger.

**Retenu :** une seule route. Toute entrée est d'abord normalisée vers la forme idu, puis découpée ou raccourcie. `idu_from_parts` et `short_id_from_parts` assemblent leurs champs puis repassent par `to_idu`. La normalisation valide au passage : une référence illisible ne franchit jamais la première étape, et il n'existe pas de second endroit où la validité serait jugée.

**Conséquence acceptée :** `short_id_from_parts` fait un aller-retour — assemblage, puis relecture. C'est un coût réel, choisi contre la garantie que toute forme produite est relisible. Cette garantie est testée comme propriété : `to_parts(to_short_id(x)) == to_parts(x)` pour chaque forme couverte.

**Écarté :** une fonction de conversion par couple de formes (plus direct, mais la validité se serait jugée en six endroits — c'est exactement ainsi que le v1 a divergé entre ses deux branches de régime).

**Rupture assumée vis-à-vis du v1 :** `idu_from_parts` prend ses arguments dans l'ordre canonique `(insee, com_abs, section, numero)`. Le v1 les prenait dans l'ordre `(insee, section, numero, com_abs)`, avec `com_abs` par défaut. Un appel positionnel du v1 recopié tel quel produirait une référence fausse sans erreur — signalé en tête de `MIGRATION.md`.

## 2026-08-09 — Pas d'identifiant court en Alsace-Moselle

**Contexte :** l'identifiant court retire les zéros de tête de la section et du numéro. En Alsace-Moselle, les sections sont numériques : `to_short_id("57463123456789")` produirait `57463123456789` → `574631234` en appliquant la même règle, et plus rien ne dirait où finit la section.

**Retenu :** en Alsace-Moselle, `to_short_id` renvoie la forme idu inchangée.

**Écarté :** lever une erreur (l'appelant qui raccourcit une colonne entière n'a pas à savoir quels départements elle contient) ; appliquer la règle générale — le v1 le fait, et produit des identifiants que sa propre fonction de lecture rejette.

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
**Retenu :** implémentation native. `pyarrow` devient une dépendance d'exécution.

*Rectification du 2026-08-09, après livraison :* la décision annonçait un passage par les accesseurs pandas (`.str.extract`, `.str.zfill`) et par de l'arithmétique numpy. **Ce n'est pas ce qui a été livré.** Tout passe directement par les noyaux de calcul PyArrow (`extract_regex`, `utf8_slice_codeunits`, `utf8_lpad`, `binary_join_element_wise`, `if_else`, `replace_with_mask`), sans repasser par pandas entre l'entrée et la sortie. La bibliothèque n'appelle plus aucun accesseur `.str`. Cette version est plus rapide et se prête au chemin rapide décrit plus bas, mais elle expose au moteur RE2 — dont les divergences avec le module `re` sont traitées dans les décisions suivantes.
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
