# 函数命令

沿用本会话已选择的 CLI 环境与登录。示例中的 `FUNCTION_ID`、`GIT_ID`、commit 和构建 ID 均替换为实际回执，名称有歧义时使用 ID。

```sh
tiana function list --page 1 --json
tiana function show FUNCTION_ID --json
tiana function create "订单后端" -m "订单业务接口" --git-instance-id GIT_ID --wait --json
```

不传 `--git-instance-id` 则创建独立源码 Git。列表每次读取一页，按需要用 `--page` 继续，不为查找已知 ID 遍历整个租户。

## 源码

```sh
tiana function source list FUNCTION_ID --json
tiana function source read FUNCTION_ID main.go --commit COMMIT > main.go
tiana function source list FUNCTION_ID handlers --commit COMMIT --offset 0 --json
```

目录结果含 `commit`、`root`、`entries`、`next_offset`。路径相对于该函数的源码根，子目录翻页使用原 commit 与 next_offset。`needs_initial_source=true` 表示还需要保存初始代码。`read` 默认输出原始文件，`--json` 输出包含路径、commit 和 UTF-8 内容的结构。

编辑本地文件后，只列出需要保存的文件：

```sh
tiana function source save FUNCTION_ID --base-commit COMMIT --file main.go=./main.go --file go.mod=./go.mod --json
```

完全空的 Git 首次保存用 `--base-commit empty`。已有前端提交的共享仓库使用 `source list` 返回的 commit，不用 empty；命令会将文件写到新函数目录，保留其他文件。保存返回新的 commit。二进制文件、删除文件、仓库根部共享模块及跨目录整理用原生 Git。

## 构建和发布

```sh
tiana function publish FUNCTION_ID --commit COMMIT --wait --json
tiana function builds FUNCTION_ID --json
tiana function builds FUNCTION_ID --before SEQUENCE --json
tiana function logs FUNCTION_ID --build SUBMISSION_ID --json
tiana function switch FUNCTION_ID --json
```

省略 `--commit` 时读取 main。已是最新发布的 commit 时直接返回 `already_published`，不重新编译。构建历史每页 20 条；继续读取时以本页最后一条的 sequence 作为 before。

提交时 stderr 显示 request ID 与 commit；JSON 回执也携带这两项。响应未知时先查询 builds；需要恢复原请求时使用相同 `--request-id REQUEST_ID --commit COMMIT`。中断等待不会取消服务端构建。

## 参数和 CORS

```sh
tiana function parameters get FUNCTION_ID --json
tiana function parameters set FUNCTION_ID --file parameters.json --json
tiana function cors get FUNCTION_ID --json
tiana function cors set FUNCTION_ID --file cors.json --json
```

两个 set 都替换整个配置对象。先读取并保留需要的现有值，再修改目标项。parameters.json 直接是参数名到字符串值的对象，例如 `{"MESSAGE":"欢迎使用订单服务"}`；不要再包一层 parameters。

cors.json 示例：

```json
{
  "origins": ["https://app.example.test"],
  "methods": ["GET", "POST"],
  "headers": ["Authorization", "Content-Type"],
  "expose_headers": ["X-Request-ID"]
}
```

origins 决定可发起跨域浏览器调用的来源；methods 和 headers 决定预检允许的方法及请求头；expose_headers 决定浏览器脚本能读取的额外响应头。CORS 不替代调用鉴权。参数文件可能包含数据库凭据，使用权限受限的临时文件，用完删除，不提交 Git。

## 启停和删除

```sh
tiana function disable FUNCTION_ID --json
tiana function enable FUNCTION_ID --json
tiana function delete FUNCTION_ID --force --wait --json
```

停用阻止访问；删除清理函数和制品，源码 Git 保留。删除必须是用户要求的操作；非交互命令用 --force 跳过已完成的人工确认。结果未知时保留回执，使用原实例 ID 和 `--request-id` 恢复。

## Web 绑定与预览

```sh
tiana web functions get WEB_ID --json
tiana web functions set WEB_ID --function-id FUNCTION_ID --expected-revision REVISION --json
tiana web serve WEB_ID --dir dist
```

set 替换完整函数列表，多个后端重复 `--function-id`；不传 ID 则清空。revision 使用 get 的回执，冲突后重新读取再决定。前端通过 `context.functions.fetch(FUNCTION_ID, "/orders", {method:"GET"})` 调用，本地预览也支持。预览使用开发者账号，不能代替跨账号 Site 分享验收。

复制 Web、函数及数据库为模板时按[函数模板](../../tiana-web/references/function-templates.md)处理共享 Git、新函数目录和数据库参数映射。
