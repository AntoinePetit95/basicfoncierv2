# Décisions

## 2026-08-13 — Le banc d'essai encadre ses gains, et refuse ceux qu'il ne soutient pas

**Contexte :** `benchmarks/` est le critère de succès de toute tâche de vitesse. Il mesurait chaque variante en entier, l'une après l'autre : le rapport publié mêlait l'écart entre les implémentations à la dérive de la machine entre deux moments. Le 2026-08-13, deux exécutions séparées ont ainsi annoncé +52 % là où il n'y avait rien.

**Retenu :** les variantes sont chronométrées **à tour de rôle dans une même boucle**, après un tour de chauffe non compté ; le gain est calculé **tour par tour**, puis encadré à 95 % par un intervalle de Student sur les logarithmes des rapports. Il n'est annoncé que si cet intervalle exclut 1.

**Pourquoi tour par tour :** l'appariement retire la part commune du bruit. Sur six tours réels, l'étendue passe de 133 % et 251 % sur les durées à 78 % sur leur rapport. Elle ne tombe pas à zéro : les à-coups ne frappent pas les deux variantes également — au tour 3, le v1 encaisse 1,2x et le v2 2,5x.

**Pourquoi un intervalle, et non l'étendue observée.** Mon premier critère disait « concluant si tous les tours désignent le même gagnant ». C'est un test des signes, et il a exactement les propriétés qu'il ne faut pas. Mesuré sur 20 000 tirages, gain vrai de 5 %, bruit de 4 % :

| Tours | Test des signes | Intervalle à 95 % |
|---|---|---|
| 3 | 70 % | 23 % |
| 5 | 55 % | 55 % |
| 10 | **31 %** | 96 % |
| 20 | **9 %** | 100 % |

Le test des signes devient **moins** capable à mesure qu'on mesure plus longtemps : le réflexe normal — « c'est bruité, augmentons le nombre de tours » — le détruisait. Son taux de fausse alerte vaut 2/2ⁿ, soit 6,2 % par comparaison à cinq tours ; sur sept comparaisons, une exécution sur trois annonçait un gain inexistant. Vérifié sur du vrai code, une opération comparée à elle-même : 2 fausses alertes sur 40. L'intervalle, lui, tient ses 5 % quel que soit le nombre de tours.

**Ce que le banc d'essai sait détecter, et ce qu'il ne sait pas.** À cinq tours il reconnaît un gain franc — 96 % sur un x2 avec 30 % de bruit — mais **pas** un écart de quelques pour-cent : avec le bruit de cette machine, un gain réel de 5 % n'est reconnu qu'une fois sur six. C'est à cela que sert `--tours`, l'intervalle se resserrant en racine du nombre de tours. Le seuil de 5 % demandé au chantier est donc atteignable, à une vingtaine de tours, et non au réglage par défaut.

**Écarté :** comparer les médianes de chaque variante, comme le prévoyait le plan — l'étendue des durées atteint 374 % là où celle du rapport reste sous 40 %, si bien qu'un critère fondé sur les durées refuserait presque tout. Écarté aussi : une dépendance à scipy pour vingt quantiles.

**Conséquence sur ce fichier :** tout chiffre de débit antérieur à cette date sort de l'ancien banc d'essai. Les gains d'un ordre de grandeur restent valides — aucun bruit ne fabrique un x10. Les écarts proches de 1, eux, ne sont plus soutenus par leur mesure ; les entrées concernées portent désormais un avertissement.

## 2026-08-12 — Calculer sur les valeurs distinctes, et non sur les lignes

**Contexte :** une colonne foncière porte très peu de valeurs différentes. Sur un million de parcelles DGFiP réelles prises au hasard, les codes Insee ne prennent que **2 811 valeurs distinctes** — chacune est donc traitée 356 fois pour un résultat identique. Mieux : les parcelles d'un lot sont mitoyennes, si bien que dans l'ordre du fichier ces valeurs ne sont pas seulement répétées, elles sont **contiguës** : **1 792 plages** pour un million de lignes, soit 558 parcelles consécutives par plage.

**Retenu :** deux encodages complémentaires, choisis par une sonde. L'**encodage par plages** (`run_end_encode`, un balayage linéaire) exploite la contiguïté ; l'**encodage par dictionnaire** (`dictionary_encode`, une table de hachage) exploite la répétition où qu'elle soit. Le calcul porte sur les valeurs encodées, puis le résultat est redistribué.

