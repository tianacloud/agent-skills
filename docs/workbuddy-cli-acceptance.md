# Tiana CLI + Skill / WorkBuddy 验收记录

状态：CLI npm 0.2.0 已发布，Connector npm 版新 Logo ZIP 已由用户提交审核；真实 WorkBuddy 验收未完成。2026-09-12 下午用户通知乌兰察布被其他需求占用，当前暂停共享环境访问、部署及真实验收；下文部署结果为此前记录，不代表当前环境状态。
实施依据：[已确认方案](workbuddy-connector-mcp.md)。

## 2026-09-12 下午：主分支同步与本地前置验证

7 个有 main 的仓库已 rebase；agent-skills 远端仍无分支。完整 SHA、备份和 8 项冲突处理见 [本轮同步报告](../../REBASE-2026-09-12-AFTERNOON.md)。原主工作区未改动。

CLI main 已改为本地文件凭据，本任务沿用该行为，并将账号索引、任务 journal 与凭据目录对齐；保留终端名称/引擎检查及聊天、终端共用的异步恢复流程。已发布 npm 0.2.0 和审核 ZIP 未变，新源码尚未在 Mac 验证，也没有迁移旧 Keychain 或旧目录记录。此项整合不能记为 WorkBuddy 原错误已修复。

CLI、MGR、Gaia、contracts 的 Go test/race/vet 通过；Web 的 Go test/race/vet、构建与 35 项本地浏览器测试通过；Node 打包/发布 fixture 测试 20 项、Rust SQL executor 测试 14 项及 clippy 通过。Control 普通 test/vet 通过，race 再现 main 的 Ergo ProcessPID/spawn 竞争，未修改 Control。

同步后的完整 Linux CLI 本地构建及 verify-install 通过：linux/amd64、embedded helper contract 3、SQL executor 0.2.0。制品位于 `/tmp/tiana-connector-rebase-20260912-afternoon.0z26IF/linux-final/`，仅用于本地验证，未发布。Mac/WorkBuddy 和真实 Gateway SQL 仍待环境窗口恢复后验收。

同一最终 CLI 制品通过 `TestAuthTransactionCLIHeadlessMySQL`（exit 0，265.77 秒）：使用实际 Web 进程、MGR 生产路由及本任务独立 MySQL，覆盖登录、身份投影、创建编排、凭据保存、resume、退出/刷新失效和再次批准。Control 为测试替身，浏览器流程使用 HTTP 客户端；随机测试库已清理，不涉及共享库。命令及制品摘要见上述同步报告，日志为 `/tmp/tiana-connector-rebase-20260912-afternoon.0z26IF/local-integration.log`。这不标记任何 WorkBuddy 或真实 Gateway SQL 场景通过。

## 2026-09-12：WorkBuddy 基础检查与创建阻塞

用户转述 WorkBuddy 执行总结：CLI 0.2.0、已登录、可列出实例；创建 wb-demo 持续返回 `CREDENTIAL_SAVE_FAILED`。随后已回传错误 JSON：`status=failed`、`data=null`、message 为 `Unable to access the local Tiana credential store`。尚未取得原始命令、退出码、任务 ID 或技能加载截图，因此仅记为用户报告的基础调用成功，不标记 WB-01/WB-05 通过。

已请用户停止重复创建，使用 CLI 的只读任务接口回传原请求状态；未读取凭据文件或输出 Token。代码中该错误码覆盖任务/索引持久化及 Token 保存多个阶段，不能据此推断实例尚未创建。
执行者从 SSH 会话只读运行相同临时 npm CLI 的 `requests list --json`，结果为 `AUTH_REQUIRED`、exit 5；该会话不能代表 WorkBuddy 已登录的进程环境。未发起重新登录、创建、恢复、签发或退出操作。
该次 `data=null` 输出对应提交前的身份读取、任务加锁或初始 journal 保存阶段；不能据此排除更早尝试已创建实例。下一步需要原 WorkBuddy 聊天的 `requests list/get` 输出，先定位具体失败点，再决定修复及原任务恢复方式；目前随共享环境窗口暂停。

## 2026-09-12：用户终端授权与实例读取成功

证据来源：用户在本线程回传 Mac 终端执行结果，不是 WorkBuddy 聊天或执行者独立复测。

- 浏览器授权后，`auth status --json` 返回 `status=succeeded`、`logged_in=true`、`reauth_required=false`，包含 Principal、Tenant 和 access/refresh 到期时间，未包含 Token 原值。
- `instances list --json` 返回 `status=succeeded`、page=1、page_size=20、total=6、total_pages=1；5 个实例为 ACTIVE、1 个为 DELETED。列表中的休眠状态不证明 Gateway 唤醒或 SQL 已通过。
- 授权过程中用户曾在点击登录／继续授权后看到 `csrf_failed`，随后报告授权成功。期间没有为该问题修改代码；失败原因未确认，未记为已修复。

本轮确认终端登录和真实管理读取可用。WB-18 仅获得登录/列表部分证据，终端 SQL 仍未验证；WB-01..WB-17 的 WorkBuddy 场景未通过本次结果得到验证。
实际凭据后端、Console 身份对照、重新授权/取消及刷新恢复仍需对应场景证据，不从上述成功输出推断。
下一步按安装手册的「审核前：WorkBuddy 复用终端登录」执行聊天只读检查；通过后再创建专用验收实例，不改动列表中的已有业务实例。

## 2026-09-12：MGR v0.27.0 发布与目标部署

用户明确授权发布 MGR Connector 增量并通过 Gaia 部署到 wulanchabu，随后确认本次无不兼容变更则不做整库备份。
部署前只读检查现网库 `tiana_mgr_branch_acceptance_20260911`：001..013 的名称、SHA-256 与 v0.27.0 内嵌迁移逐项一致，无新增迁移；没有创建数据库备份。

| 项目 | 实际证据 |
| --- | --- |
| MGR 源码 | 3748e2f6b431ed68e98d8b659ca7a3cad5185027；feat/workbuddy-connector 和 v0.27.0 已推送，main 未更新 |
| 正式镜像 | images.service.internal.tiana.com/tiana/mgr@sha256:943d1b087949f8d081a3c4692439e6219ea1f62f92b765e3561b70579d7b75c8 |
| Gaia Operation | 3e9b16b7-27ea-4e5d-877b-ec765f237f05，SUCCEEDED / commit_snapshot |
| 已部署快照 | f8af8487-11af-416b-84eb-abf30695ead8；current_matches_deployed=true，IN_SYNC |
| Kubernetes | tiana/tiana-mgr；generation=observedGeneration=48；updatedReplicas=readyReplicas=replicas=2；实际镜像与上述 digest 一致 |
| HTTP | Console /api/v1/device 返回 200；未认证 /api/v1/auth/transactions/whoami、/api/v1/me、/api/v1/app-types 返回 401 |
| Schema | latest=13；manifest sha256:746b4cd07f5020f2b364fb9ee485b532593b1ceac93f5f9a1f66c452099cdfa3 |

