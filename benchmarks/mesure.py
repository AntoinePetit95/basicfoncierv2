"""Chronométrage entrelacé, et refus d'annoncer un gain que la mesure ne soutient pas.

Mesurer deux variantes l'une après l'autre mêle l'écart entre les implémentations à la
dérive de la machine entre deux moments : sur la machine de développement, cette dérive
dépasse 10 %, ce qui suffit à inverser le signe d'un résultat.

Les variantes sont donc chronométrées **à tour de rôle dans une même boucle**, et leur
rapport est calculé tour par tour. L'appariement ne supprime pas le bruit — relevé sur
six tours réels, un à-coup peut ralentir une variante 2,5 fois et l'autre seulement 1,2
fois — mais il en retire la part commune, et c'est beaucoup : sur ces mêmes six tours,
l'étendue passe de 133 % et 251 % sur les durées à 78 % sur leur rapport.

Ce qui reste est traité pour ce qu'il est : un échantillon. :func:`encadrer` en tire un
intervalle à 95 %, et le gain n'est annoncé que si cet intervalle exclut 1. Un intervalle
resserre quand on ajoute des tours : augmenter :data:`REPETITIONS` augmente donc bien ce
que le banc d'essai sait détecter, ce qui n'allait pas de soi — un critère fondé sur
l'étendue observée fait exactement l'inverse.
"""

from __future__ import annotations

import math
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass

#: Nombre de tours mesurés par défaut. Cinq tours reconnaissent sûrement un gain franc —
#: 96 % du temps sur un x2 avec 30 % de bruit — et gardent le banc d'essai assez court
#: pour être lancé souvent. Ils ne suffisent **pas** aux écarts de quelques pour-cent :
#: avec le bruit de cette machine, un gain réel de 5 % n'est reconnu qu'une fois sur six.
#: C'est à quoi sert ``--tours`` ; le réglage est sans piège, l'augmenter ne peut que
#: resserrer les intervalles.
REPETITIONS = 5

#: Quantile de Student à 95 % bilatéral, par degré de liberté, soit un tour de moins que
#: le nombre de tours mesurés. Table close et non calculée, faute
#: de scipy : le banc d'essai ne va pas s'offrir une dépendance pour vingt nombres.
_STUDENT_95 = {
    1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571,
    6: 2.447, 7: 2.365, 8: 2.306, 9: 2.262, 10: 2.228,
    11: 2.201, 12: 2.179, 13: 2.160, 14: 2.145, 15: 2.131,
    16: 2.120, 17: 2.110, 18: 2.101, 19: 2.093, 20: 2.086,
}  # fmt: skip

#: Au-delà de la table, on garde la valeur de vingt degrés de liberté. Elle est plus large
#: que la vraie, qui décroît vers 1,96 : l'intervalle est donc un peu trop prudent, ce qui
#: est le bon sens de l'erreur. Retomber sur 1,96 le rendrait trop étroit, et le taux de
#: fausse alerte passait alors de 5 % à 8 % — mesuré.
_QUANTILE_AU_DELA_DE_LA_TABLE = 2.086


@dataclass(frozen=True)
class Mesure:
    """Ce qu'on retient d'une série de durées, en secondes."""

    mediane: float
    minimum: float
    maximum: float

    @property
    def etendue(self) -> float:
        """Écart du plus lent au plus rapide, rapporté à la médiane."""
        return (self.maximum - self.minimum) / self.mediane


@dataclass(frozen=True)
class Encadrement:
    """Un gain et son intervalle à 95 %. Au-dessus de 1, la candidate va plus vite."""

    gain: float
    borne_basse: float
    borne_haute: float

    @property
    def concluant(self) -> bool:
        """Vrai si l'intervalle exclut 1, c'est-à-dire s'il désigne un gagnant."""
        return self.borne_basse > 1.0 or self.borne_haute < 1.0


def resumer(durees: Sequence[float]) -> Mesure:
    """Résume une série de durées.

    La médiane et non la moyenne : une seule pause du ramasse-miettes suffit à décaler
    une moyenne, jamais une médiane. Fonction séparée du chronomètre, donc éprouvable
    sans rien chronométrer.
    """
    _refuser_durees_inexploitables(durees)
    triees = sorted(durees)
    milieu = len(triees) // 2
    mediane = triees[milieu] if len(triees) % 2 else (triees[milieu - 1] + triees[milieu]) / 2
    return Mesure(mediane=mediane, minimum=triees[0], maximum=triees[-1])


