# Go 后端服务开发

后端服务是监听 `PORT` 环境变量指定端口的 Go HTTP 程序。平台固定 Go 1.26 工具链。source_dir 包含 package main，所属 go.mod 可在该目录或仓库内上级目录，多个入口可共享模块；依赖由构建流程下载。本页的 Get(value, error) 与密钥引用示例使用下列配套 SDK；将解析后的 go.mod、go.sum 一起保存到源码仓库。

```sh
go get github.com/tianacloud/sdk-go@v1.1.0-function.4.0.20261102183840-52d162f75066
```

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
message, err := params.Get("MESSAGE")
if err != nil {
    http.Error(w, "尚未配置欢迎语", http.StatusInternalServerError)
    return
}
```

导入 `github.com/tianacloud/sdk-go/function`。SDK 使用平台提供的 `FUNCTION_CONFIG_FILE` 读取配置，不自行拼接宿主路径。Get 返回字符串和 error；不存在时返回 function.ErrNotExist，已配置空字符串返回 ("", nil)，必需且非空的业务凭据还需检查空值。不要返回整个参数对象，其中可能有数据库凭据。

## 使用敏感配置

先按[参数配置与生效](commands.md#参数配置与生效)保存真实值。业务参数通过 ReadConfig/Get 获取，不用 `os.Getenv("SQLITE_TOKEN")` 读取；参数不是同名环境变量。以下片段均放在 handler 内，沿用上面已成功读取的 params。

例如 `PAYMENT_API_KEY` 是业务自定义的第三方密钥参数名，req 是业务已创建的上游 HTTP 请求：

```go
apiKey, err := params.Get("PAYMENT_API_KEY")
if err != nil || apiKey == "" {
    http.Error(w, "支付服务尚未配置", http.StatusServiceUnavailable)
    return
}
req.Header.Set("Authorization", "Bearer "+apiKey)
```

按上游真实协议设置凭据，并检查调用结果。密钥仅用于后端向上游发请求；响应只返回业务需要的结果，不返回密钥或原始请求头。明文参数按配置更新；密钥参数首次读取成功后在本次执行内缓存，后续密钥变化需要新的冷启动才能读取当前值。

## 访问 SQLite

先用 `tiana-sqlite` 技能核实数据库实例、表结构及初始化 SQL。数据库 Endpoint 和实例 Token 分别保存为后端服务参数 `SQLITE_ENDPOINT`、`SQLITE_TOKEN`，Token 在该数据库的连接管理中创建。只在后端服务内读取并传给 SDK：

```go
endpoint, endpointErr := params.Get("SQLITE_ENDPOINT")
secret, tokenErr := params.Get("SQLITE_TOKEN")
if endpointErr != nil || tokenErr != nil || endpoint == "" || secret == "" {
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

在需要作者权限的 HTTP handler 内使用 Go SDK `v1.1.0-function.4.0.20261102183840-52d162f75066`（包含参数 Get 错误语义和密钥引用），并将实际依赖固定到 go.mod：

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

## WebSocket 实时连接

先在 Web 应用概览的「允许调用的后端服务」中添加并保存目标服务，再编写页面。托管 Web 和 CLI 本地预览都提供 `window.tiana.functions.websocket(instanceId, path, {protocols?, signal?})`，返回在连接打开后兑现的 `Promise<WebSocket>`；普通 HTTP 继续使用 `functions.fetch`。

### Go 服务：HTTP 与文本／二进制回声

将下面完整程序保存为 `main.go`。它监听平台提供的 `PORT`，普通 HTTP 路由是 `/health`，WebSocket 路由是 `/ws`，握手及帧处理由标准 WebSocket 库负责。

```go
package main

import (
    "log"
    "net/http"
    "os"

    "github.com/gorilla/websocket"
)

func main() {
    mux := http.NewServeMux()
    mux.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
        w.Header().Set("Content-Type", "text/plain; charset=utf-8")
        _, _ = w.Write([]byte("ok"))
    })
    upgrader := websocket.Upgrader{
        CheckOrigin: func(r *http.Request) bool { return true },
    }
    mux.HandleFunc("/ws", func(w http.ResponseWriter, r *http.Request) {
        conn, err := upgrader.Upgrade(w, r, nil)
        if err != nil {
            return
        }
        defer conn.Close()
        for {
            kind, data, err := conn.ReadMessage()
            if err != nil {
                return
            }
            if err := conn.WriteMessage(kind, data); err != nil {
                return
            }
        }
    })
    log.Fatal(http.ListenAndServe(":"+os.Getenv("PORT"), mux))
}
```

示例的 `CheckOrigin` 显式允许跨来源页面，便于托管 Web 调用；业务需要限制来源时在自己的 handler 中实现 Origin 策略。普通 HTTP CORS 配置与 WebSocket Origin 校验独立。需要用户身份时，在 Upgrade 前通过 `function.CallerFromRequest(r)` 读取，并将本次调用者保存在该连接的局部状态中；Go SDK 的导入和版本沿用本页配套 SDK；从 `function.CallerFromRequest(r)` 获取身份后，在 Upgrade 前完成业务判断。

在仅含此示例的新目录中执行：

```sh
go mod init example.com/function-echo
go get github.com/gorilla/websocket@v1.5.3
go mod tidy
go build .
PORT=8080 go run .
# 另一终端验证普通 HTTP：
curl http://127.0.0.1:8080/health
```

保存 `main.go`、`go.mod`、`go.sum`，再编译发布：

```sh
tiana function create "实时回声" --source-dir /services/echo --wait --json
tiana function source list FUNCTION_ID --json
tiana function source save FUNCTION_ID --base-commit COMMIT --file main.go=./main.go --file go.mod=./go.mod --file go.sum=./go.sum --json
tiana function publish FUNCTION_ID --commit SAVED_COMMIT --wait --json
```

将 `FUNCTION_ID` 替换为创建回执 ID，`COMMIT` 使用 source list 返回的提交；完全空仓库首次保存才使用 `empty`。`SAVED_COMMIT` 使用 save 返回的新提交。已有 Web 共仓时，create 增加 `--git-instance-id GIT_ID`，保留该仓库其他文件。

### 浏览器完整入口模块

将下面保存为 Web 的 `app.js`，替换服务 ID。按钮提供连接、取消尚未完成的握手、正常关闭和手动重连；页面直接显示错误与回声结果。

```javascript
const functionId = "<后端服务实例 ID>";
const panel = document.createElement("section");
panel.innerHTML = `<button id="connect">连接 / 重新连接</button>
  <button id="cancel">取消连接</button><button id="close">关闭</button>
  <pre role="status"></pre>`;
document.body.append(panel);
const status = panel.querySelector("pre");
let socket;
let pending;
function show(message) { status.textContent = message; }
panel.querySelector("#connect").onclick = async () => {
  if (pending || (socket && socket.readyState < WebSocket.CLOSING)) return;
  const controller = new AbortController();
  pending = controller;
  show("正在连接…");
  try {
    const ws = await window.tiana.functions.websocket(functionId, "/ws", {
      signal: controller.signal,
    });
    socket = ws; // Promise 在 open 后返回，此时注册 message/error/close。
    ws.binaryType = "arraybuffer";
    ws.addEventListener("message", (event) => {
      show(typeof event.data === "string"
        ? `文本回声：${event.data}` : `二进制回声：${event.data.byteLength} bytes`);
    });
    ws.addEventListener("error", () => show("连接发生错误，请检查服务后手动重连"));
    ws.addEventListener("close", (event) => {
      show(`连接已关闭：code=${event.code}，clean=${event.wasClean}`);
      if (socket === ws) socket = undefined;
    });
    show("已连接，正在发送文本和二进制消息");
    ws.send("hello");
    ws.send(new Uint8Array([1, 2, 3]));
  } catch (error) {
    show(error?.name === "AbortError" ? "已取消连接" : "连接失败，请检查应用授权和后端服务");
  } finally {
    if (pending === controller) pending = undefined;
  }
};
panel.querySelector("#cancel").onclick = () => pending?.abort();
panel.querySelector("#close").onclick = () => socket?.close(1000, "done");
window.addEventListener("pagehide", () => {
  pending?.abort();
  socket?.close(1000, "page exit");
});
```

平台通过现有 Site 授权提供短期凭据，以 `access_token` 查询参数用于握手；页面只保存服务 ID，不管理 Token，也不要记录 `socket.url`。浏览器握手失败通常只给通用错误，无法据此确定准确的 HTTP 原因。`signal` 只取消待完成的握手；连接打开后使用原生 `close()`。SDK 客户端 dispose、页面退出或检测到会话失效会关闭其连接；应用自己决定何时重新连接，不自动重连或重放消息。

示例没有申请子协议，成功连接的 `socket.protocol` 可以为空。设置 `protocols` 时由服务端选择其支持的协议；按浏览器握手规则，申请了非空协议列表但服务端未确认协议，原生浏览器会拒绝连接。平台透明转发协商，业务双方约定协议。

新建 Web 时指定固定入口，并先绑定服务：

```sh
tiana web create "实时回声页面" --entry app.js --json
tiana web functions get WEB_ID --json
tiana web functions set WEB_ID --function-id FUNCTION_ID --expected-revision REVISION --json
# 将 app.js 放在 dist/，已有 Web 使用其创建时固定的入口文件名。
tiana web serve WEB_ID --dir dist --port 4174
tiana web publish WEB_ID --dir dist --json
tiana web status WEB_ID --publish-id PUBLISH_ID --json
tiana web status WEB_ID --json
```

绑定 set 替换完整列表，保留仍需调用的其他服务；`REVISION` 来自 get。新 Web 初始停用，发布后在 Console Web 概览点击「启用应用」。核对当前内容 `state: running`，并确认 `remote_sha256`、`serving_sha256` 均等于发布回执的目标摘要；上传成功本身不代表正在服务。通过实际托管入口登录，验证文本、二进制回声、关闭 code 1000 和手动重连，同时用 `functions.fetch(FUNCTION_ID, "/health")` 验证普通 HTTP。

### 连接与服务生命周期

连接建立后没有固定时长上限，并阻止 Function 自动休眠。最后一条连接关闭后，平台结合现有 HTTP 请求、Jobs 和 idleN 判断休眠。连接准入计一次请求，消息不逐条计为请求；连接和普通调用共享并发预算。凭据到期或撤销影响后续新连接，不主动切断已经建立的连接。

发布代码在下次唤醒时使用；当前连接继续使用旧执行。Console「强制休眠」会断开连接，应用需自行处理关闭并按业务需要手动重连。


源码回执和构建失败恢复见[后端服务命令](commands.md#构建和发布)；Web 资源关联与托管验收继续按 `tiana-web` 技能的“后端交接与接入验证”和“预览与发布”流程完成。报告实际验证环境与未完成项，配套平台验证通过后再交付使用。
