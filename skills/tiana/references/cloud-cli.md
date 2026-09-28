# CLI 命令与恢复

本分支使用以下命令。执行前查看对应 `--help`，管理命令不统一输出 JSON。

```sh
tiana status
tiana sqlite list
tiana sqlite show INSTANCE
tiana sqlite create NAME --wait
tiana git list
tiana git show INSTANCE
tiana git create NAME --wait
tiana sqlite shell INSTANCE -f schema.sql --format json
```

创建默认只返回异步受理回执；`--wait` 等待已绑定的原始任务和实例状态。记录完整实例 ID、Job ID、Operation ID。不要从实例名称推断另一条创建请求的身份。

如果创建请求中断且仍有待完成记录，保持产品、名称和原始参数重试，CLI 复用请求 ID。若之前已成功返回，再次执行 create 是新请求。遇到未解决的其他待完成操作，应先调查原操作，不删除本地记录来强行创建。

删除使用 `sqlite/git delete INSTANCE`；默认需要终端确认。仅在用户已授权相应删除时使用 `--force`。`--wait` 等待删除操作成功，不等于物理存储已经回收完毕。

SQLite 分支使用 `tiana sqlite branch list/create/delete`。分支创建和删除的等待失败后检查原 Operation ID；不要重复创建来恢复，名称相同不代表原操作。

应用列表使用 `tiana app list`；脚本可用 `tiana app list --json` 取得全部分页的 `data.items`，保存真实 `app_id`。列表只包含当前账号拥有的应用；名称可以重复，不能仅凭同名断定是原应用。

应用命令 `app create NAME [-m DESCRIPTION]`、`app upload ID`、`app status ID` 支持 `--json`。create 返回服务端生成的 `data.app_id`（`app-` 加随机串），不接受自定义 ID；将其保存并用作清单 `app_id`。可用 `-m "应用描述"`（等价 `--description`）填写描述，默认空，最多 1024 个 UTF-8 字节，创建和 list 的 JSON 包含 `description`。创建结果未知时重复相同名称和描述的命令恢复，不删除待完成记录、不修改描述后另发请求。上传结果未知时检查同一项目、版本，并仅用完全相同的产物恢复该版本。

登录使用 `login --start --no-open --json` 和 `login --resume --json`，详见[开始使用](getting-started.md)。退出登录使用 `tiana logout`，会清理当前 origin 的账号凭据和未完成登录，不删除旧实例凭据文件。

SQL 写入中断、输出丢失或响应未知时，先用只读查询确认，不自动重放。账号、配额、网络、证书或资源状态错误均不通过创建新数据库解决。

应用删除使用 `tiana app delete APP_ID`，默认需要终端确认。仅在用户明确授权删除该应用后使用 `--force`；推荐核对 `app list --json` 的实际 ID，不依赖可能重名的名称。删除涵盖应用、全部版本及托管文件，关联的 SQLite、Git 保留。

`--wait --json` 等待源站清理完成；不加 `--wait` 只表示删除已受理。允许删除上传未完成的版本；创建请求未完成时先恢复原创建。CLI 绑定已确认的当前版本，若返回 `APP_DELETE_PREVIEW_CHANGED`，先重新核对应用与版本，再决定是否重试。中断不取消服务端删除；响应未知或停止等待后，使用同一命令或已解析的实际 ID 恢复，不重新按名称选择其他资源。公开缓存按缓存策略失效；源站清理长时间未完成时检查服务端日志。
