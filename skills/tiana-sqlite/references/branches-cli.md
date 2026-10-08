# 分支 CLI 操作

通过父技能 `tiana` 安装 CLI 和完成账号登录，继承启动器的环境。执行前查看相应命令的 `--help`。以下 INSTANCE 使用已确认的完整实例 ID，示例分支名按用户任务替换。

## 查询与连接

```sh
tiana sqlite branch list INSTANCE
tiana sqlite branch list INSTANCE --search preview
tiana sqlite branch list INSTANCE --after BRANCH_CURSOR
tiana sqlite show INSTANCE --branch preview
tiana sqlite show INSTANCE --branch preview --url
tiana sqlite shell INSTANCE --branch preview -e 'SELECT 1' --format json
```

`branch list` 每次只返回一页，显示名称、分支 ID、默认标记、生命周期、运行状态和 Endpoint。需要继续查找时将返回的 `Next cursor` 传给 `--after`，保持原实例及筛选条件；一页未找到不能认定分支不存在。`--search` 是名称子串过滤，创建来源、删除目标和连接选择使用精确名称。

`show` 显示所选分支信息；`--url` 只输出连接 URL。未传 `--branch` 时选择 ID 为 `main` 的默认分支。`--branch` 接受名称，不是分支 ID；SQL 与认证规则见 [CLI 连接](cli.md)。这些分支管理命令没有 `--json`，SQL 的 `--format json` 仅用于查询结果。

## 创建

```sh
tiana sqlite branch create INSTANCE preview --wait
tiana sqlite branch create INSTANCE preview-child --parent preview --wait
tiana sqlite branch create INSTANCE review -m "Review environment" --ttl 86400 --wait
tiana sqlite branch create INSTANCE historical --timestamp 1790000000 --wait
```

- 未传 `--parent NAME` 时从默认分支创建；指定时按精确名称解析并固定来源 ID。新分支 ID 由服务端生成。
- `-m` / `--message` 设置分支描述，UTF-8，最多 2048 字节。
- `--ttl SECONDS` 是创建成功后的存活秒数，范围 1..2592000；省略表示不自动过期，0 无效。
- `--timestamp` / `-ts` 使用无符号 Unix 秒指定来源数据时间；省略表示最新数据。历史时间不可用时创建失败，不改用最新数据。历史创建依赖来源分支保留的历史。

以上选项可组合。描述与历史时间需要匹配的服务端支持；不能仅凭 CLI 接受参数便认定服务端已应用它们，也不要删掉用户要求的参数重试。

默认输出受理回执，其中包含 instance 和 operation。`-w` / `--wait` 每秒查询原创建操作，验证来源和新分支身份，直至成功或失败。成功后用 list/show 取得并记录新分支 ID 和连接信息。结果未知的处理见 [身份与操作结果](branches-lifecycle.md)。

## 删除

```sh
tiana sqlite branch delete INSTANCE preview --wait
tiana sqlite branch delete INSTANCE BRANCH_ID --by-id --force --wait
```

默认按精确名称删除，`--by-id` 改为按固定分支 ID。终端会确认删除；非交互执行须在用户已授权该删除的前提下传 `-f` / `--force`。默认分支和受保护分支不能删除，force 只跳过确认。

默认只报告受理；`--wait` 等待原删除操作成功，不等待独立的存储回收任务。不要用 `sqlite delete INSTANCE` 代替分支删除，后者以整个实例为目标。
