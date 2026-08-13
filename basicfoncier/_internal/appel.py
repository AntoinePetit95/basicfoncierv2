"""Contrôles d'appel et conversions communs aux modules publics.

Ces règles valent pour toute la bibliothèque : une même option `invalide`, une même
façon de refuser une colonne du mauvais type, une même conversion Arrow vers pandas.
Les regrouper ici évite qu'elles divergent d'un module à l'autre.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from typing import Literal

import pandas as pd
import pyarrow as pa

SurInvalide = Literal["erreur", "manquant"]

OPTIONS_INVALIDE = ("erreur", "manquant")

#: Nombre de valeurs fautives citées dans un message d'erreur portant sur une colonne.
NOMBRE_EXEMPLES = 5

#: Ce qu'annonce le message de refus quand l'entrée n'est ni une valeur seule ni une colonne.
TEXTE_OU_COLONNE = "une chaîne ou une pandas.Series"
NOMBRE_OU_COLONNE = "un nombre ou une pandas.Series"


def valider_option_invalide(invalide: str) -> None:
    """Rejette une valeur inconnue pour l'option ``invalide``."""
    if invalide not in OPTIONS_INVALIDE:
        attendu = " ou ".join(map(repr, OPTIONS_INVALIDE))
        raise ValueError(f"invalide={invalide!r} est inconnu. Attendu : {attendu}.")


def erreur_de_type(valeur: object, attendu: str) -> TypeError:
    """Construit l'erreur signalant une entrée d'une nature inattendue."""
    return TypeError(f"attendu {attendu}, reçu {type(valeur).__name__}.")


def _est_texte(valeur: object) -> bool:
    return isinstance(valeur, str)


def est_scalaire(
    valeur: object,
    attendu: str = TEXTE_OU_COLONNE,
    admis: Callable[[object], bool] = _est_texte,
) -> bool:
    """Dit si l'appel porte sur une valeur seule plutôt que sur une colonne.

    Chaque fonction publique accepte les deux et rend le même genre qu'elle a reçu. Le
    refus de ce qui n'est ni l'un ni l'autre est écrit **ici et nulle part ailleurs** :
    huit fonctions le réécrivaient à la main, et deux d'entre elles interrogeaient la
    colonne avant la valeur seule quand les six autres faisaient l'inverse.

    :param attendu: ce que le message de refus annonce comme entrée acceptable
    :param admis: ce qui compte comme valeur seule. Le défaut est le texte ; une
        superficie, elle, est un nombre — et pas n'importe lequel, voir l'appelant.
    """
    if isinstance(valeur, pd.Series):
        return False
    if admis(valeur):
        return True
    raise erreur_de_type(valeur, attendu)


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


def en_dataframe(
    colonnes: Mapping[str, pa.Array],
    champs: Sequence[str],
    index: pd.Index,
) -> pd.DataFrame:
    """Assemble plusieurs colonnes Arrow en un ``DataFrame``, index rétabli.

    Le pendant de :func:`en_serie` pour les fonctions qui rendent plusieurs champs.
    """
    table = pa.table({champ: colonnes[champ] for champ in champs})
    parts = table.to_pandas(types_mapper=pd.ArrowDtype)
    parts.index = index
    return parts


def exemples_fautifs(valeurs: pd.Series, invalides: pa.Array) -> pd.Series:
    """Extrait quelques valeurs fautives, avec leur position, pour un message d'erreur."""
    masque = pd.Series(invalides.to_numpy(zero_copy_only=False), index=valeurs.index)
    return valeurs[masque]


def signaler_valeurs_fautives(
    erreur: type[Exception],
    valeurs: pd.Series,
    fautives: pa.Array,
    *,
    sujet: str,
    format_attendu: str | None = None,
    tolerance_possible: bool = True,
) -> None:
    """Lève l'erreur métier nommant les valeurs fautives, leur nombre et leur position.

    Un message utile dit trois choses : **combien** de lignes sont en cause sur le total,
    **ce qui était attendu**, et **quelles valeurs** ont été reçues, à quelles positions.
    Cinq fonctions écrivaient ce même patron.

    :param sujet: ce qu'on compte, accordé au pluriel — « code(s) Insee invalide(s) »
    :param format_attendu: omis quand il n'y a pas de format à rappeler, une superficie
        négative étant fautive par son signe et non par sa forme
    :param tolerance_possible: faux quand la fonction appelante n'offre pas d'option
        ``invalide`` — conseiller de la passer enverrait alors l'appelant dans le mur
    """
    fautifs = exemples_fautifs(valeurs, fautives)
    exemples = fautifs.head(NOMBRE_EXEMPLES)
    rappel = f"Attendu : {format_attendu}. " if format_attendu is not None else ""
    conseil = (
        " Passez invalide='manquant' pour les remplacer par des valeurs manquantes."
        if tolerance_possible
        else ""
    )

    raise erreur(
        f"{len(fautifs)} {sujet} sur {len(valeurs)}. "
        f"{rappel}"
        f"Reçu, aux positions {list(exemples.index)} : {list(exemples)}.{conseil}"
    )


def sont_des_textes(parties: Mapping[str, object], exigence: str) -> bool:
    """Dit si toutes les parties sont des chaînes, et refuse qu'on les mélange.

    Les fonctions d'assemblage reçoivent plusieurs champs à la fois. Les mélanger n'a pas
    de sens : deux chaînes et deux colonnes ne s'assemblent pas.

    :param exigence: la phrase qui énonce la règle, propre à l'appelant — le nombre de
        champs et leur nom en dépendent
    """
    if all(isinstance(valeur, str) for valeur in parties.values()):
        return True
    if all(isinstance(valeur, pd.Series) for valeur in parties.values()):
        return False

    natures = ", ".join(f"{champ}={type(valeur).__name__}" for champ, valeur in parties.items())
    raise TypeError(f"{exigence} Reçu : {natures}.")


def exiger_meme_index(
    valeurs: pd.Series,
    index: pd.Index,
    *,
    designation: str,
    reference: str,
    action: str,
) -> None:
    """Refuse une colonne qui n'est pas alignée sur celle qui sert de référence.

    Sans ce contrôle, pandas alignerait silencieusement sur l'union des index et
    produirait des lignes manquantes là où l'appelant attend un résultat.
    """
    if valeurs.index.equals(index):
        return

    raise ValueError(
        f"{designation} n'est pas alignée sur {reference} : "
        f"{len(valeurs)} valeurs contre {len(index)}, index différents. "
        f"Réindexez les colonnes avant de les {action}."
    )
