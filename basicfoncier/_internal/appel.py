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


#: Natures de contenu acceptables pour une colonne d'objets censée porter du texte.
#: ``empty`` couvre la colonne entièrement absente, qui n'a rien de fautif.
NATURES_TEXTUELLES = ("string", "empty")


def refuser_colonne_non_textuelle(valeurs: pd.Series, designation: str, conseil: str) -> None:
    """Rejette une colonne qui n'est pas faite de chaînes, avec la raison.

    Le type déclaré ne suffit pas : une colonne ``object`` peut contenir des entiers,
    et Arrow les convertirait en texte sans broncher — en ayant déjà perdu les zéros de
    tête. Son contenu réel est donc inspecté, par ``infer_dtype`` pour rester bon marché.

    :param valeurs: la colonne reçue
    :param designation: ce que la colonne est censée contenir, pour le message
    :param conseil: ce que l'appelant peut faire, propre au module appelant
    """
    if not (valeurs.dtype == object or pd.api.types.is_string_dtype(valeurs.dtype)):
        raise TypeError(
            f"{designation} doit contenir des chaînes, reçu une colonne de type "
            f"{valeurs.dtype}. {conseil}"
        )

    if valeurs.dtype != object:
        return

    nature = pd.api.types.infer_dtype(valeurs, skipna=True)
    if nature not in NATURES_TEXTUELLES:
        raise TypeError(
            f"{designation} doit contenir des chaînes, reçu une colonne d'objets dont le "
            f"contenu est de nature {nature}. {conseil}"
        )


def refuser_colonne_non_numerique(valeurs: pd.Series, designation: str) -> None:
    """Rejette une colonne qui ne contient pas de nombres, avec la raison.

    Les booléens sont numériques pour pandas — ``True`` y vaut 1 — mais une colonne de
    booléens n'est jamais une colonne de superficies ; l'accepter ne rendrait service à
    personne.
    """
    numerique = pd.api.types.is_numeric_dtype(valeurs.dtype)
    if numerique and not pd.api.types.is_bool_dtype(valeurs.dtype):
        return

    raise TypeError(
        f"{designation} doit contenir des nombres, reçu une colonne de type {valeurs.dtype}. "
        "Une superficie se mesure : convertissez la colonne avec pandas.to_numeric."
    )


def en_colonne_arrow(valeurs: pd.Series, type_arrow: pa.DataType | None = None) -> pa.Array:
    """Convertit une colonne pandas en un tableau Arrow d'un seul tenant.

    Une ``Series`` adossée à Arrow — celle que rend ``read_parquet(dtype_backend='pyarrow')``
    — peut être fragmentée en plusieurs morceaux. ``pa.Array.from_pandas`` rend alors un
    ``ChunkedArray``, que plusieurs noyaux de calcul (``replace_with_mask`` notamment)
    refusent. Le recollage est fait une fois pour toutes ici, à l'entrée.

    Selon la version de PyArrow, ``combine_chunks`` rend un ``Array`` ou un
    ``ChunkedArray`` à un seul morceau : les deux formes sont ramenées à un ``Array``.
    """
    colonne = pa.Array.from_pandas(valeurs, type=type_arrow)
    if isinstance(colonne, pa.ChunkedArray):
        colonne = colonne.combine_chunks()
    if isinstance(colonne, pa.ChunkedArray):
        colonne = colonne.chunk(0) if colonne.num_chunks else pa.array([], type=colonne.type)
    return colonne


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