本次仅变更 MGR current image_ref。Gateway 保持 image 4a1320c3adf010de852dcd1153c7710e2a213ff2bb98ddef971cfc5a2ed467b6、snapshot 4694def3-2506-4451-ad4b-5546da2a8ec8；Control control0 保持 image 22ddab87c0c3e6ff88376e323bab284fbd5f6ffb67e5b1a1f59f11587f36db5b、snapshot 59c0ce6f-5caa-4504-820b-11d26e47cdb7，复核均 IN_SYNC。
旧 MGR image 8e47daf0b5dc789355715857922936510c8d7967c81a80bf26e754202c7b5267 与 snapshot 8f519e1d-3ffd-4607-b70d-ecbd59d6da24 保留。部署记录在 /tmp/tiana-connector-mgr-rollout-20260912.YiG46j/，包含私有配置，不复制到聊天或 Git。

Gaia 本地提交 67ab161 固定已发布 MGR v0.27.0，test/race/vet 和完整构建通过；没有更新运行中 Gaia 的镜像。其 schema 入口与新 MGR 的既有 013 清单一致。
部署使用现有 integration 环境与认证配置，没有切换模式或发起用户登录；健康检查不代表正常浏览器授权、真实创建或 SQL 已通过。下一步按安装手册执行用户终端登录和只读列表，以及 WorkBuddy 聊天调用/正式 Connector 验收。

## 2026-09-12：主分支同步后的客户端预检准备

### MGR 本地候选构建

当前 c99ecdd + Connector 未提交增量已完成本地 Linux 服务/管理工具构建与 Docker 入口 smoke；没有推送或部署。
目录 `/tmp/tiana-connector-mgr-candidate-20260912.6RNcAk/` 中的 README.md 记录构建参数、源码 diff 和制品摘要。
本地镜像 `tiana-connector-mgr:preflight-20260912-6rncak`，image ID `sha256:4506a01a34b30a5b9e9c05d5941abcff6c91322eed4a6b9254682945c36ebc25`，不是 registry manifest digest。
入口按现有脚本在缺少配置时启动并退出，证明可执行，不代表配置完整的服务已健康运行。
实际嵌入 schema latest=13，manifest `sha256:746b4cd07f5020f2b364fb9ee485b532593b1ceac93f5f9a1f66c452099cdfa3`。
相对 main，迁移、schema.go、go.mod、go.sum 和 Dockerfile 均未改变；本候选仍是开发构建，正式版本、Gaia 固定依赖和共享部署待确认。

独立 MySQL 的正常升级与中断恢复测试已通过，命令在 MGR 仓库执行：

```sh
GOWORK=off GOMAXPROCS=2 \
TIANA_TEST_MYSQL_DSN='root@tcp(127.0.0.1:32820)/mysql?parseTime=true' \
go test -p 2 ./internal/adapters/mysql \
  -run '^(TestAuthTransactionMySQLMigrationFrom012|TestEmbeddedSchemaCompatibilityProfile)$' \
  -count=1 -v -timeout=10m
```

结果：exit 0；exact-012 254.92 秒、interrupted-013 258.35 秒，父测试 513.27 秒。
覆盖 schema 012 正常升级到 013，以及 013 第一张表已创建、迁移账本尚未提交的恢复；两者均执行迁移后校验和列定义损坏检测。
测试使用本任务容器 tiana-connector-oauth-mysql 的独立随机测试库，结束时清理这些测试库；没有迁移共享数据库，不代表生产环境升级已执行。
测试进程已结束。agent-skills 的 validate:ci 与 diff --check 通过；本轮没有修改服务生产代码。

### 用户 Mac 终端结果

用户回传 Mac 预检成功，并确认执行入口为 Mac 终端，原始非秘密输出如下：

```json
{"status":"succeeded","data":{"arch":"arm64","helper_contract":3,"helper_mode":"embedded","platform":"darwin","sql_executor_version":"0.2.0","version":"0.2.0"},"error":null}
```

这份结果确认用户侧版本与内置程序检查通过；不代表 Connector 自动安装、浏览器授权或云端 SQL 已通过。

一键发布脚本补充了首次实际发布中遇到的 npm 索引延迟处理：仅在 publish 成功后，遇 E404 时每五秒检查，最长五分钟。
索引出现后核对原 tarball SRI，再执行原有 registry 安装检查；其他错误及摘要不符立即停止验证。
Linux Node 打包/发布测试 20 项通过，Mac 临时目录 /tmp/tiana-connector-build.GDaVX8/release-check.TnzdNj 的发布模块测试 8 项通过。
真实只读 npm 查询验证 0.2.0 SRI 一致，另用不存在的版本验证 npm E404 JSON 会进入等待；检查随即停止，没有发布动作。
本轮未重跑完整原生构建或真实 publish，npm tarball 与已上传 Connector ZIP 摘要保持不变。

各工作区主分支同步结果见 [rebase 记录](../../REBASE-2026-09-12.md)。
CLI/MGR/Web 的未提交增量完整恢复；Control 主分支现有 Ergo race 已单独记录，未由本任务修复。

npm registry 再次读回 @tianacloud/cli@0.2.0 与原发布 SRI 一致。
Mac 原有 registry 安装目录仍可用；通过 SSH 设置仅本次命令的 PATH 后，verify-install --json 再次返回 succeeded、darwin/arm64、helper contract 3、executor 0.2.0。
这仍不是 WorkBuddy 聊天执行证据。

两份 canonical Skill 及管理参考文档仅修正“CLI 未发布”的过期说明，未改变命令或凭据行为。
npm validate:ci 和两份 Skill 的 quick_validate 均通过；独立 Skill ZIP 已复制到 Mac，双端摘要一致：

| 文件（Mac /Users/jason/tmp/tiana-workbuddy-precheck-0.2.0/） | SHA-256 |
| --- | --- |
| tiana-0.2.0.zip | 312595df926411af52d8317d23f0105034888603fe964975be91319fb694daf0 |
| tiana-sqlite-0.2.0.zip | 0c30d6e79a72dec24545a3c9d9d8f1cd58be9e265f10bffa40650c3d14e607ad |

Linux 文件在 dist/workbuddy-precheck-20260912/；Mac 同目录 INSTALL.md 提供仅本地 Skill 导入、聊天安装检查的步骤。
执行者仅传送文件，未在 WorkBuddy 中安装技能或修改其配置。用户已回传上述 Mac 终端预检结果；技能列表截图及 WorkBuddy 新聊天执行仍待验证。
已提交审核的 Connector ZIP 未重新生成或上传，Linux 保存副本摘要仍为 856748041f8b8932e029a195c4f215517cf31d7dbc994a171d8203dddcf2613c。

### 新基线独立认证链路

TestAuthTransactionCLIHeadlessMySQL 再次通过，268.94 秒，exit 0。
MGR 为 c99ecdd 加本任务未提交响应增量；Web 由 39445b7 当前源码重新编译，SHA-256 仍为 426a0a773a60bff812940824d35bd3a000250cf8843b71c68d80d0af6fedcfcf。
CLI 直接使用 npm registry 已安装包中的 Linux 原生程序，SHA-256 为 01de9b66e158665c9656e02fcff3fb0c94557657d668ba8d8289828398cf7fc0。

