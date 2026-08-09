"""basicfoncierv2 — références cadastrales et superficies foncières, vectorisées.

Successeur de ``basicfoncier``, qui reste publié et fonctionnel.
Voir ``docs/MIGRATION.md``.
"""

from . import ref_cadastrale, superficie
from .erreurs import ReferenceCadastraleInvalide, SuperficieInvalide

__all__ = [
    "ReferenceCadastraleInvalide",
    "SuperficieInvalide",
    "ref_cadastrale",
    "superficie",
]
