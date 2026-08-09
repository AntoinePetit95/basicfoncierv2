"""Comportement attendu des conversions de code Insee de commune."""

import pandas as pd
import pytest

from basicfoncierv2 import CodeInseeInvalide
from basicfoncierv2.commune import (
    insee_from_parts,
    to_code_commune,
    to_commune_et_arrondissement,
    to_departement,
)

# Codes Insee valides avec leur découpe en département et code commune.
DECOUPES = [
    ("78048", "78", "048"),
    ("13055", "13", "055"),
    ("2A004", "2A", "004"),
    ("2B033", "2B", "033"),
    ("97215", "972", "15"),
    ("98713", "987", "13"),
    ("75104", "75", "104"),
]

CODES_INVALIDES = [
    "",
    "7804",
    "780480",
    "AB048",
    "78 48",
    "2C004",
    "78O48",
]

# Arrondissements municipaux et leur séparation en commune et numéro.
ARRONDISSEMENTS = [
    ("75101", "75100", "101"),
    ("75104", "75100", "104"),
    ("75120", "75100", "120"),
    ("69381", "69300", "381"),
    ("69389", "69300", "389"),
    ("13201", "13055", "201"),
    ("13216", "13055", "216"),
]


class TestDepartement:
    @pytest.mark.parametrize(("insee", "departement", "_commune"), DECOUPES)
    def test_extrait_le_code_departement(self, insee, departement, _commune):
        assert to_departement(insee) == departement

    @pytest.mark.parametrize(("insee", "departement", "_commune"), DECOUPES)
    def test_donne_le_meme_resultat_sur_une_colonne(self, insee, departement, _commune):
        assert to_departement(pd.Series([insee])).iloc[0] == departement

    def test_tient_sur_trois_caracteres_en_outre_mer(self):
        assert to_departement("97215") == "972"

    def test_tient_sur_deux_caracteres_en_corse(self):
        assert to_departement("2A004") == "2A"

    def test_conserve_l_index_de_la_colonne(self):
        codes = pd.Series(["78048", "97215"], index=["a", "b"])
        assert list(to_departement(codes).index) == ["a", "b"]

    def test_propage_une_valeur_absente(self):
        assert pd.isna(to_departement(pd.Series(["78048", None])).iloc[1])


class TestCodeCommune:
    @pytest.mark.parametrize(("insee", "_departement", "commune"), DECOUPES)
    def test_extrait_le_code_commune(self, insee, _departement, commune):
        assert to_code_commune(insee) == commune

    @pytest.mark.parametrize(("insee", "_departement", "commune"), DECOUPES)
    def test_donne_le_meme_resultat_sur_une_colonne(self, insee, _departement, commune):
        assert to_code_commune(pd.Series([insee])).iloc[0] == commune

    def test_tient_sur_deux_caracteres_en_outre_mer(self):
        assert to_code_commune("97215") == "15"


class TestRecomposition:
    @pytest.mark.parametrize(("insee", "departement", "commune"), DECOUPES)
    def test_recompose_le_code_insee(self, insee, departement, commune):
        assert insee_from_parts(departement, commune) == insee

    def test_recompose_l_outre_mer_sans_tronquer_le_departement(self):
        """Le v1 renvoyait ici '9715' : il tronquait le département à deux caractères."""
        assert insee_from_parts("972", "15") == "97215"

    def test_complete_le_code_commune_de_zeros(self):
        assert insee_from_parts("78", "48") == "78048"

    def test_complete_sur_deux_caracteres_en_outre_mer(self):
        assert insee_from_parts("972", "5") == "97205"

    def test_recompose_une_colonne(self):
        codes = insee_from_parts(pd.Series(["78", "972"]), pd.Series(["048", "15"]))
        assert list(codes) == ["78048", "97215"]

    def test_refuse_des_codes_qui_ne_forment_pas_un_code_insee(self):
        with pytest.raises(CodeInseeInvalide):
            insee_from_parts("789", "048")

    def test_refuse_de_melanger_chaine_et_colonne(self):
        with pytest.raises(TypeError, match="tous deux"):
            insee_from_parts("78", pd.Series(["048"]))

    def test_refuse_des_colonnes_mal_alignees(self):
        with pytest.raises(ValueError, match="alignée"):
            insee_from_parts(
                pd.Series(["78"], index=["a"]),
                pd.Series(["048"], index=["b"]),
            )


