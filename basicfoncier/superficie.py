"""Superficies foncières : hectares, et écriture au format ``ha a ca``.

Une seule fonction publique par concept. Chacune accepte indifféremment une valeur
seule ou une colonne pandas, et renvoie le résultat de même nature.
"""

from __future__ import annotations

import numbers
import re

import pandas as pd
import pyarrow as pa
import pyarrow.compute as pc

from ._internal.appel import (
    NOMBRE_EXEMPLES,
    SurInvalide,
    en_colonne_arrow,
    en_serie,
    erreur_de_type,
    exemples_fautifs,
    refuser_colonne_non_numerique,
    refuser_colonne_non_textuelle,
    valider_option_invalide,
)
from ._internal.superficie_arrow import (
    en_metres_carres_entiers,
    formater,
    lire,
    positions_illisibles,
    positions_negatives,
)
from ._internal.unites import (
    COMPOSANTES,
    FACTEURS,
    FORMAT_ATTENDU,
    METRES_CARRES_PAR_ARE,
    METRES_CARRES_PAR_HECTARE,
    MOTIF_HA_A_CA,
)
from .erreurs import SuperficieInvalide

_HA_A_CA_COMPILE = re.compile(MOTIF_HA_A_CA)

#: Ce que l'appelant peut faire d'une colonne qui n'est pas textuelle.
_CONSEIL_TEXTE = (
    "from_ha_a_ca relit une superficie écrite — « 1 ha 13 a 20 ca » ; pour convertir "
    "une colonne de mètres carrés, c'est to_ha_a_ca qu'il faut appeler."
)


# --------------------------------------------------------------------------------------
# API publique
# --------------------------------------------------------------------------------------


def to_hectares(
    superficie: float | int | pd.Series,
    *,
    invalide: SurInvalide = "erreur",
) -> float | pd.Series:
    """Convertit une superficie en mètres carrés vers des hectares.

    :param superficie: une superficie en m², ou une colonne de superficies
    :param invalide: ``"erreur"`` lève :class:`SuperficieInvalide` sur une superficie
        négative ; ``"manquant"`` la remplace par une valeur manquante
    :return: un flottant pour un nombre, une ``Series`` pour une ``Series``
    """
    valider_option_invalide(invalide)

    if isinstance(superficie, pd.Series):
        metres_carres = _metres_carres_depuis_colonne(superficie, invalide)
        hectares = pc.divide(pc.cast(metres_carres, pa.float64()), float(METRES_CARRES_PAR_HECTARE))
        return en_serie(hectares, superficie.index)
    _refuser_non_nombre(superficie)

    metres_carres = _metres_carres_depuis_nombre(superficie, invalide)
    return pd.NA if pd.isna(metres_carres) else metres_carres / METRES_CARRES_PAR_HECTARE


def to_ha_a_ca(
    superficie: float | int | pd.Series,
    *,
    invalide: SurInvalide = "erreur",
) -> str | pd.Series:
    """Écrit une superficie en mètres carrés au format ``12 ha 34 a 56 ca``.

    Les composantes de tête nulles sont omises : ``22 a 97 ca``, ``93 ca``. La
    superficie est arrondie au mètre carré le plus proche.

    :param superficie: une superficie en m², ou une colonne de superficies
    :param invalide: voir :func:`to_hectares`
    :return: une chaîne pour un nombre, une ``Series`` pour une ``Series``
    """
    valider_option_invalide(invalide)

    if isinstance(superficie, pd.Series):
        metres_carres = _metres_carres_depuis_colonne(superficie, invalide)
        return en_serie(formater(metres_carres), superficie.index)
    _refuser_non_nombre(superficie)

    metres_carres = _metres_carres_depuis_nombre(superficie, invalide)
    return pd.NA if pd.isna(metres_carres) else _formater_nombre(metres_carres)


def from_ha_a_ca(
    superficie: str | pd.Series,
    *,
    invalide: SurInvalide = "erreur",
) -> int | pd.Series:
    """Relit une superficie écrite au format ``ha a ca`` et renvoie des mètres carrés.

    Contrairement à ``basicfoncier`` v1, la lecture repose sur un motif et non sur la
    suppression des lettres : ``1 ha 0 a 3 ca`` vaut bien 10 003 m².

    :param superficie: une superficie écrite, ou une colonne de superficies écrites
    :param invalide: ``"erreur"`` lève :class:`SuperficieInvalide` sur une écriture
        illisible ; ``"manquant"`` la remplace par une valeur manquante
    :return: un entier pour une chaîne, une ``Series`` pour une ``Series``
    """
    valider_option_invalide(invalide)

    if isinstance(superficie, str):
        return _lire_texte(superficie, invalide)
    if isinstance(superficie, pd.Series):
        return en_serie(_lire_colonne(superficie, invalide), superficie.index)
    raise erreur_de_type(superficie, "une chaîne ou une pandas.Series")


# --------------------------------------------------------------------------------------
# Chemin scalaire
# --------------------------------------------------------------------------------------


