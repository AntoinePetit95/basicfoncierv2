"""Comportement attendu de la décomposition d'une référence cadastrale."""

import pandas as pd
import pyarrow as pa
import pytest

from basicfoncierv2 import ReferenceCadastraleInvalide
from basicfoncierv2.ref_cadastrale import (
    idu_from_parts,
    short_id_from_parts,
    to_idu,
    to_parts,
    to_short_id,
)

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
    # Corse : le département s'écrit 2A ou 2B, dans toutes les formes.
    ("2A0040000H0011", ("2A004", "000", "0H", "0011")),
    ("2A004H11", ("2A004", "000", "0H", "0011")),
    ("2A004123AB1", ("2A004", "123", "AB", "0001")),
    ("2B0330000C0302", ("2B033", "000", "0C", "0302")),
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
    # Quatorze caractères, mais pas une forme idu pour autant : hors Alsace-Moselle il
    # faut une lettre de section, et en Alsace-Moselle il n'en faut pas.
    "78048000120123",
    "57463000AB1234",
    # La Corse n'admet que 2A et 2B, en majuscules : rien d'autre n'est un département.
    "2C004H11",
    "2a004H11",
    "2A04H11",
]


# Chaque référence valide avec sa forme idu et son identifiant court.
FORMES = [
    ("780480000H0011", "780480000H0011", "78048H11"),
    ("78048000H11", "780480000H0011", "78048H11"),
    ("78048H11", "780480000H0011", "78048H11"),
    ("780480H11", "780480000H0011", "78048H11"),
    ("78048123AB1", "78048123AB0001", "78048123AB1"),
    ("78048AB1234", "78048000AB1234", "78048AB1234"),
    ("972150000C0302", "972150000C0302", "97215C302"),
    ("57463123456789", "57463123456789", "57463123456789"),
    ("2A0040000H0011", "2A0040000H0011", "2A004H11"),
    ("2A004H11", "2A0040000H0011", "2A004H11"),
    ("2A004123AB1", "2A004123AB0001", "2A004123AB1"),
    ("2B0330000C0302", "2B0330000C0302", "2B033C302"),
]


class TestFormeIdu:
    @pytest.mark.parametrize(("ref", "idu", "_court"), FORMES)
    def test_ramene_une_chaine_a_sa_forme_idu(self, ref, idu, _court):
        assert to_idu(ref) == idu

    @pytest.mark.parametrize(("ref", "idu", "_court"), FORMES)
    def test_donne_le_meme_resultat_sur_une_colonne(self, ref, idu, _court):
        assert to_idu(pd.Series([ref])).iloc[0] == idu

    def test_produit_toujours_quatorze_caracteres(self):
        assert {len(to_idu(ref)) for ref, _, _ in FORMES} == {14}

    def test_conserve_l_index_de_la_colonne(self):
        refs = pd.Series(["78048H11", "78048AB1234"], index=["a", "b"])
        assert list(to_idu(refs).index) == ["a", "b"]

    def test_propage_une_valeur_absente(self):
        assert pd.isna(to_idu(pd.Series(["78048H11", None])).iloc[1])

    def test_leve_une_erreur_metier_sur_une_reference_illisible(self):
        with pytest.raises(ReferenceCadastraleInvalide):
            to_idu("AB048H11")

    def test_renvoie_une_valeur_manquante_quand_l_appelant_le_demande(self):
        assert pd.isna(to_idu("AB048H11", invalide="manquant"))


class TestIdentifiantCourt:
    @pytest.mark.parametrize(("ref", "_idu", "court"), FORMES)
    def test_reduit_une_chaine_a_son_identifiant_court(self, ref, _idu, court):
        assert to_short_id(ref) == court

    @pytest.mark.parametrize(("ref", "_idu", "court"), FORMES)
    def test_donne_le_meme_resultat_sur_une_colonne(self, ref, _idu, court):
        assert to_short_id(pd.Series([ref])).iloc[0] == court

    def test_omet_la_commune_absorbee_quand_elle_est_absente(self):
        assert to_short_id("780480000H0011") == "78048H11"

    def test_conserve_la_commune_absorbee_quand_elle_est_presente(self):
        assert to_short_id("78048123AB0001") == "78048123AB1"

    def test_laisse_une_reference_d_alsace_moselle_sous_forme_idu(self):
        """Ses sections étant numériques, une forme courte y serait illisible."""
        assert to_short_id("57463123456789") == "57463123456789"

    def test_garde_un_chiffre_quand_le_numero_ne_vaut_que_des_zeros(self):
        assert to_short_id("780480000H0000") == "78048H0"

    def test_propage_une_valeur_absente(self):
        assert pd.isna(to_short_id(pd.Series(["78048H11", None])).iloc[1])

    def test_leve_une_erreur_metier_sur_une_reference_illisible(self):
        with pytest.raises(ReferenceCadastraleInvalide):
            to_short_id("AB048H11")


