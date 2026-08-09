"""basicfoncierv2 — références cadastrales et superficies foncières, vectorisées.

Successeur de ``basicfoncier``, qui reste publié et fonctionnel.
Voir ``docs/MIGRATION.md``.
"""

from . import commune, ref_cadastrale, superficie
from .erreurs import CodeInseeInvalide, ReferenceCadastraleInvalide, SuperficieInvalide

__all__ = [
    "CodeInseeInvalide",
    "ReferenceCadastraleInvalide",
    "SuperficieInvalide",
    "commune",
    "ref_cadastrale",
    "superficie",
]
