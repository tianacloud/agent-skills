# 函数文件存储

使用 Go SDK `v1.2.0`。在函数源码目录固定依赖：

```sh
go get github.com/tianacloud/sdk-go@v1.2.0
```

SDK 至少需要 Go 1.25；平台 Go 1.26 工具链满足要求。服务端部署验收与正式 SDK 发布完成后，本技能随配套版本发布。

## 选择目录与权限

导入 `github.com/tianacloud/sdk-go/function` 与 `github.com/tianacloud/sdk-go/files`。

| 构造入口 | 当前根目录 |
| --- | --- |
| `function.Files()` | 函数所属租户的 files 根 |
| `function.FilesByWebApp(webID)` | 同一租户根下的 `<webID>/` |
| `function.FilesFromRequest(r)` | 从 Gateway 注入的 `Caller.WebID` 选择 Web 子目录；无来源 Web 返回 `files.ErrNoWebContext` |

构造不发请求。`FilesByWebApp` 和 `FilesFromRequest` 返回 `(*files.Client, error)`；`Files` 直接返回客户端。平台已配置 OSS，函数代码无需账号密钥、bucket、endpoint 或租户根路径。

客户端始终属于**函数资源所属租户**，与调用用户的租户无关。填写另一租户的 Web ID 只会选择本函数租户里的同名子目录。共享函数要访问特定 Web，使用 `FilesByWebApp`；使用可信来源 Web 时选 `FilesFromRequest`。同一租户内的 Web 子目录是目录选择，业务访问权限由 handler 根据 `CallerFromRequest` 判断。不要把请求体里的租户、用户或 Web ID 当作授权依据。

所有方法接收未进行 URL 编码的相对路径，例如 `reports/账单.csv`；列表、元数据和写入回执中的 Path 也相对当前客户端根。路径不能以 `/` 开头，目录段不能为 `.` 或 `..`。`List(ctx, "", ...)` 列当前根；列表分页用返回的 `NextCursor` 原样交回同一个客户端和目录，直到为空。

## 无入站请求时显式选择 Web

可直接编译的 [显式 Web 示例](../assets/file-storage/explicit-web/main.go) 提供 `POST /generate`，由 App 作者调用；先在函数业务参数中设置 `REPORT_WEB_ID`。其中 `generateReport(webID)` 不依赖 HTTP request，创建自有 context，写入后遇到未知结果只核对当前 Metadata，不重放写入。同一对象从租户客户端访问的路径是 `<webID>/reports/task.txt`。如果把该方法用于异步业务任务，沿函数技能的 jobs 用法管理任务生命周期。

例如业务已有确定的 Web ID，创建自有 context 后查询；client 的构造不需要 HTTP request：

```go
func reportMetadata(ctx context.Context, webID string) (files.Metadata, error) {
    client, err := function.FilesByWebApp(webID)
    if err != nil { return files.Metadata{}, err }
    return client.Metadata(ctx, "reports/latest.txt")
}
```

补充导入 `context`。`function.Files().Metadata(ctx, webID+"/reports/latest.txt")` 指向同一个对象，返回 Path 包含 Web 前缀；显式 Web 客户端返回的 Path 是 `reports/latest.txt`。两种 GetURL 分别使用租户根或 Web 文件入口授权范围，前端必须授权对应范围。

## 上传并返回浏览器地址

下面的完整 HTTP 程序允许来源 Web 的作者生成固定报表，并允许该 Web 的已登录用户下载。实际应用根据自己的业务模型决定读写权限、文件名和内容。

```go
package main

import (
    "bytes"
    "encoding/json"
    "io"
    "net/http"
    "os"

    "github.com/tianacloud/sdk-go/files"
    "github.com/tianacloud/sdk-go/function"
)

func main() {
    http.HandleFunc("/report", report)
    if err := http.ListenAndServe(":"+os.Getenv("PORT"), nil); err != nil {
        panic(err)
    }
}

func report(w http.ResponseWriter, r *http.Request) {
    caller, present := function.CallerFromRequest(r)
    if !present || caller.UserID == "" {
        http.Error(w, "请登录", http.StatusUnauthorized)
        return
    }
    client, err := function.FilesFromRequest(r)
    if err != nil {
        http.Error(w, "需要从 Web 应用访问", http.StatusBadRequest)
        return
    }
    ctx := function.ContextFromRequest(r)
    const path = "reports/latest.txt"
    switch r.Method {
    case http.MethodPost:
        if !caller.IsAppOwner() {
            http.Error(w, "仅 App 作者可生成报表", http.StatusForbidden)
            return
        }
        content := []byte("本次报表内容\n")
        receipt, err := client.Put(ctx, path, bytes.NewReader(content), files.PutOptions{
            Size: int64(len(content)), ContentType: "text/plain; charset=utf-8", Overwrite: true,
        })
        if err != nil {
            http.Error(w, "报表写入未确认，请查询文件状态", http.StatusBadGateway)
            return
        }
        publicURL, err := client.GetURL(ctx, receipt.Path)
        if err != nil {
            http.Error(w, "文件已写入，获取访问地址失败", http.StatusBadGateway)
            return
        }
        w.Header().Set("Content-Type", "application/json")
        _ = json.NewEncoder(w).Encode(map[string]any{"path": receipt.Path, "url": publicURL, "write_id": receipt.WriteID})
    case http.MethodGet:
        response, err := client.Get(ctx, path, files.GetOptions{Range: r.Header.Get("Range")})
        if err != nil {
            http.Error(w, "读取报表失败", http.StatusBadGateway)
            return
        }
        defer response.Body.Close()
        for _, key := range []string{"Content-Type", "Content-Length", "Content-Range", "Accept-Ranges", "ETag"} {
            if value := response.Header.Get(key); value != "" { w.Header().Set(key, value) }
        }
        w.WriteHeader(response.StatusCode)
        if _, err := io.Copy(w, response.Body); err != nil { return }
    default:
        w.Header().Set("Allow", "GET, POST")
        http.Error(w, "不支持的方法", http.StatusMethodNotAllowed)
    }
}
```