class TestAllerRetour:
    @pytest.mark.parametrize(("insee", "_departement", "_commune"), DECOUPES)
    def test_decouper_puis_recomposer_redonne_le_code(self, insee, _departement, _commune):
        assert insee_from_parts(to_departement(insee), to_code_commune(insee)) == insee

    def test_la_propriete_tient_sur_une_colonne_entiere(self):
        codes = pd.Series([insee for insee, _, _ in DECOUPES])
        recomposes = insee_from_parts(to_departement(codes), to_code_commune(codes))
        assert list(recomposes) == list(codes)


class TestArrondissement:
    @pytest.mark.parametrize(("insee", "commune", "numero"), ARRONDISSEMENTS)
    def test_separe_un_arrondissement_de_sa_commune(self, insee, commune, numero):
        assert to_commune_et_arrondissement(insee) == (commune, numero)

    @pytest.mark.parametrize(("insee", "commune", "numero"), ARRONDISSEMENTS)
    def test_donne_le_meme_resultat_sur_une_colonne(self, insee, commune, numero):
        parts = to_commune_et_arrondissement(pd.Series([insee]))
        assert tuple(parts.iloc[0]) == (commune, numero)

    def test_laisse_inchangee_une_commune_sans_arrondissement(self):
        assert to_commune_et_arrondissement("78048") == ("78048", "000")

    def test_nomme_les_colonnes(self):
        parts = to_commune_et_arrondissement(pd.Series(["75104"]))
        assert list(parts.columns) == ["insee_commune", "arrondissement"]

    def test_conserve_l_ordre_quand_les_communes_alternent(self):
        codes = pd.Series(["78048", "75104", "13201", "97215", "69381"])
        parts = to_commune_et_arrondissement(codes)
        assert list(parts["insee_commune"]) == ["78048", "75100", "13055", "97215", "69300"]

    def test_propage_une_valeur_absente(self):
        parts = to_commune_et_arrondissement(pd.Series(["75104", None]))
        assert parts.iloc[1].isna().all()

    def test_renvoie_des_valeurs_manquantes_sur_un_code_invalide_a_la_demande(self):
        assert all(
            pd.isna(part) for part in to_commune_et_arrondissement("AB048", invalide="manquant")
        )


class TestContratDAppel:
    @pytest.mark.parametrize("insee", CODES_INVALIDES)
    def test_refuse_un_code_mal_forme(self, insee):
        with pytest.raises(CodeInseeInvalide):
            to_departement(insee)

    @pytest.mark.parametrize("insee", CODES_INVALIDES)
    def test_refuse_les_memes_codes_sur_une_colonne(self, insee):
        with pytest.raises(CodeInseeInvalide):
            to_departement(pd.Series([insee]))

    def test_situe_les_codes_fautifs_dans_le_message(self):
        codes = pd.Series(["78048", "AB048"], index=["ok", "fautif"])
        with pytest.raises(CodeInseeInvalide, match="'fautif'"):
            to_departement(codes)

    def test_remplace_un_code_fautif_sur_demande(self):
        assert pd.isna(to_departement(pd.Series(["78048", "AB048"]), invalide="manquant").iloc[1])

    def test_epargne_les_codes_valides_qui_entourent_un_fautif(self):
        resultat = to_departement(pd.Series(["78048", "AB048"]), invalide="manquant")
        assert resultat.iloc[0] == "78"

    def test_refuse_une_entree_qui_n_est_ni_chaine_ni_colonne(self):
        with pytest.raises(TypeError, match="list"):
            to_departement(["78048"])

    def test_refuse_une_colonne_numerique(self):
        with pytest.raises(TypeError, match="des chaînes"):
            to_departement(pd.Series([78048]))

    def test_refuse_une_valeur_inconnue_pour_l_option_invalide(self):
        with pytest.raises(ValueError, match="ignorer"):
            to_departement("78048", invalide="ignorer")
