# Format des QCM

`content/qcm/<source>/` porte le type de contenu **qcm**, distinct des exercices
de `content/exercises/`. Un fichier `.tex`, nommé par son UUID, est un *contenu
qcm* : l'unité que l'on cherche, que l'on ajoute à une liste et que l'on joue.

Un contenu qcm est :

- soit **une question indépendante** — le cas général ;
- soit **une série ordonnée** — plusieurs questions qui partagent un énoncé et
  se suivent : chacune peut s'appuyer sur les précédentes.

L'ordre fait donc partie du contenu. Les questions d'une série ne sont jamais
des fichiers séparés : on ne peut ni en extraire une, ni les mélanger, et une
liste qui contient la série les joue dans l'ordre du fichier.

Les UUID sont tirés dans le même espace que ceux des exercices : un qcm et un
exercice ne portent jamais le même, ce qui permet les listes mixtes.

## En-tête

Mêmes commandes que pour les exercices (voir `content/FORMAT.md`) : `\uuid`,
`\titre`, `\auteur`, `\organisation`, `\datecreate`, `\niveau`, `\module`,
`\chapitre`, `\sousChapitre`, `\difficulte` (1 à 3, ou vide), `\theme`.

| Champ propre aux qcm | Description |
|---|---|
| `\licence{...}` | Licence du contenu quand elle diffère de celle de l'auteur dans `authors.json` |
| `\serie{ordonnee}` | Présent sur les séries, et seulement sur elles |
| `\exo7qcmid{...}` | Provenance : `<lot>.<chapitre>.<rang>` de la première question dans qcm-exo7 |

Plusieurs auteurs se séparent par ` ; ` : `\auteur{hanani ; mzari}`.

## Corps : `\contenu{}`

Le corps garde la syntaxe du paquet LaTeX
[exo7qcm](https://github.com/exo7math/qcm-exo7) : une question est un
environnement `question`, ses réponses un environnement `answers`.

```latex
\contenu{
\texte{
  Énoncé commun à la série, ou convention de chapitre. Facultatif.
}

\begin{question}
\qclassification{260.03}
\qkeeporder
Énoncé de la question.
\begin{answers}
  \bad{Une réponse fausse.}
  \good{Une réponse juste.}
  \bad{Aucune des réponses ci-dessus.}
\end{answers}
\begin{explanations}
  Correction rédigée. Facultatif.
\end{explanations}
\end{question}
}
```

| Commande | Rôle |
|---|---|
| `\texte{...}` | Énoncé commun, placé avant la première question |
| `\good{...}` / `\bad{...}` | Réponse juste / fausse ; `\feedback{...}` à l'intérieur pour une réaction propre à la réponse |
| `\begin{explanations}` | Correction de la question |
| `\qimage[options]{images/<format>/<uuid>-<n>.<ext>}` | Image, rangée dans `content/images/<source>/<format>/` |
| `\qclassification{...}` | Codes du référentiel Exo7 |
| `\qtags{...}` | Étiquettes libres de la source (`motcle=...`) |
| `\qkeeporder` | Ne pas mélanger les réponses |
| `\qtype{...}` | `onetoall` (défaut : au moins une réponse juste), `onlyone`, `zerotoall`, `truefalse` |

Par défaut une question admet **une ou plusieurs** réponses justes, et la
consigne est de cocher toutes celles qui le sont, et elles seulement.

Consignes d'écriture reprises d'exo7qcm : pas de macro personnelle (seules
`\Nn`, `\Zz`, `\Qq`, `\Rr`, `\Cc`, `\Kk` sont admises), pas de formule dans un
titre, pas de mise en forme LaTeX hors des formules.

## Import depuis qcm-exo7

```bash
python3 tools/import/import_qcm_exo7.py            # simulation
python3 tools/import/import_qcm_exo7.py --apply
python3 tools/validate/check_qcm_sources.py
```

L'import lit le clone `../qcm-exo7` et réécrit `content/qcm/exo7/<lot>/`. Il est
reproductible : `sources/manifests/qcm-exo7-id-map.json` fixe l'UUID de chaque
contenu, et `content/provenance/qcm-exo7.json` consigne le commit importé et les
écarts à la source. Règles appliquées :

- **Séries** : une sous-section dont les questions suivent un énoncé commun
  devient un seul contenu `\serie{ordonnee}` (huit séries, toutes dans le lot de
  probabilités). Les autres questions restent indépendantes.
- **Préambule de chapitre** : une convention posée en tête de chapitre (repère
  de l'espace, notation des développements limités) est répétée dans `\texte{}`
  devant chaque question, qui reste ainsi lisible seule.
- **Métadonnées** : les titres de sous-section donnent la difficulté
  (Facile/Moyen/Difficile → 1/2/3 ; Niveau 1/2/3/4 → 1/2/3/3) et les codes Exo7,
  d'où viennent `\chapitre`, `\sousChapitre` et `\module`. Les fichiers sans
  code en reçoivent un par la table `CLASSIFICATION` de l'outil.
- **Ordre des réponses** : `\qkeeporder` est ajouté quand une réponse en désigne
  d'autres (« aucune des réponses ci-dessus »).
- **Énoncé par défaut** : « Quelles sont les assertions vraies ? » remplace un
  énoncé vide.
- **Corrections éditoriales** : les erreurs manifestes de la source sont
  corrigées par la table `PATCHES` et listées dans le manifeste de provenance.