```sh
GOWORK=off GOMAXPROCS=2 \
TIANA_TEST_CLI_BINARY=/home/qujianping/local/src/tiana/.worktrees/workbuddy-connector/cli/dist/registry-install.kyCgXy/install/lib/node_modules/@tianacloud/cli/platforms/linux-amd64/tiana \
TIANA_TEST_WEB_BINARY=/tmp/tiana-connector-auth-rebase-20260912.6n4d2L/tiana-web \
TIANA_TEST_MYSQL_DSN='root@tcp(127.0.0.1:32820)/mysql?parseTime=true' \
go test ./tests -run '^TestAuthTransactionCLIHeadlessMySQL$' -count=1 -v -timeout=10m
```

命令在 MGR 仓库运行。使用本任务独立 MySQL 容器中新建的随机测试库，测试结束清理该库；未清理其他数据库或共享环境。
覆盖实际 Web 代理、MGR/MySQL、CLI 登录、账号投影、异步创建编排、凭据保存、resume、退出及已有浏览器会话再次批准。
Control 和邮箱投递仍为测试替身；浏览器为 HTTP 表单客户端，不代表 Safari、WorkBuddy 或真实 Gateway SQL 通过。
本轮进程已结束，无活跃联调进程。目标 MGR 尚待发布含响应投影的版本，再经用户确认部署。

## 2026-09-11：环境与 CLI 管理端

### 目标 Mac

经用户授权，通过 SSH 对 `jason@100.92.193.32` 做只读检查：

| 项目 | 实际结果 |
| --- | --- |
| 芯片 / 架构 | Apple M5 / arm64 |
| macOS | 26.6.2，build 25G83 |
| WorkBuddy | 5.5.4；应用位于 `/Applications/WorkBuddy.app` |
| Console HTTPS | Mac 的 curl 访问 `https://console.service.internal.tiana.com` 返回 HTTP/2 200，未关闭证书校验 |
| 原生构建条件 | `xcode-select -p` 返回 `/Library/Developer/CommandLineTools`；SSH PATH 中未找到 go/cargo/node，不能据此断定机器完全未安装这些工具 |

没有在 Mac 上安装、构建、修改配置或启动新制品。
以上不证明浏览器登录、WorkBuddy 托管 npm、Go HTTP 或 Rust Gateway 路径已经通过。

### 当前实现范围

CLI 工作树基线：`c32c12b5181cc752adab4682b948ba9da65398e8`，分支 `feat/workbuddy-connector`；
来源与 tree 校验已登记工作区根 `BASELINES.json`。

已实现但未发布的管理端能力：

- auth login/status/logout：loopback PKCE、凭据落盘后回调成功、刷新串行化、reauth_required 持久化。
- 账号与实例凭据存储：账号隔离、0700/0600、原子文件替换、进程间文件锁。
- instances list/get/create/update：分页、非秘密连接元数据、revision 更新、原异步 Operation 等待。
- credentials create、requests list/get/resume：提交前固定完整请求和幂等键、Token 一次性交付、部分成功和中断恢复。
- HTTP 写入不由 transport 隐式重放；PATCH 结果丢失后只读核查，仍区分观察结果与原请求结果。

MGR/Web 新 OAuth 接口、SQL executor、Connector 安装和真实账号联调尚未实现或验证，
不能将本地 HTTP 模拟服务的结果描述成线上闭环。

### 自动化证据

在 `cli/` 运行：

```sh
go test -race ./internal/cloud ./internal/cloudcli ./cmd/tiana
TIANA_RUST_CONTROL_ARTIFACT=/home/qujianping/local/src/tiana/sdk/tests/fixtures/control_vectors.txt go test ./...
TIANA_RUST_CONTROL_ARTIFACT=/home/qujianping/local/src/tiana/sdk/tests/fixtures/control_vectors.txt go test -race ./...
go vet ./...
```

结果：以上命令通过。
首次不带 fixture 环境变量的全仓测试失败，因为默认寻找相邻 `sdk-rust/`；
随后使用测试原有配置指向 SDK 的真实 fixture，通过其固定 SHA-256 校验并通过测试。
现有需显式提供 `TIANA_REAL_HELPER`、`TIANA_TURSO_BIN` 或 root 安装环境的黑盒测试，
未以本次常规 Go 测试通过作为已经执行的证明。

新增测试覆盖：

- PKCE 与 state、取消/兑换失败不覆盖已有凭据、保存失败不显示登录成功、结束后 listener 关闭。
- 多客户端并发只刷新一次、原始 auth_time 保留、重启后重用新凭据。
- invalid_grant、refresh 响应丢失/无效、明确暂时失败、请求未发送的状态区别。
- access 撤销使 status 变为未登录；迟到的 401 不覆盖新登录；普通服务故障保留登录态。
- logout 在线/离线均清理当前账号凭据，保留其他账号。
- 实例 create 响应丢失后按原 body/key 恢复；pending 后沿用原 Operation；失败保留原原因。
- Token 响应丢失与 COMMIT_STATUS_UNKNOWN、已提交无原值、明确 REJECTED、落盘失败与部分成功。
- Token 已保存而 journal 尚未完成时恢复；并发 resume 复用同一任务。
- 任务账号隔离与只读检查、提交前持久化、凭据状态输出脱敏。
- revision 十进制字符串、配置更新保留 cache_mb、labels/notes 清空、PATCH 丢失后只读核查。
- CLI 单一 JSON stdout、精确 status 文本/退出码、分页、参数错误与登录 URL 输出通道。

Darwin arm64 / amd64 的 Go CLI 交叉编译均通过，`file` 确认为对应 Mach-O 架构。
这些仅是 Go 编译验证，不含完整运行资产；没有在 Mac 上执行，也不是正式原生包。

`agent-skills/` 的 `npm run validate:ci` 通过，检查的仍是现有 0.1.0 Skills/包装；
这不表示目标 0.2.0 CLI Connector 包已完成。CLI 原仓库仍在 `main` 且工作区干净。

## 2026-09-11：主分支同步与统一认证方案

用户要求涉及仓库先 rebase 主分支；完成后确认复用 main 的 Auth Transaction 与 authclient 凭据存储。
方案第 2、3、5、6、11–13 节已同步；CLI + Skill 和完整聊天验收目标不变。

| 仓库 | 本次 origin/main | rebase 后 HEAD |
| --- | --- | --- |
| cli | 557957a | 557957a |
| mgr | ee51e4f | 6018e17 |
| web | cadc6cb | 96d4579 |
| gaia | bcf383b | b1ae98e |

agent-skills 远端没有 HEAD/分支，保留本地初始快照。未更新原目录 main，未 push、发布或共享部署。
工作区根 REBASE-2026-09-11.md 记录逐文件冲突处理与 stash；BASELINES.json 保留原始记录并添加本次基线。

### 当前实施边界

