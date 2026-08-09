"""Codes Insee de commune : département, code commune, arrondissements.

Une seule fonction publique par concept. Chacune accepte indifféremment une chaîne ou
une colonne pandas, et renvoie le résultat de même nature.
"""

from __future__ import annotations

import re

import pandas as pd
import pyarrow as pa
import pyarrow.compute as pc

from ._internal.appel import (
    NOMBRE_EXEMPLES,
    SurInvalide,
    en_serie,
    erreur_de_type,
    exemples_fautifs,
    refuser_colonne_non_textuelle,
    valider_option_invalide,
)
from ._internal.commune_arrow import (
    codes_communes,
    departements,
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
    LONGUEUR_DEPARTEMENT_METROPOLE,
    LONGUEUR_DEPARTEMENT_OUTRE_MER,
    LONGUEUR_INSEE,
    MOTIF_INSEE,
    PREFIXES_OUTRE_MER,
)
from .erreurs import CodeInseeInvalide

CHAMPS_ARRONDISSEMENT = ("insee_commune", "arrondissement")

_INSEE_COMPILE = re.compile(MOTIF_INSEE)


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

    Paris, Lyon et Marseille sont découpées en arrondissements qui portent leur propre
    code Insee. ``75104`` désigne le 4ᵉ arrondissement de Paris et se sépare en
    ``("75100", "104")``. Un code qui ne désigne pas un arrondissement ressort inchangé,
    accompagné de ``"000"``.

    :param insee: un code Insee de commune, ou une colonne de codes
    :param invalide: voir :func:`to_departement`
    :return: un couple ``(insee_commune, arrondissement)`` pour une chaîne, un
        ``DataFrame`` de deux colonnes pour une ``Series`` — index conservé
    """
    valider_option_invalide(invalide)

    if isinstance(insee, str):
        valide = _valider_texte(insee, invalide)
        return (pd.NA, pd.NA) if pd.isna(valide) else _separer_texte(valide)
    if isinstance(insee, pd.Series):
        colonnes = separer_arrondissement(_valider_colonne(insee, invalide))
        table = pa.table({champ: colonnes[champ] for champ in CHAMPS_ARRONDISSEMENT})
        parts = table.to_pandas(types_mapper=pd.ArrowDtype)
        parts.index = insee.index
        return parts
    raise erreur_de_type(insee, "une chaîne ou une pandas.Series")


def insee_from_parts(
    departement: str | pd.Series,
    code_commune: str | pd.Series,
) -> str | pd.Series:
    """Recompose un code Insee à partir d'un code département et d'un code commune.

    Le code commune est complété de zéros à la largeur que lui laisse le département :
    3 caractères en métropole, 2 en outre-mer. Contrairement au v1, ``("972", "15")``
    redonne bien ``"97215"``.

    :raises CodeInseeInvalide: les deux codes ne forment pas un code Insee valide
    """
    if isinstance(departement, str) and isinstance(code_commune, str):
        return _valider_texte(_recomposer_texte(departement, code_commune), "erreur")

    if isinstance(departement, pd.Series) and isinstance(code_commune, pd.Series):
        return _recomposer_colonnes(departement, code_commune)

    raise TypeError(
        "le département et le code commune doivent être tous deux des chaînes, ou "
        f"tous deux des pandas.Series. Reçu : departement={type(departement).__name__}, "
        f"code_commune={type(code_commune).__name__}."
    )


# --------------------------------------------------------------------------------------
# Aiguillage commun
# --------------------------------------------------------------------------------------


def _appliquer(insee, invalide, sur_texte, sur_colonne):
    """Aiguille vers le chemin scalaire ou le chemin colonne, après validation."""
    valider_option_invalide(invalide)

    if isinstance(insee, str):
        valide = _valider_texte(insee, invalide)
        return pd.NA if pd.isna(valide) else sur_texte(valide)
    if isinstance(insee, pd.Series):
        return en_serie(sur_colonne(_valider_colonne(insee, invalide)), insee.index)
    raise erreur_de_type(insee, "une chaîne ou une pandas.Series")


# --------------------------------------------------------------------------------------
# Chemin scalaire
# --------------------------------------------------------------------------------------


def _valider_texte(insee: str, invalide: SurInvalide) -> str:
    """Vérifie qu'un code Insee respecte le format."""
    if _INSEE_COMPILE.match(insee):
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
    return departement + code_commune.zfill(LONGUEUR_INSEE - len(departement))


# --------------------------------------------------------------------------------------
# Chemin colonne
# --------------------------------------------------------------------------------------


def _valider_colonne(insee: pd.Series, invalide: SurInvalide) -> pa.Array:
    """Valide une colonne entière de codes Insee."""
    refuser_colonne_non_textuelle(insee, "la colonne de codes Insee")

    codes = pa.Array.from_pandas(insee, type=pa.string())
    valides = valider(codes)
    invalides = positions_invalides(codes, valides)

    if invalide == "erreur" and pc.any(invalides).as_py():
        _signaler_colonne_invalide(insee, invalides)

    return valides


def _recomposer_colonnes(departement: pd.Series, code_commune: pd.Series) -> pd.Series:
    """Recompose une colonne de codes Insee, puis la valide."""
    refuser_colonne_non_textuelle(departement, "la colonne de départements")
    refuser_colonne_non_textuelle(code_commune, "la colonne de codes commune")

    if not code_commune.index.equals(departement.index):
        raise ValueError(
            "la colonne de codes commune n'est pas alignée sur celle des départements : "
            f"{len(code_commune)} valeurs contre {len(departement)}, index différents. "
            "Réindexez les colonnes avant de les recomposer."
        )

    recomposes = recomposer(
        pa.Array.from_pandas(departement, type=pa.string()),
        pa.Array.from_pandas(code_commune, type=pa.string()),
    )
    valides = valider(recomposes)
    invalides = positions_invalides(recomposes, valides)

    if pc.any(invalides).as_py():
        _signaler_colonne_invalide(en_serie(recomposes, departement.index), invalides)

    return en_serie(valides, departement.index)


# --------------------------------------------------------------------------------------
# Messages
# --------------------------------------------------------------------------------------


def _signaler_colonne_invalide(insee: pd.Series, invalides: pa.Array) -> None:
    """Lève une erreur nommant les codes fautifs et leur position."""
    fautifs = exemples_fautifs(insee, invalides)
    exemples = fautifs.head(NOMBRE_EXEMPLES)

    raise CodeInseeInvalide(
        f"{len(fautifs)} code(s) Insee invalide(s) sur {len(insee)}. "
        f"Attendu : {FORMAT_ATTENDU}. "
        f"Reçu, aux positions {list(exemples.index)} : {list(exemples)}. "
        "Passez invalide='manquant' pour les remplacer par des valeurs manquantes."
    )