**Mesuré** sur les 1 000 000 premières lignes d'un échantillon de 1 616 867 parcelles DGFiP réelles. Les quatre variantes sont chronométrées **à tour de rôle dans une même boucle**, neuf tours, médianes : la machine dérive de ±15 % entre exécutions, si bien que deux mesures prises séparément ne se comparent pas. Tous les rapports ci-dessous se déduisent des temps affichés à côté d'eux.

| Colonne (1 000 000 lignes) | Actuel | Plages | Dictionnaire | Entrée déjà encodée |
|---|---|---|---|---|
| **insee, ordre du fichier**<br>1 792 plages, 1 792 distinctes | 185,9 ms | **18,5 ms — x10,0** | 34,0 ms — x5,5 | 11,1 ms — x16,8 |
| **insee, mélangé**<br>998 864 plages, 2 811 distinctes | 226,4 ms | 273,2 ms — **x0,83** | 41,7 ms — x5,4 | 11,6 ms — x19,5 |
| **contenances, ordre du fichier**<br>737 027 plages, 66 003 distinctes | 389,4 ms | 334,8 ms — x1,16 | 62,9 ms — **x6,2** | 45,7 ms — x8,5 |
| **références (idu), ordre du fichier**<br>934 186 plages, 810 199 distinctes | 109,8 ms | 181,6 ms — x0,60 | 265,5 ms — **x0,41** | 92,3 ms — x1,19 |

Si l'appelant accepte de recevoir une colonne encodée plutôt que des chaînes, le calcul sur l'insee ordonné tombe à **1,7 ms** — la redistribution disparaît entièrement. Mesuré à part, donc non entrelacé avec le reste du tableau.

**Les deux contreparties, mesurées elles aussi, et sévères.**

- **Le dictionnaire tombe à x0,41 sur les références cadastrales**, uniques à 81 %. Le hachage y coûte à lui seul **176,9 ms** contre 109,8 ms pour le calcul complet : on paie plus cher que ce qu'on optimise.
- **Les plages tombent à x0,83 dès que l'ordre se perd** — un `sort_values`, un `merge` ou une jointure suffisent — et ne rendent que x1,16 sur les contenances, que le voisinage cadastral ne groupe pas : deux parcelles mitoyennes n'ont pas la même surface.

Aucune des deux techniques n'est donc applicable sans garde. C'est la garde, et non l'encodage, qui est le cœur du travail.

**La garde**, mesurée : sonder 10 000 lignes coûte **0,84 ms**, soit 0,2 à 0,8 % du calcul. Le critère n'est pas le taux de valeurs distinctes de l'échantillon mais sa **saturation** : sur une colonne mélangée, l'insee sonde 0,22 et l'idu 0,998, alors que le premier compte 2 811 valeurs distinctes et le second 810 199. Lu comme une fréquence, ce taux se trompe sur les deux.

**Erratum — deux défauts, pas un.** Une première campagne, publiée puis retirée avant fusion, annonçait x13,4 sur l'insee ordonné et x0,60 sur les références. Elle chronométrait la référence **deux fois** — une fois pour la ligne du tableau, une fois pour le dénominateur des rapports — si bien que les rapports ne se déduisaient pas des temps affichés à côté ; la revue l'a relevé par une simple division. Mais le script de remplacement portait un **second** défaut, trouvé en le relisant : il encodait deux fois par variante, ce qui pénalisait spécifiquement les deux stratégies mesurées et faussait donc les rapports dans l'autre sens. Les chiffres ci-dessus corrigent les deux. Leçon retenue : un rapport qu'on ne peut pas recalculer de tête à partir des temps affichés à côté de lui ne doit pas être publié.

**Écarté, avec les mesures :**

