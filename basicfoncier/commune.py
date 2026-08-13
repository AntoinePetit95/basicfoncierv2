"""Codes Insee de commune : département, code commune, arrondissements.

Une seule fonction publique par concept. Chacune accepte indifféremment une chaîne ou
une colonne pandas, et renvoie le résultat de même nature.
"""

from __future__ import annotations

import re
from collections.abc import Callable

import pandas as pd
import pyarrow as pa
import pyarrow.compute as pc

from ._internal.appel import (
    SurInvalide,
    en_colonne_arrow,
    en_dataframe,
    en_serie,
    est_scalaire,
    exiger_meme_index,
    refuser_colonne_non_textuelle,
    signaler_valeurs_fautives,
    sont_des_textes,
    valider_option_invalide,
)
from ._internal.commune_arrow import (
    codes_communes,
    departements,
    positions_departements_invalides,
    positions_invalides,
    recomposer,
    separer_arrondissement,
    valider,
)
from ._internal.insee import (
    ARRONDISSEMENT_ABSENT,
    BORNES_ARRONDISSEMENT,
    COMMUNES_A_ARRONDISSEMENTS,
    FORMAT_ATTENDU,
    FORMAT_DEPARTEMENT_ATTENDU,
    LONGUEUR_DEPARTEMENT_METROPOLE,
    LONGUEUR_DEPARTEMENT_OUTRE_MER,
    LONGUEUR_INSEE,
    MOTIF_DEPARTEMENT,
    MOTIF_INSEE,
    PREFIXES_OUTRE_MER,
)
from .erreurs import CodeInseeInvalide

CHAMPS_ARRONDISSEMENT = ("insee_commune", "arrondissement")

_INSEE_COMPILE = re.compile(MOTIF_INSEE)
_DEPARTEMENT_COMPILE = re.compile(MOTIF_DEPARTEMENT)

#: Ce que l'appelant peut faire d'une colonne qui n'est pas textuelle.
_CONSEIL_TEXTE = (
    "Un code Insee stocké en numérique a perdu ses zéros de tête — le 01 de l'Ain "
    "devient 1 : convertissez la colonne à la lecture du fichier."
)

#: La règle que la recomposition impose à ses deux arguments.
_EXIGENCE_MEME_NATURE = (
    "le département et le code commune doivent être tous deux des chaînes, ou "
    "tous deux des pandas.Series."
)


# --------------------------------------------------------------------------------------
# API publique
# --------------------------------------------------------------------------------------


def to_departement(
    insee: str | pd.Series,
    *,
    invalide: SurInvalide = "erreur",
) -> str | pd.Series:
    """Extrait le code département d'un code Insee de commune.

    Le code fait 2 caractères en métropole — Corse comprise, ``2A``, ``2B`` — et 3 en
    outre-mer.

    :param insee: un code Insee de commune, ou une colonne de codes
    :param invalide: ``"erreur"`` lève :class:`CodeInseeInvalide` sur un code mal
        formé ; ``"manquant"`` le remplace par une valeur manquante
    :return: une chaîne pour une chaîne, une ``Series`` pour une ``Series``
    """
    return _appliquer(insee, invalide, _departement_texte, departements)


def to_code_commune(
    insee: str | pd.Series,
    *,
    invalide: SurInvalide = "erreur",
) -> str | pd.Series:
    """Extrait le code commune d'un code Insee, soit ce qui suit le code département.

    :param insee: un code Insee de commune, ou une colonne de codes
    :param invalide: voir :func:`to_departement`
    :return: une chaîne pour une chaîne, une ``Series`` pour une ``Series``
    """
    return _appliquer(insee, invalide, _code_commune_texte, codes_communes)


