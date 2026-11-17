# API 接入与授权链路

本包接入 Tiana Cloud，CLI 为 {{CLI_VERSION}}，Skills 为 {{SKILLS_VERSION}}。

## 产品与 API 的关系

千问通过本地原生 CLI 入口调用 Tiana。入口与 CLI 核心从 `github.com/tianacloud/cli` 的同一个稳定版本构建；Skills 从 `@tianacloud/agent-skills` 的指定发行版原样收集。安装包将它们整合到一个 Tiana Cloud 连接器中。

默认管理入口为 `https://console.tianacloud.com`，CLI 通过该入口的管理 API 执行账号及空间操作、创建和管理产品资源。SQLite、Git、Web 发布等数据操作使用 Tiana 返回的目标连接地址与相应凭据。具体资源地址由服务返回，不把所有业务请求固定到管理域名。

公开文档入口：

- [Agent Skills](https://console.tianacloud.com/docs/agent-skills)：官网提供的软件包名称和安装方式，以及浏览器登录要求。
- [CLI 安装与登录](https://console.tianacloud.com/docs/cli)：命令行使用与登录流程。
- [API 鉴权](https://console.tianacloud.com/docs/management-api-auth)：管理 API 的鉴权方式。
- [使用条款](https://console.tianacloud.com/docs/terms-of-use)：Tiana 官网、控制台、API、CLI、SDK 等服务的适用范围及账号责任。

## 用户账号授权流程

1. 千问调用入口的 `auth init`；入口转为 CLI 浏览器登录并等待结果。
2. CLI 发起 Tiana 登录授权事务并打开浏览器，用户在 Tiana 登录页面完成登录及授权。千问入口等待登录结果；登录未完成时不返回授权成功。
3. CLI 完成授权结果查询，并在本地管理自己的账号凭据；本包不包含用户账号凭据或预置访问 Token。
4. 千问调用 `auth show --status` 检查当前账号状态。入口将其转为账号检查，正常未登录状态返回 `{"status":"unauthorized"}`；操作错误通过非零退出和错误信息报告。
5. 后续命令在用户账号、空间及目标凭据允许的范围内执行。`identity whoami` 提供非密钥身份信息；`auth logout` 执行退出登录。

上述是用户对账号访问的授权。它与“公司允许某主体提交和分发连接器”的原厂授权是两条独立链路；公司签章声明见 [确认函草稿](04-原厂确认函-待盖章.md)。

登录相关管理 API 包括创建事务 `POST /api/v1/auth/transactions`、查询服务端返回的事务 poll 路径、兑换凭据 `POST /api/v1/auth/token`，以及账号刷新和退出接口。CLI 负责这些请求；千问通过本地入口完成登录，不在包中填入应用密钥或用户 Token。

## 审核时可检查的证据

- 核对连接器清单版本 {{SKILLS_VERSION}}，及 `tiana version` 的 CLI 版本 {{CLI_VERSION}}。
- `tiana version --json` 的 `data.default_acquisition_source` 应为本渠道的 `qwenwork`。
- 使用测试账号完成登录、状态检查、授权范围内的资源操作与退出；截图隐藏令牌、授权码和用户隐私。
- 查阅本次 ZIP 旁的 `.build.json` 和 `.zip.sha256`，核对源包完整性、源码版本与最终归档摘要。它们证明构建来源和归档一致性，不是企业权属证明。
