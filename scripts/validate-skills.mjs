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

for (const skillDir of skillDirs) {
  process.stdout.write(`Validating ${skillDir}\n`);
  const result = spawnSync(validator, ["validate", skillDir], {
    stdio: "inherit",
  });
  if (result.status !== 0) {
    process.exit(result.status ?? 1);
  }
}