主分支已有事务创建/轮询/兑换、refresh/logout/whoami、现有浏览器验证页面，以及系统凭据库优先/文件回退。
本任务 CLI 管理编排已从 stash 恢复，API 前缀改为 /api/v1；统一接入该 authclient 尚未完成。
只读 status、Tenant/refresh_expires_at 投影、并发/失效状态和 InstanceToken 读取/索引列为明确增量。
不能将主分支 whoami 当作无副作用 status，不能将浏览器“已授权”当作 CLI 凭据已保存。

MGR 未发布的独立 OAuth 实现保留在 stash，没有恢复到当前代码或部署；
接下来的实现直接复用现有 Auth Transaction/schema 013。
此前该未合入实现的 MySQL 测试中，012 升级用例通过，但 native-account 用例在 fixture 建表时超时，
没有形成其完整 MySQL 验收通过记录，也不作为新方案证据。

### 本次自动化结果

- CLI：go test ./...、go test -race ./...、go vet ./... 通过。
  新 main 要求 helper contract 3；原 SDK 工作树的 contract 2 fixture hash 不匹配，首次全仓测试失败。
  随后独立 clone SDK main c681e209a9151eee8dc3a0b9ed0277145617ac82，使用其真实 fixture 重跑通过。
  路径：/tmp/tiana-connector-sdk-check.rW1GT2/sdk/tests/fixtures/control_vectors.txt；
  SHA-256：36803ef0872efe4f1e377a01917e3313b4aa21bcd361945cc0e898d45c9b9a88。
  原 SDK 工作树和 CLI 的固定校验值未修改。
- MGR：go test ./...、go test -race ./...、go vet ./... 通过。
  常规运行未设置 MySQL DSN 或外部 CLI，相关集成项按原规则跳过；不是认证生产验收。
- Gaia：go test ./...、go vet ./... 通过；未运行真实 K3s/共享环境验收。
- Web：npm ci、typecheck、build、go test ./cmd/tiana-web 通过；构建有大 chunk 提示。
  首次浏览器运行 27/34 通过，发现三个正则 mock 仍用旧 API 前缀；修正后全套 34/34 通过。
- agent-skills：npm run validate:ci 通过；方案 8 个 JSON 示例均成功解析。
  仍是现有 0.1.0 Skills 包检查，不表示 0.2.0 Connector 完成。

独立 MySQL 容器 tiana-connector-oauth-mysql、loopback 端口 32820 仅用于本任务测试。
rebase 后用户删除维护工具的三项 MySQL 用例已分别通过：TestUserDeletionMySQL（246.68 秒）、
TestSharedTenantRejectedMySQL（243.00 秒）、TestControlFailurePreservesUserUntilRetryMySQL（249.47 秒），包含建表及清理。
首次合并运行在前两项通过后达到包级 10 分钟超时，第三项单独重跑通过。未操作真实用户数据。
以上均不是 WorkBuddy 安装、原生 Keychain、浏览器生产授权或真实 Gateway SQL 的验收证据。

## 2026-09-11：Auth Transaction 服务端与共用 authclient 增量

MGR 复用当前 schema 013，已实现 token/refresh 的实际 refresh_expires_at、user.tenant_id 和 whoami 相同身份投影。
access 查询和 refresh 在当前 Principal/default Tenant/成员状态、角色、revision 与 session 绑定不符时失效；
refresh 在消费旧凭据前验证绑定，仍保留原始 auth_time、单次轮换和滚动到期语义。
事务提交前的存储失败与提交结果未知分别返回 server_error / commit_status_unknown。

服务与 HTTP 测试验证投影、滚动 expiry 和错误分类；MGR 全仓 go test、race、vet 通过。
设置独立 MySQL DSN 的 TestAuthTransactionMySQLBindingAndRefreshAtomicity 通过（266.98 秒）：
角色、成员 revision、成员状态、Principal 状态、default Tenant 变化，以及 SQL trigger 注入回滚、8 路并发刷新。
七项子用例均实际访问 MySQL；不再用无 DSN 时的跳过结果作为这部分证据。
TestAuthTransactionMySQLRoundTripAndSingleUse 也通过（259.52 秒），验证实际建表后的身份创建、
事务批准、授权码替换/单次兑换、session 读取、refresh 轮换和退出撤销。

CLI 的原 authclient 已增加：

- 凭据 Tenant/refresh 到期信息，纯本地 Status 投影和 reauth_required 持久化。
- 同 origin 登录保存/刷新/退出锁，刷新锁内重读；共享文件跨 origin 更新锁与目录同步。
- access 拒绝不自动重放业务请求；迟到的拒绝不覆盖新登录。
- 刷新发送前失败/明确回滚保留状态；提交未知、响应丢失、无效响应或 invalid_grant 进入重登状态。
- 新凭据保存失败时标记重登；失效状态也无法保存则返回凭据保存错误。
- 登录链接回调供命令入口展示/打开，等待浏览器期间不持有凭据锁。

自动化覆盖只读 status、空目录/存储读取失败、响应丢失后客户端重建、迟到拒绝、保存失败、
16 个 origin 并发写文件，以及 8 个独立 CLI 测试进程共用文件后只发出一次刷新。
测试使用临时文件与本机 HTTP 服务，尚未验证 WorkBuddy 进程中的系统 Keychain。
本次 CLI 全仓 go test ./...、go test -race ./...、go vet ./... 均通过，仍使用上述固定 SDK fixture。
GOOS=darwin、CGO_ENABLED=0 下 authclient 的 arm64/amd64 测试二进制交叉编译通过，
位于 /tmp/tiana-connector-auth-darwin.NyVdmL；没有在 Mac 执行，不等于原生 Keychain 或完整 CLI 制品验证。
agent-skills validate:ci 和 Git 差异格式检查通过，包版本仍为 0.1.0。

### WorkBuddy 命令与凭据索引整合

cloud/cloudcli 已改为调用同一 authclient 的 Auth Transaction、Status、refresh 与 HTTP 请求。
终端 login/logout 也接入同一入口，支持 --no-open/--json；origin 和凭据后端使用既有主分支配置。
当前账号从凭据记录的 user 投影取得，即使管理凭据到期或需要重登，仍可在本地定位 SQL 连接。

InstanceTokenStore 已增加按 Tenant/instance/token 引用读取和删除，共享文件写入加锁。
账号文件保存选用连接及全部已登记 Token 的非秘密引用；Token 原值保存在系统凭据库或既有文件后端。
Token 保存前登记引用，保存后更新选择；resume 能从已保存凭据恢复尚未完成的选择和 journal。
logout 在同 origin 锁内清理本账号登记过的全部 Token，再删除管理凭据；
本地清理失败保留引用和重登状态以便重试，远端结果未知与本地存储失败分别报告。

本次 CLI 全仓 go test、go test -race、go vet 通过。新增/更新的证据包括：

- Auth Transaction 的 JSON 创建/轮询/兑换及登录失败保留原凭据。
- 终端 login → WorkBuddy auth status → credentials create → 终端 logout → status 未登录的串联测试。
- Token 引用的读取/删除、12 个 origin 并发保存、非秘密连接元数据、重登所需状态下仍可本地读取连接。
- Token 已保存但选择/journal 未完成时恢复原任务，未重新签发 Token。
- 退出清理被替换的旧 Token 和当前 Token、保留另一账号 Token；本地清理失败后可重试。

