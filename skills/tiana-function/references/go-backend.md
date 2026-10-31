# Go 后端服务开发

后端服务是监听 `PORT` 环境变量指定端口的 Go HTTP 程序。平台固定 Go 1.26 工具链。source_dir 包含 package main，所属 go.mod 可在该目录或仓库内上级目录，多个入口可共享模块；依赖由构建流程下载。使用 SDK 时选择包含 function 包的已发布版本，记录在 go.mod 中，具体版本以当前配套 SDK 发布为准。

最小程序返回 JSON：

```go
package main

import (
    "encoding/json"
    "net/http"
    "os"
)

func main() {
    http.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
        w.Header().Set("Content-Type", "application/json")
        json.NewEncoder(w).Encode(map[string]string{"message": "Hello from Tiana"})
    })
    if err := http.ListenAndServe(":"+os.Getenv("PORT"), nil); err != nil {
        panic(err)
    }
}
```

## 读取业务参数

例如希望返回可修改的欢迎语：在后端服务参数中新增名为 `MESSAGE` 的参数，值填写 `欢迎使用订单服务` 并保存。`MESSAGE` 只是示例业务参数名，可以换成业务自己的名称。

在 handler 内读取配置，使之后的请求能读取更新的值：

```go
params, err := function.ReadConfig()
if err != nil {
    http.Error(w, "读取参数失败", http.StatusInternalServerError)
    return
}
message, ok := params.Get("MESSAGE")
if !ok {
    http.Error(w, "尚未配置欢迎语", http.StatusInternalServerError)
    return
}
```

导入 `github.com/tianacloud/sdk-go/function`。SDK 使用平台提供的 `FUNCTION_CONFIG_FILE` 读取配置，不自行拼接宿主路径。Get 返回字符串和是否存在；已配置空字符串也会返回 true，必需且非空的业务凭据还需检查空值。不要返回整个参数对象，其中可能有数据库凭据。

## 使用敏感配置

先按[参数配置与生效](commands.md#参数配置与生效)保存真实值。业务参数通过 ReadConfig/Get 获取，不用 `os.Getenv("SQLITE_TOKEN")` 读取；参数不是同名环境变量。以下片段均放在 handler 内，沿用上面已成功读取的 params。

例如 `PAYMENT_API_KEY` 是业务自定义的第三方密钥参数名，req 是业务已创建的上游 HTTP 请求：

```go
apiKey, ok := params.Get("PAYMENT_API_KEY")
if !ok || apiKey == "" {
    http.Error(w, "支付服务尚未配置", http.StatusServiceUnavailable)
    return
}
req.Header.Set("Authorization", "Bearer "+apiKey)
```

按上游真实协议设置凭据，并检查调用结果。密钥仅用于后端向上游发请求；响应只返回业务需要的结果，不返回密钥或原始请求头。配置热更新时每次请求读取；如果复用依赖密钥的客户端，须在参数变化后更新客户端，不能一直使用启动时的旧凭据。

## 访问 SQLite

先用 [Tiana SQLite](../../tiana-sqlite/SKILL.md)核实数据库实例、表结构及初始化 SQL。数据库 Endpoint 和实例 Token 分别保存为后端服务参数 `SQLITE_ENDPOINT`、`SQLITE_TOKEN`，Token 在该数据库的连接管理中创建。只在后端服务内读取并传给 SDK：

```go
endpoint, endpointOK := params.Get("SQLITE_ENDPOINT")
secret, tokenOK := params.Get("SQLITE_TOKEN")
if !endpointOK || !tokenOK || endpoint == "" || secret == "" {
    http.Error(w, "数据库参数未配置", http.StatusInternalServerError)
    return
}
token, err := tiana.NewToken(secret)
if err != nil {
    http.Error(w, "数据库凭据无效", http.StatusInternalServerError)
    return
}
connector, err := tianasqlite.NewConnector(tianasqlite.Config{
    Gateway: tiana.Config{Endpoint: endpoint, Token: token},
    RequestTimeout: 30 * time.Second,
})
if err != nil {
    http.Error(w, "数据库连接失败", http.StatusInternalServerError)
    return
}
db := sql.OpenDB(connector)
defer db.Close()
```

对应导入为 `database/sql`、`time`、`tiana "github.com/tianacloud/sdk-go"`、`tianasqlite "github.com/tianacloud/sdk-go-sqlite"`。OpenDB 创建句柄并不证明数据库已连接，继续执行实际查询并检查错误。后续 SQL 使用 `r.Context()` 与占位符绑定业务值。对需要按用户隔离的数据，从 SDK 读取可信请求身份并在查询条件中限定所属用户；不要提供任意 SQL 执行接口。

沙箱内包含公共 CA 包，正式环境公共证书通常无需业务配置 RootCAs。本地环境私有 CA 按该环境的测试指导提供，不关闭证书验证。只有 tmpfs 用于临时写入，持久业务数据保存到 SQLite 或平台文件存储。

## App 作者与初始权限

在需要作者权限的 HTTP handler 内使用 Go SDK `v1.1.0-function.4` 或包含 IsAppOwner 的后续配套版本，并将实际依赖固定到 go.mod：

```go
caller, present := function.CallerFromRequest(r)
if !present || !caller.IsAppOwner() {
    http.Error(w, "仅 App 作者可操作", http.StatusForbidden)
    return
}
// 在这里执行作者专属初始化或权限管理。
```

导入 `github.com/tianacloud/sdk-go/function`。`caller.AppOwnerID` 是本次调用来源 Web 的创建者 ID；同一个后端被多个 Web 使用时按本次来源分别判断。普通机器 Token 和没有来源 Web 的 Console 直接调用返回 false。前端会话 `is_app_owner` 只用于界面展示，不能将前端提交的布尔值或用户 ID 作为后端授权依据。模板安装的新 Web 使用安装后新创建者，作者账号和另一账号都需验证；CLI Web 预览要使用配套的来源 Web 授权流程。

## 异步任务与休眠

在启动后台 goroutine 前调用 `job, err := function.StartJob(jobID)`，成功后才启动任务，任务结束调用 `job.Finish()` 并处理错误。不同任务使用不同 ID；活跃期间相同 ID 的重复 Start 幂等，Finish 可重试，Finish 后复用 ID 表示新任务。已登记 Job 会阻止自动休眠；重启会清空登记，强制休眠和故障仍可中断任务。需要恢复的进度写入持久存储。

本地参数文件采用 `{"MESSAGE":{"kind":"plain","value":"欢迎使用订单服务"}}`，设置 `FUNCTION_CONFIG_FILE` 指向它即可使用 SDK，不需解密密钥。平台提供的加密参数由 SDK 解密，业务继续使用 Get；读取错误应返回业务错误，不泄露参数内容。
