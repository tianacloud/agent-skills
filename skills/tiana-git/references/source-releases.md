# 应用源码与发布

创建或发布 Tiana 应用时使用此流程。按用户选择同步源码，从确定的 Git 提交构建并发布当前归档；源码关联通过 MGR Web 项目参数记录。

## 准备 Git 客户端

在 Agent 实际执行命令的环境中检查 `git --version`、`tiana version` 及 `git-remote-tiana` 的命令路径。macOS/Linux 使用 `command -v git-remote-tiana`；Windows 按 [Windows 安装与 Git helper 排查](../../tiana/references/windows-git-helper.md)检查 npm 生成的入口与 PATH。缺少 CLI 或 helper 时，按[开始使用](../../tiana/references/getting-started.md)安装同一个 `@tianacloud/cli` 包，安装成功并核验后再继续。

## 确定源码托管方式

创建仓库或上传源码前，检查应用所在的 Git 仓库、远程地址，以及项目已记录的托管选择。

| 项目状态 | 操作 |
| --- | --- |
| 使用 Tiana 从零创建新应用，没有已有的外部仓库 | 将创建并关联 Tiana Git 仓库作为应用交付的一部分。 |
| 应用已由 Tiana Git 管理，或用户已批准同步到指定的 Tiana 仓库 | 复用该仓库，同步用户要求的每个版本，无需重复询问。 |
| 已有仓库托管在 GitHub、Gitee 或其他外部服务 | 创建 Tiana 仓库或向其上传源码前，询问一次。 |
| 现有项目的仓库归属或托管选择不明确 | 首次上传前确认目标源码仓库。 |

对于外部仓库，说明拟操作的范围：“是否同时将这个应用的源码托管到 Tiana Git，并随每次应用发布同步？现有仓库和远程配置会保留。”获得答复前，不上传源码或发布与之关联的应用；本地开发可以继续。在项目交付记录中保存批准或拒绝的结果。用户拒绝时，将源码保留在现有托管平台，按用户选择的范围发布，并说明未启用 Tiana 源码托管。单仓多应用中，对一个应用的批准不包含上传无关项目或整个仓库历史。

## 关联仓库

先解析应用已记录的 Tiana Git 实例和远程地址，没有时才创建。查看已安装 CLI 的帮助，创建并等待 Git 实例就绪：

```sh
tiana git create WEB_NAME --wait
```

确认实例已就绪，并记录实例 ID。创建中断时按原始待完成请求恢复。根据返回的 Git 实例已发布 Endpoint 的主机和端口，组成 `tiana://HOST[:PORT]/repo.git`；这是用户自己的原生 Git 实例，不是平台内部源码 Git 服务。已安装的 `git-remote-tiana` 使用 CLI 保存的账号登录态。

新仓库将 Tiana 配置为源码远程仓库。已有外部仓库则添加单独的 Tiana remote，保留现有 origin 和跟踪配置。复用匹配的远程地址；遇到远程名称或仓库绑定冲突时先澄清，不直接替换。上传内容保持在授权范围内，排除密钥，使用普通推送，不重写远程历史。

例如，确认 `tiana` 这个远程名称尚未使用后，添加实际 Endpoint 对应的地址：

```sh
git remote add tiana 'tiana://HOST:PORT/repo.git'
```

将 `HOST:PORT` 替换为实际 Endpoint。这里的 `tiana` 是远程名称；执行 `git fetch tiana` 或向它推送时，Git 根据 `tiana://` 自动调用 `git-remote-tiana`。推送时使用项目已确定的分支或版本引用。

## 发布对应源码的当前内容