上述均为本机 HTTP、临时文件和进程测试；未使用真实 WorkBuddy 或原生 Keychain。
cmd/tiana 的 darwin-arm64/darwin-amd64 测试二进制交叉编译通过，保存在
/tmp/tiana-connector-unified-auth.JQXZq4，未在 Mac 执行，也不是包含 executor/helper 的完整制品。
agent-skills validate:ci 和差异格式检查通过，验证对象仍是当前 0.1.0 包装。
随后完成终端整合，见下一节；SQL executor、跨平台完整制品和真实 WB 验收仍待完成。

### 终端与聊天管理流程统一

用户确认终端与聊天共用任务流程：Token 保存后输出状态，中断后用 requests resume 恢复。
db create/tokens 已接入 cloud 的异步创建、Endpoint Token 和任务持久化；
名称解析、列表分页与详情请求固定调用开始时的账号。connect 功能未修改。

本轮验证命令（cli/）：

```sh
TIANA_RUST_CONTROL_ARTIFACT=/tmp/tiana-connector-sdk-check.rW1GT2/sdk/tests/fixtures/control_vectors.txt go test ./... -timeout=60s
TIANA_RUST_CONTROL_ARTIFACT=/tmp/tiana-connector-sdk-check.rW1GT2/sdk/tests/fixtures/control_vectors.txt go test -race ./... -timeout=60s
go vet ./...
git diff --check
```

以上通过。新增 db_tasks_test.go 覆盖：

- 终端浏览器事务登录后提交 202，按原 Operation 等待并保存首枚 Token；请求在 HTTP 提交前完整落盘。
- 终端创建任务由聊天 requests resume 恢复，保持原实例、Token body 和幂等键；已完成任务可本地恢复。
- Token 提交结果未知时读取原 Operation；原值不可取回时保留实例及 Token ID。
- Token 落盘失败输出保存错误、保留恢复标识；相对到期时间转换后在恢复中保持同一绝对值。
- 原账号任务隔离、重登后继续，以及列表跨页/签发前名称解析期间账号变化时停止原命令。
- 任务文件 0600、JSON 结果和终端输出只含已保存状态与非秘密标识。

现有列表分页、详情 URL、陈旧运行态和 supervisor 测试也通过。
中途重构时测试包曾因旧接口引用编译失败；完成接入并更新对应合同测试后，上述全仓命令重跑通过。
这些仍是本机 HTTP/文件测试，不证明真实 Gateway SQL、Mac Keychain 或 WorkBuddy 安装可用。

### SQL 执行器与 CLI 接入

已增加 cli/sql-executor/，固定 SDK v0.1.0-dev.5，并生成 Cargo.lock；
解析到的 commit 为 0d955224802d793539835b868f75f5163f27057f。
internal/sqlexec 通过私有管道启动一次子进程，cloudcli 提供 sql execute；
参数/结果保留 JSON 原值及 int64 十进制字符串。SQL 使用本地 InstanceToken，不先访问 MGR。

本轮 Rust 测试共 11 个库测试、3 个独立子进程测试，通过 cargo test --locked：

- SQLite DDL、CRUD、sqlite_schema、pragma_table_info，中文/引号、NULL、int64 极值、blob 和浮点绑定。
- 数据库语法/参数错误、输入类型范围、HTTP 截断及不完整执行结果。
- INSERT RETURNING 已产生一行后注入 413、序列化/INTERNAL 或连接中断，返回 unknown；
  独立查询确认仍为一行，没有自动重放。execute 成功且 close 失败保留结果并附警告。
- SDK 经本地测试证书的 TLS 1.3/H2 Gateway fixture 实际 CONNECT，检查 SNI、authority、
  hrana-http 和凭据头，再将 pipeline 交给本地 SQLite；正常、401 和写入后 413 三种场景通过。
- executor 子进程在父进程保持 stdin 打开时可按期返回；stdin 关闭可取消等待中的连接；
  私有 JSON 错误返回单一脱敏结果。

Go 全仓 test、race、vet 和 diff --check 通过；使用以下额外环境执行了 Go → 已编译 Rust
子进程的真实私有协议测试（输入错误场景，不访问数据库）：

```sh
TIANA_TEST_SQL_EXECUTOR=/home/qujianping/local/src/tiana/.worktrees/workbuddy-connector/cli/sql-executor/target/debug/tiana-sql-executor \
TIANA_RUST_CONTROL_ARTIFACT=/tmp/tiana-connector-sdk-check.rW1GT2/sdk/tests/fixtures/control_vectors.txt \
go test -race ./... -timeout=60s
```

Go 还验证管理 access/refresh 已过期且 reauth_required 时仍使用本地 Token、无 MGR 调用；
缺凭据/到期/输入失败的执行边界、输入等待期限、子进程崩溃及输出失败的 unknown 结果。
CLI 命令成功结果的子进程 fixture 与 Rust 的 SDK/SQLite fixture 是独立测试，不合并宣称为部署端到端。

尚需完成三平台完整制品、真实 Gateway/App SQLite 路径、Mac Keychain、安装与 WorkBuddy 聊天验收。

cargo fmt --check、cargo clippy --locked --all-targets -- -D warnings 均通过；
cargo build --locked --release 生成本机 Linux x86-64 动态链接执行器，--version 输出 0.2.0。
本轮产物 sql-executor/target/release/tiana-sql-executor 的 SHA-256 为
9f656ddfa0abdb0e51c3341dca29e73d988c1779da7a1f0391daee209b401426；
Go 的真实私有协议测试也使用该 release 产物重跑通过。
该产物仍是开发机编译结果，不是已发布的三平台成套包。
agent-skills validate:ci 通过，校验对象仍为现有 0.1.0 Skills 包。

### 安装检查与分发包装

CLI 的 verify-install [--json] 已实际启动 helper 并完成 contract 3/SQLD adapter 握手，
结束后关闭子进程；同目录 SQL executor 的 --version 必须与 CLI 匹配。
指定的公开 Gateway CA 文件缺失、为空或证书损坏会在检查/SQL 子进程启动前报告安装问题。
新增 helper 缺失/旧 contract/缺 adapter/握手错误、executor 缺失/版本错误、证书加载测试。
Go 全仓 test、race、vet 和 diff --check 重跑通过；Rust release 的真实版本探测测试通过。

新增 cli/scripts/build-platform.mjs 和 package-cli.mjs：原生 host 成套构建与离线检查，
产出平台包、SHA-256 和依赖/源版本 manifest；三平台汇总时核对版本、哈希和可执行架构，
将现成资产放入 npm tarball，不安装依赖、不运行 lifecycle scripts、不上传。
原 build-single-binary.sh 补 darwin-amd64，并在 host/target 一致时执行安装检查。
新的 native wrapper 默认开启证书校验；原 lower-level 脚本默认策略没有变更。

