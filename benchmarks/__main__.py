"""Compare le débit de la décomposition v2 à celui de basicfoncier v1.

Usage : ``python -m benchmarks [--lignes N] [--v1 CHEMIN]``

Le v1 n'est pas une dépendance : il est importé depuis son dépôt voisin, en lecture
seule, et la mesure se contente du v2 s'il est introuvable.
"""

from __future__ import annotations

import argparse
import string
import sys
import time
from collections.abc import Callable
from pathlib import Path

import numpy as np
import pandas as pd

from basicfoncierv2.ref_cadastrale import to_parts

CHEMIN_V1_PAR_DEFAUT = Path(__file__).resolve().parents[2] / "basicfoncier"
LIGNES_PAR_DEFAUT = 1_000_000
REPETITIONS = 3
DEPARTEMENTS_ALSACE_MOSELLE = ("57", "67", "68")


def generer_references(nombre: int, graine: int = 20260809) -> pd.Series:
    """Fabrique une colonne de références cadastrales valides, dans les deux régimes.

    Les départements d'Alsace-Moselle reçoivent une section numérique, les autres une
    section alphabétique : mesurer sur des références que la bibliothèque rejetterait
    ne mesurerait rien.

    :param nombre: nombre de références à produire
    :param graine: graine du générateur, pour que la mesure soit reproductible
    :return: colonne de chaînes au format idu
    """
    if nombre <= 0:
        raise ValueError(f"nombre={nombre} : il faut au moins une référence à décomposer.")

    generateur = np.random.default_rng(graine)
    insee = pd.Series(generateur.integers(1_000, 95_999, nombre)).astype(str).str.zfill(5)
    numeros = pd.Series(generateur.integers(1, 9_999, nombre)).astype(str).str.zfill(4)
    sections_alphabetiques = pd.Series(generateur.choice(list(string.ascii_uppercase), nombre))
    sections_numeriques = pd.Series(generateur.integers(1, 99, nombre)).astype(str).str.zfill(2)

    general = insee + "0000" + sections_alphabetiques + numeros
    alsace_moselle = insee + "000" + sections_numeriques + numeros
    return general.where(~insee.str[:2].isin(DEPARTEMENTS_ALSACE_MOSELLE), alsace_moselle)


def mesurer(operation: Callable[[], object], repetitions: int = REPETITIONS) -> float:
    """Renvoie la meilleure durée observée, en secondes.

    Le minimum plutôt que la moyenne : il approche le coût réel du calcul, là où la
    moyenne mesure surtout le bruit de la machine.
    """
    durees = []
    for _ in range(repetitions):
        depart = time.perf_counter()
        operation()
        durees.append(time.perf_counter() - depart)
    return min(durees)


def charger_v1(chemin: Path) -> Callable[[pd.Series], object] | None:
    """Importe la décomposition de basicfoncier v1, ou renvoie None si indisponible."""
    if not (chemin / "basicfoncier").is_dir():
        return None

    sys.path.insert(0, str(chemin))
    try:
        from basicfoncier.vectorized_functions.for_pandas.functions import ref_parcelle_to_parts
    except ImportError:
        return None
    return ref_parcelle_to_parts


def rapporter(nom: str, lignes: int, duree: float) -> float:
    """Affiche une ligne de résultat et renvoie le débit en lignes par seconde."""
    debit = lignes / duree
    print(f"  {nom:<28} {duree:8.3f} s   {debit:14,.0f} lignes/s".replace(",", " "))
    return debit


def executer(lignes: int, chemin_v1: Path) -> None:
    """Mesure le v2, puis le v1 s'il est disponible, et affiche le rapport."""
    print(f"Décomposition de {lignes:,} références".replace(",", " "))
    refs = generer_references(lignes)

    print("\nDébit mesuré (meilleur de 3) :")
    debit_v2 = rapporter("basicfoncierv2 (Arrow)", lignes, mesurer(lambda: to_parts(refs)))

    decomposer_v1 = charger_v1(chemin_v1)
    if decomposer_v1 is None:
        print(f"\nbasicfoncier v1 introuvable dans {chemin_v1} : comparaison ignorée.")
        return

    valeurs = refs.to_numpy(dtype=object)
    debit_v1 = rapporter(
        "basicfoncier v1 (np.vectorize)", lignes, mesurer(lambda: decomposer_v1(valeurs))
    )
    print(f"\nRapport v2 / v1 : x{debit_v2 / debit_v1:.1f}")


def analyser_arguments() -> argparse.Namespace:
    analyseur = argparse.ArgumentParser(description=__doc__)
    analyseur.add_argument("--lignes", type=int, default=LIGNES_PAR_DEFAUT)
    analyseur.add_argument("--v1", type=Path, default=CHEMIN_V1_PAR_DEFAUT)
    return analyseur.parse_args()


if __name__ == "__main__":
    arguments = analyser_arguments()
    executer(arguments.lignes, arguments.v1)
