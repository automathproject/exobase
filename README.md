# exobase

`exobase` est l'atelier de captation, de normalisation et d'export des exercices.

Son rôle n'est pas de publier directement les contenus, mais de servir de point de
passage entre des sources hétérogènes et des formats exploitables par d'autres
projets, notamment `openyourmath-v2` et les formats proches d'Exo7.

## Organisation cible

- `sources/` : sources brutes ou importées, avant normalisation.
- `content/` : contenus normalisés et versionnables, classés par source.
- `exports/` : sorties générées ou préparées pour un format cible.
- `tools/` : outils d'inventaire, d'import, de normalisation, d'export et de validation.
- `migrations/` : notes et scripts liés a une source ou migration précise.
- `archive/` : éléments conservés pour historique, sans rôle actif dans le flux courant.

## Flux principal

1. Capter une source brute dans `sources/raw/<source>/`.
2. La stabiliser dans `sources/staged/<source>/` si un prétraitement manuel est nécessaire.
3. Produire les exercices normalisés dans `content/exercises/<source>/`.
4. Produire ou référencer les artefacts dans `content/images/<source>/`.
5. Exporter vers `exports/openyourmath/` ou `exports/exo7-format/`.

Les métadonnées IA récentes restent portées par `openyourmath-v2`. `exobase` ne
devrait garder que la provenance stable, les manifestes de source et les rapports
d'import/export.
