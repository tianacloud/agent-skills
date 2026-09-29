import { build } from "vite";
import { readFile, writeFile } from "node:fs/promises";
import { execFileSync } from "node:child_process";

const git = (...args) => execFileSync("git", args, { encoding: "utf8" }).trim();
const source = JSON.parse(await readFile("source.json", "utf8"));
if (!source.git_instance_id.startsWith("git-"))
  throw new Error("先在 source.json 填写已核实的 Tiana Git 实例 ID。");
if (git("status", "--porcelain"))
  throw new Error("请先提交应用源码与锁文件，再从干净的源码提交构建。");
const commit = git("rev-parse", "HEAD");
await build();
const manifest = JSON.parse(await readFile("dist/tiana.app.json", "utf8"));
manifest.git_instance_id = source.git_instance_id;
manifest.source_commit = commit;
await writeFile(
  "dist/tiana.app.json",
  `${JSON.stringify(manifest, null, 2)}\n`,
);
