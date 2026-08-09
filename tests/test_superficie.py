"""Comportement attendu des conversions de superficie."""

import pandas as pd
import pytest

from basicfoncierv2 import SuperficieInvalide
from basicfoncierv2.superficie import from_ha_a_ca, to_ha_a_ca, to_hectares

# Superficies en m² avec leur écriture canonique, dans les deux sens.
ECRITURES = [
    (0, "0 ca"),
    (93, "93 ca"),
    (100, "1 a 00 ca"),
    (140, "1 a 40 ca"),
    (2297, "22 a 97 ca"),
    (10_000, "1 ha 00 a 00 ca"),
    (10_003, "1 ha 00 a 03 ca"),
    (11_320, "1 ha 13 a 20 ca"),
    (1_518_610, "151 ha 86 a 10 ca"),
]

# Écritures non canoniques que la lecture doit accepter.
ECRITURES_TOLEREES = [
    ("1 ha 0 a 3 ca", 10_003),
    ("1 a 5 ca", 105),
    ("1 ha  13 a  20 ca", 11_320),
    ("  93 ca  ", 93),
    ("1ha13a20ca", 11_320),
    ("5 ha", 50_000),
]

ECRITURES_ILLISIBLES = [
    "",
    "   ",
    "abc",
    "12",
    "1 ha 500 ca",
    "1 a 500 ca",
    "12 km",
    "-1 ca",
]


class TestEcriture:
    @pytest.mark.parametrize(("metres_carres", "attendu"), ECRITURES)
    def test_ecrit_une_superficie_au_format_ha_a_ca(self, metres_carres, attendu):
        assert to_ha_a_ca(metres_carres) == attendu

    @pytest.mark.parametrize(("metres_carres", "attendu"), ECRITURES)
    def test_donne_le_meme_resultat_sur_une_colonne(self, metres_carres, attendu):
        assert to_ha_a_ca(pd.Series([metres_carres])).iloc[0] == attendu

    def test_omet_les_hectares_quand_ils_sont_nuls(self):
        assert to_ha_a_ca(2297) == "22 a 97 ca"

    def test_omet_les_ares_quand_eux_aussi_sont_nuls(self):
        assert to_ha_a_ca(93) == "93 ca"

    def test_complete_les_composantes_suivantes_sur_deux_chiffres(self):
        assert to_ha_a_ca(10_003) == "1 ha 00 a 03 ca"

    def test_arrondit_au_metre_carre_le_plus_proche(self):
        assert to_ha_a_ca(1025.6) == "10 a 26 ca"

    def test_refuse_une_superficie_negative(self):
        with pytest.raises(SuperficieInvalide, match="négative"):
            to_ha_a_ca(-1)

    def test_remplace_une_superficie_negative_sur_demande(self):
        assert pd.isna(to_ha_a_ca(-1, invalide="manquant"))

    def test_propage_une_valeur_absente(self):
        assert pd.isna(to_ha_a_ca(pd.Series([100, None])).iloc[1])

    def test_conserve_l_index_de_la_colonne(self):
        assert list(to_ha_a_ca(pd.Series([93, 140], index=["a", "b"])).index) == ["a", "b"]

    def test_situe_les_superficies_negatives_dans_le_message(self):
        superficies = pd.Series([93, -5], index=["ok", "fautive"])
        with pytest.raises(SuperficieInvalide, match="'fautive'"):
            to_ha_a_ca(superficies)

    def test_epargne_les_lignes_valides_qui_entourent_une_negative(self):
        resultat = to_ha_a_ca(pd.Series([93, -5]), invalide="manquant")
        assert resultat.iloc[0] == "93 ca"


