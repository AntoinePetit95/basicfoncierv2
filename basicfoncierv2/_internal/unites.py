"""Format d'une superficie foncière : unités et motif de lecture.

Une superficie s'écrit ``12 ha 34 a 56 ca`` — hectares, ares, centiares.
1 ha vaut 10 000 m², 1 a vaut 100 m², 1 ca vaut 1 m².

Les composantes de tête sont omises tant qu'elles sont nulles : ``22 a 97 ca``,
``93 ca``. Dès qu'une composante supérieure est écrite, les suivantes le sont sur
deux chiffres — mais la lecture accepte aussi les formes non complétées, que
``basicfoncier`` v1 interprétait faussement.

Le motif est écrit en groupes nommés, tous facultatifs, pour être compris à
l'identique par le moteur RE2 de PyArrow et par le module ``re``. Les ares et les
centiares y sont bornés à deux chiffres : au-delà, la valeur relève de l'unité
supérieure et la chaîne est malformée.
"""

METRES_CARRES_PAR_HECTARE = 10_000
METRES_CARRES_PAR_ARE = 100

MOTIF_HA_A_CA = (
    r"^\s*(?:(?P<ha>[0-9]+)\s*ha\s*)?"
    r"(?:(?P<a>[0-9]{1,2})\s*a\s*)?"
    r"(?:(?P<ca>[0-9]{1,2})\s*ca)?\s*$"
)

#: Écriture canonique — celle que produit la bibliothèque : espaces uniques, et
#: composantes complétées sur deux chiffres dès qu'une composante supérieure est écrite.
#: Ne sert qu'à reconnaître, pas à extraire : une écriture reconnue se découpe à
#: positions fixes, ce qui évite le motif tolérant, bien plus coûteux.
MOTIF_HA_A_CA_CANONIQUE = r"^(?:[0-9]+ ha [0-9]{2} a [0-9]{2}|[0-9]{1,2} a [0-9]{2}|[0-9]{1,2}) ca$"

# Une écriture canonique se lit depuis la fin, ses composantes basses étant de
# largeur fixe. Trois formes seulement, que la longueur suffit à distinguer :
#
#     93 ca              longueur 4 ou 5     — centiares seuls
#     22 a 97 ca         longueur 9 ou 10    — pas d'hectares
#     1 ha 13 a 20 ca    longueur 15 ou plus — forme complète
#
# Aucune écriture canonique ne tombe entre ces plages.
LONGUEUR_MAX_CENTIARES_SEULS = 5
LONGUEUR_MAX_SANS_HECTARES = 10

#: Bornes de découpe, comptées depuis la fin de la chaîne.
FIN_CENTIARES_SEULS = -3
BORNES_CENTIARES = (-5, -3)
FIN_ARES_SANS_HECTARES = -8
BORNES_ARES = (-10, -8)
FIN_HECTARES = -14

COMPOSANTES = ("ha", "a", "ca")

FACTEURS = {
    "ha": METRES_CARRES_PAR_HECTARE,
    "a": METRES_CARRES_PAR_ARE,
    "ca": 1,
}

FORMAT_ATTENDU = (
    "une superficie écrite « 12 ha 34 a 56 ca », dont les composantes de tête peuvent "
    "être omises ; les ares et les centiares tiennent sur deux chiffres au plus"
)