class TestAllerRetour:
    """Toute forme produite doit rester lisible : c'est la propriété qui compte."""

    @pytest.mark.parametrize(("ref", "_idu", "_court"), FORMES)
    def test_la_forme_idu_se_decompose_comme_la_reference_d_origine(self, ref, _idu, _court):
        assert to_parts(to_idu(ref)) == to_parts(ref)

    @pytest.mark.parametrize(("ref", "_idu", "_court"), FORMES)
    def test_l_identifiant_court_se_decompose_comme_la_reference_d_origine(self, ref, _idu, _court):
        assert to_parts(to_short_id(ref)) == to_parts(ref)

    @pytest.mark.parametrize(("ref", "idu", "_court"), FORMES)
    def test_les_champs_reassembles_redonnent_la_forme_idu(self, ref, idu, _court):
        assert idu_from_parts(*to_parts(ref)) == idu

    @pytest.mark.parametrize(("ref", "_idu", "court"), FORMES)
    def test_les_champs_reassembles_redonnent_l_identifiant_court(self, ref, _idu, court):
        assert short_id_from_parts(*to_parts(ref)) == court


class TestAssemblageDepuisLesChamps:
    def test_complete_les_champs_de_zeros_a_gauche(self):
        assert idu_from_parts("78048", "0", "H", "11") == "780480000H0011"

    def test_prend_les_champs_dans_l_ordre_insee_com_abs_section_numero(self):
        assert idu_from_parts("78048", "123", "AB", "1") == "78048123AB0001"

    def test_assemble_une_colonne_par_champ(self):
        parts = to_parts(pd.Series(["78048H11", "78048123AB1"]))
        assemblees = idu_from_parts(*(parts[champ] for champ in parts.columns))
        assert list(assemblees) == ["780480000H0011", "78048123AB0001"]

    def test_assemble_l_identifiant_court_depuis_des_colonnes(self):
        parts = to_parts(pd.Series(["780480000H0011"]))
        courts = short_id_from_parts(*(parts[champ] for champ in parts.columns))
        assert courts.iloc[0] == "78048H11"

    def test_refuse_des_champs_qui_n_assemblent_pas_une_reference_lisible(self):
        with pytest.raises(ReferenceCadastraleInvalide):
            idu_from_parts("78048", "000", "00", "0011")

    def test_refuse_un_champ_plus_long_que_sa_largeur(self):
        with pytest.raises(ReferenceCadastraleInvalide):
            idu_from_parts("78048", "000", "0H", "12345")

    def test_refuse_de_melanger_chaines_et_colonnes(self):
        with pytest.raises(TypeError, match=r"tous des pandas\.Series"):
            idu_from_parts("78048", "000", "0H", pd.Series(["0011"]))

    def test_refuse_des_colonnes_mal_alignees(self):
        with pytest.raises(ValueError, match="alignée"):
            idu_from_parts(
                pd.Series(["78048"], index=["a"]),
                pd.Series(["000"], index=["b"]),
                pd.Series(["0H"], index=["a"]),
                pd.Series(["0011"], index=["a"]),
            )


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


class TestMelangeDeFormes:
    """La colonne emprunte deux chemins selon la forme : ils doivent se recoller.

    Une référence déjà de forme idu est découpée à positions fixes ; toute autre est
    d'abord reconstruite par extraction. Ces tests vérifient que le mélange des deux
    ne décale ni ne mélange les lignes.
    """

    def test_decompose_une_forme_courte_placee_apres_une_forme_idu(self):
        parts = to_parts(pd.Series(["780480000H0011", "78048AB1"]))
        assert tuple(parts.iloc[1]) == ("78048", "000", "AB", "0001")

    def test_decompose_une_forme_idu_placee_apres_une_forme_courte(self):
        parts = to_parts(pd.Series(["78048AB1", "780480000H0011"]))
        assert tuple(parts.iloc[1]) == ("78048", "000", "0H", "0011")

    def test_conserve_l_ordre_des_lignes_quand_les_formes_alternent(self):
        refs = ["780480000H0011", "78048AB1", "57463123456789", None, "78048H11"]
        attendu = ["78048", "78048", "57463", None, "78048"]
        parts = to_parts(pd.Series(refs))
        assert list(parts["insee"].astype(object).where(parts["insee"].notna(), None)) == attendu

    def test_decompose_une_colonne_entierement_de_forme_idu(self):
        parts = to_parts(pd.Series(["780480000H0011", "972150000C0302"]))
        assert list(parts["section"]) == ["0H", "0C"]

    def test_decompose_une_colonne_sans_aucune_forme_idu(self):
        parts = to_parts(pd.Series(["78048H11", "78048AB1"]))
        assert list(parts["numero"]) == ["0011", "0001"]

    @pytest.mark.parametrize("ref", REFERENCES_INVALIDES)
    def test_rejette_les_memes_references_que_le_chemin_scalaire(self, ref):
        with pytest.raises(ReferenceCadastraleInvalide):
            to_parts(pd.Series([ref]))

    def test_isole_la_ligne_fautive_au_milieu_de_lignes_de_forme_idu(self):
        refs = pd.Series(["780480000H0011", "78048000120123", "972150000C0302"])
        parts = to_parts(refs, invalide="manquant")
        assert parts.iloc[1].isna().all()

    def test_epargne_les_formes_idu_qui_entourent_une_ligne_fautive(self):
        refs = pd.Series(["780480000H0011", "78048000120123", "972150000C0302"])
        parts = to_parts(refs, invalide="manquant")
        assert tuple(parts.iloc[2]) == ("97215", "000", "0C", "0302")


