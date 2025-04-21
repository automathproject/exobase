// mergeSkills.js

const fs = require('fs').promises;
const path = require('path');

async function loadMergePlan() {
  const planPath = path.join(__dirname, 'metadata', 'competences_unifiees.json');
  const raw = await fs.readFile(planPath, 'utf-8');
  const { merge_plan } = JSON.parse(raw);
  // Pour faciliter la recherche, on crée un map original_skill -> target_skill
  const map = new Map();
  for (const rule of merge_plan) {
    const target = rule.target_skill.trim();
    for (const orig of rule.original_skills) {
      map.set(orig.trim().toLowerCase(), target);
    }
  }
  return map;
}

async function processExercises() {
  const exercisesDir = path.join(__dirname, 'metadata', 'amscc', 'exercises');
  const files = await fs.readdir(exercisesDir);

  const mergeMap = await loadMergePlan();

  for (const file of files) {
    if (!file.endsWith('.json')) continue;
    const filePath = path.join(exercisesDir, file);
    const raw = await fs.readFile(filePath, 'utf-8');
    const data = JSON.parse(raw);

    if (Array.isArray(data.competences)) {
      const updated = [];

      for (const skill of data.competences) {
        const key = skill.trim().toLowerCase();
        if (mergeMap.has(key)) {
          // remplacer par la cible
          updated.push(mergeMap.get(key));
        } else {
          updated.push(skill.trim());
        }
      }
      // dédupliquer tout en préservant l'ordre
      data.competences = Array.from(new Set(updated));
    }

    // Écrire back
    await fs.writeFile(filePath, JSON.stringify(data, null, 2) + '\n', 'utf-8');
    console.log(`Mis à jour: ${file}`);
  }
}

processExercises()
  .then(() => console.log('✔️ Fusion terminée pour tous les exercices.'))
  .catch(err => {
    console.error('❌ Erreur lors de la fusion :', err);
    process.exit(1);
  });
