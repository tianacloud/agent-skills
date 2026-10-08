#!/usr/bin/env node
import { execFileSync } from 'node:child_process';
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
const root = fileURLToPath(new URL('../', import.meta.url));
const directory = path.resolve(process.argv[2] ?? 'dist/npm-release');
mkdirSync(directory, { recursive: true });
const [packed] = JSON.parse(execFileSync('npm', ['pack', '--ignore-scripts', '--json', '--pack-destination', directory], { cwd: root, encoding: 'utf8' }));
const bytes = readFileSync(path.join(directory, packed.filename));
const descriptor = { name: packed.name, version: packed.version, filename: packed.filename, integrity: 'sha512-' + createHash('sha512').update(bytes).digest('base64'), size: bytes.length };
writeFileSync(path.join(directory, 'skills-release.json'), JSON.stringify(descriptor, null, 2) + '\n');
console.log(JSON.stringify(descriptor));
