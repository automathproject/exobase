#!/usr/bin/env node

/**
 * Mirrors the editorial AMSCC corpus from Exercices into exobase.
 *
 * The comparison is three-way. The reference state is the Exercices commit
 * recorded in content/provenance/amscc.json, which is what separates an
 * upstream correction (copy it) from editorial work done in exobase (keep it)
 * from a genuine divergence (stop and report it). Without that reference the
 * script never overwrites: it preserves the exobase side and records the
 * commit so the following runs can decide.
 *
 * Default mode is a dry run. The synchronisation is additive: files owned by
 * exobase but absent from Exercices are deliberately never deleted, only
 * reported.
 */
import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const SOURCE_ROOT = process.env.EXERCISES_ROOT || path.resolve(ROOT, '../../COET/Exercices');
const PROVENANCE = path.join(ROOT, 'content/provenance/amscc.json');
const IMAGE_FORMATS = ['svg', 'png', 'jpg', 'jpeg', 'pdf', 'tikz', 'contourdata'];

const MAPPINGS = [
  { kind: 'sources', from: 'src', to: 'content/exercises/amscc', accept: name => name.endsWith('.tex') },
  ...IMAGE_FORMATS.map(format => ({
    kind: 'images',
    from: `img/${format}`,
    to: `content/images/amscc/${format}`,
    accept: () => true
  })),
  { kind: 'code', from: 'code/python', to: 'content/code/amscc/python', accept: name => name.endsWith('.py') }
];

const LABELS = { sources: 'Sources .tex', images: 'Images et sources graphiques', code: 'Extraits Python' };
const ACTIONS = {
  add: { mark: '＋', title: 'Ajouts' },
  update: { mark: '↻', title: 'Mises à jour depuis Exercices' },
  local: { mark: '=', title: 'Travail exobase préservé' },
  conflict: { mark: '✗', title: 'Conflits — modifiés des deux côtés' }
};

const args = new Set(process.argv.slice(2));
const apply = args.has('--apply');
const check = args.has('--check');
const force = args.has('--force');
const unknownArgs = [...args].filter(arg => !['--apply', '--check', '--force'].includes(arg));
if (unknownArgs.length || (apply && check)) {
  console.error('Usage: node scripts/sync-exercices.mjs [--check | --apply] [--force]');
  process.exit(2);
}

class SyncError extends Error {}

function git(gitArgs, options = {}) {
  return spawnSync('git', ['-C', SOURCE_ROOT, ...gitArgs], { maxBuffer: 512 * 1024 * 1024, ...options });
}

function gitText(gitArgs, message) {
  const result = git(gitArgs, { encoding: 'utf8' });
  if (result.status !== 0) throw new SyncError(message);
  return result.stdout;
}

const upstreamHead = () =>
  gitText(['rev-parse', 'HEAD'], `${SOURCE_ROOT} n'est pas un dépôt Git exploitable.`).trim();

const upstreamIsClean = () =>
  gitText(['status', '--porcelain'], "Impossible de lire l'état Git d'Exercices.").trim() === '';

const commitExists = commit => git(['cat-file', '-e', `${commit}^{commit}`]).status === 0;

function baseContent(commit, repoPath) {
  const result = git(['show', `${commit}:${repoPath}`]);
  return result.status === 0 ? result.stdout : null;
}

function tracked(repoPath) {
  return MAPPINGS.some(mapping =>
    repoPath.startsWith(`${mapping.from}/`) && mapping.accept(path.posix.basename(repoPath)));
}

/** Files removed or renamed in Exercices since the reference commit. */
function upstreamRemovals(base, head) {
  const result = git(['diff', '--name-status', '-M', base, head, '--', ...MAPPINGS.map(m => m.from)], {
    encoding: 'utf8'
  });
  if (result.status !== 0) return [];
  return result.stdout
    .split('\n')
    .filter(Boolean)
    .map(line => line.split('\t'))
    .filter(([status, from]) => (status.startsWith('D') || status.startsWith('R')) && tracked(from))
    .map(([status, from, to]) => ({ status: status[0], from, to }));
}

