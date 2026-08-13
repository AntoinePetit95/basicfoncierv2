"""Compare le débit de ce paquet à celui de `basicfoncier` 0.1, son prédécesseur.

Usage : ``python -m benchmarks [--lignes N] [--v1 CHEMIN] [--tours N]``

Le v1 n'est pas une dépendance : il est importé depuis son dépôt voisin, en lecture
seule, et la mesure se contente du v2 s'il est introuvable. Les deux portant le même
nom de paquet, le v1 est chargé sous un alias — voir :func:`_importer_sous_alias`.
"""

from __future__ import annotations

import argparse
import importlib
import importlib.util
import math
import string
import sys
from collections.abc import Callable
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd

from basicfoncier.commune import to_code_commune, to_commune_et_arrondissement, to_departement
from basicfoncier.ref_cadastrale import to_idu, to_parts, to_short_id
from basicfoncier.superficie import from_ha_a_ca, to_ha_a_ca, to_hectares
from benchmarks.mesure import (
    REPETITIONS,
    TOURS_MINIMUM,
    Encadrement,
    Mesure,
    encadrer,
    mesurer_ensemble,
    rapports_par_tour,
    resumer,
)

CHEMIN_V1_PAR_DEFAUT = Path(__file__).resolve().parents[2] / "basicfoncier"

#: Nom sous lequel le v1 est chargé, pour ne pas entrer en collision avec ce paquet,
#: qui porte désormais le même nom.
ALIAS_V1 = "basicfoncier_v1"
LIGNES_PAR_DEFAUT = 1_000_000
DEPARTEMENTS_ALSACE_MOSELLE = ("57", "67", "68")

# Distribution des contenances cadastrales, ajustée sur 837 531 parcelles réelles
# (fichiers des parcelles DGFiP, situation 2025, quatre départements).
#
# **L'ajustement porte sur les seuils d'écriture, pas sur la loi entière.** Ce qui
# détermine le coût de `formater`, c'est la répartition entre les trois formes ; c'est
# donc elle qui est contrôlée, et elle l'est à moins d'un demi-point :
#
#                          réel    simulé
#   >= 10 000 m² (ha)     21,4 %   21,5 %
#   < 100 m² (ca seuls)   13,2 %   13,7 %
#   médiane              1 396 m²  1 456 m²
#
# (colonne « simulé » relevée sur un million de tirages à la graine par défaut)
#
# La queue, elle, n'est pas ajustée : l'écart-type retenu produit quelques parcelles de
# plusieurs dizaines de km², ce que le cadastre ne connaît guère hors Guyane. Sans effet
# sur la mesure — le coût d'écriture ne dépend pas de la grandeur — mais à ne pas lire
# comme un modèle fidèle du foncier français.
#
# Ces valeurs comptent : une loi uniforme — ce que faisait ce générateur jusqu'au
# 2026-08-09 — donne 99,5 % de parcelles avec hectares. Elle mesurait donc à plein
# régime une branche du code que la réalité emprunte une fois sur cinq.
LOG_MOYENNE_CONTENANCE = 7.28
LOG_ECART_TYPE_CONTENANCE = 2.444

#: Contenance la plus faible produite. Les fichiers DGFiP n'en contiennent aucune à
#: zéro — vérifié sur 673 176 parcelles — alors que l'arrondi d'une log-normale en
#: produirait environ une pour deux mille.
CONTENANCE_MINIMALE = 1

#: Part des références tirées hors de la métropole continentale, pour que la mesure
#: traverse aussi les motifs corses et ultramarins.
PART_CORSE = 0.01
PART_OUTRE_MER = 0.02


# --------------------------------------------------------------------------------------
# Jeux de mesure
# --------------------------------------------------------------------------------------


