#!/usr/bin/env node

import { promises as fs } from "node:fs";
import os from "node:os";
import path from "node:path";
import process from "node:process";
import { zipSync } from "fflate";
import { addWorkBuddyFrontmatter } from "./workbuddy-metadata.mjs";

const root = process.cwd();
const outputFlag = process.argv.indexOf("--output");
const outputDir = path.resolve(
  outputFlag >= 0 ? process.argv[outputFlag + 1] : path.join(root, "dist", "workbuddy"),
);
if (outputFlag >= 0 && !process.argv[outputFlag + 1]) {
  throw new Error("--output requires a directory");
}

const pkg = JSON.parse(await fs.readFile(path.join(root, "package.json"), "utf8"));
const config = JSON.parse(await fs.readFile(path.join(root, "packaging", "workbuddy.json"), "utf8"));
await fs.mkdir(outputDir, { recursive: true });

async function archiveEntries(directory, relative = "") {
  const result = {};
  for (const entry of await fs.readdir(directory, { withFileTypes: true })) {
    const absolute = path.join(directory, entry.name);
    const archivePath = relative ? `${relative}/${entry.name}` : entry.name;
    if (entry.isDirectory()) Object.assign(result, await archiveEntries(absolute, archivePath));
    if (entry.isFile()) result[archivePath] = new Uint8Array(await fs.readFile(absolute));
  }
  return result;
}

for (const [name, metadata] of Object.entries(config.skills)) {
  const source = path.join(root, "skills", name);
  const staging = await fs.mkdtemp(path.join(os.tmpdir(), `tiana-${name}-`));
  try {
    await fs.cp(source, staging, { recursive: true });
    const skillFile = path.join(staging, "SKILL.md");
    const content = await fs.readFile(skillFile, "utf8");
    await fs.writeFile(skillFile, addWorkBuddyFrontmatter(content, metadata, pkg.version, config.author));

    const archivePath = path.join(outputDir, `${name}-${pkg.version}.zip`);
    const archive = zipSync(await archiveEntries(staging), { level: 9 });
    await fs.writeFile(archivePath, archive);
    process.stdout.write(`${archivePath}\n`);
  } finally {
    await fs.rm(staging, { recursive: true, force: true });
  }
}
