import { mkdtemp, cp, readFile, writeFile, rm, rename } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import { pathToFileURL } from "node:url";
import { execFileSync } from "node:child_process";
import { DatabaseSync } from "node:sqlite";

export async function prepareApp(name) {
  const directory = await mkdtemp(path.join(tmpdir(), `tiana-${name}-test-`));
  await cp(
    new URL(`../../skills/tiana-${name}/assets/app/`, import.meta.url),
    directory,
    { recursive: true },
  );
  await rename(path.join(directory, "gitignore.template"), path.join(directory, ".gitignore"));
  const manifestFile = path.join(directory, "public/tiana.app.json");
  const manifest = JSON.parse(await readFile(manifestFile, "utf8"));
  manifest.web_id = `fixture_${name}`;
  manifest.database_instance_id = "sqlite-fixture";
  await writeFile(manifestFile, JSON.stringify(manifest));
  await writeFile(
    path.join(directory, "source.json"),
    JSON.stringify({ git_instance_id: "git-fixture" }),
  );
  const run = (command, args) =>
    execFileSync(command, args, {
      cwd: directory,
      stdio: "pipe",
      encoding: "utf8",
    });
  try {
    run("npm", ["ci", "--ignore-scripts", "--no-audit", "--no-fund"]);
    run("git", ["init", "-q"]);
    run("git", ["add", "."]);
    run("git", [
      "-c",
      "user.name=Fixture",
      "-c",
      "user.email=fixture@example.invalid",
      "commit",
      "-qm",
      "Application build fixture",
    ]);
    run("npm", ["run", "build"]);
    const sdkTypes = await readFile(
      path.join(
        directory,
        "node_modules/@tianacloud/serverless/dist/index.d.ts",
      ),
      "utf8",
    );
    if (!sdkTypes.includes("readonly auth: TianaAuthProvider"))
      throw new Error("Installed SDK lacks account auth");
    const { build } = await import(
      pathToFileURL(path.join(directory, "node_modules/esbuild/lib/main.js"))
    );
    await build({
      entryPoints: [path.join(directory, "src/store.js")],
      bundle: true,
      platform: "node",
      format: "esm",
      outfile: path.join(directory, "dist/store.mjs"),
    });
    const store = await import(
      pathToFileURL(path.join(directory, "dist/store.mjs"))
    );
    const db = new DatabaseSync(":memory:");
    db.exec(await readFile(path.join(directory, "schema.sql"), "utf8"));
    const codec = await import(
      pathToFileURL(
        path.join(
          directory,
          "node_modules/@tianacloud/serverless/dist/codec.js",
        ),
      )
    );
    const calls = [];
    let failure = null;
    let pausedWrite = null;
    async function handle(frame) {
      const request = codec.decodeRequestFrameBytes(new Uint8Array(frame));
      const pipeline = JSON.parse(new TextDecoder().decode(request.body));
      const statement = pipeline.requests[0].stmt;
      calls.push(statement);
      const write = !/^SELECT\b/i.test(statement.sql);
      if (write && pausedWrite) {
        const pause = pausedWrite;
        pausedWrite = null;
        pause.started();
        await pause.wait;
      }
      if (failure === "before-write" && write) {
        failure = null;
        throw new Error("fixture disconnected before write");
      }
      const args = (statement.args || []).map((arg) =>
        arg.type === "null"
          ? null
          : arg.type === "integer"
            ? Number(arg.value)
            : arg.value,
      );
      let first;
      try {
        const query = db.prepare(statement.sql);
        const columns = query.columns();
        const rows = columns.length ? query.all(...args) : [];
        const affected = columns.length
          ? 0
          : Number(query.run(...args).changes);
        first = {
          type: "ok",
          response: {
            type: "execute",
            result: {
              cols: columns.map((column) => ({
                name: column.name,
                decltype: null,
              })),
              rows: rows.map((row) =>
                columns.map((column) => {
                  const value = row[column.name];
                  return value === null
                    ? { type: "null" }
                    : typeof value === "number"
                      ? { type: "integer", value: String(value) }
                      : { type: "text", value: String(value) };
                }),
              ),
              affected_row_count: affected,
            },
          },
        };
      } catch (error) {
        first = {
          type: "error",
          error: { message: error.message, code: "SQL_ERROR" },
        };
      }
      if (failure === "after-write" && write) {
        failure = null;
        throw new Error("fixture disconnected after commit");
      }
      const response = Buffer.from(
        JSON.stringify({
          results: [first, { type: "ok", response: { type: "close" } }],
        }),
      );
      const metadata = {
        metadata_version: 1,
        request_id: request.metadata.request_id,
        status: 200,
        status_text: "OK",
        headers: [{ name: "content-type", value: "application/json" }],
        body_length: response.length,
      };
      return codec.encodeResponseFrameBytes(metadata, response);
    }
    return {
      directory,
      store,
      db,
      calls,
      handle,
      pauseNextWrite() {
        let started, resume;
        const signal = new Promise((resolve) => (started = resolve));
        const wait = new Promise((resolve) => (resume = resolve));
        pausedWrite = { started, wait };
        return { started: signal, resume };
      },
      failNext(kind) {
        failure = kind;
      },
      async fetch(_url, init) {
        const body = await handle(init.body);
        return new Response(body, {
          headers: {
            "content-type": "application/vnd.tiana.fetch.v1",
            "cache-control": "no-store",
          },
        });
      },
      async cleanup() {
        db.close();
        await rm(directory, { recursive: true, force: true });
      },
      commit: run("git", ["rev-parse", "HEAD"]).trim(),
    };
  } catch (error) {
    await rm(directory, { recursive: true, force: true });
    throw error;
  }
}
export function runtime() {
  return {
    auth: { getAccessToken: async () => "fixture-access-token" },
    connection: async () => ({
      origin: "https://ep-00000000000000000000000000.fixture.test",
      sql_api: "hrana-v3",
    }),
  };
}
