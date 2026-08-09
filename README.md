# basicfoncierv2

Références cadastrales et superficies foncières françaises, vectorisées sur colonnes entières de `pandas`.

Une seule fonction par concept. Chacune accepte indifféremment une valeur seule ou une `Series`, et renvoie le résultat de même nature. Une donnée invalide lève une erreur qui la nomme — jamais un silence.

```python
from basicfoncierv2.ref_cadastrale import to_idu, to_parts
from basicfoncierv2.superficie import to_ha_a_ca
from basicfoncierv2.commune import to_commune_et_arrondissement

to_idu("78048H11")  # '780480000H0011'
to_parts("780480000H0011")  # ('78048', '000', '0H', '0011')
to_ha_a_ca(11_320)  # '1 ha 13 a 20 ca'
to_commune_et_arrondissement("75107")  # ('75056', '107')

to_parts(df["idu"])  # DataFrame : insee, com_abs, section, numero
```

## Installation

```bash
pip install basicfoncierv2
```

Python ≥ 3.10, `pandas` ≥ 2.1.4, `pyarrow` ≥ 15.0. Huit combinaisons de versions sont vérifiées à chaque commit — voir [la matrice de CI](.github/workflows/tests.yml).

## Ce que fait la bibliothèque

### Références cadastrales

Une référence cadastrale s'écrit sous plusieurs formes : la forme longue dite **idu**, sur 14 caractères, et des formes courtes où les zéros de remplissage et la commune absorbée sont omis. Toutes se ramènent à l'idu.

```python
from basicfoncierv2.ref_cadastrale import (
    idu_from_parts,
    short_id_from_parts,
    to_idu,
    to_parts,
    to_short_id,
)

to_idu("78048H11")  # '780480000H0011'
to_short_id("780480000H0011")  # '78048H11'
to_parts("78048123AB1")  # ('78048', '123', 'AB', '0001')
idu_from_parts("78048", "000", "0H", "0011")  # '780480000H0011'
```

Les quatre champs sortent toujours dans le même ordre — `insee`, `com_abs`, `section`, `numero` — et complétés de zéros à leur largeur canonique.

### Superficies

```python
from basicfoncierv2.superficie import from_ha_a_ca, to_ha_a_ca, to_hectares

to_ha_a_ca(11_320)  # '1 ha 13 a 20 ca'
from_ha_a_ca("1 ha 13 a 20 ca")  # 11320
to_hectares(11_320)  # 1.132
```

La lecture repose sur un motif, pas sur une suppression de lettres : `from_ha_a_ca("1 ha 0 a 3 ca")` vaut bien 10 003 m², et une écriture illisible lève une erreur au lieu de produire un nombre faux.

### Codes Insee de commune

```python
from basicfoncierv2.commune import (
    insee_from_parts,
    to_code_commune,
    to_commune_et_arrondissement,
    to_departement,
)

to_departement("97215")  # '972'  — 3 caractères outre-mer
to_code_commune("97215")  # '15'
insee_from_parts("972", "15")  # '97215'
```

## Colonnes pandas

Toute fonction accepte une `Series` et renvoie une `Series` — ou un `DataFrame` quand le résultat a plusieurs champs. L'index est conservé.

```python
parts = to_parts(df["idu"])  # colonnes insee, com_abs, section, numero
df["surface"] = to_ha_a_ca(df["contenance"])
```

Le calcul est fait par les noyaux `pyarrow` sur la colonne entière, sans boucle Python.

## Données invalides

Par défaut, une valeur illisible lève une erreur métier qui la situe et la nomme :

```
ReferenceCadastraleInvalide: 3 référence(s) cadastrale(s) invalide(s) sur 100000.
Attendu : insee (5 caractères, 2A / 2B admis en Corse) + commune absorbée (3 chiffres,
facultative) + section (1 ou 2 caractères se terminant par une lettre) + numéro (1 à 4
chiffres) ; en Alsace-Moselle (départements 57, 67, 68) : exactement 14 chiffres. Reçu,
aux positions [12, 4074, 88301] : ['7804', 'AB048H11', '78 48']. Passez
invalide='manquant' pour les remplacer par des valeurs manquantes.
```

La position est celle de l'index pandas, pas un numéro de ligne : sur un `DataFrame` réindexé, elle désigne directement la ligne fautive.

Pour tolérer les valeurs illisibles, demandez-le explicitement :

```python
to_parts(df["idu"], invalide="manquant")  # les références illisibles deviennent <NA>
```

Une valeur **absente** en entrée reste absente en sortie, sans erreur : c'est une donnée qui manque, pas une donnée fausse.

Les trois erreurs métier — `ReferenceCadastraleInvalide`, `SuperficieInvalide`, `CodeInseeInvalide` — s'importent depuis `basicfoncierv2`.

## Territoires

Tous les régimes cadastraux français sont couverts, et testés :

| Territoire | Particularité |
|---|---|
| Métropole | cas général |
| Corse | département `2A` / `2B` |
| Outre-mer | département sur 3 caractères (`97215` → `972` + `15`) |
| Alsace-Moselle | sections numériques ; seule la forme idu à 14 chiffres est acceptable |
| Paris, Lyon, Marseille | la référence porte le code d'**arrondissement**, pas celui de la commune |

Ce dernier point mérite d'être connu : la parcelle du pilier Ouest de la tour Eiffel est `75107000CR0002` — `75107`, 7ᵉ arrondissement. Aucune parcelle parisienne ne porte `75056`, le code Insee de la commune de Paris.

```python
parts = to_parts("75107000CR0002")
to_commune_et_arrondissement(parts[0])  # ('75056', '107')
```

## Venir de `basicfoncier`

Ce paquet succède à [`basicfoncier`](https://pypi.org/project/basicfoncier/), qui reste publié et fonctionnel. La migration est volontaire et peut se faire module par module.

**[docs/MIGRATION.md](docs/MIGRATION.md) donne la correspondance complète des fonctions**, les changements de comportement, et un avertissement à lire avant tout : deux fonctions du v1 renvoient des valeurs fausses, et son wrapper pandas transforme les erreurs en valeurs manquantes silencieuses. Si vous les consommez, vérifiez vos colonnes de sortie avant de migrer.

## Documentation

- [docs/MIGRATION.md](docs/MIGRATION.md) — correspondance des fonctions et changements de comportement
- [docs/VOCABULAIRE.md](docs/VOCABULAIRE.md) — vocabulaire cadastral : `idu`, `id court`, `commune absorbée`, `section`, `ha / a / ca`
- [CHANGELOG.md](CHANGELOG.md) — versions

## Licence

[Unlicense](LICENSE) — domaine public.
