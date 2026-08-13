# Journal

## 2026-08-13 — Le banc d'essai apparie ses tours et refuse de conclure sans preuve

**Demande :** rendre le banc d'essai capable de mesurer un écart de 5 %.
**Fait :**
- Les variantes sont chronométrées **à tour de rôle dans une même boucle**, après un tour de chauffe non compté, et le gain se calcule **tour par tour** puis s'encadre à 95 %. Il n'est annoncé que si son intervalle exclut 1 ; `--tours` resserre l'intervalle.
- `benchmarks/mesure.py` sépare le calcul du chronomètre ; `tests/test_banc_d_essai.py` l'éprouve sur des durées injectées, le banc d'essai n'ayant jusqu'ici aucun test.

**Fichiers :** `benchmarks/{mesure,__main__}.py`, `tests/test_banc_d_essai.py`, `docs/{DECISIONS,CHANTIERS,JOURNAL}.md`, `CHANGELOG.md`
**Vérifié par :** `pytest` → 678 passed, les 636 existants inchangés ; `ruff` propre ; `python -m benchmarks --lignes 1000000` annonce cinq gains sur sept, de x1,6 à x15,4, et **refuse** les deux autres.
**À savoir :** mon premier critère — « concluant si tous les tours désignent le même gagnant » — était faux dans le mauvais sens : la revue a montré que sa puissance **diminue** quand on ajoute des tours (55 % à 5 tours, 0,3 % à 50) et qu'il se trompe une fois sur seize. Remplacé par un intervalle de Student sur les logarithmes, mesuré à 5 % de fausse alerte.

## 2026-08-13 — Préserver le code du v1 avant que son dépôt disparaisse

**Demande :** avancer seul sur les chantiers ouverts ; celui-ci d'abord, seul à avoir une contrainte de temps.
**Fait :**
- Les trois extraits du v1 que `BUGS.md` cite y sont recopiés, avec chemin, lignes et commit : sans eux ces constats deviendraient invérifiables à la suppression du dépôt.
- Trois textes **publiés** rendus faux par cette suppression corrigés : la disponibilité du v1 (`README`, `MIGRATION.md`), le conseil d'épinglage qui pointait une version absente de PyPI, les URL de `pyproject.toml`.

**Fichiers :** `docs/{BUGS,MIGRATION,CHANTIERS,JOURNAL}.md`, `README.md`, `pyproject.toml`
**Vérifié par :** `pytest` → 636 passed ; `ruff` propre ; comportements du v1 relevés **par exécution**, extraits recomparés octet à octet par la revue.
**À savoir :** le défaut d'ordre du tuple est le cas normal, pas un cas limite — seule l'Alsace-Moselle en réchappe.

## 2026-08-13 — Un seul chemin d'appel pour les trois familles

**Demande :** repasser sur tout le code et voir si l'architecture gagnerait à être simplifiée.
**Fait :**
- Quatre formes qui étaient recopiées d'un module à l'autre remontent dans `_internal/appel.py` : la répartition valeur seule / colonne (**8 copies**), le patron de message d'erreur (**5 copies**), l'assemblage d'un `DataFrame` à plusieurs champs (2 copies mot pour mot) et le contrôle d'alignement des index (2 copies).
- `tests/test_contrat_appel.py` : le contrat éprouvé sur les **douze** fonctions publiques d'un coup, et le texte des cinq messages métier éprouvé au caractère près. 636 tests au total, contre 488.

**Fichiers :** `basicfoncier/{commune,ref_cadastrale,superficie}.py`, `basicfoncier/_internal/appel.py`, `tests/test_contrat_appel.py`, `CHANGELOG.md`, `docs/CHANTIERS.md`
**Vérifié par :** `pytest` → 636 passed, **les 488 tests existants inchangés** ; `ruff` propre ; la revue a comparé **301 scénarios** exécutés contre l'ancien code et le nouveau — sortie identique octet pour octet ; non-régression de débit établie structurellement, `git diff` ne touchant aucun noyau Arrow.
**À savoir :**
- **Ma justification de non-régression des messages était fausse.** J'avais écrit que « les tests existants, qui les inspectent, passent inchangés » : ils ne les inspectent pas. La revue l'a montré en supprimant purement et simplement la clause « Attendu » du patron — 629 tests verts. La conclusion était juste, la preuve avancée ne valait rien. Cinq mutations sont désormais posées et quatre sont détectées ; la cinquième est un mutant équivalent, expliqué dans le fichier de test.
- Deux points du plan ont fondu à la lecture du code — `_CONSEIL_TEXTE` n'est pas dupliqué, `arrow_commun.py` est bien partagé. Consigné dans `CHANTIERS.md` plutôt que corrigé par du remaniement cosmétique.
- Le banc d'essai s'est révélé incapable de trancher : entrelacé, son plancher de bruit est de ±10 % et les écarts changent de signe d'une exécution à l'autre. Deux exécutions séparées annonçaient jusqu'à +52 % de perte ; l'entrelacement montre du bruit. Chantier ouvert.

