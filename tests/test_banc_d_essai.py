"""Comportement attendu du chronométrage du banc d'essai.

Tout est éprouvé sur des durées **injectées** : le banc d'essai sert de critère de succès
aux tâches de vitesse, il ne peut pas dépendre de l'humeur de la machine qui le vérifie.
"""

import pytest

from benchmarks.mesure import (
    Mesure,
    est_concluant,
    mesurer_ensemble,
    rapports_par_tour,
    resumer,
)

# Six tours réels de l'écriture `ha a ca` sur 200 000 contenances, relevés le 2026-08-13.
# Les tours 3 et 5 sont ralentis d'un facteur trois — et les **deux** variantes le sont
# ensemble. C'est le cas que l'appariement doit traverser sans broncher.
TOURS_PERTURBES_V1 = [0.2745, 0.2142, 0.3353, 0.1951, 0.5640, 0.2783]
TOURS_PERTURBES_V2 = [0.1029, 0.1081, 0.3060, 0.0871, 0.3921, 0.1350]


class TestResumer:
    """La médiane, le minimum et le maximum d'une série d'observations."""

    def test_mediane_d_un_nombre_impair_de_valeurs(self):
        assert resumer([3.0, 1.0, 2.0]).mediane == 2.0

    def test_mediane_d_un_nombre_pair_de_valeurs(self):
        assert resumer([4.0, 1.0, 3.0, 2.0]).mediane == 2.5

    def test_une_seule_valeur_se_resume_a_elle_meme(self):
        mesure = resumer([1.5])
        assert (mesure.mediane, mesure.minimum, mesure.maximum) == (1.5, 1.5, 1.5)

    def test_les_bornes_ne_dependent_pas_de_l_ordre(self):
        mesure = resumer([5.0, 1.0, 3.0])
        assert (mesure.minimum, mesure.maximum) == (1.0, 5.0)

    def test_une_valeur_aberrante_ne_deplace_pas_la_mediane(self):
        assert resumer([1.0, 1.0, 1.0, 1.0, 40.0]).mediane == 1.0

    def test_une_serie_vide_est_refusee(self):
        with pytest.raises(ValueError, match="au moins une observation"):
            resumer([])

    def test_la_dispersion_est_l_etendue_rapportee_a_la_mediane(self):
        assert resumer([0.9, 1.0, 1.1]).dispersion == pytest.approx(0.2)

    def test_une_serie_constante_n_a_aucune_dispersion(self):
        assert resumer([2.0, 2.0, 2.0]).dispersion == 0.0


class TestRapportsParTour:
    """Le rapport se calcule tour par tour, jamais sur les totaux."""

    def test_chaque_tour_donne_son_rapport(self):
        assert rapports_par_tour([2.0, 6.0], [1.0, 2.0]) == [2.0, 3.0]

    def test_un_ralentissement_commun_laisse_le_rapport_intact(self):
        """Les deux variantes trois fois plus lentes au même tour : rapport inchangé."""
        assert rapports_par_tour([1.0, 3.0], [0.5, 1.5]) == [2.0, 2.0]

    def test_des_series_de_longueurs_differentes_sont_refusees(self):
        with pytest.raises(ValueError, match="appariées"):
            rapports_par_tour([1.0, 2.0], [1.0])

    def test_sur_des_tours_reellement_perturbes_le_gain_reste_lisible(self):
        rapports = resumer(rapports_par_tour(TOURS_PERTURBES_V1, TOURS_PERTURBES_V2))
        assert est_concluant(rapports)
        assert rapports.mediane == pytest.approx(2.0, abs=0.1)


class TestSignificativite:
    """Un écart n'est un résultat que si tous les tours désignent le même gagnant."""

    def test_un_gain_franc_est_retenu(self):
        assert est_concluant(resumer([2.4, 2.6, 2.5]))

    def test_une_perte_franche_est_retenue_aussi(self):
        assert est_concluant(resumer([0.4, 0.6, 0.5]))

    def test_un_ecart_de_5_pour_cent_dont_l_ordre_s_inverse_ne_conclut_pas(self):
        rapports = resumer([0.97, 1.05, 1.13])
        assert rapports.mediane > 1.0
        assert not est_concluant(rapports)

    def test_le_meme_ecart_de_5_pour_cent_stable_est_retenu(self):
        assert est_concluant(resumer([1.04, 1.05, 1.06]))

    def test_une_egalite_exacte_ne_conclut_pas(self):
        assert not est_concluant(resumer([1.0, 1.0, 1.0]))


class TestEntrelacement:
    """Le point de tout l'exercice : chaque variante est appelée une fois par tour."""

    def test_chaque_variante_est_appelee_une_fois_par_tour(self):
        appels = []
        mesurer_ensemble(
            {"a": lambda: appels.append("a"), "b": lambda: appels.append("b")},
            repetitions=3,
        )
        chauffe, mesures = appels[:2], appels[2:]
        assert chauffe == ["a", "b"]
        assert mesures == ["a", "b", "a", "b", "a", "b"]

    def test_le_tour_de_chauffe_n_est_pas_compte(self):
        appels = []
        mesurer_ensemble({"a": lambda: appels.append(None)}, repetitions=3)
        assert len(appels) == 4  # quatre appels pour trois tours mesurés

    def test_il_y_a_une_duree_par_tour_et_par_variante(self):
        durees = mesurer_ensemble({"a": lambda: None, "b": lambda: None}, repetitions=4)
        assert set(durees) == {"a", "b"}
        assert all(len(serie) == 4 for serie in durees.values())

    def test_une_variante_seule_est_admise(self):
        assert set(mesurer_ensemble({"seule": lambda: None}, repetitions=2)) == {"seule"}


class TestMesure:
    """Le type qui porte le résumé."""

    def test_la_dispersion_se_lit_sur_une_mesure_construite_a_la_main(self):
        assert Mesure(mediane=2.0, minimum=1.0, maximum=3.0).dispersion == 1.0
