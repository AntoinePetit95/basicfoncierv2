"""Le contrat d'appel, éprouvé sur les douze fonctions publiques d'un coup.

Chaque famille avait jusqu'ici sa propre classe de contrat, et chacune n'éprouvait
qu'une partie de ses fonctions. Le contrat étant désormais tenu en un seul endroit —
``_internal/appel.py`` —, il se vérifie en un seul endroit, sur **toutes** les fonctions
publiques : une nouvelle fonction ajoutée à l'une des listes ci-dessous est aussitôt
soumise aux mêmes exigences.

Les classes de contrat propres à chaque famille restent en place : elles éprouvent des
règles de domaine que ce fichier ne connaît pas.
"""

from __future__ import annotations

import pandas as pd
import pytest

from basicfoncier import commune, ref_cadastrale, superficie

#: Fonctions à un argument prenant une valeur seule ou une colonne, plus l'option
#: ``invalide``. Pour chacune : une entrée valide en texte, et la même en colonne.
A_UN_ARGUMENT = [
    pytest.param(commune.to_departement, "78048", id="to_departement"),
    pytest.param(commune.to_code_commune, "78048", id="to_code_commune"),
    pytest.param(commune.to_commune_et_arrondissement, "75107", id="to_commune_et_arrondissement"),
    pytest.param(ref_cadastrale.to_idu, "78048000AB0011", id="to_idu"),
    pytest.param(ref_cadastrale.to_short_id, "78048000AB0011", id="to_short_id"),
    pytest.param(ref_cadastrale.to_parts, "78048000AB0011", id="to_parts"),
    pytest.param(superficie.from_ha_a_ca, "1 ha 13 a 20 ca", id="from_ha_a_ca"),
]

#: Mêmes règles, mais la valeur seule y est un nombre et non du texte.
A_UN_ARGUMENT_NUMERIQUE = [
    pytest.param(superficie.to_hectares, 11320, id="to_hectares"),
    pytest.param(superficie.to_ha_a_ca, 11320, id="to_ha_a_ca"),
]

#: Fonctions d'assemblage : plusieurs champs, tous de même nature, sans option ``invalide``.
ASSEMBLAGES = [
    pytest.param(commune.insee_from_parts, ("78", "048"), id="insee_from_parts"),
    pytest.param(
        ref_cadastrale.idu_from_parts, ("78048", "000", "AB", "0011"), id="idu_from_parts"
    ),
    pytest.param(
        ref_cadastrale.short_id_from_parts, ("78048", "000", "AB", "0011"), id="short_id_from_parts"
    ),
]

TOUTES_A_UN_ARGUMENT = A_UN_ARGUMENT + A_UN_ARGUMENT_NUMERIQUE


class TestOptionInvalide:
    """L'option ``invalide`` n'accepte que deux valeurs, sur toutes les fonctions."""

    @pytest.mark.parametrize(("fonction", "valide"), TOUTES_A_UN_ARGUMENT)
    def test_refuse_une_option_inconnue_sur_une_valeur_seule(self, fonction, valide):
        with pytest.raises(ValueError, match="ignorer"):
            fonction(valide, invalide="ignorer")

    @pytest.mark.parametrize(("fonction", "valide"), TOUTES_A_UN_ARGUMENT)
    def test_refuse_une_option_inconnue_sur_une_colonne(self, fonction, valide):
        with pytest.raises(ValueError, match="ignorer"):
            fonction(pd.Series([valide]), invalide="ignorer")

    @pytest.mark.parametrize(("fonction", "valide"), TOUTES_A_UN_ARGUMENT)
    def test_refuse_l_option_avant_de_regarder_la_donnee(self, fonction, valide):
        """Une option fautive est signalée même quand la donnée l'est aussi.

        L'ordre compte : c'est l'appel qui est mal écrit, pas la donnée qui est mauvaise.
        """
        with pytest.raises(ValueError, match="ignorer"):
            fonction(pd.Series(["\x00 jamais valide"]), invalide="ignorer")


