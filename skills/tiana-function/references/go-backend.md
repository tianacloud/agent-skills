# Go 函数开发

函数是监听 `PORT` 环境变量指定端口的 Go HTTP 程序。平台固定 Go 1.26 工具链。源码包含实际 go.mod/go.sum；依赖由构建流程下载。使用 SDK 时选择包含 function 包的已发布版本，记录在 go.mod 中，具体版本以当前配套 SDK 发布为准。

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

例如希望返回可修改的欢迎语：在函数参数中新增名为 `MESSAGE` 的参数，值填写 `欢迎使用订单服务` 并保存。`MESSAGE` 只是示例业务参数名，可以换成业务自己的名称。

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

导入 `github.com/tianacloud/sdk-go/function`。SDK 使用平台提供的 `FUNCTION_CONFIG_FILE` 读取配置，不自行拼接宿主路径。不要返回整个参数对象，其中可能有数据库凭据。

## 访问 SQLite

先用 [Tiana SQLite](../../tiana-sqlite/SKILL.md)核实数据库实例、表结构及初始化 SQL。数据库 Endpoint 和实例 Token 分别保存为函数参数 `SQLITE_ENDPOINT`、`SQLITE_TOKEN`，Token 在该数据库的连接管理中创建。只在函数内读取并传给 SDK：

```go
endpoint, endpointOK := params.Get("SQLITE_ENDPOINT")
secret, tokenOK := params.Get("SQLITE_TOKEN")
if !endpointOK || !tokenOK {
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

对应导入为 `database/sql`、`time`、`tiana "github.com/tianacloud/sdk-go"`、`tianasqlite "github.com/tianacloud/sdk-go-sqlite"`。后续 SQL 使用 `r.Context()` 与占位符绑定业务值。对需要按用户隔离的数据，从 SDK 读取可信请求身份并在查询条件中限定所属用户；不要提供任意 SQL 执行接口。

沙箱内包含公共 CA 包，正式环境公共证书通常无需业务配置 RootCAs。本地环境私有 CA 按该环境的测试指导提供，不关闭证书验证。只有 tmpfs 用于临时写入，持久业务数据保存到 SQLite 或平台文件存储。
