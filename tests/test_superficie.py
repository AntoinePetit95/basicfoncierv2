"""Comportement attendu des conversions de superficie."""

from typing import ClassVar

import numpy as np
import pandas as pd
import pyarrow as pa
import pytest

from basicfoncier import SuperficieInvalide
from basicfoncier.superficie import from_ha_a_ca, to_ha_a_ca, to_hectares

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

    @pytest.mark.parametrize("negative", [-0.4, -0.5, -0.9])
    def test_refuse_une_superficie_negative_qui_s_arrondit_a_zero(self, negative):
        """Le signe se lit avant l'arrondi, sans quoi -0,4 passerait pour 0 m²."""
        with pytest.raises(SuperficieInvalide, match="négative"):
            to_ha_a_ca(negative)

    @pytest.mark.parametrize("negative", [-0.4, -0.5, -0.9])
    def test_la_refuse_aussi_sur_une_colonne(self, negative):
        with pytest.raises(SuperficieInvalide, match="négative"):
            to_ha_a_ca(pd.Series([negative]))

    def test_remplace_une_negative_arrondie_a_zero_sur_demande(self):
        assert pd.isna(to_ha_a_ca(pd.Series([-0.4]), invalide="manquant").iloc[0])

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


class TestMelangeDeFormes:
    """L'écriture n'emprunte qu'une des trois formes par ligne : elles doivent se recoller.

    Chaque ligne est écrite sur le sous-ensemble qui la concerne, puis recollée par
    masque. Ces tests vérifient que le recollage ne décale ni ne mélange les lignes,
    quelles que soient les proportions — y compris quand une forme est absente.
    """

    TROIS_FORMES: ClassVar = [
        (0, "0 ca"),
        (93, "93 ca"),
        (2297, "22 a 97 ca"),
        (11_320, "1 ha 13 a 20 ca"),
    ]

    def test_ecrit_les_trois_formes_melangees_dans_l_ordre(self):
        metres = [valeur for valeur, _ in self.TROIS_FORMES]
        attendues = [texte for _, texte in self.TROIS_FORMES]
        assert list(to_ha_a_ca(pd.Series(metres))) == attendues

    def test_conserve_l_ordre_quand_les_formes_alternent(self):
        metres = pd.Series([11_320, 93, 2297, 0, 11_320])
        assert list(to_ha_a_ca(metres)) == [
            "1 ha 13 a 20 ca",
            "93 ca",
            "22 a 97 ca",
            "0 ca",
            "1 ha 13 a 20 ca",
        ]

    @pytest.mark.parametrize(
        ("metres", "attendues"),
        [
            ([10_000, 20_000], ["1 ha 00 a 00 ca", "2 ha 00 a 00 ca"]),
            ([100, 2297], ["1 a 00 ca", "22 a 97 ca"]),
            ([0, 93], ["0 ca", "93 ca"]),
        ],
    )
    def test_ecrit_une_colonne_d_une_seule_forme(self, metres, attendues):
        """Une forme absente ne doit pas empêcher les autres d'être écrites."""
        assert list(to_ha_a_ca(pd.Series(metres))) == attendues

    def test_isole_une_valeur_absente_entre_deux_formes_differentes(self):
        ecrites = to_ha_a_ca(pd.Series([11_320, None, 93]))
        assert list(ecrites.isna()) == [False, True, False]
        assert [ecrites.iloc[0], ecrites.iloc[2]] == ["1 ha 13 a 20 ca", "93 ca"]

    @pytest.mark.parametrize("borne", [0, 1, 99, 100, 101, 9_999, 10_000, 10_001])
    def test_ecrit_les_bornes_entre_formes_comme_une_valeur_seule(self, borne):
        """Les seuils de 100 et 10 000 m² font basculer de forme : ils sont exacts."""
        assert to_ha_a_ca(pd.Series([borne])).iloc[0] == to_ha_a_ca(borne)

    def test_accepte_une_colonne_vide(self):
        assert len(to_ha_a_ca(pd.Series([], dtype="int64"))) == 0


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


