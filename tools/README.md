Outils de travail pour les flux `exobase`.

- `import/` : captation depuis des sources externes.
- `normalize/` : conversion vers le format interne de `content/`.
- `export/` : production de formats cibles.
- `validate/` : contrôles avant synchronisation ou publication.
- `utils/` : code partagé par les outils.

## Validation LaTeX

`check_exercise_sources.py` est le port Python du contrôle
`openyourmath-v2/scripts/quality/check-exercise-sources.js`.

Usage :

```bash
python3 tools/check_exercise_sources.py
python3 tools/check_exercise_sources.py content/exercises/exo7/6-L2/IfVH.tex
python3 tools/check_exercise_sources.py --max-errors=0
python3 tools/check_exercise_sources.py --csv
```

La cible par défaut est `content/exercises/`. Les codes d'erreur et le format de
sortie sont alignés avec `pnpm test:tex` dans `openyourmath-v2`.

## Convention de modules

`exobase` n'a pas de `package.json` : les scripts n'ont aucune dépendance et
tournent sur un Node nu. Un fichier `.js` y est donc du CommonJS (`require`) et
un module ES porte l'extension `.mjs`, qui le déclare sans dépendre d'un
`package.json` ni de la détection automatique des Node récents.
