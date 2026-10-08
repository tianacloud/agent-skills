#!/usr/bin/env node
import { execFileSync } from 'node:child_process';
import { readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

export function publishSkills(directory, { run = execFileSync, environment = process.env, pause = ms => Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, ms) } = {}) {
  const descriptor = JSON.parse(readFileSync(path.join(directory, 'skills-release.json'), 'utf8'));
  if (descriptor.name !== '@tianacloud/agent-skills') throw new Error('Unexpected Skills package.');
  const tarball = path.join(directory, descriptor.filename);
  const integrity = 'sha512-' + createHash('sha512').update(readFileSync(tarball)).digest('base64');
  if (integrity !== descriptor.integrity) throw new Error('Local artifact integrity differs.');
  const env = environment.NPM_TOKEN ? { ...environment, NPM_CONFIG_USERCONFIG: fileURLToPath(new URL('./npm-token.npmrc', import.meta.url)) } : environment;
  const tag = descriptor.version.split('+')[0].includes('-') ? 'next' : 'latest';
  const read = fields => run('npm', ['view', ...fields, '--json', '--registry=https://registry.npmjs.org/'], { env, encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] });
  const remoteIntegrity = () => {
    try { return JSON.parse(read([`${descriptor.name}@${descriptor.version}`, 'dist.integrity'])); }
    catch (error) {
      let result;try { result = JSON.parse(error.stdout?.toString() ?? '{}'); } catch {}
      if (result?.error?.code === 'E404') return undefined;
      throw new Error('Cannot check npm release; inspect registry access and retry the same artifact.');
    }
  };
  const existing = remoteIntegrity();
  if (existing && existing !== integrity) throw new Error('Published version contains different artifacts; choose a new version.');
  if (!existing) {
    try { run('npm', ['publish', tarball, '--access=public', `--tag=${tag}`, '--registry=https://registry.npmjs.org/'], { env, stdio: 'inherit' }); }
    catch { if (remoteIntegrity() !== integrity) throw new Error('Publication failed; preserve and retry the same artifact.'); }
  }
  let verified = remoteIntegrity();
  for (let attempt = 0; verified === undefined && attempt < 60; attempt++) {
    pause(5000);
    verified = remoteIntegrity();
  }
  if (verified !== integrity) throw new Error('npm release integrity verification failed; retry the original artifact after registry processing.');
  const tags = JSON.parse(read([descriptor.name, 'dist-tags']));
  if (tags[tag] !== descriptor.version) throw new Error(`Published version exists but ${tag} points elsewhere; inspect the channel.`);
  return descriptor;
}
if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  try {
    if (process.argv.length !== 3) throw new Error('Usage: node scripts/publish-skills.mjs ARTIFACT_DIRECTORY');
    const result = publishSkills(path.resolve(process.argv[2]));
    console.log(`Published ${result.name}@${result.version}.`);
  } catch (error) { console.error(error.message);process.exitCode = 1; }
}
