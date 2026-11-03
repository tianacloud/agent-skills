import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { once } from 'node:events';
import { promises as fs } from 'node:fs';
import http from 'node:http';
import os from 'node:os';
import path from 'node:path';
import { setTimeout as delay } from 'node:timers/promises';
import test from 'node:test';

const cli = {
  auth: {commands: ['tiana login']},
  status: {commands: ['tiana status --auth-only --json']},
  un_auth: {commands: ['tiana logout']},
  status_match_rex: String.raw`"logged_in"\s*:\s*true\b`,
};
const binary = process.env.TIANA_TEST_CLI_BINARY;

test('real CLI blocking login and local status with a simulated browser (not Doubao)', {
  skip: !binary || !['linux', 'darwin'].includes(process.platform), timeout: 45000,
}, async t => {
  const directory = await fs.mkdtemp(path.join(os.tmpdir(), 'tiana-doubao-auth-'));
  t.after(() => fs.rm(directory, { recursive: true, force: true }));
  const browserLog = path.join(directory, 'browser.log');
  const launcher = path.join(directory, process.platform === 'darwin' ? 'open' : 'xdg-open');
  await fs.writeFile(launcher, '#!/bin/sh\nprintf "%s\\n" "$@" >> "$TIANA_TEST_BROWSER_LOG"\nexit "${TIANA_TEST_BROWSER_EXIT:-0}"\n', { mode: 0o700 });
  const link = 'https://console.example.test/approve?code=ABCD-EFGH&return=a%20b';
  let approved = false, calls = 0, transactions = 0, exchanges = 0;
  const server = http.createServer(async (request, response) => {
    calls++;
    for await (const chunk of request) { /* Consume the fixture request. */ }
    response.setHeader('Content-Type', 'application/json');
    switch (request.url.split('?')[0]) {
      case '/api/v1/auth/transactions':
        transactions++;
        response.end(JSON.stringify({ transaction_id: 'fixture', client_secret: 'synthetic-secret', user_code: 'ABCD-EFGH',
          verification_uri_complete: link, expires_in: 60, poll_interval: 1 }));
        break;
      case '/api/v1/auth/transactions/fixture/poll':
        response.end(JSON.stringify(approved ? { status: 'approved', authorization_code: 'synthetic-code' } : { status: 'pending' }));
        break;
      case '/api/v1/auth/token':
        exchanges++;
        response.end(JSON.stringify({ access_token: 'synthetic-access', refresh_token: 'synthetic-refresh', expires_in: 3600,
          user: { user_id: 'user-fixture', tenant_id: 'tenant-fixture' } }));
        break;
      case '/api/v1/auth/transactions/logout': response.writeHead(204).end(); break;
      default: response.writeHead(503).end('{}');
    }
  });
  server.listen(0, '127.0.0.1');
  await once(server, 'listening');
  t.after(() => new Promise(resolve => server.close(resolve)));
  const env = { ...process.env, TIANA_API_ORIGIN: `http://127.0.0.1:${server.address().port}`,
    XDG_CONFIG_HOME: path.join(directory, 'config'), PATH: `${directory}${path.delimiter}${process.env.PATH}`,
    TIANA_TEST_BROWSER_LOG: browserLog, TIANA_DIAGNOSTICS: '1' };
  function start(command, extraEnv = {}) {
    const [name, ...args] = command.split(' ');
    assert.equal(name, 'tiana');
    const child = spawn(binary, args, { env: { ...env, ...extraEnv }, stdio: ['ignore', 'pipe', 'pipe'] });
    t.after(() => { if (child.exitCode === null && child.signalCode === null) child.kill('SIGKILL'); });
    const output = { stdout: '', stderr: '' };
    child.stdout.on('data', data => { output.stdout += data; });
    child.stderr.on('data', data => { output.stderr += data; });
    const finished = once(child, 'close').then(([code, signal]) => ({ ...output, code, signal }));
    return { child, output, finished };
  }
  async function waitFor(check, label) {
    const deadline = performance.now() + 5000;
    while (!await check()) { assert.ok(performance.now() < deadline, label); await delay(20); }
  }
  async function status(expected) {
    const before = calls;
    const result = await start(cli.status.commands[0]).finished;
    assert.equal(result.code, 0, result.stderr);
    assert.equal(JSON.parse(result.stdout).data.logged_in, expected);
    assert.equal(new RegExp(cli.status_match_rex).test(result.stdout), expected);
    assert.equal(calls, before, 'status must not request quota, refresh or remote authentication');
  }
  await status(false);
  await assert.rejects(fs.stat(env.XDG_CONFIG_HOME), { code: 'ENOENT' });

  for (const mode of ['text', 'json', 'browser-failed', 'no-open']) {
    approved = false;
    await fs.rm(browserLog, { force: true });
    const command = cli.auth.commands[0] + (mode === 'json' ? ' --json' : mode === 'no-open' ? ' --no-open' : '');
    const beforeTransactions = transactions, beforeExchanges = exchanges;
    const auth = start(command, { TIANA_TEST_BROWSER_EXIT: mode === 'browser-failed' ? '1' : '0' });
    await waitFor(() => (auth.output.stdout + auth.output.stderr).includes(link), 'login URL not emitted');
    if (mode !== 'no-open') {
      await waitFor(async () => (await fs.readFile(browserLog, 'utf8').catch(() => '')) === `${link}\n`, 'browser did not receive the full URL as one argument');
    }
    if (mode === 'browser-failed') await waitFor(() => auth.output.stderr.includes('could not open a browser'), 'browser failure not reported');
    await delay(mode === 'text' ? 5500 : 1100);
    assert.equal(auth.child.exitCode, null, 'login exited before browser approval');
    assert.equal(auth.child.signalCode, null);
    if (mode === 'json') assert.equal(auth.output.stdout, '', 'JSON stdout must wait for the terminal result');
    assert.equal(transactions, beforeTransactions + 1, 'browser launch failure must keep the same transaction');
    if (mode === 'no-open') await assert.rejects(fs.stat(browserLog), { code: 'ENOENT' });
    approved = true;
    const result = await auth.finished;
    assert.equal(result.code, 0, result.stderr);
    assert.equal(exchanges, beforeExchanges + 1);
    if (mode === 'json') {
      assert.deepEqual(JSON.parse(result.stdout), { status: 'succeeded', data: { logged_in: true }, error: null });
      assert.ok(result.stderr.includes(link));
    } else assert.ok(result.stdout.includes(`Open:\n${link}\n\nWaiting for authentication...\n`));
    for (const secret of ['synthetic-secret', 'synthetic-code', 'synthetic-access', 'synthetic-refresh']) {
      assert.equal((result.stdout + result.stderr).includes(secret), false);
    }
    const credentials = path.join(env.XDG_CONFIG_HOME, 'tiana/credentials.json');
    const saved = await fs.readFile(credentials);
    for (let i = 0; i < 3; i++) await status(true);
    assert.deepEqual(await fs.readFile(credentials), saved, 'status changed saved credentials');
    assert.equal((await start(cli.un_auth.commands[0]).finished).code, 0);
    await status(false);
    assert.equal((await start(cli.un_auth.commands[0]).finished).code, 0, 'logout must be idempotent');
  }

  for (const signal of ['SIGINT', 'SIGTERM']) {
    approved = false;
    const interrupted = start('tiana login --json --no-open');
    await waitFor(() => interrupted.output.stderr.includes(link), 'cancel fixture did not start');
    interrupted.child.kill(signal);
    const result = await interrupted.finished;
    assert.equal(result.code, 130);
    assert.equal(JSON.parse(result.stdout).error.code, 'CANCELLED');
    await status(false);
  }
});
