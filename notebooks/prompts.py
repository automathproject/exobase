"""
Module contenant les prompts pour l'analyse des fichiers LaTeX.
Ces prompts sont utilisés pour interroger l'API Gemini.
"""

def create_metadata_prompt(latex_content: str) -> str:
    """Create prompt for metadata extraction via Gemini API."""
    return f"""Voici un exercice de mathématiques au format LaTeX. Analyse-le et génère les métadonnées suivantes:

1. Compétences mathématiques requises pour résoudre l'exercice (5 maximum)
   - Exprime chaque compétence sous forme d'un verbe d'action suivi d'un complément précis
   - Utilise des verbes comme: calculer, démontrer, dériver, résoudre, appliquer, interpréter, modéliser
   - Fais correspondre la compétence à une action concrète que l'étudiant doit maîtriser
   - Liste les compétences par ordre d'importance (la plus cruciale en premier)
   - Exemple: "calculer une dérivée partielle" plutôt que "dérivée partielle"

2. Niveau de difficulté (facile, intermédiaire, avancé)

3. Mots-clés pertinents pour la recherche (8 maximum)

4. Concepts théoriques fondamentaux mobilisés (3-5)

5. Prérequis nécessaires pour aborder l'exercice

6. Type d'exercice (Exercice d'application directe, Problème à étapes, problème ouvert, Démonstration, Modélisation, Investigation)

7. Temps estimé pour la résolution

Réponds uniquement en format JSON structuré avec ces 7 clés exactes:
{{
  "competences": ["compétence 1", "compétence 2", ...],
  "niveau_difficulte": "niveau",
  "mots_cles": ["mot-clé 1", "mot-clé 2", ...],
  "concepts_fondamentaux": ["concept 1", "concept 2", ...],
  "prerequis": ["prérequis 1", "prérequis 2", ...],
  "type_exercice": "type",
  "temps_estime": "temps"
}}

Voici l'exercice:
{latex_content}"""

def create_resume_prompt(latex_content: str) -> str:
    """Create prompt for summary extraction via Gemini API."""
    return f"""Voici un exercice de mathématiques au format LaTeX. Analyse-le et génère un résumé synthétique de l'exercice. 
Ne réécris pas les questions, formule plutôt les compétences mises en oeuvre et sois concis. 
Si tu utilises des formules mathématiques, mets les entre $.
Réponds uniquement en format JSON structuré avec cette clé exacte:
{{
  "resume": "résumé"
}}

Voici l'exercice:
{latex_content}"""
