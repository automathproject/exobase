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

Par défaut, la source est résolue vers `../../COET/Exercices`. Pour une autre
copie locale, définir `EXERCISES_ROOT=/chemin/vers/Exercices`. Le script refuse
d'écraser une modification locale d'exobase ; `--force` ne doit être utilisé
qu'après revue explicite.

Les fichiers qui existent seulement dans exobase ne sont jamais supprimés par
la synchronisation.

Après une synchronisation : vérifier `git diff --check`, relire les changements
puis les committer dans exobase. OpenYourMath importe ensuite ce commit avec
son synchroniseur `scripts/sync-exobase.js`.

## Validation des sources LaTeX

```bash
python3 tools/check_exercise_sources.py
```
