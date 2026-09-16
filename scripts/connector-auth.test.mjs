import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { once } from 'node:events';
import { promises as fs } from 'node:fs';
import { createHash } from 'node:crypto';
import http from 'node:http';
import os from 'node:os';
import path from 'node:path';
import { setTimeout as delay } from 'node:timers/promises';
import test from 'node:test';

const binary = process.env.TIANA_TEST_CLI_BINARY;

test('real CLI auth processes with delayed fixture approval (not WorkBuddy)', { skip: !binary, timeout: 35000 }, async t => {
  const cli = JSON.parse(await fs.readFile('packaging/workbuddy/tiana-cloud/cli.json', 'utf8'));
  const directory = await fs.mkdtemp(path.join(os.tmpdir(), 'tiana-connector-auth-'));
  t.after(() => fs.rm(directory, { recursive: true, force: true }));
  let approved = false, calls = 0, exchanges = 0, logouts = 0;
  const server = http.createServer(async (request, response) => {
    calls++;
    for await (const chunk of request) { /* Consume the isolated fixture request. */ }
    response.setHeader('Content-Type', 'application/json');
    switch (request.url) {
      case '/api/v1/auth/transactions':
        response.end(JSON.stringify({ transaction_id: 'at-fixture', client_secret: 'fixture-secret', user_code: 'ABCD-EFGH',
          verification_uri_complete: 'https://console.service.internal.tiana.com/api/v1/a/ABCD-EFGH', expires_in: 240, poll_interval: 1 }));
        break;
      case '/api/v1/auth/transactions/at-fixture/poll':
        response.end(JSON.stringify(approved ? { status: 'approved', authorization_code: 'fixture-code', expires_in: 30 } : { status: 'pending' }));
        break;
      case '/api/v1/auth/token':
        exchanges++;
        response.end(JSON.stringify({ access_token: 'fixture-access', refresh_token: 'fixture-refresh', expires_in: 3600,
          refresh_expires_at: '2100-01-01T00:00:00Z', user: { user_id: 'prn_fixture', tenant_id: 'ten_fixture' } }));
        break;
      case '/api/v1/auth/transactions/logout':
        logouts++;
        response.writeHead(204).end();
        break;
      default:
        response.writeHead(404).end('{}');
    }
  });
  server.listen(0, '127.0.0.1');
  await once(server, 'listening');
  t.after(() => new Promise(resolve => server.close(resolve)));
  const env = { ...process.env, TIANA_MGR_ORIGIN: `http://127.0.0.1:${server.address().port}`,
    TIANA_CREDENTIALS_FILE: path.join(directory, 'credentials.json'),
    TIANA_INSTANCE_TOKENS_FILE: path.join(directory, 'instance-tokens.json') };
  delete env.TIANA_AUTH_ORIGIN;
  function start(command) {
    // The configured commands have only fixed words; no shell or browser is used.
    const [name, ...args] = command.split(' ');
    assert.equal(name, 'tiana');
    const child = spawn(binary, args, { env, stdio: ['ignore', 'pipe', 'pipe'] });
    t.after(() => { if (child.exitCode === null) child.kill('SIGKILL'); });
    const output = { stdout: '', stderr: '' };
    child.stdout.on('data', data => { output.stdout += data; });
    child.stderr.on('data', data => { output.stderr += data; });
    const finished = once(child, 'close').then(([code, signal]) => ({ ...output, code, signal }));
    return { child, output, finished };
  }
  async function status() {
    const result = await start(cli.status[process.platform]).finished;
    return { ...result, connected: result.code === 0 && new RegExp(cli.statusMatch).test(result.stdout.trimEnd()) };
  }
  async function snapshot() {
    const files = {};
    async function walk(dir) {
      for (const item of await fs.readdir(dir, { withFileTypes: true })) {
        const filename = path.join(dir, item.name);
        if (item.isDirectory()) await walk(filename);
        else {
          const stat = await fs.stat(filename);
          files[path.relative(directory, filename)] = { modified: stat.mtimeMs,
            hash: createHash('sha256').update(await fs.readFile(filename)).digest('hex') };
        }
      }
    }
    await walk(directory);
    return files;
  }
  const before = await snapshot();
  assert.equal((await status()).connected, false);
  assert.equal(calls, 0, 'status called the network');
  assert.deepEqual(await snapshot(), before, 'unauthenticated status changed storage');

  const started = performance.now();
  const auth = start(cli.auth[process.platform]);
  const urlReady = (async () => {
    while (performance.now() - started < 10000) {
      const link = (auth.output.stdout + auth.output.stderr).match(/(?:^|\s)(https:\/\/[^\s]+)(?=\s)/)?.[1];
      if (link) return link;
      assert.equal(auth.child.exitCode, null, 'auth ended before outputting a URL');
      assert.equal(auth.child.signalCode, null, 'auth was killed before outputting a URL');
      await delay(20);
    }
    throw new Error('No URL within 10 seconds');
  })();
  const link = await urlReady;
  assert.equal(new URL(link).hostname, cli.authUrlDomain);
  assert.ok(performance.now() - started < 10000);
  assert.equal(cli.authWaitForExit, true);
  await delay(11000);
  assert.equal(auth.child.exitCode, null, 'auth did not survive delayed approval beyond 10 seconds');
  assert.equal((await status()).connected, false);
  approved = true;
  const authenticated = await auth.finished;
  assert.equal(authenticated.code, 0);
  assert.equal(exchanges, 1);
  for (const secret of ['fixture-secret', 'fixture-code', 'fixture-access', 'fixture-refresh']) {
    assert.equal((authenticated.stdout + authenticated.stderr).includes(secret), false);
  }
  const saved = await snapshot();
  const callsBefore = calls;
  for (let i = 0; i < 3; i++) assert.equal((await status()).connected, true);
  assert.equal(calls, callsBefore, 'restart status called the network');
  assert.deepEqual(await snapshot(), saved, 'restart status changed persisted credentials');
  assert.equal((await start(cli.unAuth[process.platform]).finished).code, 0);
  assert.equal(logouts, 1);
  assert.equal((await status()).connected, false);
  assert.equal((await start(cli.unAuth[process.platform]).finished).code, 0, 'repeated logout failed');

  approved = false;
  const interrupted = start(cli.auth[process.platform]);
  await once(interrupted.child.stdout, 'data');
  interrupted.child.kill('SIGINT');
  assert.equal((await interrupted.finished).code, 5);
  assert.equal((await status()).connected, false);
});
