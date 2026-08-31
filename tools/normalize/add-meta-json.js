// script/add-meta-json.js
const fs = require('fs').promises;
const path = require('path');

// Récupérer les arguments de ligne de commande
const args = process.argv.slice(2);

// Vérifier si on a assez d'arguments
if (args.length < 2) {
  console.error('Usage: node script.js <inputDir> <outputDir>');
  console.error('  - inputDir: répertoire contenant les fichiers JSON avec les champs à ajouter');
  console.error('  - outputDir: répertoire contenant les fichiers JSON originaux à modifier');
  process.exit(1);
}

// Récupérer les répertoires depuis les arguments
const inputDir = args[0];
const outputDir = args[1];

async function mergeJsonFiles() {
  try {
    // Vérifier que les répertoires existent
    try {
      await fs.access(inputDir);
      await fs.access(outputDir);
    } catch (err) {
      console.error(`Erreur: Un des répertoires n'existe pas.`);
      process.exit(1);
    }
    
    // Lire tous les fichiers dans le répertoire de sortie (où sont les fichiers à modifier)
    const outputFiles = await fs.readdir(outputDir);
    
    // Filtrer pour ne garder que les fichiers JSON
    const jsonOutputFiles = outputFiles.filter(file => file.endsWith('.json'));
    
    console.log(`Traitement de ${jsonOutputFiles.length} fichiers JSON...`);
    
    let filesUpdated = 0;
    let filesNotFound = 0;
    
    // Traiter chaque fichier JSON
    for (const file of jsonOutputFiles) {
      try {
        // Extraire l'UUID du nom de fichier
        const uuid = path.basename(file, '.json');
        
        // Lire le fichier JSON du répertoire de sortie (à modifier)
        const outputData = JSON.parse(await fs.readFile(path.join(outputDir, file), 'utf8'));
        
        // Chercher le fichier correspondant dans le répertoire d'entrée
        const inputFile = path.join(inputDir, `${uuid}.json`);
        
        try {
          // Lire le fichier avec les champs supplémentaires
          const inputData = JSON.parse(await fs.readFile(inputFile, 'utf8'));
          
          // Ajouter les champs supplémentaires aux métadonnées existantes
          outputData.metadata = {
            ...outputData.metadata,
            resume: inputData.resume,
            competences: inputData.competences,
            niveau_difficulte: inputData.niveau_difficulte,
            mots_cles: inputData.mots_cles,
            concepts_fondamentaux: inputData.concepts_fondamentaux,
            prerequis: inputData.prerequis,
            type_exercice: inputData.type_exercice,
            temps_estime: inputData.temps_estime
          };
          
          // Écrire le fichier JSON mis à jour dans le répertoire de sortie
          await fs.writeFile(
            path.join(outputDir, file),
            JSON.stringify(outputData, null, 2),
            'utf8'
          );
          
          console.log(`✅ Fichier ${file} mis à jour avec succès.`);
          filesUpdated++;
        } catch (err) {
          if (err.code === 'ENOENT') {
            console.log(`⚠️ Aucun fichier d'entrée trouvé pour ${uuid}. Le fichier ne sera pas modifié.`);
            filesNotFound++;
          } else {
            throw err;
          }
        }
      } catch (err) {
        console.error(`❌ Erreur lors du traitement du fichier ${file}:`, err);
      }
    }
    
    console.log(`\nTraitement terminé!`);
    console.log(`- ${filesUpdated} fichiers mis à jour`);
    console.log(`- ${filesNotFound} fichiers sans correspondance`);
    console.log(`- ${jsonOutputFiles.length - filesUpdated - filesNotFound} fichiers avec erreur`);
  } catch (err) {
    console.error('Erreur générale:', err);
  }
}

// Exécuter la fonction principale
mergeJsonFiles();
