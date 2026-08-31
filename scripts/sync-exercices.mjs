#!/usr/bin/env node

/**
 * Mirrors the editorial AMSCC corpus from Exercices into exobase.
 *
 * Default mode is a dry run. The synchronisation is additive: files owned by
 * exobase but absent from Exercices are deliberately never deleted.
 */
import crypto from 'node:crypto';
import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const SOURCE_ROOT = process.env.EXERCISES_ROOT || path.resolve(ROOT, '../../COET/Exercices');
const SOURCE_SOURCES = path.join(SOURCE_ROOT, 'src');
const TARGET_SOURCES = path.join(ROOT, 'content/exercises/amscc');
const SOURCE_IMAGES = path.join(SOURCE_ROOT, 'img');
const TARGET_IMAGES = path.join(ROOT, 'content/images/amscc');
const IMAGE_FORMATS = ['svg', 'png', 'jpg', 'jpeg', 'pdf', 'tikz', 'contourdata'];

const args = new Set(process.argv.slice(2));
const apply = args.has('--apply');
const check = args.has('--check');
const force = args.has('--force');
const unknownArgs = [...args].filter(arg => !['--apply', '--check', '--force'].includes(arg));
if (unknownArgs.length || (apply && check)) {
  console.error('Usage: node scripts/sync-exercices.mjs [--check | --apply] [--force]');
  process.exit(2);
}

const digest = buffer => crypto.createHash('sha256').update(buffer).digest('hex');

async function files(directory, predicate = () => true) {
  const entries = await fs.readdir(directory, { withFileTypes: true });
  const result = [];
  for (const entry of entries) {
    const fullPath = path.join(directory, entry.name);
    if (entry.isDirectory()) {
      result.push(...await files(fullPath, predicate));
    } else if (entry.isFile() && predicate(entry.name)) {
      result.push(fullPath);
    }
  }
  return result.sort();
}

async function planDirectory(sourceDirectory, targetDirectory, predicate, kind) {
  try {
    await fs.access(sourceDirectory);
  } catch {
    return [];
  }

  const result = [];
  for (const sourcePath of await files(sourceDirectory, predicate)) {
    const relativePath = path.relative(sourceDirectory, sourcePath);
    const targetPath = path.join(targetDirectory, relativePath);
    const sourceContent = await fs.readFile(sourcePath);
    let action = 'add';
    try {
      const targetContent = await fs.readFile(targetPath);
      action = digest(sourceContent) === digest(targetContent) ? 'unchanged' : 'update';
    } catch (error) {
      if (error.code !== 'ENOENT') throw error;
    }
    result.push({ kind, action, sourcePath, targetPath, relativeTargetPath: path.relative(ROOT, targetPath) });
  }
  return result;
}

function modifiedPaths() {
  const status = spawnSync('git', ['status', '--porcelain=v1', '-z', '--untracked-files=all'], {
    cwd: ROOT,
    encoding: 'utf8'
  });
  if (status.status !== 0) throw new Error('Impossible de lire l’état Git de exobase.');
  return new Set(status.stdout.split('\0').filter(Boolean).map(record => record.slice(3)));
}

function summary(entries) {
  return entries.reduce((counts, entry) => {
    counts[entry.kind] ??= { add: 0, update: 0, unchanged: 0 };
    counts[entry.kind][entry.action]++;
    return counts;
  }, {});
}

async function main() {
  const sourceEntries = await planDirectory(SOURCE_SOURCES, TARGET_SOURCES, name => name.endsWith('.tex'), 'sources');
  const imageEntries = (await Promise.all(IMAGE_FORMATS.map(format =>
    planDirectory(path.join(SOURCE_IMAGES, format), path.join(TARGET_IMAGES, format), () => true, 'images')
  ))).flat();
  const entries = [...sourceEntries, ...imageEntries];
  const selected = entries.filter(entry => entry.action !== 'unchanged');

  console.log(`Exercices : ${SOURCE_ROOT}`);
  for (const [kind, counts] of Object.entries(summary(entries))) {
    console.log(`${kind === 'sources' ? 'Sources .tex' : 'Images et sources graphiques'} — ${counts.add} ajout(s), ${counts.update} mise(s) à jour, ${counts.unchanged} identique(s)`);
  }

  if (!selected.length) {
    console.log('\n✅ exobase est déjà synchronisé avec Exercices.');
    return;
  }

  console.log('\nFichiers à synchroniser :');
  for (const entry of selected) console.log(`  ${entry.action === 'add' ? '＋' : '↻'} ${entry.relativeTargetPath}`);

  if (!apply) {
    console.log('\nAperçu uniquement. Pour appliquer : node scripts/sync-exercices.mjs --apply');
    if (check) process.exitCode = 1;
    return;
  }

  if (!force) {
    const dirty = modifiedPaths();
    const conflicts = selected.filter(entry => entry.action === 'update' && dirty.has(entry.relativeTargetPath));
    if (conflicts.length) {
      throw new Error(`Synchronisation annulée : modifications locales à préserver dans ${conflicts.map(entry => entry.relativeTargetPath).join(', ')}. Committez-les ou relancez avec --force après vérification.`);
    }
  }

  for (const entry of selected) {
    await fs.mkdir(path.dirname(entry.targetPath), { recursive: true });
    await fs.copyFile(entry.sourcePath, entry.targetPath);
  }
  console.log(`\n✅ ${selected.length} fichier(s) synchronisé(s). Vérifiez puis committez dans exobase.`);
}

main().catch(error => {
  console.error(`\n❌ ${error.message}`);
  process.exitCode = 1;
});
