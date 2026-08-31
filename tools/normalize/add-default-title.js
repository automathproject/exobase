const fs = require('fs').promises;
const path = require('path');
const { randomUUID } = require('crypto');

const args = process.argv.slice(2);
const dryRun = args.includes('--dry-run');
const targetArg = args.find(a => a !== '--dry-run');
const defaultDir = path.join(__dirname, '..', 'src', 'latex');
const targetPath = targetArg ? path.resolve(targetArg) : defaultDir;

async function addTitleToFile(filePath) {
  let content;
  try {
    content = await fs.readFile(filePath, 'utf8');
  } catch (err) {
    console.error(`❌ Impossible de lire le fichier ${filePath}`, err);
    return false;
  }

  if (/\\titre\s*\{/.test(content)) {
    return false;
  }

  let id;
  if (/\\exo7id\{([^}]+)\}/.test(content)) {
    id = content.match(/\\exo7id\{([^}]+)\}/)[1].trim();
    content = content.replace(/(\\exo7id\{[^}]+\}\s*)/, `$1\\titre{exo7 ${id}}\n`);
  } else if (/\\uuid\{([^}]+)\}/.test(content)) {
    id = content.match(/\\uuid\{([^}]+)\}/)[1].trim();
    content = content.replace(/(\\uuid\{[^}]+\}\s*)/, `$1\\titre{exo7 ${id}}\n`);
  } else {
    id = randomUUID();
    content = `\\titre{exo7 ${id}}\n${content}`;
  }

  if (!dryRun) {
    try {
      await fs.writeFile(filePath, content, 'utf8');
    } catch (err) {
      console.error(`❌ Impossible d'écrire le fichier ${filePath}`, err);
      return false;
    }
  }

  return id;
}

async function processPath(p) {
  const stat = await fs.stat(p);
  if (stat.isDirectory()) {
    const entries = await fs.readdir(p, { withFileTypes: true });
    for (const entry of entries) {
      await processPath(path.join(p, entry.name));
    }
  } else if (stat.isFile() && p.endsWith('.tex')) {
    const id = await addTitleToFile(p);
    if (id) {
      console.log(`${dryRun ? '[dry-run] ' : ''}Titre ajouté dans ${p} -> exo7 ${id}`);
    }
  }
}

processPath(targetPath)
  .then(() => console.log('Terminé'))
  .catch(err => {
    console.error('Erreur:', err);
    process.exit(1);
  });
