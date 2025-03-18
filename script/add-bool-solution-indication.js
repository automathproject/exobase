const fs = require('fs').promises;
const path = require('path');

// Fonction pour trouver tous les fichiers JSON de manière récursive
async function findJsonFiles(directory) {
  let jsonFiles = [];
  
  // Lire le contenu du répertoire
  const items = await fs.readdir(directory, { withFileTypes: true });
  
  // Parcourir chaque élément
  for (const item of items) {
    const itemPath = path.join(directory, item.name);
    
    if (item.isDirectory()) {
      // Si c'est un dossier, rechercher récursivement
      const subDirFiles = await findJsonFiles(itemPath);
      jsonFiles = jsonFiles.concat(subDirFiles);
    } else if (item.isFile() && path.extname(item.name) === '.json') {
      // Si c'est un fichier JSON, l'ajouter à la liste
      jsonFiles.push(itemPath);
    }
  }
  
  return jsonFiles;
}

// Fonction pour traiter un fichier JSON
async function processJsonFile(filePath) {
  try {
    // Lire le contenu du fichier
    const fileContent = await fs.readFile(filePath, 'utf8');
    const jsonData = JSON.parse(fileContent);
    
    let hasModified = false;
    
    // Vérifier et mettre à jour hasCorrection si nécessaire
    if (jsonData.metadata.hasCorrection === "") {
      // Chercher des éléments de type "reponse" non vides
      const hasReponse = jsonData.contenu.some(item => 
        item.type === "reponse" && 
        item.value && 
        ((item.value.latex && item.value.latex.trim() !== "") || 
         (item.value.html && item.value.html.trim() !== ""))
      );
      
      jsonData.metadata.hasCorrection = hasReponse;
      hasModified = true;
    }
    
    // Vérifier et mettre à jour hasIndication si nécessaire
    if (jsonData.metadata.hasIndication === "") {
      // Chercher des éléments de type "indication" non vides
      const hasIndication = jsonData.contenu.some(item => 
        item.type === "indication" && 
        item.value && 
        ((item.value.latex && item.value.latex.trim() !== "") || 
         (item.value.html && item.value.html.trim() !== ""))
      );
      
      jsonData.metadata.hasIndication = hasIndication;
      hasModified = true;
    }
    
    // Si des modifications ont été effectuées, écrire le fichier
    if (hasModified) {
      await fs.writeFile(filePath, JSON.stringify(jsonData, null, 2), 'utf8');
      console.log(`Mis à jour: ${filePath}`);
      return true;
    }
    
    return false;
  } catch (error) {
    console.error(`Erreur lors du traitement de ${filePath}:`, error.message);
    return false;
  }
}

// Fonction principale
async function main() {
  try {
    const sourceDir = path.resolve('src/json');
    console.log(`Recherche de fichiers JSON dans ${sourceDir}...`);
    
    // Trouver tous les fichiers JSON
    const jsonFiles = await findJsonFiles(sourceDir);
    console.log(`${jsonFiles.length} fichiers JSON trouvés.`);
    
    // Traiter chaque fichier
    let modifiedCount = 0;
    for (const filePath of jsonFiles) {
      const modified = await processJsonFile(filePath);
      if (modified) modifiedCount++;
    }
    
    console.log(`Terminé ! ${modifiedCount} fichiers ont été mis à jour.`);
  } catch (error) {
    console.error('Erreur:', error.message);
    process.exit(1);
  }
}

// Exécuter la fonction principale
main();