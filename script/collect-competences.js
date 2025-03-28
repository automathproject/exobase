const fs = require('fs');
const path = require('path');

// Fonction pour accéder à une propriété imbriquée via une chaîne de chemin (e.g., "metadata.competences")
function getNestedProperty(obj, propertyPath) {
  const properties = propertyPath.split('.');
  return properties.reduce((prev, curr) => {
    return prev && prev[curr] !== undefined ? prev[curr] : undefined;
  }, obj);
}

// Fonction principale
function collectCompetences(directoryPath, propertyPath = 'metadata.competences') {
  // Structure résultante: { competence1: [uuid1, uuid2, ...], competence2: [...], ... }
  const competencesMap = {};
  
  try {
    // Vérifier que le répertoire existe
    if (!fs.existsSync(directoryPath)) {
      throw new Error(`Le répertoire "${directoryPath}" n'existe pas.`);
    }
    
    // Lire tous les fichiers du répertoire
    const files = fs.readdirSync(directoryPath);
    
    // Filtrer pour ne garder que les fichiers JSON
    const jsonFiles = files.filter(file => path.extname(file) === '.json');
    
    console.log(`Traitement de ${jsonFiles.length} fichiers JSON dans ${directoryPath}...`);
    
    // Traiter chaque fichier JSON
    jsonFiles.forEach(file => {
      try {
        // Extraire l'UUID du nom du fichier
        const uuid = path.basename(file, '.json');
        
        // Lire et parser le contenu du fichier
        const fileContent = fs.readFileSync(path.join(directoryPath, file), 'utf8');
        const data = JSON.parse(fileContent);
        
        // Récupérer la valeur de la propriété imbriquée (ex: metadata.competences)
        const competences = getNestedProperty(data, propertyPath);
        
        // Vérifier si la propriété existe et est un tableau
        if (competences && Array.isArray(competences)) {
          // Ajouter chaque compétence à notre map
          competences.forEach(competence => {
            if (!competencesMap[competence]) {
              competencesMap[competence] = [];
            }
            // Ajouter l'UUID s'il n'est pas déjà présent
            if (!competencesMap[competence].includes(uuid)) {
              competencesMap[competence].push(uuid);
            }
          });
        }
      } catch (fileError) {
        console.error(`Erreur lors du traitement du fichier ${file}:`, fileError);
      }
    });
    
    // Conversion vers le format final
    const result = {};
    for (const [competence, uuids] of Object.entries(competencesMap)) {
      result[competence] = { uuid: uuids };
    }
    
    // Extraire le nom de la propriété pour le nom du fichier de sortie
    const propertyName = propertyPath.split('.').pop();
    
    // Déterminer le chemin du répertoire parent
    const parentDirPath = path.resolve(directoryPath, '..');
    const outputFilePath = path.join(parentDirPath, `${propertyName}_uniques.json`);
    
    // Écrire le résultat dans un fichier JSON dans le répertoire parent
    fs.writeFileSync(outputFilePath, JSON.stringify(result, null, 2), 'utf8');
    console.log(`Fichier "${outputFilePath}" créé avec succès`);
    
    return result;
  } catch (error) {
    console.error('Erreur lors de la collecte des compétences:', error);
    return null;
  }
}

// Récupérer les arguments
const args = process.argv.slice(2);

if (args.length === 0) {
  console.error('Erreur: Veuillez spécifier le chemin du répertoire en argument.');
  console.log('Exemple d\'utilisation: node collectCompetences.js ./mon_repertoire [metadata.competences]');
  console.log('Le second argument est facultatif et correspond au chemin de la propriété à extraire (par défaut: metadata.competences)');
  process.exit(1);
}

const directoryPath = args[0];
const propertyPath = args.length > 1 ? args[1] : 'metadata.competences';

console.log(`Extraction de la propriété "${propertyPath}" depuis les fichiers JSON...`);
collectCompetences(directoryPath, propertyPath);
