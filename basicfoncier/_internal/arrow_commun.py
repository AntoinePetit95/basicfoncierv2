"""Primitives Arrow partagées par la décomposition et la composition."""

from __future__ import annotations

import pyarrow as pa
import pyarrow.compute as pc

from .motifs import DEPARTEMENTS_ALSACE_MOSELLE

_PREFIXES_ALSACE_MOSELLE = pa.array(DEPARTEMENTS_ALSACE_MOSELLE, type=pa.string())

#: Les quatre champs d'une référence, chacun sous forme de colonne Arrow.
Colonnes = dict[str, pa.ChunkedArray | pa.Array]


def masque_alsace_moselle(refs: pa.Array) -> pa.Array:
    """Vrai là où le département est 57, 67 ou 68."""
    departements = pc.utf8_slice_codeunits(refs, 0, 2)
    return pc.is_in(departements, value_set=_PREFIXES_ALSACE_MOSELLE)
