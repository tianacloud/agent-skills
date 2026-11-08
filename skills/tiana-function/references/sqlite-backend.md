# SQLite 访问配置

本流程需要提供 `tiana token create` 的配套 CLI。先执行 `tiana token create --help`；缺少命令时说明配套能力尚未可用。沿用用户已选定的登录。

## 准备资源

1. 核实 SQLite 实例和目标分支；缺少数据库才创建。用 `sqlite shell` 准备业务表与少量可核验数据。
2. 创建或复用后端服务，记录完整 `FUNCTION_ID`。创建、源码目录和发布按 [后端服务命令](commands.md)。
3. 执行 `tiana secrets init --json`。确认 `data.state=ACTIVE` 后继续；若仍 accepted，保留原实例/任务，稍后再次 init 查看同一密钥库的状态。

## 创建凭据并配置

下例为 POSIX shell 和 Python 3。先将 `DB_ID`、`FUNCTION_ID` 设为已确认的完整实例 ID；需要非默认分支时，在 sqlite show 中增加 `--branch NAME`。`secret_key` 为本函数独立的 key，已有函数的更新只修改本次数据库参数。

```sh
set -e
umask 077
work_dir=$(mktemp -d)
secret_key="functions/$FUNCTION_ID/sqlite-token"
tiana sqlite show "$DB_ID" --json > "$work_dir/database.json"
tiana token create "$DB_ID" --name "$FUNCTION_ID SQLite" --json > "$work_dir/token.json"
python3 - "$work_dir/token.json" "$secret_key" <<'PY'
import json, subprocess, sys
with open(sys.argv[1]) as f:
    receipt = json.load(f)
assert receipt['status'] == 'succeeded' and receipt['data']['token']
subprocess.run(['tiana', 'secrets', 'set', sys.argv[2], '--stdin', '--json'],
               input=receipt['data']['token'], text=True, check=True)
PY
tiana function parameters get "$FUNCTION_ID" --json > "$work_dir/current.json"
python3 - "$work_dir" "$secret_key" <<'PY'
import json, pathlib, sys
root = pathlib.Path(sys.argv[1])
connection = json.loads((root / 'database.json').read_text())['data']['connection']
parameters = json.loads((root / 'current.json').read_text())['data']['parameters']
parameters['SQLITE_ENDPOINT'] = {'kind': 'plain', 'value': connection['hostname']}
parameters['SQLITE_TOKEN'] = {'kind': 'secret', 'value': sys.argv[2]}
(root / 'parameters.json').write_text(json.dumps(parameters))
PY
tiana function parameters set "$FUNCTION_ID" --file "$work_dir/parameters.json" --json > "$work_dir/applied.json"
python3 - "$work_dir/applied.json" <<'PY'
import json, sys
with open(sys.argv[1]) as f:
    result = json.load(f)
print('Parameter application:', result['data']['application'])
PY
```

`token create` 默认不过期，业务有到期要求时增加 `--expires-at UNIX_SECONDS`。退出码非零时停止后续步骤；保留 token ID、request ID 和错误，不因重跑整段脚本签发另一枚 Token。未交付明文或响应未知时先在 Console 查看原 Token，必要时撤销后明确创建替代凭据。密钥写入失败而原回执仍在时，从原回执恢复写入。

参数 set 替换整个对象，上例保留其余参数。`applied` 或 `next_start` 后执行真实函数请求；`pending` 先核对配置下发状态。保留受限临时目录用于未完成步骤的恢复；凭据写入、参数保存及验证成功后删除本次临时目录，源码和交付记录只保留资源身份、密钥 key 和结果。

## 使用参数

按 [Go 后端服务开发](go-backend.md#访问-sqlite)读取 `SQLITE_ENDPOINT` 和 `SQLITE_TOKEN` 并连接数据库。Endpoint 使用主机名，端口沿用 SDK 默认值。完成源码发布后，通过应用的业务接口执行实际查询，确认返回预期数据；仅创建数据库句柄或编译成功不能确认连接成功。
