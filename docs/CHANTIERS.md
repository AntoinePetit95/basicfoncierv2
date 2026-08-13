# Chantiers

Ce qui est décidé mais pas fait, et ce qui reste à décider. Les décisions **prises** vont
dans `DECISIONS.md` ; ce fichier ne porte que l'ouvert.

---

## Chantiers ouverts

### 1.1.0 — Calculer sur les valeurs distinctes

Décision et mesures dans `DECISIONS.md`, entrée du 2026-08-12. Sept unités, chacune à
livrer avec ses tests.

| # | Unité | Ce qu'elle fait |
|---|---|---|
| 1 | `_internal/repetitions.py` | Sonder 10 000 lignes (≈ 1 ms) et choisir : plages, dictionnaire ou calcul direct |
| 2 | Entrées encodées | Accepter `category` et `dictionary` — corrige le défaut consigné dans `BUGS.md` |
| 3 | Report des positions fautives | Redéployer le masque d'invalidité sur les lignes **seulement s'il y a une erreur** |
| 4 | Famille `commune` | Le gain principal : x5,5 par le dictionnaire, x10,0 par les plages |
| 5 | Famille `superficie` | x6,2 |
| 6 | Famille `ref_cadastrale` | **Exclue**, avec un test vérifiant que la sonde décline : références uniques à 81 %, où le dictionnaire rend x0,41 |
| 7 | Banc d'essai et docs | Jeux ordonné / mélangé / unique ; `CHANGELOG` |

**Le point délicat, à ne pas sous-estimer :** l'unité 3. Les erreurs annoncent
aujourd'hui « *N codes invalides sur M, aux positions […]* ». Calculés sur les valeurs
distinctes, ces deux nombres deviennent faux. Une colonne où la même valeur fautive
apparaît mille fois doit toujours signaler mille lignes, pas une. C'est le vrai travail
de cette version, et il mérite ses propres tests.

### Noyau fusionné en C ou Cython — reporté, pas abandonné

Plancher mesuré à 25 ms contre 500 ms : la seule piste donnant accès à un ordre de
grandeur. Se paie en roues binaires par plateforme et par version de Python, en
compilateur dans la CI, et par la fin de la roue pure Python. À rouvrir si le levier
dictionnaire ne suffit pas.

### Supprimer le dépôt v1, puis renommer celui-ci `basicfoncier`

**Tranché par le propriétaire du dépôt le 2026-08-12** : le v1 n'est utilisé nulle part,
ni par lui ni, à sa connaissance, par quiconque. Il sera supprimé, et ce dépôt prendra son
nom. Le paquet s'appelle déjà `basicfoncier` sur PyPI ; seul le dépôt garde `basicfoncierv2`.

Ordre à respecter, faute de quoi on casse ce qu'on veut préserver :

1. ~~**Recopier le code fautif du v1 dans la documentation.**~~ **Fait le 2026-08-13** :
   les trois extraits sont dans `BUGS.md`, avec leur chemin d'origine et le commit. Trois
   textes publiés que cette suppression allait rendre faux sont corrigés : la promesse
   « le v1 reste disponible » (`README`, `MIGRATION.md`), le conseil d'épinglage qui
   renvoyait à une version absente de PyPI, et les URL de `pyproject.toml`.
2. **Vérifier une dernière fois qu'aucun programme n'installe depuis l'URL GitHub du v1.**
   Un `pip install git+…/basicfoncier` cesserait de fonctionner sans message utile.
3. **Archiver le v1 avant de le supprimer.** Une suppression GitHub est définitive. Au
   minimum : un clone complet conservé hors GitHub.
4. **Supprimer le v1, puis renommer ce dépôt.** GitHub refuse le nom tant que l'autre existe.
5. **Mettre à jour le publieur de confiance PyPI** — il nomme le dépôt. Sans cette étape,
   la publication de la 1.1.0 échouera à l'authentification, et le message d'erreur ne dira
   pas pourquoi.