def _refuser_non_nombre(superficie: object) -> None:
    """Rejette ce qui n'est pas une superficie mesurable.

    ``numbers.Real`` plutôt que ``int | float`` : une valeur tirée d'un tableau numpy est
    un ``numpy.int64``, qui n'hérite ni de l'un ni de l'autre mais mesure tout aussi bien.
    Les booléens en sont exclus explicitement — ``True`` vaut 1 pour Python, jamais un m².
    """
    if isinstance(superficie, bool) or not isinstance(superficie, numbers.Real):
        raise erreur_de_type(superficie, "un nombre ou une pandas.Series")


def _metres_carres_depuis_nombre(superficie: float | int, invalide: SurInvalide) -> int:
    """Arrondit une superficie au mètre carré et refuse les valeurs négatives."""
    if pd.isna(superficie):
        return pd.NA

    if superficie < 0:
        if invalide == "manquant":
            return pd.NA
        raise SuperficieInvalide(
            f"Superficie négative : {superficie}. Une superficie se mesure en mètres "
            "carrés et ne peut pas être inférieure à zéro."
        )

    return round(superficie)


def _formater_nombre(metres_carres: int) -> str:
    """Écrit une superficie unique au format ``ha a ca``."""
    hectares, reste = divmod(metres_carres, METRES_CARRES_PAR_HECTARE)
    ares, centiares = divmod(reste, METRES_CARRES_PAR_ARE)

    if hectares > 0:
        return f"{hectares} ha {ares:02d} a {centiares:02d} ca"
    if ares > 0:
        return f"{ares} a {centiares:02d} ca"
    return f"{centiares} ca"


def _lire_texte(superficie: str, invalide: SurInvalide) -> int:
    """Relit une superficie écrite unique."""
    # ``fullmatch`` et non ``match`` : le ``$`` du module ``re`` accepte un saut de ligne
    # final, celui de RE2 non. Les deux chemins doivent lire les mêmes écritures.
    correspondance = _HA_A_CA_COMPILE.fullmatch(superficie)
    groupes = correspondance.groupdict() if correspondance else {}

    if not any(groupes.get(nom) for nom in COMPOSANTES):
        if invalide == "manquant":
            return pd.NA
        raise SuperficieInvalide(
            f"Superficie illisible : {superficie!r}. Attendu : {FORMAT_ATTENDU}."
        )

    return sum(int(groupes[nom] or 0) * FACTEURS[nom] for nom in COMPOSANTES)


# --------------------------------------------------------------------------------------
# Chemin colonne
# --------------------------------------------------------------------------------------


def _metres_carres_depuis_colonne(superficies: pd.Series, invalide: SurInvalide) -> pa.Array:
    """Arrondit une colonne de superficies et refuse les valeurs négatives."""
    refuser_colonne_non_numerique(superficies, "la colonne de superficies")

    brutes = en_colonne_arrow(superficies)

    # Le signe se lit sur les valeurs brutes, avant l'arrondi : -0,4 s'arrondirait à 0 et
    # passerait pour une superficie nulle valide, là où le chemin scalaire la refuse.
    negatives = positions_negatives(brutes)
    metres_carres = en_metres_carres_entiers(brutes)

    if not pc.any(negatives).as_py():
        return metres_carres

    if invalide == "erreur":
        _signaler_colonne_negative(superficies, negatives)

    return pc.if_else(negatives, pa.scalar(None, type=pa.int64()), metres_carres)


def _lire_colonne(superficies: pd.Series, invalide: SurInvalide) -> pa.Array:
    """Relit une colonne entière de superficies écrites."""
    refuser_colonne_non_textuelle(superficies, "la colonne de superficies", _CONSEIL_TEXTE)

    textes = en_colonne_arrow(superficies, pa.string())
    metres_carres = lire(textes)
    illisibles = positions_illisibles(textes, metres_carres)

    if invalide == "erreur" and pc.any(illisibles).as_py():
        _signaler_colonne_illisible(superficies, illisibles)

    return metres_carres


# --------------------------------------------------------------------------------------
# Messages
# --------------------------------------------------------------------------------------


def _signaler_colonne_negative(superficies: pd.Series, negatives: pa.Array) -> None:
    """Lève une erreur nommant les superficies négatives et leur position."""
    fautives = exemples_fautifs(superficies, negatives)
    exemples = fautives.head(NOMBRE_EXEMPLES)

    raise SuperficieInvalide(
        f"{len(fautives)} superficie(s) négative(s) sur {len(superficies)}. "
        f"Reçu, aux positions {list(exemples.index)} : {list(exemples)}. "
        "Passez invalide='manquant' pour les remplacer par des valeurs manquantes."
    )


def _signaler_colonne_illisible(superficies: pd.Series, illisibles: pa.Array) -> None:
    """Lève une erreur nommant les superficies illisibles et leur position."""
    fautives = exemples_fautifs(superficies, illisibles)
    exemples = fautives.head(NOMBRE_EXEMPLES)

    raise SuperficieInvalide(
        f"{len(fautives)} superficie(s) illisible(s) sur {len(superficies)}. "
        f"Attendu : {FORMAT_ATTENDU}. "
        f"Reçu, aux positions {list(exemples.index)} : {list(exemples)}. "
        "Passez invalide='manquant' pour les remplacer par des valeurs manquantes."
    )
