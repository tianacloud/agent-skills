# Tiana WorkBuddy Connector / MCP Server 详细设计

## 1. 交付目标

本方案交付一个可被 WorkBuddy 安装的 Tiana Cloud Connector。安装后，用户可以用自然语言
完成以下操作：

- 列出 Tiana 实例；
- 查看一个实例的当前状态和连接地址；
- 创建 SQLite 实例并取得首枚 `default` 连接 Token；
- 修改实例名称、标签、备注和空闲超时；
- 为已有实例创建追加或替代连接 Token。

本方案同时交付 WorkBuddy 连接 Tiana 所需的 OAuth 登录闭环：

- WorkBuddy 自动发现 Tiana Authorization Server，并向其注册为 OAuth public client；
- 浏览器打开 Tiana 授权页；
- 用户通过现有 Tiana 账号体系登录，未注册用户可以完成注册；
- 用户授权后，WorkBuddy 使用 Authorization Code + PKCE 获取 Tiana MCP access token 和
  refresh token；
- access token 到期后由 WorkBuddy 使用 refresh token 自动续期。

交付内容由五部分组成：

1. 新增独立部署的 `tiana-mcp` 服务，提供 `/mcp` resource server；
2. 现有 MGR Auth 增加 WorkBuddy 所需的 OAuth Authorization Server 能力；
3. 现有 MGR 增加供 `tiana-mcp` 使用的内部 Token introspection 和业务接口；
4. 现有 Web 增加 Tiana OAuth 授权页，以及登录、首次注册和授权完成后的回跳；
5. 一个包含连接配置和现有 Tiana Skills 的 WorkBuddy Connector ZIP。

`tiana-mcp` 是一个新的 Deployment、进程和 Kubernetes Service，但不拥有数据库或其他持久化
存储。OAuth 继续由现有 MGR Auth 实现，Connector 和 Skills 是安装包内容。

## 2. 设计结论

| 项目 | 决定 |
| --- | --- |
| MCP transport | Streamable HTTP |
| MCP endpoint | `https://mcp.service.internal.tiana.com/mcp` |
| Connector 认证 | OAuth 2.1 Authorization Code + PKCE |
| 新用户入口 | WorkBuddy 连接时打开 Tiana 登录/注册页 |
| MCP 实现位置 | 独立 `tiana-mcp` 服务 |
| MCP 业务调用 | 调用现有 MGR 内部接口 |
| MCP 新增持久化 | 无独立存储；OAuth 数据进入 MGR Auth MySQL |
| OAuth 持久化 | 需要开发；新增数据表放在 MGR Auth 现有 MySQL |
| 首版 tools 数量 | 5 |
| 首版数据库引擎 | `sqlite` |
| 首版分支管理 | 不包含；当前仍为未发布设计 |
| CLI 依赖 | 无 |

## 3. Neon 与 Turso 的参考结论

本方案只借鉴它们已经验证过的交互形态，不照搬其资源模型。

- Tiana 当前 Web/CLI 的“创建实例”向导本身是两个 MGR 操作：先创建实例，再立即签发首枚
  `default` Token。MCP 的 `create_instance` 对用户保留这一完整任务语义，不要求用户手动调用
  第二个 tool 才得到可连接的实例。
- Neon 将 operation-backed write 封装在用户任务型 tool 内，不要求模型操作底层 operation。
  Tiana MCP 同样在一个用户任务型 tool 内编排上述两个 MGR 操作。Neon 的
  `get_connection_string` 只用于参考凭据的一次性返回方式，不是 Tiana Token 生命周期的直接
  依据。
- Neon MCP 不提供 API key 清单 tool。Turso Cloud 把建库与数据库 Token 创建分开，公开 CLI
  也以 create/invalidate 为主。`create_instance_token` 参考的是这种独立的新 Token 签发能力，
  用于已有实例的追加或替代 Token，不用于补齐刚创建实例的首枚 Token。Tiana 首版不提供
  Token inventory 和撤销 tool，它们继续由 Console 提供。
- Neon 将 API 的非 5xx 失败作为 `isError: true` 的 MCP tool result 返回，而不是把它变成
  MCP protocol error。Tiana 沿用这一行为，同时保留 Tiana 的产品错误码。
- Neon 的 secret-bearing `get_connection_string` 使用普通 tool result 返回连接字符串。
  WorkBuddy 没有单独的 secret-result 类型。Tiana 的一次性 InstanceToken 也直接作为
  `create_instance` 或 `create_instance_token` 的 tool result 返回。

参考实现：

