"""Références cadastrales : décomposition en champs élémentaires.

Une seule fonction publique par concept. Elle accepte indifféremment une chaîne ou
une colonne pandas, et renvoie le résultat de même nature — un quadruplet pour une
chaîne, un ``DataFrame`` de quatre colonnes pour une ``Series``.
"""

from __future__ import annotations

import re
from typing import Literal

import pandas as pd
import pyarrow as pa
import pyarrow.compute as pc

from ._internal.decomposition_arrow import decomposer, positions_invalides
from ._internal.motifs import (
    CHAMPS,
    FORMAT_ATTENDU,
    LARGEURS,
    MOTIF_ALSACE_MOSELLE,
    MOTIF_GENERAL,
    est_alsace_moselle,
)
from .erreurs import ReferenceCadastraleInvalide

SurInvalide = Literal["erreur", "manquant"]

_OPTIONS_INVALIDE = ("erreur", "manquant")
_NOMBRE_EXEMPLES = 5

_GENERAL_COMPILE = re.compile(MOTIF_GENERAL)
_ALSACE_MOSELLE_COMPILE = re.compile(MOTIF_ALSACE_MOSELLE)


def to_parts(
    ref: str | pd.Series,
    *,
    invalide: SurInvalide = "erreur",
) -> tuple[str, str, str, str] | pd.DataFrame:
    """Décompose une référence cadastrale en ``(insee, com_abs, section, numero)``.

    Les quatre champs sortent toujours complétés de zéros à gauche, respectivement
    sur 5, 3, 2 et 4 caractères — quelle que soit la forme de l'entrée.

    :param ref: une référence cadastrale, ou une colonne de références
    :param invalide: ``"erreur"`` lève :class:`ReferenceCadastraleInvalide` sur une
        référence non décomposable ; ``"manquant"`` la remplace par des valeurs
        manquantes. Une entrée absente reste absente dans les deux cas : c'est une
        donnée qui manque, pas une donnée fausse.
    :return: un quadruplet de chaînes pour une chaîne en entrée, un ``DataFrame``
        aux colonnes ``insee``, ``com_abs``, ``section``, ``numero`` pour une
        ``Series`` — index conservé.
    :raises ReferenceCadastraleInvalide: référence non décomposable, si ``invalide="erreur"``
    :raises TypeError: entrée qui n'est ni une chaîne ni une ``Series`` de chaînes
    :raises ValueError: valeur inconnue pour ``invalide``
    """
    if invalide not in _OPTIONS_INVALIDE:
        attendu = " ou ".join(map(repr, _OPTIONS_INVALIDE))
        raise ValueError(f"invalide={invalide!r} est inconnu. Attendu : {attendu}.")

    if isinstance(ref, str):
        return _parts_depuis_texte(ref, invalide)

    if isinstance(ref, pd.Series):
        return _parts_depuis_colonne(ref, invalide)

    raise TypeError(f"to_parts attend une chaîne ou une pandas.Series, reçu {type(ref).__name__}.")


def _parts_depuis_texte(ref: str, invalide: SurInvalide) -> tuple[str, str, str, str]:
    """Décompose une référence unique."""
    motif = _ALSACE_MOSELLE_COMPILE if est_alsace_moselle(ref) else _GENERAL_COMPILE
    correspondance = motif.match(ref)

    if correspondance is None:
        if invalide == "manquant":
            return (pd.NA,) * 4
        raise ReferenceCadastraleInvalide(
            f"Référence cadastrale invalide : {ref!r}. Attendu : {FORMAT_ATTENDU}."
        )

    groupes = correspondance.groupdict()
    parts = tuple((groupes[champ] or "").zfill(LARGEURS[champ]) for champ in CHAMPS)

    # Contrat interne : le motif borne chaque groupe, le complément fixe la largeur.
    assert all(len(part) == LARGEURS[champ] for part, champ in zip(parts, CHAMPS, strict=True)), (
        parts
    )
    return parts


def _parts_depuis_colonne(refs: pd.Series, invalide: SurInvalide) -> pd.DataFrame:
    """Décompose une colonne entière, sans boucle Python."""
    _refuser_colonne_non_textuelle(refs)

    valeurs = pa.Array.from_pandas(refs, type=pa.string())
    colonnes = decomposer(valeurs)
    invalides = positions_invalides(valeurs, colonnes)

    if invalide == "erreur" and pc.any(invalides).as_py():
        _signaler_colonne_invalide(refs, invalides)

    # Pas de postcondition par ligne : la largeur est garantie par construction —
    # le motif borne chaque groupe et le complément de zéros fixe la largeur — et
    # la vérifier coûterait un parcours de plus sur le chemin chaud.
    table = pa.table({champ: colonnes[champ] for champ in CHAMPS})
    parts = table.to_pandas(types_mapper=pd.ArrowDtype)
    parts.index = refs.index
    return parts


def _refuser_colonne_non_textuelle(refs: pd.Series) -> None:
    """Rejette une colonne qui n'est pas faite de chaînes, avec la raison."""
    if refs.dtype == object or pd.api.types.is_string_dtype(refs.dtype):
        return

    raise TypeError(
        f"to_parts attend une colonne de chaînes, reçu une colonne de type {refs.dtype}. "
        "Une référence cadastrale stockée en numérique a perdu ses zéros de tête et "
        "n'est plus décomposable : convertissez la colonne à la lecture du fichier."
    )


def _signaler_colonne_invalide(refs: pd.Series, invalides: pa.Array) -> None:
    """Lève une erreur nommant le nombre de références fautives et quelques exemples."""
    masque = pd.Series(invalides.to_numpy(zero_copy_only=False), index=refs.index)
    fautives = refs[masque]
    exemples = fautives.head(_NOMBRE_EXEMPLES)

    raise ReferenceCadastraleInvalide(
        f"{len(fautives)} référence(s) cadastrale(s) invalide(s) sur {len(refs)}. "
        f"Attendu : {FORMAT_ATTENDU}. "
        f"Reçu, aux positions {list(exemples.index)} : {list(exemples)}. "
        "Passez invalide='manquant' pour les remplacer par des valeurs manquantes."
    )
