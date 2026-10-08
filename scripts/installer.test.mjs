import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, mkdir, readFile, rm, writeFile, readdir, lstat, cp } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';

const root = fileURLToPath(new URL('../', import.meta.url));
const names = ['tiana', 'tiana-git', 'tiana-sqlite', 'tiana-web'];
const run = (bin, args, cwd, env = {}) => spawnSync(process.execPath, [bin, ...args], { cwd, env: { ...process.env, DISABLE_TELEMETRY: '1', ...env }, encoding: 'utf8' });

async function assertInstalled(directory) {
  for (const name of names) {
    assert.equal((await lstat(path.join(directory, name))).isSymbolicLink(), false);
    assert.equal(await readFile(path.join(directory, name, 'SKILL.md'), 'utf8'), await readFile(path.join(root, 'skills', name, 'SKILL.md'), 'utf8'));
  }
}

test('explicit directory installs from another cwd, updates four skills and preserves unrelated skills', async () => {
  const temporary = await mkdtemp(path.join(os.tmpdir(), 'tiana skills installer '));
  try {
    const target = path.join(temporary, 'client skills');
    let result = run(path.join(root, 'bin/tiana-skills.mjs'), ['install', '--dir', target], temporary);
    assert.equal(result.status, 0, result.stderr);
    await assertInstalled(target);
    await mkdir(path.join(target, 'other-skill'));
    await writeFile(path.join(target, 'other-skill/SKILL.md'), 'unrelated');
    await writeFile(path.join(target, 'tiana/stale.md'), 'removed in new version');
    result = run(path.join(root, 'bin/tiana-skills.mjs'), ['install', '--dir', target], temporary);
    assert.equal(result.status, 0, result.stderr);
    assert.equal(await readFile(path.join(target, 'other-skill/SKILL.md'), 'utf8'), 'unrelated');
    assert.equal((await readdir(path.join(target, 'tiana'))).includes('stale.md'), false);
    await assertInstalled(target);
  } finally { await rm(temporary, { recursive: true, force: true }); }
});

test('packed npm installer installs Codex copies that survive deletion of the downloaded package', async () => {
  const temporary = await mkdtemp(path.join(os.tmpdir(), 'tiana packed skills '));
  try {
    const packed = spawnSync('npm', ['pack', '--ignore-scripts', '--json', '--pack-destination', temporary], { cwd: root, encoding: 'utf8' });
    assert.equal(packed.status, 0, packed.stderr);
    const tarball = path.join(temporary, JSON.parse(packed.stdout)[0].filename);
    const unpacked = path.join(temporary, 'unpacked');
    await mkdir(unpacked);
    const tar = spawnSync('tar', ['-xzf', tarball, '-C', unpacked], { encoding: 'utf8' });
    assert.equal(tar.status, 0, tar.stderr);
    await mkdir(path.join(unpacked, 'package/node_modules'));
    const link = await import('node:fs/promises');
    await link.symlink(path.join(root, 'node_modules/skills'), path.join(unpacked, 'package/node_modules/skills'), 'dir');
    const codexDirectory = path.join(temporary, 'codex home');
    const homeDirectory = path.join(temporary, 'user home');
    await mkdir(homeDirectory);
    const result = run(path.join(unpacked, 'package/bin/tiana-skills.mjs'), ['install', '--agent', 'codex'], temporary, { CODEX_HOME: codexDirectory, HOME: homeDirectory, USERPROFILE: homeDirectory });
    assert.equal(result.status, 0, result.stderr + result.stdout);
    await rm(unpacked, { recursive: true, force: true });
    await assertInstalled(path.join(homeDirectory, '.agents/skills'));
    const content = await readFile(path.join(homeDirectory, '.agents/skills/tiana-web/references/template-init.md'), 'utf8');
    assert.ok(content.length > 0);
  } finally { await rm(temporary, { recursive: true, force: true }); }
});

test('write failure is reported and mutually exclusive install targets fail', async () => {
  const temporary = await mkdtemp(path.join(os.tmpdir(), 'tiana-install-error-'));
  try {
    const file = path.join(temporary, 'file');
    await writeFile(file, 'preserve');
    const result = run(path.join(root, 'bin/tiana-skills.mjs'), ['install', '--dir', file], temporary);
    assert.notEqual(result.status, 0);
    assert.equal(await readFile(file, 'utf8'), 'preserve');
    assert.notEqual(run(path.join(root, 'bin/tiana-skills.mjs'), ['install', '--dir', temporary, '--agent', 'codex'], temporary).status, 0);
  } finally { await rm(temporary, { recursive: true, force: true }); }
});

test('failed source preparation retains the installed skill and reports partial completion', async () => {
  const temporary = await mkdtemp(path.join(os.tmpdir(), 'tiana-partial-install-'));
  try {
    const downloaded=path.join(temporary,'downloaded');
    await mkdir(path.join(downloaded,'bin'),{recursive:true});
    await cp(path.join(root,'bin/tiana-skills.mjs'),path.join(downloaded,'bin/tiana-skills.mjs'));
    await writeFile(path.join(downloaded,'package.json'),JSON.stringify({version:'fixture'}));
    await mkdir(path.join(downloaded,'skills'),{recursive:true});
    await cp(path.join(root,'skills/tiana'),path.join(downloaded,'skills/tiana'),{recursive:true});
    const target=path.join(temporary,'installed');
    await mkdir(path.join(target,'tiana-sqlite'),{recursive:true});
    await writeFile(path.join(target,'tiana-sqlite/SKILL.md'),'previous installed skill');
    const result=run(path.join(downloaded,'bin/tiana-skills.mjs'),['install','--dir',target],temporary);
    assert.notEqual(result.status,0);
    assert.match(result.stderr,/Completed: tiana/);
    assert.match(result.stderr,/Not installed: tiana-sqlite, tiana-git, tiana-web/);
    assert.equal(await readFile(path.join(target,'tiana-sqlite/SKILL.md'),'utf8'),'previous installed skill');
    assert.ok((await readdir(target)).every(name=>!name.startsWith('.tiana-skills-')));
  } finally {await rm(temporary,{recursive:true,force:true});}
});