- [Neon MCP Server](https://github.com/neondatabase/mcp-server-neon)
- [Turso Cloud CLI](https://github.com/tursodatabase/turso-cli)
- [Turso Agent Skills](https://github.com/tursodatabase/agent-skills)

## 4. 服务架构

```text
WorkBuddy
    │  Authorization: Bearer <MCP access token>
    │  POST https://mcp.service.internal.tiana.com/mcp
    ▼
tiana-mcp
    │  introspect opaque token
    ▼
MGR Auth
    │  Principal/Tenant/scope/resource
    ▼
tiana-mcp
    │  trusted internal business request
    ▼
MGR application service
    │
    └── existing Tiana control plane
```

`mcp.service.internal.tiana.com` 路由到独立 `tiana-mcp` 服务。该服务：

1. 完成 MCP `initialize`、`tools/list` 和 `tools/call`；
2. 验证 WorkBuddy 请求携带的 MCP access token；
3. 调用 MGR Auth 内部 introspection 接口，取得现有 Principal、Tenant 和产品权限；
4. 使用该授权上下文调用 MGR 内部业务接口；
5. 将结果转换为 MCP tool result。

这里的 Principal 是 MGR 账号体系中稳定的用户主体，以 `principal_id` 标识。GitHub、微信、
邮箱或手机只是登录身份，同一用户可以绑定多个身份，但它们都映射到同一个 Principal。Tenant
是资源归属边界；Principal 通过 `mgr_prod_tenant_members` 在 Tenant 中拥有角色和产品权限。
WorkBuddy 的 OAuth `client_id` 只标识客户端，不是 Principal。

`tiana-mcp` 不直接访问 MGR MySQL，也不复制 MGR 的账号、Tenant 或实例状态。MCP access token
只发送给 MGR Auth 的 introspection 接口，不作为调用 MGR 业务接口的 Bearer credential；业务
调用携带 introspection 得到的内部 Principal/Tenant 授权上下文。这样保持 MCP token 的 resource
边界，也不把它透传成另一项 API 的 access token。

MCP 使用 `mcp.service.internal.tiana.com`；数据库客户端仍通过
`<endpoint-id>.db.service.internal.tiana.com` 进入现有 Gateway。MCP tools 操作的是账号、Tenant、
实例配置和连接 Token，属于控制面请求；Gateway 继续处理数据库 Fetch、隧道、实例路由和数据
会话。

MGR 当前尚未实现 MCP OAuth Authorization Server。client registration、authorization
code 和 refresh token 的签发与持久化都属于本次新增开发，数据表放在 MGR Auth 已使用的
MySQL 中，不引入新的数据库。

## 5. MCP 服务接口

### 5.1 HTTP endpoint

```text
POST https://mcp.service.internal.tiana.com/mcp
```

`tiana-mcp` 在该路由实现 MCP Streamable HTTP transport。WorkBuddy 请求的 `Authorization`
header 只用于 MCP resource server 认证；服务通过 MGR introspection 得到授权上下文后调用
MGR 内部业务接口。

`tiana-mcp` 提供自己的 `GET /health/live` 和 `GET /health/ready`。

### 5.2 MCP server identity

`initialize` 返回：

```json
{
  "name": "tiana-cloud",
  "version": "0.1.0"
}
```

首版声明 `tools` capability，不声明 resources、prompts 或 sampling capability。

实现使用官方 [`github.com/modelcontextprotocol/go-sdk`](https://github.com/modelcontextprotocol/go-sdk)
`v1.7.0`，Streamable HTTP transport 采用 stateless 模式。

### 5.3 首次连接、注册和登录

用户不需要预先拥有 Tiana 账号，也不需要安装 CLI。首次连接流程如下：

账号创建属于浏览器授权流程，不做成 MCP tool；MCP tools 只有在 Tiana 已经建立 Principal 和
Tenant 后才能调用。

这里需要区分协议流程和 Tiana 的实现选择：

| 层次 | 内容 |
| --- | --- |
| WorkBuddy/MCP OAuth 流程 | WorkBuddy 发现 Tiana Authorization Server，以 public client 发起 Authorization Code + PKCE；Tiana Authorization Server 向 WorkBuddy 返回 code，并由 token endpoint 签发 Tiana MCP access token 和 refresh token。 |
| Tiana 实现选择 | MCP resource server 是独立 `tiana-mcp` 服务；Authorization Server 放在现有 MGR Auth；`/oauth/authorize` 检查现有 Tiana Web session，未登录时复用现有账号登录/注册能力。GitHub 只是部署已启用时可选的一种 Tiana 登录方式。 |

MCP 和 WorkBuddy 不规定 Tiana 必须使用 GitHub，也不接收 GitHub token。它们只要求用户在
Tiana Authorization Server 的浏览器授权流程中完成身份认证和授权。因此，不应把这条链路
表述为“WorkBuddy 使用 GitHub OAuth 登录”：WorkBuddy 使用的是 Tiana OAuth，GitHub 登录仅
发生在 Tiana 内部的用户认证环节。

```text
用户在 WorkBuddy 安装 Tiana Connector 并点击连接
  → WorkBuddy 请求 /mcp，收到 401 和 OAuth resource metadata 地址
  → WorkBuddy 读取 MCP resource metadata 和 Tiana authorization server metadata
  → WorkBuddy 动态注册 public client
  → WorkBuddy 打开 Tiana /oauth/authorize
  → 已有账号：登录
  → 没有账号：进入现有邮箱、手机或社交注册流程
  → 注册成功后回到 /oauth/authorize
  → 用户确认授权
  → Tiana 将 authorization code 返回 WorkBuddy callback
  → WorkBuddy 使用 PKCE code_verifier 换取 access token 和 refresh token
  → WorkBuddy 自动携带 access token 调用 /mcp
```

MCP protected resource metadata 由 `tiana-mcp` 提供：

```text
GET https://mcp.service.internal.tiana.com/.well-known/oauth-protected-resource
```

首次未携带 Token 请求 `/mcp` 时，`tiana-mcp` 返回：

```http
HTTP/1.1 401 Unauthorized
WWW-Authenticate: Bearer resource_metadata="https://mcp.service.internal.tiana.com/.well-known/oauth-protected-resource", scope="tiana:manage"
```

WorkBuddy 优先从 `WWW-Authenticate` 的 `resource_metadata` 参数取得 metadata URL；若响应头中
没有该参数，MCP 客户端也可以按规范尝试 well-known URL。读取 protected resource metadata 后，
WorkBuddy 从 `authorization_servers` 数组取得
`https://console.service.internal.tiana.com`，再读取该 issuer 的 Authorization Server metadata。
因此 Connector 的 `mcp.json` 只需配置 MCP URL，不需要硬编码 authorize 或 token endpoint。

authorization server metadata 和 OAuth endpoints 使用现有 Console 公共入口：

```text
GET  https://console.service.internal.tiana.com/.well-known/oauth-authorization-server
POST https://console.service.internal.tiana.com/oauth/register
GET  https://console.service.internal.tiana.com/oauth/authorize
POST https://console.service.internal.tiana.com/oauth/token
```

其中 `/oauth/authorize` 是 Web 页面；metadata、client registration、authorization code 和
token 签发由 MGR Auth 实现，并通过 Console 入口暴露。Web 在用户批准授权后调用 MGR Auth
完成 authorization code 签发。

Protected resource metadata 返回：

```json
{
  "resource": "https://mcp.service.internal.tiana.com/mcp",
  "authorization_servers": [
    "https://console.service.internal.tiana.com"
  ],
  "scopes_supported": ["tiana:manage"],
  "bearer_methods_supported": ["header"]
}
```

Authorization Server metadata 返回：

```json
{
  "issuer": "https://console.service.internal.tiana.com",
  "authorization_endpoint": "https://console.service.internal.tiana.com/oauth/authorize",
  "token_endpoint": "https://console.service.internal.tiana.com/oauth/token",
  "registration_endpoint": "https://console.service.internal.tiana.com/oauth/register",
  "response_types_supported": ["code"],
  "grant_types_supported": ["authorization_code", "refresh_token"],
  "token_endpoint_auth_methods_supported": ["none"],
  "code_challenge_methods_supported": ["S256"],
  "scopes_supported": ["tiana:manage"]
}
```

WorkBuddy 调用 `/oauth/register` 注册 public client，请求包含其 callback：

```json
{
  "client_name": "WorkBuddy",
  "redirect_uris": [
    "workbuddy://workbuddy/mcp/connector%3Atiana-cloud/oauth/callback"
  ],
  "grant_types": ["authorization_code", "refresh_token"],
  "response_types": ["code"],
  "token_endpoint_auth_method": "none"
}
```

MGR 返回 `client_id` 并原样返回 `redirect_uris`。随后 WorkBuddy 打开的 authorization request
至少携带：

```text
response_type=code
client_id=<registered client id>
redirect_uri=workbuddy://workbuddy/mcp/connector%3Atiana-cloud/oauth/callback
code_challenge=<PKCE challenge>
code_challenge_method=S256
state=<WorkBuddy state>
scope=tiana:manage
resource=https://mcp.service.internal.tiana.com/mcp
```

`/oauth/authorize` 检查现有 Tiana Web session。匿名用户进入 `/login`；登录页的“注册”入口
保留 OAuth authorize request。注册完成并建立 Web session 后，Web 返回原 authorize request，
不会把用户送到普通 Console 首页。

注册方式直接使用 `GET /mgr/v1/auth/capabilities` 当前返回的部署能力：邮箱、手机和已配置的
社交登录提供方。注册本身继续使用现有 Tiana 注册 API，不在 MCP Server 中实现第二套账号
系统。

WorkBuddy callback 使用：

```text
workbuddy://workbuddy/mcp/connector%3Atiana-cloud/oauth/callback
```

MGR 接受 WorkBuddy 作为不持有 client secret 的 public client，并要求 PKCE S256。签发的
OAuth access token 映射到现有 Principal、Tenant 和产品权限，并绑定 resource
`https://mcp.service.internal.tiana.com/mcp`。`tiana-mcp` 通过 MGR Auth introspection 验证 token
并建立请求授权上下文，不会把该 token 转发给 MGR 业务 API。GitHub access token 也不会返回
WorkBuddy 或用作 MCP access token。

WorkBuddy 使用 authorization code 换 token 时提交：

```text
grant_type=authorization_code
client_id=<registered client id>
code=<one-time authorization code>
redirect_uri=<same registered callback>
code_verifier=<PKCE verifier>
resource=https://mcp.service.internal.tiana.com/mcp
```

MGR 返回：

```json
{
  "access_token": "<opaque MCP access token>",
  "token_type": "Bearer",
  "expires_in": 3600,
  "refresh_token": "<rotating refresh token>",
  "scope": "tiana:manage"
}
```

Token 由 WorkBuddy 内置的客户端侧 OAuth 管理器持有，并在每个 `/mcp` 请求中通过
`Authorization: Bearer <access_token>` 发送。WorkBuddy 公开文档没有说明 MCP OAuth Token
具体保存在哪个文件、数据库或系统凭据仓库中，本方案不依赖其物理存储位置；用户自填 Token
模式文档中的 `~/.workbuddy` 示例也不能据此当作 MCP OAuth 的存储合同。

MGR 在 token response 中通过 `expires_in` 告知 access token 的有效期；`tiana-mcp` 在
introspection 返回 inactive 时向 WorkBuddy 返回 `401`。WorkBuddy 官方只承诺 access token 过期时自动使用 refresh token
调用同一个 token endpoint 并重试原 MCP 请求，没有公开它是提前按本地过期时间刷新，还是在
首次收到 `401` 后刷新。Tiana 服务端同时正确提供 `expires_in`、`401` 和 refresh-token grant，
不依赖客户端采用其中某一种判断方式。刷新成功时 MGR 消费旧 refresh token，并返回新的
access token 和 refresh token；WorkBuddy OAuth 管理器用新值替换旧值。若 refresh token 也已
过期或失效，token endpoint 返回 OAuth `invalid_grant`，用户需要重新完成授权。

### 5.4 调试阶段的网络方向

本方案使用 WorkBuddy 客户端内置的 MCP OAuth，不使用 WorkBuddy 的 `server-side` 或
`gateway` 托管认证模式。流程中没有 WorkBuddy 云服务向 Tiana 服务端发起 OAuth callback：

| 请求 | 发起方 | 目标 |
| --- | --- | --- |
| MCP 请求和 protected resource metadata | 用户机器上的 WorkBuddy | `tiana-mcp` |
| Authorization Server metadata、client registration、token exchange 和 token refresh | 用户机器上的 WorkBuddy | Tiana MGR Auth |
| 登录、注册和授权页面访问 | 用户机器上的浏览器 | Tiana Console Web |
| 授权完成回跳 | 用户浏览器 | `workbuddy://...` 私有协议，由本机 WorkBuddy 接收 |

因此，调试阶段可以继续使用内网域名，但运行 WorkBuddy 的用户机器必须能够解析并访问
`mcp.service.internal.tiana.com` 和 `console.service.internal.tiana.com`，同时信任它们的 HTTPS
证书。若用户机器不在内网或未连接 VPN，连接会在 MCP/OAuth metadata 请求或浏览器登录页面
处失败；这不是服务端 callback 不可达导致的。

### 5.5 通用 tool result

成功结果使用一个 JSON text content：

```json
{
  "content": [
    {
      "type": "text",
      "text": "{...tool-specific JSON...}"
    }
  ]
}
```

业务失败仍返回成功的 MCP JSON-RPC response，但 tool result 标记为失败：

```json
{
  "isError": true,
  "content": [
    {
      "type": "text",
      "text": "{\"error\":{\"code\":\"INSTANCE_NOT_FOUND\",\"message\":\"instance not found\",\"retryable\":false,\"request_id\":\"req-...\"}}"
    }
  ]
}
```

认证缺失或 access token 无效发生在 MCP endpoint 边界，返回 HTTP `401` 和
`WWW-Authenticate` resource metadata 引用。JSON-RPC 格式错误、
未知 method 和未知 tool 使用标准 MCP error。MGR service 返回的产品错误使用上述
`isError: true` 结果。

## 6. Tool 定义

所有 tool 名称使用 `snake_case`。下列 description、input schema 和 result shape 是首版
接口合同，实现时直接注册到 `tools/list`。

实例返回对象统一为：

```json
{
  "id": "sqlite-...",
  "display_name": "Demo",
  "labels": {"env": "dev"},
  "notes": "development database",
  "engine": "sqlite",
  "config": {"idle_timeout_ms": 60000},
  "config_revision": "1",
  "endpoint_id": "ep-...",
  "endpoint_url": "https://ep-....db.service.internal.tiana.com",
  "product_state": "ACTIVE",
  "product_revision": "1",
  "desired_state": "ENABLED",
  "observed_state": "SLEEPING",
  "last_error_code": "",
  "runtime_status_stale": false,
  "stale_reason": "",
  "created_at": "2026-09-10T00:00:00Z",
  "updated_at": "2026-09-10T00:00:00Z"
}
```

`endpoint_url` 由 MCP Server 根据 `endpoint_id` 生成，其他字段来自 MGR。空的 optional
字段可以省略。

### 6.1 `list_instances`

**Title**：List Tiana instances

**Description**：

> Lists Tiana Cloud instances visible to the current user. Use this to discover
> an instance ID before calling `get_instance`, `update_instance`, or
> `create_instance_token`. Results are paginated with at most 20 instances per page.

**Annotations**：`readOnlyHint: true`、`destructiveHint: false`、`idempotentHint: true`

**Input schema**：

```json
{
  "type": "object",
  "properties": {
    "page": {
      "type": "integer",
      "minimum": 1,
      "description": "Page number. Defaults to 1."
    },
    "page_size": {
      "type": "integer",
      "minimum": 1,
      "maximum": 20,
      "description": "Instances per page. Defaults to 20."
    }
  }
}
```

**MGR application operation**：
`application.Service.ListInstances(ctx, auth, page, pageSize)`

**Result JSON**：

```json
{
  "items": ["<instance object>"],
  "page": 1,
  "page_size": 20,
  "total": 1,
  "total_pages": 1
}
```

### 6.2 `get_instance`

**Title**：Get Tiana instance

**Description**：

> Gets the current configuration, lifecycle state, revisions, and connection endpoint
> of one Tiana Cloud instance. Call this before updating an instance so that the latest
> `product_revision` and `config_revision` are used.

**Annotations**：`readOnlyHint: true`、`destructiveHint: false`、`idempotentHint: true`

**Input schema**：

```json
{
  "type": "object",
  "properties": {
    "instance_id": {
      "type": "string",
      "description": "Opaque Tiana instance ID returned by list_instances."
    }
  },
  "required": ["instance_id"]
}
```

**MGR application operation**：
`application.Service.GetInstance(ctx, auth, instanceID)`

**Result JSON**：`<instance object>`

### 6.3 `create_instance`

**Title**：Create Tiana SQLite instance

**Description**：

> Creates a Tiana Cloud SQLite instance, issues its initial non-expiring `default`
> connection Token, and returns both. The Token is shown only in this result and must be
> saved immediately. Do not call `create_instance_token` merely to complete this flow.

**Annotations**：`readOnlyHint: false`、`destructiveHint: false`、`idempotentHint: false`

**Input schema**：

```json
{
  "type": "object",
  "properties": {
    "display_name": {
      "type": "string",
      "description": "Human-readable instance name."
    },
    "labels": {
      "type": "object",
      "additionalProperties": {"type": "string"},
      "description": "Optional labels attached to the instance."
    },
    "notes": {
      "type": "string",
      "description": "Optional user notes."
    },
    "idle_timeout_ms": {
      "type": "integer",
      "minimum": 1000,
      "maximum": 86400000,
      "description": "Optional idle timeout in milliseconds. Tiana uses the App default when omitted."
    }
  },
  "required": ["display_name"]
}
```

**MGR application operation**：

```go
created := application.Service.CreateInstance(ctx, auth, application.CreateInstanceInput{
    IdempotencyKey: generatedInstanceUUID,
    DisplayName:    input.DisplayName,
    Labels:         input.Labels,
    Notes:          input.Notes,
    Engine:         "sqlite",
    Config:         domain.PublicConfig{IdleTimeoutMS: input.IdleTimeoutMS},
})

initialToken := production.Service.CreateToken(ctx, auth, production.TokenCreateInput{
    InstanceID: created.Instance.ID,
    IdempotencyKey: generatedTokenUUID,
    Request: productwire.CreateTokenRequest{
        RequestID: generatedTokenUUID,
        Name:       "default",
        ExpiresAt:  productwire.InstanceTokenNoExpiry,
    },
})
```

这与现有 Web/CLI 创建向导一致：实例创建和首枚 Token 签发仍是两个独立、可幂等的 MGR
操作，只由 MCP handler 编排为一个用户任务。两个操作使用不同 UUID；同一个 handler 内重试
某一步时复用该步的 UUID。MCP Server 不把 `Idempotency-Key` 暴露为模型参数。第二步失败时
不删除已经创建的实例；实例保持锁定，用户可随后调用 `create_instance_token` 签发替代 Token。

**Result JSON**：

```json
{
  "instance": "<instance object>",
  "initial_token": {
    "token_id": "tok-...",
    "token": "<one-time InstanceToken>",
    "name": "default",
    "expires_at": "9999-12-31T23:59:59.999Z",
    "effective_no_later_than": "2026-09-10T00:00:30Z"
  }
}
```

MCP Server 不记录该 tool 的 result body。

### 6.4 `update_instance`

**Title**：Update Tiana instance

**Description**：

> Updates editable metadata or the idle timeout of a Tiana Cloud instance. Call
> `get_instance` first and pass its current revisions. Pass `config_revision` only when
> changing `idle_timeout_ms`. If a revision conflict occurs, read the instance again and
> ask the user before reapplying the change.

**Annotations**：`readOnlyHint: false`、`destructiveHint: false`、`idempotentHint: true`

**Input schema**：

```json
{
  "type": "object",
  "properties": {
    "instance_id": {
      "type": "string",
      "description": "Opaque Tiana instance ID."
    },
    "product_revision": {
      "type": "string",
      "description": "Current product_revision returned by get_instance."
    },
    "display_name": {
      "type": "string",
      "description": "Replacement display name."
    },
    "labels": {
      "type": "object",
      "additionalProperties": {"type": "string"},
      "description": "Complete replacement label map."
    },
    "notes": {
      "type": "string",
      "description": "Replacement notes."
    },
    "idle_timeout_ms": {
      "type": "integer",
      "minimum": 1000,
      "maximum": 86400000,
      "description": "Replacement idle timeout in milliseconds."
    },
    "config_revision": {
      "type": "string",
      "description": "Current config_revision. Required when idle_timeout_ms is present."
    }
  },
  "required": ["instance_id", "product_revision"]
}
```

调用必须至少包含 `display_name`、`labels`、`notes`、`idle_timeout_ms` 中的一项。

**MGR application operation**：

```go
application.Service.EditInstance(ctx, auth, input.InstanceID, application.EditInstanceInput{
    ExpectedProductRevision: parseUint64(input.ProductRevision),
    DisplayName:             input.DisplayName,
    Labels:                  input.Labels,
    Notes:                   input.Notes,
    Config:                  publicConfigWhenPresent(input.IdleTimeoutMS),
    ExpectedConfigRevision:  input.ConfigRevision,
})
```

只发送用户在 tool input 中提供的可编辑字段。设置 `idle_timeout_ms` 时发送 `config` 和
`expected_config_revision`；否则两者都不发送。

**Result JSON**：`<instance object>`

### 6.5 `create_instance_token`

**Title**：Create an additional Tiana instance Token

**Description**：

> Creates an additional or replacement one-time connection Token for an existing Tiana
> Cloud instance. A successful `create_instance` already returns the initial `default`
> Token, so use this tool only when the user asks for another Token. The returned Token is
> shown only in this result; use it with the returned endpoint URL and save it immediately.

**Annotations**：`readOnlyHint: false`、`destructiveHint: false`、`idempotentHint: false`

**Input schema**：

```json
{
  "type": "object",
  "properties": {
    "instance_id": {
      "type": "string",
      "description": "Opaque Tiana instance ID."
    },
    "name": {
      "type": "string",
      "description": "Human-readable purpose of the Token, for example workbuddy."
    },
    "expires_at": {
      "type": "string",
      "format": "date-time",
      "description": "Token expiration time. Use 9999-12-31T23:59:59.999Z only when the user explicitly requests no expiration."
    }
  },
  "required": ["instance_id", "name", "expires_at"]
}
```

**MGR application operation**：

```go
production.Service.CreateToken(ctx, auth, production.TokenCreateInput{
    InstanceID: input.InstanceID,
    IdempotencyKey: generatedUUID,
    Request: productwire.CreateTokenRequest{
        RequestID: generatedUUID,
        Name:       input.Name,
        ExpiresAt:  input.ExpiresAt,
    },
})
```

当前 MGR Token 创建 API 在 Token 提交完成后返回结果，因此 MCP Server 直接返回该结果，
不发布或调用单独的 operation tool。

**Result JSON**：

```json
{
  "instance_id": "sqlite-...",
  "endpoint_id": "ep-...",
  "endpoint_url": "https://ep-....db.service.internal.tiana.com",
  "token_id": "tok-...",
  "token": "<one-time InstanceToken>",
  "name": "workbuddy",
  "expires_at": "2026-10-10T00:00:00Z",
  "effective_no_later_than": "2026-09-10T00:00:30Z"
}
```

MCP Server 不记录该 tool 的 result body。

## 7. WorkBuddy Connector 包

### 7.1 目录

```text
connectors/
└── tiana-cloud/
    ├── connector-meta.json
    ├── icon.svg
    ├── mcp.json
    └── skills/
        ├── tiana/
        └── tiana-sqlite/
```

Connector 复用本仓库的 `tiana` 和 `tiana-sqlite` Skills。构建脚本在打包时复制它们，
源码不维护第二份。

### 7.2 `connector-meta.json`

```json
{
  "name": "Tiana Cloud",
  "name_zh": "Tiana Cloud",
  "name_en": "Tiana Cloud",
  "description": "Create, inspect, and configure Tiana Cloud serverless SQLite instances.",
  "description_zh": "创建、查看和配置 Tiana Cloud serverless SQLite 实例。",
  "description_en": "Create, inspect, and configure Tiana Cloud serverless SQLite instances.",
  "examples_zh": [
    "列出我的 Tiana 实例",
    "创建一个名为 demo 的 SQLite 实例",
    "给 demo 实例创建一个一个月后过期的连接 Token"
  ],
  "examples_en": [
    "List my Tiana instances",
    "Create a SQLite instance named demo",
    "Create a connection Token for demo that expires in one month"
  ],
  "type": "mcp",
  "source": "tiana-cloud",
  "version": "0.1.0",
  "minWorkbuddyVersion": "4.24.0"
}
```

### 7.3 `mcp.json`

WorkBuddy 配置中的 transport 名称使用 `streamableHttp`：

```json
{
  "mcpServers": {
    "tiana": {
      "type": "streamableHttp",
      "url": "https://mcp.service.internal.tiana.com/mcp",
      "timeout": 30000
    }
  }
}
```

Connector 不声明 `auth_mode`，也不包含 `token-schema.json`。WorkBuddy 连接远程 MCP 时根据
服务返回的 `401` 和 OAuth metadata 自动进入浏览器授权流程。

## 8. 工程设计

MCP Server 独立成仓，OAuth 和 MGR 内部适配器进入现有 MGR：

```text
tiana-mcp/
├── cmd/tiana-mcp/
│   └── main.go
├── internal/
│   ├── mcphttp/
│   │   ├── server.go
│   │   ├── tools.go
│   │   └── results.go
│   └── mgrclient/
│       └── client.go
└── go.mod

mgr/
├── internal/
│   ├── api/
│   │   └── mcpinternal/
│   │       └── server.go
│   └── auth/
│       ├── oauth.go
│       └── oauth_store.go
└── go.mod

web/
└── src/pages/auth/
    └── OAuthAuthorizePage.tsx
```

- `tiana-mcp/internal/mcphttp`：protected resource metadata、Streamable HTTP transport、
  五个 tool 定义和 handler。
- `tiana-mcp/internal/mgrclient`：调用 MGR token introspection 和内部业务接口。
- `mgr/internal/api/mcpinternal`：把内部 HTTP 请求映射到现有 MGR application service。
- `auth/oauth.go`：client registration、authorization code、PKCE、access/refresh token。
- `auth/oauth_store.go`：MGR Auth MySQL 的 OAuth 持久化接口。
- `OAuthAuthorizePage.tsx`：登录、注册、授权确认和回跳 WorkBuddy。

官方 MCP Go SDK 加入 `tiana-mcp` 的 `go.mod`。MGR 不依赖 MCP SDK。

### 8.1 请求处理

```text
tools/call
  → resolve tool handler
  → read Authorization header
  → call MGR Auth introspection
  → resolve Principal/Tenant into AuthContext
  → call MGR internal business API
  → add endpoint_url when endpoint_id exists
  → encode JSON text result
```

`create_instance` 为实例创建和首枚 Token 签发分别生成一个 UUID；
`create_instance_token` 生成一个 UUID。每个 UUID 作为对应 MGR 操作的
`Idempotency-Key`，Token 操作的 UUID 同时作为 `request_id`。同一个 handler 内重试某一步时
复用该步的 UUID。

### 8.2 服务配置

```text
# tiana-mcp
TIANA_MCP_LISTEN_ADDR=:8080
TIANA_MCP_RESOURCE=https://mcp.service.internal.tiana.com/mcp
TIANA_MGR_INTERNAL_URL=http://tiana-mgr.tiana-mgr.svc.cluster.local
TIANA_ENDPOINT_SUFFIX=db.service.internal.tiana.com

# MGR
TIANA_OAUTH_ISSUER=https://console.service.internal.tiana.com
TIANA_MCP_RESOURCE=https://mcp.service.internal.tiana.com/mcp
```

MGR 继续使用现有 MySQL。`tiana-mcp` 不配置数据库；用户 access token 逐请求从
`Authorization` header 取得，不进入服务配置。

## 9. 实施任务

### 9.1 `tiana-mcp`

1. 建立独立 Go 服务并接入官方 `github.com/modelcontextprotocol/go-sdk v1.7.0`，启用 stateless
   Streamable HTTP transport。
2. 提供 `/mcp`、protected resource metadata 和健康检查。
3. 通过 MGR Auth introspection 验证 MCP access token 的 OAuth client、有效期、scope 和
   resource。
4. 注册本文定义的五个 tools。
5. handler 使用解析出的授权上下文调用 MGR 内部业务接口。
6. 实现 result/error 转换、create tool UUID 和单次调用重试语义。
7. 为 Instance 结果补充 `endpoint_url`。

### 9.2 MGR Auth（新增开发）

现有 MGR Auth 已具备账号注册、登录、Principal/Tenant 和 Web/CLI opaque session，但没有
WorkBuddy MCP OAuth 所需的 Authorization Server 能力。本节全部属于新增开发。

按照标准 OAuth 角色，WorkBuddy 是 public OAuth client，`tiana-mcp` 是 protected resource，
Tiana Authorization Server 负责签发 code 和 Tiana MCP token。本方案选择由现有 MGR Auth
承担 Tiana Authorization Server，而不是协议要求 Authorization Server 必须部署在 MGR。

在 `/oauth/authorize` 内，MGR Auth 先检查现有 Tiana Web session；没有 session 时进入现有
登录/注册流程。GitHub、WeChat、邮箱和手机都是 Tiana 现有账号体系可提供的认证方式，具体
显示哪些方式以当前部署的 auth capabilities 为准。若选择 GitHub，MGR 仍是 GitHub 的 OAuth
client；GitHub 登录完成后只建立 Tiana 用户身份和 Web session。随后 Tiana Authorization
Server 才向 WorkBuddy 签发 Tiana authorization code 和 MCP token。两个 OAuth 关系彼此独立，
GitHub code/token 不会交给 WorkBuddy。

1. 增加 authorization server metadata、dynamic client registration、authorize 和 token
   endpoints。
2. Dynamic Client Registration 接受 WorkBuddy public client，并保存 `client_id` 和精确的
   `redirect_uris`。
3. Authorization Code 绑定 client、redirect URI、当前 Principal/Tenant、scope 和 PKCE S256
   challenge；有效期 10 分钟，只能消费一次。
4. Token endpoint 校验 `code_verifier` 后签发 access token 和 refresh token。
5. Access token 和 refresh token 使用 opaque 随机值，只持久化摘要，并绑定 OAuth client、
   Principal/Tenant、成员权限、resource 和 scope。
6. Refresh token 成功使用后标记为已消费，同时签发下一组 access token 和 refresh token。
7. 首版只提供 `tiana:manage` scope，对应本文五个 tools。

OAuth 不新建账号或复制 GitHub 身份。用户身份继续来自现有 `mgr_prod_principals`，Tenant 和
权限继续来自 `mgr_prod_tenants`、`mgr_prod_tenant_members`。新增 OAuth 持久数据放在 MGR
Auth 现有 MySQL 中，建议使用以下三个表：

```text
mgr_prod_oauth_clients
mgr_prod_oauth_authorization_codes
mgr_prod_oauth_token_sets
```

三类记录都以 MySQL 为权威存储。`authorization_codes` 虽然只有约 10 分钟生命周期，但需要在
多个 MGR 副本间原子地完成“未消费 → 已消费”，MySQL 可以直接使用条件更新实现；过期记录按
`expires_at` 清理。当前 MGR 没有自己的 Redis，Gateway Redis 也不属于 MGR，因此本方案不为
这批低频 OAuth 状态增加新的 Redis 依赖。

数据模型示例：

```sql
CREATE TABLE mgr_prod_oauth_clients (
    client_id VARCHAR(128) PRIMARY KEY,
    client_name VARCHAR(255) NOT NULL,
    redirect_uris JSON NOT NULL,
    created_at DATETIME(6) NOT NULL
);

CREATE TABLE mgr_prod_oauth_authorization_codes (
    code_hash CHAR(64) PRIMARY KEY,
    client_id VARCHAR(128) NOT NULL,
    principal_id VARCHAR(128) NOT NULL,
    tenant_id VARCHAR(128) NOT NULL,
    redirect_uri VARCHAR(2048) NOT NULL,
    scope VARCHAR(255) NOT NULL,
    resource VARCHAR(2048) NOT NULL,
    code_challenge VARCHAR(128) NOT NULL,
    auth_time DATETIME(6) NOT NULL,
    expires_at DATETIME(6) NOT NULL,
    consumed_at DATETIME(6) NULL,
    created_at DATETIME(6) NOT NULL
);

CREATE TABLE mgr_prod_oauth_token_sets (
    token_set_id VARCHAR(128) PRIMARY KEY,
    access_token_hash CHAR(64) NOT NULL UNIQUE,
    refresh_token_hash CHAR(64) NOT NULL UNIQUE,
    client_id VARCHAR(128) NOT NULL,
    principal_id VARCHAR(128) NOT NULL,
    tenant_id VARCHAR(128) NOT NULL,
    role VARCHAR(32) NOT NULL,
    membership_revision VARCHAR(32) NOT NULL,
    scope VARCHAR(255) NOT NULL,
    resource VARCHAR(2048) NOT NULL,
    access_expires_at DATETIME(6) NOT NULL,
    refresh_expires_at DATETIME(6) NOT NULL,
    refresh_consumed_at DATETIME(6) NULL,
    revoked_at DATETIME(6) NULL,
    created_at DATETIME(6) NOT NULL
);
```

字段用途如下：

- `mgr_prod_oauth_clients` 保存 WorkBuddy 动态注册得到的 `client_id` 和允许的 callback；
  WorkBuddy 是 public client，因此没有 `client_secret`。
- `mgr_prod_oauth_authorization_codes` 保存一次性 code 的摘要、PKCE challenge、用户、Tenant、
  callback、scope 和目标 MCP resource；换取 token 后写入 `consumed_at`。
- `mgr_prod_oauth_token_sets` 保存一组 access/refresh token 的摘要及其授权上下文。MCP 请求按
  `access_token_hash` 查找；刷新按 `refresh_token_hash` 查找，并消费旧 refresh token。

raw authorization code、raw access token 和 raw refresh token 都只在签发响应中出现，不写入
MySQL。MCP access token 不复用 `mgr_prod_sessions`：该表现有结构服务于 Web/CLI session，包含
CSRF 字段和 WEB/CLI client kind；OAuth token 使用独立表，但解析后仍构造相同的
Principal/Tenant 授权上下文并调用现有 MGR application service。

### 9.3 MGR 内部接口

1. 增加仅供 `tiana-mcp` 调用的 token introspection 接口。输入 raw MCP access token，查询
   `mgr_prod_oauth_token_sets` 并校验有效期、resource、scope、Principal 状态以及当前 Tenant
   membership；返回 `active`、`client_id`、`principal_id`、`tenant_id`、角色、membership
   revision、scope、resource 和过期时间。
2. 增加内部 HTTP adapter，把本文五个操作映射到现有 MGR application service。该接口接收
   introspection 得到的 Principal/Tenant 授权上下文和业务参数，不接收 MCP access token。
3. `tiana-mcp` 不直接访问 MGR MySQL，也不直接调用 Control。

### 9.4 Web

1. 增加 `/oauth/authorize` 授权页面。
2. 匿名访问 authorize 时跳转 `/login`，并保留完整的内部 authorize return path。
3. 登录页跳转注册页时继续携带该 return path。
4. 邮箱、手机或社交注册成功后回到 authorize 页面，而不是 `/console`。
5. 用户确认后由 Web 调用 MGR 完成 authorization code 签发，并跳转 WorkBuddy callback。

### 9.5 Connector

1. 新增 `connectors/tiana-cloud` 模板文件。
2. 扩展构建脚本，在打包时复制两个 Skills。
3. 生成 `tiana-cloud-0.1.0.zip`。
4. 在 WorkBuddy 4.24.0 或更高版本导入并连接。

### 9.6 文档

1. 在 README 增加 Connector 构建和安装说明。
2. 说明 WorkBuddy 首次连接时的登录、注册和授权流程。
3. 为五个 tools 各提供一个自然语言调用示例。

## 10. 测试与验收

### 10.1 自动测试

- `initialize` 返回正确的 server identity 和 tools capability。
- 未认证的 `/mcp` 请求返回 `401` 和正确的 protected resource metadata 地址。
- OAuth metadata、public client registration、PKCE S256、authorization code 单次消费、
  access token 和 refresh token 轮换通过 MGR 集成测试。
- 未登录用户从 authorize 进入注册，注册成功后返回同一个 authorize request。
- 已有账号从 authorize 登录后返回同一个 authorize request。
- `tools/list` 只返回本文定义的五个 tools，schema 与本文一致。
- 每个 tool 的参数正确映射到现有 MGR service input。
- MCP access token 验证后得到正确的 Principal、Tenant、scope 和 resource。
- `create_instance` 的 body 固定使用 `engine: sqlite`，随后签发名称为 `default`、有效期为
  `9999-12-31T23:59:59.999Z` 的首枚 Token，并在同一 tool result 中返回。
- `update_instance` 正确构造 `If-Match`，只在修改配置时发送
  `expected_config_revision`。
- create tool 的单次上游重试复用对应步骤的幂等 UUID。
- MGR 4xx 映射为 `isError: true`，并保留 code、message、retryable 和 request ID。
- 无效 MCP method/tool 使用标准 MCP error。
- Instance 结果根据 `endpoint_id` 得到正确的 `endpoint_url`。
- `create_instance` 和 `create_instance_token` 的日志都不包含明文 Token。
- MGR 重启后从现有 MySQL 恢复 OAuth 状态并继续处理请求。

### 10.2 WorkBuddy 端到端验收

在真实内部环境使用一个尚未注册 Tiana 的用户完成以下流程：

1. 导入 Connector ZIP 并点击连接，确认 WorkBuddy 自动打开 Tiana authorize 页面。
2. 从登录页进入注册，完成当前部署提供的邮箱、手机或社交注册。
3. 确认注册成功后回到原 authorize 页面，批准授权并自动返回 WorkBuddy。
4. 输入“列出我的 Tiana 实例”，确认新 Tenant 的列表为空。
5. 输入“创建一个名为 workbuddy-demo 的 SQLite 实例，空闲超时 60 秒”，确认返回实例、
   endpoint URL 和只显示一次的首枚 `default` Token。
6. 查看新实例，确认状态、revision 和 endpoint URL 正确。
7. 修改实例显示名称，确认返回新的 `product_revision`。
8. 使用创建实例时返回的 endpoint URL 和首枚 Token 完成一次 SQLite `SELECT 1` 连接测试。
9. 明确要求为实例追加一个有到期时间的 Token，确认 `create_instance_token` 返回另一枚且只
   显示一次的完整 Token。
10. 让 access token 到期，确认 WorkBuddy 使用 refresh token 更新后自动重试成功。

再使用一个已有 Tiana 账号验证登录授权路径。以上流程全部通过即达到首版交付标准。

## 11. 后续版本

首版稳定后再分别设计以下能力，不纳入本次交付：

- Token 清单和单 Token 撤销；
- Tiana branch tools；
- SQL 查询、schema inspection 等数据面 tools。

## 12. 参考资料

- [WorkBuddy Connector 开发文档](https://open.workbuddy.cn/docs/connector)
- [WorkBuddy Skill 开发文档](https://open.workbuddy.cn/docs/skill)
- [MCP Authorization Specification](https://modelcontextprotocol.io/specification/2025-06-18/basic/authorization)
- [Official MCP Go SDK](https://github.com/modelcontextprotocol/go-sdk)
- [Neon MCP Server](https://github.com/neondatabase/mcp-server-neon)
- [Turso Cloud CLI](https://github.com/tursodatabase/turso-cli)
- [Turso Agent Skills](https://github.com/tursodatabase/agent-skills)
