#!/usr/bin/env node

import { promises as fs } from "node:fs";
import path from "node:path";
import process from "node:process";

const root = process.cwd();
const pkg = JSON.parse(await fs.readFile(path.join(root, "package.json"), "utf8"));
const plugin = JSON.parse(await fs.readFile(path.join(root, "plugin.json"), "utf8"));
const workbuddy = JSON.parse(await fs.readFile(path.join(root, "packaging", "workbuddy.json"), "utf8"));
const connector = JSON.parse(await fs.readFile(path.join(root, "packaging/workbuddy/tiana-cloud/connector-meta.json"), "utf8"));
const errors = [];

if (pkg.name !== "@tianacloud/agent-skills") errors.push("unexpected npm package name");
if (pkg.version !== plugin.version) errors.push("package.json and plugin.json versions differ");
if (pkg.version !== connector.version) errors.push("Connector and package.json versions differ");

const skillNames = (await fs.readdir(path.join(root, "skills"), { withFileTypes: true }))
  .filter((entry) => entry.isDirectory())
  .map((entry) => entry.name)
  .sort();
const packagedNames = Object.keys(workbuddy.skills).sort();
if (JSON.stringify(skillNames) !== JSON.stringify(packagedNames)) {
  errors.push("WorkBuddy metadata does not cover exactly the canonical skills");
}

for (const name of skillNames) {
  const body = await fs.readFile(path.join(root, "skills", name, "SKILL.md"), "utf8");
  if (!body.includes(`version: "${pkg.version}"`)) {
    errors.push(`${name} metadata version does not match package.json`);
  }
}

const catalog = JSON.parse(await fs.readFile(path.join(root, "skills.sh.json"), "utf8"));
const indexed = catalog.groupings.flatMap((group) => group.skills).sort();
if (JSON.stringify(skillNames) !== JSON.stringify(indexed)) {
  errors.push("skills.sh.json does not index exactly the canonical skills");
}

if (errors.length > 0) {
  process.stderr.write(`${errors.join("\n")}\n`);
  process.exit(1);
}
process.stdout.write(`All package metadata agrees on version ${pkg.version}.\n`);
