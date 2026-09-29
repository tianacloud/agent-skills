# Tiana Agent Skills

Agent Skills that help coding agents build, publish and maintain applications
with Tiana Cloud, including SQLite connections and source releases in Tiana Git.

## 安装并开始任务

这个仓库提供技能。用户同时要求安装技能和完成任务时，按以下流程衔接：

1. 用当前客户端支持的方式，从用户指定的仓库安装技能。所需技能的 `SKILL.md` 与引用资源可读取后，继续用户任务；本仓库的 npm 打包脚本属于分发维护流程。
2. 根据用户当前需求和技能描述选择入口，只加载对应技能及其明确引用的依赖。已有匹配的应用模板时从该模板技能开始；通用应用创建、发布或实例管理从 [Tiana](skills/tiana/SKILL.md) 开始；数据库操作从 [SQLite](skills/tiana-sqlite/SKILL.md) 开始。仅要求安装时，报告安装结果即可。
3. 需要使用应用模板时，将所选技能的 `assets/app/` 复制到用户的应用项目目录；尚无项目时，在技能安装目录和仓库检出之外创建独立应用目录。应用的依赖安装、Git、构建与发布在应用目录执行。技能来源仓库及其 Git remote 属于技能源码。
4. 任务需要 CLI 且命令缺失或登录需要恢复时，按 [CLI 安装与登录](skills/tiana/references/getting-started.md) 处理，然后继续原任务。

技能文件的相对路径从各自 `SKILL.md` 所在目录解析；安装器若将技能分别存放，使用客户端返回的安装位置。

## Skills

`tiana` is the shared entry point. Specialist skills are sibling directories,
identify `tiana` as their parent, and can be selected directly for a focused task.
Load detailed references only for the workflow being performed. After installation,
start at the selected skill’s `SKILL.md`; application work uses that skill’s
references/assets and the explicitly linked `tiana` / `tiana-sqlite` dependencies.
Copy the application template to a project directory before running its npm
commands. The repository root package manages skill distribution.

```text
skills/
├── tiana/                 Application workflow, instances, login and source releases
│   ├── SKILL.md           Entry point and workflow routing
│   └── references/        Application template, publishing and CLI details
├── tiana-sqlite/          SQL, schemas and application database connections
│   ├── SKILL.md
│   └── references/        CLI, JavaScript, shell and Rust workflows
├── tiana-two-to-three/    Pregnancy planning and family journey app starter
├── tiana-study/           Study planning and focus dashboard app starter
├── tiana-whiteboard/      Collaborative whiteboard app starter
├── tiana-ledger/          Personal income and expense ledger
├── tiana-notes/           Autosaving notebook with search and folders
├── tiana-calendar/        Personal calendar and daily agenda
└── tiana-branches/        Database branch design (preview only)
    ├── SKILL.md
    └── references/        Lifecycle model and proposed API
```

### `tiana`

Start here to build and publish a Tiana application, create and inspect instances,
or recover CLI login and saved credentials. The application workflow covers the
fixed HTML template, hash routing, hosted versions and source synchronization to
Tiana Git. Existing external repositories require source-hosting consent;
approved releases keep their hosted version linked to a verified source commit.

### `tiana-sqlite`

Query and connect to Tiana SQLite with the CLI, JavaScript SDK, shell or Rust
transport SDK. Browser connection, protocol selection and result decoding live
here; application packaging and publication live in `tiana`.

Install `@tianacloud/cli` from npm; see
[CLI installation](skills/tiana/references/getting-started.md).
Browser application guidance requires the new SDK `auth` interface and a shared
`window.tiana.auth` runtime provider. No static-token or older-version fallback is
provided. Refresh credentials remain with the trusted CLI/runtime, never skills
or browser code. The published `@tianacloud/serverless@0.1.0-beta.1` package has been verified
to include the SDK auth interface. Hosted runtime support is implemented; determine
the target environment’s readiness from current evidence, not a historical
deployment warning. The six app starters deliver a published URL for the user
to check; browser-based [runtime diagnosis](skills/tiana-sqlite/references/js-sdk.md#核验目标托管环境)
is for requested verification or connection troubleshooting.

### Application starters

`tiana-two-to-three`, `tiana-study`, `tiana-whiteboard`, `tiana-ledger`,
`tiana-notes`, and `tiana-calendar` include complete
application templates, SQLite schemas, and guided first screens. They use
`tiana` for source releases and hosting and `tiana-sqlite` for database access.
Use a verified SDK build with the account-auth provider before building them.

### `tiana-branches`

Plan around Tiana's preview database-branch lifecycle. This skill includes the
current design-only Control API proposal and does not present it as a released
or callable public API.

## Install

Skills use the separately installed `@tianacloud/cli` package, which provides
both `tiana` and `git-remote-tiana`. Importing a skill does not install these
commands. Follow [CLI installation](skills/tiana/references/getting-started.md)
in the agent's execution environment. For Windows and WorkBuddy, see
[Git helper troubleshooting](skills/tiana/references/windows-git-helper.md).

Install skills from GitHub with a compatible Agent Skills client:

```sh
npx skills add tianacloud/agent-skills
```

Pi users can install the npm package after it has been published:

```sh
pi install npm:@tianacloud/agent-skills
```

The repository root is also an Agent Plugins v1 package. Clients that support
the portable plugin format discover the immediate children of `skills/`.

### Doubao and other directory-based clients

Import the desired directory under `skills/`, preserving its `SKILL.md`, `references/`, and any `assets/` files together. If the client accepts ZIP uploads, zip one skill
directory with `SKILL.md` at the archive root.
For application development, import `tiana`, `tiana-sqlite`, and the relevant
application starter.
`tiana-branches` is only needed for database branch design work.

### WorkBuddy

Import the skill archives supplied for your client. For application development,
load `tiana`, `tiana-sqlite`, and the chosen application starter, then follow their
`SKILL.md` entry points.

## Maintaining this repository

Package generation, Connector integration and repository tests are covered in
[Contributing](https://github.com/tianacloud/agent-skills/blob/main/CONTRIBUTING.md).
These are maintainer workflows, separate from creating a customer's application.

## License

MIT
