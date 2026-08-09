"""Format d'un code Insee de commune : motif, découpe et arrondissements.

Un code Insee de commune tient sur cinq caractères : un code département suivi d'un
code commune. La coupure n'est pas toujours au même endroit :

- **métropole** — département sur 2 caractères, commune sur 3 (``78048`` → ``78`` + ``048``).
  La Corse fait exception dans l'alphabet, pas dans la longueur : ``2A004``, ``2B033``.
- **outre-mer** — départements 97x et 98x, donc 3 caractères, et commune sur 2
  (``97215`` → ``972`` + ``15``).

Trois communes sont découpées en arrondissements municipaux, qui portent leur propre
code Insee. ``75107`` désigne le 7ᵉ arrondissement de Paris, dont la commune est
``75056``.

**C'est le code d'arrondissement, et non celui de la commune, que porte une référence
cadastrale.** La parcelle du pilier Ouest de la tour Eiffel est ``75107000CR0002`` : son
champ insee vaut ``75107``, jamais ``75056``. Aucune parcelle parisienne ne porte
``75056``. Il en va de même à Lyon (``69123``) et à Marseille (``13055``).
"""

LONGUEUR_INSEE = 5

#: Code Insee de commune, **sans ancrage**, pour être inséré dans un motif plus large.
#: Source unique de la forme d'un code Insee : toute règle sur les départements — la
#: Corse en particulier — s'écrit ici et nulle part ailleurs.
FRAGMENT_INSEE = r"(?:[0-9]{2}|2[AB])[0-9]{3}"

MOTIF_INSEE = rf"^{FRAGMENT_INSEE}$"

#: Code département seul : 2 chiffres, ``2A`` / ``2B`` en Corse, 3 chiffres outre-mer.
MOTIF_DEPARTEMENT = r"^(?:9[78][0-9]|2[AB]|[0-9]{2})$"

FORMAT_DEPARTEMENT_ATTENDU = (
    "un code département : 2 chiffres, 2A ou 2B en Corse, 3 chiffres en outre-mer"
)

FORMAT_ATTENDU = (
    "un code Insee de commune sur 5 caractères : 2 chiffres de département "
    "(ou 2A / 2B en Corse, ou 3 chiffres en outre-mer) suivis du code commune"
)

#: Préfixes des départements dont le code tient sur trois caractères.
PREFIXES_OUTRE_MER = ("97", "98")

LONGUEUR_DEPARTEMENT_METROPOLE = 2
LONGUEUR_DEPARTEMENT_OUTRE_MER = 3


def _arrondissements(prefixe: str, premier: int, dernier: int) -> tuple[str, ...]:
    """Énumère les codes Insee des arrondissements d'une commune."""
    return tuple(f"{prefixe}{numero:02d}" for numero in range(premier, dernier + 1))


# Codes vérifiés au Code officiel géographique de l'Insee : 20 arrondissements à Paris
# (75101-75120), 9 à Lyon (69381-69389), 16 à Marseille (13201-13216).
ARRONDISSEMENTS_PARIS = _arrondissements("751", 1, 20)
ARRONDISSEMENTS_LYON = _arrondissements("693", 81, 89)
ARRONDISSEMENTS_MARSEILLE = _arrondissements("132", 1, 16)

#: Code Insee **réel** de la commune, par jeu d'arrondissements.
#:
#: Ce sont les codes du répertoire Insee, et non ceux du v1, qui associait à Paris et à
#: Lyon des codes synthétiques (75100, 69300) absents du répertoire. Un code
#: d'arrondissement se ramène donc ici à la commune qui existe vraiment.
COMMUNES_A_ARRONDISSEMENTS = {
    "75056": ARRONDISSEMENTS_PARIS,
    "69123": ARRONDISSEMENTS_LYON,
    "13055": ARRONDISSEMENTS_MARSEILLE,
}

#: Valeur du code arrondissement pour une commune qui n'en a pas.
ARRONDISSEMENT_ABSENT = "000"

#: Position du code arrondissement dans le code Insee : ``75104`` → ``104``.
BORNES_ARRONDISSEMENT = (2, 5)