```sh
node --test packaging/launcher.test.mjs packaging/package.test.mjs
```

共 12 项测试通过：argv/stdin/cwd/stdout/stderr/退出码透传、SIGINT/SIGTERM 转发、
缺失可执行文件、原生信号退出、三个平台布局、全新缓存下离线 npm 安装和 npm bin 启动、
缺平台/版本不符/哈希损坏/架构不符。三平台使用明确标记的 Go 合成可执行文件，
测试 CA 也为非证书占位数据；这些只验证包装，不宣称真实 Mac 运行或连接成功。

本机真实 Linux 开发测试包另外构建成功：
`/tmp/tiana-connector-package-check.0bogSu/linux-build/tiana-cli-0.2.0-linux-amd64.tar.gz`，约 6 MiB。
其中 Go CLI 静态链接，Rust SQL executor 为本机构建的 glibc 动态链接程序。
CLI SHA-256：d6700653cd9f5fcaf43418296febcdd5aad6a23c6ce88b1aae8e934669239302。
真实 verify-install --json 返回 succeeded、version 0.2.0、helper_contract 3、helper_mode embedded。
helper 使用 SDK main c681e209a9151eee8dc3a0b9ed0277145617ac82（无发布 tag）；
SQL SDK 使用已固定的 dev.5。正式发布前需协调 contract 3 的不可变 helper 版本。
测试构建显式 TIANA_INSECURE_TLS=false、port 443，打包了本机公开 Console CA；
这仅供离线构建测试，不代表该 CA/端口就是目标 Gateway 的发布配置。
首次包的 manifest 尚未记录后来补上的 insecure_tls 字段，后续按新脚本重建。
没有执行真实服务登录/SQL，没有上传 tarball，也没有在用户 Mac 安装或构建。

### Canonical Skills 与 Connector 候选包

已更新 tiana/tiana-sqlite 为 0.2.0 preview，通过 CLI 处理管理/恢复与 SQL；
主入口简短，完整命令、typed params、DDL/CRUD、状态解释放在直接链接的 references。
旧的 MGR HTTP 管理示例已由当前 CLI 说明替换；SDK/原生 Turso 连接资料继续用于明确的应用集成任务。
package.json、lockfile、plugin.json、Skill metadata 和 Connector metadata 版本对齐 0.2.0。
tiana-branches 只同步分发版本，内容未改、不包含在 Connector 内。

新增 packaging/workbuddy/tiana-cloud/{connector-meta.json,cli.json,icon.svg}，
以及 build-workbuddy-connector.mjs / validate-workbuddy-connector.mjs。
构建从 canonical Skill 复制正文/资源，并复用现有 WorkBuddy 本地化 frontmatter 注入函数；
校验 ZIP 根布局、版本、两份 Skill 正文和引用副本、本地化字段、配置命令和校验和。
本轮 npm run validate:ci、两个主 Skill 的 quick_validate 和 git diff --check 通过。

0.2.0 ZIP 已生成于 agent-skills/dist/workbuddy/tiana-cloud-0.2.0.zip，约 14 KiB；
候选包 SHA-256 以同目录 .sha256 为准。它仍仅为配置候选包：
init 指向的 tarball 尚未发布，不能据此认定可安装。

SQL reference 中的 8 个完整 JSON 示例经 Node 解析、交给内存 SQLite 3.46.1 实际执行：
中文/引号/int64 极值、建表、sqlite_schema/pragma_table_info、两行 INSERT RETURNING、SELECT、
UPDATE RETURNING、DELETE RETURNING 和最终行状态全部符合预期。这不是 Gateway 集成测试。

```sh
TIANA_TEST_CLI_BINARY=/tmp/tiana-connector-package-check.0bogSu/linux-build/linux-amd64/tiana \
npm run test:connector-auth
```

1 项真实 CLI 多进程认证调度测试通过（11.08 秒）：使用 CLI 配置中的 auth/status/unAuth，
对接本地 HTTP fixture 和独立临时凭据目录；未打开浏览器、未读取真实用户凭据。
验证 URL 在 10 秒内输出、11 秒延迟批准前进程继续运行、只兑换一次、输出不泄露 fixture 密钥、
3 次新进程 status 不调用网络也不改凭据、退出/重复退出以及 SIGINT 中断返回需重登。
它证明 CLI 进程合同，不证明 WorkBuddy 的 authWaitForExit 实际实现。

U-02 已提供 [平台交接说明](workbuddy-platform-handoff.md)，并通过用户授权的 Safari 读取实际账号页面。
用户确认当前企业主体后已上传 ZIP，平台解析成功，生成 ID `oc_19e12297ca82254a`。
名称、0.2.0 版本、图标、中文介绍和三个示例被识别，选择技术开发类目后进入最终确认页；未点击提交。
配置字段已对照 2026-09-11 官方 Connector 文档核对；三步流程没有测试入口，source 归属和客户端测试可见性仍需平台确认。

## 真实 MGR / MySQL / CLI 集成

2026-09-11，`TestAuthTransactionCLIHeadlessMySQL` 通过（256.04 秒）。
使用独立 MySQL、真实 MGR HTTP 服务和 Linux CLI，验证浏览器邮箱验证与批准、CLI JSON 登录身份、
实例创建后凭据保存、实例查询、`requests resume`、退出后刷新失效，以及保留浏览器会话再次批准登录。
凭据文件位于测试临时目录，校验文件权限与输出不包含密钥。
Control 为测试替身；浏览器交互由测试 HTTP 客户端执行。这不代表 Safari、WorkBuddy、真实 Control 或 Gateway SQL 验收。

Web 的授权 POST、浏览器 proof / JSON 透传以及下载文件字节、HEAD、缺失文件测试通过；
全仓 `go test`、race 和 vet 通过，生产代理代码未改。

随后在同一测试中指定 `TIANA_TEST_WEB_BINARY`，使用实际 Web 子进程作为 CLI 和浏览器访问入口，
MGR 的 PublicOrigin 配置为该 Console 入口。完整流程再次通过（272.87 秒）：

```sh
TIANA_TEST_CLI_BINARY=/tmp/tiana-connector-package-check.0bogSu/linux-build/linux-amd64/tiana \
TIANA_TEST_WEB_BINARY=/tmp/tiana-connector-web-chain.nPvKT3/tiana-web \
TIANA_TEST_MYSQL_DSN='root@tcp(127.0.0.1:32820)/mysql?parseTime=true' \
go test ./tests -run '^TestAuthTransactionCLIHeadlessMySQL$' -count=1 -v -timeout=10m
```

命令在 MGR 仓库运行。Web 来自 `96d45792576e47d038b5be3105cb1625eabcc42b` 的生产代码，
二进制 SHA-256 `426a0a773a60bff812940824d35bd3a000250cf8843b71c68d80d0af6fedcfcf`。
这证明本地真实 Console 代理 → MGR 的认证及管理协议可运行，仍不是已部署 HTTPS、真实邮件投递、Safari 或 WorkBuddy 验收。
Control 使用测试替身，未验证真实实例运行或 Gateway SQL。测试后 MGR 全仓 test/race/vet 通过。

