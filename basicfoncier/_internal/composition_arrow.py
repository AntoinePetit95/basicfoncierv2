"""Composition d'une référence cadastrale à partir de ses quatre champs, au niveau Arrow.

Deux formes de sortie, toutes deux construites depuis la forme idu :

- **idu** — les quatre champs à leur largeur pleine, quatorze caractères.
- **id court** — la même référence débarrassée de ce qui se déduit : commune absorbée
  omise quand elle vaut ``000``, zéros de tête retirés de la section et du numéro.

Le régime Alsace-Moselle n'a pas de forme courte. Ses sections étant numériques, rien
n'y sépare la section du numéro : une référence raccourcie y serait illisible, et
:func:`~basicfoncier._internal.decomposition_arrow.normaliser` la rejetterait. Elle
est donc laissée sous forme idu.
"""

from __future__ import annotations

import pyarrow as pa
import pyarrow.compute as pc

from .arrow_commun import Colonnes
from .motifs import CHAMPS, LARGEURS

COM_ABS_ABSENTE = "000"


def completer_zeros(colonnes: Colonnes) -> Colonnes:
    """Ramène chaque champ à sa largeur canonique par des zéros à gauche.

    Sert aussi à normaliser la commune absorbée : le motif général la rend facultative,
    et PyArrow restitue une chaîne vide quand le groupe n'a pas participé — que ce
    complément transforme en ``000``.
    """
    return {
        champ: pc.utf8_lpad(valeurs, LARGEURS[champ], padding="0")
        for champ, valeurs in colonnes.items()
    }


def recoller(colonnes: Colonnes) -> pa.Array:
    """Rassemble les quatre champs dans l'ordre canonique, sans séparateur.

    Un champ nul rend la référence nulle : une référence à moitié décomposée n'existe pas.
    """
    return pc.binary_join_element_wise(*(colonnes[champ] for champ in CHAMPS), "")


def en_idu(colonnes: Colonnes) -> pa.Array:
    """Assemble les quatre champs en une référence de forme idu."""
    return recoller(completer_zeros(colonnes))


def _sans_zeros_de_tete(valeurs: pa.Array) -> pa.Array:
    """Retire les zéros de tête, en gardant un chiffre si tout était à zéro."""
    rognees = pc.utf8_ltrim(valeurs, characters="0")
    return pc.if_else(pc.equal(rognees, ""), "0", rognees)


def en_id_court(colonnes: Colonnes, alsace_moselle: pa.Array) -> pa.Array:
    """Assemble les quatre champs en identifiant court.

    :param colonnes: les quatre champs, déjà à leur largeur canonique
    :param alsace_moselle: vrai là où la référence relève du régime Alsace-Moselle,
        qui n'a pas de forme courte et reste donc en forme idu
    """
    com_abs = colonnes["com_abs"]
    court = pc.binary_join_element_wise(
        colonnes["insee"],
        pc.if_else(pc.equal(com_abs, COM_ABS_ABSENTE), "", com_abs),
        _sans_zeros_de_tete(colonnes["section"]),
        _sans_zeros_de_tete(colonnes["numero"]),
        "",
    )
    return pc.if_else(alsace_moselle, recoller(colonnes), court)
