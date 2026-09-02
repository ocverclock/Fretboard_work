# Méthode pédagogique progressive — 24 semaines

## Finalité

L'objectif n'est pas de connaître davantage de dessins. À la fin du cursus,
l'élève doit pouvoir :

1. trouver rapidement une note ou un degré sur les 14 premières frettes ;
2. construire une gamme à partir de sa formule ;
3. voir les notes d'un accord à l'intérieur de cette gamme ;
4. naviguer entre les cinq zones CAGED sans perdre la tonique ;
5. suivre une progression en visant les notes d'accord ;
6. créer des phrases courtes, rythmiques et résolues ;
7. expliquer ce qu'il joue avec des notes **et** des degrés.

La méthode est conçue pour cinq séances de 30 minutes par semaine. Une semaine
n'est validée que lorsque le critère de sortie est atteint. Si ce n'est pas le
cas, elle est répétée : avancer avec une compétence fragile ne fait qu'empiler
les confusions.

## La boucle d'apprentissage

Chaque notion suit toujours la même boucle :

1. **Voir** la carte complète.
2. **Nommer** les notes ou degrés à voix haute.
3. **Jouer** lentement, sans erreur et au métronome.
4. **Entendre** la fonction : repos, couleur ou tension.
5. **Appliquer** sur un accord ou une progression.
6. **Retrouver** sans carte avec un exercice interactif ou une fiche.

Un générateur n'est donc jamais une fin. Il fournit le support d'une action
précise et mesurable.

## Séance type de 30 minutes

| Durée | Travail | Règle |
|---:|---|---|
| 3 min | rappel à voix haute | sans guitare et sans fiche |
| 7 min | rappel actif | application web ou fiche, sans regarder la réponse |
| 8 min | carte du jour sur le manche | jouer lentement et nommer |
| 8 min | application musicale | accord, boucle ou backing track |
| 4 min | test et journal | noter score, tempo et difficulté |

Deux séances par semaine peuvent être allongées à 45 minutes, mais augmenter
la fréquence est plus utile qu'une longue séance isolée.

## Règles de validation communes

- **Exactitude** : au moins 90 % de bonnes réponses.
- **Vitesse** : 24 repères en moins de 8 minutes pour les fiches de rappel.
- **Continuité** : jouer le motif dans les deux sens sans arrêt.
- **Transfert** : réussir dans au moins deux tonalités et deux zones du manche.
- **Musicalité** : terminer volontairement sur une note d'accord et pouvoir la
  nommer.
- **Rétention** : refaire la même série 48 heures plus tard avec le même score
  ou mieux.

Si un seul de ces critères échoue, on ne rajoute pas une nouvelle gamme. On
réduit la zone, le tempo ou le nombre de notes.

---

# Phase 1 — Géographie du manche

## Applications web recommandées

