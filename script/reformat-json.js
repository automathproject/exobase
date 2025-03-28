const fs = require('fs').promises;
const path = require('path');

/**
 * Reformate le contenu JSON en supprimant le niveau d'imbrication de l'UUID
 * @param {string} jsonContent - Le contenu JSON à reformater
 * @param {string} uuid - L'UUID qui sert de clé principale
 * @returns {string} - Le contenu JSON reformaté
 */
function reformatJson(jsonContent, uuid) {
  try {
    // Analyser le contenu JSON
    const jsonData = JSON.parse(jsonContent);
    
    // Vérifier si l'UUID existe comme clé principale
    if (jsonData[uuid]) {
      // Remplacer le contenu entier par le contenu sous l'UUID
      const reformatted = jsonData[uuid];
      // Retourner le JSON reformaté avec indentation
      return JSON.stringify(reformatted, null, 2);
    } else {
      console.log(`UUID "${uuid}" non trouvé dans le fichier "${uuid}.json"`);
      return jsonContent; // Retourner le contenu original si l'UUID n'est pas trouvé
    }
  } catch (error) {
    console.error(`Erreur lors du traitement du JSON: ${error.message}`);
    return jsonContent; // Retourner le contenu original en cas d'erreur
  }
}

/**
 * Parcourt le répertoire et traite tous les fichiers JSON
 * @param {string} directoryPath - Le chemin du répertoire à traiter
 */
async function processDirectory(directoryPath) {
  try {
    // Lire tous les fichiers du répertoire
    const files = await fs.readdir(directoryPath);
    
    // Compter les fichiers traités
    let filesProcessed = 0;
    let filesModified = 0;
    
    // Traiter chaque fichier JSON
    for (const file of files) {
      // Vérifier si le fichier est un JSON
      if (path.extname(file) === '.json') {
        const filePath = path.join(directoryPath, file);
        
        // Extraire l'UUID du nom de fichier (sans l'extension .json)
        const uuid = path.basename(file, '.json');
        
        // Lire le contenu du fichier
        const content = await fs.readFile(filePath, 'utf8');
        
        // Reformater le contenu
        const reformattedContent = reformatJson(content, uuid);
        
        // Si le contenu a changé, écrire le nouveau contenu
        if (content !== reformattedContent) {
          await fs.writeFile(filePath, reformattedContent, 'utf8');
          console.log(`Fichier reformaté: ${file}`);
          filesModified++;
        }
        
        filesProcessed++;
      }
    }
    
    console.log(`\nTerminé: ${filesProcessed} fichiers JSON traités, ${filesModified} fichiers modifiés.`);
  } catch (error) {
    console.error(`Erreur: ${error.message}`);
  }
}

// Récupérer le chemin du répertoire depuis les arguments de la ligne de commande
const directoryPath = process.argv[2];

if (!directoryPath) {
  console.error('Veuillez spécifier le chemin du répertoire à traiter.');
  console.log('Utilisation: node reformatJson.js <chemin_du_repertoire>');
  process.exit(1);
}

// Vérifier si le répertoire existe
fs.stat(directoryPath)
  .then(stats => {
    if (stats.isDirectory()) {
      console.log(`Traitement des fichiers JSON dans: ${directoryPath}`);
      processDirectory(directoryPath);
    } else {
      console.error('Le chemin spécifié n\'est pas un répertoire.');
      process.exit(1);
    }
  })
  .catch(error => {
    console.error(`Erreur: ${error.message}`);
    process.exit(1);
  });