## 2026-08-12 — Campagne de mesure : cinq pistes de performance, une retenue

**Demande :** chercher d'autres leviers que le threading — Cython, mise en cache — puis cadrer celui qui est retenu.
**Fait :**
- Cinq pistes mesurées sur parcelles DGFiP réelles, une retenue : calculer sur les valeurs distinctes, par plages ou par dictionnaire selon la forme de la colonne. Détail chiffré et contreparties dans `DECISIONS.md`.
- `docs/CHANTIERS.md` ouvert — décidé mais pas fait, reste à décider, décisions prises seul — et déclaré en §3 de `CLAUDE.md`. Défaut des colonnes `category` consigné dans `BUGS.md`.

**Fichiers :** `docs/{DECISIONS,BUGS,CHANTIERS,JOURNAL}.md`, `CLAUDE.md` (§3 seulement)
**Vérifié par :** `pytest` → 488 passed, `ruff check .` → All checks passed ; mesures entrelacées, neuf tours, médianes, sur données réelles jamais sur le générateur ; chaque prototype confronté à l'implémentation en place avant d'être chronométré.
**À savoir :** trois résultats contre-intuitifs, tous consignés dans `DECISIONS.md` — le noyau fusionné en numpy ne rend que x1,40 là où je pariais un ordre de grandeur ; la sonde de cardinalité doit lire une **saturation** et non un taux ; et ma première campagne, non entrelacée, annonçait x13,4 au lieu de x10,0 parce qu'elle chronométrait sa référence deux fois. La revue l'a trouvée par une division. Aucun code de la bibliothèque modifié.

## 2026-08-10 — Revue de l'écriture filtrée : sept corrections, aucune sur le calcul

**Demande :** respecter la boucle plan → mise en œuvre → revue → correction → fusion.
**Fait :**
- **Revue indépendante de la branche `perf/generateur-realiste-et-ecriture-filtree`.** Verdict : aucun défaut bloquant ni important. `formater` est correct, vérifié contre une réimplémentation de l'ancienne version sur 0 à 30 000 exhaustivement, sur les cas limites, sur des tranches non contiguës, sur 3 000 tirages aléatoires, sur 500 000 valeurs log-normales via l'API publique, et par mutation des nouveaux tests. Sept remarques mineures, toutes documentaires ou sur le banc d'essai.
- **Le générateur produisait des parcelles de contenance nulle**, environ une pour deux mille. Vérifié sur les fichiers DGFiP : **0 contenance nulle sur 673 176**. Le tirage est désormais ramené à un minimum d'un mètre carré. Les trois régimes d'écriture ne bougent pas (21,5 % / 13,7 % / médiane 1 456 m²).
- **Trois docstrings du banc d'essai disaient faux ou trop.** L'ajustement de la loi porte sur les seuils d'écriture, pas sur la loi entière — la queue reste bien plus lourde que la réalité, c'est désormais écrit. Le mélange métropole / Corse / outre-mer ne se justifie pas par le débit (effet mesuré 1,00 à 1,07x, soit du bruit) mais par le fait de ne jamais fabriquer une donnée que la bibliothèque rejetterait. Et `generer_codes_insee` annonçait « arrondissements compris » pour un pour deux mille.
- **Un chiffre faux dans `DECISIONS.md` corrigé.** J'y avais écrit « x2,4 sur des parcelles toutes petites ». Le relecteur a reproduit x5,24 ; je mesure x4,94 sur une colonne entièrement sous 100 m². L'entrée porte désormais **x4,9 à x5,2**. Mon étiquette décrivait en réalité un jeu mixte, pas ce qu'elle disait.
- **Les trois mesures de débit antérieures à la correction du générateur portent maintenant un avertissement explicite** dans `DECISIONS.md`. Le `CHANGELOG` les déclarait obsolètes, mais rien ne le signalait à qui lisait l'entrée.