6. **Ramener les trois URL de `pyproject.toml` sur `basicfoncier`.** Elles pointent
   aujourd'hui sur `basicfoncierv2` — voir ci-dessous. GitHub redirige après un renommage,
   donc rien ne casse dans l'intervalle ; c'est une question de justesse, pas de panne.

---

## Décisions en attente

Ce que je n'ai pas tranché seul. Chacune porte ma recommandation et ce qui la déciderait.

### Faut-il un interrupteur pour désactiver l'encodage ?

La sonde choisit seule. Un appelant qui connaît ses données mieux qu'elle n'a aucun moyen
de la contredire, et un appelant surpris par une variation de débit n'a aucun moyen de
l'expliquer.

*Recommandation :* attendre. Ajouter un paramètre est facile, le retirer d'une API
publiée ne l'est pas. **Ce qui déciderait :** un cas réel où la sonde se trompe.

### La 1.1.0 doit-elle publier ses chiffres dans le README ?

Le README ne promet aujourd'hui aucun débit. Annoncer « x5 à x10 » attirerait, mais ces
chiffres dépendent entièrement de la forme des données — la même bibliothèque rend **x0,41**
sur des références cadastrales, uniques à 81 %.

*Recommandation :* annoncer le principe (« le calcul porte sur les valeurs distinctes »)
sans le chiffre, et renvoyer aux mesures de `DECISIONS.md`. **Ce qui déciderait :** un
utilisateur extérieur — issue, question, téléchargement suivi d'un rapport — qui montre
qu'il a choisi ou écarté le paquet sur une question de débit.

### Deux points du socle EF que je ne peux pas trancher moi-même

Le bloc « Socle EF » de `CLAUDE.md` est marqué non modifiable localement. Deux frottements
s'y répètent d'une tâche à l'autre, relevés par les revues :

1. **`docs/` n'est pas un préfixe de branche autorisé.** §10.1 admet `feat/`, `fix/`,
   `chore/`, `refac/` ; §10.2 admet pourtant `docs` comme type de commit. Une branche
   `docs/…` a déjà été fusionnée, celle-ci est la deuxième, et une branche `perf/` —
   également hors liste — a été fusionnée elle aussi. *Recommandation :* ajouter `docs/`
   à §10.1, dans le socle partagé et non ici ; trancher `perf/` en même temps. La règle
   de longueur du même §10.1, elle, ne pose pas de problème : sur dix-sept branches, une
   seule a dépassé quatre mots.
2. **La longueur des entrées de `JOURNAL.md`.** §9 dit « une à trois puces » et « cinq
   lignes suffisent » ; toutes les entrées de ce dépôt, les miennes comprises, en font
   trois à quatre fois plus. Soit la règle vaut et je m'y tiens — au prix de renvoyer le
   détail vers `DECISIONS`, `BUGS` et ce fichier — soit elle est à assouplir dans le socle.
   *Recommandation :* m'y tenir, et n'écrire dans le `JOURNAL` que ce qui sert à
   **reprendre le travail**, jamais ce qui sert à le justifier.

**Ce qui déciderait :** un passage sur le socle EF partagé, qui vaut pour tous les projets
et pas seulement celui-ci.

### Jusqu'où faire remonter le contrat d'appel dans `_internal/appel.py` ?

La repasse d'architecture unifie ce qui est manifestement dupliqué. Reste une zone grise :
faut-il un objet « famille » décrivant chaque domaine (erreur, format attendu, conseil,
noms de champs) et un chemin d'appel entièrement générique, ou garder trois modules
publics lisibles isolément ?

*Recommandation :* s'arrêter à l'unification des cinq formes dupliquées. Un cadre
générique rendrait chaque module illisible sans le cadre. **Ce qui déciderait :**
l'arrivée d'une quatrième famille.

---

## Décisions prises seul, consignées ici pour être contredites