def _codes_insee(generateur: np.random.Generator, nombre: int) -> pd.Series:
    """Tire des codes Insee couvrant métropole, Corse et outre-mer.

    Le but n'est pas le débit : mesuré, l'écart entre une colonne toute métropolitaine et
    ce mélange tient dans le bruit (1,00 à 1,07x). Il est de ne jamais fabriquer une
    donnée que la bibliothèque rejetterait — un code corse mal formé ferait échouer le
    banc d'essai plutôt qu'il ne le fausserait — et de garder les motifs corse et
    ultramarin sous la mesure, au cas où une optimisation future les traiterait à part.
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

    Le tirage est ramené à :data:`CONTENANCE_MINIMALE` : arrondie, la loi produit une
    contenance nulle environ une fois sur deux mille, cas que le cadastre ne connaît pas.
    """
    _refuser_nombre_nul(nombre)

    generateur = np.random.default_rng(graine)
    tirage = generateur.lognormal(LOG_MOYENNE_CONTENANCE, LOG_ECART_TYPE_CONTENANCE, nombre)
    arrondi = np.rint(tirage).astype("int64")
    return pd.Series(np.maximum(arrondi, CONTENANCE_MINIMALE))


def generer_codes_insee(nombre: int, graine: int = 20260809) -> pd.Series:
    """Fabrique une colonne de codes Insee de commune, Corse et outre-mer compris.

    Les codes d'arrondissement de Paris, Lyon et Marseille n'y sont représentés qu'à
    hauteur de leur poids dans un tirage uniforme, soit environ un pour deux mille : la
    conversion vers la commune réelle n'est donc pas mesurée à charge significative.
    """
    _refuser_nombre_nul(nombre)

    return _codes_insee(np.random.default_rng(graine), nombre)


def _refuser_nombre_nul(nombre: int) -> None:
    if nombre <= 0:
        raise ValueError(f"nombre={nombre} : il faut au moins une valeur à mesurer.")


# --------------------------------------------------------------------------------------
# Mesure et présentation
# --------------------------------------------------------------------------------------


def rapporter(nom: str, lignes: int, mesure: Mesure) -> None:
    """Affiche une ligne de résultat : durée médiane, débit, et étendue des tours."""
    debit = lignes / mesure.mediane
    print(
        f"  {nom:<34} {mesure.mediane:8.3f} s   {debit:14,.0f} lignes/s"
        f"   étendue {mesure.etendue:5.0%}".replace(",", " ")
    )


def conclure(encadrement: Encadrement) -> str:
    """Formule le gain du v2 sur le v1, ou dit qu'il n'y a rien à annoncer."""
    if math.isinf(encadrement.borne_haute):
        # Tous les tours ont rendu le même rapport au bit près : l'horloge n'a pas séparé
        # les variantes. Afficher « x0.00 à xinf » serait exact et illisible.
        return "gain v2 / v1 : non concluant — tous les tours donnent le même rapport"
    bornes = f"x{encadrement.borne_basse:.2f} à x{encadrement.borne_haute:.2f}"
    if not encadrement.concluant:
        return f"gain v2 / v1 : non concluant — l'intervalle {bornes} contient 1"
    return f"gain v2 / v1 : x{encadrement.gain:.2f}   ({bornes} à 95 %)"


def comparer(
    intitule: str,
    lignes: int,
    operation_v2: Callable[[], object],
    operation_v1: Callable[[], object] | None,
    tours: int = REPETITIONS,
) -> None:
    """Mesure une opération du v2 et son équivalent v1 entrelacés, puis les compare."""
    if operation_v1 is None:
        durees = mesurer_ensemble({"v2": operation_v2}, tours)
        rapporter(f"v2  {intitule}", lignes, resumer(durees["v2"]))
        return

    durees = mesurer_ensemble({"v2": operation_v2, "v1": operation_v1}, tours)
    rapporter(f"v2  {intitule}", lignes, resumer(durees["v2"]))
    rapporter(f"v1  {intitule}", lignes, resumer(durees["v1"]))
    # Le v1 est la référence, donc au numérateur : le gain se lit « le v2 va x fois plus
    # vite que le v1 ». Inverser ces deux arguments inverserait chaque gain publié — c'est
    # ce que vérifie `TestSensDuGain`.
    rapports = rapports_par_tour(durees_reference=durees["v1"], durees_candidate=durees["v2"])
    print(f"      {conclure(encadrer(rapports))}\n")


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


