# exobase

Sources éditoriales LaTeX et ressources associées destinées à OpenYourMath.

## Rôle dans le flux de contenu

`Exercices` reste le dépôt d’édition des exercices AMSCC. `exobase` en est le
miroir canonique versionné, limité ici aux sources, images et auteurs. Il ne
contient pas les données dérivées d’OpenYourMath (cache, base SQLite,
artefacts de rendu et embeddings).

```text
Exercices  →  exobase  →  OpenYourMath
 édition       contenu      parsing, indexation et publication
```

Le dossier `content/` suit le contrat de contenu d’OpenYourMath :

- `content/exercises/amscc/` : sources `.tex` ;
- `content/images/amscc/<format>/` : images et sources graphiques ;
- `content/authors.json` : auteurs et licences.

Les fichiers qui existent seulement dans exobase ne sont jamais supprimés par
la synchronisation.

## Synchroniser depuis Exercices

Le script est sans effet par défaut et affiche le plan de synchronisation :

```bash
node scripts/sync-exercices.mjs
node scripts/sync-exercices.mjs --check # utile en automatisation, échoue si un écart existe
node scripts/sync-exercices.mjs --apply
```

Par défaut, la source est résolue vers `../../COET/Exercices`. Pour une autre
copie locale, définir `EXERCISES_ROOT=/chemin/vers/Exercices`. Le script refuse
d’écraser une modification locale d’exobase ; `--force` ne doit être utilisé
qu’après revue explicite.

Après une synchronisation : vérifier `git diff --check`, relire les changements
puis les committer dans exobase. OpenYourMath importe ensuite ce commit avec
son synchroniseur `scripts/sync-exobase.js`.