`PutOptions.Size` 是准确字节数，包含零字节；最大单文件 5 GiB。请求体已有可靠 ContentLength 时可直接将 `r.Body` 流式传给 Put；未知长度先在业务允许的大小内准备临时内容并确定长度。不要为流式接口无界读取整个上传体。默认同名冲突，显式 `Overwrite: true` 会先删除再上传，操作不是原子的，失败后旧文件可能已经删除。

`GetURL` 返回当前环境的完整公网文件入口 URL，和前端 SDK 一样仍需要浏览器自身的文件授权；它不是免授权下载链接，也不安装 Cookie。把此 URL 交给已经通过前端文件 SDK 完成授权的页面。函数自己的 Get 直接返回文件流，调用方负责 Close；可用 `GetOptions{Method: http.MethodHead}` 或 Range，传入的 context 可取消请求。

## 查询、分页和删除

可直接编译的 [租户根示例](../assets/file-storage/tenant-root/main.go) 提供 `POST /file-demo`，由 App 作者调用。它创建唯一的演示对象，读取 Capabilities、上传、查询元数据、遍历演示目录的所有页、流式读取并关闭 Body，最后删除刚创建的对象。请求失败时会返回错误而不自动重放；若演示中断，用返回的写入状态或目录查询处理遗留对象。

两个源码示例分别作为 `main.go` 放到独立目录，执行 `go mod init example.com/file-demo`，按本技能的配套 SDK 版本执行 `go get`，再运行 `go mod tidy && go build .`；保存生成的 go.mod/go.sum。平台 Go 1.26 工具链满足 SDK 的 Go 1.25 最低要求。它们与上面的来源 Web 程序分别发布为独立函数入口；通过 CLI/Console 取得真实调用入口，不把 `supervisor.tiana.com` 当作客户端公网地址。

下面片段在已有 `ctx`、`client` 的业务方法中使用，错误交给该方法的返回值处理：

```go
for cursor := ""; ; {
    page, err := client.List(ctx, "reports/", files.ListOptions{Cursor: cursor})
    if err != nil { return err }
    for _, entry := range page.Entries {
        // 使用 entry.Path、IsDir、Size、ETag、LastModified 构造业务结果。
        _ = entry
    }
    if page.NextCursor == "" { break }
    cursor = page.NextCursor
}
metadata, err := client.Metadata(ctx, "reports/latest.txt")
if err != nil { return err }
_ = metadata // Size、ETag、ContentType、LastModified、WriteID。
capabilities, err := client.Capabilities(ctx)
if err != nil { return err }
_ = capabilities // MaxFileBytes、最近已应用的 WriteBlocked。
// 用户明确要求删除时，在业务权限判断后执行：
if err := client.Delete(ctx, "reports/latest.txt"); err != nil { return err }
```

Delete 删除当前对象，不存在也成功。每次 List 计 100 文件 read 消耗；Get、Metadata 不增加该 List 消耗。存储字节异步核对，额度状态存在传播窗口；`WriteBlocked` 不是实时剩余容量。禁止写入时 Put/Overwrite 失败，文件 API 的读、列目录、删除仍可用；Gateway 的整租户准入可能阻止新的函数业务调用，释放空间也可使用 Console/CLI 文件管理。

## 写入结果与验收

用 `errors.As(err, &fileErr)` 读取 `*files.Error` 的 Code、Stage、Outcome、DeleteConfirmed、WriteID 和 RequestID。`Outcome == "unknown"` 表示结果未确认；不要自动重放 Put 或 Overwrite。用 Metadata 核对当前对象的 WriteID、大小及业务内容；WriteID 只是写入标识，不提供幂等或历史版本保证。请求取消也可能发生在 OSS 已接收写入之后。

发布前编译示例并保存真实 go.mod/go.sum。发布后在目标函数验证一次上传、Metadata、流式/Range 读取、分页和删除；验证来源 Web、明确选择 Web 及无 Web 上下文的行为。需要交付公网 URL 时，继续在对应已登录 Web 中验证前端文件授权与访问。平台未注入文件配置时会返回 `FILE_NOT_CONFIGURED`，报告服务配置缺口，不在函数源码中填入 OSS 凭据。
