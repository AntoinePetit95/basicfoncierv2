"""Comportement attendu des conversions de code Insee de commune."""

import pandas as pd
import pyarrow as pa
import pytest

from basicfoncierv2 import CodeInseeInvalide
from basicfoncierv2.commune import (
    insee_from_parts,
    to_code_commune,
    to_commune_et_arrondissement,
    to_departement,
)
from basicfoncierv2.ref_cadastrale import idu_from_parts, to_idu, to_parts

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

# Arrondissements municipaux et leur séparation en commune réelle et numéro.
# Bornes vérifiées au Code officiel géographique : Paris 75101-75120, Lyon 69381-69389,
# Marseille 13201-13216 ; communes 75056, 69123, 13055.
ARRONDISSEMENTS = [
    ("75101", "75056", "101"),
    ("75107", "75056", "107"),
    ("75120", "75056", "120"),
    ("69381", "69123", "381"),
    ("69389", "69123", "389"),
    ("13201", "13055", "201"),
    ("13216", "13055", "216"),
]

# Codes voisins des plages d'arrondissements, qui n'en sont pas.
HORS_ARRONDISSEMENTS = ["75056", "69123", "13055", "75121", "75100", "69380", "69390", "13217"]


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

    @pytest.mark.parametrize("departement", ["7", "", "2C", "2a", "9721", "AB"])
    def test_refuse_un_code_departement_mal_forme(self, departement):
        """Sans ce contrôle, ``("7", "048")`` donnerait ``"70048"`` sans lever d'erreur.

        Le remplissage du code commune compense la lettre manquante du département, et
        le résultat a la bonne longueur : seul le département lui-même peut le trahir.
        """
        with pytest.raises(CodeInseeInvalide, match="département"):
            insee_from_parts(departement, "048")

    @pytest.mark.parametrize("departement", ["7", "2C", "9721"])
    def test_refuse_le_meme_code_departement_sur_une_colonne(self, departement):
        with pytest.raises(CodeInseeInvalide, match="département"):
            insee_from_parts(pd.Series([departement]), pd.Series(["048"]))

    def test_situe_les_departements_fautifs_dans_le_message(self):
        with pytest.raises(CodeInseeInvalide, match="'fautif'"):
            insee_from_parts(
                pd.Series(["78", "7"], index=["ok", "fautif"]),
                pd.Series(["048", "048"], index=["ok", "fautif"]),
            )

    def test_ne_conseille_pas_une_option_qui_n_existe_pas(self):
        """``insee_from_parts`` n'offre pas d'option ``invalide`` : ne pas la suggérer."""
        with pytest.raises(CodeInseeInvalide) as leve:
            insee_from_parts(pd.Series(["78"]), pd.Series(["0480"]))
        assert "invalide='manquant'" not in str(leve.value)

    def test_recompose_la_corse(self):
        assert insee_from_parts("2A", "004") == "2A004"

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

    @pytest.mark.parametrize("insee", HORS_ARRONDISSEMENTS)
    def test_laisse_inchange_un_code_voisin_d_une_plage_d_arrondissements(self, insee):
        """Les bornes des trois plages sont exactes : ni trop larges, ni décalées.

        ``75100`` en fait partie : c'est le code que le v1 employait pour la commune de
        Paris, et il n'existe pas au répertoire Insee.
        """
        assert to_commune_et_arrondissement(insee) == (insee, "000")

    def test_ramene_un_arrondissement_a_la_commune_reelle_et_non_au_code_du_v1(self):
        """Le v1 rendait ``75100`` pour Paris et ``69300`` pour Lyon : ils n'existent pas."""
        assert to_commune_et_arrondissement("75107")[0] == "75056"
        assert to_commune_et_arrondissement("69381")[0] == "69123"

    def test_nomme_les_colonnes(self):
        parts = to_commune_et_arrondissement(pd.Series(["75104"]))
        assert list(parts.columns) == ["insee_commune", "arrondissement"]

    def test_conserve_l_ordre_quand_les_communes_alternent(self):
        codes = pd.Series(["78048", "75104", "13201", "97215", "69381"])
        parts = to_commune_et_arrondissement(codes)
        assert list(parts["insee_commune"]) == ["78048", "75056", "13055", "97215", "69123"]
        assert list(parts["arrondissement"]) == ["000", "104", "201", "000", "381"]

    def test_propage_une_valeur_absente(self):
        parts = to_commune_et_arrondissement(pd.Series(["75104", None]))
        assert parts.iloc[1].isna().all()

    def test_renvoie_des_valeurs_manquantes_sur_un_code_invalide_a_la_demande(self):
        assert all(
            pd.isna(part) for part in to_commune_et_arrondissement("AB048", invalide="manquant")
        )

    @pytest.mark.parametrize(
        ("commune", "codes"),
        [
            ("75056", [f"751{numero:02d}" for numero in range(1, 21)]),
            ("69123", [f"693{numero:02d}" for numero in range(81, 90)]),
            ("13055", [f"132{numero:02d}" for numero in range(1, 17)]),
        ],
    )
    def test_couvre_tous_les_arrondissements_de_la_ville(self, commune, codes):
        """20 arrondissements à Paris, 9 à Lyon, 16 à Marseille (Insee, COG)."""
        parts = to_commune_et_arrondissement(pd.Series(codes))
        assert list(parts["insee_commune"]) == [commune] * len(codes)
        assert list(parts["arrondissement"]) == [code[2:] for code in codes]


