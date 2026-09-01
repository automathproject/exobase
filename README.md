# exobase

`exobase` est l'atelier de captation, de normalisation et d'export des exercices.

Son rôle n'est pas de publier directement les contenus, mais de servir de point de
passage entre des sources hétérogènes et des formats exploitables par d'autres
projets, notamment `openyourmath-v2` et les formats proches d'Exo7.

```text
Exercices  →  exobase  →  OpenYourMath
 édition       contenu      parsing, indexation et publication
```

`Exercices` reste le dépôt d'édition des exercices AMSCC. `exobase` en est le
miroir canonique versionné, limité aux sources, images, codes et auteurs. Il ne
contient pas les données dérivées d'OpenYourMath (cache, base SQLite, artefacts
de rendu et embeddings).

## Organisation

- `sources/` : sources brutes ou importées, avant normalisation.
- `content/` : contenus normalisés et versionnables, classés par source.
- `exports/` : sorties générées ou préparées pour un format cible.
- `tools/` : outils d'inventaire, d'import, de normalisation, d'export et de validation.
- `scripts/` : scripts de synchronisation et de maintenance du dépôt.
- `migrations/` : notes et scripts liés à une source ou migration précise.
- `archive/` : éléments conservés pour historique, sans rôle actif dans le flux courant.

Le dossier `content/` suit le contrat de contenu d'OpenYourMath :

- `content/exercises/<source>/` : sources `.tex` ;
- `content/images/<source>/<format>/` : images et sources graphiques ;
- `content/code/<source>/python/` : extraits Python référencés par `\pythoncode` ;
- `content/provenance/` : manifestes de provenance par source ;
- `content/authors.json` : auteurs et licences ;
- `content/FORMAT.md` : documentation du format des exercices `.tex`.

## Flux principal

1. Capter une source brute dans `sources/raw/<source>/`.
2. La stabiliser dans `sources/staged/<source>/` si un prétraitement manuel est nécessaire.
3. Produire les exercices normalisés dans `content/exercises/<source>/`.
4. Produire ou référencer les artefacts dans `content/images/<source>/`.
5. Exporter vers `exports/openyourmath/` ou `exports/exo7-format/`.

Les métadonnées IA récentes restent portées par `openyourmath-v2`. `exobase` ne
devrait garder que la provenance stable, les manifestes de source et les rapports
d'import/export.

## Synchroniser depuis Exercices

Le script est sans effet par défaut et affiche le plan de synchronisation :

```bash
node scripts/sync-exercices.mjs
node scripts/sync-exercices.mjs --check # utile en automatisation, échoue si un écart existe
node scripts/sync-exercices.mjs --apply
```

La comparaison est à trois versions : l'état d'Exercices, celui d'exobase, et
l'état de référence — le commit d'Exercices enregistré dans
`content/provenance/amscc.json` par la dernière synchronisation. C'est cette
référence qui distingue les quatre situations :

| Situation | Décision |
| --- | --- |
| Corrigé dans Exercices seulement | copié dans exobase |
| Retravaillé dans exobase seulement | préservé, jamais écrasé |
| Modifié des deux côtés | conflit : signalé, rien n'est copié |
| Absent d'exobase | ajouté |

Tant qu'un conflit subsiste, la référence n'avance pas et le script sort en
code 1 : les autres fichiers sont bien copiés, mais le conflit reste visible à
chaque exécution jusqu'à ce qu'il soit tranché.

`--force` donne autorité à Exercices sur tout ce qui diffère côté exobase, les
conflits comme le travail local délibérément préservé. C'est donc la façon
d'abandonner une adaptation faite dans exobase au profit de l'amont. L'aperçu
sans `--apply` liste nommément les fichiers concernés sous « Écrasés par
--force » : relisez-le avant d'appliquer.

Sans référence enregistrée — première exécution, ou historique amont réécrit —
le script ne détruit rien : il préserve le côté exobase et enregistre le commit
courant, ce qui permet aux exécutions suivantes de décider.

## Remonter du travail vers Exercices

`Exercices` reste l'atelier d'édition, mais une correction faite dans exobase peut
y être remontée plutôt que d'y rester en travail local :

```bash
node scripts/sync-exercices.mjs --push          # aperçu
node scripts/sync-exercices.mjs --push --apply  # écrit dans Exercices
```

Seuls les fichiers classés « travail exobase » partent, c'est-à-dire ceux que
l'amont n'a pas touchés depuis la référence. Un conflit — modifié des deux côtés —
bloque la remontée entière tant qu'il n'est pas tranché, et `Exercices` doit être
propre pour que la remontée soit relisible.

La remontée ne propage que des **modifications** : un fichier qui n'existerait
que dans exobase n'est pas créé dans Exercices.

Ensuite : relire et committer dans `Exercices`, puis relancer la synchro
descendante (`--apply`) pour enregistrer la nouvelle référence. Les fichiers
redeviennent alors identiques des deux côtés.

`--apply` exige qu'Exercices n'ait pas de modification non committée, sans quoi
la référence enregistrée serait fausse. Par défaut, la source est résolue vers
`../../COET/Exercices` ; pour une autre copie locale, définir
`EXERCISES_ROOT=/chemin/vers/Exercices`.

Les fichiers qui existent seulement dans exobase ne sont jamais supprimés par
la synchronisation. Les suppressions et les renommages faits dans Exercices
depuis la référence sont signalés, jamais répercutés automatiquement.

Codes de sortie : `0` succès, `1` écart ou conflit, `2` usage, `3` erreur.

Après une synchronisation : vérifier `git diff --check`, relire les changements
puis les committer dans exobase. OpenYourMath importe ensuite ce commit avec
son synchroniseur `scripts/sync-exobase.js`.

## Validation des sources LaTeX

```bash
python3 tools/check_exercise_sources.py
```