**Fichiers :** `benchmarks/__main__.py`, `basicfoncier/_internal/superficie_arrow.py`, `docs/DECISIONS.md`
**Vérifié par :** `pytest` → 488 passed ; `ruff check .` + `ruff format --check .` → All checks passed ; distribution du générateur relevée après plafonnement (min 1, 0 nulle, 21,52 % ≥ 1 ha, 13,67 % < 100 m², médiane 1 456) ; gain de `formater` remesuré moi-même plutôt que repris du relecteur.
**À savoir :**
- La revue n'a rien trouvé sur le calcul lui-même, et tout sur ce que j'en avais écrit. Les sept remarques sont des écarts entre le code et sa documentation — chiffre non reproductible, justification inventée après coup, promesse d'une docstring que le code ne tient pas.
- Le seul apport de code de cette passe, le plafonnement à 1 m², vient d'une propriété des données réelles que je n'avais pas vérifiée avant de déclarer le générateur « réaliste ».

## 2026-08-09 — Banc d'essai réaliste, puis écriture des superficies en une passe

**Demande :** avant d'envisager d'autres optimisations, corriger le générateur de mesure puis implémenter l'écriture filtrée.
**Fait :**
- **Le générateur mesurait l'inverse de la charge réelle.** Confronté aux fichiers des parcelles de la DGFiP, sa loi uniforme produit 99,5 % de parcelles d'au moins un hectare quand le cadastre réel en compte 21,4 %. Remplacé par une loi log-normale ajustée sur 837 531 contenances réelles, qui reproduit les trois régimes d'écriture à moins d'un demi-point.
- Corse et outre-mer ajoutés aux générateurs de références et de codes Insee, absents jusque-là — vérifié : 1,01 % et 2,02 % obtenus pour 1 % et 2 % visés, et les 200 000 références produites sont toutes décomposables.
- **`formater` n'écrit plus chaque ligne qu'une fois** au lieu de construire les trois formes possibles pour toutes. Même motif « reconnaître puis découper » que la lecture. **636 ms → 415 ms, x1,5** sur un million de contenances réelles.
- 15 tests ajoutés sur le mélange des trois formes, les bornes de bascule (100 et 10 000 m²), les colonnes d'une seule forme et la colonne vide.

**Fichiers :** `benchmarks/__main__.py`, `basicfoncier/_internal/superficie_arrow.py`, `tests/test_superficie.py`, `CHANGELOG.md`, `docs/DECISIONS.md`
**Vérifié par :** `pytest` → 488 passed (473 avant) ; `ruff check .` → All checks passed ; équivalence avec l'ancienne implémentation confirmée sur les 30 001 valeurs de 0 à 30 000, les bornes exactes, les nuls, la colonne vide et 200 000 contenances réelles ; `python -m benchmarks` → écriture 0,439 s contre 0,636 s.
**À savoir :**
- **Une hypothèse que j'ai testée et qui était fausse :** supprimer les conversions en texte redondantes ne gagne rien du tout (x1,0). Je l'aurais affirmée sans mesurer.
- Le profil a montré que la conversion pandas ↔ Arrow est **gratuite** — moins d'une milliseconde par million de lignes dans les deux sens. Tout le temps est dans les noyaux de calcul.
- Contexte utile pour la suite : `read_parquet` coûte 80 ms par million de lignes, `read_csv` en coûte 915. Pour une chaîne de traitement alimentée en CSV, le format d'entrée pèse plus lourd que tout ce que la bibliothèque peut gagner.
- Les rapports de débit face au v1 publiés avant cette correction portent sur une charge irréaliste. Ceux d'aujourd'hui sont les premiers comparables à la production.

## 2026-08-09 — Le paquet reprend le nom `basicfoncier`, en version 1.0.0

