# Tiana Agent Skills

五个基础技能覆盖 Tiana 账号与实例、SQLite、Git、后端服务、密钥和 Web 应用。应用模板由在线目录提供，用户描述需求后，Agent 根据实时目录决定使用模板还是直接开发。

## 从 npm 安装

需要 Node.js 22.20+：

```sh
npx --yes @tianacloud/agent-skills@latest install
```

安装器调用精确依赖的 skills 工具，把 npm 包中的全部技能复制到所选客户端的持久目录。

目录导入型客户端可指定实际技能根目录：

```sh
npx --yes @tianacloud/agent-skills@latest install --dir /path/to/client/skills
```

Windows PowerShell 使用 `npx.cmd`。目录可以含空格，用引号包住。重复安装会更新包内全部技能并补齐新版新增技能，其他技能保留。安装完成后让客户端重载技能或开始新会话。

目录／ZIP 导入型宿主加载这五个目录，保留 SKILL.md 和 references。若要求独立技能 ZIP，将每个技能目录的内容打包，SKILL.md 位于包根部。归档检查验证格式和内容；宿主运行行为须在实际客户端验收。

## 五个入口

| 技能 | 职责 |
| --- | --- |
| [tiana](skills/tiana/SKILL.md) | CLI 安装、登录、账号额度和通用实例管理 |
| [tiana-sqlite](skills/tiana-sqlite/SKILL.md) | SQL、表结构、SDK 连接和数据库分支 |
| [tiana-git](skills/tiana-git/SKILL.md) | Git 实例、原生仓库操作和源码版本同步 |
| [tiana-function](skills/tiana-function/SKILL.md) | Go 后端服务源码、构建发布、参数/CORS、数据库后端与用户密钥管理 |
| [tiana-web](skills/tiana-web/SKILL.md) | 实时模板选择、工程与数据初始化、通用开发、构建发布 |

Web 技能每次任务都实际执行 `tiana web list-template --json`，使用当前 name/description 判断需求。模板 ZIP 原样下载解压到独立项目目录；Agent 按根部 metadata.json 替换变量、先 schema 后 seeds。应用模板由所属空间内的来源 Web 应用打包并发布到在线目录（见 [tiana-web](skills/tiana-web/SKILL.md)），客户安装模板由 CLI 和 MGR 目录完成。

技能安装器只安装技能。Agent 首次执行 Tiana 任务时检查 CLI，缺少时自动执行下面的安装并继续原任务；CLI 要求 1.0.17 或更新正式版，需要 Node.js 20+。

```sh
npm install -g @tianacloud/cli@latest --registry=https://registry.npmjs.org/
```

CLI 主包及当前系统的原生平台包全部来自 npm，提供 tiana 和 git-remote-tiana。保持 optional dependencies 启用；`--ignore-scripts` 也可安装。

## 环境选择

普通用户可以直接要求：“执行 `npx -y @tianacloud/agent-skills@latest install` 安装 Tiana skills，然后使用 tiana 创建一个账单应用。”未配置环境时，CLI 使用 online 公有域名与系统 CA；首次登录按 Agent 提供的浏览器链接授权。

连接器已提供运行环境时，沿用其 API origin、CLI 入口与安装位置。

## 检查与更新

各 Tiana 技能调用 CLI 检查两个 npm 包的 latest。两个包各自最多每 24 小时尝试检查一次，CLI 普通终端与 Skills 共用每 24 小时一次提醒。Agent 发现 CLI 或 Skills 新正式版且 should_notify=true 时展示版本并询问用户，仅在用户同意后安装并核验；用户拒绝或尚未回复时保留当前版本。CLI 缺失或低于 1.0.17 时可自动安装并核验基线。每个会话首次检查后简短报告检查、两个包的更新结果及新增技能。

CLI 在当前实际使用的安装位置升级并核验版本和所需命令；Skills 安装新版包中的全部技能，覆盖已有技能并补齐新增技能，核验 metadata.version 与宿主加载结果。实质性技能变更发布到 npm 时，同步向接入平台告知 Skills 与 Connector 版本号并提交对应连接器包审核。已加载的会话不会因磁盘替换而自动更换指令；需要重载时明确提示。具体步骤及失败后的继续条件见 [开始使用](skills/tiana/references/getting-started.md#更新)，各宿主安装位置及加载核验见[连接器与宿主中的更新](skills/tiana/references/connector-updates.md)。

## 维护与其他分发格式

skills/ 是所有格式的规范源。支持 Agent Plugins v1 的宿主可发现 plugin.json；其他宿主沿用其包管理或目录导入方式。构建、版本对齐、GitHub Actions 自动发布及 npm 初始配置见 [Contributing](CONTRIBUTING.md)。

Apache-2.0
