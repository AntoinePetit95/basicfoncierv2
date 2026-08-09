"""Erreurs métier de basicfoncierv2.

Ces erreurs signalent une **donnée externe invalide** — une référence saisie, lue
dans un fichier ou remontée d'une base. Ce n'est pas un bug du programme : c'est un
cas nominal, et il se signale par une exception explicite, jamais par une assertion.
"""


class ReferenceCadastraleInvalide(ValueError):
    """Une référence cadastrale ne respecte aucun format connu."""
