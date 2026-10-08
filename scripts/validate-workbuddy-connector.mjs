#!/usr/bin/env node
import assert from 'node:assert/strict';
import { promises as fs } from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { strFromU8, unzipSync } from 'fflate';

const root = process.cwd();
const temporary = await fs.mkdtemp(path.join(os.tmpdir(), 'tiana-connector-validation-'));
const pkg = JSON.parse(await fs.readFile(path.join(root, 'package.json'), 'utf8'));
const localized = JSON.parse(await fs.readFile(path.join(root, 'packaging/workbuddy.json'), 'utf8'));
try {
  const build = spawnSync(process.execPath, ['scripts/build-workbuddy-connector.mjs', '--output', temporary], { cwd: root, stdio: 'inherit' });
  assert.equal(build.status, 0, 'Connector build failed');
  const name = `tiana-cloud-${pkg.version}.zip`;
  const archive = await fs.readFile(path.join(temporary, name));
  const zip = unzipSync(archive);
  const meta = JSON.parse(strFromU8(zip['connector-meta.json']));
  const cli = JSON.parse(strFromU8(zip['cli.json']));
  assert.equal(meta.source, 'tiana-cloud');
  assert.equal(meta.type, 'cli');
  assert.equal(meta.version, pkg.version);
  assert.equal(meta.minWorkbuddyVersion, '4.24.0');
  for (const field of ['name', 'name_zh', 'name_en', 'description', 'description_zh', 'description_en']) assert.ok(meta[field]);
  for (const field of ['examples_zh', 'examples_en']) assert.ok(meta[field].length >= 2);
  assert.deepEqual(cli.runtime, { type: 'node', version: '22' });
  assert.equal(cli.authWaitForExit, true);
  assert.equal(cli.authUrlDomain, 'console.tianacloud.com');
  for (const platform of ['darwin', 'linux', 'win32']) {
    const npm = platform === 'win32' ? 'npm.cmd' : 'npm';
    const tiana = platform === 'win32' ? 'tiana.cmd' : 'tiana';
    assert.equal(cli.init[platform], `${npm} install -g @tianacloud/cli@latest --registry=https://registry.npmjs.org/`);
    assert.equal(cli.auth[platform], `${tiana} login --no-open`);
    assert.equal(cli.status[platform], `${tiana} status`);
    assert.equal(cli.unAuth[platform], `${tiana} logout`);
  }
  assert.deepEqual(cli.env, {TIANA_API_ORIGIN: 'https://console.tianacloud.com'});
  const connected = new RegExp(cli.statusMatch);
  assert.equal(connected.test('Email: user@example.test\nQuota period: week (start to end)\nRESOURCE USED LIMIT'), true);
  assert.equal(connected.test('Not logged in'), false);
  assert.equal(connected.test('Not Logged in'), false);
  assert.deepEqual(Buffer.from(zip['icon.png']), await fs.readFile(path.join(root, 'packaging/workbuddy/tiana-cloud/icon.png')));
  const expected = ['connector-meta.json', 'cli.json', 'icon.png'];
  async function compareCanonical(directory, prefix) {
    for (const entry of await fs.readdir(directory, { withFileTypes: true })) {
      const name = `${prefix}/${entry.name}`;
      if (entry.isDirectory()) await compareCanonical(path.join(directory, entry.name), name);
      if (entry.isFile()) {
        expected.push(name);
        const canonical = await fs.readFile(path.join(directory, entry.name));
        if (entry.name === 'SKILL.md') {
          const actual = strFromU8(zip[name]);
          const original = canonical.toString('utf8');
          const actualEnd = actual.indexOf('\n---\n', 4);
          const originalEnd = original.indexOf('\n---\n', 4);
          assert.equal(actual.slice(actualEnd), original.slice(originalEnd), `${name}: canonical body changed`);
          const skill = prefix.split('/')[1];
          const frontmatter = actual.slice(0, actualEnd);
          for (const [field, value] of Object.entries({ ...localized.skills[skill], version: pkg.version, author: localized.author })) {
            assert.ok(frontmatter.split('\n').includes(`${field}: ${JSON.stringify(value)}`), `${name}: missing localized ${field}`);
          }
        } else {
          assert.deepEqual(Buffer.from(zip[name]), canonical, `${name} differs from canonical source`);
        }
      }
    }
  }
  for (const skill of ['tiana', 'tiana-sqlite', 'tiana-git', 'tiana-web']) await compareCanonical(path.join(root, 'skills', skill), `skills/${skill}`);
  assert.deepEqual(Object.keys(zip).sort(), expected.sort(), 'Unexpected or missing Connector files');
  const sha = createHash('sha256').update(archive).digest('hex');
  assert.equal(await fs.readFile(path.join(temporary, `${name}.sha256`), 'utf8'), `${sha}  ${name}\n`);
  console.log('Connector configuration, canonical skills, ZIP layout and checksum are valid. This is not a WorkBuddy runtime test.');
} finally {
  await fs.rm(temporary, { recursive: true, force: true });
}
