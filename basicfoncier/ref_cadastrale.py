"""Références cadastrales : décomposition, forme idu et identifiant court.

Une seule fonction publique par concept. Chacune accepte indifféremment une chaîne ou
une colonne pandas, et renvoie le résultat de même nature.

Tout passe par la forme idu : c'est elle qui sert de pivot. Une référence est d'abord
normalisée — ce qui la valide au passage — puis découpée ou raccourcie. Une référence
illisible ne franchit jamais cette première étape.
"""

from __future__ import annotations

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
    refuser_colonne_non_textuelle,
    valider_option_invalide,
)
from ._internal.arrow_commun import masque_alsace_moselle
from ._internal.composition_arrow import COM_ABS_ABSENTE, en_id_court
from ._internal.decomposition_arrow import decouper, normaliser, positions_invalides
from ._internal.motifs import (
    BORNES,
    CHAMPS,
    FORMAT_ATTENDU,
    LARGEURS,
    MOTIF_ALSACE_MOSELLE,
    MOTIF_GENERAL,
    est_alsace_moselle,
)
from .erreurs import ReferenceCadastraleInvalide

_GENERAL_COMPILE = re.compile(MOTIF_GENERAL)
_ALSACE_MOSELLE_COMPILE = re.compile(MOTIF_ALSACE_MOSELLE)

#: Ce que l'appelant peut faire d'une colonne qui n'est pas textuelle.
_CONSEIL_TEXTE = (
    "Une référence cadastrale stockée en numérique a perdu ses zéros de tête et "
    "n'est plus décomposable : convertissez la colonne à la lecture du fichier."
)


# --------------------------------------------------------------------------------------
# API publique
# --------------------------------------------------------------------------------------


def to_idu(
    ref: str | pd.Series,
    *,
    invalide: SurInvalide = "erreur",
) -> str | pd.Series:
    """Ramène une référence cadastrale à sa forme idu, sur 14 caractères.

    :param ref: une référence cadastrale sous n'importe quelle forme, ou une colonne
    :param invalide: ``"erreur"`` lève :class:`ReferenceCadastraleInvalide` sur une
        référence illisible ; ``"manquant"`` la remplace par une valeur manquante
    :return: une chaîne pour une chaîne, une ``Series`` pour une ``Series``
    """
    valider_option_invalide(invalide)

    if isinstance(ref, str):
        return _idu_depuis_texte(ref, invalide)
    if isinstance(ref, pd.Series):
        return en_serie(_canoniques_depuis_colonne(ref, invalide), ref.index)
    raise erreur_de_type(ref, "une chaîne ou une pandas.Series")


def to_short_id(
    ref: str | pd.Series,
    *,
    invalide: SurInvalide = "erreur",
) -> str | pd.Series:
    """Ramène une référence cadastrale à son identifiant court.

    L'identifiant court omet ce qui se déduit : la commune absorbée quand elle est
    absente, les zéros de tête de la section et du numéro. **En Alsace-Moselle, la
    forme idu est renvoyée telle quelle** : les sections y étant numériques, une
    référence raccourcie n'y serait plus décomposable.

    :param ref: une référence cadastrale sous n'importe quelle forme, ou une colonne
    :param invalide: voir :func:`to_idu`
    :return: une chaîne pour une chaîne, une ``Series`` pour une ``Series``
    """
    valider_option_invalide(invalide)

    if isinstance(ref, str):
        idu = _idu_depuis_texte(ref, invalide)
        return idu if pd.isna(idu) else _raccourcir_texte(idu)
    if isinstance(ref, pd.Series):
        canoniques = _canoniques_depuis_colonne(ref, invalide)
        courts = en_id_court(decouper(canoniques), masque_alsace_moselle(canoniques))
        return en_serie(courts, ref.index)
    raise erreur_de_type(ref, "une chaîne ou une pandas.Series")


