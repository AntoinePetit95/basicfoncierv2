"""basicfoncierv2 — références cadastrales et superficies foncières, vectorisées.

Successeur de ``basicfoncier``, qui reste publié et fonctionnel.
Voir ``docs/MIGRATION.md``.
"""

from . import ref_cadastrale
from .erreurs import ReferenceCadastraleInvalide

__all__ = ["ReferenceCadastraleInvalide", "ref_cadastrale"]
