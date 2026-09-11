# Repository Guidance

This repository contains Agent Skills for Tiana Cloud. The directories directly
under `skills/` are the canonical source for every distribution format.

- Keep each `SKILL.md` concise and move conditional detail into directly linked
  files under `references/`.
- Describe shipped behavior from current product documentation and
  implementations. Keep proposed interfaces visibly marked as preview or
  design-only.
- Do not add an MCP declaration until Tiana has a real user-facing MCP service.
- Keep the version in `package.json`, `plugin.json`, skill metadata, and
  WorkBuddy packaging metadata aligned.
- Run `npm run validate:ci` before submitting changes.

