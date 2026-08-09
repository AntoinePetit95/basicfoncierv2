"""Conversion d'une colonne entière de superficies, au niveau Arrow.

Deux sens, tous deux sans boucle Python :

- **écriture** — une superficie en m² se décompose en hectares, ares et centiares par
  divisions entières, puis s'assemble en chaîne par des noyaux de concaténation ;
- **lecture** — une superficie écrite se relit par extraction des trois composantes,
  puis recomposition arithmétique.

Une superficie illisible ressort nulle ; c'est à l'appelant de décider si cela vaut
erreur. Les valeurs manquantes traversent le module sans traitement particulier.
"""

from __future__ import annotations

import pyarrow as pa
import pyarrow.compute as pc

from .unites import (
    COMPOSANTES,
    FACTEURS,
    METRES_CARRES_PAR_ARE,
    METRES_CARRES_PAR_HECTARE,
    MOTIF_HA_A_CA,
)

_NUL_ENTIER = pa.scalar(None, type=pa.int64())


def en_metres_carres_entiers(superficies: pa.Array) -> pa.Array:
    """Arrondit une colonne de superficies au mètre carré le plus proche.

    Une superficie cadastrale est un nombre entier de mètres carrés ; une valeur
    fractionnaire est un artefact de calcul, pas une mesure plus fine.
    """
    if pa.types.is_integer(superficies.type):
        return pc.cast(superficies, pa.int64())
    return pc.cast(pc.round(superficies, ndigits=0), pa.int64(), safe=False)


def positions_negatives(superficies: pa.Array) -> pa.Array:
    """Vrai là où la superficie est strictement négative."""
    return pc.fill_null(pc.less(superficies, 0), False)


def _composantes(metres_carres: pa.Array) -> dict[str, pa.Array]:
    """Décompose des mètres carrés en hectares, ares et centiares."""
    hectares = pc.divide(metres_carres, METRES_CARRES_PAR_HECTARE)
    reste = pc.subtract(metres_carres, pc.multiply(hectares, METRES_CARRES_PAR_HECTARE))
    ares = pc.divide(reste, METRES_CARRES_PAR_ARE)
    centiares = pc.subtract(reste, pc.multiply(ares, METRES_CARRES_PAR_ARE))
    return {"ha": hectares, "a": ares, "ca": centiares}


def _en_texte(valeurs: pa.Array, largeur: int | None = None) -> pa.Array:
    """Écrit des entiers, éventuellement complétés de zéros à gauche."""
    texte = pc.cast(valeurs, pa.string())
    return texte if largeur is None else pc.utf8_lpad(texte, largeur, padding="0")


def formater(metres_carres: pa.Array) -> pa.Array:
    """Écrit une colonne de superficies au format ``ha a ca``.

    Les composantes de tête nulles sont omises, comme le veut l'usage foncier.
    """
    composantes = _composantes(metres_carres)
    hectares, ares, centiares = (composantes[nom] for nom in COMPOSANTES)

    avec_hectares = pc.binary_join_element_wise(
        _en_texte(hectares), " ha ", _en_texte(ares, 2), " a ", _en_texte(centiares, 2), " ca", ""
    )
    avec_ares = pc.binary_join_element_wise(
        _en_texte(ares), " a ", _en_texte(centiares, 2), " ca", ""
    )
    centiares_seuls = pc.binary_join_element_wise(_en_texte(centiares), " ca", "")

    return pc.if_else(
        pc.greater(hectares, 0),
        avec_hectares,
        pc.if_else(pc.greater(ares, 0), avec_ares, centiares_seuls),
    )


def lire(textes: pa.Array) -> pa.Array:
    """Relit une colonne de superficies écrites et renvoie des mètres carrés.

    Une chaîne qui ne correspond pas au format, ou qui ne porte aucune composante,
    ressort nulle : les trois groupes du motif étant facultatifs, il accepterait sinon
    une chaîne vide.
    """
    groupes = pc.extract_regex(textes, pattern=MOTIF_HA_A_CA)
    brutes = {nom: pc.struct_field(groupes, nom) for nom in COMPOSANTES}
    absentes = {nom: pc.equal(valeur, "") for nom, valeur in brutes.items()}
    lues = {
        nom: pc.cast(pc.if_else(absentes[nom], "0", brutes[nom]), pa.int64()) for nom in COMPOSANTES
    }

    metres_carres = pc.add(
        pc.add(
            pc.multiply(lues["ha"], FACTEURS["ha"]),
            pc.multiply(lues["a"], FACTEURS["a"]),
        ),
        lues["ca"],
    )

    aucune_composante = pc.and_(absentes["ha"], pc.and_(absentes["a"], absentes["ca"]))
    return pc.if_else(aucune_composante, _NUL_ENTIER, metres_carres)


def positions_illisibles(textes: pa.Array, metres_carres: pa.Array) -> pa.Array:
    """Vrai là où une superficie était écrite mais n'a pas pu être relue."""
    return pc.and_(pc.is_valid(textes), pc.is_null(metres_carres))