def to_parts(
    ref: str | pd.Series,
    *,
    invalide: SurInvalide = "erreur",
) -> tuple[str, str, str, str] | pd.DataFrame:
    """Décompose une référence cadastrale en ``(insee, com_abs, section, numero)``.

    Les quatre champs sortent toujours complétés de zéros à gauche, respectivement
    sur 5, 3, 2 et 4 caractères — quelle que soit la forme de l'entrée.

    À Paris, Lyon et Marseille, le champ ``insee`` est celui de l'**arrondissement
    municipal**, tel qu'il figure dans la référence : ``to_parts("75107000CR0002")``
    donne ``insee="75107"``. Pour obtenir la commune, passez ce champ à
    ``commune.to_commune_et_arrondissement``, qui rend ``("75056", "107")``.

    :param ref: une référence cadastrale, ou une colonne de références
    :param invalide: voir :func:`to_idu`. Une entrée absente reste absente dans les
        deux cas : c'est une donnée qui manque, pas une donnée fausse.
    :return: un quadruplet de chaînes pour une chaîne en entrée, un ``DataFrame`` aux
        colonnes ``insee``, ``com_abs``, ``section``, ``numero`` pour une ``Series`` —
        index conservé.
    :raises ReferenceCadastraleInvalide: référence illisible, si ``invalide="erreur"``
    :raises TypeError: entrée qui n'est ni une chaîne ni une ``Series`` de chaînes
    :raises ValueError: valeur inconnue pour ``invalide``
    """
    valider_option_invalide(invalide)

    if isinstance(ref, str):
        idu = _idu_depuis_texte(ref, invalide)
        return (pd.NA,) * 4 if pd.isna(idu) else _decouper_texte(idu)
    if isinstance(ref, pd.Series):
        return _parts_depuis_colonne(ref, invalide)
    raise erreur_de_type(ref, "une chaîne ou une pandas.Series")


def idu_from_parts(
    insee: str | pd.Series,
    com_abs: str | pd.Series,
    section: str | pd.Series,
    numero: str | pd.Series,
) -> str | pd.Series:
    """Assemble une référence de forme idu à partir de ses quatre champs.

    Les champs sont complétés de zéros à gauche à leur largeur canonique. L'ordre des
    arguments est celui de :func:`to_parts` — il diffère de celui de ``basicfoncier`` v1.

    .. warning::
       **Paris, Lyon et Marseille.** Le champ insee d'une référence cadastrale y porte le
       code de l'**arrondissement municipal**, pas celui de la commune : la parcelle du
       pilier Ouest de la tour Eiffel est ``75107000CR0002``, et non ``75056...``. Rien
       dans les quatre champs reçus ne permet de deviner l'arrondissement : l'assemblage
       se contente de concaténer ce qu'on lui donne. Passer ``insee="75056"`` produit une
       référence bien formée mais qui ne désigne aucune parcelle.

       Le sens inverse sait trancher : ``commune.to_commune_et_arrondissement`` ramène
       ``75107`` à ``("75056", "107")``.

    :raises ReferenceCadastraleInvalide: les champs n'assemblent pas une référence lisible
    """
    return to_idu(_assembler(insee, com_abs, section, numero))


def short_id_from_parts(
    insee: str | pd.Series,
    com_abs: str | pd.Series,
    section: str | pd.Series,
    numero: str | pd.Series,
) -> str | pd.Series:
    """Assemble un identifiant court à partir des quatre champs.

    Mêmes règles que :func:`idu_from_parts` pour les champs — **y compris l'avertissement
    sur Paris, Lyon et Marseille** — et que :func:`to_short_id` pour la forme du résultat.

    :raises ReferenceCadastraleInvalide: les champs n'assemblent pas une référence lisible
    """
    return to_short_id(_assembler(insee, com_abs, section, numero))


# --------------------------------------------------------------------------------------
# Chemin scalaire
# --------------------------------------------------------------------------------------


def _idu_depuis_texte(ref: str, invalide: SurInvalide) -> str:
    """Normalise une référence unique vers sa forme idu."""
    motif = _ALSACE_MOSELLE_COMPILE if est_alsace_moselle(ref) else _GENERAL_COMPILE

    # ``fullmatch`` et non ``match`` : le ``$`` du module ``re`` accepte un saut de ligne
    # final, celui de RE2 non. Sans cela le chemin scalaire admettrait des références que
    # le chemin colonne rejette.
    correspondance = motif.fullmatch(ref)

    if correspondance is None:
        if invalide == "manquant":
            return pd.NA
        raise ReferenceCadastraleInvalide(
            f"Référence cadastrale invalide : {ref!r}. Attendu : {FORMAT_ATTENDU}."
        )

    groupes = correspondance.groupdict()
    idu = "".join((groupes[champ] or "").zfill(LARGEURS[champ]) for champ in CHAMPS)

    # Contrat interne : le motif borne chaque groupe, le complément fixe la largeur.
    assert len(idu) == sum(LARGEURS.values()), idu
    return idu


def _decouper_texte(idu: str) -> tuple[str, str, str, str]:
    """Lit les quatre champs à leurs positions fixes."""
    return tuple(idu[debut:fin] for debut, fin in BORNES.values())


