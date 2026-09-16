# macOS 原生构建交接（U-03）

状态：0.2.0 开发源码快照已准备，用户已授权在 Mac 独立临时目录准备工具、构建和离线测试。
此文面向构建执行者；最终 WorkBuddy 用户安装 npm 制品，不编译源码。

## 本轮源码材料

开发机 `qujianping@100.91.108.24`：

```text
/tmp/tiana-connector-source-handoff.h2COwS/tiana-connector-source-0.2.0-preview.tar.gz
/tmp/tiana-connector-source-handoff.h2COwS/tiana-connector-source-0.2.0-preview.tar.gz.sha256
```

这是本次临时交接位置，不是已发布下载入口。源码包包含：

| 文件 | 用途 |
| --- | --- |
| cli-baseline.bundle | CLI 基线 `557957ae294443632a4094cd432c8bc2af1cb653` |
| cli-working-tree.patch | 已跟踪文件的开发改动 |
| cli-new-files.tar.gz | 新增 CLI、SQL executor、打包脚本和测试 |
| sdk-helper.bundle | 完整 Git 历史、helper contract 3 快照 `c681e209a9151eee8dc3a0b9ed0277145617ac82` 与 SQL SDK dev.5 标签 |
| SHA256SUMS | 上述四项的 SHA-256 |

CLI 修改尚未推送；用户已允许本次 npm 候选包使用固定 helper 提交 `c681e209a9151eee8dc3a0b9ed0277145617ac82`，并记录提交与摘要。
SQL executor 的 SDK 仍由 Cargo.lock 固定为 `v0.1.0-dev.5`，提交
`0d955224802d793539835b868f75f5163f27057f`，不能用 helper 快照替换它。
包内不含仓库凭据、工具链、依赖缓存或目标 Gateway 配置。

## 构建前提

当前一键 npm 发布入口见 [CLI 发布说明](../../cli/packaging/README.md)。它自动向已授权 Mac 临时目录传入当前源码，并完成两平台构建、测试、组包和安装验证；下文源码包是此前手工构建交接快照，不是最新发布输入。

- 当前交付使用用户的 arm64 Mac。TODO：darwin-amd64 原生构建与验收延期，待有 Intel Mac / 对应 CI runner 后再安排，不阻塞本次交付。
- 需要 Go、Rust/Cargo、Node、Git、`file`、`tar` 和 Xcode Command Line Tools。
  Linux 已验证 Go 1.26.5、Rust/Cargo 1.97.1、Node 22.23.2；这不是 macOS 验证结果。
- 构建需要访问 Go/Rust 依赖和内部 SDK Git 仓库；使用执行环境的仓库认证方式，
  不把访问令牌写进源码包、命令参数或 Cargo.lock。缺少权限时回传错误，不改依赖版本。
- 成套包的目标 Gateway 发布端口为 9443；公开 CA PEM 来自 Vault `kv/platform/gaia/wulanchabu-gateway-ca-v2` 的 `ca_pem` 字段，已只读验证，指纹见 [安装交接](workbuddy-cli-install.md)。
  Console CA 和本地测试的 443 不能当成目标 Gateway 配置。

## 取得并还原源码

以下命令在已授权的构建主机执行，使用执行者自己的 SSH 凭据：

```sh
export TIANA_BUILD_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/tiana-connector-build.XXXXXX")"
cd "$TIANA_BUILD_ROOT"
scp qujianping@100.91.108.24:/tmp/tiana-connector-source-handoff.h2COwS/tiana-connector-source-0.2.0-preview.tar.gz .
scp qujianping@100.91.108.24:/tmp/tiana-connector-source-handoff.h2COwS/tiana-connector-source-0.2.0-preview.tar.gz.sha256 .
shasum -a 256 -c tiana-connector-source-0.2.0-preview.tar.gz.sha256
tar -xzf tiana-connector-source-0.2.0-preview.tar.gz
shasum -a 256 -c SHA256SUMS
git clone --no-checkout cli-baseline.bundle cli
git -C cli checkout --detach 557957ae294443632a4094cd432c8bc2af1cb653
git -C cli apply "$TIANA_BUILD_ROOT/cli-working-tree.patch"
tar -xzf cli-new-files.tar.gz -C cli
git clone --no-checkout sdk-helper.bundle sdk
git -C sdk checkout --detach c681e209a9151eee8dc3a0b9ed0277145617ac82
git -C cli fsck --connectivity-only
git -C sdk fsck --connectivity-only
```

