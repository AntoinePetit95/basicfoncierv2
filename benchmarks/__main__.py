"""Compare le débit de basicfoncierv2 à celui de basicfoncier v1.

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
from types import ModuleType

import numpy as np
import pandas as pd

from basicfoncierv2.ref_cadastrale import to_idu, to_parts, to_short_id
from basicfoncierv2.superficie import from_ha_a_ca, to_ha_a_ca, to_hectares

CHEMIN_V1_PAR_DEFAUT = Path(__file__).resolve().parents[2] / "basicfoncier"
LIGNES_PAR_DEFAUT = 1_000_000
REPETITIONS = 3
DEPARTEMENTS_ALSACE_MOSELLE = ("57", "67", "68")
METRES_CARRES_MAXIMUM = 2_000_000


# --------------------------------------------------------------------------------------
# Jeux de mesure
# --------------------------------------------------------------------------------------


def generer_references(nombre: int, graine: int = 20260809) -> pd.Series:
    """Fabrique une colonne de références cadastrales valides, dans les deux régimes.

    Les départements d'Alsace-Moselle reçoivent une section numérique, les autres une
    section alphabétique : mesurer sur des références que la bibliothèque rejetterait
    ne mesurerait rien.
    """
    _refuser_nombre_nul(nombre)

    generateur = np.random.default_rng(graine)
    insee = pd.Series(generateur.integers(1_000, 95_999, nombre)).astype(str).str.zfill(5)
    numeros = pd.Series(generateur.integers(1, 9_999, nombre)).astype(str).str.zfill(4)
    sections_alphabetiques = pd.Series(generateur.choice(list(string.ascii_uppercase), nombre))
    sections_numeriques = pd.Series(generateur.integers(1, 99, nombre)).astype(str).str.zfill(2)

    general = insee + "0000" + sections_alphabetiques + numeros
    alsace_moselle = insee + "000" + sections_numeriques + numeros
    return general.where(~insee.str[:2].isin(DEPARTEMENTS_ALSACE_MOSELLE), alsace_moselle)


def generer_superficies(nombre: int, graine: int = 20260809) -> pd.Series:
    """Fabrique une colonne de superficies en mètres carrés."""
    _refuser_nombre_nul(nombre)

    generateur = np.random.default_rng(graine)
    return pd.Series(generateur.integers(0, METRES_CARRES_MAXIMUM, nombre))


def _refuser_nombre_nul(nombre: int) -> None:
    if nombre <= 0:
        raise ValueError(f"nombre={nombre} : il faut au moins une valeur à mesurer.")


# --------------------------------------------------------------------------------------
# Mesure et présentation
# --------------------------------------------------------------------------------------


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


def rapporter(nom: str, lignes: int, duree: float) -> float:
    """Affiche une ligne de résultat et renvoie le débit en lignes par seconde."""
    debit = lignes / duree
    print(f"  {nom:<34} {duree:8.3f} s   {debit:14,.0f} lignes/s".replace(",", " "))
    return debit


def comparer(
    intitule: str,
    lignes: int,
    operation_v2: Callable[[], object],
    operation_v1: Callable[[], object] | None,
) -> None:
    """Mesure une opération du v2, puis son équivalent v1 s'il existe."""
    debit_v2 = rapporter(f"v2  {intitule}", lignes, mesurer(operation_v2))
    if operation_v1 is None:
        return
    debit_v1 = rapporter(f"v1  {intitule}", lignes, mesurer(operation_v1))
    print(f"      rapport v2 / v1 : x{debit_v2 / debit_v1:.1f}\n")


# --------------------------------------------------------------------------------------
# Chargement du v1
# --------------------------------------------------------------------------------------


def charger_v1(chemin: Path) -> ModuleType | None:
    """Importe les fonctions vectorisées de basicfoncier v1, ou None si indisponible."""
    if not (chemin / "basicfoncier").is_dir():
        return None

    sys.path.insert(0, str(chemin))
    try:
        from basicfoncier.vectorized_functions.for_pandas import functions
    except ImportError:
        return None
    return functions


# --------------------------------------------------------------------------------------
# Exécution
# --------------------------------------------------------------------------------------


def mesurer_references(lignes: int, v1: ModuleType | None) -> None:
    """Compare les conversions de référence cadastrale."""
    refs = generer_references(lignes)
    brutes = refs.to_numpy(dtype=object)

    print("Références cadastrales")
    comparer(
        "décomposition",
        lignes,
        lambda: to_parts(refs),
        None if v1 is None else lambda: v1.ref_parcelle_to_parts(brutes),
    )
    rapporter("v2  forme idu", lignes, mesurer(lambda: to_idu(refs)))
    rapporter("v2  identifiant court", lignes, mesurer(lambda: to_short_id(refs)))
    print(
        "      les équivalents v1 renvoient une valeur fausse ou lèvent une exception\n"
        "      (docs/BUGS.md) : les comparer n'aurait pas de sens.\n"
    )


def mesurer_superficies(lignes: int, v1: ModuleType | None) -> None:
    """Compare les conversions de superficie."""
    metres_carres = generer_superficies(lignes)
    brutes = metres_carres.to_numpy(dtype=object)
    ecrites = to_ha_a_ca(metres_carres)
    ecrites_brutes = ecrites.to_numpy(dtype=object)

    print("Superficies")
    comparer(
        "écriture ha a ca",
        lignes,
        lambda: to_ha_a_ca(metres_carres),
        None if v1 is None else lambda: v1.superficie_ha_a_ca(brutes),
    )
    comparer(
        "lecture ha a ca",
        lignes,
        lambda: from_ha_a_ca(ecrites),
        None if v1 is None else lambda: v1.superficie_from_str(ecrites_brutes),
    )
    comparer(
        "hectares",
        lignes,
        lambda: to_hectares(metres_carres),
        None if v1 is None else lambda: v1.superficie_ha(brutes),
    )


def executer(lignes: int, chemin_v1: Path) -> None:
    """Lance toutes les mesures et affiche le rapport."""
    print(f"{lignes:,} lignes, meilleur de {REPETITIONS}\n".replace(",", " "))

    v1 = charger_v1(chemin_v1)
    if v1 is None:
        print(f"basicfoncier v1 introuvable dans {chemin_v1} : comparaison ignorée.\n")

    mesurer_references(lignes, v1)
    mesurer_superficies(lignes, v1)


def analyser_arguments() -> argparse.Namespace:
    analyseur = argparse.ArgumentParser(description=__doc__)
    analyseur.add_argument("--lignes", type=int, default=LIGNES_PAR_DEFAUT)
    analyseur.add_argument("--v1", type=Path, default=CHEMIN_V1_PAR_DEFAUT)
    return analyseur.parse_args()


if __name__ == "__main__":
    arguments = analyser_arguments()
    executer(arguments.lignes, arguments.v1)
