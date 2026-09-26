# SQL 命令

使用 `tiana sqlite shell INSTANCE`，其中 INSTANCE 是已确认的完整实例 ID。

```sh
tiana sqlite shell INSTANCE -e "SELECT name, type, sql FROM sqlite_schema WHERE type IN ('table','view') ORDER BY name LIMIT 100" --format json
tiana sqlite shell INSTANCE -e "SELECT * FROM pragma_table_info('notes') LIMIT 100" --format json
tiana sqlite shell INSTANCE -f schema.sql --format json
```

文件模式先做语法预检，再按顺序执行。事务语句保持同一连接；每条 CLI 调用之间不共享事务、TEMP 表或会话设置。不要使用不支持的 `--atomic`。

`-e` 和 `-f` 接受已核对的 SQL 文本，没有 typed params JSON 输入接口。业务数据的参数绑定使用 [JavaScript 应用流程](js-sdk.md)；不要把用户提供的动态值插入 SQL 字符串或未引用的 shell heredoc。

使用实际数据库返回的 ID 修改或删除数据，不照抄示例 ID。输出 JSON 保持数据库的列、行和值类型；大整数保留精度。出现错误、断线或不完整输出时不得将写入判定为成功，也不要自动重复写入，先只读核实。
