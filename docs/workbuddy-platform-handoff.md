# WorkBuddy 平台测试入口交接

状态：0.2.0 npm 版新 Logo 配置包已由用户上传，连接器 ID 为 `oc_5878fe73dc7a3123`，用户回传「审核中」；CLI npm 包已公开发布并通过双平台 registry 安装检查，真实 WorkBuddy 验收未完成。

## 当前平台记录

2026-09-11 用户回传个人账号 ID `oc_5878fe73dc7a3123`，状态为「审核中」。后续测试入口、审核沟通和发布跟踪使用此 ID。
下文企业账号 `oc_19e12297ca82254a` 仅代表开发者执行的配置预检，该记录未由开发者提交审核。
个人账号状态来自用户回传，尚未通过该账号页面独立核验；当前没有撤回或修改审核的授权。

当前候选配置已改为 npm registry 安装固定版本 `@tianacloud/cli@0.2.0`，该版本已公开发布。
2026-09-11 用户确认已上传下述 npm 版新 Logo ZIP，沿用原连接器 ID，状态为「审核中」。
审核中不代表可安装或可验收；后续需确认审核结果及客户端安装入口。

## U-02：请用户确认平台归属与测试通道

本节点只需操作 WorkBuddy 开放平台或与平台团队确认，不需要在 Mac 安装工具、导入证书或执行 CLI。

材料位置（开发工作区）：

- [Connector ZIP](../dist/workbuddy-npm/tiana-cloud-0.2.0.zip)
- [SHA-256](../dist/workbuddy-npm/tiana-cloud-0.2.0.zip.sha256)
- [CLI 配置](../packaging/workbuddy/tiana-cloud/cli.json)
- [连接器元信息](../packaging/workbuddy/tiana-cloud/connector-meta.json)

包中包含根目录 connector-meta.json、cli.json、icon.png，和 skills/tiana、skills/tiana-sqlite。
图标使用用户提供的 tiana_icon_64x64.png 原图。
两份 Skill 正文和 references 来自 canonical 源；打包时注入 WorkBuddy 所需的本地化 frontmatter。
CLI 原生程序不在 ZIP 内；init 通过 npm registry 安装已发布的 `@tianacloud/cli@0.2.0`。
换用用户 Logo 的新 ZIP 已放在 Mac `/Users/jason/tmp/tiana-cloud-0.2.0-npm.zip`，由用户自行上传。
SHA-256 为 `856748041f8b8932e029a195c4f215517cf31d7dbc994a171d8203dddcf2613c`。
此前构建临时目录中的 ZIP 保留；上传时使用上面的新路径。
当前 ZIP 的 CLI 下载前提已就绪；平台入口、真实安装/授权调度及聊天验收仍待完成。

### 操作步骤

