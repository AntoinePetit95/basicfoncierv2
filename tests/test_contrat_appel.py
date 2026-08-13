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
from basicfoncier._internal.insee import FORMAT_ATTENDU as FORMAT_INSEE
from basicfoncier._internal.motifs import FORMAT_ATTENDU as FORMAT_REFERENCE
from basicfoncier._internal.unites import FORMAT_ATTENDU as FORMAT_SUPERFICIE

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
        """La clause « Reçu : … » doit citer chaque champ avec le type reçu.

        Contraint sur la clause elle-même : ``match="Series"`` serait satisfait par la
        phrase d'exigence, qui contient déjà « pandas.Series », sans jamais atteindre ce
        que ce test prétend éprouver.
        """
        melange = (pd.Series([champs[0]]), *champs[1:])
        with pytest.raises(TypeError) as leve:
            fonction(*melange)

        message = str(leve.value)
        assert "Reçu : " in message
        assert "insee=Series" in message or "departement=Series" in message
        assert "=str" in message

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


class TestTexteDesMessages:
    """Les messages d'erreur métier, éprouvés au caractère près.

    La refonte a réuni cinq messages en un patron unique, et lui a donné deux degrés de
    liberté qui n'existaient pas — ``format_attendu`` facultatif et ``tolerance_possible``.
    Une revue a montré par mutation que rien ne les gardait : supprimer la clause
    « Attendu », changer sa ponctuation, retirer le conseil ou intervertir le nombre de
    fautifs et le total laissait la suite entièrement verte.

    Ces tests comparent le message entier, pas un fragment. Ils sont volontairement
    rigides : c'est leur raison d'être. Repassés à la mutation, ils détectent désormais
    les quatre atteintes au patron.

    Une cinquième mutation reste indétectable — inverser l'ordre du dispatch dans
    ``aiguiller`` — et le restera : c'est un mutant **équivalent**. Aucun objet n'est à la
    fois une ``pd.Series`` et une valeur seule admise ; l'ordre des deux tests n'a donc
    aucun effet observable. Vérifié sur 301 formes d'entrée, y compris scalaires numpy,
    tableau à zéro dimension, ``Decimal``, ``Fraction`` et sous-classes des deux types.
    """

    CONSEIL = " Passez invalide='manquant' pour les remplacer par des valeurs manquantes."

    def _message(self, appel) -> str:
        # La classe d'erreur varie d'une famille à l'autre ; ce qui est éprouvé ici est le
        # texte du message, que chaque test compare ensuite en entier.
        with pytest.raises(Exception) as leve:
            appel()
        return str(leve.value)

    def test_code_insee_invalide(self):
        """Le message entier, assemblé à partir du seul format attendu.

        Le texte du format vient de la bibliothèque : ce qui est éprouvé ici est le
        **patron** — l'ordre des trois clauses, leurs séparateurs et leur ponctuation —
        et non la formulation du domaine, qui a ses propres tests.
        """
        message = self._message(lambda: commune.to_departement(pd.Series(["78048", "fautif"])))
        assert message == (
            f"1 code(s) Insee invalide(s) sur 2. Attendu : {FORMAT_INSEE}. "
            f"Reçu, aux positions [1] : ['fautif'].{self.CONSEIL}"
        )

    def test_code_departement_invalide_ne_conseille_pas_l_option(self):
        """``insee_from_parts`` n'a pas d'option ``invalide`` : la conseiller enverrait
        l'appelant dans le mur."""
        message = self._message(
            lambda: commune.insee_from_parts(pd.Series(["7X"]), pd.Series(["048"]))
        )
        assert message.startswith("1 code(s) département invalide(s) sur 1. Attendu : ")
        assert message.endswith("Reçu, aux positions [0] : ['7X'].")
        assert "invalide='manquant'" not in message

    def test_reference_cadastrale_invalide(self):
        message = self._message(
            lambda: ref_cadastrale.to_parts(pd.Series(["78048000AB0011", "fautive"]))
        )
        assert message == (
            f"1 référence(s) cadastrale(s) invalide(s) sur 2. Attendu : {FORMAT_REFERENCE}. "
            f"Reçu, aux positions [1] : ['fautive'].{self.CONSEIL}"
        )

    def test_superficie_negative_ne_rappelle_aucun_format(self):
        """Une superficie négative est fautive par son signe, pas par sa forme."""
        message = self._message(lambda: superficie.to_hectares(pd.Series([100, -5])))
        assert message == (
            "1 superficie(s) négative(s) sur 2. Reçu, aux positions [1] : [-5]." + self.CONSEIL
        )
        assert "Attendu" not in message

    def test_superficie_illisible(self):
        message = self._message(
            lambda: superficie.from_ha_a_ca(pd.Series(["1 ha 13 a 20 ca", "fautive"]))
        )
        assert message == (
            f"1 superficie(s) illisible(s) sur 2. Attendu : {FORMAT_SUPERFICIE}. "
            f"Reçu, aux positions [1] : ['fautive'].{self.CONSEIL}"
        )

    def test_le_compte_precede_le_total(self):
        """Deux nombres se suivent dans la phrase ; les intervertir la rendrait fausse
        sans qu'aucun test de sous-chaîne ne s'en aperçoive."""
        message = self._message(lambda: commune.to_departement(pd.Series(["a", "b", "c", "78048"])))
        assert message.startswith("3 code(s) Insee invalide(s) sur 4.")

    def test_au_plus_cinq_exemples_sont_cites(self):
        message = self._message(lambda: commune.to_departement(pd.Series(["x"] * 9)))
        assert message.startswith("9 code(s) Insee invalide(s) sur 9.")
        assert "positions [0, 1, 2, 3, 4] :" in message