- **Le threading.** x1,6 à 3,2 à quatre fils, x3,9 combiné à l'écriture filtrée — et pire à huit fils, la mémoire étant le facteur limitant. Écarté par l'utilisateur : une bibliothèque appelée depuis un pool de processus prendrait des cœurs à ses appelants sans le leur dire.
- **Cython sur l'orchestration.** Mesuré en comparant le coût à une ligne, entièrement Python, au coût au million : le Python ne pèse que **0,27 à 0,59 %** du temps. Tout le reste est déjà dans les noyaux C++ d'Arrow. Il n'y a rien à y prendre.
- **Le noyau fusionné, écrit en numpy.** L'idée est bonne : remplacer une quinzaine de noyaux Arrow enchaînés par un seul passage écrivant les octets. Implémenté et vérifié identique sur les 30 001 valeurs de 0 à 30 000, sur les bornes et sur 200 000 tirages — puis mesuré : **x1,40**. Le profil dit pourquoi : 125 ms partent à fabriquer 81 Mo d'indices et 174 ms en `log10`, deux coûts qu'une boucle C ne paierait pas et que numpy ne sait pas éviter. Remplacer 40 lignes lisibles par de l'arithmétique de tampon d'octets pour x1,4 est un mauvais échange. **Consigné parce que je pariais bien plus haut.**
- **La mise en cache.** Pour reconnaître une colonne déjà vue, il faut lire tous ses octets : c'est exactement ce que fait `dictionary_encode`, mesuré à **23,7 ms sur l'insee ordonné, soit 70 % du coût total de la stratégie par dictionnaire** (34,0 ms — sur cette colonne, ce sont d'ailleurs les plages qui l'emportent, à 18,5 ms). Fabriquer la clé reviendrait donc presque aussi cher que faire le travail, pour un gain qui ne viendrait que si la **même** colonne était passée deux fois — ce qui n'arrive pas dans une chaîne de traitement, où chaque colonne est traduite une fois. Une clé par identité d'objet éviterait le hachage mais serait fausse dès qu'une colonne est modifiée en place, et retiendrait la mémoire indéfiniment.

**Reporté :** le noyau fusionné écrit en **C ou Cython**. Le plancher mesuré — écrire un million de chaînes, sans aucun calcul — est de **25 ms contre 500 ms** aujourd'hui : la marge est réelle, de l'ordre de x10 à x20, et c'est la seule piste qui y donne accès. Elle se paie en roues binaires par plateforme et par version de Python, en compilateur dans la CI, et par la fin de la roue pure Python qui s'installe partout. À rouvrir si le dictionnaire ne suffit pas.

## 2026-08-09 — Le générateur de mesure suit la distribution cadastrale réelle

**Contexte :** `generer_superficies` tirait une contenance uniforme entre 0 et 2 000 000 m². Confrontée aux fichiers des parcelles de la DGFiP (situation 2025), cette loi s'est révélée **l'inverse de la réalité** : elle produit 99,5 % de parcelles d'au moins un hectare, là où le cadastre réel en compte 21,4 %, avec une médiane à 1 396 m². Toutes les mesures de performance du projet ont donc été faites à plein régime sur une branche du code que la réalité emprunte une fois sur cinq.

**Retenu :** une loi log-normale ajustée sur 837 531 contenances réelles (quatre départements), paramètres `mu = 7,28` et `sigma = 2,444`. Elle reproduit les trois régimes d'écriture à moins d'un demi-point : 21,5 % contre 21,4 % au-dessus de l'hectare, 13,7 % contre 13,2 % sous les 100 m², médiane à 1 456 m² contre 1 396. Le tirage est en outre ramené à un minimum d'un mètre carré : les fichiers DGFiP ne contiennent aucune contenance nulle (vérifié sur 673 176 parcelles), là où l'arrondi de la log-normale en produit une pour deux mille. Les générateurs de références et de codes Insee reçoivent au passage une part de Corse et d'outre-mer, absents jusque-là.

**Pourquoi :** un banc d'essai n'a de valeur que s'il ressemble à la charge. Le nôtre orientait vers l'optimisation d'un cas rare, et aurait fait juger inutile une amélioration qui vaut x1,5 en production. La loi log-normale est le modèle usuel des surfaces foncières, et l'ajustement est vérifié plutôt que postulé.

**Écarté :** lire un vrai fichier DGFiP dans le banc d'essai (il cesserait d'être reproductible et autonome, et dépendrait de données non versionnables) ; conserver la loi uniforme en documentant son biais (on continuerait à mesurer la mauvaise chose, en le sachant).

**À savoir :** les rapports face au v1 changent mécaniquement avec la distribution. Ceux publiés avant cette date portent sur une charge irréaliste ; les entrées concernées portent désormais un avertissement.

**Limite assumée :** l'ajustement porte sur les **seuils d'écriture**, seuls déterminants du coût, et non sur la loi entière. La queue reste bien plus lourde que la réalité — quelques parcelles de plusieurs dizaines de km². Sans effet sur la mesure, mais ce générateur n'est pas un modèle du foncier français et ne doit pas être cité comme tel.

