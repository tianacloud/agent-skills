#!/usr/bin/env node

import { promises as fs } from "node:fs";
import path from "node:path";
import process from "node:process";

const root = process.cwd();
const manifest = JSON.parse(await fs.readFile(path.join(root, "plugin.json"), "utf8"));
const allowed = new Set([
  "$schema",
  "name",
  "version",
  "description",
  "author",
  "homepage",
  "repository",
  "license",
  "keywords",
  "extensions",
]);
const errors = [];

if (manifest.$schema !== "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json") {
  errors.push("plugin.json targets the wrong Agent Plugins schema");
}
if (!/^(?!.*(?:--|\.\.))[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?$/.test(manifest.name ?? "")) {
  errors.push("plugin.json has an invalid name");
}
for (const key of Object.keys(manifest)) {
  if (!allowed.has(key)) errors.push(`plugin.json has unsupported field ${key}`);
}

const skillsDir = path.join(root, "skills");
for (const entry of await fs.readdir(skillsDir, { withFileTypes: true })) {
  if (!entry.isDirectory()) continue;
  const skillFile = path.join(skillsDir, entry.name, "SKILL.md");
  try {
    const stat = await fs.lstat(skillFile);
    if (!stat.isFile()) errors.push(`${skillFile} is not a regular file`);
  } catch {
    errors.push(`${skillFile} is missing`);
  }
}

if (errors.length > 0) {
  process.stderr.write(`${errors.join("\n")}\n`);
  process.exit(1);
}
process.stdout.write("Portable plugin manifest and skill discovery are valid.\n");