## macOS arm64 原生构建与离线测试

2026-09-11，用户授权后在 Mac `/tmp/tiana-connector-build.GDaVX8` 内准备源码、工具链与缓存，
没有系统级安装、证书或 WorkBuddy 配置改动。
Go 1.26.5、Node 22.23.2；SQL executor 使用 Rust 1.97.1，helper 按其仓库 toolchain 使用 Rust 1.85.1。
官方工具下载 SHA-256 校验通过。

- helper 与 SQL executor release 均在该 Mac 原生编译，`file` 为 Mach-O arm64。
- SQL executor：11 项库测试、3 项子进程测试和 `cargo clippy --locked --all-targets -- -D warnings` 通过。
  包括本机 TLS/H2 fixture、SQLite DDL/CRUD/类型和提交后响应不明时不重放；不是生产 Gateway。
- CLI：`go mod verify`、`go test ./...`、`go test -race ./...`、`go vet ./...` 通过，
  已指定该 Mac 的真实 helper/executor 和原始 SDK control vectors。
- Node launcher 与 npm 打包 12 项测试通过，包含新缓存离线安装；三平台包内程序仍为合成 fixture。
  工作目录断言按文件系统真实路径比较，在 macOS 的 `/tmp` 符号链接环境也通过。
- 新编译的 arm64 `tiana-dev` 跑真实 CLI 多进程认证测试通过（11.73 秒），使用 darwin 配置命令，
  覆盖延迟批准、保存后跨进程状态、退出及中断；使用本机 HTTP fixture 和临时文件凭据，不是 Keychain 或 WorkBuddy 调度。

原生组件摘要：

| 组件 | SHA-256 |
| --- | --- |
| helper | 0c68d817a5f1fa80718d73080f0449e6ce6cfeacc2e8ae9e3f81e04fe015f07b |
| SQL executor | a85bb65f1c7ff3694b5d5c63c6b78d259f0bd279c755653ddf26f8bc2624b2e1 |

日志保留在 Mac `build-test-complete-source.log`（Rust）与 `test-go-native.log`（Go/打包/认证）。
Go 依赖经 Linux 准备后传入临时文件代理，按原 go.sum 验证；SDK 从完整 Git bundle 提取固定 dev.5，
不改变 Cargo.lock 或全局 Git 配置。Linux 上相应打包与认证测试也通过。

当前产物是原生组件与测试 CLI，不是完整发布包：尚需目标 Gateway 公开 CA、helper 正式不可变版本、
组装发布和真实 WorkBuddy 验收。用户确认 darwin-amd64 延期，留 TODO，不作为本次交付门槛。
现有打包脚本仍要求三平台资产，后续组包前需按已确认的两平台范围对齐；本轮只更新方案和交接记录。
未登录真实 Tiana 账号或读写用户数据库。

## 目标环境只读预检

2026-09-11，通过现有 Gaia GET 接口读取并仅保留公开字段，未提交部署、登录账号或修改配置：

| 组件 | current/deployed 观察 |
| --- | --- |
| Gateway | 两者一致，IN_SYNC；`https://gateway.service.internal.tiana.com:9443`，实例域名后缀 `db.service.internal.tiana.com`，snapshot `4f179631-9631-4f7c-ab04-c96288905d38` |
| MGR | 两者一致，IN_SYNC；PublicOrigin 为 Console，snapshot `8f519e1d-3ffd-4607-b70d-ecbd59d6da24` |
| Web | 两者一致，IN_SYNC；PublicOrigin 为 Console，snapshot `c1a80b40-84e4-404f-b270-59159ba8e65e` |

Gateway 镜像摘要 `badfd5435f9dc9e40b1f183703cb326539c73536b837e59dfbfd3d59b18561d2`；
MGR `8e47daf0b5dc789355715857922936510c8d7967c81a80bf26e754202c7b5267`；
Web `04a3521b140bf8ab7357dd1da3ced34cca192a3749422ec78443df5fdb3af376`。
这些是当前线上镜像观察，不证明本任务未发布的改动已部署。

Gateway 实际 TLS 1.3 / ALPN h2 握手成功，叶子证书指纹与 Gaia 配置一致：
`47:D1:11:18:2A:6F:9E:28:4C:F8:6E:A9:60:70:8A:66:5D:74:CB:86:80:56:96:61:43:22:F0:3C:FF:EF:64:3D`。
签发者为 `Tiana Wulanchabu Gateway Root`，仅服务端叶子证书被返回；本机默认链验证失败，未关闭验证。
后按用户要求追查 spec 历史提交 `a7f18a9` 的 `ensure-region-secrets.sh`，
并与当前 Gaia `operations/legacy-acceptance/wulanchabu-region-multi-control/config.env:84` 对照，定位到
Vault KV v2 mount `kv`、路径 `platform/gaia/wulanchabu-gateway-ca-v2`、字段 `ca_pem`。
只读获取该公开字段，确认 subject=issuer=`Tiana Wulanchabu Gateway Root`、`CA:TRUE`，
有效期为 2026-08-31 13:33:13 UTC 至 2027-08-31 13:33:13 UTC，SHA-256 指纹
`93:BC:7E:F3:32:4A:61:AE:91:DA:2D:61:54:D1:56:26:D8:D8:B5:8B:E6:08:00:AB:0C:BA:A2:77:24:E6:7E:44`。
指定该 CA 后，当前 Gateway:9443 握手返回 `Verification: OK`、`ALPN protocol: h2`、`Verify return code: 0 (ok)`。
没有读取私钥、写入证书文件或修改系统信任；该检查不执行 SQL，不替代完整包和真实数据库验收。

Console GET `/api/v1/device` 返回 200 HTML 表单，未登录的 GET `/api/v1/auth/transactions/whoami` 返回 401 JSON；
只证明对应入口存在，没有创建 Auth Transaction 或批准登录。CLI tarball HEAD 仍为 404。

在已授权的 Mac 临时目录放置公开 Console CA，执行 HEAD Console 的只读网络检查：
原生 Go 返回 200 且 VerifiedChains=1；临时 Node 22 返回 200 且 authorized=true。
未改变系统信任，未在 `$HOME/.tiana/trust` 写文件。WorkBuddy 托管 Node 20 的 init/env 仍待实测。
已新增 [安装交接手册](workbuddy-cli-install.md)，标明当前不能完成安装，待实际入口与制品发布后补齐 UI 证据。

## 用户协作节点

### npm 候选制品与一键发布验证（2026-09-11）

用户确认公共 npm 分发、darwin-amd64 延期，并允许本次候选包内置 helper 固定提交
`c681e209a9151eee8dc3a0b9ed0277145617ac82`；SQL SDK 仍为 dev.5。
CLI 已核对 origin/main=`557957ae294443632a4094cd432c8bc2af1cb653`，与 HEAD 相同；
agent-skills 远端无可用分支。未改主任务分支，无 stash 或 rebase 冲突。

