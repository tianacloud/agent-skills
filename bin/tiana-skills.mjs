#!/usr/bin/env node
import { cp, mkdir, rm, realpath, readFile, mkdtemp, rename } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { createRequire } from 'node:module';
import { spawnSync } from 'node:child_process';

const root = fileURLToPath(new URL('../', import.meta.url));
const names = ['tiana', 'tiana-sqlite', 'tiana-git', 'tiana-web'];
const usage = 'tiana-skills install [--agent NAME | --dir PATH]';
try {
  const args = process.argv.slice(2);
  if (!args.length || args[0] === '--help' || args[0] === '-h') {
    console.log(usage);
  } else {
    if (args.shift() !== 'install') throw new Error(usage);
    let agent, directory;
    while (args.length) {
      const flag = args.shift();
      if (!['--agent', '--dir'].includes(flag) || !args[0] || args[0].startsWith('--')) throw new Error(usage);
      if (flag === '--agent' && agent === undefined) agent = args.shift();
      else if (flag === '--dir' && directory === undefined) directory = args.shift();
      else throw new Error(usage);
    }
    if (agent && directory) throw new Error('Choose --agent or --dir.');
    const source = path.join(root, 'skills');
    const pkg = JSON.parse(await readFile(path.join(root, 'package.json'), 'utf8'));
    if (directory) {
      const target = path.resolve(directory);
      await mkdir(target, { recursive: true });
      if (await realpath(target) === await realpath(source)) throw new Error('Choose an installation directory outside the downloaded package.');
      const completed = [];
      for (const name of names) {
        let staging;
        try {
          staging = await mkdtemp(path.join(target, '.tiana-skills-'));
          await cp(path.join(source, name), path.join(staging, name), { recursive: true });
          const destination = path.join(target, name);
          await rm(destination, { recursive: true, force: true });
          await rename(path.join(staging, name), destination);
          completed.push(name);
        } catch (error) {
          throw new Error(`${error.message}\nCompleted: ${completed.join(', ') || 'none'}\nNot installed: ${names.slice(completed.length).join(', ')}`);
        } finally {
          if (staging) await rm(staging, { recursive: true, force: true });
        }
      }
      console.log(`Installed Tiana Skills ${pkg.version}: ${names.join(', ')}\nDirectory: ${target}`);
    } else {
      const require = createRequire(import.meta.url);
      const tool = path.join(path.dirname(require.resolve('skills/package.json')), 'bin/cli.mjs');
      const parameters = [tool, 'add', source, '--global', '--copy', '--skill', ...names];
      if (agent) parameters.push('--agent', agent, '--yes');
      const result = spawnSync(process.execPath, parameters, { stdio: 'inherit', env: { ...process.env, DISABLE_TELEMETRY: '1' } });
      if (result.error) throw result.error;
      if (result.status !== 0) process.exitCode = result.status ?? 1;
      else console.log(`Installed Tiana Skills ${pkg.version}: ${names.join(', ')}`);
    }
  }
} catch (error) { console.error(`Tiana Skills installation failed: ${error.message}`); process.exitCode = 1; }
