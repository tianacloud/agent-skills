#!/usr/bin/env node

import { promises as fs } from "node:fs";
import path from "node:path";
import process from "node:process";
import { spawnSync } from "node:child_process";

const skillsRoot = path.join(process.cwd(), "skills");
const validator = path.join(process.cwd(), "node_modules", ".bin", "skills-ref");

const entries = await fs.readdir(skillsRoot, { withFileTypes: true });
const skillDirs = entries
  .filter((entry) => entry.isDirectory())
  .map((entry) => path.join("skills", entry.name))
  .sort();

if (skillDirs.length === 0) {
  throw new Error("No skill directories found under skills/");
}

const platformNames = /work[\s_-]*buddy|code[\s_-]*buddy|qwen(?:work)?|千问|豆包|doubao|codex|claude/i;
async function checkPlatformNeutralContent(file) {
  const info = await fs.stat(file);
  if (info.isDirectory()) {
    for (const entry of await fs.readdir(file)) {
      if (entry === "__pycache__" || /\.py[cod]$/.test(entry)) continue;
      await checkPlatformNeutralContent(path.join(file, entry));
    }
    return;
  }
  if (platformNames.test(path.relative(process.cwd(), file))) throw new Error(`Platform name in Skill file path: ${file}`);
  const text = await fs.readFile(file, "utf8");
  for (const [line, content] of text.split("\n").entries()) {
    if (platformNames.test(content)) throw new Error(`Platform name in Skill content: ${file}:${line + 1}`);
  }
}
await checkPlatformNeutralContent(skillsRoot);
await checkPlatformNeutralContent(path.join(process.cwd(), "README.md"));

for (const skillDir of skillDirs) {
  process.stdout.write(`Validating ${skillDir}\n`);
  const result = spawnSync(validator, ["validate", skillDir], {
    stdio: "inherit",
  });
  if (result.status !== 0) {
    process.exit(result.status ?? 1);
  }
}

