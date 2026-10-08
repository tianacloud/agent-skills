import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { once } from 'node:events';
import { promises as fs } from 'node:fs';
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
  let approved = false, calls = 0, exchanges = 0, logouts = 0, quotaAvailable = true, whoamiCalls = 0;
  const server = http.createServer(async (request, response) => {
    calls++;
    for await (const chunk of request) { /* Consume the isolated fixture request. */ }
    response.setHeader('Content-Type', 'application/json');
    switch (request.url.split('?')[0]) {
      case '/api/v1/auth/transactions':
        response.end(JSON.stringify({ transaction_id: 'at-fixture', client_secret: 'fixture-secret', user_code: 'ABCD-EFGH',
          verification_uri_complete: 'https://console.tianacloud.com/api/v1/a/ABCD-EFGH', expires_in: 240, poll_interval: 1 }));
        break;
      case '/api/v1/auth/transactions/at-fixture/poll':
        response.end(JSON.stringify(approved ? { status: 'approved', authorization_code: 'fixture-code', expires_in: 30 } : { status: 'pending' }));
        break;
      case '/api/v1/auth/token':
        exchanges++;
        response.end(JSON.stringify({ access_token: 'fixture-access', refresh_token: 'fixture-refresh', expires_in: 3600,
          refresh_expires_at: '2100-01-01T00:00:00Z', user: { user_id: 'prn_fixture', tenant_id: 'ten_fixture' } }));
        break;
      case '/api/v1/auth/transactions/whoami':
        whoamiCalls++;
        assert.equal(request.headers.authorization, 'Bearer fixture-access');
        response.end(JSON.stringify({user: {user_id: 'prn_fixture', tenant_id: 'ten_fixture', email: 'user@example.test'}}));
        break;
      case '/api/v1/usage':
        if (!quotaAvailable) { response.writeHead(503).end('{}'); break; }
        response.end(JSON.stringify({tenant_id:'ten_fixture',compute_used:'123',storage_used:'456',instances_used:'2',
          updated_at:1790083200123,period_start:1789948800000,period_end:1790553600000,
          limits:{compute:'10000',storage_bytes:'2000000000',max_instances:'3',period:'week'},blocked:false,reason:''}));
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
  const env = { ...process.env, TIANA_API_ORIGIN: `http://127.0.0.1:${server.address().port}`,
    XDG_CONFIG_HOME: path.join(directory, 'config') };
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
  assert.equal((await status()).connected, false);

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
  assert.equal((await fs.stat(path.join(directory, "config/tiana/credentials.json"))).isFile(), true, "login must use the isolated default credential store");
  for (const secret of ['fixture-secret', 'fixture-code', 'fixture-access', 'fixture-refresh']) {
    assert.equal((authenticated.stdout + authenticated.stderr).includes(secret), false);
  }
  const whoamiBefore = whoamiCalls;
  for (let i = 0; i < 3; i++) assert.equal((await status()).connected, true);
  assert.equal(whoamiCalls, whoamiBefore + 3, 'ordinary status verifies the saved account');
  quotaAvailable = false;
  const unavailable = await status();
  assert.equal(unavailable.connected, false);
  assert.equal(unavailable.code, 1);
  assert.match(unavailable.stdout, /Quota: unavailable/);
  quotaAvailable = true;
  assert.equal((await status()).connected, true);
  assert.equal((await start(cli.unAuth[process.platform]).finished).code, 0);
  assert.equal(logouts, 1);
  assert.equal((await status()).connected, false);
  assert.equal((await start(cli.unAuth[process.platform]).finished).code, 0, 'repeated logout failed');

  approved = false;
  const interrupted = start(cli.auth[process.platform]);
  await once(interrupted.child.stdout, 'data');
  interrupted.child.kill('SIGINT');
  assert.equal((await interrupted.finished).code, 130);
  assert.equal((await status()).connected, false);
});
