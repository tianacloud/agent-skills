# 后端服务命令

沿用本会话已选择的 CLI 环境与登录。示例中的 `FUNCTION_ID`、`GIT_ID`、commit 和构建 ID 均替换为实际回执，名称有歧义时使用 ID。

```sh
tiana function list --page 1 --json
tiana function show FUNCTION_ID --json
tiana function create "订单后端" -m "订单业务接口" --git-instance-id GIT_ID --source-dir /services/orders --wait --json
```

不传 `--git-instance-id` 则创建独立源码 Git。列表每次读取一页，按需要用 `--page` 继续，不为查找已知 ID 遍历整个租户。

## 源码

```sh
tiana function source list FUNCTION_ID --json
tiana function source read FUNCTION_ID main.go --commit COMMIT > main.go
tiana function source list FUNCTION_ID handlers --commit COMMIT --offset 0 --json
```

目录结果含 `commit`、`root`、`entries`、`next_offset`。路径相对于该后端服务的源码根，子目录翻页使用原 commit 与 next_offset。`needs_initial_source=true` 表示还需要保存初始代码。`read` 默认输出原始文件，`--json` 输出包含路径、commit 和 UTF-8 内容的结构。

编辑本地文件后，只列出需要保存的文件：

```sh
tiana function source save FUNCTION_ID --base-commit COMMIT --file main.go=./main.go --file go.mod=./go.mod --json
```

完全空的 Git 首次保存用 `--base-commit empty`。已有前端提交的共享仓库使用 `source list` 返回的 commit，不用 empty；命令会将文件写到新后端服务目录，保留其他文件。保存返回新的 commit。二进制文件、删除文件、仓库根部共享模块及跨目录整理用原生 Git。

## 构建和发布

```sh
tiana function publish FUNCTION_ID --commit COMMIT --wait --json
tiana function builds FUNCTION_ID --json
tiana function builds FUNCTION_ID --before SEQUENCE --json
tiana function logs FUNCTION_ID --build SUBMISSION_ID --json
```

省略 `--commit` 时读取 main。已是最新发布的 commit 时直接返回 `already_published`，不重新编译。构建历史每页 20 条；继续读取时以本页最后一条的 sequence 作为 before。

提交时 stderr 显示 request ID 与 commit；JSON 回执也携带这两项。响应未知时先查询 builds；需要恢复原请求时使用相同 `--request-id REQUEST_ID --commit COMMIT`。中断等待不会取消服务端构建。

## 参数配置与生效

先列出代码实际需要的参数名和用途，例如 `SQLITE_ENDPOINT`（数据库连接地址）、`SQLITE_TOKEN`（该数据库实例 Token）、`PAYMENT_API_KEY`（第三方接口密钥）。使用已核实的目标资源取得实际值；缺少第三方密钥时请用户在 Console 配置，不要求在对话中粘贴。

Console 操作：打开目标后端服务 →「参数配置」→「参数列表」，分别填写参数名和值并保存。参数名须与代码 Get 的名称一致。当前只支持 `kind=plain`；敏感值也通过此入口配置，不能将它描述为已支持密钥引用管理。

CLI 操作：

```sh
tiana function parameters get FUNCTION_ID --json
tiana function parameters set FUNCTION_ID --file parameters.json --json
```

set 替换整个参数对象。get 的 JSON 回执从 `data.parameters` 取出已有参数，再修改目标项，保留其他值；不能把完整 get 回执直接交给 set。parameters.json 根部直接是参数名到类型和值的对象，不再包一层 parameters。下面仅展示格式，使用前替换为实际值：

```json
{
  "MESSAGE": {"kind": "plain", "value": "欢迎使用订单服务"},
  "SQLITE_ENDPOINT": {"kind": "plain", "value": "<实际数据库 Endpoint>"},
  "SQLITE_TOKEN": {"kind": "plain", "value": "<实际数据库实例 Token>"}
}
```

含凭据的文件放在 Git 和前端构建目录之外，使用仅当前用户可读写的临时文件，用完删除。get 和 set 回执都可能包含参数值，同样写入受限临时文件处理，不打印到对话或交付日志。仅报告参数名称与生效状态。

核对 set 返回的 `data.application`：

| 结果 | 后续动作 |
| --- | --- |
| `applied` | 当前执行已接收配置，再发一个实际业务请求验证读取与使用成功。 |
| `next_start` | 配置已保存，下次启动使用；调用已发布的服务完成唤醒并验证。 |
| `pending` | 已保存但当前执行尚未确认收到。可在 Console 点击「重试下发」，再核对结果；不能报告已生效。 |

更新参数无需重新编译。Go 读取与使用按[Go 后端服务开发](go-backend.md)；验证数据库连接或上游调用是否成功，不通过回显密钥来验证。参数读取、必需值缺失和下游拒绝都要有明确业务错误。轮换凭据后再验证新请求，避免代码启动时缓存旧值造成“配置改了仍失败”。

## CORS

```sh
tiana function cors get FUNCTION_ID --json
tiana function cors set FUNCTION_ID --file cors.json --json
```

CORS set 同样替换整个配置对象，先读取保留仍需使用的规则。

cors.json 示例：

```json
{
  "origins": ["https://app.example.test"],
  "methods": ["GET", "POST"],
  "headers": ["Authorization", "Content-Type"],
  "expose_headers": ["X-Request-ID"]
}
```

origins 决定可发起跨域浏览器调用的来源；methods 和 headers 决定预检允许的方法及请求头；expose_headers 决定浏览器脚本能读取的额外响应头。CORS 不替代调用鉴权。

## 启停和删除

```sh
tiana function disable FUNCTION_ID --json
tiana function enable FUNCTION_ID --json
tiana function delete FUNCTION_ID --force --wait --json
```

停用阻止访问；删除清理后端服务和制品，源码 Git 保留。删除必须是用户要求的操作；非交互命令用 --force 跳过已完成的人工确认。结果未知时保留回执，使用原实例 ID 和 `--request-id` 恢复。

## 交付 Web 使用

为 Web 开发后端时，将服务 ID、源码 Git 和 source_dir、发布回执、接口契约及参数生效结果交回 [Tiana Web 接入流程](../../tiana-web/references/backend-apps.md)。Web 绑定、前端预览与模板安装由该 skill 负责。

源码目录支持根目录 `/`，创建后固定。服务改名不改路径，保存提交信息为 `Save source of <当前服务名称>`。多个入口目录可共用上级 go.mod；同仓同目录也可被多个服务共享。
