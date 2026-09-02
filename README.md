# Fretboard Work

Méthode progressive pour comprendre le manche de guitare, relier accords et
gammes, puis improviser sans dépendre d'un dessin mémorisé.

Le dépôt ne doit pas être utilisé comme une simple collection de cartes. Le
parcours recommandé est :

> voir → nommer → jouer → entendre → appliquer → retrouver sans support

Le cursus complet est décrit dans
[`docs/METHODE_PEDAGOGIQUE.md`](docs/METHODE_PEDAGOGIQUE.md).

## Démarrage rapide

Les semaines 1 et 2 commencent sans installation avec
[My Fretboard Trainer — Note Identification](https://myfretboardtrainer.com/noteidentification/).
La méthode donne les réglages de cordes, de frettes et d'altérations. Les
générateurs locaux servent ensuite de supports visuels ou de tests hors ligne.

Prérequis : Python 3.10 ou plus récent. Les SVG ne demandent aucune dépendance
externe et s'impriment directement au format A4. Chaque générateur est
autonome : télécharger un seul fichier `.py` suffit pour l'exécuter.

```bash
git clone https://github.com/ocverclock/Fretboard_work.git
cd Fretboard_work
python3 generateur_entrainement_manche_v1.py --tonalite G --niveau 1 --serie 1
```

Cette commande produit une fiche d'exercice et son corrigé. Commencer par
l'exercice ; n'ouvrir le corrigé qu'après avoir terminé.

## Ordre pédagogique des générateurs

| Étape | Compétence | Générateur | Sortie |
|---:|---|---|---|
| 1 | Construire le manche depuis la tonique | `generateur_construction_manche_v1_7.py` | A4 portrait |
| 2 | Rappeler notes et degrés hors ligne | `generateur_entrainement_manche_v1.py` (facultatif) | exercice + corrigé A4 portrait |
| 3 | Distinguer majeur et mineur | `generateur_comparaison_majeur_mineur_caged_v1_2.py` | A4 paysage |
| 4 | Comprendre les gammes relatives | `generateur_relatifs_majeur_mineur_caged.py` | SVG vertical |
| 5 | Relier accord, arpège, gamme et forme suivante | `generateur_caged_application_v2_2.py` | SVG pédagogique |
| 6 | Passer de la gamme aux accords d'une tonalité | `generateur_harmonisation_progressions_v1.py` | A4 paysage |
| 7 | Réduire le vocabulaire en petites cellules musicales | `generateur_cellules_caged_v1_3_4.py` | A4 paysage + guide |

Les étapes 2 et 6 sont les compléments structurants ajoutés au projet : la
première offre un test hors ligne reproductible ; la seconde transforme la
gamme en harmonie et en progression réelle.

## Commandes utiles

### 1. Construction du manche

```bash
python3 generateur_construction_manche_v1_7.py
```

Le script demande la tonalité, le mode et le type d'étiquettes. La fiche suit
quatre couches : fondamentales, octaves, triade, gamme complète.

### 2. Entraînement et corrigé

```bash
python3 generateur_entrainement_manche_v1.py \
  --tonalite G --niveau 1 --quantite 24 --serie 1
```

Niveaux :

1. notes naturelles ;
2. notes chromatiques ;
3. degrés de la tonalité ;
4. note et degré simultanément.

`--serie` est une graine reproductible : refaire la même série 48 heures plus
tard mesure la mémorisation, pas la chance.

### 3. Comparaison majeur / mineur

```bash
python3 generateur_comparaison_majeur_mineur_caged_v1_2.py \
  --tonalite A --forme E
```

Utiliser `--forme T` pour générer les cinq formes.

### 4. Relatifs majeur / mineur

```bash
python3 generateur_relatifs_majeur_mineur_caged.py C
python3 generateur_relatifs_majeur_mineur_caged.py Am
```

### 5. CAGED appliqué

```bash
python3 generateur_caged_application_v2_2.py \
  --tonalite G --accord majeur --forme E --etiquettes mixte
```

Accords disponibles : `majeur`, `mineur`, `7`, `maj7`, `m7`.

### 6. Harmonisation et progressions

```bash
python3 generateur_harmonisation_progressions_v1.py \
  --tonalite G --progression I-IV-V-I --accords triades --etiquettes mixte

python3 generateur_harmonisation_progressions_v1.py \
  --tonalite Am --progression i-bVII-bVI-bVII --accords septiemes
```

Progressions majeures : `I-IV-V-I`, `I-vi-IV-V`, `ii-V-I`, `vi-IV-I-V`.

Progressions mineures naturelles : `i-iv-v-i`, `i-bVII-bVI-bVII`,
`i-bVI-III-bVII`, `iiø-v-i`.

Le contour vert signale une note commune avec l'accord suivant. S'il n'y en a
pas, viser la tierce la plus proche du prochain accord.

### 7. Cellules et pentatoniques enrichies

```bash
python3 generateur_cellules_caged_v1_3_4.py \
  --tonalite G --lot tout --etiquettes degres

python3 generateur_cellules_caged_v1_3_4.py --guide
```

## Vérifications

```bash
python3 generateur_comparaison_majeur_mineur_caged_v1_2.py --test
python3 generateur_cellules_caged_v1_3_4.py --test
python3 generateur_caged_application_v2_2.py --test
python3 generateur_entrainement_manche_v1.py --test
python3 generateur_harmonisation_progressions_v1.py --test
python3 -m unittest discover -s tests -v
```

## Impression

- Imprimer à 100 %, sans « ajuster à la page » si le logiciel respecte déjà
  les dimensions A4 du SVG.
- Conserver les couleurs : tonique rouge, tierce orange, quinte bleue,
  septième violette.
- Les nouveaux exercices utilisent 14 frettes. Les générateurs historiques
  conservent pour l'instant leur géométrie validée afin d'éviter une régression
  silencieuse.

## Licence

Voir [`LICENSE`](LICENSE).