class TestParcelleDansUnArrondissement:
    """Une référence cadastrale porte le code d'arrondissement, pas celui de la commune.

    Cas réel : la parcelle du pilier Ouest de la tour Eiffel, dans le 7ᵉ arrondissement
    de Paris. Aucune parcelle parisienne ne porte ``75056``.
    """

    PILIER_OUEST = "75107000CR0002"

    def test_le_champ_insee_de_la_reference_est_l_arrondissement(self):
        assert to_parts(self.PILIER_OUEST)[0] == "75107"

    def test_la_reference_traverse_la_bibliotheque_inchangee(self):
        assert to_idu(self.PILIER_OUEST) == self.PILIER_OUEST

    def test_la_commune_reelle_se_deduit_du_champ_insee(self):
        insee = to_parts(self.PILIER_OUEST)[0]
        assert to_commune_et_arrondissement(insee) == ("75056", "107")

    def test_le_chemin_colonne_donne_la_meme_chose(self):
        parts = to_parts(pd.Series([self.PILIER_OUEST]))
        communes = to_commune_et_arrondissement(parts["insee"])
        assert tuple(communes.iloc[0]) == ("75056", "107")

    def test_le_departement_reste_celui_de_paris(self):
        assert to_departement(to_parts(self.PILIER_OUEST)[0]) == "75"

    def test_la_recomposition_concatene_sans_deviner_l_arrondissement(self):
        """Rien dans ``("75", "056")`` ne dit l'arrondissement : on ne l'invente pas."""
        assert insee_from_parts("75", "056") == "75056"
        assert insee_from_parts("75", "107") == "75107"

    def test_assembler_une_reference_depuis_le_code_commune_ne_leve_pas_d_erreur(self):
        """Elle est bien formée, mais ne désigne aucune parcelle : la docstring le dit."""
        assert idu_from_parts("75056", "000", "CR", "0002") == "75056000CR0002"


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

    def test_refuse_une_colonne_d_objets_qui_contient_des_nombres(self):
        with pytest.raises(TypeError, match="des chaînes"):
            to_departement(pd.Series([78048], dtype=object))

    @pytest.mark.parametrize(
        "fonction", [to_departement, to_code_commune, to_commune_et_arrondissement]
    )
    def test_refuse_un_saut_de_ligne_final_des_deux_cotes(self, fonction):
        """Le ``$`` du module ``re`` tolère un saut de ligne final, celui de RE2 non."""
        with pytest.raises(CodeInseeInvalide):
            fonction("78048\n")
        with pytest.raises(CodeInseeInvalide):
            fonction(pd.Series(["78048\n"]))

    @pytest.mark.parametrize("fonction", [to_code_commune, to_commune_et_arrondissement])
    def test_les_autres_fonctions_remplacent_aussi_un_code_fautif_sur_demande(self, fonction):
        resultat = fonction(pd.Series(["AB048"]), invalide="manquant")
        assert resultat.isna().all(axis=None)

    @pytest.mark.parametrize(
        "fonction", [to_departement, to_code_commune, to_commune_et_arrondissement]
    )
    def test_refuse_une_valeur_inconnue_pour_l_option_invalide(self, fonction):
        with pytest.raises(ValueError, match="ignorer"):
            fonction("78048", invalide="ignorer")

    def test_traite_une_colonne_fragmentee(self):
        """Une colonne issue de read_parquet(dtype_backend='pyarrow') est découpée."""
        morceaux = pa.chunked_array([["78048", "97215"], ["2A004"]], type=pa.string())
        codes = pd.Series(pd.arrays.ArrowExtensionArray(morceaux))

        assert morceaux.num_chunks > 1
        assert list(to_departement(codes)) == ["78", "972", "2A"]
