import test from "node:test";
import assert from "node:assert/strict";
import { mkdtemp, cp, rename, readFile, writeFile, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import { execFileSync } from "node:child_process";

for (const name of ["study", "two-to-three", "whiteboard"])
  test(`${name}: build from a verified source commit`, async (t) => {
    const directory = await mkdtemp(path.join(tmpdir(), `tiana-${name}-build-`));
    t.after(() => rm(directory, { recursive: true, force: true }));
    await cp(new URL(`../skills/tiana-${name}/assets/app/`, import.meta.url), directory, { recursive: true });
    await rename(path.join(directory, "gitignore.template"), path.join(directory, ".gitignore"));
    await writeFile(path.join(directory, "source.json"), JSON.stringify({ git_instance_id: "git-fixture" }));
    const run = (command, args) => execFileSync(command, args, { cwd: directory, encoding: "utf8", stdio: "pipe" });
    run("npm", ["ci", "--ignore-scripts", "--no-audit", "--no-fund"]);
    run("git", ["init", "-q"]);
    run("git", ["add", "."]);
    run("git", ["-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "-qm", "Application source fixture"]);
    const commit = run("git", ["rev-parse", "HEAD"]).trim();
    assert.equal(run("git", ["status", "--porcelain"]), "");
    const sourceManifest = await readFile(path.join(directory, "public/tiana.app.json"), "utf8");
    run(process.execPath, ["scripts/build.mjs", commit]);
    const manifestPath = path.join(directory, "dist/tiana.app.json");
    const built = await readFile(manifestPath, "utf8");
    const manifest = JSON.parse(built);
    assert.equal(manifest.git_instance_id, "git-fixture");
    assert.equal(manifest.source_commit, commit);
    assert.equal(await readFile(path.join(directory, "public/tiana.app.json"), "utf8"), sourceManifest);
    assert.equal(run("git", ["status", "--porcelain"]), "");
    assert.equal(run("git", ["rev-parse", "HEAD"]).trim(), commit);
    const module = await readFile(path.join(directory, "dist", manifest.entry), "utf8");
    assert.ok(!module.includes("process.env.NODE_ENV"));
    for (const style of manifest.styles) await readFile(path.join(directory, "dist", style));
    for (const args of [[], ["abc"]]) {
      assert.throws(() => run(process.execPath, ["scripts/build.mjs", ...args]), /完整提交号/);
      assert.equal(await readFile(manifestPath, "utf8"), built);
    }
  });