class TestMelangeDEcritures:
    """La lecture emprunte deux chemins selon la forme : ils doivent se recoller.

    Une écriture canonique est découpée à positions fixes ; toute autre passe par le
    motif tolérant. Ces tests vérifient que le mélange ne décale ni ne mélange les lignes.
    """

    def test_lit_une_ecriture_toleree_placee_apres_une_canonique(self):
        assert list(from_ha_a_ca(pd.Series(["1 ha 13 a 20 ca", "1 a 5 ca"]))) == [11_320, 105]

    def test_lit_une_ecriture_canonique_placee_apres_une_toleree(self):
        assert list(from_ha_a_ca(pd.Series(["1 a 5 ca", "1 ha 13 a 20 ca"]))) == [105, 11_320]

    def test_conserve_l_ordre_quand_les_formes_alternent(self):
        ecrites = pd.Series(["93 ca", "1 a 5 ca", "1 ha 13 a 20 ca", "22 a 97 ca", "5 ha"])
        assert list(from_ha_a_ca(ecrites)) == [93, 105, 11_320, 2297, 50_000]

    def test_ne_decoupe_pas_une_ecriture_qui_ressemble_a_la_forme_canonique(self):
        """« 1 a 4 ca » a la longueur d'une forme canonique sans en être une."""
        assert from_ha_a_ca(pd.Series(["1 a 4 ca"])).iloc[0] == 104

    def test_isole_une_ligne_illisible_entre_deux_canoniques(self):
        ecrites = pd.Series(["93 ca", "abc", "22 a 97 ca"])
        relues = from_ha_a_ca(ecrites, invalide="manquant")
        assert list(relues.isna()) == [False, True, False]
        assert [relues.iloc[0], relues.iloc[2]] == [93, 2297]

    def test_propage_une_valeur_absente_au_milieu_de_canoniques(self):
        relues = from_ha_a_ca(pd.Series(["93 ca", None, "22 a 97 ca"]))
        assert list(relues.isna()) == [False, True, False]
        assert [relues.iloc[0], relues.iloc[2]] == [93, 2297]

    def test_lit_une_colonne_fragmentee_en_plusieurs_morceaux(self):
        """Une colonne issue de read_parquet(dtype_backend='pyarrow') peut être découpée.

        Le mélange des deux chemins de lecture passe alors par ``replace_with_mask``, qui
        refuse un tableau fragmenté : il doit être recollé à l'entrée.
        """
        morceaux = pa.chunked_array([["1 ha 13 a 20 ca", "1 a 5 ca"], ["93 ca"]])
        ecrites = pd.Series(pd.arrays.ArrowExtensionArray(morceaux))

        assert morceaux.num_chunks > 1
        assert list(from_ha_a_ca(ecrites)) == [11_320, 105, 93]

    def test_lit_une_colonne_entierement_canonique(self):
        assert list(from_ha_a_ca(pd.Series(["93 ca", "22 a 97 ca"]))) == [93, 2297]

    def test_lit_une_colonne_sans_aucune_forme_canonique(self):
        assert list(from_ha_a_ca(pd.Series(["1 a 5 ca", "1ha13a20ca"]))) == [105, 11_320]


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

    def test_refuse_une_superficie_negative_sur_une_colonne(self):
        with pytest.raises(SuperficieInvalide, match="négative"):
            to_hectares(pd.Series([-1]))

    def test_refuse_une_negative_qui_s_arrondit_a_zero(self):
        with pytest.raises(SuperficieInvalide, match="négative"):
            to_hectares(pd.Series([-0.49]))

    def test_remplace_une_superficie_negative_sur_demande(self):
        assert pd.isna(to_hectares(-1, invalide="manquant"))

    def test_remplace_une_negative_sur_demande_sur_une_colonne(self):
        hectares = to_hectares(pd.Series([11_320, -1]), invalide="manquant")
        assert hectares.iloc[0] == pytest.approx(1.132)
        assert pd.isna(hectares.iloc[1])

    def test_situe_les_superficies_negatives_dans_le_message(self):
        with pytest.raises(SuperficieInvalide, match="'fautive'"):
            to_hectares(pd.Series([93, -5], index=["ok", "fautive"]))

    def test_refuse_une_valeur_inconnue_pour_l_option_invalide(self):
        with pytest.raises(ValueError, match="ignorer"):
            to_hectares(93, invalide="ignorer")

    def test_propage_une_valeur_absente(self):
        assert pd.isna(to_hectares(pd.Series([100, None])).iloc[1])


