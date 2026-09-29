import { build } from "vite";
import { readFile, writeFile } from "node:fs/promises";

const commit = process.argv[2];
if (!/^(?:[0-9a-f]{40}|[0-9a-f]{64})$/.test(commit ?? ""))
  throw new Error("先按源码发布指引核验干净工作树，再运行 node scripts/build.mjs <完整提交号>。");
const source = JSON.parse(await readFile("source.json", "utf8"));
if (!source.git_instance_id.startsWith("git-"))
  throw new Error("先在 source.json 填写已核实的 Tiana Git 实例 ID。");
await build();
const manifest = JSON.parse(await readFile("dist/tiana.app.json", "utf8"));
manifest.git_instance_id = source.git_instance_id;
manifest.source_commit = commit;
await writeFile(
  "dist/tiana.app.json",
  `${JSON.stringify(manifest, null, 2)}\n`,
);
