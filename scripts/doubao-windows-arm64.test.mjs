import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { once } from 'node:events';
import { promises as fs } from 'node:fs';
import { createHash } from 'node:crypto';
import { createRequire } from 'node:module';
import http from 'node:http';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';
import { setTimeout as delay } from 'node:timers/promises';

// Run against the downloaded delivery ZIP and the registry install, on native Windows ARM64.
const delivery = path.resolve(process.env.TIANA_TEST_DELIVERY ?? 'dist/doubao');
const plugin = path.resolve(process.env.TIANA_TEST_PLUGIN ?? 'dist/plugin');
const version = process.env.TIANA_TEST_CLI_VERSION;

for (const channel of ['v1', 'v2']) {
  test(`${channel}: Windows ARM64 installation and connector authentication (simulated service)`, { timeout: 120000 }, async t => {
    assert.equal(process.platform, 'win32');
    assert.equal(process.arch, 'arm64');
    assert.ok(version, 'TIANA_TEST_CLI_VERSION is required');
    const directory = await fs.mkdtemp(path.join(os.tmpdir(), 'tiana arm64 '));
    t.after(() => fs.rm(directory, { recursive: true, force: true }));
    const env = { ...process.env, XDG_CONFIG_HOME: path.join(directory, 'config'), TIANA_DIAGNOSTICS: '1' };
    for (const key of Object.keys(env)) {
      if (key.toLowerCase() === 'tiana_from') delete env[key];
    }
    const children = [];
    t.after(() => {
      for (const child of children) {
        if (child.exitCode === null && child.signalCode === null) child.kill();
      }
    });
    function start(command, native = false) {
      const child = native
        ? spawn(path.join(delivery, 'native/tiana.exe'), command.split(' ').slice(1), { env, stdio: ['ignore', 'pipe', 'pipe'] })
        : spawn(process.env.ComSpec || 'cmd.exe', ['/d', '/s', '/c', command], { env, windowsVerbatimArguments: true, stdio: ['ignore', 'pipe', 'pipe'] });
      children.push(child);
      const output = { stdout: '', stderr: '' };
      child.stdout.on('data', data => { output.stdout += data; });
      child.stderr.on('data', data => { output.stderr += data; });
      const finished = once(child, 'close').then(([code]) => ({ ...output, code }));
      return { child, output, finished };
    }
    async function run(command, native = channel === 'v1') {
      const result = await start(command, native).finished;
      assert.equal(result.code, 0, `${command}: ${result.stderr}\n${result.stdout}`);
      return result;
    }
    let cli, binary;
    if (channel === 'v1') {
      cli = {
        versionCheck: { win32: ['tiana.exe version'] }, help: { win32: ['tiana.exe help'] },
        auth: { win32: ['tiana.exe login'] }, status: { win32: ['tiana.exe status --auth-only --json'] },
        unAuth: { win32: ['tiana.exe logout'] }, statusMatchRegex: String.raw`"logged_in"\s*:\s*true\b`,
      };
      binary = path.join(delivery, 'native/tiana.exe');
      const manifest = JSON.parse(await fs.readFile(path.join(delivery, 'packages.json')));
      assert.equal(manifest.cli_version, version);
      const entry = manifest.packages.find(item => item.platform === 'windows-arm64');
      assert.ok(entry);
      assert.equal(createHash('sha256').update(await fs.readFile(binary)).digest('hex'), entry.binary_sha256);
    } else {
      cli = JSON.parse(await fs.readFile(path.join(plugin, 'com.doubao/cli.json'))).connectors.tiana;
      const prefix = path.join(directory, 'npm prefix');
      const originalPath = Object.entries(env).find(([key]) => key.toLowerCase() === 'path')[1];
      for (const key of Object.keys(env)) if (key.toLowerCase() === 'path') delete env[key];
      env.Path = `${prefix}${path.delimiter}${originalPath}`;
      env.npm_config_prefix = prefix;
      env.npm_config_cache = path.join(directory, 'npm cache');
      env.npm_config_registry = 'https://registry.npmjs.org/';
      for (const command of cli.install.win32) await run(command, false);
      const installedCLI = path.join(prefix, 'node_modules/@tianacloud/cli/package.json');
      const packageRoot = path.dirname(createRequire(installedCLI).resolve('@tianacloud/cli-win32-arm64/package.json'));
      const metadata = JSON.parse(await fs.readFile(path.join(packageRoot, 'package.json')));
      assert.equal(metadata.version, version);
      assert.deepEqual(metadata.os, ['win32']);
      assert.deepEqual(metadata.cpu, ['arm64']);
      binary = path.join(packageRoot, 'bin/tiana.exe');
    }
    const bytes = await fs.readFile(binary);
    const pe = bytes.readUInt32LE(0x3c);
    assert.equal(bytes.subarray(pe, pe + 4).toString(), 'PE\0\0');
    assert.equal(bytes.readUInt16LE(pe + 4), 0xaa64);
    const result = await run(cli.versionCheck.win32[0] + ' --json');
    const details = JSON.parse(result.stdout).data;
    assert.equal(details.version, version);
    assert.equal(details.default_acquisition_source, channel === 'v1' ? 'doubao' : '');
    await run(cli.help.win32[0]);
    console.log(JSON.stringify({ channel, platform: process.platform, arch: process.arch, version,
      binary_sha256: createHash('sha256').update(bytes).digest('hex'), default_acquisition_source: details.default_acquisition_source }));

    let approved = false, calls = 0, transactions = 0, exchanges = 0;
    const sources = [];
    const server = http.createServer(async (request, response) => {
      calls++;
      let body = ''; for await (const chunk of request) body += chunk;
      response.setHeader('Content-Type', 'application/json');
      switch (request.url.split('?')[0]) {
        case '/api/v1/auth/transactions':
          transactions++;
          sources.push(JSON.parse(body).client.acquisition_source);
          response.end(JSON.stringify({ transaction_id: 'fixture', client_secret: 'synthetic-secret', user_code: 'ABCD-EFGH',
            verification_uri_complete: 'https://console.example.test/approve?code=ABCD-EFGH', expires_in: 60, poll_interval: 1 }));
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
    env.TIANA_API_ORIGIN = `http://127.0.0.1:${server.address().port}`;
    async function status(expected) {
      const before = calls;
      const result = await run(cli.status.win32[0]);
      assert.equal(JSON.parse(result.stdout).data.logged_in, expected);
      assert.equal(new RegExp(cli.statusMatchRegex).test(result.stdout), expected);
      assert.equal(calls, before);
    }
    await status(false);
    for (const mode of ['text', 'json']) {
      approved = false;
      const before = transactions, exchangedBefore = exchanges;
      const auth = start(cli.auth.win32[0] + ' --no-open' + (mode === 'json' ? ' --json' : ''), channel === 'v1');
      const deadline = performance.now() + 15000;
      while (!(auth.output.stdout + auth.output.stderr).includes('https://console.example.test/approve')) {
        assert.ok(performance.now() < deadline, `login URL not emitted: ${auth.output.stderr}`);
        await delay(50);
      }
      await delay(1200);
      assert.equal(auth.child.exitCode, null, 'login must wait for approval');
      assert.equal(transactions, before + 1);
      assert.equal(sources.at(-1), 'doubao');
      if (mode === 'json') assert.equal(auth.output.stdout, '');
      approved = true;
      const terminal = await auth.finished;
      assert.equal(terminal.code, 0, terminal.stderr);
      assert.equal(exchanges, exchangedBefore + 1);
      if (mode === 'json') assert.equal(JSON.parse(terminal.stdout).data.logged_in, true);
      await status(true);
      await run(cli.unAuth.win32[0]);
      await status(false);
      await run(cli.unAuth.win32[0]);
    }
  });
}