async function walk(directory, accept) {
  let entries;
  try {
    entries = await fs.readdir(directory, { withFileTypes: true });
  } catch (error) {
    if (error.code === 'ENOENT') return [];
    throw error;
  }
  const result = [];
  for (const entry of entries) {
    const fullPath = path.join(directory, entry.name);
    if (entry.isDirectory()) result.push(...await walk(fullPath, accept));
    else if (entry.isFile() && accept(entry.name)) result.push(fullPath);
  }
  return result.sort();
}

async function readOptional(file) {
  try {
    return await fs.readFile(file);
  } catch (error) {
    if (error.code === 'ENOENT') return null;
    throw error;
  }
}

/** Three-way decision for one file: upstream now, exobase now, reference state. */
function decide(repoPath, base, upstream, downstream) {
  if (downstream === null) return { action: 'add' };
  if (upstream.equals(downstream)) return { action: 'unchanged' };
  if (!base) return { action: 'local', reason: 'référence inconnue' };
  const reference = baseContent(base, repoPath);
  if (reference === null) return { action: 'conflict', reason: 'créé des deux côtés' };
  if (reference.equals(downstream)) return { action: 'update' };
  if (reference.equals(upstream)) return { action: 'local', reason: 'travail exobase' };
  return { action: 'conflict', reason: 'modifié des deux côtés' };
}

async function plan(base) {
  const entries = [];
  for (const mapping of MAPPINGS) {
    const sourceDirectory = path.join(SOURCE_ROOT, mapping.from);
    for (const sourcePath of await walk(sourceDirectory, mapping.accept)) {
      const relative = path.relative(sourceDirectory, sourcePath);
      const targetPath = path.join(ROOT, mapping.to, relative);
      const repoPath = path.posix.join(mapping.from, relative.split(path.sep).join('/'));
      const upstream = await fs.readFile(sourcePath);
      const downstream = await readOptional(targetPath);
      entries.push({
        kind: mapping.kind,
        sourcePath,
        targetPath,
        repoPath,
        relativeTargetPath: path.relative(ROOT, targetPath),
        ...decide(repoPath, base, upstream, downstream)
      });
    }
  }
  return entries;
}

function summarize(entries) {
  return entries.reduce((counts, entry) => {
    counts[entry.kind] ??= { add: 0, update: 0, local: 0, conflict: 0, unchanged: 0 };
    counts[entry.kind][entry.action]++;
    return counts;
  }, {});
}

function report(entries, action) {
  const selected = entries.filter(entry => entry.action === action);
  if (!selected.length) return;
  const { mark, title } = ACTIONS[action];
  console.log(`\n${title} :`);
  for (const entry of selected) {
    const reason = entry.reason ? ` (${entry.reason})` : '';
    console.log(`  ${mark} ${entry.relativeTargetPath}${reason}`);
  }
}

async function recordSync(commit, entries, previous) {
  const counts = entries.reduce((totals, entry) => {
    totals[entry.kind] = (totals[entry.kind] ?? 0) + 1;
    return totals;
  }, {});
  const provenance = JSON.parse(await fs.readFile(PROVENANCE, 'utf8'));
  const unchangedBookmark = previous === commit && provenance.exercices === counts.sources;
  if (unchangedBookmark) return false;
  provenance.exercices = counts.sources ?? 0;
  provenance.sync = {
    commit,
    date: new Date().toISOString(),
    fichiers: { sources: counts.sources ?? 0, images: counts.images ?? 0, code: counts.code ?? 0 }
  };
  await fs.writeFile(PROVENANCE, `${JSON.stringify(provenance, null, 2)}\n`);
  return true;
}