- **Le type de sortie ne change que si l'entrée était encodée.** Rendre systématiquement
  une colonne `category` donnerait le gain maximal — 1,7 ms contre 185,9 sur les codes
  Insee — mais changerait un type visible par les programmes appelants, sans qu'ils
  l'aient demandé. Le gain maximal reste accessible à qui encode son entrée.
- **Les plages entrent dans la 1.1.0 avec le dictionnaire, pas après.** La sonde qui
  choisit doit exister de toute façon ; livrer le dictionnaire seul laisserait de côté le
  x10,0, qui est précisément le cas des lots de parcelles mitoyennes.
- **Les URL de `pyproject.toml` passent sur `basicfoncierv2` maintenant, et non au
  renommage.** Elles désignaient le dépôt du **prédécesseur** : le lien `Changelog` était
  un 404 — le v1 n'a pas de `CHANGELOG.md` — et une issue ouverte depuis PyPI atterrissait
  sur l'autre paquet. Attendre le renommage aurait laissé une 1.1.0 se publier avec des
  liens faux si ce renommage tardait. Le corriger deux fois coûte moins cher que le
  publier une fois de travers.
  **Élargissement de périmètre assumé :** le socle (§11) dit de noter un problème hors
  sujet plutôt que de le corriger. Ici le problème était déjà noté comme chantier, il
  touche du texte **publié**, et le correctif tient en trois lignes. J'ai tranché de le
  faire ; à contredire si la règle doit primer sur le cas d'espèce.
- **`superficie._refuser_non_nombre` reste une exception à l'unification.** Une superficie
  est un nombre et non une chaîne : il faut y exclure `bool` tout en acceptant les
  scalaires numpy. C'est une asymétrie de domaine, pas une dérive. Devenu
  `_est_nombre`, il est passé en prédicat à `est_scalaire` plutôt que supprimé.
- **`_CONSEIL_TEXTE` n'est pas dupliqué**, contrairement à ce que la relecture
  d'architecture annonçait : seul le commentaire au-dessus est identique d'un module à
  l'autre, les trois textes diffèrent réellement — celui de `commune` parle des zéros de
  tête d'un code Insee, celui de `ref_cadastrale` d'une référence non décomposable, celui
  de `superficie` oriente vers l'autre fonction. Rien à factoriser.
- **`_internal/arrow_commun.py` reste en place**, pour la même raison : son type
  `Colonnes` sert bien à la décomposition **et** à la composition. Seul
  `masque_alsace_moselle` est propre à une famille ; le déplacer laisserait un module de
  dix lignes pour un alias de type, ce qui est pire que le défaut qu'on corrige.
- **Le seuil « pas plus de 5 % de perte » du plan est inapplicable en l'état.** Mesuré
  entrelacé, le banc d'essai de cette machine a un plancher de bruit de **±10 %** : les
  écarts changent de signe d'une exécution à l'autre. La non-régression est donc établie
  structurellement — aucun noyau Arrow n'est modifié, le travail par ligne est identique
  au bit près — et non par le chronomètre. Rendre le banc d'essai capable de détecter
  5 % demanderait de le refondre en comparaisons entrelacées, ce qui est un chantier en
  soi. **Fait le 2026-08-13** : le banc d'essai apparie désormais les tours, et un écart
  de 5 % est détectable s'il est stable — voir la décision ci-dessous.
- **Le banc d'essai compare des rapports par tour, et non des durées agrégées.** Le plan
  prévoyait de comparer les médianes de chaque variante. Mesuré, ce n'était pas
  suffisant : les perturbations frappent les **deux** variantes du même tour — un
  ralentissement d'un facteur quatre relevé sur six tours — si bien que l'étendue des
  durées atteint ±150 % alors que le rapport, lui, ne bouge pas. Diviser tour par tour
  rend le gain lisible malgré ces à-coups, et le critère devient net : si les rapports
  encadrent 1, l'ordre s'inverse et il n'y a rien à conclure. Un tour de chauffe non
  compté a dû être ajouté par la même occasion — sans lui, l'étendue montait à ±3 000 %.
