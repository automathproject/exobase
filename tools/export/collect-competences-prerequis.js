const fs = require('fs');
const path = require('path');

// Fonction pour accéder à une propriété imbriquée via une chaîne de chemin (e.g., "metadata.competences")
function getNestedProperty(obj, propertyPath) {
  const properties = propertyPath.split('.');
  return properties.reduce((prev, curr) => {
    return prev && prev[curr] !== undefined ? prev[curr] : undefined;
  }, obj);
}

// Fonction principale modifiée pour extraire plusieurs propriétés
function collectProperties(directoryPath, propertyPaths = ['metadata.competences', 'metadata.prerequis']) {
  // Vérifier que propertyPaths est un tableau
  if (!Array.isArray(propertyPaths)) {
    propertyPaths = [propertyPaths];
  }

  // Créer un objet pour stocker les résultats pour chaque propriété
  const results = {};
  propertyPaths.forEach(propPath => {
    // Extraire le nom de la propriété pour la clé dans results
    const propName = propPath.split('.').pop();
    results[propName] = {
      _metadata: {
        total_count: 0  // Compteur pour le nombre total de compétences uniques
      }
    };
  });

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

        // Pour chaque propriété à extraire
        propertyPaths.forEach(propPath => {
          const propName = propPath.split('.').pop();
          
          // Récupérer la valeur de la propriété imbriquée (ex: metadata.competences)
          const values = getNestedProperty(data, propPath);
          
          // Vérifier si la propriété existe et est un tableau
          if (values && Array.isArray(values)) {
            // Ajouter chaque valeur à notre map
            values.forEach(value => {
              if (!results[propName][value]) {
                results[propName][value] = { 
                  uuid: [],
                  count: 0  // Initialiser le compteur
                };
                // Incrémenter le compteur total des compétences uniques
                results[propName]._metadata.total_count++;
              }
              
              // Ajouter l'UUID s'il n'est pas déjà présent
              if (!results[propName][value].uuid.includes(uuid)) {
                results[propName][value].uuid.push(uuid);
                results[propName][value].count++;  // Incrémenter le compteur
              }
            });
          }
        });
      } catch (fileError) {
        console.error(`Erreur lors du traitement du fichier ${file}:`, fileError);
      }
    });

    // Déterminer le chemin du répertoire parent
    const parentDirPath = path.resolve(directoryPath, '..');
    
    // Calculer quelques statistiques supplémentaires
    for (const propName in results) {
      // Calculer le nombre total d'occurrences (somme de tous les counts)
      let totalOccurrences = 0;
      for (const value in results[propName]) {
        if (value !== '_metadata') {
          totalOccurrences += results[propName][value].count;
        }
      }
      
      // Ajouter ces statistiques aux métadonnées
      results[propName]._metadata.total_occurrences = totalOccurrences;
    }
    
    // Écrire un fichier de sortie pour chaque propriété avec un format de JSON spécifique
    for (const [propName, propData] of Object.entries(results)) {
      const outputFilePath = path.join(parentDirPath, `${propName}_uniques.json`);
      
      // Configurer le JSON.stringify pour forcer l'écriture des UUID en ligne
      const formattedJson = JSON.stringify(propData, null, 2)
        // Cette regex remplace les tableaux d'UUID formattés sur plusieurs lignes par des tableaux en ligne
        .replace(/\[\n\s+(?:".+",\n\s+)+".+"\n\s+\]/g, match => {
          // Transformer le tableau formaté en tableau sur une seule ligne
          return JSON.stringify(JSON.parse(match));
        });
      
      fs.writeFileSync(outputFilePath, formattedJson, 'utf8');
      console.log(`Fichier "${outputFilePath}" créé avec succès`);
    }

    return results;
  } catch (error) {
    console.error('Erreur lors de la collecte des propriétés:', error);
    return null;
  }
}

// Récupérer les arguments
const args = process.argv.slice(2);
if (args.length === 0) {
  console.error('Erreur: Veuillez spécifier le chemin du répertoire en argument.');
  console.log('Exemple d\'utilisation: node collectProperties.js ./mon_repertoire [metadata.competences,metadata.prerequis]');
  console.log('Le second argument est facultatif et correspond aux chemins des propriétés à extraire (par défaut: metadata.competences,metadata.prerequis)');
  process.exit(1);
}

const directoryPath = args[0];
let propertyPaths = ['metadata.competences', 'metadata.prerequis']; // Valeurs par défaut

// Si l'utilisateur a spécifié des propriétés personnalisées
if (args.length > 1) {
  propertyPaths = args[1].split(',').map(path => path.trim());
}

console.log(`Extraction des propriétés "${propertyPaths.join(', ')}" depuis les fichiers JSON...`);
collectProperties(directoryPath, propertyPaths);