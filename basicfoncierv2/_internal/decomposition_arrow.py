"""Décomposition d'une colonne entière de références cadastrales, au niveau Arrow.

Tout se joue ici : chaque opération est un noyau PyArrow appliqué à la colonne
complète, sans aucune boucle Python. C'est ce qui sépare ce module de l'approche
``numpy.vectorize`` de basicfoncier v1, qui appelle une fonction Python par ligne.

Les valeurs manquantes traversent le module sans traitement particulier : un noyau
Arrow propage les nuls. Une référence qui ne correspond à aucun motif ressort nulle
elle aussi ; c'est à l'appelant de décider si cela vaut erreur — voir
:func:`positions_invalides`.
"""

from __future__ import annotations

import pyarrow as pa
import pyarrow.compute as pc

from .motifs import (
    CHAMPS,
    DEPARTEMENTS_ALSACE_MOSELLE,
    LARGEURS,
    MOTIF_ALSACE_MOSELLE,
    MOTIF_GENERAL,
)

_PREFIXES_ALSACE_MOSELLE = pa.array(DEPARTEMENTS_ALSACE_MOSELLE, type=pa.string())

Colonnes = dict[str, pa.ChunkedArray | pa.Array]


def _masque_alsace_moselle(refs: pa.Array) -> pa.Array:
    """Vrai là où le département est 57, 67 ou 68."""
    departements = pc.utf8_slice_codeunits(refs, 0, 2)
    return pc.is_in(departements, value_set=_PREFIXES_ALSACE_MOSELLE)


def _extraire(refs: pa.Array, motif: str) -> Colonnes:
    """Applique un motif à toute la colonne et éclate ses groupes nommés.

    Une référence qui ne correspond pas au motif donne un nul dans chaque champ.
    """
    correspondances = pc.extract_regex(refs, pattern=motif)
    return {champ: pc.struct_field(correspondances, champ) for champ in CHAMPS}


def _choisir(masque: pa.Array, si_vrai: Colonnes, si_faux: Colonnes) -> Colonnes:
    """Retient champ par champ la décomposition du régime désigné par le masque."""
    return {champ: pc.if_else(masque, si_vrai[champ], si_faux[champ]) for champ in CHAMPS}


def _completer_zeros(colonnes: Colonnes) -> Colonnes:
    """Ramène chaque champ à sa largeur canonique par des zéros à gauche.

    Sert aussi à normaliser la commune absorbée : le motif général la rend
    facultative, et PyArrow restitue une chaîne vide quand le groupe n'a pas
    participé — que ce complément transforme en ``000``.
    """
    return {
        champ: pc.utf8_lpad(valeurs, LARGEURS[champ], padding="0")
        for champ, valeurs in colonnes.items()
    }


def decomposer(refs: pa.Array) -> Colonnes:
    """Décompose une colonne de références en ses quatre champs, complétés de zéros.

    :param refs: colonne Arrow de chaînes
    :return: un dictionnaire ``insee``, ``com_abs``, ``section``, ``numero``
    """
    par_regime = _choisir(
        _masque_alsace_moselle(refs),
        _extraire(refs, MOTIF_ALSACE_MOSELLE),
        _extraire(refs, MOTIF_GENERAL),
    )
    return _completer_zeros(par_regime)


def positions_invalides(refs: pa.Array, colonnes: Colonnes) -> pa.Array:
    """Vrai là où une référence était présente mais n'a correspondu à aucun motif.

    Distingue l'échec de décomposition de la valeur simplement absente en entrée :
    seul le premier est une donnée invalide.
    """
    return pc.and_(pc.is_valid(refs), pc.is_null(colonnes["insee"]))
