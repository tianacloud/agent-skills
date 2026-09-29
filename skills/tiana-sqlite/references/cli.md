# CLI 连接

CLI 安装按父技能 `tiana` 的开始使用说明处理。先执行 `tiana --version` 和 `tiana sqlite shell --help`。

```sh
tiana sqlite shell INSTANCE
tiana sqlite shell INSTANCE -e 'SELECT 1' --format json
tiana sqlite show INSTANCE --url
```

已知完整 Endpoint 时，可执行 `tiana sqlite shell --endpoint HTTPS_ENDPOINT -e 'SELECT 1'`。使用 MGR 返回的 HTTPS 主机与端口，不猜测地址或关闭 TLS 验证。

SQLite、Git 和 `connect` 默认使用当前 origin 的账号登录态，不自动在连接阶段刷新；缺少有效登录时先完成 `tiana login`。只在用户明确提供相应认证配置时使用 `TIANA_TOKEN` 或 `TIANA_TOKEN_FILE`，两者互斥；不要主动查找、复制或打印这些密钥。

原生客户端包装命令以当前 `tiana connect --help` 为准。连接成功后发生错误不自动重放 SQL 或 Git 操作；先核实原操作结果。