def to_commune_et_arrondissement(
    insee: str | pd.Series,
    *,
    invalide: SurInvalide = "erreur",
) -> tuple[str, str] | pd.DataFrame:
    """Sépare un arrondissement municipal de sa commune.

    Paris, Lyon et Marseille sont découpées en arrondissements municipaux qui portent
    leur propre code Insee, et **c'est ce code que porte une référence cadastrale**, non
    celui de la commune. La parcelle du pilier Ouest de la tour Eiffel est
    ``75107000CR0002`` : son champ insee vaut ``75107``, le 7ᵉ arrondissement.

    Dans ce sens de lecture, l'arrondissement est reconnaissable : le code est donc
    ramené à la commune **réelle** du répertoire Insee, l'arrondissement étant rendu à
    part. ``75107`` se sépare en ``("75056", "107")``. Un code qui ne désigne pas un
    arrondissement ressort inchangé, accompagné de ``"000"``.

    La référence cadastrale elle-même n'est pas modifiée : elle continue de porter le
    code d'arrondissement, qui est ce que contiennent les fichiers de la DGFiP.

    :param insee: un code Insee de commune, ou une colonne de codes
    :param invalide: voir :func:`to_departement`
    :return: un couple ``(insee_commune, arrondissement)`` pour une chaîne, un
        ``DataFrame`` de deux colonnes pour une ``Series`` — index conservé
    """
    valider_option_invalide(invalide)

    if est_scalaire(insee):
        valide = _valider_texte(insee, invalide)
        return (pd.NA, pd.NA) if pd.isna(valide) else _separer_texte(valide)

    colonnes = separer_arrondissement(_valider_colonne(insee, invalide))
    return en_dataframe(colonnes, CHAMPS_ARRONDISSEMENT, insee.index)


def insee_from_parts(
    departement: str | pd.Series,
    code_commune: str | pd.Series,
) -> str | pd.Series:
    """Recompose un code Insee à partir d'un code département et d'un code commune.

    Le code commune est complété de zéros à la largeur que lui laisse le département :
    3 caractères en métropole, 2 en outre-mer. Contrairement au v1, ``("972", "15")``
    redonne bien ``"97215"``.

    .. warning::
       **Paris, Lyon et Marseille.** Rien dans un code département et un code commune ne
       permet de deviner l'arrondissement : la recomposition se contente donc de
       concaténer. ``("75", "056")`` donne ``"75056"``, le code de la commune de Paris —
       qu'aucune parcelle parisienne ne porte, puisque les références cadastrales y
       portent le code d'arrondissement (``75101`` à ``75120``). Si vous recomposez un
       code destiné à être rapproché de données cadastrales, partez du code
       d'arrondissement : ``("75", "107")`` donne ``"75107"``.

       Le sens inverse, lui, sait trancher : voir :func:`to_commune_et_arrondissement`.

    :raises CodeInseeInvalide: les deux codes ne forment pas un code Insee valide
    """
    parties = {"departement": departement, "code_commune": code_commune}
    if sont_des_textes(parties, _EXIGENCE_MEME_NATURE):
        return _valider_texte(_recomposer_texte(departement, code_commune), "erreur")

    return _recomposer_colonnes(departement, code_commune)


# --------------------------------------------------------------------------------------
# Aiguillage commun
# --------------------------------------------------------------------------------------


def _appliquer(
    insee: str | pd.Series,
    invalide: SurInvalide,
    sur_texte: Callable[[str], str],
    sur_colonne: Callable[[pa.Array], pa.Array],
) -> str | pd.Series:
    """Aiguille vers le chemin scalaire ou le chemin colonne, après validation."""
    valider_option_invalide(invalide)

    if est_scalaire(insee):
        valide = _valider_texte(insee, invalide)
        return pd.NA if pd.isna(valide) else sur_texte(valide)

    return en_serie(sur_colonne(_valider_colonne(insee, invalide)), insee.index)


# --------------------------------------------------------------------------------------
# Chemin scalaire
# --------------------------------------------------------------------------------------


def _valider_texte(insee: str, invalide: SurInvalide) -> str:
    """Vérifie qu'un code Insee respecte le format."""
    # ``fullmatch`` et non ``match`` : le ``$`` du module ``re`` accepte un saut de ligne
    # final, celui de RE2 non. Les deux chemins doivent accepter les mêmes codes.
    if _INSEE_COMPILE.fullmatch(insee):
        return insee
    if invalide == "manquant":
        return pd.NA
    raise CodeInseeInvalide(f"Code Insee invalide : {insee!r}. Attendu : {FORMAT_ATTENDU}.")


def _est_outre_mer(insee: str) -> bool:
    """Indique si le code département tient sur trois caractères."""
    return insee[:2] in PREFIXES_OUTRE_MER


