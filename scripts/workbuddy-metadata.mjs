export function addWorkBuddyFrontmatter(content, metadata, version, author) {
  if (!content.startsWith('---\n')) throw new Error('SKILL.md is missing YAML frontmatter');
  const end = content.indexOf('\n---\n', 4);
  if (end < 0) throw new Error('SKILL.md has unterminated YAML frontmatter');
  const fields = Object.entries({
    display_name: metadata.display_name,
    display_name_en: metadata.display_name_en,
    description_zh: metadata.description_zh,
    description_en: metadata.description_en,
    version,
    author,
  }).map(([name, value]) => `${name}: ${JSON.stringify(value)}`).join('\n');
  return `${content.slice(0, end)}\n${fields}${content.slice(end)}`;
}
