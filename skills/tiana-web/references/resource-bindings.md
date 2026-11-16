# 已有 Web 的 SQLite 与 Git 关联

本指引需要 CLI 1.0.31 或更新的正式版，以及目标环境的资源关联接口。先执行 `tiana web bindings --help` 确认实际 CLI 支持；命令或接口不可用时报告缺口。

## 读取、补绑与解绑

1. 在当前用户选择的环境和空间执行 `tiana web bindings get WEB_ID --json`，核对 Web ID、当前两个资源 ID、`can_manage` 和 `project_revision`。管理者为应用创建者或所属空间 owner/admin。
2. 补绑前，用 `tiana sqlite show` 或 `tiana git show` 核实用户指定或本次任务确定的实例，确认同空间、类型正确且已就绪。仅给未绑定的资源槽位补绑；已有关联时先按用户意图解绑，再补绑。文件托管 Web 没有 Site 入口，不能绑定 SQLite。
3. 使用读取结果的 revision 提交；只传本次要修改的资源。每次成功后使用返回的新 revision；并发冲突先重新读取，不能用旧 revision 重放。

```sh
# 读取
tiana web bindings get WEB_ID --json

# 补绑 SQLite 或 Git，可在一条命令中同时指定两个未绑定的资源
tiana web bindings bind WEB_ID --database-instance-id SQLITE_ID --expected-revision REVISION --json
tiana web bindings bind WEB_ID --git-instance-id GIT_ID --expected-revision REVISION --json

# 解绑 SQLite、Git，或同时指定 --database --git
tiana web bindings unbind WEB_ID --database --expected-revision REVISION --json
tiana web bindings unbind WEB_ID --git --expected-revision REVISION --json
```

解绑只解除 Web 关联，原实例及数据保留。补绑不迁移数据、初始化数据库或复制 Git 源码；需要这些工作时按本次应用需求单独处理。数据库和源码引用分别管理，不改变函数调用列表、Function 的源码仓库或数据库配置。

绑定变更无需重新发布 Web。刷新应用页面后，新数据库连接读取当前绑定；已签发的临时凭据和已建立连接沿原生命周期结束。CLI 本地预览重新启动后使用当前绑定。

请求中断或回执异常时保留原 Web ID 与所请求的修改，先执行 `bindings get` 核对结果，不自动重发写请求。交付时报告实际关联状态，以及原实例是否保留；不把解绑报告成删除。
