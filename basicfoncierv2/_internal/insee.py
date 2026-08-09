"""Format d'un code Insee de commune : motif, découpe et arrondissements.

Un code Insee de commune tient sur cinq caractères : un code département suivi d'un
code commune. La coupure n'est pas toujours au même endroit :

- **métropole** — département sur 2 caractères, commune sur 3 (``78048`` → ``78`` + ``048``).
  La Corse fait exception dans l'alphabet, pas dans la longueur : ``2A004``, ``2B033``.
- **outre-mer** — départements 97x et 98x, donc 3 caractères, et commune sur 2
  (``97215`` → ``972`` + ``15``).

Trois communes sont découpées en arrondissements municipaux, qui portent leur propre
code Insee. ``75104`` désigne le 4ᵉ arrondissement de Paris.
"""

LONGUEUR_INSEE = 5

MOTIF_INSEE = r"^(?:[0-9]{2}|2[AB])[0-9]{3}$"

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


ARRONDISSEMENTS_PARIS = _arrondissements("751", 1, 20)
ARRONDISSEMENTS_LYON = _arrondissements("693", 81, 89)
ARRONDISSEMENTS_MARSEILLE = _arrondissements("132", 1, 16)

#: Code Insee retenu pour la commune, par jeu d'arrondissements.
#:
#: .. warning::
#:    Ces trois valeurs sont **reprises telles quelles de basicfoncier v1**, y compris
#:    son incohérence : Marseille reçoit son code Insee réel (13055) tandis que Paris
#:    et Lyon reçoivent des codes synthétiques (75100, 69300) au lieu de leurs codes
#:    réels (75056, 69123). Les changer romprait les traitements existants ; la
#:    question est posée dans ``docs/BUGS.md``.
COMMUNES_A_ARRONDISSEMENTS = {
    "75100": ARRONDISSEMENTS_PARIS,
    "69300": ARRONDISSEMENTS_LYON,
    "13055": ARRONDISSEMENTS_MARSEILLE,
}

#: Valeur du code arrondissement pour une commune qui n'en a pas.
ARRONDISSEMENT_ABSENT = "000"

#: Position du code arrondissement dans le code Insee : ``75104`` → ``104``.
BORNES_ARRONDISSEMENT = (2, 5)
