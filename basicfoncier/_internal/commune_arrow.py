"""Découpe et recomposition d'une colonne de codes Insee, au niveau Arrow.

Tout se fait par découpes à positions fixes et par masques : aucune extraction par
expression régulière n'est nécessaire ici, la seule variable étant la longueur du code
département, que son préfixe suffit à déterminer.
"""

from __future__ import annotations

from functools import reduce

import pyarrow as pa
import pyarrow.compute as pc

from .insee import (
    ARRONDISSEMENT_ABSENT,
    BORNES_ARRONDISSEMENT,
    COMMUNES_A_ARRONDISSEMENTS,
    LONGUEUR_DEPARTEMENT_METROPOLE,
    LONGUEUR_DEPARTEMENT_OUTRE_MER,
    LONGUEUR_INSEE,
    MOTIF_DEPARTEMENT,
    MOTIF_INSEE,
    PREFIXES_OUTRE_MER,
)

_NUL_TEXTE = pa.scalar(None, type=pa.string())
_PREFIXES_OUTRE_MER = pa.array(PREFIXES_OUTRE_MER, type=pa.string())


def valider(codes: pa.Array) -> pa.Array:
    """Renvoie les codes Insee, nuls là où le format n'est pas respecté."""
    valides = pc.fill_null(pc.match_substring_regex(codes, pattern=MOTIF_INSEE), False)
    return pc.if_else(valides, codes, _NUL_TEXTE)


def positions_invalides(codes: pa.Array, valides: pa.Array) -> pa.Array:
    """Vrai là où un code était présent mais ne respecte pas le format."""
    return pc.and_(pc.is_valid(codes), pc.is_null(valides))


def positions_departements_invalides(departement: pa.Array) -> pa.Array:
    """Vrai là où un code département est présent mais mal formé.

    Contrôlé avant la recomposition : un département d'un seul caractère se ferait sinon
    compenser par le remplissage du code commune, et donnerait un code Insee de bonne
    longueur mais faux — ``("7", "048")`` deviendrait ``"70048"``.
    """
    conforme = pc.fill_null(pc.match_substring_regex(departement, pattern=MOTIF_DEPARTEMENT), False)
    return pc.and_(pc.is_valid(departement), pc.invert(conforme))


def _masque_outre_mer(codes: pa.Array) -> pa.Array:
    """Vrai là où le code département tient sur trois caractères."""
    return pc.is_in(pc.utf8_slice_codeunits(codes, 0, 2), value_set=_PREFIXES_OUTRE_MER)


def departements(codes: pa.Array) -> pa.Array:
    """Extrait le code département, sur 2 ou 3 caractères selon le territoire."""
    return pc.if_else(
        _masque_outre_mer(codes),
        pc.utf8_slice_codeunits(codes, 0, LONGUEUR_DEPARTEMENT_OUTRE_MER),
        pc.utf8_slice_codeunits(codes, 0, LONGUEUR_DEPARTEMENT_METROPOLE),
    )


def codes_communes(codes: pa.Array) -> pa.Array:
    """Extrait le code commune, soit ce qui suit le code département."""
    return pc.if_else(
        _masque_outre_mer(codes),
        pc.utf8_slice_codeunits(codes, LONGUEUR_DEPARTEMENT_OUTRE_MER, LONGUEUR_INSEE),
        pc.utf8_slice_codeunits(codes, LONGUEUR_DEPARTEMENT_METROPOLE, LONGUEUR_INSEE),
    )


def recomposer(departement: pa.Array, code_commune: pa.Array) -> pa.Array:
    """Recolle un code département et un code commune en un code Insee.

    Le code commune est complété de zéros à la largeur que lui laisse le département :
    trois caractères en métropole, deux en outre-mer. Le v1 tronquait au contraire le
    département à deux caractères, ce qui produisait un code de quatre caractères
    outre-mer — voir ``docs/BUGS.md``.
    """
    departement_long = pc.equal(pc.utf8_length(departement), LONGUEUR_DEPARTEMENT_OUTRE_MER)
    complete = pc.if_else(
        departement_long,
        pc.utf8_lpad(code_commune, LONGUEUR_INSEE - LONGUEUR_DEPARTEMENT_OUTRE_MER, padding="0"),
        pc.utf8_lpad(code_commune, LONGUEUR_INSEE - LONGUEUR_DEPARTEMENT_METROPOLE, padding="0"),
    )
    return pc.binary_join_element_wise(departement, complete, "")


def separer_arrondissement(codes: pa.Array) -> dict[str, pa.Array]:
    """Sépare un code d'arrondissement municipal en commune et numéro d'arrondissement.

    Un code qui ne désigne pas un arrondissement ressort inchangé, accompagné de
    :data:`~basicfoncier._internal.insee.ARRONDISSEMENT_ABSENT`.
    """
    appartenances = {
        commune: pc.is_in(codes, value_set=pa.array(arrondissements, type=pa.string()))
        for commune, arrondissements in COMMUNES_A_ARRONDISSEMENTS.items()
    }

    communes = codes
    for commune, appartient in appartenances.items():
        communes = pc.if_else(appartient, commune, communes)

    est_arrondissement = reduce(pc.or_, appartenances.values())
    arrondissements = pc.if_else(
        est_arrondissement,
        pc.utf8_slice_codeunits(codes, *BORNES_ARRONDISSEMENT),
        ARRONDISSEMENT_ABSENT,
    )
    return {
        "insee_commune": communes,
        "arrondissement": pc.if_else(pc.is_null(communes), _NUL_TEXTE, arrondissements),
    }
