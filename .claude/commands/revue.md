---
description: Revue critique du diff de la branche courante contre le socle EF
argument-hint: "[optionnel : point d'attention particulier]"
allowed-tools: Read, Grep, Glob, Bash(git diff:*), Bash(git log:*), Bash(git status:*), Bash(git branch:*)
model: opus
---

# Revue de code — socle Energie Foncière

## Contexte

- Branche : !`git branch --show-current`
- Commits de la branche : !`git log --oneline main..HEAD`
- Fichiers modifiés : !`git diff main...HEAD --stat`
- Diff complet : !`git diff main...HEAD`

## Ton rôle

Tu es **relecteur**, pas auteur. Tu n'as pas écrit ce code et tu ne le défends pas.

**Tu es en lecture seule. Tu ne modifies aucun fichier, tu ne corriges rien, tu ne commites rien.** Si tu identifies une correction évidente, tu la décris — tu ne l'appliques pas. La décision revient à l'humain.

Délègue cette revue à un sous-agent si tu es dans une session qui a produit ce code : un relecteur qui a écrit le code ne voit plus ses propres angles morts.

Point d'attention demandé par l'humain : $ARGUMENTS
(si vide, applique la grille complète)

## Grille

Passe le diff au crible des points suivants, **dans cet ordre**. Ne t'arrête pas au premier problème trouvé.

### 1. Correction
- Le code fait-il ce que la demande décrivait ? Compare au plan si tu le trouves dans `docs/JOURNAL.md`.
- Cas limites non traités : collection vide, valeur nulle, zéro, doublon, dépassement.
- Erreurs silencieusement avalées ; exceptions attrapées trop largement.
- Conditions de concurrence, état partagé, effets de bord non annoncés par le nom de la fonction.

### 2. Élémentarité (socle §8.1)
- Une fonction qui fait deux choses. Signal : sa description contient « et ».
- Fonction qui dépasse un écran.
- Mélange de niveaux d'abstraction dans une même fonction.
- Nom qui décrit l'implémentation au lieu du rôle, ou qui ment sur ce que fait la fonction.

### 3. Auto-vérification (socle §8.2)
- Fonctions sans vérification de préconditions.
- **Erreur grave à signaler systématiquement : une donnée externe validée par une assertion** au lieu d'une erreur métier explicite. Entrée utilisateur, réponse d'API, contenu de fichier, ligne de base : jamais d'assertion.
- Messages d'erreur qui ne permettent pas de diagnostiquer (pas de valeur reçue, pas de valeur attendue).
- Assertions redondantes avec le système de types.

### 4. Tests (socle §8.3)
- Du code livré sans test. Liste précisément les fonctions concernées.
- Test qui vérifie plusieurs comportements à la fois.
- Cas limites et cas d'erreur absents.
- Test dépendant de l'horloge, du réseau, de l'ordre d'exécution ou d'un état résiduel.
- **Test modifié pour passer** : compare avec l'historique. C'est le signal le plus grave de tous.
- Correction de bug sans test de non-régression associé.

### 5. Sécurité et données
- Secret, clé, mot de passe, jeton, chaîne de connexion présents dans le diff.
- Donnée personnelle réelle en dur ou dans une fixture de test.
- Entrée non assainie atteignant une requête, une commande système ou un rendu.
- Élévation de portée : une modification qui donne accès à plus que nécessaire.

### 6. Hygiène de branche (socle §10)
- Commits sur `main` au lieu d'une branche.
- Modifications hors périmètre de la tâche — le signal d'un agent qui a élargi sa mission.
- Fichiers générés, dépendances ou artefacts volumineux commités.
- Message de commit qui ne dit pas ce que fait le commit.

### 7. Journaux (socle §9)
- `docs/JOURNAL.md` à jour, avec la commande de vérification et son résultat ?
- Bug corrigé : est-il bien passé en « Résolu » et **réduit à une ligne** ?
- Décision structurante prise sans entrée dans `docs/DECISIONS.md` ?
- `CLAUDE.md` alourdi par des informations qui relèvent du journal ?

## Format du rapport

Ordonne les constats par gravité, pas par ordre d'apparition dans le fichier.

```markdown
## Verdict
{À corriger avant fusion | Fusionnable avec réserves | Bon pour fusion}
{Une phrase de justification.}

## Bloquant
{Ce qui rend le code faux, dangereux, ou non testé. À corriger avant fusion.}
- **{fichier}:{ligne}** — {le problème}. {Pourquoi ça compte.} → {ce qu'il faudrait faire}

## À corriger
{Ce qui devrait être repris mais ne bloque pas.}

## À discuter
{Choix défendables sur lesquels tu n'es pas d'accord — pas des erreurs.}

## Non vérifiable
{Ce que tu n'as pas pu évaluer : dépendance externe, comportement à l'exécution,
règle métier que tu ne connais pas. Sois explicite : un angle mort tu ne le vois pas,
mais tu peux nommer les endroits où tu es aveugle.}
```

## Règles de la revue

- **Chaque constat est localisé et actionnable.** « Ce module manque de robustesse » n'est pas un constat.
- **Rien n'est un constat sans conséquence énoncée.** Dis ce qui casse, pas ce qui te déplaît.
- **Ne signale pas les questions de style** déjà couvertes par le formateur automatique.
- **Ne réécris pas l'architecture** parce que tu l'aurais faite autrement. Une divergence de goût va dans « À discuter », jamais dans « Bloquant ».
- **Si le code est bon, dis-le et arrête-toi.** Une revue qui trouve toujours quelque chose devient une revue qu'on n'écoute plus. Un rapport vide est un résultat valide.
- **N'invente pas de problème pour justifier la revue.** Si tu n'as pas pu vérifier un point, il va dans « Non vérifiable ».
