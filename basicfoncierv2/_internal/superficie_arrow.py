"""Conversion d'une colonne entière de superficies, au niveau Arrow.

Deux sens, tous deux sans boucle Python :

- **écriture** — une superficie en m² se décompose en hectares, ares et centiares par
  divisions entières, puis s'assemble en chaîne par des noyaux de concaténation ;
- **lecture** — une écriture canonique, celle que produit ce module, se lit par
  découpe à positions fixes après un simple test de forme. Le motif tolérant, dix
  fois plus coûteux, ne porte que sur les écritures venues d'ailleurs.

Une superficie illisible ressort nulle ; c'est à l'appelant de décider si cela vaut
erreur. Les valeurs manquantes traversent le module sans traitement particulier.
"""

from __future__ import annotations

import pyarrow as pa
import pyarrow.compute as pc

from .unites import (
    BORNES_ARES,
    BORNES_CENTIARES,
    COMPOSANTES,
    FACTEURS,
    FIN_ARES_SANS_HECTARES,
    FIN_CENTIARES_SEULS,
    FIN_HECTARES,
    LONGUEUR_MAX_CENTIARES_SEULS,
    LONGUEUR_MAX_SANS_HECTARES,
    METRES_CARRES_PAR_ARE,
    METRES_CARRES_PAR_HECTARE,
    MOTIF_HA_A_CA,
    MOTIF_HA_A_CA_CANONIQUE,
)

_NUL_ENTIER = pa.scalar(None, type=pa.int64())
_NUL_TEXTE = pa.scalar(None, type=pa.string())


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


def _recomposer(composantes: dict[str, pa.Array]) -> pa.Array:
    """Additionne les trois composantes, converties en mètres carrés."""
    entieres = {nom: pc.cast(valeur, pa.int64()) for nom, valeur in composantes.items()}
    return pc.add(
        pc.add(
            pc.multiply(entieres["ha"], FACTEURS["ha"]),
            pc.multiply(entieres["a"], FACTEURS["a"]),
        ),
        entieres["ca"],
    )


def _lire_par_decoupe(textes: pa.Array, canoniques: pa.Array) -> pa.Array:
    """Lit les écritures canoniques à positions fixes, comptées depuis la fin.

    Les autres lignes — et les valeurs absentes — ressortent nulles : c'est ce qui
    désigne ensuite les lignes à reprendre par le motif tolérant.
    """
    longueurs = pc.utf8_length(textes)
    centiares_seuls = pc.less_equal(longueurs, LONGUEUR_MAX_CENTIARES_SEULS)
    sans_hectares = pc.less_equal(longueurs, LONGUEUR_MAX_SANS_HECTARES)

    decoupes = {
        "ca": pc.if_else(
            centiares_seuls,
            pc.utf8_slice_codeunits(textes, 0, FIN_CENTIARES_SEULS),
            pc.utf8_slice_codeunits(textes, *BORNES_CENTIARES),
        ),
        "a": pc.if_else(
            centiares_seuls,
            "0",
            pc.if_else(
                sans_hectares,
                pc.utf8_slice_codeunits(textes, 0, FIN_ARES_SANS_HECTARES),
                pc.utf8_slice_codeunits(textes, *BORNES_ARES),
            ),
        ),
        "ha": pc.if_else(sans_hectares, "0", pc.utf8_slice_codeunits(textes, 0, FIN_HECTARES)),
    }
    retenues = {nom: pc.if_else(canoniques, valeur, _NUL_TEXTE) for nom, valeur in decoupes.items()}
    return _recomposer(retenues)


def _lire_par_motif(textes: pa.Array) -> pa.Array:
    """Lit des écritures quelconques par extraction, motif tolérant aux espaces.

    Une chaîne qui ne porte aucune composante ressort nulle : les trois groupes du
    motif étant facultatifs, il accepterait sinon une chaîne vide.
    """
    groupes = pc.extract_regex(textes, pattern=MOTIF_HA_A_CA)
    brutes = {nom: pc.struct_field(groupes, nom) for nom in COMPOSANTES}
    absentes = {nom: pc.equal(valeur, "") for nom, valeur in brutes.items()}
    presentes = {nom: pc.if_else(absentes[nom], "0", brutes[nom]) for nom in COMPOSANTES}

    aucune_composante = pc.and_(absentes["ha"], pc.and_(absentes["a"], absentes["ca"]))
    return pc.if_else(aucune_composante, _NUL_ENTIER, _recomposer(presentes))


def lire(textes: pa.Array) -> pa.Array:
    """Relit une colonne de superficies écrites et renvoie des mètres carrés.

    Les écritures canoniques — celles que produit :func:`formater`, donc l'essentiel
    d'une colonne déjà passée par la bibliothèque — se lisent par découpe. Le motif
    tolérant, dix fois plus coûteux, ne porte que sur le reste.

    Une écriture illisible ressort nulle, tout comme une valeur absente.
    """
    canoniques = pc.fill_null(
        pc.match_substring_regex(textes, pattern=MOTIF_HA_A_CA_CANONIQUE), False
    )
    metres_carres = _lire_par_decoupe(textes, canoniques)

    a_relire = pc.and_(pc.is_valid(textes), pc.invert(canoniques))
    if not pc.any(a_relire).as_py():
        return metres_carres

    return pc.replace_with_mask(
        metres_carres, a_relire, _lire_par_motif(pc.filter(textes, a_relire))
    )


def positions_illisibles(textes: pa.Array, metres_carres: pa.Array) -> pa.Array:
    """Vrai là où une superficie était écrite mais n'a pas pu être relue."""
    return pc.and_(pc.is_valid(textes), pc.is_null(metres_carres))
