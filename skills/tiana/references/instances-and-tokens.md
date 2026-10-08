# 实例与凭据

实例 ID 标识数据库或 Git 资源；Endpoint ID 标识已发布的连接入口。名称可重复，后续操作应记录并使用完整实例 ID。Endpoint 的主机与端口以 MGR 返回的连接信息为准。

`sqlite/git create` 默认只报告受理。`--wait` 成功才表示原始资源已达到可用状态；创建不再自动签发首个实例 Token，也不保存 `instance-tokens.json`。CLI 连接使用已有账号登录态；正常 access token 过期由鉴权组件刷新，refresh token 失效或刷新结果不明时重新登录并继续使用原资源。

账号凭据由 CLI 的安全存储管理。不要在聊天、源码、构建文件或 Git URL 中复制凭据。缺少权限、配额超限与登录失效是不同问题，按实际错误处理。

浏览器应用通过 `window.tiana.connection()` 获取连接元信息，通过共享的 `window.tiana.auth` 获取动态 access token。应用不使用 `connection.tianaToken` 快照、不传静态 Token，也不回退到实例 Token。

CLI 本地预览优先复用已有 CLI 登录，通过一次性本地启动链接授权浏览器；没有可用账号时才走独立浏览器登录。刷新和持久化由 CLI/SDK 负责，refresh token 不交给页面。access token 具有账号/租户级权限，清单中的数据库 ID 不收窄凭据权限。

托管应用使用动态账号鉴权 provider。以目标环境实际返回的能力判断就绪状态；能力缺失时报告具体结果，SDK 或 CLI 安装成功不能代替托管运行时核验。

SDK 要求、调用示例和失败恢复见 [JavaScript 数据库连接](../../tiana-sqlite/references/js-sdk.md)。skills 不读取或保存 refresh token，不自行调用刷新接口，也不从 CLI 凭据文件向浏览器复制凭据。登录与刷新由 CLI/SDK 或可信运行时代理负责。

浏览器注销、关闭本地预览会话不应被视为已交付 access token 立即撤销的证明。凭据的失效、撤销由服务端机制决定。
