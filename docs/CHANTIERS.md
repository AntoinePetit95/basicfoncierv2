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
| 4 | Famille `commune` | Le gain principal : x6,7 à x13,4 |
| 5 | Famille `superficie` | x6,2 |
| 6 | Famille `ref_cadastrale` | **Exclue**, avec un test vérifiant que la sonde décline : références uniques à 82 % |
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

### Renommer le dépôt GitHub

Le paquet s'appelle `basicfoncier` sur PyPI, le dépôt `basicfoncierv2`. Sans conséquence
technique. Déconseillé tant que des programmes installent depuis l'URL GitHub ; imposerait
en outre de mettre à jour le publieur de confiance PyPI.

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

Le README ne promet aujourd'hui aucun débit. Annoncer « x6 à x13 » attirerait, mais ces
chiffres dépendent entièrement de la forme des données — la même bibliothèque rend x0,60
sur une colonne unique.

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
  une colonne `category` donnerait le gain maximal (x90 mesuré sur les codes Insee) mais
  changerait un type visible par les programmes appelants, sans qu'ils l'aient demandé.
  Le gain maximal reste accessible à qui encode son entrée.
- **Les plages entrent dans la 1.1.0 avec le dictionnaire, pas après.** La sonde qui
  choisit doit exister de toute façon ; livrer le dictionnaire seul laisserait de côté le
  x13,4, qui est précisément le cas des lots de parcelles mitoyennes.
- **`superficie._refuser_non_nombre` reste une exception à l'unification.** Une superficie
  est un nombre et non une chaîne : il faut y exclure `bool` tout en acceptant les
  scalaires numpy. C'est une asymétrie de domaine, pas une dérive.
