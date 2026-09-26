# 开始使用

先执行 `tiana --version`、`tiana login --help` 和 `tiana apps --help`。CLI 必须具备全局 `--config`、`login --start/--resume`、`sqlite`、`git` 和 `apps`。

## 安装

找不到 CLI 或版本不兼容时，执行：

```sh
npm install -g @tianadb/cli@0.2.1-beta.0
```

安装后重新检查版本和上述帮助。若旧 `@tianacloud/cli` 占用 `tiana` 命令，先执行 `npm uninstall -g @tianacloud/cli`，再安装新版。安装失败时报告 npm 错误，不搜索下载目录或云盘。

管理端地址由随技能安装的 [config.json](../config.json) 提供。把示例路径替换为当前加载的 `tiana` 技能目录：

```sh
tiana --config /path/to/tiana/config.json status
```

后续命令均带同一个 `--config`。切换部署时修改该文件的 `managementOrigin`，无需配置 Shell 环境变量。文件只保存站点地址，登录凭据仍由 CLI 单独管理。私有 CA 使用 `--ca-file`；不要关闭 TLS 校验。

## 对话中的登录

1. 执行 `tiana --config /path/to/tiana/config.json login --start --no-open --json`。
2. 向用户展示 `data.verification_uri`，让用户打开并批准登录。`status=pending`、退出码 3 表示等待授权。
3. 用户完成授权后执行 `tiana --config /path/to/tiana/config.json login --resume --json`。只有 `status=succeeded` 且 `data.logged_in=true` 才继续；仍等待时保留同一链接并遵循 `data.retry_after`，不要连续创建新登录。
4. 链接失效后重新 start。CLI 本地保存账号登录态，不需要 Connector。

普通终端也可执行 `tiana login`，打开它输出的链接并等待完成。`tiana status` 检查服务端账号和用量；用量接口失败不等于已经退出登录。

命令与恢复见 [CLI 命令与恢复](cloud-cli.md)。
