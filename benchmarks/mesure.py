"""Chronométrage entrelacé, et refus d'annoncer un écart que la mesure ne soutient pas.

Mesurer deux variantes l'une après l'autre mêle l'écart entre les implémentations à
l'écart entre deux moments : sur la machine de développement, la dérive d'une exécution
à l'autre atteint 10 %, ce qui suffit à inverser le signe d'un résultat.

Les variantes sont donc chronométrées **à tour de rôle dans une même boucle**. Cela ne
supprime pas les perturbations — relevé sur six tours, un ralentissement d'un facteur
quatre frappe les deux variantes du **même** tour — mais cela les rend communes, et donc
comparables. C'est pourquoi le rapport se calcule tour par tour et non sur les totaux :
un tour perturbé garde un rapport juste, alors qu'il fausserait toute moyenne. Et si les
rapports observés encadrent 1, c'est-à-dire si l'ordre s'inverse d'un tour à l'autre, il
n'y a rien à conclure et le banc d'essai le dit.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass

#: Nombre de tours mesurés. Trois valeurs donnent une médiane instable ; au-delà de cinq,
#: le banc d'essai devient trop long pour être lancé souvent.
REPETITIONS = 5


@dataclass(frozen=True)
class Mesure:
    """Ce qu'on retient d'une série d'observations : durées en secondes, ou rapports."""

    mediane: float
    minimum: float
    maximum: float

    @property
    def dispersion(self) -> float:
        """Étendue rapportée à la médiane : la précision de cette mesure."""
        return (self.maximum - self.minimum) / self.mediane


def resumer(valeurs: Sequence[float]) -> Mesure:
    """Résume une série d'observations.

    La médiane et non la moyenne : une seule pause du ramasse-miettes suffit à décaler
    une moyenne, jamais une médiane. Fonction séparée du chronomètre, donc éprouvable
    sans rien chronométrer.
    """
    if not valeurs:
        raise ValueError("aucune valeur à résumer : il faut au moins une observation.")
    triees = sorted(valeurs)
    milieu = len(triees) // 2
    mediane = triees[milieu] if len(triees) % 2 else (triees[milieu - 1] + triees[milieu]) / 2
    return Mesure(mediane=mediane, minimum=triees[0], maximum=triees[-1])


def mesurer_ensemble(
    operations: Mapping[str, Callable[[], object]], repetitions: int = REPETITIONS
) -> dict[str, list[float]]:
    """Chronomètre toutes les variantes à tour de rôle et renvoie les durées brutes.

    Un tour appelle **chaque** variante une fois ; on fait ``repetitions`` tours. Les
    durées sont rendues dans l'ordre des tours, sans être résumées : c'est
    l'appariement tour à tour qui permet ensuite un rapport robuste.

    Un tour de chauffe précède les tours mesurés et n'est pas compté. Sans lui, le
    premier appel paie les imports différés, les défauts de page et la croissance de
    l'allocateur, ce qui suffit à faire passer l'étendue de ±25 % à ±3 000 %.
    """
    for operation in operations.values():
        operation()

    durees: dict[str, list[float]] = {nom: [] for nom in operations}
    for _ in range(repetitions):
        for nom, operation in operations.items():
            depart = time.perf_counter()
            operation()
            durees[nom].append(time.perf_counter() - depart)
    return durees


def rapports_par_tour(reference: Sequence[float], candidate: Sequence[float]) -> list[float]:
    """Divise les deux séries tour par tour : combien de fois la candidate va plus vite.

    Apparier est ce qui rend l'entrelacement utile. Un tour où la machine ralentit de
    moitié allonge les deux durées, et leur rapport reste juste ; rapporter des totaux,
    au contraire, laisserait ce tour peser sur le résultat.
    """
    if len(reference) != len(candidate):
        raise ValueError(
            f"{len(reference)} durées de référence contre {len(candidate)} : "
            "les rapports par tour exigent des séries appariées."
        )
    apparies = zip(reference, candidate, strict=True)
    return [duree / duree_candidate for duree, duree_candidate in apparies]


def est_concluant(rapports: Mesure) -> bool:
    """Dit si les rapports observés désignent tous le même gagnant.

    Une étendue qui encadre 1 signifie que l'ordre s'est inversé d'un tour à l'autre :
    l'écart est alors plus petit que le bruit, et l'annoncer serait lire du bruit comme
    un résultat. C'est l'erreur commise le 2026-08-13, où deux exécutions séparées
    donnaient +52 % là où il n'y avait rien.
    """
    return rapports.minimum > 1.0 or rapports.maximum < 1.0