## 2026-08-09 — Écrire chaque superficie une fois, et non trois

**Contexte :** `formater` construisait les trois écritures possibles — `ha a ca`, `a ca`, `ca` — pour **chaque** ligne, puis en sélectionnait une par `if_else`. Le travail de chaînes, qui est l'essentiel du coût (98 % du temps de `to_ha_a_ca` au profil), était donc payé trois fois.

**Retenu :** le même motif « reconnaître puis découper » que la lecture emploie déjà. La forme la plus courte sert de fond, les deux autres sont construites sur les seuls sous-ensembles concernés (`pc.filter`) et recollées par `pc.replace_with_mask`.

**Mesuré** sur un million de contenances réelles : **636 ms → 415 ms, x1,5**. Le gain dépend entièrement de la distribution : x1,3 sur l'ancienne loi uniforme, où presque toutes les lignes prennent la forme longue, et **x4,9 à x5,2 sur une colonne entièrement sous les 100 m²**, où aucune ne la prend. C'est précisément pourquoi la décision précédente devait venir en premier : sur l'ancien générateur, on aurait lu x1,3 et jugé que cela n'en valait pas la peine.

**Vérifié :** résultats identiques à l'ancienne implémentation sur les 30 001 valeurs de 0 à 30 000, sur les bornes exactes des trois formes, sur les valeurs nulles, sur une colonne vide, sur des colonnes d'une seule forme, et sur 200 000 contenances réelles.

**Écarté :** supprimer les conversions en texte redondantes — l'hypothèse paraissait solide, la mesure donne **x1,0**, aucun gain. Consigné parce que je l'aurais volontiers affirmée sans mesurer.

> ⚠️ Ce x1,0 vient de l'ancien banc d'essai, incapable de distinguer un petit écart du bruit (décision du 2026-08-13). Il ne prouve pas l'absence de gain, seulement l'absence de gain **visible à cette précision**. La piste est écartée faute de preuve, non réfutée ; à rouvrir avec `--tours 20` si elle redevient intéressante.

## 2026-08-09 — Arrondissements municipaux : conversion asymétrique, assumée

**Contexte :** à Paris, Lyon et Marseille, le champ insee d'une référence cadastrale porte le code de l'**arrondissement municipal**, pas celui de la commune. La parcelle du pilier Ouest de la tour Eiffel est `75107000CR0002` ; aucune parcelle parisienne ne porte `75056`. Ce cas n'avait jamais été traité, ni dans le v1 ni dans le v2. Le v1 associait en outre aux arrondissements des codes commune inexistants (`75100`, `69300`).

**Retenu :** deux comportements différents selon le sens de la conversion.

- **Lecture** — l'arrondissement est reconnaissable à son code : `to_commune_et_arrondissement("75107")` rend `("75056", "107")`, le code Insee **réel** de la commune. La référence cadastrale, elle, n'est pas touchée : elle continue de porter `75107`, qui est ce que contiennent les fichiers de la DGFiP.
- **Construction** — rien dans `("75", "056")` ni dans les quatre champs d'une référence ne dit l'arrondissement. `insee_from_parts` et `idu_from_parts` concatènent sans chercher à deviner. L'avertissement est dans leurs docstrings.

**Pourquoi :** l'asymétrie n'est pas une commodité, c'est la structure du problème. L'information « quel arrondissement » est présente dans un code d'arrondissement et absente d'un code commune ; une fonction ne peut pas restituer ce qu'elle n'a pas reçu. Refuser de trancher dans le sens où l'on peut trancher, au nom de la symétrie, priverait l'appelant d'un résultat qu'il est en droit d'attendre.

**Écarté :** normaliser le champ insee des références vers la commune (`75107000CR0002` → `75056000CR0002`) — produirait une référence qui ne désigne aucune parcelle et casserait toute jointure avec les fichiers DGFiP ; deviner l'arrondissement à la construction en exigeant un champ supplémentaire (changerait la signature de fonctions de la parité v1) ; lever une erreur quand on reçoit `75056` en construction (le code est valide, et l'appelant peut vouloir un code commune pour autre chose qu'une parcelle).

