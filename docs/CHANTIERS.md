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

### Repasse d'architecture

Trois familles publiques font la même chose de trois façons : la répartition
scalaire/colonne est réécrite à la main 8 fois, le patron de message d'erreur 5 fois, et
la conversion d'un résultat multi-colonnes en `DataFrame` est dupliquée mot pour mot.
À unifier dans `_internal/appel.py` **avant** d'y greffer le levier dictionnaire, qui
passe par ce même chemin d'appel.

Contrainte : l'API publique de la 1.0.0 ne bouge pas, et les tests existants passent sans
modification.

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

1. **Vérifier une dernière fois qu'aucun programme n'installe depuis l'URL GitHub du v1.**
   Un `pip install git+…/basicfoncier` cesserait de fonctionner sans message utile.
2. **Archiver le v1 avant de le supprimer.** Une suppression GitHub est définitive, et le
   v1 est la référence de `MIGRATION.md` et de la section « défauts hérités » de `BUGS.md`,
   qui citent son code. Au minimum : un clone complet conservé hors GitHub.
3. **Supprimer le v1, puis renommer ce dépôt.** GitHub refuse le nom tant que l'autre existe.
4. **Mettre à jour le publieur de confiance PyPI** — il nomme le dépôt. Sans cette étape,
   la publication de la 1.1.0 échouera à l'authentification, et le message d'erreur ne dira
   pas pourquoi.
5. Mettre à jour les URL de `pyproject.toml`, du `README` et de `MIGRATION.md`.

**Point à décider au passage :** `MIGRATION.md` et `BUGS.md` renvoient au code du v1 pour
étayer les défauts hérités. Le dépôt disparu, faut-il recopier les extraits concernés dans
la documentation, ou assumer que ces renvois deviennent des références historiques sans
source consultable ? Recommandation : recopier les trois extraits fautifs, courts, au
moment de la suppression — c'est le seul moment où ils sont encore accessibles.

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
sans le chiffre, et renvoyer aux mesures de `DECISIONS.md`. **Ce qui déciderait :** l'idée
qu'on se fait du public du paquet.

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
- **`superficie._refuser_non_nombre` reste une exception à l'unification.** Une superficie
  est un nombre et non une chaîne : il faut y exclure `bool` tout en acceptant les
  scalaires numpy. C'est une asymétrie de domaine, pas une dérive.