def _longueur_departement(insee: str) -> int:
    """Renvoie la longueur du code département d'un code Insee."""
    if _est_outre_mer(insee):
        return LONGUEUR_DEPARTEMENT_OUTRE_MER
    return LONGUEUR_DEPARTEMENT_METROPOLE


def _departement_texte(insee: str) -> str:
    return insee[: _longueur_departement(insee)]


def _code_commune_texte(insee: str) -> str:
    return insee[_longueur_departement(insee) :]


def _separer_texte(insee: str) -> tuple[str, str]:
    """Sépare un arrondissement municipal de sa commune."""
    debut, fin = BORNES_ARRONDISSEMENT
    for commune, arrondissements in COMMUNES_A_ARRONDISSEMENTS.items():
        if insee in arrondissements:
            return commune, insee[debut:fin]
    return insee, ARRONDISSEMENT_ABSENT


def _recomposer_texte(departement: str, code_commune: str) -> str:
    """Recolle un code département et un code commune, celui-ci complété de zéros."""
    if not _DEPARTEMENT_COMPILE.fullmatch(departement):
        raise CodeInseeInvalide(
            f"Code département invalide : {departement!r}. Attendu : {FORMAT_DEPARTEMENT_ATTENDU}."
        )
    return departement + code_commune.zfill(LONGUEUR_INSEE - len(departement))


# --------------------------------------------------------------------------------------
# Chemin colonne
# --------------------------------------------------------------------------------------


def _valider_colonne(insee: pd.Series, invalide: SurInvalide) -> pa.Array:
    """Valide une colonne entière de codes Insee."""
    refuser_colonne_non_textuelle(insee, "la colonne de codes Insee", _CONSEIL_TEXTE)

    codes = en_colonne_arrow(insee, pa.string())
    valides = valider(codes)
    invalides = positions_invalides(codes, valides)

    if invalide == "erreur" and pc.any(invalides).as_py():
        _signaler_colonne_invalide(insee, invalides)

    return valides


def _recomposer_colonnes(departement: pd.Series, code_commune: pd.Series) -> pd.Series:
    """Recompose une colonne de codes Insee, puis la valide."""
    refuser_colonne_non_textuelle(departement, "la colonne de départements", _CONSEIL_TEXTE)
    refuser_colonne_non_textuelle(code_commune, "la colonne de codes commune", _CONSEIL_TEXTE)

    exiger_meme_index(
        code_commune,
        departement.index,
        designation="la colonne de codes commune",
        reference="celle des départements",
        action="recomposer",
    )

    codes_departements = en_colonne_arrow(departement, pa.string())
    fautifs = positions_departements_invalides(codes_departements)
    if pc.any(fautifs).as_py():
        signaler_valeurs_fautives(
            CodeInseeInvalide,
            departement,
            fautifs,
            sujet="code(s) département invalide(s)",
            format_attendu=FORMAT_DEPARTEMENT_ATTENDU,
            tolerance_possible=False,
        )

    recomposes = recomposer(
        codes_departements,
        en_colonne_arrow(code_commune, pa.string()),
    )
    valides = valider(recomposes)
    invalides = positions_invalides(recomposes, valides)

    if pc.any(invalides).as_py():
        _signaler_colonne_invalide(
            en_serie(recomposes, departement.index), invalides, tolerance_possible=False
        )

    return en_serie(valides, departement.index)


# --------------------------------------------------------------------------------------
# Messages
# --------------------------------------------------------------------------------------


def _signaler_colonne_invalide(
    insee: pd.Series,
    invalides: pa.Array,
    *,
    tolerance_possible: bool = True,
) -> None:
    """Lève une erreur nommant les codes fautifs et leur position.

    :param tolerance_possible: faux quand la fonction appelante n'offre pas d'option
        ``invalide`` — conseiller de la passer enverrait alors l'appelant dans le mur
    """
    signaler_valeurs_fautives(
        CodeInseeInvalide,
        insee,
        invalides,
        sujet="code(s) Insee invalide(s)",
        format_attendu=FORMAT_ATTENDU,
        tolerance_possible=tolerance_possible,
    )