class TestNatureDeLEntree:
    """Une entrée qui n'est ni une valeur seule ni une colonne est refusée."""

    @pytest.mark.parametrize(("fonction", "valide"), TOUTES_A_UN_ARGUMENT)
    @pytest.mark.parametrize(
        "entree",
        [
            pytest.param(["78048"], id="liste"),
            pytest.param(("78048",), id="tuple"),
            pytest.param({"code": "78048"}, id="dict"),
            pytest.param(None, id="None"),
            pytest.param(object(), id="objet"),
        ],
    )
    def test_refuse_ce_qui_n_est_ni_valeur_seule_ni_colonne(self, fonction, valide, entree):
        del valide
        with pytest.raises(TypeError):
            fonction(entree)

    @pytest.mark.parametrize(("fonction", "valide"), TOUTES_A_UN_ARGUMENT)
    def test_le_message_nomme_le_type_recu(self, fonction, valide):
        del valide
        with pytest.raises(TypeError, match="list"):
            fonction(["peu importe"])

    @pytest.mark.parametrize(("fonction", "valide"), A_UN_ARGUMENT)
    def test_un_nombre_n_est_pas_du_texte(self, fonction, valide):
        """Les sept fonctions textuelles refusent un nombre nu.

        Un code Insee ou une référence stockés en numérique ont perdu leurs zéros de
        tête : les accepter reviendrait à traiter une donnée déjà fausse.
        """
        del valide
        with pytest.raises(TypeError):
            fonction(78048)

    @pytest.mark.parametrize(("fonction", "valide"), A_UN_ARGUMENT_NUMERIQUE)
    def test_un_booleen_n_est_pas_une_superficie(self, fonction, valide):
        """``True`` vaut 1 pour Python, jamais un mètre carré."""
        del valide
        with pytest.raises(TypeError):
            fonction(True)


class TestGenreDuResultat:
    """Le résultat est du même genre que l'entrée, et garde son index."""

    @pytest.mark.parametrize(("fonction", "valide"), TOUTES_A_UN_ARGUMENT)
    def test_une_colonne_rend_une_colonne(self, fonction, valide):
        resultat = fonction(pd.Series([valide, valide]))
        assert isinstance(resultat, pd.Series | pd.DataFrame)

    @pytest.mark.parametrize(("fonction", "valide"), TOUTES_A_UN_ARGUMENT)
    def test_une_valeur_seule_ne_rend_pas_une_colonne(self, fonction, valide):
        assert not isinstance(fonction(valide), pd.Series | pd.DataFrame)

    @pytest.mark.parametrize(("fonction", "valide"), TOUTES_A_UN_ARGUMENT)
    def test_l_index_est_conserve(self, fonction, valide):
        index = pd.Index([10, 20, 30], name="parcelle")
        resultat = fonction(pd.Series([valide] * 3, index=index))
        pd.testing.assert_index_equal(resultat.index, index)

    @pytest.mark.parametrize(("fonction", "valide"), A_UN_ARGUMENT)
    def test_une_colonne_textuelle_vide_reste_vide(self, fonction, valide):
        del valide
        resultat = fonction(pd.Series([], dtype="object"))
        assert len(resultat) == 0

    @pytest.mark.parametrize(("fonction", "valide"), A_UN_ARGUMENT_NUMERIQUE)
    def test_une_colonne_numerique_vide_reste_vide(self, fonction, valide):
        """Vide, mais numérique : une colonne d'objets n'est pas une colonne de mesures,
        même sans aucune valeur — le type porte l'intention."""
        del valide
        resultat = fonction(pd.Series([], dtype="float64"))
        assert len(resultat) == 0


class TestAssemblages:
    """Les fonctions d'assemblage exigent que tous leurs champs soient de même nature."""

    @pytest.mark.parametrize(("fonction", "champs"), ASSEMBLAGES)
    def test_refuse_un_melange_de_texte_et_de_colonne(self, fonction, champs):
        melange = (pd.Series([champs[0]]), *champs[1:])
        with pytest.raises(TypeError, match=r"pandas\.Series"):
            fonction(*melange)

    @pytest.mark.parametrize(("fonction", "champs"), ASSEMBLAGES)
    def test_le_message_nomme_chaque_champ_et_sa_nature(self, fonction, champs):
        melange = (pd.Series([champs[0]]), *champs[1:])
        with pytest.raises(TypeError, match="Series"):
            fonction(*melange)

    @pytest.mark.parametrize(("fonction", "champs"), ASSEMBLAGES)
    def test_refuse_des_colonnes_mal_alignees(self, fonction, champs):
        premiere = pd.Series([champs[0]], index=[0])
        autres = [pd.Series([valeur], index=[1]) for valeur in champs[1:]]
        with pytest.raises(ValueError, match="alignée"):
            fonction(premiere, *autres)

    @pytest.mark.parametrize(("fonction", "champs"), ASSEMBLAGES)
    def test_assemble_des_textes_en_texte(self, fonction, champs):
        assert isinstance(fonction(*champs), str)

    @pytest.mark.parametrize(("fonction", "champs"), ASSEMBLAGES)
    def test_assemble_des_colonnes_en_colonne(self, fonction, champs):
        colonnes = [pd.Series([valeur]) for valeur in champs]
        assert isinstance(fonction(*colonnes), pd.Series)
