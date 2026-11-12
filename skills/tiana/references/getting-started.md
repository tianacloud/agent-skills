# 开始使用

在 Agent 实际执行命令的环境检查 `tiana version`。本技能要求 CLI 1.0.17 或更新正式版，具备分步登录、sqlite、git、web、file、list-template/init-template 和 version check。CLI 不存在或版本低于基线时，自动执行下面的 npm latest 安装并重新核验；版本无法核实时先排查实际错误，核验通过后再执行资源操作。

连接器环境中，安装或更新前先按[宿主说明](connector-updates.md)定位实际 Node/npm、CLI 安装 prefix 和技能根目录，沿用宿主运行环境。

最低版本是可用性基线；通过后仍须检查新正式版，升级前取得用户同意。0.x、预发行版、dev 或无法核实的版本不满足基线。CLI 与 Skills 独立编号，`--skills-version` 传实际加载的 Skills 版本。

## 安装

CLI 主包和适合当前系统的原生平台包都由 npm registry 提供。需要 Node.js 20+，使用 Tiana Git 还需要原生 Git。安装不运行下载二进制的 postinstall：

```sh
npm install -g @tianacloud/cli@latest --registry=https://registry.npmjs.org/
```

该包提供 `tiana` 和 `git-remote-tiana`，npm optionalDependencies 选择当前平台原生包；保持 optional 依赖启用，`--ignore-scripts` 也可以正常安装。缺少平台包时按实际错误修复安装，不能只凭命令入口存在宣称成功。Windows PowerShell 使用 `npm.cmd`，详情见 [Windows 安装](windows-install.md)和 [Git helper 排查](windows-git-helper.md)。

安装 Skills 使用 Node.js 22.20+；CLIENT 取实际受支持的客户端标识：

```sh
npx --yes @tianacloud/agent-skills@latest install --agent CLIENT
```

其他客户端按自己的安装目录使用 `install --dir PATH`，或不传目标运行客户端选择流程。Skills 来自 npm 包内全部技能目录，安装后是持久文件副本。导入 Skill 与安装 CLI 是两步。

核验安装后，先完成入口 SKILL.md 中的会话更新检查，再执行 `tiana status`，按实际结果继续任务或恢复登录。用户同时要求创建应用时，完成安装和登录后继续原始需求。当前会话可以读取新安装的 SKILL.md 及其引用文件；宿主必须重载才可使用时，明确提示重载，并保留应用需求及本次环境选择。安装失败时报告实际阶段；没有执行过的登录、资源创建或发布仍然未知。

## 更新

CLI 与 Skills 独立编号，分别与自身 npm latest 比较。版本检查和 npm 安装访问公共包仓库，不要求 Tiana 登录，也不查询或修改 Tiana 云端资源；“暂不登录／不操作云端资源”不影响这一步。用户明确要求离线、禁止联网或禁止安装时遵从其限制。

