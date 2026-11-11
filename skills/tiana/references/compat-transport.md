# 数据连接失败时尝试兼容传输

先按各技能的标准命令执行。SQLite、Git、Web 发布或 Function 源码传输遇到连接断开、握手失败、连接超时等数据连接错误时，可尝试单次命令的 `--transport compat`。部分 Agent 环境不支持标准连接中的 HTTP CONNECT；报错可能只表现为 EOF 或 reset，不必等到错误明确提到 CONNECT。

1. 保留原实例、Endpoint、分支、账号和操作参数。先看错误是否已明确属于登录、权限、证书、配额、SQL 或应用业务问题；这些错误按原流程处理。
2. 执行 `tiana --help` 确认当前安装支持 `--transport`。参数放在产品命令之前；无需配置代理地址、代理密码或环境变量。旧 CLI 不支持时，按安装更新流程取得支持版本，不能假称已启用。
3. 优先用同一目标的只读命令尝试兼容连接。成功后，本任务访问该目标的数据命令可显式带上参数；CLI 不会自动选择或切换模式。兼容尝试仍失败时，保留两次错误，按实际原因排查，不循环重试。

```sh
tiana --transport compat sqlite shell INSTANCE -e 'SELECT 1'
tiana --transport compat git ls-remote origin
```

Git 保持原 remote 和参数，支持直接 `clone`、`fetch`、`pull`、`push`、`ls-remote`、`submodule` 子命令，例如 `tiana --transport compat git push origin main`。Git 参数仍归 Git 解析；无需 `git run --`，也无需改写 remote URL。Git 来源应为原本使用的 Tiana 仓库；此选项只改变 Tiana Endpoint 连接。

写 SQL、push、发布等操作在断线前可能已成功。先按原流程核对结果，再决定是否执行写操作：SQL 查询目标状态；Git 查询实际 push 目标的远端 ref（`git remote get-url --push REMOTE`，多个 push URL 用 `--all` 分别核对），不要假定 fetch URL 与 push URL 相同；Web/Function 保留原回执、请求 ID 和源码提交，查询原操作。不能因换传输就重放结果未知的写入。

兼容参数覆盖内置 SQLite shell、直接 Git 子命令、Web 的 Gateway 发布/状态查询及 Function 源码数据传输。管理 API、对象存储下载和更新检查沿用原网络方式；`connect` 外部客户端及其 WebSocket 模式保持原用法。兼容方式仍访问原 Endpoint，保留原认证和证书校验；是否改善当前沙盒连接，以实际尝试结果为准。
