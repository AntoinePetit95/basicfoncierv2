"""Comportement attendu de la décomposition d'une référence cadastrale."""

import pandas as pd
import pytest

from basicfoncierv2 import ReferenceCadastraleInvalide
from basicfoncierv2.ref_cadastrale import to_parts

# Références valides couvrant toutes les formes acceptées, avec leur décomposition
# canonique (insee, com_abs, section, numero). Sert aux deux chemins d'exécution.
REFERENCES_VALIDES = [
    ("780480000H0011", ("78048", "000", "0H", "0011")),
    ("78048000H11", ("78048", "000", "0H", "0011")),
    ("78048H11", ("78048", "000", "0H", "0011")),
    ("780480H11", ("78048", "000", "0H", "0011")),
    ("78048123AB1", ("78048", "123", "AB", "0001")),
    ("78048AB1234", ("78048", "000", "AB", "1234")),
    ("972150000C0302", ("97215", "000", "0C", "0302")),
    ("57463123456789", ("57463", "123", "45", "6789")),
]

REFERENCES_INVALIDES = [
    "",
    "7804",
    "78048",
    "78048000",
    "780480001234",
    "57463H11",
    "5746312345678",
    "574631234567890",
    "78048 H11",
    "AB048H11",
]


class TestDecompositionScalaire:
    @pytest.mark.parametrize(("ref", "attendu"), REFERENCES_VALIDES)
    def test_decompose_dans_l_ordre_insee_com_abs_section_numero(self, ref, attendu):
        assert to_parts(ref) == attendu

    def test_complete_chaque_champ_de_zeros_a_gauche(self):
        insee, com_abs, section, numero = to_parts("78048H11")
        assert (len(insee), len(com_abs), len(section), len(numero)) == (5, 3, 2, 4)

    def test_alsace_moselle_place_la_commune_absorbee_au_meme_rang_que_le_regime_general(self):
        """Non-régression du bug hérité de basicfoncier v1 (docs/BUGS.md).

        Le v1 renvoyait (insee, section, numero, com_abs) en Alsace-Moselle et
        (insee, com_abs, section, numero) ailleurs. Les deux régimes doivent
        désormais produire le même ordre.
        """
        _, com_abs_alsace_moselle, _, _ = to_parts("57463123456789")
        _, com_abs_general, _, _ = to_parts("78048123AB1")

        assert com_abs_alsace_moselle == "123"
        assert com_abs_general == "123"

    @pytest.mark.parametrize("ref", REFERENCES_INVALIDES)
    def test_leve_une_erreur_metier_sur_une_reference_non_decomposable(self, ref):
        with pytest.raises(ReferenceCadastraleInvalide):
            to_parts(ref)

    def test_le_message_d_erreur_nomme_la_reference_fautive(self):
        with pytest.raises(ReferenceCadastraleInvalide, match="'78048'"):
            to_parts("78048")

    def test_une_forme_courte_est_refusee_en_alsace_moselle(self):
        """Les sections y sont numériques : rien ne sépare la section du numéro."""
        with pytest.raises(ReferenceCadastraleInvalide):
            to_parts("57463H11")

    def test_renvoie_des_valeurs_manquantes_quand_l_appelant_le_demande(self):
        assert all(pd.isna(part) for part in to_parts("78048", invalide="manquant"))


class TestDecompositionColonne:
    @pytest.mark.parametrize(("ref", "attendu"), REFERENCES_VALIDES)
    def test_donne_le_meme_resultat_que_sur_une_chaine(self, ref, attendu):
        """Les deux chemins — RE2 côté Arrow, re côté Python — doivent concorder."""
        parts = to_parts(pd.Series([ref]))
        assert tuple(parts.iloc[0]) == attendu

    def test_nomme_les_colonnes_dans_l_ordre_canonique(self):
        parts = to_parts(pd.Series(["78048H11"]))
        assert list(parts.columns) == ["insee", "com_abs", "section", "numero"]

    def test_conserve_l_index_de_la_colonne_d_entree(self):
        refs = pd.Series(["78048H11", "78048AB1234"], index=["a", "b"])
        assert list(to_parts(refs).index) == ["a", "b"]

    def test_propage_une_valeur_absente_sans_lever_d_erreur(self):
        parts = to_parts(pd.Series(["78048H11", None]))
        assert parts.iloc[1].isna().all()

    def test_decompose_la_ligne_valide_qui_accompagne_une_valeur_absente(self):
        parts = to_parts(pd.Series(["78048H11", None]))
        assert tuple(parts.iloc[0]) == ("78048", "000", "0H", "0011")

    def test_accepte_une_colonne_d_une_seule_ligne(self):
        assert len(to_parts(pd.Series(["78048H11"]))) == 1

    def test_accepte_une_colonne_vide(self):
        assert to_parts(pd.Series([], dtype=object)).empty

    def test_leve_une_erreur_metier_sur_une_reference_non_decomposable(self):
        with pytest.raises(ReferenceCadastraleInvalide):
            to_parts(pd.Series(["78048H11", "AB048H11"]))

    def test_le_message_d_erreur_situe_les_references_fautives(self):
        refs = pd.Series(["78048H11", "AB048H11"], index=["ok", "fautive"])
        with pytest.raises(ReferenceCadastraleInvalide, match="'fautive'"):
            to_parts(refs)

    def test_remplace_la_ligne_fautive_par_des_valeurs_manquantes_sur_demande(self):
        parts = to_parts(pd.Series(["78048H11", "AB048H11"]), invalide="manquant")
        assert parts.iloc[1].isna().all()

    def test_epargne_les_lignes_valides_qui_entourent_une_ligne_fautive(self):
        parts = to_parts(pd.Series(["78048H11", "AB048H11"]), invalide="manquant")
        assert tuple(parts.iloc[0]) == ("78048", "000", "0H", "0011")


class TestContratDAppel:
    def test_refuse_une_entree_qui_n_est_ni_chaine_ni_colonne(self):
        with pytest.raises(TypeError, match="list"):
            to_parts(["78048H11"])

    def test_refuse_une_colonne_numerique_en_expliquant_les_zeros_perdus(self):
        with pytest.raises(TypeError, match="zéros de tête"):
            to_parts(pd.Series([78048011]))

    def test_refuse_une_valeur_inconnue_pour_l_option_invalide(self):
        with pytest.raises(ValueError, match="ignorer"):
            to_parts("78048H11", invalide="ignorer")