**Demande :** publier sous le nom `basicfoncier` directement, les utilisateurs n'ayant pas à savoir qu'il s'agit d'une v2. Information complémentaire : aucune parcelle de Paris, Lyon ou Marseille n'a jamais été traitée.
**Fait :**
- Paquet renommé `basicfoncierv2` → `basicfoncier`, 41 occurrences dans 16 fichiers, distribution et import compris.
- **Version portée à `1.0.0`, et non `0.1.0`.** Le v1 déclare `version='0.1'`, et **PEP 440 tient `0.1` et `0.1.0` pour la même version** — vérifié. Publier `0.1.0` aurait rendu la réécriture indiscernable du v1 pour `pip`, qui aurait pu considérer une installation existante comme déjà satisfaisante. La version majeure est par ailleurs le signal juste : l'API change entièrement.
- **Benchmarks : le v1 est désormais chargé sous l'alias `basicfoncier_v1`.** Les deux paquets portant le même nom, l'ancien aurait masqué le nouveau et la mesure aurait comparé le paquet à lui-même. Possible parce que le v1 n'emploie que des imports relatifs, qui se résolvent contre le nom d'alias — vérifié avant d'être écrit.
- `MIGRATION.md` et le README réécrits en conséquence : le raccourci « v1 / v2 » y est explicitement défini, puisque seul le numéro de version distingue les deux.
- Question des exports existants **close** : aucune donnée EF ne porte les anciens codes de Paris ou Lyon, la reprise envisagée est sans objet. Consigné dans `BUGS.md`.

**Fichiers :** `basicfoncier/**`, `tests/**`, `benchmarks/__main__.py`, `pyproject.toml`, `README.md`, `CHANGELOG.md`, `CLAUDE.md`, `docs/{BUGS,DECISIONS,MIGRATION}.md`, `.github/workflows/publish.yml`
**Vérifié par :** `pytest` → 473 passed ; `ruff check .` → All checks passed ; roue `basicfoncier-1.0.0-py3-none-any.whl` construite ; `python -m benchmarks` → comparaison au v1 toujours fonctionnelle après renommage (décomposition x3,1 sur 150 000 lignes).
**À savoir :** le dépôt GitHub s'appelle encore `basicfoncierv2` alors que le paquet s'appelle `basicfoncier`. Sans conséquence technique — les URL de `pyproject.toml` pointent sur le dépôt réel — mais c'est une décision qui reste à prendre.

## 2026-08-09 — Version 0.1.0 et workflow de publication

**Demande :** avancer vers la publication ; adresse de contact personnelle plutôt que professionnelle.
**Fait :**
- `version = "0.1.0"`, `CHANGELOG` daté, adresse de l'auteur passée à `antoine.petit@lilo.org` — plus aucune occurrence de l'adresse professionnelle dans le dépôt.
- **`.github/workflows/publish.yml`** en publication de confiance (OIDC), sans jeton stocké. Déclenché par une release GitHub, jamais par un push. Le job de publication est séparé et rattaché à un environnement `pypi`, ce qui permet d'exiger une approbation manuelle.
- Le workflow **refuse de construire tant que la suite ne passe pas**, et **refuse de publier si l'étiquette de la release ne correspond pas à la version déclarée**. C'est exactement le défaut relevé sur le v1, dont l'unique workflow publierait sans avoir rien vérifié.
- Contrôle d'étiquette rejoué localement (`v0.1.0` et `0.1.0` acceptées, `v0.2.0` refusée), YAML des deux workflows validé, roue reconstruite et métadonnées relues.

