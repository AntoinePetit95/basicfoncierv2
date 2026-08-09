# CLAUDE.md — basicfoncierv2

> Section **Socle EF** : identique sur tous les projets Energie Foncière. Ne pas modifier localement.

---

## 1. Le projet

Bibliothèque Python de manipulation de références cadastrales et de superficies foncières, consommée par les scripts EF qui traitent des fichiers cadastraux (DGFiP, MAJIC, fichiers fonciers). Elle succède à `basicfoncier` (dépôt GitHub public, en production ; **jamais publié sur PyPI** — vérifié le 2026-08-09, l'index renvoie 404) avec trois objectifs : API plus simple, tests intégrés, exécution vectorisée sur colonnes entières de DataFrame pandas.

**Statut actuel :** les trois modules publics — `ref_cadastrale`, `superficie`, `commune` — sont écrits et testés ; la parité fonctionnelle avec le v1 est atteinte. Le paquet n'est pas encore publié : version `0.0.1`, dépôt privé.

**`basicfoncier` v1 est intouchable** : publié et utilisé par d'autres programmes. Aucune modification, aucune republication. La compatibilité se traite par [docs/MIGRATION.md](docs/MIGRATION.md), jamais en modifiant le v1.

---

## 2. Vocabulaire métier

→ [docs/VOCABULAIRE.md](docs/VOCABULAIRE.md). À lire avant toute tâche touchant les références cadastrales : `idu`, `id court`, `commune absorbée`, `section`, `Alsace-Moselle`, `ha/a/ca` ont un sens précis et non devinable.

---

## 3. Stack et structure

**Runtime :** Python ≥ 3.12 · **Exécution :** pandas, numpy, pyarrow · **Dev :** pytest, ruff
**Base de données :** aucune · **Paquets :** pip + `pyproject.toml`

```
basicfoncierv2/   ref_cadastrale.py · superficie.py · commune.py
  _internal/      implémentations vectorisées, non publiques
tests/            un fichier de test par module du paquet
benchmarks/       mesures de débit, critère de succès des tâches « vitesse »
docs/             JOURNAL · BUGS · DECISIONS · MIGRATION · VOCABULAIRE
```

---

## 4. Commandes qui font foi

| Objectif | Commande |
|---|---|
| Lancer les tests | `pytest` |
| Tests d'un seul fichier | `pytest tests/test_ref_cadastrale.py` |
| Lint | `ruff check .` |
| Format | `ruff format .` |
| Vérification de types | *aucune pour l'instant* |
| Build | `python -m build` |
| Benchmarks | `python -m benchmarks` |

Utilise ces commandes, pas d'autres. Si l'une échoue pour une raison d'environnement, signale-le, ne la contourne pas.

---

## 5. Zones sensibles

- **Dépôt `basicfoncier` v1** (`C:/Users/antoi/PycharmProjects/basicfoncier`) : lecture seule absolue.
- **Signatures publiques** après la première publication : toute rupture casse les consommateurs.
- **`docs/MIGRATION.md`** : une fonction publique ajoutée, renommée ou supprimée sans mise à jour de ce fichier est une tâche non terminée.

**Dette technique assumée :** aucune. Les défauts du v1 ne sont pas repris — voir [docs/BUGS.md](docs/BUGS.md).

---

## 6. Interdits sans validation explicite

- Migrations de base de données et modification de schéma
- Suppression de fichiers ou de données
- `git push`, création de tags, toute action sur une branche partagée
- Ajout d'une dépendance externe
- Toute écriture vers un environnement autre que local
- Manipulation de secrets, clés, variables d'environnement de production
- Toute écriture dans le dépôt `basicfoncier` v1
- Publication sur PyPI, sous toute forme : elle reste manuelle et humaine
- Modification du numéro de version, du nom du paquet ou des bornes de dépendances
- Modification de la signature d'une fonction publique après la première publication

---

# SOCLE EF

> Bloc commun à tous les projets Energie Foncière. Recopié tel quel, jamais reformulé.

## 7. Protocole de travail

Le travail se déroule en trois temps. Ne passe jamais au suivant sans avoir terminé le précédent.

### 7.1 — Cadrage

À la réception d'une demande, **avant toute écriture** :

1. Lis le code concerné. Ne suppose rien de ce que tu peux vérifier.
2. Consulte `docs/BUGS.md` et `docs/DECISIONS.md` : la demande touche peut-être un problème connu ou un choix déjà tranché.
3. Rassemble **toutes** tes zones d'incertitude et pose-les **en un seul message**, avec ta recommandation par défaut pour chacune.
4. Si tu n'as aucune question, dis-le et passe au plan.

Une question posée au milieu de l'exécution est un échec de cadrage. Anticipe : ce qui est ambigu maintenant le sera encore dans vingt minutes.

### 7.2 — Plan

Produis un plan avant d'exécuter. Le plan doit contenir :

- l'objectif reformulé en une phrase
- les fichiers que tu vas créer ou modifier, et ce que chacun devient
- **le critère de succès vérifiable** : quelle commande, lancée à la fin, prouve que c'est fait
- ce que tu ne feras pas, et pourquoi
- les risques identifiés

Le plan est le point de contrôle humain. Il doit être relisible en deux minutes : c'est là que se rattrapent les erreurs d'architecture, pas dans la relecture du diff.

### 7.3 — Exécution autonome

Une fois le plan validé, travaille **jusqu'au bout sans interruption**. Tu ne rends la main que dans quatre cas :

| Situation | Action |
|---|---|
| C'est terminé et vérifié | Tu rends le résultat |
| Une hypothèse du plan s'avère fausse | Tu t'arrêtes, tu expliques, tu proposes une révision du plan |
| Tu dois franchir un interdit de la section 6 | Tu t'arrêtes et tu demandes |
| Trois tentatives ont échoué sur le même point | Tu t'arrêtes et tu exposes ce que tu as essayé |

En dehors de ces quatre cas : continue. Ne demande pas de confirmation intermédiaire, ne demande pas si tu peux poursuivre, n'annonce pas ce que tu vas faire — fais-le.

**Une tâche n'est jamais terminée tant que tu n'as pas lancé toi-même le critère de succès et constaté qu'il passe.** « Ça devrait marcher » n'est pas un résultat.

---

## 8. Règles de code

### 8.1 — Élémentarité

**Une fonction, un rôle.** Si la description de ce que fait une fonction contient « et », c'est deux fonctions.

- Une fonction tient dans un écran. Au-delà, découpe.
- Un niveau d'abstraction par fonction : ne mélange pas orchestration et détail d'implémentation.
- Nommage explicite plutôt que court. Le nom doit dire le rôle, pas l'implémentation.
- Pas d'astuce. Le code élémentaire est ennuyeux à lire ; c'est la qualité recherchée.

### 8.2 — Code auto-vérifiant

Chaque fonction valide ce qu'elle reçoit et ce qu'elle produit.

- **En entrée :** vérifie les préconditions — types, bornes, présence, cohérence entre arguments. Échoue immédiatement et avec un message qui nomme la valeur fautive.
- **En sortie :** vérifie les postconditions — invariants que le résultat doit respecter par construction.
- **Distingue deux natures de vérification :**
  - *Contrat interne* (une erreur ici est un bug de programmation) → assertion.
  - *Donnée externe* (entrée utilisateur, réponse d'API, contenu de fichier, ligne de base) → validation explicite qui lève une erreur métier. **Jamais une assertion :** les assertions peuvent être désactivées à l'exécution, et une donnée externe invalide n'est pas un bug, c'est un cas nominal.
- Un message d'erreur doit permettre de diagnostiquer sans ouvrir un débogueur : quoi était attendu, quoi a été reçu, où.
- N'assertionne pas ce que le système de types garantit déjà.

### 8.3 — Tests

**Chaque unité de code livrée est accompagnée de ses tests.** Pas de code sans test dans la même tâche.

Pour chaque fonction, au minimum :
- le cas nominal
- les cas limites (vide, zéro, un seul élément, maximum)
- les cas d'erreur attendus, avec vérification que la bonne erreur est levée

Règles :
- Un test échoue pour une seule raison. Un test qui vérifie cinq choses est cinq tests.
- Le nom du test décrit le comportement attendu, pas la fonction appelée.
- Pas de test dépendant de l'ordre d'exécution, de l'horloge, du réseau ou d'un état résiduel.
- Un bug corrigé donne d'abord un test qui reproduit le bug, ensuite la correction. Jamais l'inverse.
- Ne modifie jamais un test pour le faire passer. Si un test existant échoue, soit le code est faux, soit le test l'est — tranche et dis lequel.

---

## 9. Journal, bugs, décisions

Trois fichiers, trois usages. **Ce `CLAUDE.md` n'en fait partie d'aucun** : il ne s'allonge pas au fil des tâches.

### `docs/JOURNAL.md`

À écrire **à la fin de chaque tâche terminée**, en tête de fichier (antichronologique) :

```markdown
## AAAA-MM-JJ — {titre en une ligne}
**Demande :** {ce qui était demandé, une phrase}
**Fait :** {ce qui a changé, 1 à 3 puces}
**Fichiers :** {liste}
**Vérifié par :** {commande lancée + résultat}
**À savoir :** {ce qu'un futur intervenant doit savoir — souvent vide}
```

Cinq lignes suffisent. Le journal n'est pas un rapport, c'est un fil de reprise.
Au-delà de 300 lignes, condense les entrées de plus de trois mois en un résumé mensuel de trois lignes.

### `docs/BUGS.md`

Deux sections : **Ouverts** et **Résolus**.

Un bug ouvert est détaillé — symptôme, reproduction, piste, contournement en place.
Un bug résolu est **réduit à une seule ligne** dès la correction :

```markdown
- {AAAA-MM-JJ} {symptôme en cinq mots} → corrigé dans {fichier} ({test de non-régression})
```

Le détail disparaît avec le bug : il ne sert plus qu'à alourdir la lecture. Ce qui compte est qu'il ait existé et qu'un test le garde fermé.
Purge les résolus de plus de six mois.

### `docs/DECISIONS.md`

Une entrée uniquement quand un choix engage la suite du projet — pas pour chaque tâche.

```markdown
## {AAAA-MM-JJ} — {décision en une ligne}
**Contexte :** {le problème}
**Retenu :** {l'option choisie}
**Écarté :** {les options rejetées et pourquoi}
```

Avant de proposer une architecture, relis ce fichier : la question a peut-être déjà été tranchée.

---

## 10. Git

Git est le filet de sécurité du mode autonome : c'est ce qui rend une tâche ratée annulable en une commande. Les règles ci-dessous sont impératives.

### 10.1 — Branches

- `main` est toujours dans un état fonctionnel. **Aucun commit direct sur `main`, jamais.**
- Une tâche = une branche, créée par toi au début de l'exécution, à partir d'un `main` à jour.
- Nommage : `feat/{sujet-court}`, `fix/{sujet-court}`, `chore/{sujet-court}`, `refac/{sujet-court}`. En minuscules, avec des tirets, trois ou quatre mots maximum.
- Annonce le nom de la branche dans le plan.
- Si la tâche est abandonnée, la branche est simplement supprimée : rien n'a été touché ailleurs.

### 10.2 — Commits

- Un commit = une modification cohérente qui laisse le code dans un état valide. Ni un commit par fichier, ni un commit pour toute la tâche.
- Ne commite jamais du code dont les tests échouent, sauf à l'écrire explicitement dans le message.
- Format du message :

```
{type}: {ce que fait le commit, à l'infinitif, une ligne}

{pourquoi, si ce n'est pas évident — deux lignes maximum}
```

`type` ∈ `feat`, `fix`, `refac`, `test`, `docs`, `chore`.
Exemple : `fix: rejeter les surfaces de parcelle négatives à la saisie`

- Le message dit **ce que fait le commit**, pas ce que tu as fait pendant. Pas de « suite des modifications », pas de « wip ».

### 10.3 — Interdits git

Ces actions demandent une validation humaine explicite, sans exception :

- `git push` sous toutes ses formes
- toute fusion vers `main`
- `git rebase`, `git reset --hard`, `git commit --amend` sur des commits qui ne sont pas les tiens dans cette tâche
- `git checkout .`, `git clean`, ou toute commande qui détruit du travail non commité
- la suppression d'une branche autre que celle que tu viens de créer
- l'ajout d'un fichier de plus de 5 Mo

**Avant toute commande git destructrice, vérifie qu'il n'y a pas de travail non commité** (`git status`) et signale-le plutôt que de l'écraser.

### 10.4 — Ce qui ne doit jamais entrer dans le dépôt

Secrets, clés d'API, mots de passe, fichiers `.env`, dumps de base, données personnelles réelles, fichiers générés (build, dépendances, caches).

Si le `.gitignore` ne les couvre pas, corrige-le **avant** de commiter et signale-le. Un secret commité reste dans l'historique même après suppression : traite-le comme un incident, arrête-toi et préviens.

### 10.5 — Fin de tâche

Quand la tâche est terminée et vérifiée :

1. Tous les changements sont commités sur la branche.
2. Tu rends la main en indiquant : le nom de la branche, la liste des commits, la commande de vérification et son résultat.
3. Tu ne fusionnes pas. Tu ne pousses pas. C'est la décision de l'humain.

---

## 11. Réflexes

- Vérifie plutôt que supposer : ouvre le fichier, lance la commande.
- Si une demande est incohérente avec le code existant, dis-le avant d'exécuter.
- Si tu constates un problème hors périmètre, note-le dans `docs/BUGS.md` et continue ta tâche. Ne l'élargis pas.
- Si tu ne sais pas, dis que tu ne sais pas. Ne produis pas de code plausible pour combler un trou.
