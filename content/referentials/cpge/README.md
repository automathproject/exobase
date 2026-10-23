# Référentiel CPGE — programmes officiels de mathématiques

Ce répertoire contient les programmes officiels de mathématiques des classes
préparatoires scientifiques, convertis en Markdown structuré. Ils servent de
base à la classification CPGE des exercices : chaque section et sous-section
porte un identifiant stable auquel un exercice se rattache par la macro
`\cpge{}` de sa source (voir `content/FORMAT.md` et, pour la conception
d'ensemble, `openyourmath-v2/docs/classification-cpge.md`).

## Contenu

| Fichier                   | Filières   | Année | Texte officiel                                              |
| ------------------------- | ---------- | ----- | ----------------------------------------------------------- |
| `programmes/mpsi-mp2i.md` | MPSI, MP2I | 1     | BO spécial n°1 du 11-2-2021, NOR ESRS2035779A               |
| `programmes/pcsi.md`      | PCSI       | 1     | BO spécial n°1 du 11-2-2021, NOR ESRS2035780A               |
| `programmes/ptsi.md`      | PTSI       | 1     | BO spécial n°1 du 11-2-2021, NOR ESRS2035781A               |
| `programmes/bcpst1.md`    | BCPST      | 1     | BO n°26 du 1-7-2021, NOR ESRH2108111A (annexe 3)            |
| `programmes/mp-mpi.md`    | MP, MPI    | 2     | BO n°31 du 26-8-2021, NOR ESRS2111702A et ESRS2111756A      |
| `programmes/pc.md`        | PC         | 2     | BO n°31 du 26-8-2021, NOR ESRS2111703A                      |
| `programmes/psi.md`       | PSI        | 2     | BO n°31 du 26-8-2021, NOR ESRS2111748A                      |
| `programmes/pt.md`        | PT         | 2     | BO n°31 du 26-8-2021, NOR ESRS2111735A                      |
| `programmes/bcpst2.md`    | BCPST      | 2     | BO n°26 du 1-7-2021, NOR ESRH2108111A (annexe 3)            |

Programmes en vigueur depuis la rentrée 2021 (1re année) et 2022 (2e année).

### Sources

Les PDF officiels ne sont pas versionnés. `sources.json` donne, pour chaque
annexe d'arrêté, l'URL du PDF, la page du Bulletin officiel, le NOR, la date
de l'arrêté et les pages converties. Pour les récupérer localement dans
`sources/raw/cpge/` (ignoré par Git) :

```bash
node tools/import/fetch_programmes_cpge.mjs
```

Chaque PDF est l'annexe complète de l'arrêté (mathématiques, physique-chimie,
SII…). Seules les pages de mathématiques sont converties. Les pages de
`sources.json` et du front matter sont celles du PDF, pas la pagination
imprimée.

Deux paires de filières partagent un texte identique : MPSI et MP2I (un seul
programme « Mathématiques MPSI, MP2I ») ; MP et MPI (les annexes 1 des arrêtés
ESRS2111702A et ESRS2111756A ne diffèrent que par la page de titre). Un seul
fichier Markdown est donc produit par texte, et le champ `filieres` du front
matter liste les filières concernées. À l'inverse, BCPST a deux textes
distincts, un par année (`bcpst1`, `bcpst2`), pour une même filière.

## Format des fichiers `programmes/*.md`

Le format vise deux usages : être lisible tel quel, et être analysable par un
script pour produire le référentiel machine (identifiants stables de sections
et sous-sections).

### Front matter

```yaml
---
programme: mp-mpi            # identifiant du texte, = nom du fichier
titre: Programme de mathématiques MP, MPI
filieres: [MP, MPI]
annee: 2
bo: Bulletin officiel n°31 du 26 août 2021
nor: [ESRS2111702A, ESRS2111756A]
arrete: 2021-07-13
rentree: 2022
source: https://cache.media.education.gouv.fr/file/31/08/5/ensecsup702_annexes_1417085.pdf
bo_url: https://www.education.gouv.fr/bo/21/Hebdo31/ESRS2111702A.htm
pages: 1-29                  # pages du PDF source
---
```

### Hiérarchie des titres

- `#` : titre du document (une seule fois).
- `##` : grandes parties : `Préambule` (objectifs de formation, compétences,
  architecture…), puis pour la 1re année `Premier semestre` et
  `Deuxième semestre`, pour la 2e année `Programme`.
- `###` dans le préambule : ses rubriques ; dans le programme : les
  **sections** (« Nombres complexes », « Espaces préhilbertiens réels »…).
- `####` : les **sous-sections** lettrées du programme (« a) Nombres
  complexes »), ou les rubriques de niveau inférieur du préambule.

Les sections et sous-sections du programme portent un identifiant stable en
fin de titre, à la syntaxe Pandoc :

```markdown
### Nombres complexes {#mpsi-mp2i.nombres-complexes}
#### a) Nombres complexes {#mpsi-mp2i.nombres-complexes.a}
```

- section : `<programme>.<slug>` où `<slug>` est le titre en kebab-case ASCII
  sans accents ni mots vides, réduit à ses 1 à 4 mots significatifs
  (`espaces-prehilbertiens`, `suites-series-fonctions`) ; unique dans le
  fichier ;
- sous-section : `<id de section>.<lettre>` (lettre de la sous-section dans
  le PDF). Une section sans sous-section lettrée n'a que l'identifiant de
  section.

Les titres du préambule n'ont pas d'identifiant.

Certaines sections sont découpées en parties « A - », « B - »… (par exemple
« Techniques fondamentales de calcul différentiel et intégral » en MPSI). Le
titre général et chaque partie sont alors des `###`, chacun avec son
identifiant de section ; les sous-sections lettrées sont rattachées à la
partie. Un titre `###` commençant par `<Lettre majuscule> - ` appartient donc
à la section générale qui le précède :