def _raccourcir_texte(idu: str) -> str:
    """Réduit une forme idu à son identifiant court."""
    if est_alsace_moselle(idu):
        return idu

    insee, com_abs, section, numero = _decouper_texte(idu)
    return "".join(
        (
            insee,
            "" if com_abs == COM_ABS_ABSENTE else com_abs,
            section.lstrip("0") or "0",
            numero.lstrip("0") or "0",
        )
    )


# --------------------------------------------------------------------------------------
# Chemin colonne
# --------------------------------------------------------------------------------------


def _canoniques_depuis_colonne(refs: pd.Series, invalide: SurInvalide) -> pa.Array:
    """Normalise une colonne entière vers la forme idu, sans boucle Python."""
    refuser_colonne_non_textuelle(refs, "la colonne", _CONSEIL_TEXTE)

    valeurs = en_colonne_arrow(refs, pa.string())
    canoniques = normaliser(valeurs)
    invalides = positions_invalides(valeurs, canoniques)

    if invalide == "erreur" and pc.any(invalides).as_py():
        _signaler_colonne_invalide(refs, invalides)

    return canoniques


def _parts_depuis_colonne(refs: pd.Series, invalide: SurInvalide) -> pd.DataFrame:
    """Décompose une colonne entière en un tableau de quatre colonnes."""
    colonnes = decouper(_canoniques_depuis_colonne(refs, invalide))

    # Pas de postcondition par ligne : la largeur est garantie par construction — la
    # normalisation produit exactement quatorze caractères — et la vérifier coûterait
    # un parcours de plus sur le chemin chaud.
    table = pa.table({champ: colonnes[champ] for champ in CHAMPS})
    parts = table.to_pandas(types_mapper=pd.ArrowDtype)
    parts.index = refs.index
    return parts


# --------------------------------------------------------------------------------------
# Assemblage depuis les champs
# --------------------------------------------------------------------------------------


def _assembler(
    insee: str | pd.Series,
    com_abs: str | pd.Series,
    section: str | pd.Series,
    numero: str | pd.Series,
) -> str | pd.Series:
    """Concatène les quatre champs, chacun complété à sa largeur canonique."""
    parties = dict(zip(CHAMPS, (insee, com_abs, section, numero), strict=True))

    if all(isinstance(valeur, str) for valeur in parties.values()):
        return "".join(parties[champ].zfill(LARGEURS[champ]) for champ in CHAMPS)

    if all(isinstance(valeur, pd.Series) for valeur in parties.values()):
        return _assembler_colonnes(parties)

    natures = ", ".join(f"{champ}={type(valeur).__name__}" for champ, valeur in parties.items())
    raise TypeError(
        "les quatre champs doivent être tous des chaînes, ou tous des pandas.Series. "
        f"Reçu : {natures}."
    )


def _assembler_colonnes(parties: dict[str, pd.Series]) -> pd.Series:
    """Concatène quatre colonnes alignées sur le même index."""
    index = parties["insee"].index
    for champ, valeurs in parties.items():
        refuser_colonne_non_textuelle(valeurs, f"la colonne {champ}", _CONSEIL_TEXTE)
        if not valeurs.index.equals(index):
            raise ValueError(
                f"la colonne {champ} n'est pas alignée sur la colonne insee : "
                f"{len(valeurs)} valeurs contre {len(index)}, index différents. "
                "Réindexez les colonnes avant de les assembler."
            )

    completees = [
        pc.utf8_lpad(
            en_colonne_arrow(parties[champ], pa.string()),
            LARGEURS[champ],
            padding="0",
        )
        for champ in CHAMPS
    ]
    return en_serie(pc.binary_join_element_wise(*completees, ""), index)


# --------------------------------------------------------------------------------------
# Contrôles d'appel et messages
# --------------------------------------------------------------------------------------


def _signaler_colonne_invalide(refs: pd.Series, invalides: pa.Array) -> None:
    """Lève une erreur nommant le nombre de références fautives et quelques exemples."""
    fautives = exemples_fautifs(refs, invalides)
    exemples = fautives.head(NOMBRE_EXEMPLES)

    raise ReferenceCadastraleInvalide(
        f"{len(fautives)} référence(s) cadastrale(s) invalide(s) sur {len(refs)}. "
        f"Attendu : {FORMAT_ATTENDU}. "
        f"Reçu, aux positions {list(exemples.index)} : {list(exemples)}. "
        "Passez invalide='manquant' pour les remplacer par des valeurs manquantes."
    )