class TestColonneFragmentee:
    """Une colonne adossée à Arrow peut être découpée en plusieurs morceaux.

    C'est le cas ordinaire d'un ``read_parquet(dtype_backend='pyarrow')``. Le mélange
    des deux chemins de normalisation passe par ``replace_with_mask``, qui refuse un
    tableau fragmenté : il doit être recollé à l'entrée.
    """

    @staticmethod
    def _fragmentee(*morceaux: list[str]) -> pd.Series:
        decoupe = pa.chunked_array(list(morceaux), type=pa.string())
        assert decoupe.num_chunks > 1
        return pd.Series(pd.arrays.ArrowExtensionArray(decoupe))

    def test_decompose_une_colonne_fragmentee_de_formes_melangees(self):
        refs = self._fragmentee(["780480000H0011", "78048H11"], ["972150000C0302"])
        assert tuple(to_parts(refs).iloc[1]) == ("78048", "000", "0H", "0011")

    def test_ramene_une_colonne_fragmentee_a_la_forme_idu(self):
        refs = self._fragmentee(["78048H11"], ["2A004H11", "972150000C0302"])
        assert list(to_idu(refs)) == ["780480000H0011", "2A0040000H0011", "972150000C0302"]

    def test_signale_les_references_fautives_d_une_colonne_fragmentee(self):
        refs = self._fragmentee(["780480000H0011"], ["AB048H11"])
        with pytest.raises(ReferenceCadastraleInvalide, match="AB048H11"):
            to_parts(refs)


class TestContratDAppel:
    def test_refuse_une_entree_qui_n_est_ni_chaine_ni_colonne(self):
        with pytest.raises(TypeError, match="list"):
            to_parts(["78048H11"])

    def test_refuse_une_colonne_numerique_en_expliquant_les_zeros_perdus(self):
        with pytest.raises(TypeError, match="zéros de tête"):
            to_parts(pd.Series([78048011]))

    def test_refuse_une_colonne_d_objets_qui_contient_des_nombres(self):
        """Le dtype ``object`` ne dit rien du contenu : Arrow convertirait sans broncher."""
        with pytest.raises(TypeError, match="zéros de tête"):
            to_parts(pd.Series([78048011], dtype=object))

    def test_accepte_une_colonne_d_objets_entierement_absente(self):
        """Rien à reprocher à une colonne vide de toute valeur."""
        assert to_idu(pd.Series([None, None], dtype=object)).isna().all()

    @pytest.mark.parametrize("fonction", [to_idu, to_short_id, to_parts])
    def test_refuse_un_saut_de_ligne_final_des_deux_cotes(self, fonction):
        """Le ``$`` du module ``re`` tolère un saut de ligne final, celui de RE2 non.

        Sans ``fullmatch``, le chemin scalaire accepterait une référence que le chemin
        colonne rejette.
        """
        with pytest.raises(ReferenceCadastraleInvalide):
            fonction("780480000H0011\n")
        with pytest.raises(ReferenceCadastraleInvalide):
            fonction(pd.Series(["780480000H0011\n"]))

    @pytest.mark.parametrize("fonction", [to_idu, to_short_id])
    def test_remplace_une_reference_illisible_sur_demande(self, fonction):
        assert pd.isna(fonction("AB048H11", invalide="manquant"))
        assert fonction(pd.Series(["AB048H11"]), invalide="manquant").isna().all()

    @pytest.mark.parametrize("fonction", [to_idu, to_short_id, to_parts])
    def test_refuse_une_valeur_inconnue_pour_l_option_invalide(self, fonction):
        with pytest.raises(ValueError, match="ignorer"):
            fonction("78048H11", invalide="ignorer")