**Sources :** codes commune et plages d'arrondissements vérifiés au Code officiel géographique de l'Insee — Paris `75056` / `75101`-`75120`, Lyon `69123` / `69381`-`69389`, Marseille `13055` / `13201`-`13216`. Les plages du v1 étaient exactes ; seuls deux codes commune étaient faux.

**Conséquence :** changement de valeurs produites pour Paris et Lyon, signalé en tête de la section Communes de `docs/MIGRATION.md`.

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

**Pourquoi :** ces codes sortent de traitements existants. Les « corriger » changerait silencieusement des données produites, sur la seule foi de ma lecture du répertoire Insee — alors qu'il peut s'agir d'une convention interne. Le rôle d'un paquet de migration est de reproduire le comportement connu, pas de le réformer au passage.

**Écarté :** aligner Paris et Lyon sur leurs codes réels (correction plausible, conséquences invérifiables d'ici) ; lever une erreur sur ces deux communes (casserait des traitements qui fonctionnent aujourd'hui).

**Réversibilité :** la table tient dans `_internal/insee.py`. Si la réponse est « ce sont des erreurs », la correction est de deux caractères et d'une mise à jour des cas de test.

**➜ Renversée le 2026-08-09** par la décision « Arrondissements municipaux » ci-dessus : la réponse est venue, ce sont bien deux erreurs. La réversibilité annoncée était juste — la correction a effectivement tenu en deux valeurs et une mise à jour des tests.

## 2026-08-09 — Lire les superficies par découpe, le motif en secours

**Contexte :** la lecture `ha a ca` était **plus lente que le v1** (x0,6). Le profil désignait un seul coupable : le motif tolérant coûtait 1 103 ms sur 1 254, dont 512 pour les `\s*` qui acceptent les espaces multiples. Cette tolérance est nécessaire — les données du v1 en contiennent — donc la retirer était exclu.

**Retenu :** le même schéma que pour les références. Une écriture canonique est *reconnue* par `match_substring_regex` (145 ms, aucune capture), puis découpée à positions fixes comptées depuis la fin. Trois formes seulement, que la longueur suffit à distinguer sans ambiguïté — aucune écriture canonique ne tombe entre les plages 4-5, 9-10 et 15 et plus. Le motif tolérant ne porte plus que sur les lignes non reconnues.

