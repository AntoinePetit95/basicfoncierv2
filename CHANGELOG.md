# Changelog

Le format suit [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/), et le
versionnage [SemVer](https://semver.org/lang/fr/).

## [Non publié]

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
