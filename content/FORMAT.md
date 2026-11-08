# Format des exercices

Les exercices de `content/exercises/` sont des fichiers `.tex` nommés par leur UUID.
Ce document décrit les champs attendus et les conventions de structure.

## En-tête

Chaque fichier commence par une série de commandes de métadonnées avant `\contenu{}`.

### Champs obligatoires

| Champ | Description | Exemple |
|---|---|---|
| `\uuid{...}` | Identifiant unique de l'exercice. Le nom du fichier doit correspondre. | `\uuid{0C55}` |
| `\titre{...}` | Titre court de l'exercice | `\titre{Loi normale}` |
| `\auteur{...}` | Auteur (peut être vide si inconnu) | `\auteur{Maxime Nguyen}` |
| `\datecreate{...}` | Date de création au format `YYYY-MM-DD` | `\datecreate{2024-12-01}` |
| `\niveau{...}` | Niveau académique | `\niveau{L2}` |
| `\module{...}` | Discipline | `\module{Probabilité et statistique}` |
| `\chapitre{...}` | Chapitre dans le module | `\chapitre{Lois usuelles}` |
| `\sousChapitre{...}` | Sous-section du chapitre | `\sousChapitre{Loi normale}` |
| `\organisation{...}` | Source d'origine | `\organisation{AMSCC}` |
| `\difficulte{...}` | Niveau de difficulté (1 à 3, ou vide) | `\difficulte{2}` |

### Champs optionnels communs

| Champ | Description |
|---|---|
| `\theme{...}` | Mots-clés thématiques libres |
| `\duree{...}` | Durée estimée en minutes |

### Champs spécifiques à exo7

| Champ | Description |
|---|---|
| `\exo7id{...}` | Identifiant numérique dans la base exo7 (lien de provenance) |
| `\isIndication{true\|false}` | Indique si une indication est disponible dans la source |
| `\isCorrection{true\|false}` | Indique si une correction est disponible dans la source |

## Corps : `\contenu{}`

Le contenu de l'exercice est encapsulé dans `\contenu{}`. Les commandes disponibles :

| Commande | Rôle |
|---|---|
| `\texte{...}` | Contexte ou énoncé introductif |
| `\question{...}` | Une question posée |
| `\indication{...}` | Aide ou piste (optionnel) |
| `\reponse{...}` | Correction complète (optionnel) |

Pour plusieurs questions, utiliser `\begin{enumerate}...\end{enumerate}` avec
`\item \question{...}` (et `\indication{}` / `\reponse{}` associés si besoin).

### Animation interactive

Une figure interactive se place dans le bloc qu'elle illustre (énoncé, question,
réponse) :

```latex
\reponse{
  …
  \animation[\exercisespath img/pdf/ebva-tikz-1]{ebva-directionnelle}{Dérivée directionnelle en l'origine}
}
```

- Le **nom** (lettres, chiffres, `-`, `_`) désigne la figure
  `content/animations/<source>/<nom>.js`, écrite avec le kit d'OpenYourMath. Il doit être unique toutes sources
  confondues, car l'adresse publique `https://openyourmath.org/animation/<nom>`
  ne porte pas la source ; on le préfixe par l'uuid de l'exercice.
- L'**image fixe**, entre crochets et facultative, s'écrit comme le chemin d'un
  `\includegraphics` : imprimée dans l'encadré du PDF, elle sert aussi de vignette
  sur le site. On la dessine de préférence en TikZ.
- La **légende** est du texte simple, sans formule : c'est le titre de la figure ;
  dans un PDF, elle accompagne l'image fixe, l'adresse et son QR code.
- L'exercice reste complet sans l'animation. La figure n'utilise que le kit
  (aucune ressource externe) ; la charte de création et le kit sont décrits
  dans `docs/animations.md` d'OpenYourMath.

## Exemple minimal

```latex
\uuid{ABCD}
\titre{Titre de l'exercice}
\auteur{Prénom Nom}
\datecreate{2025-01-15}
\niveau{L1}
\module{Algèbre}
\chapitre{Matrices}
\sousChapitre{Opérations}
\organisation{AMSCC}
\difficulte{1}

\contenu{
\texte{
  Contexte ou énoncé général.
}
\begin{enumerate}
  \item \question{Première question.}
  \indication{Une piste.}
  \reponse{La réponse.}

  \item \question{Deuxième question.}
  \reponse{La réponse.}
\end{enumerate}
}
```

## Incohérences connues

- **`\difficulte{}`** : souvent vide dans les fichiers amscc et exo7.
- **`\organisation{}`** : absent ou vide dans les fichiers crouzet — comportement accepté.
