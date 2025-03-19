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

// Fonction pour obtenir le répertoire racine d'un chemin de fichier (premier répertoire après src/json/)
function getRootDirectory(filePath, baseDir) {
  // Obtenir le chemin relatif par rapport au répertoire de base
  const relativePath = path.relative(baseDir, filePath);
  // Obtenir le premier segment du chemin (le répertoire racine)
  const parts = relativePath.split(path.sep);
  return parts[0];
}

// Fonction pour créer des bundles
async function createBundles(jsonFiles, baseDir, outputDir) {
  // Organiser les fichiers par répertoire racine
  const filesByRoot = {};
  
  for (const filePath of jsonFiles) {
    const rootDir = getRootDirectory(filePath, baseDir);
    
    if (!filesByRoot[rootDir]) {
      filesByRoot[rootDir] = [];
    }
    
    // Lire et parser le fichier JSON
    try {
      const fileContent = await fs.readFile(filePath, 'utf8');
      const jsonData = JSON.parse(fileContent);
      
      filesByRoot[rootDir].push(jsonData);
    } catch (error) {
      console.error(`Erreur lors de la lecture de ${filePath}:`, error.message);
    }
  }
  
  // Créer des bundles par répertoire racine
  for (const rootDir in filesByRoot) {
    const files = filesByRoot[rootDir];
    const MAX_ENTRIES_PER_BUNDLE = 300;
    
    // Diviser les fichiers en bundles de MAX_ENTRIES_PER_BUNDLE
    const bundleCount = Math.ceil(files.length / MAX_ENTRIES_PER_BUNDLE);
    
    for (let i = 0; i < bundleCount; i++) {
      // Sélectionner les fichiers pour ce bundle
      const startIndex = i * MAX_ENTRIES_PER_BUNDLE;
      const endIndex = Math.min((i + 1) * MAX_ENTRIES_PER_BUNDLE, files.length);
      const bundleFiles = files.slice(startIndex, endIndex);
      
      // Créer le bundle
      const bundle = {};
      
      for (const file of bundleFiles) {
        // Utiliser l'UUID comme clé d'entrée dans le bundle
        if (file.uuid) {
          bundle[file.uuid] = file;
        }
      }
      
      // Définir le nom du fichier bundle
      const bundleFileName = `${rootDir}-bundle-part${i + 1}.json`;
      const bundleFilePath = path.join(outputDir, bundleFileName);
      
      // Écrire le bundle dans un fichier
      try {
        await fs.mkdir(outputDir, { recursive: true }); // Créer le répertoire s'il n'existe pas
        await fs.writeFile(bundleFilePath, JSON.stringify(bundle, null, 2), 'utf8');
        console.log(`Bundle créé: ${bundleFilePath} avec ${bundleFiles.length} entrées`);
      } catch (error) {
        console.error(`Erreur lors de l'écriture de ${bundleFilePath}:`, error.message);
      }
    }
  }
}

// Fonction principale
async function main() {
  try {
    const sourceDir = path.resolve('src/json');
    const outputDir = path.resolve('src/bundles');
    
    console.log(`Recherche de fichiers JSON dans ${sourceDir}...`);
    
    // Trouver tous les fichiers JSON
    const jsonFiles = await findJsonFiles(sourceDir);
    console.log(`${jsonFiles.length} fichiers JSON trouvés.`);
    
    // Créer des bundles
    await createBundles(jsonFiles, sourceDir, outputDir);
    
    console.log(`Terminé ! Les bundles ont été créés dans ${outputDir}.`);
  } catch (error) {
    console.error('Erreur:', error.message);
    process.exit(1);
  }
}

// Exécuter la fonction principale
main();