Le support principal des deux premières semaines est
[**My Fretboard Trainer — Note Identification**](https://myfretboardtrainer.com/noteidentification/).
L'exercice fonctionne directement dans le navigateur et permet de choisir les
cordes, les frettes de début et de fin, ainsi que d'inclure ou non les dièses
et bémols. Le générateur local est conservé comme évaluation imprimable,
reproductible et utilisable hors ligne ; il n'est plus le point d'entrée du
parcours.

Deux alternatives peuvent être utilisées sans modifier les objectifs :

- [**GuitarOrb — Guitar Notes**](https://www.guitarorb.com/guitar-notes), en
  mode `Practice`, pour régler une plage de cordes et de frettes puis passer au
  mode chronométré ;
- [**MusicTheory.net — Fretboard Note Identification**](https://www.musictheory.net/exercises/fretboard),
  pour une interface très sobre et un exercice personnalisable.

My Fretboard Trainer et GuitarOrb emploient la notation internationale :

| Internationale | C | D | E | F | G | A | B |
|---|---|---|---|---|---|---|---|
| Française | Do | Ré | Mi | Fa | Sol | La | Si |

## Semaine 1 — Cordes, demi-tons et notes naturelles

**But** : connaître l'accordage, les cases naturelles et les deux demi-tons
sans note intermédiaire : B–C et E–F.

Support principal : ouvrir l'exercice **Note Identification**, désactiver
`Include flats/sharps` et utiliser l'accordage standard. Commencer avec les
frettes 0 à 5, puis étendre jusqu'à la frette 12 le cinquième jour.

Réglage des cordes et travail :

- jours 1–2 : cordes 6 et 5 ;
- jour 3 : cordes 4 et 3 ;
- jour 4 : cordes 2 et 1 ;
- jour 5 : mélange des six cordes ;
- dire le nom français **avant** de sélectionner la lettre internationale ;
- sur la guitare, jouer ensuite la note et contrôler sa justesse à l'accordeur.

Test hors ligne facultatif :

```bash
python3 generateur_entrainement_manche_v1.py --tonalite C --niveau 1 --serie 1
```

Ce script est autonome : le fichier `.py` peut être téléchargé et exécuté seul
dans n'importe quel dossier. Il produit une série stable avec son corrigé,
utile pour mesurer la rétention 48 heures plus tard.

**Validation** : 90 % sur 30 questions de l'application, puis 85 % minimum sur
une nouvelle session 48 heures plus tard. La fiche locale peut remplacer cette
seconde session, mais elle n'est pas obligatoire.

## Semaine 2 — Notes chromatiques

**But** : trouver dièses et bémols sans compter depuis le sillet à chaque fois.

Dans **My Fretboard Trainer**, activer `Include flats/sharps`, sélectionner les
six cordes et travailler des frettes 0 à 12. Garder l'exercice normal jusqu'à
90 %, puis passer à **Note Identification (Timer)** pour mesurer le temps.

Test hors ligne facultatif pour contrôler séparément l'orthographe avec dièses
et avec bémols :

```bash
python3 generateur_entrainement_manche_v1.py --tonalite G --niveau 2 --serie 2
python3 generateur_entrainement_manche_v1.py --tonalite Bb --niveau 2 --serie 3
```

La première fiche privilégie les noms avec dièses ; la seconde les noms avec
bémols. Il faut comprendre l'enharmonie, pas mélanger arbitrairement les deux
orthographes dans une même tonalité.

**Validation** : trouver n'importe quelle note demandée sur trois cordes en
moins de cinq secondes.

## Semaine 3 — Tonique et octaves

**But** : construire un réseau de fondamentales au lieu de mémoriser des points
isolés.

```bash
python3 generateur_construction_manche_v1_7.py
```

Générer G majeur en degrés. Travailler d'abord les étapes « fondamentales » et
« octaves ». Refaire ensuite en C et A.

Exercice musical : jouer une tonique, chanter la même note, puis rejoindre son
octave la plus proche sur une autre corde.

**Validation** : montrer toutes les toniques d'une tonalité sur la zone étudiée
sans regarder la fiche.

---

# Phase 2 — Des notes aux degrés et aux accords

## Semaine 4 — Degrés de la gamme majeure

**But** : remplacer la mémorisation de sept noms par une structure transposable
`1 2 3 4 5 6 7`.

```bash
python3 generateur_construction_manche_v1_7.py
python3 generateur_entrainement_manche_v1.py --tonalite G --niveau 3 --serie 4
```

Jouer chaque degré et chanter son numéro. Insister sur 3 et 7, qui définissent
fortement la couleur majeure et la tension vers 1.

**Validation** : donner immédiatement le nom correspondant aux degrés 1, 3,
5 et 7 dans G, C et D.

## Semaine 5 — Triade majeure 1–3–5

**But** : voir l'accord comme le squelette de la gamme.

Utiliser l'étape « squelette 1–3–5 » du générateur de construction. Jouer :

- 1–3–5–3 ;
- 1–5–3–1 ;
- une note par corde ;
- la même formule dans deux octaves.

Sur une boucle d'accord majeur, improviser uniquement avec 1, 3 et 5. Cette
restriction est volontaire : elle révèle si l'accord est réellement entendu.

**Validation** : finir dix phrases consécutives sur 1, 3 ou 5, puis nommer la
note d'arrivée.

## Semaine 6 — Mineur naturel et triade mineure

**But** : comprendre les modifications `3 → b3`, `6 → b6`, `7 → b7`.

```bash
python3 generateur_comparaison_majeur_mineur_caged_v1_2.py --tonalite A --forme E
python3 generateur_entrainement_manche_v1.py --tonalite Am --niveau 3 --serie 5
```

Ne pas apprendre quatre dessins indépendants. Jouer A majeur puis A mineur en
ne changeant d'abord que la tierce. Ajouter ensuite b6 et b7.

**Validation** : entendre et localiser la tierce qui fait basculer majeur vers
mineur dans trois zones du manche.

---

# Phase 3 — CAGED comme réseau, pas comme cinq boîtes

## Semaines 7 à 11 — Une forme par semaine

Ordre : C, A, G, E, D. Pour chaque semaine :

```bash
python3 generateur_caged_application_v2_2.py \
  --tonalite G --accord majeur --forme C --etiquettes mixte
```

Remplacer la forme dans la commande chaque semaine.

### Jour 1 — Accord

- jouer le voicing exact ;
- nommer ses 1, 3 et 5 ;
- retrouver ces notes autour du voicing.

### Jour 2 — Arpège

- monter et descendre ;
- partir successivement de 1, 3 et 5 ;
- conserver un tempo où aucune hésitation n'apparaît.

### Jour 3 — Gamme

- ajouter les autres degrés autour du squelette ;
- jouer `accord → arpège → gamme` ;
- ne jamais perdre de vue les notes d'accord.

### Jour 4 — Forme suivante

- utiliser la zone commune affichée ;
- créer une phrase qui commence dans la forme courante et finit dans la
  suivante ;
- revenir sans glissade automatique.

### Jour 5 — Rappel sans carte

```bash
python3 generateur_entrainement_manche_v1.py --tonalite G --niveau 4 --serie 7
```

**Validation de chaque forme** : jouer accord, arpège, gamme et transition dans
les deux sens, puis retrouver 90 % des repères sans fiche.

---

# Phase 4 — Relatifs et double lecture

## Semaine 12 — Majeur relatif / mineur relatif

```bash
python3 generateur_relatifs_majeur_mineur_caged.py C
python3 generateur_relatifs_majeur_mineur_caged.py Am
```

**But** : entendre que C majeur et A mineur partagent les mêmes notes mais pas
le même centre de gravité.

Exercice : jouer exactement les mêmes notes pendant quatre mesures sur C, puis
quatre mesures sur Am. Faire reposer les phrases sur C dans le premier cas et
sur A dans le second.

**Validation** : expliquer et jouer la conversion des degrés 1–7 de C majeur
vers ceux de A mineur.

## Semaine 13 — Même fondamentale, deux couleurs

Comparer G majeur et G mineur dans deux formes CAGED. Le test n'est pas de
réciter les formules, mais de basculer instantanément de l'une à l'autre en
modifiant les degrés concernés.

**Validation** : sur un accord G, faire entendre quatre phrases majeures puis
quatre phrases mineures sans changer de zone.

---

# Phase 5 — Harmonisation et progressions

## Semaine 14 — Les sept triades diatoniques

```bash
python3 generateur_harmonisation_progressions_v1.py \
  --tonalite G --progression I-IV-V-I --accords triades
```

**But** : comprendre que chaque accord est construit en empilant une note sur
deux dans la gamme.

Jouer les accords du tableau dans l'ordre. Dire degré, symbole et notes :
`I = G = G-B-D`, `ii = Am = A-C-E`, etc.

**Validation** : reconstruire sans fiche les sept triades de G majeur et A
mineur naturel.

## Semaine 15 — I–IV–V–I et i–iv–v–i

Travailler deux fiches, G majeur et A mineur. Commencer par les accords, puis
les arpèges. Les contours verts montrent les notes communes ; en leur absence,
viser la tierce la plus proche du prochain accord.

**Validation** : jouer une ligne continue d'une note par temps qui suit les
quatre accords sans saut supérieur à cinq cases.

## Semaine 16 — Progressions de quatre accords

```bash
python3 generateur_harmonisation_progressions_v1.py \
  --tonalite C --progression I-vi-IV-V --accords triades
```

Créer trois versions :

1. fondamentales seulement ;
2. tierces seulement ;
3. arpèges complets avec une note de passage entre les accords.

**Validation** : identifier l'accord en cours à partir des notes ciblées, sans
regarder la grille.

## Semaine 17 — Accords de septième et notes guides

```bash
python3 generateur_harmonisation_progressions_v1.py \
  --tonalite G --progression ii-V-I --accords septiemes
```

Isoler tierces et septièmes. Ce sont elles qui décrivent le mieux la fonction
harmonique. Jouer d'abord deux notes par accord, puis ajouter fondamentale et
quinte.

**Validation** : relier ii–V–I avec uniquement tierces et septièmes à 60 bpm,
deux temps par accord.

---

# Phase 6 — Vocabulaire court et phrasé

## Semaine 18 — Cellules 1–2–3–5

```bash
python3 generateur_cellules_caged_v1_3_4.py \
  --tonalite G --module cellule --formule maj1235 --etiquettes mixte
```

Jouer la cellule dans les cinq formes, mais varier le rythme : croches,
syncopes, triolets, silence sur le premier temps.

**Validation** : produire quatre phrases rythmiquement différentes avec les
mêmes quatre notes.

## Semaine 19 — Cellules avec 4 et #4

Comparer `maj1345` et `maj13#45`. Le 4 doit résoudre vers 3 ou 5 ; le #4 doit
faire entendre sa poussée vers 5.

**Validation** : l'auditeur doit pouvoir distinguer les deux couleurs sans voir
le manche.

## Semaine 20 — Cellules mineures

Travailler `min1235` et `min1345`. Ajouter ensuite b7 pour reconstituer la
pentatonique mineure.

**Validation** : partir de la triade, ajouter une seule note, puis expliquer ce
qu'elle change.

---

# Phase 7 — Pentatoniques enrichies et intégration

## Semaine 21 — Pentatonique majeure enrichie

Générer le lot majeur :

```bash
python3 generateur_cellules_caged_v1_3_4.py \
  --tonalite G --lot penta --etiquettes mixte
```

Ne choisir qu'une extension par séance. L'objectif est d'entendre la nouvelle
note, pas de collectionner les variantes.

## Semaine 22 — Pentatonique mineure enrichie

Travailler m+2, m+6 et m+b6 sur des boucles différentes. Vérifier que la note
ajoutée appartient réellement à l'harmonie du morceau.

**Validation des semaines 21–22** : jouer la pentatonique de base, ajouter la
couleur pendant deux mesures, puis revenir à la base sans perdre le centre.

## Semaine 23 — Improvisation guidée sur progression

Choisir une progression déjà validée. Structure d'un chorus :

1. accord uniquement ;
2. arpège + une note de passage ;
3. cellule rythmique ;
4. déplacement vers une forme CAGED voisine.

Enregistrer. À l'écoute, relever les moments où la phrase suit l'accord et ceux
où elle ne fait que parcourir une gamme.

**Validation** : au moins 75 % des changements d'accord doivent être marqués
par une note d'accord identifiable.

## Semaine 24 — Évaluation finale

### Épreuve A — Cartographie

```bash
python3 generateur_entrainement_manche_v1.py \
  --tonalite G --niveau 4 --quantite 32 --serie 24
```

Objectif : 90 % en moins de 10 minutes.

### Épreuve B — Construction

Sans fiche, écrire la gamme, les triades et les accords de septième d'une
tonalité tirée au sort.

### Épreuve C — Navigation

Jouer une phrase qui traverse les cinq formes CAGED et termine sur la tierce de
l'accord.

### Épreuve D — Harmonie

Improviser deux chorus sur une progression de quatre accords : le premier avec
les notes d'accord, le second avec cellules et notes de passage.

### Épreuve E — Explication

Nommer les notes et les degrés de deux phrases jouées. Une connaissance qui ne
peut pas être expliquée reste généralement trop fragile pour être transposée.

---

# Diagnostic et remédiation

| Problème observé | Cause probable | Correction |
|---|---|---|
| L'élève compte depuis la case 0 | repères insuffisants | revenir aux notes naturelles, séries courtes |
| Il connaît la forme mais perd la tonique | dessin appris sans centre | jouer seulement toniques et octaves |
| Il monte et descend la gamme mécaniquement | absence de cible harmonique | limiter à 1–3–5 puis suivre une progression |
| Il confond majeur et mineur | tierce non entendue | alterner 3 et b3 sur une fondamentale tenue |
| Il reste prisonnier d'une boîte | transitions non travaillées | une phrase doit obligatoirement finir dans la forme voisine |
| Trop d'erreurs en double lecture | charge cognitive excessive | revenir séparément aux notes puis aux degrés |
| Les phrases sont justes mais plates | rythme non contraint | garder quatre notes et varier uniquement le rythme |
| Les extensions sonnent faux | note choisie hors harmonie | vérifier l'accord du moment avant d'ajouter une couleur |

# Suite après les 24 semaines

Le travail peut ensuite s'étendre à l'harmonique mineure, au blues, aux modes,
aux accords altérés et aux substitutions. Ces sujets ne doivent pas être
ajoutés avant que les critères finaux soient solides. Sinon, ils augmentent le
vocabulaire théorique sans améliorer le jeu réel.
