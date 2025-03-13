const fs = require('fs');
const path = require('path');
const directories = ['src/amscc', 'src/exo7'];
const outputFile = 'index.json';
let index = {};

// Fonction récursive pour explorer les répertoires et sous-répertoires
function exploreDirectory(directory) {
  const items = fs.readdirSync(directory, { withFileTypes: true });
  
  for (const item of items) {
    const fullPath = path.join(directory, item.name);
    
    if (item.isDirectory()) {
      // Si c'est un répertoire, on l'explore récursivement
      exploreDirectory(fullPath);
    } else if (item.isFile() && path.extname(item.name) === '.tex') {
      // Si c'est un fichier .tex, on l'analyse
      const content = fs.readFileSync(fullPath, 'utf8');
      const uuidMatch = content.match(/\\uuid\{([^\}]+)\}/);
      
      if (uuidMatch) {
        const uuid = uuidMatch[1];
        // Construction du chemin relatif pour GitHub
        // Utilisation de path.relative pour obtenir le chemin relatif à partir 
        // de la racine du projet
        const repoPath = fullPath.replace(/\\/g, '/'); // Normalisation des séparateurs pour GitHub
        const url = `https://github.com/automathproject/exobase/blob/main/${repoPath}`;
        index[uuid] = url;
      }
    }
  }
}

// Parcourir chaque répertoire de base
for (const dir of directories) {
  exploreDirectory(dir);
}

// Écriture du fichier index.json
fs.writeFileSync(outputFile, JSON.stringify(index, null, 2));

console.log(`Index créé avec ${Object.keys(index).length} entrées dans ${outputFile}`);