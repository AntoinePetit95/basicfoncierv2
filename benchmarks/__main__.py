"""Compare le débit de ce paquet à celui de `basicfoncier` 0.1, son prédécesseur.

Usage : ``python -m benchmarks [--lignes N] [--v1 CHEMIN]``

Le v1 n'est pas une dépendance : il est importé depuis son dépôt voisin, en lecture
seule, et la mesure se contente du v2 s'il est introuvable. Les deux portant le même
nom de paquet, le v1 est chargé sous un alias — voir :func:`_importer_sous_alias`.
"""

from __future__ import annotations

import argparse
import importlib
import importlib.util
import string
import sys
import time
from collections.abc import Callable
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd

from basicfoncier.commune import to_code_commune, to_commune_et_arrondissement, to_departement
from basicfoncier.ref_cadastrale import to_idu, to_parts, to_short_id
from basicfoncier.superficie import from_ha_a_ca, to_ha_a_ca, to_hectares

CHEMIN_V1_PAR_DEFAUT = Path(__file__).resolve().parents[2] / "basicfoncier"

#: Nom sous lequel le v1 est chargé, pour ne pas entrer en collision avec ce paquet,
#: qui porte désormais le même nom.
ALIAS_V1 = "basicfoncier_v1"
LIGNES_PAR_DEFAUT = 1_000_000
REPETITIONS = 3
DEPARTEMENTS_ALSACE_MOSELLE = ("57", "67", "68")

# Distribution des contenances cadastrales, ajustée sur 837 531 parcelles réelles
# (fichiers des parcelles DGFiP, situation 2025, quatre départements). Une loi
# log-normale reproduit les trois régimes d'écriture à moins d'un demi-point :
#
#                          réel    simulé
#   >= 10 000 m² (ha)     21,4 %   21,6 %
#   < 100 m² (ca seuls)   13,2 %   13,6 %
#   médiane              1 396 m²  1 454 m²
#
# Ces valeurs comptent : une loi uniforme — ce que faisait ce générateur jusqu'au
# 2026-08-09 — donne 99,5 % de parcelles avec hectares. Elle mesurait donc à plein
# régime une branche du code que la réalité emprunte une fois sur cinq.
LOG_MOYENNE_CONTENANCE = 7.28
LOG_ECART_TYPE_CONTENANCE = 2.444

#: Part des références tirées hors de la métropole continentale, pour que la mesure
#: traverse aussi les motifs corses et ultramarins.
PART_CORSE = 0.01
PART_OUTRE_MER = 0.02


# --------------------------------------------------------------------------------------
# Jeux de mesure
# --------------------------------------------------------------------------------------


def _codes_insee(generateur: np.random.Generator, nombre: int) -> pd.Series:
    """Tire des codes Insee couvrant métropole, Corse et outre-mer.

    Les trois territoires empruntent des branches distinctes des motifs : n'en mesurer
    qu'une seule reviendrait à ignorer les deux autres.
    """
    metropole = pd.Series(generateur.integers(1_000, 95_999, nombre)).astype(str).str.zfill(5)

    lettre = pd.Series(generateur.choice(["A", "B"], nombre))
    commune = pd.Series(generateur.integers(1, 999, nombre)).astype(str).str.zfill(3)
    corse = "2" + lettre + commune

    departement = pd.Series(generateur.choice(["971", "972", "973", "974", "976"], nombre))
    outre_mer = departement + pd.Series(generateur.integers(1, 99, nombre)).astype(str).str.zfill(2)

    tirage = pd.Series(generateur.random(nombre))
    return metropole.where(
        tirage >= PART_CORSE + PART_OUTRE_MER,
        corse.where(tirage >= PART_OUTRE_MER, outre_mer),
    )


def generer_references(nombre: int, graine: int = 20260809) -> pd.Series:
    """Fabrique une colonne de références cadastrales valides, dans les deux régimes.

    Les départements d'Alsace-Moselle reçoivent une section numérique, les autres une
    section alphabétique : mesurer sur des références que la bibliothèque rejetterait
    ne mesurerait rien. Corse et outre-mer sont représentés — voir :func:`_codes_insee`.
    """
    _refuser_nombre_nul(nombre)

    generateur = np.random.default_rng(graine)
    insee = _codes_insee(generateur, nombre)
    numeros = pd.Series(generateur.integers(1, 9_999, nombre)).astype(str).str.zfill(4)
    sections_alphabetiques = pd.Series(generateur.choice(list(string.ascii_uppercase), nombre))
    sections_numeriques = pd.Series(generateur.integers(1, 99, nombre)).astype(str).str.zfill(2)

    general = insee + "0000" + sections_alphabetiques + numeros
    alsace_moselle = insee + "000" + sections_numeriques + numeros
    return general.where(~insee.str[:2].isin(DEPARTEMENTS_ALSACE_MOSELLE), alsace_moselle)


def generer_superficies(nombre: int, graine: int = 20260809) -> pd.Series:
    """Fabrique une colonne de contenances suivant la distribution cadastrale réelle.

    Une loi log-normale ajustée sur les fichiers de la DGFiP — voir
    :data:`LOG_MOYENNE_CONTENANCE`. Les trois formes d'écriture sont ainsi mesurées dans
    les proportions où elles se présentent, ce qu'une loi uniforme ne fait pas du tout.
    """
    _refuser_nombre_nul(nombre)

    generateur = np.random.default_rng(graine)
    tirage = generateur.lognormal(LOG_MOYENNE_CONTENANCE, LOG_ECART_TYPE_CONTENANCE, nombre)
    return pd.Series(np.rint(tirage).astype("int64"))


