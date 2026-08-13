"""Reconnaître la forme d'une colonne pour calculer sur ses valeurs distinctes.

Une colonne foncière porte très peu de valeurs différentes : sur 749 527 parcelles
réelles, les codes Insee n'en prennent que 1 116. Et comme les parcelles d'un lot sont
mitoyennes, ces valeurs ne sont pas seulement répétées, elles sont **contiguës** — 1 116
plages pour 749 527 lignes. Calculer sur les valeurs distinctes plutôt que sur les lignes
vaut alors un facteur dix.

Encore faut-il que la colonne s'y prête, et deux formes de répétition appellent deux
encodages différents :

- l'**encodage par plages** (``run_end_encode``, un balayage linéaire) exploite la
  contiguïté, et ne rend rien sans elle ;
- l'**encodage par dictionnaire** (``dictionary_encode``, une table de hachage) exploite
  la répétition où qu'elle se trouve, pour un coût de construction plus élevé ;
- sur une colonne de valeurs presque toutes différentes — les références cadastrales,
  uniques à 85 % — les deux **coûtent** au lieu de rapporter : le calcul direct reste
  le bon choix.

D'où cette sonde : lire les dix premiers milliers de lignes, y compter les valeurs
distinctes et les plages, et en déduire lequel des trois chemins emprunter. Le coût de la
sonde est de l'ordre de la milliseconde, contre plusieurs centaines pour le calcul qu'elle
oriente.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import pyarrow as pa
import pyarrow.compute as pc

PLAGES = "plages"
DICTIONNAIRE = "dictionnaire"
DIRECT = "direct"
Strategie = Literal["plages", "dictionnaire", "direct"]

#: Nombre de lignes lues par la sonde. Dix mille suffisent à séparer les quatre régimes
#: mesurés sur données réelles, et se lisent en une milliseconde environ.
TAILLE_SONDE = 10_000

#: Au-dessous de cette part de plages, la colonne est assez contiguë pour l'encodage par
#: plages. Mesuré : une colonne de codes Insee dans l'ordre du fichier sonde à 0,001, la
#: même mélangée à 0,997, et les deux autres régimes au-dessus de 0,6. Aucune colonne
#: réelle ne s'est présentée entre les deux ; le seuil est donc large, faute de savoir où
#: se trouve exactement la bascule.
PART_DE_PLAGES_MAXIMALE = 0.25

#: Au-dessous de cette part de valeurs distinctes, l'encodage par dictionnaire rapporte.
#: Mesuré aux deux bords : x6,2 sur des contenances qui sondent à 0,29, et **x0,41** sur
#: des références cadastrales qui sondent à 0,85. Entre les deux, le seuil est un choix
#: et non une mesure — voir docs/CHANTIERS.md.
PART_DE_VALEURS_DISTINCTES_MAXIMALE = 0.50


@dataclass(frozen=True)
class Repetitions:
    """Ce qu'un échantillon dit de la répétition d'une colonne."""

    lignes: int
    distinctes: int
    plages: int

    @property
    def part_de_valeurs_distinctes(self) -> float:
        """Part des lignes qui portent une valeur qu'on n'a pas déjà vue."""
        return self.distinctes / self.lignes

    @property
    def part_de_plages(self) -> float:
        """Part des lignes qui ouvrent une nouvelle plage de valeurs identiques."""
        return self.plages / self.lignes


def sonder(colonne: pa.Array, taille: int = TAILLE_SONDE) -> Repetitions:
    """Compte les valeurs distinctes et les plages sur les premières lignes.

    Les **premières** lignes, et non un tirage au hasard : c'est la contiguïté qu'on
    cherche, et un tirage la détruirait précisément là où elle existe.
    """
    if taille < 1:
        raise ValueError(f"taille={taille} : la sonde doit lire au moins une ligne.")

    echantillon = colonne.slice(0, taille)
    if not len(echantillon):
        return Repetitions(lignes=0, distinctes=0, plages=0)

    return Repetitions(
        lignes=len(echantillon),
        distinctes=pc.count_distinct(echantillon, mode="all").as_py(),
        plages=_compter_les_plages(echantillon),
    )


def _compter_les_plages(echantillon: pa.Array) -> int:
    """Compte les suites de valeurs identiques consécutives.

    ``run_end_encode`` rend un ``ChunkedArray`` quand son entrée en est un, et les
    morceaux y sont encodés séparément : la somme de leurs plages majore le vrai compte
    d'au plus un par morceau. C'est sans effet sur la décision — la sonde compare des
    ordres de grandeur, pas des unités — et cela évite de recoller une colonne entière
    pour la seule sonde.
    """
    encode = pc.run_end_encode(echantillon)
    if isinstance(encode, pa.ChunkedArray):
        return sum(len(morceau.run_ends) for morceau in encode.chunks)
    return len(encode.run_ends)


def choisir(repetitions: Repetitions) -> Strategie:
    """Dit lequel des trois chemins de calcul une colonne doit emprunter.

    Les plages d'abord : quand la colonne est contiguë, elles sont le meilleur des trois,
    et leur coût de construction est le plus faible. Fonction séparée de la sonde, donc
    éprouvable sans fabriquer de colonne.
    """
    if repetitions.lignes == 0:
        return DIRECT
    if repetitions.part_de_plages <= PART_DE_PLAGES_MAXIMALE:
        return PLAGES
    if repetitions.part_de_valeurs_distinctes <= PART_DE_VALEURS_DISTINCTES_MAXIMALE:
        return DICTIONNAIRE
    return DIRECT