**Fichiers :** `pyproject.toml`, `CHANGELOG.md`, `.github/workflows/publish.yml`, `README.md`, `CLAUDE.md`, `docs/{DECISIONS,MIGRATION}.md`
**Vérifié par :** `pytest` → 473 passed ; `ruff check .` → All checks passed ; roue `basicfoncierv2-0.1.0-py3-none-any.whl` construite, métadonnées conformes.
**À savoir :**
- **`basicfoncier` n'a jamais été publié sur PyPI.** L'index officiel et l'API JSON renvoient 404 : `pip install basicfoncier` échouerait. J'ai affirmé le contraire dans `CLAUDE.md`, `DECISIONS.md`, `MIGRATION.md` et le README, sans l'avoir jamais vérifié — je l'ai repris d'une note de cadrage et propagé pendant tout le projet. Corrigé partout ; le v1 s'installe depuis son dépôt GitHub, qui est public. La leçon vaut d'être notée : c'est la seule affirmation du projet que je n'avais pas mise à l'épreuve, et elle était fausse.
- Le nom `basicfoncierv2` est libre sur PyPI (404 sur l'index, vérifié le 2026-08-09).
- **La publication de confiance doit être déclarée côté PyPI avant la première release** : nom du projet `basicfoncierv2`, propriétaire `AntoinePetit95`, dépôt `basicfoncierv2`, workflow `publish.yml`, environnement `pypi`. Sans cette déclaration, le job échoue à l'authentification.

## 2026-08-09 — Préparation d'un paquet publiable

**Demande :** README pensé pour un public extérieur, `py.typed`, `CHANGELOG`, suppression d'`adresse`, et vigilance sur les informations internes puisque le paquet ira sur PyPI.
**Fait :**
- **README public** réécrit de bout en bout : installation, les trois modules, le chemin colonne, le contrat sur les données invalides, un tableau des territoires couverts. **Chacun de ses 17 exemples a été exécuté et comparé au résultat annoncé** avant d'être publié.
- **`py.typed`** ajouté et déclaré en `package-data` ; sa présence dans la roue construite est vérifiée.
- **`CHANGELOG.md`** créé, section `[Non publié]`, avec les différences de comportement face au v1.
- **`adresse` supprimé** définitivement du périmètre, avec son équivalent d'une ligne dans `MIGRATION.md` — testé lui aussi, y compris la propagation des valeurs manquantes sur colonne.
- **Classificateurs PyPI** ajoutés (aucun jusque-là), plus les liens `Changelog` et `Issues`. Pas de classificateur `License ::` : la licence est déjà déclarée en expression PEP 639, et les deux ensemble sont refusés.
- **`BUGS.md` restructuré** : la section « Ouverts » ne contenait plus que des défauts *du v1*, ce qu'un lecteur extérieur aurait lu comme « le v2 a trois bugs ouverts ».
- **Traces internes retirées** des documents destinés au public — `README`, `CHANGELOG`, `MIGRATION`, `VOCABULAIRE`, `BUGS`, `DECISIONS` : plus aucune mention d'EF ni renvoi à `CLAUDE.md`.
- Roue construite et métadonnées relues : `Requires-Python: >=3.10`, `License-Expression: Unlicense`, `Description-Content-Type: text/markdown`, dépendances correctes.

**Fichiers :** `README.md`, `CHANGELOG.md`, `pyproject.toml`, `basicfoncierv2/py.typed`, `docs/{BUGS,DECISIONS,MIGRATION}.md`
**Vérifié par :** `pytest` → 473 passed ; `ruff check .` → All checks passed ; roue construite, `py.typed` présent ; 17 exemples du README rejoués.
**À savoir :**
- `ruff format` formate aussi les blocs Python du README : les exemples publiés suivent le style du code, sans effort particulier.
- Le message d'erreur que j'avais écrit dans le README de mémoire était tronqué. Je l'ai remplacé par un message réellement levé, capturé sur une colonne de 100 000 lignes.
- **Reste à trancher, et cela ne se règle pas par une modification de l'arbre :** `CLAUDE.md`, `.claude/commands/revue.md` et ce journal contiennent la méthode de travail interne. Les retirer aujourd'hui ne les retirerait pas de l'historique git, qui deviendra public en même temps que le dépôt. Aucun secret n'y figure — vérifié sur tout l'historique — mais la décision reste entière.

## 2026-08-09 — Plancher Python abaissé à 3.10

**Demande :** élargir `requires-python`, en le prouvant plutôt qu'en le déclarant.
**Fait :**
- Suite exécutée sur Python 3.10.11 (pandas 2.3.3) et 3.11.9 (pandas 3.0.5) avant toute modification : **473 tests verts sur les deux**. Aucune syntaxe postérieure à 3.10 dans le code.
- `requires-python = ">=3.10"`, et `target-version = "py310"` côté ruff pour qu'il refuse ce que le plancher ne comprendrait pas.
- Deux entrées de matrice ajoutées (3.10, 3.11) ; la vérification d'épinglage porte désormais aussi sur la version de Python.

**Fichiers :** `pyproject.toml`, `.github/workflows/tests.yml`, `docs/JOURNAL.md`
**Vérifié par :** `pytest` → 473 passed sur 3.10, 3.11 et 3.12 ; `ruff check .` → All checks passed après abaissement de la cible.
**À savoir :** **pandas 3.0 exige Python ≥ 3.11.** Sous 3.10 la résolution s'arrête à pandas 2.3. L'entrée de matrice 3.10 épingle donc pandas 2.3.3 : sans cela, pip part dans une résolution interminable — c'est ce qui a fait expirer ma première tentative d'installation locale, à dix minutes.

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
