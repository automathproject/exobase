/**  Script pour convertir les fichiers LaTeX en JSON
 * src/script/convertTex2JsonV4.js */
 import fs from 'fs';
 import path from 'path';
 import { exec } from 'child_process';
 import util from 'util';
 import os from 'os';
 import crypto from 'crypto';
 
 import {
   preprocessLatex,
   stripComments,
   wrapAlignWithDollar,
   isCommandCommented,
   convertLaTeXToHTML
 } from './utils/Tex2HtmlUtils.js';
 
 import {
   extractAndConvertTikzBlocks,
   checkDependencies
 } from './utils/Tikz2SvgUtils.js';

 import { generatePreview } from './utils/PreviewUtils.js';
 
 const fsPromises = fs.promises;
 const execPromise = util.promisify(exec);
 
 function generateUniqueId() {
   return crypto.randomUUID();
 }
 
 /**
  * Fonction pour extraire et remplacer les blocs TikZ par des identifiants uniques
  * @param {string} latex - Contenu LaTeX
  * @returns {Promise<{modifiedLatex: string, tikzMap: Map<string, string>}>}
  */
 async function preprocessTikzBlocks(latex) {
   try {
     const blocks = await extractAndConvertTikzBlocks(latex);
     let modifiedLatex = latex;
     const tikzMap = new Map();
 
     for (const block of blocks) {
       if (block && block.original) {
         const id = `__TIKZ_${generateUniqueId()}__`;
         tikzMap.set(id, block.svg);
         modifiedLatex = modifiedLatex.replace(block.original, id);
       }
     }
 
     return { modifiedLatex, tikzMap };
   } catch (error) {
     console.error('Erreur lors du prétraitement des blocs TikZ:', error);
     // En cas d'erreur, retourner le LaTeX original sans modification
     return { modifiedLatex: latex, tikzMap: new Map() };
   }
 }
 
 /**
  * Fonction pour restaurer les SVGs dans le HTML
  * @param {string} html - Contenu HTML
  * @param {Map<string, string>} tikzMap - Map des identifiants vers les SVGs
  * @returns {string}
  */
 function restoreTikzSvg(html, tikzMap) {
   let result = html;
   for (const [id, svg] of tikzMap.entries()) {
     result = result.replace(id, svg);
   }
   return result;
 }
 
 /**
  * Fonction principale pour extraire les commandes LaTeX
  * @param {string} latex - Contenu LaTeX
  * @param {Array} commands - Liste des commandes à extraire
  * @param {string} [fileName="fichier inconnu"] - Nom complet du fichier LaTeX (pour la gestion des erreurs)
  */
 async function extractLaTeXCommands(latex, commands, fileName = "fichier inconnu") {
   const extracted = {
     uuid: "",
     titre: "",
     theme: [],
     niveau: "",
     metadata: {},
     contenu: []
   };
 
   // Vérifier les dépendances TikZ
   const deps = await checkDependencies();
   if (!deps.success) {
     console.warn('Attention: Support TikZ désactivé -', deps.error);
   }
 
   // Prétraiter les blocs TikZ si les dépendances sont disponibles
   let modifiedLatex = latex;
   let tikzMap = new Map();
 
   if (deps.success) {
     const { modifiedLatex: processed, tikzMap: blocks } = await preprocessTikzBlocks(latex);
     modifiedLatex = processed;
     tikzMap = blocks;
   }
 
   // Initialiser les champs uniques
   commands.filter(cmd => !cmd.isContent).forEach(cmd => {
     const keys = cmd.jsonKey.split('.');
     let obj = extracted;
     for (let i = 0; i < keys.length - 1; i++) {
       if (!(keys[i] in obj)) {
         obj[keys[i]] = {};
       }
       obj = obj[keys[i]];
     }
     const lastKey = keys[keys.length - 1];
     obj[lastKey] = "";
   });
 
   // Créer une regex pour toutes les commandes à extraire
   const allCommandNames = commands.map(cmd => cmd.name).join('|');
   const regex = new RegExp(`(?<!\\\\)\\\\(${allCommandNames})\\s*\\{`, 'g');
 
   let match;
   while ((match = regex.exec(modifiedLatex)) !== null) {
     const commandName = match[1];
     const commandObj = commands.find(cmd => cmd.name === commandName);
     if (!commandObj) continue;
 
     const matchStart = match.index;
     const lineStart = modifiedLatex.lastIndexOf('\n', matchStart) + 1;
     const lineEnd = modifiedLatex.indexOf('\n', matchStart);
     const line = modifiedLatex.substring(lineStart, lineEnd === -1 ? modifiedLatex.length : lineEnd);
     const commandPosInLine = match.index - lineStart;
 
     if (isCommandCommented(line, commandPosInLine)) {
       continue;
     }
 
     let startIndex = match.index + match[0].length;
     let index = startIndex;
     let braceCount = 1;
     let content = '';
 
     while (braceCount > 0 && index < modifiedLatex.length) {
       const char = modifiedLatex[index];
       if (char === '\\') {
         content += char;
         index++;
         if (index < modifiedLatex.length) {
           content += modifiedLatex[index];
         }
       } else if (char === '{') {
         braceCount++;
         content += char;
       } else if (char === '}') {
         braceCount--;
         if (braceCount > 0) {
           content += char;
         }
       } else {
         content += char;
       }
       index++;
     }
 
     let finalContent = commandObj.isVerbatim ? content.trim() : stripComments(content.trim());
     if (commandObj.isContent) {
       finalContent = wrapAlignWithDollar(finalContent);
     }
 
     if (commandObj.isContent) {
       let htmlContent = "";
       // Encapsulation de l'appel à Pandoc pour capter d'éventuelles erreurs
       try {
         htmlContent = await convertLaTeXToHTML(finalContent);
       } catch (error) {
         console.error(`Erreur lors de la conversion LaTeX -> HTML avec pandoc pour le fichier ${fileName} : ${error.message}`);
         // Vous pouvez choisir de renvoyer un contenu d'erreur ou de laisser une chaîne vide
         htmlContent = `<div class="error">Erreur de conversion pour le fichier ${fileName} : ${error.message}</div>`;
       }
 
       // Restaurer les SVGs dans le HTML si nécessaire
       if (deps.success) {
         htmlContent = restoreTikzSvg(htmlContent, tikzMap);
       }
 
       const id = generateUniqueId();
       extracted.contenu.push({
         id: id,
         type: commandName === 'texte' ? 'description' : commandName,
         value: {
           latex: finalContent,
           html: htmlContent
         }
       });
     } else {
       const keys = commandObj.jsonKey.split('.');
       let obj = extracted;
       for (let i = 0; i < keys.length - 1; i++) {
         if (!(keys[i] in obj)) {
           obj[keys[i]] = {};
         }
         obj = obj[keys[i]];
       }
       const lastKey = keys[keys.length - 1];
 
       if (lastKey === 'theme') {
         obj[lastKey] = finalContent.split(',').map(s => s.trim());
       } else {
         obj[lastKey] = preprocessLatex(finalContent);
       }
     }
   }
 
   // Ajouter les timestamps dans metadata
   const now = new Date().toISOString();
   if (!extracted.metadata.createdAt) {
     extracted.metadata.createdAt = now;
   }
   extracted.metadata.updatedAt = now;
 
   return extracted;
 }
 
 /**
  * Fonction pour traiter un fichier .tex et générer le fichier .json correspondant.
  * Le paramètre outputDir est le répertoire dans lequel sera créé le fichier de sortie.
  * @returns {Promise<boolean>} - true si le fichier est ignoré (déjà à jour en mode --update)
  */
 async function processFile(inputFilePath, outputDir, commandsToExtract, options = { update: false }) {
    try {
      const outputFileName = path.basename(inputFilePath, path.extname(inputFilePath)) + '.json';
      const outputFilePath = path.join(outputDir, outputFileName);
  
      // Vérification du mode update (code existant)
      if (options.update && fs.existsSync(outputFilePath)) {
        const inputStats = fs.statSync(inputFilePath);
        const outputStats = fs.statSync(outputFilePath);
        if (outputStats.mtime >= inputStats.mtime) {
          return true;
        }
      }
  
      const latexContentRaw = await fsPromises.readFile(inputFilePath, 'utf8');
      const extractedData = await extractLaTeXCommands(latexContentRaw, commandsToExtract, inputFilePath);
  
      if (!extractedData.uuid) {
        extractedData.uuid = generateUniqueId();
      }
  
      // Générer la preview en utilisant PreviewUtils avec sa gestion native de la limite
      extractedData.preview = generatePreview(extractedData);
  
      await fsPromises.writeFile(outputFilePath, JSON.stringify(extractedData, null, 2), 'utf8');
      console.log(`Conversion réussie : ${inputFilePath} -> ${outputFilePath}`);
    } catch (error) {
      console.error(`Erreur lors du traitement du fichier ${inputFilePath} :`, error.message);
    }
    return false;
  }
 
 /**
  * Fonction récursive pour parcourir un répertoire et ses sous-répertoires.
  * Pour chaque fichier .tex rencontré, on effectue la conversion en JSON.
  * Les fichiers JSON de sortie sont créés dans outputDir en respectant la même arborescence.
  * @returns {Promise<number>} - Le nombre de fichiers ignorés en mode update.
  */
 async function traverseDirectory(inputDir, outputDir, commandsToExtract, updateMode) {
   let ignoredCount = 0;
   const entries = await fsPromises.readdir(inputDir, { withFileTypes: true });
 
   for (const entry of entries) {
     const fullInputPath = path.join(inputDir, entry.name);
     if (entry.isDirectory()) {
       // Créer le répertoire de sortie correspondant
       const correspondingOutputDir = path.join(outputDir, entry.name);
       if (!fs.existsSync(correspondingOutputDir)) {
         fs.mkdirSync(correspondingOutputDir, { recursive: true });
         console.log(`Répertoire de sortie créé : ${correspondingOutputDir}`);
       }
       ignoredCount += await traverseDirectory(fullInputPath, correspondingOutputDir, commandsToExtract, updateMode);
     } else if (entry.isFile() && path.extname(entry.name).toLowerCase() === '.tex') {
       const fileIgnored = await processFile(fullInputPath, outputDir, commandsToExtract, { update: updateMode });
       if (fileIgnored) ignoredCount++;
     }
   }
   return ignoredCount;
 }
 
 /**
  * Fonction principale
  */
 async function main() {
   const args = process.argv.slice(2);
 
   if (args.length < 1) {
     console.error("Usage : node convertLaTeXToJSON.js <chemin_du_fichier_ou_répertoire> [chemin_de_sortie] [--update]");
     process.exit(1);
   }
 
   const inputPath = path.resolve(args[0]);
   let outputPath = null;
   let updateMode = false;
 
   for (let i = 1; i < args.length; i++) {
     if (args[i] === '--update') {
       updateMode = true;
     } else {
       outputPath = path.resolve(args[i]);
     }
   }
 
   const commandsToExtract = [
     // Métadonnées de base
     { name: 'uuid', jsonKey: 'uuid', isContent: false, isVerbatim: false },
     { name: 'exo7id', jsonKey: 'metadata.exo7id', isContent: false, isVerbatim: false },
     { name: 'auteur', jsonKey: 'metadata.auteur', isContent: false, isVerbatim: false },
     { name: 'datecreate', jsonKey: 'metadata.createdAt', isContent: false, isVerbatim: false },
     
     // Configuration de l'exercice
     { name: 'isIndication', jsonKey: 'metadata.hasIndication', isContent: false, isVerbatim: false },
     { name: 'isCorrection', jsonKey: 'metadata.hasCorrection', isContent: false, isVerbatim: false },
     { name: 'video', jsonKey: 'metadata.youtube', isContent: false, isVerbatim: false },
     
     // Structure et organisation
     { name: 'chapitre', jsonKey: 'metadata.chapitre', isContent: false, isVerbatim: false },
     { name: 'sousChapitre', jsonKey: 'metadata.sousChapitre', isContent: false, isVerbatim: false },
     { name: 'titre', jsonKey: 'titre', isContent: false, isVerbatim: false },
     { name: 'theme', jsonKey: 'theme', isContent: false, isVerbatim: false },
     { name: 'niveau', jsonKey: 'niveau', isContent: false, isVerbatim: false },
     { name: 'organisation', jsonKey: 'metadata.organisation', isContent: false, isVerbatim: false },
     
     // Contenu de l'exercice
     { name: 'texte', jsonKey: 'contenu', isContent: true, isVerbatim: false },
     { name: 'question', jsonKey: 'contenu', isContent: true, isVerbatim: false },
     { name: 'reponse', jsonKey: 'contenu', isContent: true, isVerbatim: false },
     { name: 'indication', jsonKey: 'contenu', isContent: true, isVerbatim: false },
     { name: 'code', jsonKey: 'contenu', isContent: true, isVerbatim: true },
   ];
 
   if (!fs.existsSync(inputPath)) {
     console.error(`Le chemin spécifié n'existe pas : ${inputPath}`);
     process.exit(1);
   }
 
   const stats = fs.statSync(inputPath);
   let ignoredCount = 0;
 
   if (stats.isFile()) {
     if (path.extname(inputPath).toLowerCase() !== '.tex') {
       console.error(`Le fichier spécifié n'est pas un fichier .tex : ${inputPath}`);
       process.exit(1);
     }
     const outputDir = outputPath ? outputPath : path.dirname(inputPath);
     if (!fs.existsSync(outputDir)) {
       fs.mkdirSync(outputDir, { recursive: true });
       console.log(`Répertoire de sortie créé : ${outputDir}`);
     }
     const fileIgnored = await processFile(inputPath, outputDir, commandsToExtract, { update: updateMode });
     if (fileIgnored) ignoredCount++;
   } else if (stats.isDirectory()) {
     const inputDir = inputPath;
     const outputDir = outputPath ? outputPath : inputDir;
     if (!fs.existsSync(outputDir)) {
       fs.mkdirSync(outputDir, { recursive: true });
       console.log(`Répertoire de sortie créé : ${outputDir}`);
     }
     ignoredCount = await traverseDirectory(inputDir, outputDir, commandsToExtract, updateMode);
   } else {
     console.error(`Le chemin spécifié n'est ni un fichier ni un répertoire : ${inputPath}`);
     process.exit(1);
   }
 
   if (updateMode && ignoredCount > 0) {
     console.log(`\n${ignoredCount} fichier${ignoredCount > 1 ? 's' : ''} ignoré${ignoredCount > 1 ? 's' : ''} car déjà à jour.`);
   }
 }
 
 main().catch(error => {
   console.error("Une erreur inattendue s'est produite :", error);
   process.exit(1);
 });
 