def _refuser_durees_inexploitables(durees: Sequence[float]) -> None:
    """Une durée nulle ou négative ne vient pas d'un chronomètre : elle vient d'un bogue.

    Sans ce contrôle, elle ressort en division par zéro trois fonctions plus loin, où
    plus rien n'indique d'où elle venait.
    """
    if not durees:
        raise ValueError("aucune durée à résumer : il faut au moins un tour mesuré.")
    fautives = [duree for duree in durees if not duree > 0 or math.isinf(duree)]
    if fautives:
        raise ValueError(
            f"{len(fautives)} durée(s) sur {len(durees)} hors du domaine mesurable, "
            f"dont {fautives[0]} : une durée est un réel strictement positif et fini."
        )


def mesurer_ensemble(
    operations: Mapping[str, Callable[[], object]], repetitions: int = REPETITIONS
) -> dict[str, list[float]]:
    """Chronomètre toutes les variantes à tour de rôle et renvoie les durées brutes.

    Un tour appelle **chaque** variante une fois ; on fait ``repetitions`` tours. Les
    durées sont rendues dans l'ordre des tours, sans être résumées : c'est l'appariement
    tour à tour qui permet ensuite un encadrement robuste.

    Un tour de chauffe précède les tours mesurés et n'est pas compté. Sans lui, le
    premier appel paie les imports différés, les défauts de page et la croissance de
    l'allocateur, ce qui suffit à faire passer l'étendue de ±25 % à ±3 000 %. Chaque
    variante est donc appelée ``repetitions + 1`` fois.
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


def rapports_par_tour(
    durees_reference: Sequence[float], durees_candidate: Sequence[float]
) -> list[float]:
    """Divise les deux séries tour par tour : combien de fois la candidate va plus vite.

    Apparier est ce qui rend l'entrelacement utile. Un ralentissement subi par les deux
    variantes du même tour s'annule dans leur rapport, là où il pèserait sur toute
    comparaison de durées agrégées.
    """
    if len(durees_reference) != len(durees_candidate):
        raise ValueError(
            f"{len(durees_reference)} durées de référence contre {len(durees_candidate)} : "
            "les rapports par tour exigent des séries appariées."
        )
    _refuser_durees_inexploitables(durees_reference)
    _refuser_durees_inexploitables(durees_candidate)
    return [
        durees_reference[tour] / durees_candidate[tour] for tour in range(len(durees_reference))
    ]


def encadrer(rapports: Sequence[float]) -> Encadrement:
    """Encadre le gain vrai à 95 %, à partir des rapports observés tour par tour.

    Le calcul se fait sur les **logarithmes** des rapports : un rapport est multiplicatif,
    et x2 comme x0,5 sont deux écarts de même ampleur, ce qu'une moyenne arithmétique ne
    voit pas. Le gain publié est donc une moyenne géométrique.

    L'intervalle est celui de Student, adapté au petit nombre de tours. Sa largeur décroît
    en racine du nombre de tours, si bien qu'un écart de quelques pour-cent devient
    détectable en allongeant la mesure — voir :data:`REPETITIONS`. Un écart de 50 % qui
    n'est pas stable, lui, reste refusé quel que soit le nombre de tours.
    """
    if len(rapports) < 2:
        raise ValueError(
            f"{len(rapports)} tour(s) : il en faut au moins deux pour encadrer un gain, "
            "un tour unique ne dit rien de sa propre dispersion."
        )
    _refuser_rapports_inexploitables(rapports)

    logarithmes = [math.log(rapport) for rapport in rapports]
    moyenne = sum(logarithmes) / len(logarithmes)
    variance = sum((valeur - moyenne) ** 2 for valeur in logarithmes) / (len(logarithmes) - 1)
    marge = _quantile_95(len(rapports) - 1) * math.sqrt(variance / len(rapports))
    return Encadrement(
        gain=math.exp(moyenne),
        borne_basse=math.exp(moyenne - marge),
        borne_haute=math.exp(moyenne + marge),
    )


def _refuser_rapports_inexploitables(rapports: Sequence[float]) -> None:
    fautifs = [rapport for rapport in rapports if not rapport > 0 or math.isinf(rapport)]
    if fautifs:
        raise ValueError(
            f"{len(fautifs)} rapport(s) sur {len(rapports)} hors du domaine du logarithme, "
            f"dont {fautifs[0]} : un rapport de durées est strictement positif et fini."
        )


def _quantile_95(degres_de_liberte: int) -> float:
    return _STUDENT_95.get(degres_de_liberte, _QUANTILE_AU_DELA_DE_LA_TABLE)
