"""Comportement attendu de la sonde de répétition.

Les quatre régimes éprouvés ici sont ceux de vraies colonnes cadastrales : les chiffres
en commentaire viennent de 749 527 parcelles DGFiP, relevés le 2026-08-13.
"""

import pyarrow as pa
import pytest

from basicfoncier._internal.repetitions import (
    DICTIONNAIRE,
    DIRECT,
    PLAGES,
    Repetitions,
    choisir,
    sonder,
)


def colonne_par_plages(valeurs: int, longueur_de_plage: int) -> pa.Array:
    """Une colonne contiguë : chaque valeur répétée `longueur_de_plage` fois de suite."""
    return pa.array([str(ligne // longueur_de_plage) for ligne in range(valeurs)])


class TestSonder:
    """Ce que la sonde relève sur les premières lignes."""

    def test_une_colonne_contigue_a_peu_de_plages(self):
        repetitions = sonder(colonne_par_plages(10_000, 500))
        assert repetitions == Repetitions(lignes=10_000, distinctes=20, plages=20)

    def test_une_colonne_toute_distincte_n_a_que_des_plages_d_une_ligne(self):
        repetitions = sonder(colonne_par_plages(1_000, 1))
        assert repetitions == Repetitions(lignes=1_000, distinctes=1_000, plages=1_000)

    def test_une_colonne_repetee_sans_contiguite_a_beaucoup_de_plages(self):
        """Deux valeurs alternées : deux valeurs distinctes, mais autant de plages."""
        repetitions = sonder(pa.array(["a", "b"] * 500))
        assert (repetitions.distinctes, repetitions.plages) == (2, 1_000)

    def test_la_sonde_ne_lit_que_les_premieres_lignes(self):
        repetitions = sonder(colonne_par_plages(50_000, 1), taille=10_000)
        assert repetitions.lignes == 10_000

    def test_une_colonne_plus_courte_que_la_sonde_est_lue_entierement(self):
        assert sonder(colonne_par_plages(300, 1), taille=10_000).lignes == 300

    def test_une_colonne_vide_ne_fait_pas_echouer_la_sonde(self):
        assert sonder(pa.array([], type=pa.string())) == Repetitions(0, 0, 0)

    def test_les_valeurs_manquantes_comptent_pour_une_valeur(self):
        """`mode='all'` : un trou est une valeur comme une autre pour l'encodage."""
        assert sonder(pa.array(["a", None, "a", None])).distinctes == 2

    def test_une_sonde_de_taille_nulle_est_refusee(self):
        with pytest.raises(ValueError, match="au moins une ligne"):
            sonder(colonne_par_plages(10, 1), taille=0)

    def test_une_colonne_fragmentee_est_sondee_sans_incident(self):
        """`read_parquet` rend des colonnes en plusieurs morceaux, que `run_end_encode`
        encode séparément. La sonde doit les traverser, pas s'y arrêter."""
        fragmentee = pa.chunked_array([colonne_par_plages(600, 300)] * 2)
        repetitions = sonder(fragmentee)
        assert repetitions.lignes == 1_200
        assert repetitions.distinctes == 2
        assert repetitions.plages <= 4  # au plus une plage de trop par morceau

    def test_une_colonne_fragmentee_et_contigue_reste_orientee_vers_les_plages(self):
        fragmentee = pa.chunked_array([colonne_par_plages(5_000, 500)] * 2)
        assert choisir(sonder(fragmentee)) == PLAGES


class TestChoisir:
    """La décision, éprouvée sans fabriquer de colonne."""

    def test_une_colonne_contigue_passe_par_les_plages(self):
        # Codes Insee dans l'ordre du fichier : 9 plages et 9 valeurs sur 10 000.
        assert choisir(Repetitions(lignes=10_000, distinctes=9, plages=9)) == PLAGES

    def test_une_colonne_repetee_mais_melangee_passe_par_le_dictionnaire(self):
        # Les mêmes codes Insee mélangés : la contiguïté a disparu, la répétition non.
        assert choisir(Repetitions(10_000, distinctes=1_063, plages=9_974)) == DICTIONNAIRE

    def test_des_contenances_passent_par_le_dictionnaire(self):
        # 2 949 valeurs distinctes sur 10 000, et 6 018 plages : trop morcelé pour les
        # plages, assez répété pour le dictionnaire. Gain mesuré : x6,2.
        assert choisir(Repetitions(10_000, distinctes=2_949, plages=6_018)) == DICTIONNAIRE

    def test_des_references_cadastrales_sont_calculees_directement(self):
        # 8 449 valeurs distinctes sur 10 000. Le dictionnaire y rend **x0,41** : la sonde
        # doit décliner. C'est le cas qui justifie qu'elle existe.
        assert choisir(Repetitions(10_000, distinctes=8_449, plages=9_821)) == DIRECT

    def test_une_colonne_vide_est_calculee_directement(self):
        assert choisir(Repetitions(0, 0, 0)) == DIRECT

    def test_les_plages_l_emportent_sur_le_dictionnaire(self):
        """Contiguë **et** peu variée : les plages, moins chères à construire."""
        assert choisir(Repetitions(10_000, distinctes=20, plages=20)) == PLAGES

    @pytest.mark.parametrize(
        ("plages", "attendu"),
        [(2_500, PLAGES), (2_501, DICTIONNAIRE)],
    )
    def test_le_seuil_de_contiguite_est_franc(self, plages, attendu):
        assert choisir(Repetitions(10_000, distinctes=3_000, plages=plages)) == attendu

    @pytest.mark.parametrize(
        ("distinctes", "attendu"),
        [(5_000, DICTIONNAIRE), (5_001, DIRECT)],
    )
    def test_le_seuil_de_variete_est_franc(self, distinctes, attendu):
        assert choisir(Repetitions(10_000, distinctes=distinctes, plages=9_000)) == attendu


class TestSondeEtDecision:
    """Les deux bout à bout, sur des colonnes fabriquées à l'image des vraies."""

    def test_des_parcelles_mitoyennes_passent_par_les_plages(self):
        assert choisir(sonder(colonne_par_plages(20_000, 500))) == PLAGES

    def test_des_references_toutes_differentes_sont_calculees_directement(self):
        assert choisir(sonder(colonne_par_plages(20_000, 1))) == DIRECT

    def test_une_colonne_vide_traverse_les_deux_sans_incident(self):
        assert choisir(sonder(pa.array([], type=pa.string()))) == DIRECT
