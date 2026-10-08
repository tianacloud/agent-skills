import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, writeFileSync, rmSync } from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { createHash } from 'node:crypto';
import { publishSkills } from './publish-skills.mjs';

function fixture(t) {
  const directory = mkdtempSync(path.join(os.tmpdir(), 'tiana-skills-release-'));
  t.after(() => rmSync(directory, { recursive: true, force: true }));
  const bytes = Buffer.from('one immutable prepared artifact');
  const descriptor = { name: '@tianacloud/agent-skills', version: '0.3.0', filename: 'skills.tgz', integrity: 'sha512-' + createHash('sha512').update(bytes).digest('base64') };
  writeFileSync(path.join(directory, descriptor.filename), bytes);
  writeFileSync(path.join(directory, 'skills-release.json'), JSON.stringify(descriptor));
  const calls = [];let remote;let tags = {};let uncertain = false;
  const run = (_command, args) => {
    calls.push(args);
    if (args[0] === 'publish') { remote = descriptor.integrity; tags = { [args.find(item => item.startsWith('--tag=')).slice(6)]: descriptor.version }; if (uncertain) throw new Error('lost response'); return ''; }
    if (args.includes('dist-tags')) return JSON.stringify(tags);
    if (remote) return JSON.stringify(remote);
    const error = new Error('missing');error.stdout = JSON.stringify({ error: { code: 'E404' } });throw error;
  };
  return { directory, descriptor, calls, run, setRemote(value) { remote = value; tags = { latest: descriptor.version }; }, setUncertain() { uncertain = true; } };
}
test('publishes one prepared tarball, verifies exact integrity/channel and resumes without rewriting', t => {
  const f = fixture(t);publishSkills(f.directory, { run: f.run });publishSkills(f.directory, { run: f.run });
  assert.equal(f.calls.filter(call => call[0] === 'publish').length, 1);
  assert.ok(f.calls.some(call => call.includes(path.join(f.directory, 'skills.tgz'))));
  assert.ok(f.calls.find(call => call[0] === 'publish').includes('--tag=latest'));
});
test('lost publication response is resolved by reading back the same artifact', t => {
  const f = fixture(t);f.setUncertain();assert.doesNotThrow(() => publishSkills(f.directory, { run: f.run }));
});
test('remote conflict and tampered local artifact stop before publication', t => {
  const f = fixture(t);f.setRemote('different');assert.throws(() => publishSkills(f.directory, { run: f.run }), /different artifacts/);
  assert.equal(f.calls.some(call => call[0] === 'publish'), false);
  writeFileSync(path.join(f.directory, 'skills.tgz'), 'changed');assert.throws(() => publishSkills(f.directory, { run: f.run }), /Local artifact/);
});
test('prerelease chooses next channel', t => {
  const f = fixture(t);f.descriptor.version = '0.3.0-beta.1';writeFileSync(path.join(f.directory, 'skills-release.json'), JSON.stringify(f.descriptor));
  publishSkills(f.directory, { run: f.run });assert.ok(f.calls.find(call => call[0] === 'publish').includes('--tag=next'));
});

test('accepted publication waits for npm to expose the exact artifact', t => {
 const f=fixture(t); let remaining=3; let published=false; const waits=[];
 const run=(command,args,options)=>{
  if(args[0]==='publish'){published=true;return f.run(command,args,options);}
  if(published && args.includes('dist.integrity') && remaining-->0){const error=new Error('processing');error.stdout=JSON.stringify({error:{code:'E404'}});throw error;}
  return f.run(command,args,options);
 };
 publishSkills(f.directory,{run,pause:ms=>waits.push(ms)});
 assert.equal(waits.length,3);
 assert.equal(f.calls.filter(call=>call[0]==='publish').length,1);
});