`cli` 保留开发改动，`sdk` 是干净快照，两仓相邻满足测试读取 SDK 原始 control vectors 的路径要求。

## 原生编译与本机测试

先记录系统和工具版本：

```sh
uname -m
sw_vers
xcode-select -p
go version
rustc --version
cargo --version
node --version
```

设置下面两项为已确认的部署值；公开 CA 文件应已交付到构建目录：

```sh
export TIANA_GATEWAY_PORT='<实际 Gateway 发布端口>'
export TIANA_GATEWAY_CA='<实际 Gateway 公开 CA PEM 的绝对路径>'
export TIANA_INSECURE_TLS=false
cd "$TIANA_BUILD_ROOT/cli"
node scripts/build-platform.mjs "$TIANA_BUILD_ROOT/sdk" "$TIANA_GATEWAY_CA" "$TIANA_BUILD_ROOT/native-output"
export TIANA_TEST_HELPER="$TIANA_BUILD_ROOT/native-output/.build/helper/release/tiana-helper"
export TIANA_TEST_SQL_EXECUTOR="$TIANA_BUILD_ROOT/native-output/.build/sql/release/tiana-sql-executor"
export TIANA_RUST_CONTROL_ARTIFACT="$TIANA_BUILD_ROOT/sdk/tests/fixtures/control_vectors.txt"
go test ./...
go test -race ./...
go vet ./...
node --test packaging/launcher.test.mjs packaging/package.test.mjs
cd "$TIANA_BUILD_ROOT/cli/sql-executor"
CARGO_TARGET_DIR="$TIANA_BUILD_ROOT/native-output/.build/sql" cargo test --locked
CARGO_TARGET_DIR="$TIANA_BUILD_ROOT/native-output/.build/sql" cargo clippy --locked --all-targets -- -D warnings
```

离线安装检查不需要账号登录、创建实例或系统信任变更。SQL 测试使用本机 fixture，不代表真实 Gateway。
构建脚本会启动刚编译的 CLI、内嵌 helper 和 executor，检查 contract 3 与 0.2.0 版本，
在 `native-output/darwin-arm64` 或 `native-output/darwin-amd64` 生成：

```text
tiana
tiana-sql-executor
gateway-ca.pem
manifest.json
SHA256SUMS
```

## 回传与后续

回传系统/工具版本、命令退出结果、脱敏错误，以及 `native-output` 下对应架构的
`tiana-cli-0.2.0-darwin-*.tar.gz` 和 `.sha256`。不要回传 `.build`、凭据或完整环境变量。
manifest 应显示正确架构、helper contract 3、固定 SQL SDK、实际 Gateway 端口、`insecure_tls: false` 和文件摘要。

三平台资产齐备后组装 npm tarball并重新检查安装；之后协调不可变 helper 版本、制品发布、
Console/Node/Gateway 信任交付与 WorkBuddy 测试入口。Mac Keychain、隔离/签名属性、5 分钟安装时限、
15 秒延迟授权、新聊天 PATH 和 WB-01..WB-18 仍须实际验证。

Linux 还原检查已逐字节核对 CLI 134 个文件和 SDK 27 个文件及可执行位；
还原后指定原始 SDK vectors、真实 helper 和 SQL executor 的 Go 测试通过，完整 Git bundle 的对象连通性检查通过。