async function main() {
  const head = upstreamHead();
  const provenance = JSON.parse(await fs.readFile(PROVENANCE, 'utf8'));
  let base = provenance.sync?.commit ?? null;

  console.log(`Exercices : ${SOURCE_ROOT}`);
  console.log(`Commit amont : ${head.slice(0, 7)}`);
  if (base && !commitExists(base)) {
    console.log(`⚠ Référence ${base.slice(0, 7)} introuvable dans Exercices (historique réécrit ?).`);
    base = null;
  }
  console.log(base
    ? `Référence : ${base.slice(0, 7)}`
    : 'Référence : aucune — les fichiers divergents seront préservés, jamais écrasés.');

  const entries = await plan(base);
  console.log();
  for (const [kind, counts] of Object.entries(summarize(entries))) {
    console.log(`${LABELS[kind]} — ${counts.add} ajout(s), ${counts.update} mise(s) à jour, ` +
      `${counts.local} local(aux), ${counts.conflict} conflit(s), ${counts.unchanged} identique(s)`);
  }

  if (base) {
    const removals = upstreamRemovals(base, head);
    if (removals.length) {
      console.log('\nSupprimés ou renommés dans Exercices (jamais répercuté automatiquement) :');
      for (const removal of removals) {
        console.log(removal.status === 'R'
          ? `  → ${removal.from} → ${removal.to}`
          : `  − ${removal.from}`);
      }
    }
  }

  // --force gives Exercices authority over everything the exobase side changed,
  // conflicts and preserved editorial work alike, so the plan must say so.
  const overridden = force
    ? entries.filter(entry => entry.action === 'local' || entry.action === 'conflict')
    : [];
  if (overridden.length) {
    console.log('\nÉcrasés par --force — Exercices fait autorité :');
    for (const entry of overridden) {
      console.log(`  ↻ ${entry.relativeTargetPath}${entry.reason ? ` (${entry.reason})` : ''}`);
    }
    for (const action of ['add', 'update']) report(entries, action);
  } else {
    for (const action of ['conflict', 'add', 'update', 'local']) report(entries, action);
  }

  const conflicts = force ? [] : entries.filter(entry => entry.action === 'conflict');
  const copies = [
    ...entries.filter(entry => entry.action === 'add' || entry.action === 'update'),
    ...overridden
  ];

  if (!apply) {
    if (conflicts.length && !force) {
      console.log('\nRésolvez les conflits dans exobase, ou tranchez en faveur d’Exercices avec --force.');
    }
    if (copies.length || conflicts.length) {
      console.log('\nAperçu uniquement. Pour appliquer : node scripts/sync-exercices.mjs --apply');
    } else if (base === head) {
      console.log('\n✅ exobase est à jour vis-à-vis d’Exercices.');
    } else {
      console.log(`\n✅ Aucun fichier à copier. Lancez --apply pour enregistrer la référence ${head.slice(0, 7)}.`);
    }
    if (check && (copies.length || conflicts.length)) process.exitCode = 1;
    return;
  }

  if (!upstreamIsClean() && !force) {
    throw new SyncError(
      'Exercices a des modifications non committées : la référence enregistrée serait fausse. ' +
      'Committez-les dans Exercices, ou relancez avec --force.');
  }

  for (const entry of copies) {
    await fs.mkdir(path.dirname(entry.targetPath), { recursive: true });
    await fs.copyFile(entry.sourcePath, entry.targetPath);
  }
  console.log(`\n${copies.length} fichier(s) copié(s) depuis Exercices.`);

  if (conflicts.length) {
    console.log(`⚠ ${conflicts.length} conflit(s) non résolu(s) : la référence reste à ` +
      `${base ? base.slice(0, 7) : 'aucune'}. Résolvez-les puis relancez.`);
    process.exitCode = 1;
    return;
  }

  const recorded = await recordSync(head, entries, base);
  if (recorded) console.log(`Référence enregistrée : ${head.slice(0, 7)} dans content/provenance/amscc.json`);
  console.log('\n✅ Relisez le diff puis committez dans exobase. OpenYourMath importera ce commit.');
}

main().catch(error => {
  if (error instanceof SyncError) {
    console.error(`\n❌ ${error.message}`);
    process.exitCode = 1;
  } else {
    console.error(`\n❌ ${error.stack}`);
    process.exitCode = 3;
  }
});