def generer_codes_insee(nombre: int, graine: int = 20260809) -> pd.Series:
    """Fabrique une colonne de codes Insee de commune, arrondissements compris."""
    _refuser_nombre_nul(nombre)

    return _codes_insee(np.random.default_rng(graine), nombre)


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


def _importer_sous_alias(paquet: Path, alias: str) -> bool:
    """Charge un paquet depuis son chemin, sous un nom de module choisi.

    Le v1 et le v2 portent le même nom : les mettre tous deux sur ``sys.path`` ferait
    que l'un masquerait l'autre, et la comparaison mesurerait deux fois la même chose.
    Le v1 est donc chargé sous ``basicfoncier_v1``. C'est possible parce qu'il n'emploie
    que des imports relatifs, qui se résolvent contre le nom d'alias.
    """
    if alias in sys.modules:
        return True

    spec = importlib.util.spec_from_file_location(
        alias, paquet / "__init__.py", submodule_search_locations=[str(paquet)]
    )
    if spec is None or spec.loader is None:
        return False

    module = importlib.util.module_from_spec(spec)
    sys.modules[alias] = module
    spec.loader.exec_module(module)
    return True


def charger_v1(chemin: Path) -> SimpleNamespace | None:
    """Importe basicfoncier v1 depuis son dépôt voisin, ou None si indisponible.

    Les fonctions de commune n'y existent qu'en version scalaire : elles sont
    enveloppées par ``np.vectorize``, ce qu'un utilisateur du v1 doit faire lui-même.
    """
    paquet = chemin / "basicfoncier"
    if not paquet.is_dir() or not _importer_sous_alias(paquet, ALIAS_V1):
        return None

    try:
        communes_departements_regions = importlib.import_module(
            f"{ALIAS_V1}.utils.communes_departements_regions"
        )
        functions = importlib.import_module(f"{ALIAS_V1}.vectorized_functions.for_pandas.functions")
    except ImportError:
        return None

    return SimpleNamespace(
        vectorisees=functions,
        departement=np.vectorize(communes_departements_regions.code_dep_from_com_insee, otypes="O"),
        code_commune=np.vectorize(
            communes_departements_regions.code_com_from_com_insee, otypes="O"
        ),
        arrondissement=np.vectorize(
            communes_departements_regions.com_insee_com_arrdt_from_insee, otypes=["O", "O"]
        ),
    )


# --------------------------------------------------------------------------------------
# Exécution
# --------------------------------------------------------------------------------------


def mesurer_references(lignes: int, v1: SimpleNamespace | None) -> None:
    """Compare les conversions de référence cadastrale."""
    refs = generer_references(lignes)
    brutes = refs.to_numpy(dtype=object)

    print("Références cadastrales")
    comparer(
        "décomposition",
        lignes,
        lambda: to_parts(refs),
        None if v1 is None else lambda: v1.vectorisees.ref_parcelle_to_parts(brutes),
    )
    rapporter("v2  forme idu", lignes, mesurer(lambda: to_idu(refs)))
    rapporter("v2  identifiant court", lignes, mesurer(lambda: to_short_id(refs)))
    print(
        "      les équivalents v1 renvoient une valeur fausse ou lèvent une exception\n"
        "      (docs/BUGS.md) : les comparer n'aurait pas de sens.\n"
    )


def mesurer_superficies(lignes: int, v1: SimpleNamespace | None) -> None:
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
        None if v1 is None else lambda: v1.vectorisees.superficie_ha_a_ca(brutes),
    )
    comparer(
        "lecture ha a ca",
        lignes,
        lambda: from_ha_a_ca(ecrites),
        None if v1 is None else lambda: v1.vectorisees.superficie_from_str(ecrites_brutes),
    )
    comparer(
        "hectares",
        lignes,
        lambda: to_hectares(metres_carres),
        None if v1 is None else lambda: v1.vectorisees.superficie_ha(brutes),
    )


def mesurer_communes(lignes: int, v1: SimpleNamespace | None) -> None:
    """Compare les conversions de code Insee de commune."""
    codes = generer_codes_insee(lignes)
    brutes = codes.to_numpy(dtype=object)

    print("Codes Insee de commune")
    comparer(
        "département",
        lignes,
        lambda: to_departement(codes),
        None if v1 is None else lambda: v1.departement(brutes),
    )
    comparer(
        "code commune",
        lignes,
        lambda: to_code_commune(codes),
        None if v1 is None else lambda: v1.code_commune(brutes),
    )
    comparer(
        "commune et arrondissement",
        lignes,
        lambda: to_commune_et_arrondissement(codes),
        None if v1 is None else lambda: v1.arrondissement(brutes),
    )


def executer(lignes: int, chemin_v1: Path) -> None:
    """Lance toutes les mesures et affiche le rapport."""
    print(f"{lignes:,} lignes, meilleur de {REPETITIONS}\n".replace(",", " "))

    v1 = charger_v1(chemin_v1)
    if v1 is None:
        print(f"basicfoncier v1 introuvable dans {chemin_v1} : comparaison ignorée.\n")

    mesurer_references(lignes, v1)
    mesurer_superficies(lignes, v1)
    mesurer_communes(lignes, v1)


def analyser_arguments() -> argparse.Namespace:
    analyseur = argparse.ArgumentParser(description=__doc__)
    analyseur.add_argument("--lignes", type=int, default=LIGNES_PAR_DEFAUT)
    analyseur.add_argument("--v1", type=Path, default=CHEMIN_V1_PAR_DEFAUT)
    return analyseur.parse_args()


if __name__ == "__main__":
    arguments = analyser_arguments()
    executer(arguments.lignes, arguments.v1)
