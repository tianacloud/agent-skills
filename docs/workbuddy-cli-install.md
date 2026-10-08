# 在 macOS WorkBuddy 使用 Tiana Cloud

> 历史材料：本文记录 2026-09 Connector 实施与验收；地址已按当前域名规范更新，历史测试结果不代表迁移后的重新验收。当前域名职责和使用流程见[开始使用](../skills/tiana/references/getting-started.md#环境与地址)；Connector 打包登录域名以 `packaging/workbuddy/tiana-cloud/cli.json` 为准。


本文记录 2026-09-12 的 macOS Connector 验收环境。当前 CLI 安装见[开始使用](../skills/tiana/references/getting-started.md)，Windows / WorkBuddy 的命令查找问题见 [Git helper 排查](../skills/tiana/references/windows-git-helper.md)。

2026-09-12 最新安排：乌兰察布服务被其他需求占用，下面的云端登录、实例与 SQL 步骤暂缓执行，等待新的环境窗口。
源码已 rebase CLI main `1a69699`，后续构建统一使用 `XDG_CONFIG_HOME/tiana` 或 `~/.config/tiana` 保存凭据、账号索引与任务。
这项变化尚未进入已发布 npm 0.2.0；下方临时安装路径仍指向旧制品。后续版本需重新验证登录和任务可见性；仅有旧 Keychain/旧目录记录的用户需要重新授权，不能把当前源码测试视为旧任务已恢复。

当前为交付准备版：可先按下面的本地预检步骤验证 Skill 导入和聊天执行 CLI，**正式 Connector 安装仍待平台入口**。个人账号连接器
`oc_5878fe73dc7a3123` 的 npm 版新 Logo ZIP 已由用户上传，回传状态为审核中；测试安装入口未确认。
CLI npm 包 `@tianacloud/cli@0.2.0` 已公开发布，并通过 Linux/Mac 从 registry 下载安装检查。
MGR v0.27.0 已经用户授权部署；用户已回传 Mac 终端浏览器授权及实例列表成功，下一步可在 WorkBuddy 复用该登录做只读检查。WorkBuddy Connector 安装仍独立等待平台入口。
此页会随真实安装结果更新，完整验收状态见 [验收记录](workbuddy-cli-acceptance.md)。

## 安装前需要具备什么

| 项目 | 当前事实 |
| --- | --- |
| Mac | Apple M5 / arm64，macOS 26.6.2，WorkBuddy 5.5.4 |
| Connector | Tiana Cloud 0.2.0，source=tiana-cloud，包含 tiana 与 tiana-sqlite 两个 Skill |
| 配置 ZIP | npm 版新 Logo 包位于 Mac `/Users/jason/tmp/tiana-cloud-0.2.0-npm.zip`；用户确认已上传，审核中 |
| CLI 下载 | npm registry 的 `@tianacloud/cli@0.2.0` 已公开发布；Connector 固定安装该版本 |
| Console | `https://console.tianacloud-staging.net`；Mac 原生 Go 和临时 Node 的 HTTPS 只读检查均为 200，证书验证成功 |
| Gateway | 当前实际发布为 `api.tianacloud-staging.net`，实例域名后缀 `tianacloud-staging.net` |
| 原生程序 | darwin-arm64 / linux-amd64 完整包已发布，离线安装及 registry 真实下载安装检查通过；尚未安装到 WorkBuddy；darwin-amd64 留 TODO |

平台 ZIP 是配置和 Skills，不是 CLI 安装包。上传成功、审核中、单独安装 Skill 或运行临时开发 CLI，
都不等于 WorkBuddy Connector 已安装。当前平台三步创建流程没有显示审核前测试入口，具体接入需平台团队确认。

## 审核前：本地 Skill 与 CLI 预检

此阶段只验证客户端能够加载技能、运行已发布 CLI，不发起账号登录或云端读写。
它不替代 Connector 的自动安装、连接、退出和重启验收。
本地技能包导入依据 [WorkBuddy 技能说明](https://www.workbuddy.cn/docs/workbuddy/From-Beginner-to-Expert-Guide/Function-Description/Skills-Market)；具体按钮以客户端实际显示为准。

1. 在 WorkBuddy 的技能页面选择「添加技能 → 上传技能」，分别导入 Mac 上的两个文件：

   ```text
   /Users/jason/tmp/tiana-workbuddy-precheck-0.2.0/tiana-0.2.0.zip
   /Users/jason/tmp/tiana-workbuddy-precheck-0.2.0/tiana-sqlite-0.2.0.zip
   ```

   确认已安装列表出现 Tiana 管理和 SQLite 两个技能并启用，回传该页面截图。
   这里导入的是独立 Skill ZIP，不是已提交审核的 tiana-cloud Connector ZIP。

2. 开启一个可执行本地命令的新聊天，请它只运行以下安装检查。PATH 只对本次 shell 生效，使用此前已从 npm 下载的临时安装，不修改系统或 WorkBuddy 配置：

   ```sh
   export PATH="/tmp/tiana-connector-build.GDaVX8/tools/node-v22.23.2-darwin-arm64/bin:/tmp/tiana-connector-build.GDaVX8/registry-install.GFnpqV/install/bin:/usr/bin:/bin"
   tiana version
   tiana verify-install --json
   ```

   预期 version=0.2.0、platform=darwin、arch=arm64、helper_contract=3，安装检查 status=succeeded。
   2026-09-12 通过 SSH 在上述临时环境再次执行已通过；用户随后也回传 verify-install 成功 JSON，并确认来自 Mac 终端。WorkBuddy 新聊天执行仍待验证。
   如客户端申请本地命令执行确认，由用户按实际提示确认；若命令失败，保留原始错误，不自行安装其他版本或源码编译。

3. 回传技能列表截图，以及新聊天中两条命令的实际输出。
   此步骤只检查本地调用。服务部署已就绪后，可继续下一节的终端登录与只读验证。

该临时 PATH 不代表 Connector 安装后的聊天 PATH 已通过。正式 Connector 就绪后，在不设置临时 PATH 的新聊天中重新验收，并确认没有重复技能加载。

两个包使用与 Connector 相同的 canonical Skills，只修正 npm 已发布的状态说明；本次没有替换已提交审核的 Connector ZIP。

## 审核前：终端浏览器登录与只读验证

MGR v0.27.0 已部署并通过健康检查。这一步使用 Mac 上已安装的 CLI，验证真实账号流程，不算 WorkBuddy 授权验收。

在 Mac 终端执行：

```sh
export PATH="/tmp/tiana-connector-build.GDaVX8/tools/node-v22.23.2-darwin-arm64/bin:/tmp/tiana-connector-build.GDaVX8/registry-install.GFnpqV/install/bin:/usr/bin:/bin"
tiana auth login
```

浏览器打开 Console 授权页后，用自己的正常账号完成登录并确认授权。如果没有自动打开，打开 CLI 输出的验证链接。
密码、验证码只在产品页面输入，不回传到聊天。CLI 成功结束后，在同一终端执行：

```sh
tiana auth status --json
tiana instances list --json
```

预期 status 显示 logged_in=true 和账号/租户 ID，列表返回 succeeded；空列表也通过。
回传这两个命令的 JSON 或错误信息即可，不读取或发送凭据文件。此步骤不创建实例或修改数据；实际创建和 SQL 随后单独验收。
目标服务仍使用现有 integration 配置，本项只在用户完成正常浏览器流程后记录实际身份认证结果，不以部署健康检查代替认证验收。

## 审核前：WorkBuddy 复用终端登录

2026-09-12 用户已完成上一节：本地登录状态为已登录，实例列表成功返回 6 条记录。无需为这轮检查退出或重新登录。
先按前面的步骤导入、启用两个独立 Skill，再把下面整段发到 WorkBuddy 的新聊天：

```text
请使用已安装的 tiana 和 tiana-sqlite 技能做只读接入检查。
先确认能加载这两个技能；若不可用，请报告并停止。
在同一次本地 shell 调用中依次执行：
export PATH="/tmp/tiana-connector-build.GDaVX8/tools/node-v22.23.2-darwin-arm64/bin:/tmp/tiana-connector-build.GDaVX8/registry-install.GFnpqV/install/bin:/usr/bin:/bin"
tiana version
tiana verify-install --json
tiana auth status --json
tiana instances list --json
请展示每条命令的实际输出与退出码，不要仅给出建议命令。
任何一步失败请停止，保留错误，不安装其他版本，不退出或重新登录。
不要读取凭据文件、Keychain 或输出 Token；不创建实例、不签发凭据、不修改数据。
```

预期：CLI 0.2.0、darwin/arm64、helper contract 3；登录状态为 true，实例列表 succeeded。
列表数量可能随账号实际操作变化，以本次真实返回为准。回传技能列表截图及聊天中的实际执行输出；无需发送凭据文件。
若聊天中未登录而终端已登录，回传错误和命令结果，先核对执行用户/环境，不复制凭据进行补救。

这一轮验证独立 Skills、聊天执行和已有登录复用，不证明 Connector 自动安装或浏览器调度通过。
只读检查成功后，继续专用实例的创建、结构查询和 CRUD；正式 Connector 可见后，仍需在不设置临时 PATH 的新聊天重跑安装与授权验收。

## 网络与证书

Console 使用现有 Caddy 私有 CA。公开证书已放在 Mac 的临时路径：

```text
/tmp/tiana-connector-build.GDaVX8/console-ca.pem
```

文件 SHA-256：`d9af24fc272df2c216b70914f4985d7cf88d617b33eb6eeaf42c9c238a971881`。
证书 SHA-256 指纹：`2B:E9:94:30:BC:E6:4B:09:DC:68:01:08:A8:FA:8B:83:F2:85:C7:C9:64:41:9C:61:C7:9B:A2:B5:7E:C8:22:9D`。

Console CA 用于浏览器和原生 Go 的管理连接。当前 Mac 原生 Go 的系统信任检查已通过；
如果实际登录还需系统信任导入，先请用户确认。目前没有修改系统证书。
WorkBuddy 托管 Node 20 从公共 npm registry 安装 CLI，仍需验证实际 init 和聊天 PATH。

Gateway 使用另一套证书，签发者为 `Tiana Wulanchabu Gateway Root`。
公开根 CA 已定位并只读验证：Vault KV v2 mount `kv`，路径
`platform/gaia/wulanchabu-gateway-ca-v2`，字段 `ca_pem`。
配置来源见 [Gaia 部署配置](../../gaia/operations/legacy-acceptance/wulanchabu-region-multi-control/config.env:84)。
证书 SHA-256 指纹：`93:BC:7E:F3:32:4A:61:AE:91:DA:2D:61:54:D1:56:26:D8:D8:B5:8B:E6:08:00:AB:0C:BA:A2:77:24:E6:7E:44`。
使用该根证书对当前 Gateway:9443 的 TLS/h2 验证成功，已用于本次候选包构建。
它用于 CLI 执行 SQL 时验证 Gateway 的 TLS 证书，将作为 `gateway-ca.pem` 随完整原生包分发。
CLI 安装包从 npm registry 下载。Console/Gateway CA 用于后续管理和数据连接，CA 不是账号或实例访问 Token。

## 入口与制品就绪后的安装验收

下面是需要实际完成的检查，不是已经验证的 WorkBuddy 点击说明；客户端入口与截图将在测试通道可用后补齐。

1. 在平台提供的真实入口找到 Tiana Cloud，执行安装/连接；CLI 由 Connector 自动准备，最终用户无需安装编译工具。
2. 首次授权故意等待至少 15 秒再在浏览器批准。确认 WorkBuddy 没有提前终止认证，成功后显示已连接。
3. 确认两个 Skills 已加载，并在**新聊天的命令执行环境**检查：

   ```sh
   tiana version
   tiana verify-install --json
   tiana auth status --json
   ```

   预期版本为 0.2.0、helper contract 为 3，安装检查成功。auth status 只检查本地登录状态，不证明服务端仍接受凭据。
4. 在新聊天中逐项发送以下口令；记录实际实例 ID，不让模型输出 Token：

   > 创建一个名为 wb-demo 的 SQLite 实例。
   > 查看刚创建实例的表结构。
   > 新建 notes 表，字段为 id INTEGER PRIMARY KEY、title TEXT NOT NULL。
   > 插入“你好，O'Reilly”和“第二条”两条记录，查询并显示结果。
   > 把第一条记录更新为“已更新”，查询确认。
   > 删除第二条记录，查询确认只剩 id=1、title=已更新。

   创建返回 `credential_saved=true` 后才能进行 SQL。如果存在同名实例，先明确使用哪个完整 ID；不要为了演示删除已有表或实例。
5. 重开聊天、重启 WorkBuddy 后再读取同一实例，确认无需重新复制 Token。继续完成验收表中的多实例、重连、撤销与中断场景。

## 出错时如何继续

| 情况 | 操作 |
| --- | --- |
| 找不到 tiana 或安装检查失败 | 回传 WorkBuddy 安装日志和 `verify-install` 结果；核对完整包、下载及聊天 PATH，不靠单装 Skill 补齐 |
| 管理登录失效 | 在 WorkBuddy 重新连接 Tiana；完成浏览器授权后继续原任务 |
| 创建实例或创建凭据中断 | 保留 request_id；用 `tiana requests resume REQUEST_ID --json` 恢复原任务，不重复创建实例 |
| Token 已创建但原值无法取回 | 保留原实例；用户同意后为该实例创建并保存替换凭据 |
| SQL_OUTCOME_UNKNOWN | 写入可能已经提交；用实际记录 ID 或业务键只读核对，不自动重放写入 |
| SQL 凭据缺失或失效 | 确认选对实例，再按用户批准补充凭据；不要仅为诊断 SQL 执行 logout |

回传错误码、实例/任务 ID 和脱敏日志即可，不回传 Token、登录凭据文件或完整环境变量。
终端和聊天共用凭据与任务恢复流程；断开/退出会清理当前账号的本地登录和已登记实例凭据。

## 使用边界

当前使用 Tiana 账号的默认 Tenant。SQL 每次执行一条语句并使用独立连接，不能跨命令使用 BEGIN/COMMIT。
凭据由 CLI 的系统凭据存储或既有文件后端管理；本轮 Mac 离线测试使用临时文件后端，Keychain 和真实客户端仍需实测。
InstanceToken 原值只在创建时返回给 CLI 并保存，不能从服务端重新读回；不要要求模型读取或手工拼接凭据。

构建者需要源码和工具链时，另见 [macOS 构建交接](workbuddy-macos-build-handoff.md)；这不是最终用户安装流程。
