#!/usr/bin/env node
import { promises as fs } from 'node:fs';
import path from 'node:path';
import { createHash } from 'node:crypto';
import { zipSync } from 'fflate';
import { addWorkBuddyFrontmatter } from './workbuddy-metadata.mjs';

const root = process.cwd();
const args = process.argv.slice(2);
if (args.length && (args.length !== 2 || args[0] !== '--output')) {
  throw new Error('Usage: node scripts/build-workbuddy-connector.mjs [--output DIRECTORY]');
}
const output = path.resolve(args[1] ?? path.join(root, 'dist/workbuddy'));
const pkg = JSON.parse(await fs.readFile(path.join(root, 'package.json'), 'utf8'));
const template = path.join(root, 'packaging/workbuddy/tiana-cloud');
const metadata = JSON.parse(await fs.readFile(path.join(template, 'connector-meta.json'), 'utf8'));
const localized = JSON.parse(await fs.readFile(path.join(root, 'packaging/workbuddy.json'), 'utf8'));
if (metadata.version !== pkg.version) throw new Error('Connector and package versions differ');
const entries = {};
async function addDirectory(directory, prefix) {
  for (const entry of await fs.readdir(directory, { withFileTypes: true })) {
    const name = `${prefix}/${entry.name}`;
    if (entry.isDirectory()) await addDirectory(path.join(directory, entry.name), name);
    if (entry.isFile()) entries[name] = new Uint8Array(await fs.readFile(path.join(directory, entry.name)));
  }
}
for (const name of ['connector-meta.json', 'cli.json', 'icon.png']) {
  entries[name] = new Uint8Array(await fs.readFile(path.join(template, name)));
}
for (const name of ['tiana', 'tiana-sqlite', 'tiana-git', 'tiana-web']) {
  await addDirectory(path.join(root, 'skills', name), `skills/${name}`);
  const entry = `skills/${name}/SKILL.md`;
  entries[entry] = Buffer.from(addWorkBuddyFrontmatter(Buffer.from(entries[entry]).toString('utf8'), localized.skills[name], pkg.version, localized.author));
}
await fs.mkdir(output, { recursive: true });
const name = `tiana-cloud-${pkg.version}.zip`;
const archive = zipSync(entries, { level: 9 });
await fs.writeFile(path.join(output, name), archive);
const sha = createHash('sha256').update(archive).digest('hex');
await fs.writeFile(path.join(output, `${name}.sha256`), `${sha}  ${name}\n`);
console.log(path.join(output, name));
