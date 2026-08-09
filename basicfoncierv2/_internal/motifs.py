"""Format d'une référence cadastrale : motifs et dimensions, source unique de vérité.

Une référence se décompose toujours dans le même ordre :
``insee (5) + commune absorbée (3) + section (2) + numéro (4)``.

Deux régimes coexistent :

- **général** — la section se termine par une lettre, ce qui permet de la distinguer
  du numéro. La commune absorbée peut être omise, et chaque champ peut être privé de
  ses zéros de remplissage : c'est la forme courte, usuelle en saisie humaine.
- **Alsace-Moselle** (départements 57, 67, 68) — les sections y sont entièrement
  numériques. Plus rien ne sépare visuellement la section du numéro : seule la forme
  longue, 14 chiffres exactement, est acceptable. Une forme courte y serait ambiguë,
  elle est donc rejetée.

Les motifs sont écrits en groupes nommés et sans classes raccourcies (``\\d``) afin
d'être compris à l'identique par le moteur RE2 de PyArrow et par le module ``re``.
"""

DEPARTEMENTS_ALSACE_MOSELLE = ("57", "67", "68")

CHAMPS = ("insee", "com_abs", "section", "numero")

LARGEURS = {"insee": 5, "com_abs": 3, "section": 2, "numero": 4}

MOTIF_GENERAL = (
    r"^(?P<insee>[0-9]{5})"
    r"(?P<com_abs>[0-9]{3})?"
    r"(?P<section>[0-9A-Za-z]?[A-Za-z])"
    r"(?P<numero>[0-9]{1,4})$"
)

MOTIF_ALSACE_MOSELLE = (
    r"^(?P<insee>[0-9]{5})"
    r"(?P<com_abs>[0-9]{3})"
    r"(?P<section>[0-9]{2})"
    r"(?P<numero>[0-9]{4})$"
)

FORMAT_ATTENDU = (
    "insee (5 chiffres) + commune absorbée (3 chiffres, facultative) + "
    "section (1 ou 2 caractères se terminant par une lettre) + numéro (1 à 4 chiffres) ; "
    "en Alsace-Moselle (départements 57, 67, 68) : exactement 14 chiffres"
)


def est_alsace_moselle(ref: str) -> bool:
    """Indique si une référence relève du régime Alsace-Moselle.

    :param ref: une référence cadastrale
    :return: vrai si le département est 57, 67 ou 68
    """
    return ref[:2] in DEPARTEMENTS_ALSACE_MOSELLE
