# Vocabulaire métier

> **Rédigé depuis le code de `basicfoncier` v1, non encore validé par un humain.**
> Corriger avant de s'appuyer dessus. Un agent qui se trompe sur « commune absorbée »
> produira du code plausible et faux.

- **Parcelle** : unité foncière élémentaire du cadastre.

- **idu** : identifiant unique de parcelle, exactement 14 caractères.
  `insee (5) + commune absorbée (3) + section (2) + numéro (4)`, chaque champ complété par des zéros à gauche.
  Exemple : `780480000H0011`.

- **id court** : la même référence sans les zéros de remplissage, 7 à 14 caractères. Forme usuelle en saisie humaine.

- **Code insee commune** : 5 caractères identifiant la commune ou l'arrondissement.

- **Commune absorbée** : 3 caractères, `000` si aucune. Commune fusionnée dans une commune nouvelle dont le cadastre conserve une numérotation propre.

- **Section** : 2 caractères, division cadastrale de la commune. Alphanumérique — sauf en Alsace-Moselle.

- **Numéro** : 4 caractères numériques, identifiant la parcelle dans sa section.

- **Alsace-Moselle** : départements 57, 67, 68. Les sections y sont **entièrement numériques**. La détection de la section par recherche du dernier caractère alphabétique — celle qu'utilise le v1 — n'y fonctionne pas : ces références exigent un traitement séparé et le format idu strict (14 caractères, numérique).

- **Arrondissement municipal** : Paris, Lyon, Marseille. Le code insee de l'arrondissement (`75104`) se décompose en code insee de la commune (`75100`) et code d'arrondissement (`104`).

- **ha / a / ca** : hectare (10 000 m²), are (100 m²), centiare (1 m²). Format d'affichage foncier usuel : `12 ha 34 a 56 ca`. Les composantes `a` et `ca` sont affichées sur deux chiffres dès qu'une composante supérieure est présente.
