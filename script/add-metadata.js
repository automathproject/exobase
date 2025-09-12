const fs = require('fs').promises;
const path = require('path');

const args = process.argv.slice(2);
const dryRun = args.includes('--dry-run');
const targetArg = args.find(a => a !== '--dry-run');
const defaultDir = path.join(__dirname, '..', 'src', 'latex', 'exo7');
const targetPath = targetArg ? path.resolve(targetArg) : defaultDir;

const metadataPath = path.join(__dirname, '..', 'info_migration', 'exo7', 'exercices.json');
let metaByUuid = new Map();
let metaByExo7id = new Map();

async function loadMetadata() {
  const raw = await fs.readFile(metadataPath, 'utf8');
  const data = JSON.parse(raw);
  data.forEach(entry => {
    if (entry.uuid) metaByUuid.set(entry.uuid, entry);
    if (entry.exo7id !== undefined) metaByExo7id.set(String(entry.exo7id), entry);
  });
}

function findMeta(id, isUuid) {
  if (isUuid) return metaByUuid.get(id);
  return metaByExo7id.get(id) || metaByUuid.get(id);
}

async function addMetadataToFile(file) {
  let content;
  try {
    content = await fs.readFile(file, 'utf8');
  } catch (err) {
    console.error(`❌ Lecture impossible ${file}`, err);
    return;
  }

  const hasModule = /\\module\{[^}]*\}/.test(content);
  const hasNiveau = /\\niveau\{[^}]*\}/.test(content);
  const hasDifficulte = /\\difficulte\{[^}]*\}/.test(content);

  if (hasModule && hasNiveau && hasDifficulte) return;

  let idMatch = content.match(/\\uuid\{([^}]+)\}/);
  let isUuid = false;
  let id;
  if (idMatch) {
    id = idMatch[1].trim();
    isUuid = true;
  } else {
    idMatch = content.match(/\\exo7id\{([^}]+)\}/);
    if (idMatch) id = idMatch[1].trim();
  }
  if (!id) return;

  const meta = findMeta(id, isUuid);
  if (!meta) return;

  const lines = content.split('\n');
  let insertIndex = lines.findIndex(l => l.trim() === '');
  if (insertIndex === -1) insertIndex = lines.length;

  const newLines = [];
  if (!hasModule && meta.moduleDescription) newLines.push(`\\module{${meta.moduleDescription}}`);
  if (!hasNiveau && meta.niveau) newLines.push(`\\niveau{${meta.niveau}}`);
  if (!hasDifficulte) newLines.push('\\difficulte{}');

  if (newLines.length === 0) return;

  lines.splice(insertIndex, 0, ...newLines);

  if (!dryRun) {
    try {
      await fs.writeFile(file, lines.join('\n'), 'utf8');
    } catch (err) {
      console.error(`❌ Écriture impossible ${file}`, err);
      return;
    }
  }
  console.log(`${dryRun ? '[dry-run] ' : ''}Métadonnées ajoutées dans ${file}`);
}

async function processPath(p) {
  const stat = await fs.stat(p);
  if (stat.isDirectory()) {
    const entries = await fs.readdir(p, { withFileTypes: true });
    for (const entry of entries) {
      await processPath(path.join(p, entry.name));
    }
  } else if (stat.isFile() && p.endsWith('.tex')) {
    await addMetadataToFile(p);
  }
}

loadMetadata()
  .then(() => processPath(targetPath))
  .then(() => console.log('Terminé'))
  .catch(err => {
    console.error('Erreur:', err);
    process.exit(1);
  });
