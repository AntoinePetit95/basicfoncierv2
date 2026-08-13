"""Comportement attendu du chronométrage du banc d'essai.

L'essentiel est éprouvé sur des durées **injectées** : le banc d'essai sert de critère de
succès aux tâches de vitesse, il ne peut pas dépendre de l'humeur de la machine qui le
vérifie. Seul le sens du gain est éprouvé sur du travail réel, faute de pouvoir l'être
autrement — voir :class:`TestSensDuGain`.
"""

import math

import pytest

from benchmarks.__main__ import comparer, conclure
from benchmarks.mesure import (
    Encadrement,
    Mesure,
    encadrer,
    mesurer_ensemble,
    rapports_par_tour,
    resumer,
)

# Six tours réels de l'écriture `ha a ca` sur 200 000 contenances, relevés le 2026-08-13.
# Les tours 3 et 5 sont ralentis — inégalement : au tour 3 le v1 encaisse 1,2x et le v2
# 2,5x. C'est le cas que l'appariement doit atténuer sans prétendre l'annuler.
TOURS_PERTURBES_V1 = [0.2745, 0.2142, 0.3353, 0.1951, 0.5640, 0.2783]
TOURS_PERTURBES_V2 = [0.1029, 0.1081, 0.3060, 0.0871, 0.3921, 0.1350]


class TestResumer:
    """La médiane, le minimum et le maximum d'une série de durées."""

    def test_mediane_d_un_nombre_impair_de_valeurs(self):
        assert resumer([9.0, 1.0, 2.0]).mediane == 2.0

    def test_mediane_d_un_nombre_pair_de_valeurs(self):
        assert resumer([16.0, 1.0, 3.0, 2.0]).mediane == 2.5

    def test_une_seule_valeur_se_resume_a_elle_meme(self):
        mesure = resumer([1.5])
        assert (mesure.mediane, mesure.minimum, mesure.maximum) == (1.5, 1.5, 1.5)

    def test_les_bornes_ne_dependent_pas_de_l_ordre(self):
        mesure = resumer([5.0, 1.0, 3.0])
        assert (mesure.minimum, mesure.maximum) == (1.0, 5.0)

    def test_une_valeur_aberrante_ne_deplace_pas_la_mediane(self):
        assert resumer([1.0, 1.0, 1.0, 1.0, 40.0]).mediane == 1.0

    def test_l_etendue_est_l_ecart_des_bornes_rapporte_a_la_mediane(self):
        assert resumer([0.9, 1.0, 1.1]).etendue == pytest.approx(0.2)

    def test_une_serie_constante_n_a_aucune_etendue(self):
        assert resumer([2.0, 2.0, 2.0]).etendue == 0.0


class TestDureesRefusees:
    """Une durée hors du domaine mesurable est un bogue, pas une donnée."""

    def test_une_serie_vide_est_refusee(self):
        with pytest.raises(ValueError, match="au moins un tour"):
            resumer([])

    @pytest.mark.parametrize("fautive", [0.0, -1.0, math.inf])
    def test_une_duree_hors_domaine_est_refusee(self, fautive):
        with pytest.raises(ValueError, match="strictement positif"):
            resumer([1.0, fautive, 1.0])

    def test_le_message_situe_la_faute(self):
        with pytest.raises(ValueError, match=r"1 durée\(s\) sur 3"):
            resumer([1.0, 0.0, 1.0])

    def test_une_duree_nulle_de_la_candidate_ne_ressort_pas_en_division_par_zero(self):
        with pytest.raises(ValueError, match="strictement positif"):
            rapports_par_tour([1.0, 1.0], [1.0, 0.0])

    def test_une_duree_nulle_de_la_reference_est_refusee_aussi(self):
        """Les deux séries sont contrôlées, pas seulement celle qui divise."""
        with pytest.raises(ValueError, match="strictement positif"):
            rapports_par_tour([1.0, 0.0], [1.0, 1.0])


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

    def test_l_appariement_resserre_ce_que_les_durees_dispersent(self):
        """Sur des tours réellement perturbés, le rapport bouge moins que les durées."""
        rapports = resumer(rapports_par_tour(TOURS_PERTURBES_V1, TOURS_PERTURBES_V2))
        assert rapports.etendue < resumer(TOURS_PERTURBES_V1).etendue
        assert rapports.etendue < resumer(TOURS_PERTURBES_V2).etendue

    def test_le_gain_reste_lisible_malgre_les_perturbations(self):
        encadrement = encadrer(rapports_par_tour(TOURS_PERTURBES_V1, TOURS_PERTURBES_V2))
        assert encadrement.concluant
        assert encadrement.gain == pytest.approx(1.9, abs=0.1)


