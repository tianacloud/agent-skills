# Tiana Agent Skills

四个基础技能覆盖 Tiana 账号与实例、SQLite、Git 和 Web 应用。应用模板由在线目录提供，用户描述需求后，Agent 根据实时目录决定使用模板还是直接开发。

## 从 npm 安装

需要 Node.js 22.20+：

```sh
npx --yes @tianacloud/agent-skills@latest install --agent codex
```

安装器调用精确依赖的 skills 工具，把 npm 包中的四个技能复制到客户端的持久目录；Codex 当前工具使用 `~/.agents/skills/`。不传目标时选择客户端：

```sh
npx --yes @tianacloud/agent-skills@latest install
```

目录导入型客户端可指定实际技能根目录：

```sh
npx --yes @tianacloud/agent-skills@latest install --dir /path/to/client/skills
```

Windows PowerShell 使用 `npx.cmd`。目录可以含空格，用引号包住。重复安装会更新这四个技能目录，其他技能保留。安装完成后让客户端重载技能或开始新会话。

WorkBuddy、豆包按所用版本的目录／ZIP 导入方式加载这四个目录，保留 SKILL.md 和 references。若要求 ZIP，可将每个技能目录的内容打包，SKILL.md 位于包根部。WorkBuddy 专用本地化 ZIP 由维护者构建流程提供；本仓验证 ZIP 格式和内容，不声称已验收这些客户端的运行行为。

## 四个入口

| 技能 | 职责 |
| --- | --- |
| [tiana](skills/tiana/SKILL.md) | CLI 安装、登录、账号额度和通用实例管理 |
| [tiana-sqlite](skills/tiana-sqlite/SKILL.md) | SQL、表结构、SDK 连接和数据库分支 |
| [tiana-git](skills/tiana-git/SKILL.md) | Git 实例、原生仓库操作和源码版本同步 |
| [tiana-web](skills/tiana-web/SKILL.md) | 实时模板选择、工程与数据初始化、通用开发、构建发布 |

Web 技能每次任务都实际执行 `tiana web list-template --json`，使用当前 name/description 判断需求。模板 ZIP 原样下载解压到独立项目目录；Agent 按根部 metadata.json 替换变量、先 schema 后 seeds。模板源码和制作规范见 [template-apps](https://github.com/tianacloud/template-apps)，客户安装模板由 CLI 和 MGR 目录完成。

技能安装器只安装技能。Agent 首次执行 Tiana 任务时检查 CLI，缺少时自动执行下面的安装并继续原任务；CLI 要求 1.0.0 或更新正式版，需要 Node.js 20+。

```sh
npm install -g @tianacloud/cli@latest --registry=https://registry.npmjs.org/
```

CLI 主包及当前系统的原生平台包全部来自 npm，提供 tiana 和 git-remote-tiana。保持 optional dependencies 启用；`--ignore-scripts` 也可安装。

## 环境选择

普通用户可以直接要求：“执行 `npx -y @tianacloud/agent-skills@latest install` 安装 Tiana skills，然后使用 tiana 创建一个账单应用。”未配置环境时，CLI 使用 online 公有域名与系统 CA；首次登录按 Agent 提供的浏览器链接授权。

开发者也可以向已运行的 Agent 要求：“设置 `TIANA_API_ORIGIN=https://console.tianacloud-staging.net`，安装 Tiana skills，然后创建一个账单应用。”技能会在本任务每次 CLI/Git 调用中传递这一选择。staging CLI 自动加载内置 CA；开发者需已有 VPN/DNS 和浏览器 CA 信任。仅在安装器子进程中 export 一次不会配置后续命令。

WorkBuddy Connector 固定 online，配置和当前使用说明见 [Connector](docs/workbuddy-connector.md)。

## 检查与更新

四个技能调用 CLI 检查 npm latest，CLI 普通终端调用也使用同一本地状态。两个包各自最多每 24 小时尝试检查一次，CLI 与 Skills 共用每 24 小时一次提醒。已满足最低 CLI 版本时，断网不阻断任务；升级需要用户确认。

确认升级后重新安装检查返回的实际版本，并核验 `tiana version`、技能 metadata.version 和宿主重载结果。已加载的会话不会因磁盘替换而自动更换指令。详情见 [开始使用](skills/tiana/references/getting-started.md)。

## 维护与其他分发格式

skills/ 是所有格式的规范源。Pi 可使用 `pi install npm:@tianacloud/agent-skills`，支持 Agent Plugins v1 的客户端也可发现 plugin.json。构建、版本对齐、GitHub Actions 自动发布及 npm 初始配置见 [Contributing](CONTRIBUTING.md)。

MIT