```markdown
### Techniques fondamentales de calcul différentiel et intégral {#mpsi-mp2i.calcul-differentiel-integral}
### A - Fonctions d'une variable réelle à valeurs réelles ou complexes {#mpsi-mp2i.fonctions-valeurs-reelles-complexes}
#### a) Généralités sur les fonctions {#mpsi-mp2i.fonctions-valeurs-reelles-complexes.a}
```

### Gabarit BCPST

Les programmes BCPST suivent une présentation différente, que le Markdown
ramène à la même structure :

- `##` : `I – Objectifs de formation` (ou `I – Préambule`), traité comme le
  préambule ; `II – Programme de première année` (ou de seconde année), avec
  son texte général ; en 1re année, les semestres (`2 – Programme du premier
  semestre`, `3 – Programme du second semestre`) sont aussi des `##`.
- `###` : les chapitres, titre officiel complet conservé (« Outils 1 –
  Logique, ensembles et raisonnemment », « Analyse 5 – Suites réelles »).
  Leur identifiant ne reprend pas le numéro :
  `{#bcpst1.logique-ensembles-raisonnement}`.
- `####` : les sous-parties a), b)… Dans le PDF, ce sont des lignes en gras à
  l'intérieur du tableau. Elles deviennent des titres `####`, et le tableau
  est coupé à chacune.

Les titres de niveau `###` qui ne portent pas de tableau (rubriques du texte
général d'un `##` de programme) n'ont pas besoin d'identifiant.

### Bandeau de section

Le texte d'introduction d'une section (en italique dans le PDF) suit le titre
en paragraphes ordinaires, listes en `-`.

### Tableaux Contenus / Capacités & commentaires

Chaque sous-section (ou section sans sous-section) est suivie d'un tableau
GFM à deux colonnes :

```markdown
| Contenus | Capacités & commentaires |
| --- | --- |
| Parties réelle et imaginaire.<br>Opérations sur les nombres complexes. | La construction de $\mathbb{C}$ est hors programme. |
| Point du plan associé à un nombre complexe, affixe d'un point, affixe d'un vecteur. | On identifie $\mathbb{C}$ au plan usuel muni d'un repère orthonormé direct (« plan complexe »). |
```

- Une ligne de tableau = un groupe horizontal du PDF : les contenus de gauche
  et le commentaire de droite qui leur fait face. Une cellule vide reste vide.
- Retours à la ligne internes à une cellule : `<br>` (jamais de saut de ligne
  réel dans une ligne de tableau).
- Mathématiques en LaTeX compatible KaTeX, `$...$` uniquement dans les
  cellules. **Jamais de `|` littéral dans une cellule**, y compris en
  mathématiques : `\lvert x\rvert`, `\lVert x\rVert`, `\mid`.
- Les mentions de liens avec d'autres disciplines (pictogrammes ou sigles
  « PC », « SI », « I »…) sont reproduites en texte à l'endroit où elles
  apparaissent, sous la forme `⇆ PC`, `⇆ SI`, `⇆ I`. En BCPST, le symbole
  du PDF est reproduit tel quel : `⇌`.
- En PTSI, des ★ vont par paires et encadrent certains passages
  (déterminants, suites sommables, fonctions de deux variables). Le texte n'en
  donne pas la légende. Ils sont reproduits tels quels ; quand un ★ précède un
  titre dans le PDF, il est placé juste après le titre, pour ne pas gêner la
  détection des lettres et des parties.
- L'en-tête reprend celui du PDF : `Capacités & commentaires`, ou
  `Commentaires` en BCPST.
- Un tableau qui se poursuit sur la page suivante est fusionné en un seul
  tableau (l'en-tête répété n'est pas recopié).

Hors des tableaux, les formules isolées utilisent `$$...$$` sur leurs propres
lignes.

### Validation

```bash
node tools/check_programmes_cpge.mjs
```

Le script vérifie les éléments suivants :

- le front matter, et son accord avec `sources.json` (PDF cité, pages
  converties) ;
- l'unicité et la forme des identifiants, et la cohérence entre la lettre et
  l'identifiant ;
- la présence d'un identifiant sur toute sous-section lettrée, toute partie
  « A - » et tout titre portant un tableau ;
- que chaque ligne de tableau a exactement deux cellules ;
- l'équilibre des accolades dans chaque formule ;
- l'absence de pieds de page et de césures résiduels.

Le script n'a pas de dépendance ; le rendu KaTeX des formules est vérifié en
aval par les tests d'OpenYourMath (`pnpm test`).

### Usage en aval

OpenYourMath importe ce répertoire par `pnpm sync:exobase`, puis
`pnpm build:referentiel-cpge` (inclus dans `pnpm build:content`) le lit et
remplit ses tables `cpge_programmes`, `cpge_filieres` et `cpge_noeuds`.

Les identifiants y sont figés par un instantané versionné
(`tests/build/__snapshots__/cpge-identifiants.txt`). **Changer un identifiant,
c'est casser les rattachements d'exercices qui y renvoient** : ajouter une
section ne pose pas de problème, renommer ou supprimer demande de corriger
dans le même commit les `\cpge{}` des sources concernées, que
`tools/check_exercise_sources.py` signale (`unknown-cpge-node`).

### Fidélité

Le texte est reproduit intégralement et sans reformulation, typographie
française conservée (espaces insécables inutiles supprimés). Les pieds de page
(« © Ministère… », numéros de page) et les coupures de mots en fin de ligne
sont supprimés.
