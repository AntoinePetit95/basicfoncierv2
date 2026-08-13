# Changelog

Le format suit [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/), et le
versionnage [SemVer](https://semver.org/lang/fr/).

## [Non publié]

### Modifié

- `to_ha_a_ca` écrit chaque superficie une seule fois au lieu de construire les trois
  formes possibles pour chaque ligne : **x1,5** sur un million de contenances réelles.
  Résultats identiques, aucun changement d'API.

### Interne

- Chemin d'appel unifié : la répartition valeur seule / colonne, le patron de message
  d'erreur, l'assemblage d'un `DataFrame` et le contrôle d'alignement des index n'existent
  plus qu'en un exemplaire, dans `_internal/appel.py`. **Aucun changement de
  comportement** — messages d'erreur identiques au caractère près, vérifiés sur
  301 scénarios face à la version précédente.
- Le générateur du banc d'essai suit désormais la distribution cadastrale réelle, ajustée
  sur 837 531 contenances de la DGFiP. Il tirait jusqu'ici une loi uniforme, qui produit
  99,5 % de parcelles d'au moins un hectare contre 21,4 % dans la réalité. Corse et
  outre-mer y sont également représentés. Les rapports de débit publiés avant cette
  correction portent sur une charge irréaliste.

## [1.0.0] — 2026-08-09

Première version publiée sur PyPI. Réécriture complète de `basicfoncier` `0.1`, dont
elle garde le nom et atteint la parité fonctionnelle.

**L'API change entièrement.** Le passage à une version majeure le signale : `1.0.0`
n'est pas une évolution de la `0.1`, qui s'installait depuis GitHub et n'a jamais été
publiée sur PyPI. Voir [docs/MIGRATION.md](docs/MIGRATION.md) pour la correspondance
fonction par fonction.

> Note de numérotation : PEP 440 tient `0.1` et `0.1.0` pour la **même** version. Publier
> `0.1.0` aurait rendu cette réécriture indiscernable de l'ancienne pour `pip`.

### Ajouté

- Références cadastrales : `to_idu`, `to_short_id`, `to_parts`, `idu_from_parts`,
  `short_id_from_parts`.
- Superficies : `to_hectares`, `to_ha_a_ca`, `from_ha_a_ca`.
- Codes Insee de commune : `to_departement`, `to_code_commune`, `insee_from_parts`,
  `to_commune_et_arrondissement`.
- Trois erreurs métier : `ReferenceCadastraleInvalide`, `SuperficieInvalide`,
  `CodeInseeInvalide`.
- Option `invalide="manquant"` sur toutes les fonctions de lecture, pour tolérer
  explicitement les données illisibles.
- Marqueur `py.typed` : le paquet est entièrement annoté.

### Différences avec `basicfoncier`

Voir [docs/MIGRATION.md](docs/MIGRATION.md) pour la correspondance complète. En résumé :

- **Un seul nom par concept.** Le niveau `vectorized_functions.for_pandas.functions`
  disparaît : la même fonction accepte une `str` ou une `Series`.
- **Plus d'échec silencieux.** Le v1 attrapait toute exception et renvoyait `NA`. Une
  donnée invalide lève désormais une erreur qui la nomme et la situe.
- **Ordre des arguments de `idu_from_parts` et `short_id_from_parts`** :
  `(insee, com_abs, section, numero)`. Un appel positionnel recopié du v1 produit une
  référence fausse sans lever d'erreur.
- **Codes commune de Paris et Lyon** : `75056` et `69123`, codes réels du répertoire
  Insee, là où le v1 renvoyait `75100` et `69300`, qui n'existent pas.
- **Trois résultats faux du v1 corrigés** : ordre de tuple en Alsace-Moselle, lecture
  des écritures `ha a ca` non complétées, recomposition d'un code Insee outre-mer.
- **Vectorisation réelle.** Le v1 employait `np.vectorize`, c'est-à-dire une boucle
  Python. Le calcul se fait ici sur la colonne entière, par les noyaux `pyarrow`.
