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

La cible par défaut est `content/exercises/`. Le format de sortie est aligné sur
`pnpm test:tex` dans `openyourmath-v2`, et les codes d'erreur le sont aussi à une
exception près.

### `unbalanced-environment` — propre à exobase

Ce contrôle apparie `\begin{...}` et `\end{...}` avec une pile, et distingue :

- un environnement ouvert et jamais fermé ;
- un `\end{}` qui ne ferme rien ;
- un `\end{}` qui ne correspond pas à l'environnement ouvert juste avant — c'est
  ce dernier cas qui révèle les environnements entrelacés, invisibles à un simple
  comptage.

Les commentaires sont ignorés et les blocs verbatim neutralisés, donc un
`\begin{}` cité en exemple ne déclenche rien.

Cette règle n'existe pas encore dans le validateur JavaScript d'OpenYourMath :
un fichier refusé ici passera `pnpm test:tex` là-bas. C'est le sens voulu — la
sévérité appartient à l'usine — mais il faudra la porter si la CI d'aval doit
bloquer sur les mêmes défauts.

## Convention de modules

`exobase` n'a pas de `package.json` : les scripts n'ont aucune dépendance et
tournent sur un Node nu. Un fichier `.js` y est donc du CommonJS (`require`) et
un module ES porte l'extension `.mjs`, qui le déclare sans dépendre d'un
`package.json` ni de la détection automatique des Node récents.
