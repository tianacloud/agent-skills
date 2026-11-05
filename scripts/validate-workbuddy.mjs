#!/usr/bin/env node

import { promises as fs } from "node:fs";
import os from "node:os";
import path from "node:path";
import process from "node:process";
import { spawnSync } from "node:child_process";
import { strFromU8, unzipSync } from "fflate";

const root = process.cwd();
const temporary = await fs.mkdtemp(path.join(os.tmpdir(), "tiana-workbuddy-validation-"));
const pkg = JSON.parse(await fs.readFile(path.join(root, "package.json"), "utf8"));
const config = JSON.parse(await fs.readFile(path.join(root, "packaging", "workbuddy.json"), "utf8"));
const errors = [];

try {
  const result = spawnSync(process.execPath, ["scripts/build-workbuddy.mjs", "--output", temporary], {
    cwd: root,
    stdio: "inherit",
  });
  if (result.status !== 0) process.exit(result.status ?? 1);

  for (const name of Object.keys(config.skills)) {
    const file = path.join(temporary, `${name}-${pkg.version}.zip`);
    const zip = unzipSync(new Uint8Array(await fs.readFile(file)));
    const names = Object.keys(zip);
    if (!names.includes("SKILL.md")) errors.push(`${name}: ZIP has no root SKILL.md`);
    const skill = zip["SKILL.md"] ? strFromU8(zip["SKILL.md"]) : "";
    for (const field of ["description_zh", "description_en", "version", "author"]) {
      if (!new RegExp(`^${field}:`, "m").test(skill)) errors.push(`${name}: missing ${field}`);
    }
    for (const entry of names.filter((entry) => entry.endsWith(".md") && entry !== "SKILL.md")) {
      if (!entry.startsWith("references/")) errors.push(`${name}: unexpected Markdown path ${entry}`);
    }
  }
} finally {
  await fs.rm(temporary, { recursive: true, force: true });
}

if (errors.length > 0) {
  process.stderr.write(`${errors.join("\n")}\n`);
  process.exit(1);
}
process.stdout.write("WorkBuddy archives contain the required localized metadata and resources.\n");