1. 打开 [WorkBuddy 开放平台](https://open.workbuddy.cn/)，用你要发布/测试连接器的账号登录。
   若平台要求入驻，按账号页面流程确认主体；不要把账号密码或 Cookie 发给开发者。
2. 确认 `source=tiana-cloud` 是否可由该账号/团队使用，以及如何让你的 WorkBuddy 5.5.4 账号看到测试连接器。
3. 在平台提供的开发测试入口或团队沟通渠道询问以下问题；需要配置材料时提供上面的候选 ZIP，
   同时说明 CLI npm 包已发布，但客户端与目标服务整体验收尚未完成。

可直接转发：

> 我们正在接入 Tiana Cloud，使用 CLI + Skill，source=tiana-cloud，目标版本 0.2.0。
> 首个测试客户端是 macOS arm64、WorkBuddy 5.5.4。
> 请确认该 source 的归属/占用情况，以及指定账号可用的开发测试发布通道、进入位置和操作步骤。
> CLI 使用托管 Node 20；auth 输出浏览器 URL 后继续轮询并保存凭据，配置 authWaitForExit=true。
> 请确认测试通道可验证超过 10 秒的 auth 进程等待、init 从 npm registry 安装固定版本，
> 以及安装后的命令在新聊天执行环境中可见。
> 附件是 npm 配置候选包；CLI 已公开发布并通过双平台安装检查，需要继续验证客户端安装和聊天调用。

### 预期结果与需回传的信息

- source 的归属或占用结论，以及测试账号/团队是否已开通对应权限。
- 实际测试入口的 URL、页面路径或截图，如何提交测试版本、如何使客户端账号可见。
- 平台要求的附加材料，以及对上述 auth/npm 安装/聊天 PATH 测试方式的说明。
- 如没有自助测试入口，请回传平台团队给出的接入方式；不要自行假定有“本地导入 Connector ZIP”按钮。

官方文档说明连接器目录需提交 WorkBuddy 团队审核，审核后进入连接器市场；它没有给出适用于
本账号的开发测试入口。上述字段依据 [Connector 文档](https://open.workbuddy.cn/docs/connector)
核对（2026-09-11）；本地化字段依据 [Skill 规范](https://open.workbuddy.cn/docs/skill)。
实际调度仍以该客户端实测为准。

## 2026-09-11 账号页面检查

用户授权操作 Safari 并开启 Apple Events JavaScript 后，已读取实际登录页面：

- 当前主体为「北京千帆阅文科技有限公司」，角色为企业超管。
- [连接器列表](https://open.workbuddy.cn/connector/all) 显示「暂未发布」。这不能证明 `source=tiana-cloud` 全局未占用。
- [创建页面](https://open.workbuddy.cn/connector/publish) 为「配置连接器 → 确认信息 → 提交审核」，支持不超过 20 MB 的 ZIP。
- 用户确认使用当前主体做配置预检后，已上传 `tiana-cloud-0.2.0.zip`（13.7 KB），
  SHA-256 为 `4eb3bd6444315df68f7b0fef285de6edaa769166642f528e29b31b9feb6a2a16`。
  平台解析成功，生成连接器 ID `oc_19e12297ca82254a`。
- [确认信息页](https://open.workbuddy.cn/connector/publish?step=2) 正确显示 Tiana Cloud、0.2.0、图标、中文介绍和三个聊天示例。
  类目选择「商业服务 → 软件/建站/技术开发」。
- 已进入[最终确认页](https://open.workbuddy.cn/connector/publish?step=3)，没有点击「提交」；未进入审核、发布或上架。
  该 URL 是流程入口，不保证其他会话能恢复这次上传，平台未显示独立草稿保存入口。
- 已检查的列表、三步创建流程和首页未显示独立开发测试入口；不据此断言平台没有测试能力。
- [平台上架 Q&A](https://open.workbuddy.cn/dashboard/contents/ann_1788334307262_r0ny30?source=announcement)
  （2026-09-02）说明审核通过进入待发布，连接器发布后仍需运营协助上架。
  文中提及可接入 WorkBuddy 使用调试，但未给出该账号的具体入口；支持渠道为首页开发者群聊。

预检证明该主体能上传并解析候选包，但页面只显示平台连接器 ID，没有显示 `source=tiana-cloud` 的归属或占用结论。
客户端测试可见性仍未确认，U-02 的配置预检部分完成，测试通道部分未完成。

下一步请通过首页开发者群聊向平台团队提供连接器 ID，并询问：

> 我们已在个人账号提交 Tiana Cloud 0.2.0 候选包，连接器 ID 为 oc_5878fe73dc7a3123，当前审核中，
> 包内 source=tiana-cloud；CLI 下载仍在准备。
> 创建流程只有上传、确认、提交审核，没有测试发布入口。
> 请确认该 source 的归属，以及如何让同一账号的 macOS WorkBuddy 5.5.4 在审核前安装并调试此连接器。
> 请同时说明审核中的候选包如何更新；目前先确认测试接入步骤，不请求直接市场上架。

## U-03/U-04 前置材料状态

原生构建脚本与工具链说明已在 CLI 仓库 [packaging/README.md](../../cli/packaging/README.md)；
Linux 成套开发测试包已验证离线 helper 握手与 SQL executor 版本。
Mac arm64 原生组件构建已通过；完整安装包的隔离属性和系统凭据库测试尚未完成。darwin-amd64 已由用户确认延期，留 TODO。
用户已额外授权在 Mac 的 Safari 操作开放平台，并已开启 Allow JavaScript from Apple Events，页面自动化可用。
用户随后授权在独立临时目录准备 Go/Rust/Node、执行 arm64 构建与离线测试；系统级安装、证书、登录项和 WorkBuddy 配置不变。
Mac 构建目录为 `/tmp/tiana-connector-build.GDaVX8`，arm64 原生组件编译与 Go/Rust/打包/认证子进程离线测试通过。
用户需要个人账号上传的候选 Connector ZIP 也已放在该目录，并已核对 SHA-256。

源码材料、还原校验和构建命令见 [macOS 构建交接](workbuddy-macos-build-handoff.md)。
本轮 helper 使用已记录的 contract 3 开发快照；SQL SDK 固定 dev.5 依赖从已校验的本地 Git bundle 取源，未改锁文件或全局 Git 配置。
目标 Gateway 端口已核实为 9443，公开根 CA 已从 Vault 定位、验证 TLS 链并随包交付。
完整两平台 tarball 已公开发布到 npm；构建、测试、离线安装和 registry 真实下载安装检查均通过。
用户允许本次候选包使用 helper 固定提交 `c681e209a9151eee8dc3a0b9ed0277145617ac82`，版本清单记录提交与摘要；SQL SDK 仍固定 dev.5。
用户确认 wulanchabu 当前正在测试 branch，本任务暂不向该环境发布，集成基线与部署窗口等用户通知。

实际安装前仍需确认测试 Connector 可见性、更新平台旧候选配置，并验证 Console 的浏览器登录。
届时再指导“安装/连接 → 浏览器授权 → 新聊天调用”全过程；当前候选 ZIP 的存在不替代这些前提。

## 当前自动化证据的边界

- validate:ci 校验版本、canonical 引用、单 Skill 包、Connector 布局/配置/副本一致性和 SHA-256。
- 8 个 SQL 文档示例在内存 SQLite 实际执行，验证类型化输入、schema、DDL/CRUD 与 int64 精度。
- 真实 Linux CLI 子进程连接本地测试认证服务：10 秒内输出 URL、延迟超过 10 秒批准、保存后跨进程
  status 无网络和文件改动、logout 和取消登录；测试使用独立临时凭据，不打开浏览器。
- 这些都不证明 WorkBuddy 的托管 runtime、实际浏览器、Mac Keychain 或生产 Gateway 已经通过。

真实 WB-01..WB-18 继续记录在 [验收记录](workbuddy-cli-acceptance.md)。