**Écarté :** `extract_regex` avec un motif canonique nommé (581 ms mesurés, contre 400 pour la découpe, et il aurait fallu fusionner six groupes en trois) ; un découpage par `utf8_split_whitespace` (377 ms pour le seul découpage, et `list_element` échoue dès que les listes n'ont pas toutes la même longueur) ; un motif strict unique, qui aurait cassé la lecture des données du v1.

**Mesuré :** lecture **x1,5** contre le v1 — 2 394 228 lignes/s contre 1 619 601, là où le v2 était à x0,6.

> ⚠️ Chiffre obsolète : mesuré sur l'ancien générateur uniforme, qui produit des écritures presque toutes de la forme longue. Voir « Le générateur de mesure suit la distribution cadastrale réelle ». Le sens de la décision — le chemin rapide vaut mieux que le motif seul — n'est pas en cause ; le rapport chiffré, si.

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

> ⚠️ Chiffre antérieur à la correction du générateur. Ici l'effet est faible : les références ne changent que par l'ajout de la Corse et de l'outre-mer, dont l'incidence mesurée sur le débit tient dans le bruit (1,00 à 1,07x). À reprendre tout de même avant toute publication du chiffre.

**Contrepartie assumée :** sur une colonne composée *uniquement* de formes courtes, le test de forme échoue à chaque ligne et ne sert à rien : le débit tombe à 819 277 lignes/s, environ 15 % de moins que l'implémentation précédente. Le pari est que les fichiers fonciers sont massivement en forme idu. S'il s'avérait faux sur un usage réel, c'est cette décision qu'il faudrait rouvrir.

## 2026-08-09 — Nouveau paquet `basicfoncier` dans un dépôt séparé

**Contexte :** `basicfoncier` est en production et sert de dépendance à d'autres programmes. Il doit rester intact, mais son API et ses performances ne conviennent plus.
**Retenu :** un dépôt indépendant `basicfoncier`, avec son propre versioning et sa propre publication. Le v1 n'est plus touché ; la continuité est assurée par `docs/MIGRATION.md`.
**Écarté :** un second paquet dans le dépôt du v1 (un seul workflow de publication pour deux paquets, et tout commit touche le dépôt en production) ; une branche v2 (une branche durablement divergente n'est pas un paquet distinct).

## 2026-08-09 — Vectorisation native pandas/pyarrow, zéro boucle Python

**Contexte :** le v1 expose ses fonctions « vectorisées » via `np.vectorize`, qui n'est pas une vectorisation : c'est une boucle Python avec un appel de fonction par ligne. C'est le coût dominant sur une colonne de plusieurs centaines de milliers de parcelles.
**Retenu :** implémentation native. `pyarrow` devient une dépendance d'exécution.

*Rectification du 2026-08-09, après livraison :* la décision annonçait un passage par les accesseurs pandas (`.str.extract`, `.str.zfill`) et par de l'arithmétique numpy. **Ce n'est pas ce qui a été livré.** Tout passe directement par les noyaux de calcul PyArrow (`extract_regex`, `utf8_slice_codeunits`, `utf8_lpad`, `binary_join_element_wise`, `if_else`, `replace_with_mask`), sans repasser par pandas entre l'entrée et la sortie. La bibliothèque n'appelle plus aucun accesseur `.str`. Cette version est plus rapide et se prête au chemin rapide décrit plus bas, mais elle expose au moteur RE2 — dont les divergences avec le module `re` sont traitées dans les décisions suivantes.
**Écarté :** numpy pur en dtype `object` (portable et sans dépendance nouvelle, mais les opérations sur chaînes y restent nettement plus lentes qu'en Arrow) ; numba ou Cython (le travail est majoritairement du traitement de chaînes, où ils aident peu, et ils ajoutent une chaîne de compilation à la publication) ; conserver `np.vectorize` (n'attaque pas la cause).

**Mesuré le 2026-08-09, à la première implémentation** (`python -m benchmarks`, 1 million de références) : **x2,1**, et non « un à deux ordres de grandeur » comme annoncé au moment de la décision. Cette prévision était fausse — `np.vectorize` tient 435 000 lignes/s, bien mieux que supposé.

Le profil montre que le coût est intégralement dans les deux passes de `extract_regex` (740 ms sur 1 117 ms). La marge restante est identifiée et chiffrée : sur la forme idu à 14 caractères, la décomposition par découpes fixes coûte 155 ms et sa validation 117 ms, soit environ 290 ms au lieu de 1 117 ms — de l'ordre de x8 contre le v1. La décision reste valide, mais le gain visé ne sera atteint qu'avec ce chemin rapide.

> ⚠️ Chiffre antérieur à la correction du générateur, et de surcroît dépassé par la décision « Normaliser puis découper » ci-dessus. Conservé pour l'histoire du raisonnement, pas comme état des performances.

## 2026-08-09 — Une fonction par concept, acceptant scalaire ou Series

**Contexte :** le v1 impose de choisir entre `basicfoncier.ref_cadastrales.ref_parcelle_to_idu` et `basicfoncier.vectorized_functions.for_pandas.functions.ref_parcelle_to_idu`. Deux chemins d'import pour un même concept, et le second avale silencieusement les erreurs.
**Retenu :** un seul nom public par concept. La fonction accepte une `str` ou une `Series` et renvoie le même type. Le niveau `vectorized_functions.for_pandas` disparaît.
**Écarté :** deux espaces de noms explicites `scalaire` / `series` (honnête sur le coût, mais reconduit le défaut principal du v1 : l'appelant doit choisir) ; un accessor DataFrame `df.foncier.…` (idiomatique, mais lie la bibliothèque à pandas et complique l'usage sur une valeur unique).

## 2026-08-09 — pytest, ruff et CI de test

**Contexte :** le v1 n'a ni linter, ni formateur, ni job de test en CI ; son unique workflow GitHub Actions publierait sur PyPI sans avoir rien vérifié. Un travail autonome n'a de filet que si la suite de tests existe et tourne.
**Retenu :** `pytest` pour les tests, `ruff` pour lint et format, un job GitHub Actions lançant les tests à chaque push. Dépendances de développement uniquement : elles n'atteignent pas les consommateurs du paquet.
**Écarté :** `unittest` de la stdlib seul (zéro dépendance, mais paramétrage et fixtures nettement plus verbeux, et pas de mesure de couverture) ; pytest sans CI (rien ne garantit alors qu'un push ne casse pas la suite).
