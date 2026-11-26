# 三方服务调用

沿用本任务的 CLI 环境和已登录空间。运行 `tiana third-party-service --help` 核对命令，运行 `tiana status --json` 确认当前空间。三方服务命令随 CLI 1.0.36 提供。若已安装 CLI 缺少命令，按主技能的配套版本指引更新。服务可用性以目标环境的实际回执为准。

## 查找 API 与使用说明

```sh
tiana third-party-service category list --json
tiana third-party-service provider list --json
tiana third-party-service api list --category CATEGORY_SLUG --provider PROVIDER_SLUG --json
tiana third-party-service api show API_SLUG --json
tiana third-party-service api docs API_SLUG
```

从相应列表读取分类、供应商和 API 的 `slug` 字段，填入对应的命令参数。查询 API 时可单独传入 `--provider`。用 `api show` 确认分类、供应商、调用方式、有效周期额度和计量规则。读取 `api docs` 返回的完整 Markdown 后，再采用其中的真实调用 URL、输入格式、响应字段和错误说明。需保留本地副本时重定向到 `.md`，或用 `--json` 从 `data.markdown` 读取同一份正文。

## 开通分类与配置密钥

1. 查看目标分类的资格和开关。当前空间有资格且确需启用时，运行 `tiana third-party-service enable --category CATEGORY_SLUG --json`。回执确认保存成功后，允许最多 30 秒生效。分类内所有 API 与同空间各 Key 共用开关。
2. `tiana third-party-service key list --json` 返回 Key 标识、名称、遮罩值与状态。若需创建新 Key，将 `key create NAME --json` 的成功回执在进程内交给 `tiana secrets set SECRET_NAME --stdin --json`，然后读取写入回执。CLI 登录会话用于管理，Function 业务请求使用空间 API Key，供应商凭据由平台持有。
3. 按[参数配置与生效](commands.md#参数配置与生效)把 `SECRET_NAME` 保存为 Function 的密钥引用参数。保留其他参数，验证参数生效回执。代码按 [Go 后端服务开发](go-backend.md)读取参数值，使用 API 文档所列的 `Authorization: Bearer` 请求头。

下面的写入只执行成功回执中的新 Key。先按[用户密钥库](secrets.md)确认密钥库已就绪，并按任务修改 Key 名和密钥引用名称。脚本保持完整值在进程内，并只显示密钥库写入回执。

```sh
python3 - <<'PY'
import json
import subprocess
import sys

key_name = "function integrations"
secret_name = "third-party-services/function-key"
created = subprocess.run(
    ["tiana", "third-party-service", "key", "create", key_name, "--json"],
    check=True, text=True, stdout=subprocess.PIPE,
)
receipt = json.loads(created.stdout)
data = receipt.get("data") or {}
key = data.get("key")
if receipt.get("status") != "succeeded" or not key:
    raise SystemExit("Key creation did not return a usable credential")
print(f"Created Key ID: {data['id']}", file=sys.stderr)
subprocess.run(
    ["tiana", "secrets", "set", secret_name, "--stdin", "--json"],
    check=True, text=True, input=key,
)
PY
```

创建或写入结果不确定时，先用 Key 列表、密钥元数据和对应回执核对状态，再决定后续操作。报告 Key 标识和密钥引用名称，完整值只交给密钥库。密钥写入失败时保留已确认的 Key 标识，避免下次创建重复 Key。

## Function 调用与验收

在已发布的 Function 中按 `api docs` 的示例用标准 HTTP 或 WebSocket 客户端访问 `third-party-services.tianacloud.com`。HTTP 响应按 API 说明判断业务成功，地图与 OCR 使用各自请求和响应格式。语音转文本流式调用按文档发送二进制音频与结束消息，每条中间结果替换当前累计文本，最终结果完成后结束连接。结合实际响应验证一次真实业务调用并记录结果。需要核对用量时，在当前空间的 Console 打开「用量 → 三方服务」。

停用分类用 `tiana third-party-service disable --category CATEGORY_SLUG --json`，作用于当前空间此分类下的 API。撤销单把 Key 用 `tiana third-party-service key delete KEY_ID --json`，其他 Key 继续有效。两者均以保存回执为准，新调用最多 30 秒生效。
