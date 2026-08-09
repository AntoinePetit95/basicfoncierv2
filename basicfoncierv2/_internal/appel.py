"""Contrôles d'appel et conversions communs aux modules publics.

Ces règles valent pour toute la bibliothèque : une même option `invalide`, une même
façon de refuser une colonne du mauvais type, une même conversion Arrow vers pandas.
Les regrouper ici évite qu'elles divergent d'un module à l'autre.
"""

from __future__ import annotations

from typing import Literal

import pandas as pd
import pyarrow as pa

SurInvalide = Literal["erreur", "manquant"]

OPTIONS_INVALIDE = ("erreur", "manquant")

#: Nombre de valeurs fautives citées dans un message d'erreur portant sur une colonne.
NOMBRE_EXEMPLES = 5


def valider_option_invalide(invalide: str) -> None:
    """Rejette une valeur inconnue pour l'option ``invalide``."""
    if invalide not in OPTIONS_INVALIDE:
        attendu = " ou ".join(map(repr, OPTIONS_INVALIDE))
        raise ValueError(f"invalide={invalide!r} est inconnu. Attendu : {attendu}.")


def erreur_de_type(valeur: object, attendu: str) -> TypeError:
    """Construit l'erreur signalant une entrée d'une nature inattendue."""
    return TypeError(f"attendu {attendu}, reçu {type(valeur).__name__}.")


def refuser_colonne_non_textuelle(valeurs: pd.Series, designation: str) -> None:
    """Rejette une colonne qui n'est pas faite de chaînes, avec la raison."""
    if valeurs.dtype == object or pd.api.types.is_string_dtype(valeurs.dtype):
        return

    raise TypeError(
        f"{designation} doit contenir des chaînes, reçu une colonne de type {valeurs.dtype}. "
        "Une référence cadastrale stockée en numérique a perdu ses zéros de tête et "
        "n'est plus décomposable : convertissez la colonne à la lecture du fichier."
    )


def refuser_colonne_non_numerique(valeurs: pd.Series, designation: str) -> None:
    """Rejette une colonne qui ne contient pas de nombres, avec la raison."""
    if pd.api.types.is_numeric_dtype(valeurs.dtype):
        return

    raise TypeError(
        f"{designation} doit contenir des nombres, reçu une colonne de type {valeurs.dtype}. "
        "Une superficie se mesure : convertissez la colonne avec pandas.to_numeric."
    )


def en_serie(valeurs: pa.Array, index: pd.Index) -> pd.Series:
    """Enveloppe une colonne Arrow dans une ``Series`` pandas, index rétabli."""
    serie = pa.table({"valeur": valeurs}).to_pandas(types_mapper=pd.ArrowDtype)["valeur"]
    serie.index = index
    serie.name = None
    return serie


def exemples_fautifs(valeurs: pd.Series, invalides: pa.Array) -> pd.Series:
    """Extrait quelques valeurs fautives, avec leur position, pour un message d'erreur."""
    masque = pd.Series(invalides.to_numpy(zero_copy_only=False), index=valeurs.index)
    return valeurs[masque]
