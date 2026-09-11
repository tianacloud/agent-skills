#!/usr/bin/env node

import { promises as fs } from "node:fs";
import path from "node:path";
import process from "node:process";

const skillsRoot = path.join(process.cwd(), "skills");
const markdownLink = /!?\[[^\]]*\]\(\s*(<[^>]+>|[^)\s]+)(?:\s+(?:"[^"]*"|'[^']*'))?\s*\)/g;

async function walk(directory) {
  const files = [];
  for (const entry of await fs.readdir(directory, { withFileTypes: true })) {
    const full = path.join(directory, entry.name);
    if (entry.isDirectory()) files.push(...(await walk(full)));
    if (entry.isFile()) files.push(full);
  }
  return files;
}

function localTarget(link, fromFile, skillDir) {
  const clean = link.replace(/^<|>$/g, "").split("#")[0].split("?")[0];
  if (!clean || clean.startsWith("#") || /^[a-z][a-z0-9+.-]*:/i.test(clean)) {
    return null;
  }
  const target = path.resolve(path.dirname(fromFile), clean);
  const relative = path.relative(skillDir, target);
  if (relative.startsWith("..") || path.isAbsolute(relative)) return null;
  return target;
}

const problems = [];
const entries = await fs.readdir(skillsRoot, { withFileTypes: true });
for (const entry of entries.filter((item) => item.isDirectory())) {
  const skillDir = path.join(skillsRoot, entry.name);
  const entrypoint = path.join(skillDir, "SKILL.md");
  const allMarkdown = (await walk(skillDir)).filter((file) => file.endsWith(".md"));
  const existing = new Set(allMarkdown.map((file) => path.resolve(file)));
  const reached = new Set([path.resolve(entrypoint)]);
  const queue = [entrypoint];

  while (queue.length > 0) {
    const current = queue.shift();
    const content = await fs.readFile(current, "utf8");
    for (const match of content.matchAll(markdownLink)) {
      const target = localTarget(match[1], current, skillDir);
      if (!target || !target.endsWith(".md")) continue;
      const absolute = path.resolve(target);
      if (!existing.has(absolute)) {
        problems.push(`${entry.name}: broken reference ${match[1]} in ${path.relative(skillDir, current)}`);
      } else if (!reached.has(absolute)) {
        reached.add(absolute);
        queue.push(absolute);
      }
    }
  }

  for (const file of allMarkdown) {
    if (!reached.has(path.resolve(file))) {
      problems.push(`${entry.name}: orphan markdown file ${path.relative(skillDir, file)}`);
    }
  }
}

if (problems.length > 0) {
  process.stderr.write(`${problems.join("\n")}\n`);
  process.exit(1);
}
process.stdout.write("All skill Markdown references are reachable and valid.\n");