class TestEncadrer:
    """Le gain est publié avec l'intervalle qui le soutient, ou pas publié du tout."""

    def test_un_gain_franc_est_retenu(self):
        assert encadrer([2.4, 2.6, 2.5]).concluant

    def test_une_perte_franche_est_retenue_aussi(self):
        encadrement = encadrer([0.4, 0.6, 0.5])
        assert encadrement.concluant
        assert encadrement.gain < 1.0

    def test_un_ecart_de_5_pour_cent_noye_dans_le_bruit_ne_conclut_pas(self):
        assert not encadrer([0.97, 1.05, 1.13]).concluant

    def test_le_meme_ecart_de_5_pour_cent_stable_est_retenu(self):
        assert encadrer([1.04, 1.05, 1.06]).concluant

    def test_une_egalite_exacte_ne_conclut_pas(self):
        assert not encadrer([1.0, 1.0, 1.0]).concluant

    def test_l_intervalle_encadre_le_gain(self):
        encadrement = encadrer([1.8, 2.0, 2.2])
        assert encadrement.borne_basse < encadrement.gain < encadrement.borne_haute

    def test_le_gain_est_une_moyenne_geometrique(self):
        """x2 et x0,5 sont deux écarts de même ampleur : leur gain moyen est 1."""
        assert encadrer([2.0, 0.5]).gain == pytest.approx(1.0)

    def test_ajouter_des_tours_resserre_l_intervalle(self):
        """La propriété qui manquait au critère précédent : la mesure s'améliore."""
        etroit = encadrer([1.04, 1.05, 1.06] * 4)
        large = encadrer([1.04, 1.05, 1.06])
        assert etroit.borne_haute - etroit.borne_basse < large.borne_haute - large.borne_basse

    def test_ajouter_des_tours_ne_retire_jamais_une_conclusion_acquise(self):
        assert encadrer([1.04, 1.05, 1.06]).concluant
        assert encadrer([1.04, 1.05, 1.06] * 7).concluant

    def test_au_dela_de_la_table_le_quantile_reste_celui_de_vingt_degres(self):
        """Retomber sur 1,96 rendrait l'intervalle trop étroit : 8 % de fausse alerte."""
        rapports = [1.10, 0.90] * 11  # 22 tours, soit 21 degrés de liberté, hors table
        encadrement = encadrer(rapports)
        logarithmes = [math.log(rapport) for rapport in rapports]
        moyenne = sum(logarithmes) / len(logarithmes)
        variance = sum((valeur - moyenne) ** 2 for valeur in logarithmes) / (len(rapports) - 1)
        attendu = 2.086 * math.sqrt(variance / len(rapports))
        assert math.log(encadrement.borne_haute / encadrement.gain) == pytest.approx(attendu)

    def test_un_tour_unique_est_refuse(self):
        with pytest.raises(ValueError, match="au moins deux"):
            encadrer([1.5])

    @pytest.mark.parametrize("fautif", [0.0, -1.0, math.inf])
    def test_un_rapport_hors_du_domaine_du_logarithme_est_refuse(self, fautif):
        with pytest.raises(ValueError, match="strictement positif"):
            encadrer([1.0, fautif])


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


class TestSensDuGain:
    """Un gain annoncé à l'envers serait pire que pas de gain du tout.

    Ces deux épreuves passent par du travail réel, parce que le sens se décide au point
    d'appel, entre `mesurer_ensemble` et `encadrer` : aucune durée injectée ne l'atteint.
    L'écart entre les deux charges est de plusieurs ordres de grandeur, ce qui les met
    à l'abri de la machine qui les exécute.
    """

    @staticmethod
    def _lente() -> int:
        return sum(range(300_000))

    def test_un_v2_plus_rapide_donne_un_gain_superieur_a_un(self, capsys):
        comparer("épreuve", 1, lambda: None, self._lente, tours=3)
        annonce = capsys.readouterr().out.splitlines()[-2]
        assert "non concluant" not in annonce
        assert float(annonce.split("x")[1].split()[0]) > 1.0

    def test_un_v2_plus_lent_donne_un_gain_inferieur_a_un(self, capsys):
        comparer("épreuve", 1, self._lente, lambda: None, tours=3)
        annonce = capsys.readouterr().out.splitlines()[-2]
        assert "non concluant" not in annonce
        assert float(annonce.split("x")[1].split()[0]) < 1.0


class TestAnnonce:
    """Ce que le banc d'essai écrit, et ce qu'il refuse d'écrire."""

    def test_un_gain_concluant_est_annonce_avec_son_intervalle(self):
        annonce = conclure(Encadrement(gain=2.5, borne_basse=2.1, borne_haute=2.9))
        assert annonce == "gain v2 / v1 : x2.5   (x2.10 à x2.90 à 95 %)"

    def test_un_gain_non_concluant_n_est_pas_chiffre(self):
        annonce = conclure(Encadrement(gain=1.4, borne_basse=0.8, borne_haute=2.4))
        assert annonce == "gain v2 / v1 : non concluant — l'intervalle x0.80 à x2.40 contient 1"
        assert "x1.4" not in annonce


class TestMesure:
    """Le type qui porte le résumé."""

    def test_l_etendue_se_lit_sur_une_mesure_construite_a_la_main(self):
        assert Mesure(mediane=2.0, minimum=1.0, maximum=3.0).etendue == 1.0