会话检查顺序和记录规则见入口 [SKILL.md](../SKILL.md#每个会话一次的更新检查)。最低版本核验通过后，从本会话实际加载的 SKILL.md 的 metadata.version 读取 SKILLS_VERSION，在同一次 shell 调用中赋值后执行 `tiana version check --skills-version "$SKILLS_VERSION" --json`。结果是直接 JSON，包含 should_notify、check_status 和 updates。逐项识别 package 为 `@tianacloud/cli` 或 `@tianacloud/agent-skills` 的新正式版。should_notify=true 时展示包名、当前版本和 latest_version，询问用户是否升级；Skills 升级会覆盖已有技能并补齐新增技能，询问时说明这一影响。仅在用户同意后安装其选择的包和版本。should_notify=false 时保留检查记录，不主动发起升级；用户主动要求升级时可展示已返回的目标版本并按其授权操作。check_status=cached 表示缓存结果，仍遵循相同确认流程。用户拒绝或尚未回复时保留当前版本，可继续不依赖升级的原任务。

保留本会话实际检查结果、执行错误及两个包的安装与核验结果；每个获准升级的包最多尝试安装一次。首次检查和更新结束后，在对话中简短报告实际 CLI/Skills 版本、检查状态与各包结果、新增技能及重载要求。检查不可用时说明未能确认是否有新版；后续复用本会话记录时无需重复报告。

### 用户确认后更新 CLI

```sh
npm install -g @tianacloud/cli@VERSION --registry=https://registry.npmjs.org/
```

VERSION 取 CLI 更新项的 latest_version。Windows PowerShell 使用 `npm.cmd`。升级使用 Agent 实际调用的 CLI 所属 Node/npm 和安装 prefix；保留宿主注入的运行环境。连接器的实际安装位置与运行环境按[连接器与宿主中的更新](connector-updates.md)核验。

安装后核验实际 `tiana version` 与目标版本一致，以及本任务所需命令的 `--help`。npm 安装成功但仍运行旧版本时，按 [PATH 与 helper 排查](windows-git-helper.md)核对命令位置，完成前报告为尚未生效。

### 用户确认后更新 Skills 与新增技能

VERSION 取 Skills 更新项的 latest_version。原来通过受支持客户端安装的，使用同一 CLIENT：

```sh
npx --yes @tianacloud/agent-skills@VERSION install --agent CLIENT
```

目录安装或连接器内置技能使用已核实的实际技能根目录（其中直接包含各技能目录），安装整个新版包：

```sh
npx --yes @tianacloud/agent-skills@VERSION install --dir "SKILLS_DIR"
```

Windows PowerShell 使用 `npx.cmd`。从当前加载的 SKILL.md 实际路径确认安装目标；重用原安装方式，各连接器均按[宿主说明](connector-updates.md)操作。安装器枚举新版包 skills/ 下的全部技能目录，覆盖对应已安装目录并安装新增目录，保留其他技能。

检查安装器返回的版本、技能名单及目录，逐份核验已安装 SKILL.md 的 metadata.version 与目标一致；名单以新版包为准。读取本任务所需的新 SKILL.md 和引用，按新指令继续；需要宿主重载才能启用时提示重载或开始新会话，保留原任务、环境选择和检查记录。文件安装成功与宿主加载成功分别报告，新增技能需确认出现在宿主技能列表并可加载后才算启用。

### 失败后继续

检查不可用且没有可用更新项时，或安装失败时，保留并简短报告实际错误，分别记录两个包的结果。核实 CLI 仍满足基线且具备所需命令、所需技能可加载后，可继续原任务；否则报告具体阻塞。部分安装失败时按安装器返回的已完成/未安装名单核对现状。安装缺失 CLI 或提升过低版本失败后，同样须核验通过才能继续资源操作。

### npm 仓库连接失败

访问 `https://registry.npmjs.org/` 超时、连接重置、返回代理拦截页或证书错误时，向用户说明 npm 仓库不可达，可能与企业代理、防火墙或证书配置有关。保留实际错误，可在同一宿主运行环境执行 `npm ping --registry=https://registry.npmjs.org/` 验证连通性（Windows 使用 `npm.cmd`），核对宿主的代理及 npm proxy/https-proxy 配置；请用户或网络管理员确认放行该域名，按企业要求配置代理和受信任 CA。展示排障结果时隐藏代理凭据。保持证书验证，不自动改用其他 registry。

连接器初始化尚未完成时，修复网络后重新执行初始化；更新检查或安装失败时按上面的继续条件判断。不要把 npm 网络错误当作 Tiana 登录失败，也不要报告升级成功。

## 环境与地址

未设置 `TIANA_API_ORIGIN` 时，CLI 默认连接 online：`https://console.tianacloud.com`，使用系统公有 CA。外围启动器已设置变量时继承其选择。

用户在当前任务明确指定 origin（包括把 `export TIANA_API_ORIGIN=...` 写在请求中）时，将该值传入本任务后续每次 CLI、原生 Git 和相关子进程调用。优先使用执行器的环境参数；执行器只有 shell 时，在同一次调用中设置变量并执行命令。每次工具调用都可能启动新进程，安装时执行一次 export 不会影响后续调用。任务恢复时继续使用用户已选 origin；没有用户的新选择时不要自行切换。环境选择只属于当前任务，不写入技能目录、应用源码或用户启动文件。

后续 `git push` 也在其所在的工具调用中设置相同变量，让 `git-remote-tiana` 继承。PowerShell 使用 `$env:TIANA_API_ORIGIN`，同样需在每次独立调用中传递。

Console/管理 API、用户 Web 地址、数据库 Endpoint 各有用途：全部取实际 CLI/服务回执，不猜域名或把管理地址作为数据库连接地址。应用地址使用回执中的 application_url，Git URL 使用用户 Git 实例的 Endpoint。

## 对话中的登录

1. 执行 `tiana login --start --no-open --json`。
2. 向用户展示 data.verification_uri，等待用户打开并批准。status=pending、退出码 3 表示等待授权。
3. 用户授权后 `tiana login --resume --json`；只有 status=succeeded 且 data.logged_in=true 才继续。仍等待时保留同一链接和 data.retry_after，不连续 start。
4. 链接失效后再 start。CLI 保存账号会话，不需要读取凭据文件。

普通终端也可执行 `tiana login`。用量接口失败不代表退出登录；命令与恢复见 [CLI 指引](cloud-cli.md)。


配套修复后的 CLI 在缺少 pending 时返回 `NO_PENDING_AUTH`、`pending_auth:false`，不据此否定当前登录；用 `tiana status --json` 单独核实。`logged_in` 仅在本次已确认登录成功时为 true，其他登录结果可能省略；省略 `pending_auth` 表示无法确认 pending 是否仍在，保存/网络失败后不能假定授权已丢失。按错误 code/message/next_action 处理目录、锁、过期或拒绝，不机械重复 start。先通过 `--help` 核实当前安装版本的新 JSON 能力。
