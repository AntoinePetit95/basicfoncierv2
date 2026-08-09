"""Décomposition d'une colonne entière de références cadastrales, au niveau Arrow.

La décomposition se fait en deux temps, et c'est là que se joue la vitesse :

1. **Normalisation** — chaque référence est ramenée à sa forme idu canonique : quatorze
   caractères, les quatre champs à leur largeur pleine. Une référence déjà canonique —
   la quasi-totalité des lignes d'un fichier foncier — ne coûte qu'un test de forme.
2. **Découpe** — les quatre champs se lisent alors à positions fixes.

L'extraction par expression régulière, de loin l'opération la plus chère, ne porte donc
que sur les références à normaliser : formes courtes, régime Alsace-Moselle, et
références illisibles.

Tout est exprimé en noyaux PyArrow appliqués à la colonne complète, sans aucune boucle
Python. Les valeurs manquantes traversent le module sans traitement particulier : un
noyau Arrow propage les nuls. Une référence qui ne correspond à aucun motif ressort
nulle elle aussi ; c'est à l'appelant de décider si cela vaut erreur — voir
:func:`positions_invalides`.
"""

from __future__ import annotations

import pyarrow as pa
import pyarrow.compute as pc

from .motifs import (
    BORNES,
    CHAMPS,
    DEPARTEMENTS_ALSACE_MOSELLE,
    LARGEURS,
    MOTIF_ALSACE_MOSELLE,
    MOTIF_GENERAL,
    MOTIF_IDU_GENERAL,
)

_PREFIXES_ALSACE_MOSELLE = pa.array(DEPARTEMENTS_ALSACE_MOSELLE, type=pa.string())

Colonnes = dict[str, pa.ChunkedArray | pa.Array]


def _masque_alsace_moselle(refs: pa.Array) -> pa.Array:
    """Vrai là où le département est 57, 67 ou 68."""
    departements = pc.utf8_slice_codeunits(refs, 0, 2)
    return pc.is_in(departements, value_set=_PREFIXES_ALSACE_MOSELLE)


def _deja_canoniques(refs: pa.Array) -> pa.Array:
    """Vrai là où la référence est déjà sous forme idu et peut être découpée telle quelle.

    Le motif impose à lui seul la longueur ; le régime Alsace-Moselle en est écarté,
    ses références étant reconnues par un autre motif.
    """
    forme_idu = pc.match_substring_regex(refs, pattern=MOTIF_IDU_GENERAL)
    hors_alsace_moselle = pc.invert(_masque_alsace_moselle(refs))
    return pc.fill_null(pc.and_(forme_idu, hors_alsace_moselle), False)


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

    Sert aussi à normaliser la commune absorbée : le motif général la rend facultative,
    et PyArrow restitue une chaîne vide quand le groupe n'a pas participé — que ce
    complément transforme en ``000``.
    """
    return {
        champ: pc.utf8_lpad(valeurs, LARGEURS[champ], padding="0")
        for champ, valeurs in colonnes.items()
    }


def _recoller(colonnes: Colonnes) -> pa.Array:
    """Rassemble les quatre champs en une référence de forme idu.

    Un champ nul rend la référence nulle : une référence à moitié décomposée n'existe pas.
    """
    return pc.binary_join_element_wise(*(colonnes[champ] for champ in CHAMPS), "")


def _canoniser_par_motif(refs: pa.Array) -> pa.Array:
    """Reconstruit la forme idu des références qui ne l'ont pas déjà, par extraction."""
    par_regime = _choisir(
        _masque_alsace_moselle(refs),
        _extraire(refs, MOTIF_ALSACE_MOSELLE),
        _extraire(refs, MOTIF_GENERAL),
    )
    return _recoller(_completer_zeros(par_regime))


def normaliser(refs: pa.Array) -> pa.Array:
    """Ramène toute la colonne à la forme idu, en n'analysant que ce qui le nécessite.

    :param refs: colonne Arrow de chaînes
    :return: colonne de références sur 14 caractères, nulle là où la référence était
        absente ou illisible
    """
    a_normaliser = pc.and_(pc.is_valid(refs), pc.invert(_deja_canoniques(refs)))

    if not pc.any(a_normaliser).as_py():
        return refs

    reconstruites = _canoniser_par_motif(pc.filter(refs, a_normaliser))
    return pc.replace_with_mask(refs, a_normaliser, reconstruites)


def _decouper(canoniques: pa.Array) -> Colonnes:
    """Lit les quatre champs à leurs positions fixes dans une référence de forme idu."""
    return {
        champ: pc.utf8_slice_codeunits(canoniques, debut, fin)
        for champ, (debut, fin) in BORNES.items()
    }


def decomposer(refs: pa.Array) -> Colonnes:
    """Décompose une colonne de références en ses quatre champs, complétés de zéros.

    :param refs: colonne Arrow de chaînes
    :return: un dictionnaire ``insee``, ``com_abs``, ``section``, ``numero``
    """
    return _decouper(normaliser(refs))


def positions_invalides(refs: pa.Array, colonnes: Colonnes) -> pa.Array:
    """Vrai là où une référence était présente mais n'a correspondu à aucun motif.

    Distingue l'échec de décomposition de la valeur simplement absente en entrée :
    seul le premier est une donnée invalide.
    """
    return pc.and_(pc.is_valid(refs), pc.is_null(colonnes["insee"]))