class TestAllerRetour:
    """Toute écriture produite doit être relisible à l'identique."""

    @pytest.mark.parametrize(("metres_carres", "_ecriture"), ECRITURES)
    def test_relire_ce_qui_vient_d_etre_ecrit_redonne_la_superficie(self, metres_carres, _ecriture):
        assert from_ha_a_ca(to_ha_a_ca(metres_carres)) == metres_carres

    @pytest.mark.parametrize(("ecriture", "metres_carres"), ECRITURES_TOLEREES)
    def test_une_ecriture_toleree_se_recanonise(self, ecriture, metres_carres):
        """Relire puis réécrire une écriture tolérée doit donner la forme canonique."""
        assert to_ha_a_ca(from_ha_a_ca(ecriture)) == to_ha_a_ca(metres_carres)

    @pytest.mark.parametrize(("ecriture", "metres_carres"), ECRITURES_TOLEREES)
    def test_la_recanonisation_tient_sur_une_colonne(self, ecriture, metres_carres):
        relues = from_ha_a_ca(pd.Series([ecriture]))
        assert to_ha_a_ca(relues).iloc[0] == to_ha_a_ca(metres_carres)

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

    def test_refuse_une_colonne_d_objets_qui_ne_contient_pas_de_texte(self):
        """Une colonne object porte n'importe quoi : son contenu réel décide."""
        with pytest.raises(TypeError, match="des chaînes"):
            from_ha_a_ca(pd.Series([93], dtype=object))

    def test_refuse_une_colonne_de_booleens(self):
        """True vaut 1 pour pandas, qui la tient donc pour numérique."""
        with pytest.raises(TypeError, match="des nombres"):
            to_ha_a_ca(pd.Series([True, False]))

    @pytest.mark.parametrize(
        ("valeur", "attendu"),
        [(np.int64(11_320), "1 ha 13 a 20 ca"), (np.float64(11_320.0), "1 ha 13 a 20 ca")],
    )
    def test_accepte_un_scalaire_numpy(self, valeur, attendu):
        """Une valeur tirée d'un tableau numpy mesure aussi bien qu'un int Python."""
        assert to_ha_a_ca(valeur) == attendu

    def test_refuse_un_booleen_numpy(self):
        with pytest.raises(TypeError):
            to_ha_a_ca(np.True_)

    def test_refuse_une_valeur_inconnue_pour_l_option_invalide(self):
        with pytest.raises(ValueError, match="ignorer"):
            to_ha_a_ca(93, invalide="ignorer")

    def test_refuse_une_valeur_inconnue_pour_l_option_invalide_a_la_lecture(self):
        with pytest.raises(ValueError, match="ignorer"):
            from_ha_a_ca("93 ca", invalide="ignorer")

    @pytest.mark.parametrize("ecriture", ["9\xa0ca", "9\x0bca"])
    def test_refuse_les_blancs_hors_de_la_classe_ecrite_en_clair(self, ecriture):
        """Le ``\\s`` de Python couvre l'espace insécable et la tabulation verticale.

        Celui de RE2 non. Les blancs admis sont donc écrits en clair, pour que les deux
        chemins refusent les mêmes écritures au lieu de diverger silencieusement.
        """
        with pytest.raises(SuperficieInvalide):
            from_ha_a_ca(ecriture)
        with pytest.raises(SuperficieInvalide):
            from_ha_a_ca(pd.Series([ecriture]))

    @pytest.mark.parametrize("ecriture", ["9 ca\n", "\t9 ca", "9 ca "])
    def test_lit_les_blancs_de_la_classe_de_la_meme_facon_des_deux_cotes(self, ecriture):
        assert from_ha_a_ca(ecriture) == 9
        assert from_ha_a_ca(pd.Series([ecriture])).iloc[0] == 9