class TestLecture:
    @pytest.mark.parametrize(("metres_carres", "ecriture"), ECRITURES)
    def test_relit_une_ecriture_canonique(self, metres_carres, ecriture):
        assert from_ha_a_ca(ecriture) == metres_carres

    @pytest.mark.parametrize(("ecriture", "attendu"), ECRITURES_TOLEREES)
    def test_relit_une_ecriture_non_completee(self, ecriture, attendu):
        """Le v1 se trompait ici : il retirait les lettres au lieu de lire le format."""
        assert from_ha_a_ca(ecriture) == attendu

    @pytest.mark.parametrize(("ecriture", "attendu"), ECRITURES_TOLEREES)
    def test_donne_le_meme_resultat_sur_une_colonne(self, ecriture, attendu):
        assert from_ha_a_ca(pd.Series([ecriture])).iloc[0] == attendu

    @pytest.mark.parametrize("ecriture", ECRITURES_ILLISIBLES)
    def test_refuse_une_ecriture_illisible(self, ecriture):
        with pytest.raises(SuperficieInvalide):
            from_ha_a_ca(ecriture)

    @pytest.mark.parametrize("ecriture", ECRITURES_ILLISIBLES)
    def test_refuse_les_memes_ecritures_sur_une_colonne(self, ecriture):
        with pytest.raises(SuperficieInvalide):
            from_ha_a_ca(pd.Series([ecriture]))

    def test_remplace_une_ecriture_illisible_sur_demande(self):
        assert pd.isna(from_ha_a_ca("abc", invalide="manquant"))

    def test_propage_une_valeur_absente(self):
        assert pd.isna(from_ha_a_ca(pd.Series(["93 ca", None])).iloc[1])

    def test_situe_les_ecritures_illisibles_dans_le_message(self):
        superficies = pd.Series(["93 ca", "abc"], index=["ok", "fautive"])
        with pytest.raises(SuperficieInvalide, match="'fautive'"):
            from_ha_a_ca(superficies)


class TestHectares:
    def test_convertit_des_metres_carres_en_hectares(self):
        assert to_hectares(11_320) == pytest.approx(1.132)

    def test_convertit_zero(self):
        assert to_hectares(0) == pytest.approx(0.0)

    def test_donne_le_meme_resultat_sur_une_colonne(self):
        assert to_hectares(pd.Series([11_320])).iloc[0] == pytest.approx(1.132)

    def test_refuse_une_superficie_negative(self):
        with pytest.raises(SuperficieInvalide, match="négative"):
            to_hectares(-1)

    def test_propage_une_valeur_absente(self):
        assert pd.isna(to_hectares(pd.Series([100, None])).iloc[1])


class TestAllerRetour:
    """Toute écriture produite doit être relisible à l'identique."""

    @pytest.mark.parametrize(("metres_carres", "_ecriture"), ECRITURES)
    def test_relire_ce_qui_vient_d_etre_ecrit_redonne_la_superficie(self, metres_carres, _ecriture):
        assert from_ha_a_ca(to_ha_a_ca(metres_carres)) == metres_carres

    @pytest.mark.parametrize(("_ecriture", "metres_carres"), ECRITURES_TOLEREES)
    def test_une_ecriture_toleree_se_recanonise(self, _ecriture, metres_carres):
        assert from_ha_a_ca(to_ha_a_ca(metres_carres)) == metres_carres

    def test_la_propriete_tient_sur_une_colonne_entiere(self):
        superficies = pd.Series([0, 1, 99, 100, 9_999, 10_000, 1_234_567])
        relues = from_ha_a_ca(to_ha_a_ca(superficies))
        assert list(relues) == list(superficies)


class TestContratDAppel:
    def test_refuse_une_entree_qui_n_est_ni_nombre_ni_colonne(self):
        with pytest.raises(TypeError, match="list"):
            to_ha_a_ca([93])

    def test_refuse_un_booleen(self):
        """True vaut 1 en Python ; ce n'est pas une superficie pour autant."""
        with pytest.raises(TypeError, match="bool"):
            to_ha_a_ca(True)

    def test_refuse_une_colonne_textuelle_a_l_ecriture(self):
        with pytest.raises(TypeError, match="des nombres"):
            to_ha_a_ca(pd.Series(["93 ca"]))

    def test_refuse_une_colonne_numerique_a_la_lecture(self):
        with pytest.raises(TypeError, match="des chaînes"):
            from_ha_a_ca(pd.Series([93]))

    def test_refuse_une_valeur_inconnue_pour_l_option_invalide(self):
        with pytest.raises(ValueError, match="ignorer"):
            to_ha_a_ca(93, invalide="ignorer")