新增 `cli/scripts/release-npm.mjs`、`test-platform.mjs`、配置示例与发布说明，
打包和启动器使用 darwin-arm64 / linux-amd64，Connector init 固定 npm 包版本。
首次 dry-run 在 Mac 私有协议测试的一秒期限处停止；相同程序独立复测 5 次均通过，
该非性能测试改用实际命令的 25 秒期限，生产行为不变。

第二次完整运行 `node scripts/release-npm.mjs dist/release.local.json --dry-run` 成功（session 17902，exit 0）：

- 两台原生主机均完成 helper/executor/embedded CLI release 构建，Gateway port=9443、insecure_tls=false，公开 CA 随包。
- 两台均通过 Go test/race/vet、Rust 11 单元 + 3 子进程测试、clippy，以及 Node 15 项启动器/打包/发布脚本测试。
- 同一个真实 npm tarball 在两台全新临时 prefix/cache 中离线全局安装成功，`tiana verify-install --json` 返回 succeeded、helper_mode=embedded、contract=3、version=0.2.0。
- npm publish --dry-run 成功；没有实际发布，输出中的 `+ @tianacloud/cli@0.2.0` 仅为预检结果。
- agent-skills validate:ci 与两仓 diff --check 通过。没有写用户凭据、系统信任或真实数据库，没有发布 wulanchabu。

待发布制品：`cli/dist/npm-0.2.0-qFj93S/npm/tiana-cli-0.2.0.tgz`，11,931,920 bytes，
解包约 27.2 MB、14 个文件；SHA-256 `87e4e4dac25b10be22a191ba47e95bcf6da5ca960a5fcfd6e4b5a4cda45fd183`。
Linux 原生 CLI 摘要 `01de9b66e158665c9656e02fcff3fb0c94557657d668ba8d8289828398cf7fc0`，
Mac 原生 CLI 摘要 `d9b95aeed88063d54ab0ebe41dd0e3da80828202f5a4ed198c69bda3d8558a56`。
其他组件与公开 CA 摘要见包内两个 `manifest.json` 和 `SHA256SUMS`。
Mac 构建/安装目录 `/tmp/tiana-connector-build.GDaVX8/npm-0.2.0.cMpX4y`，tarball 为其中 `package.tgz`。

新 npm Connector ZIP：Mac `/tmp/tiana-connector-build.GDaVX8/npm-connector/tiana-cloud-0.2.0.zip`，
SHA-256 `e2a94a6b2a12e692e2d0d14419a92c8e4821de12e5c07ef03ae0d8359fea4c04`，旧 ZIP 和审核记录未改。
发布机 `npm whoami` 返回 ENEEDAUTH，registry 查询目标版本返回 404；用户正在准备账号，
已提供注册、邮箱验证、2FA、免费组织与发布机登录说明。真实发布及 registry 安装验证待账号就绪。

| 节点 | 当前状态 | 下一步所需证据 |
| --- | --- | --- |
| U-01 | 版本/架构、网络可达性已验证；用户回传浏览器授权后终端登录与实例读取成功 | 已具备继续客户端验收的环境证据；客户端执行另见 U-04 |
| U-02 | 企业账号配置预检成功；用户另以个人账号提交 oc_5878fe73dc7a3123，回传审核中 | source 归属、账号可见性和真实开发测试入口；需平台团队确认 |
| U-03 | 两平台完整包已公开发布；构建、测试、离线及 registry 真实下载安装检查通过；已含 Gateway CA 和获授权的固定 helper | WorkBuddy 实际安装/执行验证；darwin-amd64 延期 TODO |
| U-04 | 用户回传 Mac 终端 verify-install 成功，版本/arm64/helper 3/executor 均正确；Connector 入口仍待确认 | WorkBuddy 新聊天调用和技能加载状态；正式 Connector 安装和授权调度仍另行验收 |
| U-05 | MGR v0.27.0 已部署；用户回传 Mac 终端授权及实例读取成功；曾出现 csrf_failed，原因未确认 | WorkBuddy 授权调度、Console 身份对照、新注册和取消；社交场景按实际启用情况核验 |
| U-06 | 此前已部署 MGR v0.27.0；2026-09-12 下午用户通知乌兰察布被占用，当前暂停共享环境操作。本地各仓库已重新同步并验证 | 等用户通知环境窗口恢复，再核对实际服务基线并继续真实创建/SQL 验收 |
| U-07 | npm 已发布；用户确认 npm 版新 Logo ZIP 已上传，ID oc_5878fe73dc7a3123，审核中（用户回传） | 最终审核结果及客户端可见性证据 |
| U-08 | 未就绪 | 客户端及服务就绪后执行完整聊天验收 |

## WB 验收状态

### npm 实际发布及 registry 安装（2026-09-11）

发布机登录账号 `qjpcpu`，组织 `tianacloud` 的 developer；用户完成发布所需的浏览器身份验证。
实际 `npm publish` session 18073 退出 0，registry PUT 返回 200，发布公开包 `@tianacloud/cli@0.2.0`。
发布参数为 `--access public --tag next --registry=https://registry.npmjs.org/ --ignore-scripts`；
实际 registry 的 next/latest 均指向 0.2.0，未额外更改标签。

最初包索引暂时 404，而版本 API、公开状态与 tarball 已可用；没有重复发布。
随后标准 `npm view @tianacloud/cli@0.2.0` 返回版本和摘要，SHA-512 与本地已测试 tarball 完全一致：
`sha512-eQpiGxpZFUkL0vwsK67mRYgNfZzJuDkPRoX3qdROQHB+SYORH/pg3Ani9Nc04D8Y3D9FidkJxq8AW/tIkJxVSg==`。
公开 tarball：`https://registry.npmjs.org/@tianacloud/cli/-/cli-0.2.0.tgz`。

同一个固定版本通过标准 npm 包名从 registry 下载安装：

- Linux：独立 prefix `cli/dist/registry-install.kyCgXy/install`，独立 cache；安装约 5 秒，verify-install 返回 succeeded，安装后原生组件 SHA256SUMS 全部匹配。
- Mac：独立 prefix `/tmp/tiana-connector-build.GDaVX8/registry-install.GFnpqV/install`，独立 cache；安装约 7 秒，`--version` 与 verify-install 均为 0.2.0 / embedded / helper contract 3。

本项是 registry 真实下载与本机执行验证，不是 WorkBuddy 安装、真实账号登录或数据库 SQL 验收。
未改 Mac 系统安装、证书或 WorkBuddy 配置，未修改平台审核记录，未发布 wulanchabu。

WB-01 至 WB-17 尚无 WorkBuddy 真实验收通过证据。WB-18 已有用户 Mac 终端登录/列表成功的部分证据，终端 SQL 未验证，整项仍未通过。
CLI npm 制品及 MGR 响应增量部署已就绪，用户已上传 npm 版新 Logo Connector ZIP，终端授权与管理读取已获得用户成功回传；当前仍缺可安装 Connector 入口、WorkBuddy 授权调度、聊天及数据路径验收。
后续每个场景记录实际环境版本、实例/任务非秘密标识、命令或聊天结果和必要截图。
