# Contributing

Edit the canonical four directories under skills/. npm, portable plugins,
WorkBuddy ZIPs and the Connector use these same instructions. App source and
its build/persistence/browser tests belong to tianacloud/template-apps.

## Verify locally

```sh
npm ci --ignore-scripts
npm run validate:ci
npm run test:installer
npm run test:release
npm run build:workbuddy
npm run build:connector
node scripts/pack-skills.mjs dist/npm-release
```

The installer suite runs the actual npm tarball and pinned skills tool, verifies
copied Codex files after removing the downloaded source, and checks explicit
paths, repeat installation and preservation of other skills. Connector validation
checks the archive and existing configuration; it is not a WorkBuddy runtime test.
Process-level Connector auth fixtures remain available via test:connector-auth
with TIANA_TEST_CLI_BINARY pointing at the corresponding local CLI.

## npm initial setup and Actions release

The npm scope owner initializes @tianacloud/agent-skills once and configures its
Trusted Publisher: GitHub owner tianacloud, repository agent-skills, workflow
release.yml, direct publication enabled. The job uses GitHub-hosted Ubuntu,
id-token: write, Node.js 24 and npm 11.20.0. See
[npm trusted publishing](https://docs.npmjs.com/trusted-publishers/).

Choose the release version, align package.json/lockfile, plugin.json, Connector
metadata and all four SKILL.md metadata and check-command versions. Validation
checks distribution alignment. Push the immutable vVERSION source tag after
review. GitHub Actions validates and tests, packs one npm tarball, retains it
with its integrity descriptor and WorkBuddy archives, then publishes that exact
artifact. Stable releases use latest; prereleases use next. Update discovery
checks latest.

Manual dispatch accepts an existing matching tag and defaults to dry_run=true.
It builds and verifies without publishing. After publication, the workflow
installs the exact registry version in a fresh persistent skills directory.

Retry a failed publish job with the original skills-release artifact. Local
recovery after downloading its npm-release directory uses:

```sh
node scripts/publish-skills.mjs ARTIFACT_DIRECTORY
```

Manual publication uses npm login or NPM_TOKEN; its npmrc references the variable
without embedding a token. Existing identical versions are read back and reused.
Conflicting content requires a new version. A lost publication response is resolved
by reading registry integrity before claiming failure. Inspect an unexpected
channel before changing it.

Do not edit generated archives. Detailed historical Connector evidence lives in
docs/ and is separate from current Skills installation and application workflows.
