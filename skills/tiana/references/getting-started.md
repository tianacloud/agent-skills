# 开始使用

先执行 `tiana --version`、`tiana login --help` 和 `tiana web --help`。CLI 必须具备 `login --start/--resume`、`sqlite`、`git` 和 `web`。

## 安装

使用同时支持 `TIANA_API_ORIGIN` 和 `web` 命令的已核验 CLI 构建。本轮接口改名尚未发布，不用旧的固定版本号推断能力，也不臆造新发布版本。已提供符合要求的 CLI 时直接复用。

缺少 CLI 时，使用用户或发布流程提供的正式版本或获授权候选包。例如，本地 npm 候选包可通过 `npm install -g /实际路径/tiana-cli-VERSION.tgz` 安装；路径和版本必须来自实际交付产物，不按示例猜测。正式发布后固定核实过的版本及锁定来源。

安装后检查版本及 `tiana web --help`。无法取得符合要求的构建、安装失败或命令缺失时报告具体阻塞，不切回旧命令、不搜索下载目录或云盘。

管理端选择由外围环境负责。需要指定部署时，由用户或运行器在启动 Agent 或 Shell 前设置 `TIANA_API_ORIGIN`；技能不执行 export、不按命令注入或覆盖该变量，不修改 Shell 启动文件或技能安装文件。原生 Git 与 CLI 继承同一环境。

直接执行 `tiana status`。CLI 可以复用唯一已保存的管理地址；如果报告地址缺失或多个地址无法选择，说明需在外围启动环境中配置，再重新运行。不要猜测部署地址。私有 CA 使用既有 `TIANA_CA_FILE` 或用户提供的 `--ca-file`；不要关闭 TLS 校验。

## 对话中的登录

1. 执行 `tiana login --start --no-open --json`。
2. 向用户展示 `data.verification_uri`，让用户打开并批准登录。`status=pending`、退出码 3 表示等待授权。
3. 用户完成授权后执行 `tiana login --resume --json`。只有 `status=succeeded` 且 `data.logged_in=true` 才继续；仍等待时保留同一链接并遵循 `data.retry_after`，不要连续创建新登录。
4. 链接失效后重新 start。CLI 本地保存账号登录态，不需要 Connector。

普通终端也可执行 `tiana login`，打开它输出的链接并等待完成。`tiana status` 检查服务端账号和用量；用量接口失败不等于已经退出登录。

命令与恢复见 [CLI 命令与恢复](cloud-cli.md)。