def mesurer_references(lignes: int, v1: SimpleNamespace | None, tours: int) -> None:
    """Compare les conversions de référence cadastrale."""
    refs = generer_references(lignes)
    brutes = refs.to_numpy(dtype=object)

    print("Références cadastrales")
    comparer(
        "décomposition",
        lignes,
        lambda: to_parts(refs),
        None if v1 is None else lambda: v1.vectorisees.ref_parcelle_to_parts(brutes),
        tours,
    )
    comparer("forme idu", lignes, lambda: to_idu(refs), None, tours)
    comparer("identifiant court", lignes, lambda: to_short_id(refs), None, tours)
    print(
        "      les équivalents v1 renvoient une valeur fausse ou lèvent une exception\n"
        "      (docs/BUGS.md) : les comparer n'aurait pas de sens.\n"
    )


def mesurer_superficies(lignes: int, v1: SimpleNamespace | None, tours: int) -> None:
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
        tours,
    )
    comparer(
        "lecture ha a ca",
        lignes,
        lambda: from_ha_a_ca(ecrites),
        None if v1 is None else lambda: v1.vectorisees.superficie_from_str(ecrites_brutes),
        tours,
    )
    comparer(
        "hectares",
        lignes,
        lambda: to_hectares(metres_carres),
        None if v1 is None else lambda: v1.vectorisees.superficie_ha(brutes),
        tours,
    )


def mesurer_communes(lignes: int, v1: SimpleNamespace | None, tours: int) -> None:
    """Compare les conversions de code Insee de commune."""
    codes = generer_codes_insee(lignes)
    brutes = codes.to_numpy(dtype=object)

    print("Codes Insee de commune")
    comparer(
        "département",
        lignes,
        lambda: to_departement(codes),
        None if v1 is None else lambda: v1.departement(brutes),
        tours,
    )
    comparer(
        "code commune",
        lignes,
        lambda: to_code_commune(codes),
        None if v1 is None else lambda: v1.code_commune(brutes),
        tours,
    )
    comparer(
        "commune et arrondissement",
        lignes,
        lambda: to_commune_et_arrondissement(codes),
        None if v1 is None else lambda: v1.arrondissement(brutes),
        tours,
    )


def _refuser_tours_insuffisants(tours: int) -> None:
    """Deux tours au minimum : un seul ne dit rien de sa propre dispersion.

    Contrôlé ici, à l'entrée, et non trois couches plus bas : sans cela le banc d'essai
    imprime son en-tête et ses premières mesures avant de s'interrompre sur une trace.
    """
    if tours < TOURS_MINIMUM:
        raise ValueError(
            f"tours={tours} : il en faut au moins {TOURS_MINIMUM} pour encadrer un gain."
        )


def executer(lignes: int, chemin_v1: Path, tours: int) -> None:
    """Lance toutes les mesures et affiche le rapport."""
    _refuser_nombre_nul(lignes)
    _refuser_tours_insuffisants(tours)
    nombre = f"{lignes:,}".replace(",", " ")
    print(f"{nombre} lignes, {tours} tours entrelacés, gain encadré à 95 %\n")

    v1 = charger_v1(chemin_v1)
    if v1 is None:
        print(f"basicfoncier v1 introuvable dans {chemin_v1} : comparaison ignorée.\n")

    mesurer_references(lignes, v1, tours)
    mesurer_superficies(lignes, v1, tours)
    mesurer_communes(lignes, v1, tours)


def analyser_arguments() -> argparse.Namespace:
    analyseur = argparse.ArgumentParser(description=__doc__)
    analyseur.add_argument("--lignes", type=int, default=LIGNES_PAR_DEFAUT)
    analyseur.add_argument("--v1", type=Path, default=CHEMIN_V1_PAR_DEFAUT)
    analyseur.add_argument("--tours", type=int, default=REPETITIONS)
    return analyseur.parse_args()


if __name__ == "__main__":
    arguments = analyser_arguments()
    executer(arguments.lignes, arguments.v1, arguments.tours)