1. 提交应用源码、构建配置、锁文件、SQL 和迁移。生成物只包含模块与资源，不含 tiana.app.json。应用源码提交和推送仍须在用户授权范围内；验证远端分支/标签确实指向将要构建的提交，不改写已分配的源码引用。
2. 从干净、已确认的源码提交按工程 README 构建。用实际 Git ID 和完整小写 40/64 位提交号更新项目参数；若构建脚本输出 `TIANA_PROJECT_PARAMS`，核对其值与真实源码及远端提交一致。项目参数不写进 dist。不得只修改参数冒充重新构建。
3. 新建项目：`tiana web create NAME --entry assets/app.js --database-instance-id DB_ID --git-instance-id GIT_ID --source-commit FULL_HASH --json`。既有项目先读取最新 project_revision，再用 `tiana web update WEB_ID --expected-revision REV --git-instance-id GIT_ID --source-commit FULL_HASH --json`。Git ID 可先绑定、commit 可暂缺；commit 非空时必须有 Git。entry 创建后不可修改，没有 styles/rendering/routing 字段。
4. 发布该提交产物：`tiana web publish WEB_ID --dir DIST --json`，保存 publish_id 和归档 SHA256，随后 `tiana web status WEB_ID --publish-id PUBLISH_ID --json` 确认 ACTIVATED 和 serving_sha256。项目参数和归档分别更新，MGR 不管理发布。参数更新成功但文件发布失败时报告部分完成；不伪称源码、项目参数、S3 对象原子一致。
5. 保存 Web/实例 ID、Git ID、远端引用、源码 commit、publish_id、校验和及托管链接。没有 Web 版本列表或恢复接口；Git 源码历史由 Git 管理。发布结果未知时只查询，禁止自动重放 PUT。用户不采用 Tiana Git 时保留原托管平台，不填写虚构关联。

## 构建时传入源码提交

先读取下载工程的 README 和构建脚本。以下示例适用于接收 `SOURCE_COMMIT` 的 `scripts/build.mjs`：由命令工具执行 Git，`source.json` 保留 Git 实例 ID，提交号随 TIANA_PROJECT_PARAMS 输出，作为 MGR 命令参数录入，不进入归档。在应用仓库根目录完成依赖安装和源码提交后，使用当前命令工具对应的一组命令；其他工程使用自己的构建命令。

Bash：

```sh
sourceStatus=$(git status --porcelain) || exit 1
[ -z "$sourceStatus" ] || { echo '请先处理并提交源码变更'; exit 1; }
sourceCommit=$(git rev-parse HEAD) || exit 1
node scripts/build.mjs "$sourceCommit" || exit 1
buildStatus=$(git status --porcelain) || exit 1
buildCommit=$(git rev-parse HEAD) || exit 1
[ -z "$buildStatus" ] && [ "$buildCommit" = "$sourceCommit" ] || { echo '构建期间源码变化，请从确认的提交重新构建'; exit 1; }
```

PowerShell（直接使用已有的 PowerShell 命令工具）：

```powershell
$sourceStatus = git status --porcelain
if ($LASTEXITCODE -ne 0) { throw '读取 Git 状态失败' }
if ($sourceStatus) { throw '请先处理并提交源码变更' }
$sourceCommit = git rev-parse HEAD
if ($LASTEXITCODE -ne 0) { throw '读取 Git 提交失败' }
node scripts/build.mjs $sourceCommit
if ($LASTEXITCODE -ne 0) { throw '构建失败' }
$buildStatus = git status --porcelain
if ($LASTEXITCODE -ne 0) { throw '读取构建后的 Git 状态失败' }
$buildCommit = git rev-parse HEAD
if ($LASTEXITCODE -ne 0) { throw '读取构建后的 Git 提交失败' }
if ($buildStatus -or $buildCommit -ne $sourceCommit) { throw '构建期间源码变化，请从确认的提交重新构建' }
```

以上命令在同一次工具调用中执行；构建期间保持源码不变。核对构建输出参数的 `source_commit` 与本次 `$sourceCommit`、远程版本引用一致后再上传。脚本只检查提交号格式，不证明源码归属；调用方的 Git 核验是发布流程的一部分。

### 遇到子进程启动失败

记录失败的具体层级和原始错误：命令工具启动失败、npm 生命周期失败、Node 启动 Git 失败、Vite/esbuild 启动失败是不同阶段。`EBUSY` 等 `spawn` / `execFileSync` 错误本身不能证明是沙箱或本机策略，只有明确的策略拒绝才能据此归因。没有环境变化时，不盲目重复同一命令。

上述构建示例由命令工具读取 Git 提交，但 Vite/esbuild 仍可能需要子进程；这不保证整个构建能在禁止所有子进程的环境中运行。明确禁止执行的操作交由获准的构建环境完成。若旧应用仍在构建脚本中调用 Git，先按该应用的实际构建步骤修改源码并提交，再从新提交构建；保留它的其他生成逻辑，不临时拆解“等价构建”、手填产物清单或删除源码核验来宣称完成。
