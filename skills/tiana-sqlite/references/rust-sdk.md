# Rust SQLite 客户端

Rust 1.85+ 可从公开 GitHub 仓库安装已发布的 Git 标签 `v1.0.0`：

- [sdk-rust-sqlite](https://github.com/tianacloud/sdk-rust-sqlite/tree/v1.0.0) 提供 Hrana v3 SQL 会话、参数和事务。
- [sdk-rust](https://github.com/tianacloud/sdk-rust/tree/v1.0.0) 提供 TLS/H2 CONNECT transport；原生通道本身不是 SQL 客户端或 ORM。

## 固定依赖

```toml
[dependencies]
tiana-sdk-sqlite = { git = "https://github.com/tianacloud/sdk-rust-sqlite.git", tag = "v1.0.0" }
tiana-sdk = { git = "https://github.com/tianacloud/sdk-rust.git", rev = "c1f5c9872bdea4aaa542d33f613e92e005ea03ff", version = "=0.1.0-dev.5" }
tokio = { version = "=1.53.1", features = ["macros", "rt-multi-thread"] }
```

core 的完整 revision 是其 `v1.0.0` 指向的提交，并与 SQLite adapter 的依赖来源保持一致，避免同一 core 的不同 Cargo Git source 导致类型不兼容。Git 标签不是 crates.io 包版本：这次标签下的 crate 版本仍分别为 `0.1.0-dev.1`（SQLite）和 `0.1.0-dev.5`（core）；不要写成来自 crates.io 的 `tiana-sdk = "1.0.0"`。提交 Cargo.toml 和 Cargo.lock，后续构建使用 `cargo build --locked`，不依赖相邻工作副本或本机 path/patch。

## 参数化只读查询

连接目标使用 CLI 返回的实际数据库 Endpoint。应用由自己的凭据提供方注入有效连接 Token；示例从环境读取，不读取 CLI 凭据文件，不把 Token 写入源码或日志，不要求用户粘贴 Token。SDK 不自动复用 CLI 登录态或刷新凭据。

```rust
use tiana_sdk::{Client, SecretToken};
use tiana_sdk_sqlite::{Session, Statement, Value};

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let endpoint = std::env::var("TIANA_ENDPOINT")?;
    let token = std::env::var("TIANA_TOKEN")?;
    let client = Client::builder(endpoint)
        .token(SecretToken::parse(token.as_bytes())?)
        .build()?;
    let mut session = Session::new(client);
    let result = session
        .query(&Statement::new("SELECT ? AS value").args([Value::Integer(42)]))
        .await;
    let closed = session.close().await;
    let result = result?;
    closed?;
    let value = match result.rows.first().and_then(|row| row.first()) {
        Some(Value::Integer(value)) => value,
        _ => return Err("unexpected result type".into()),
    };
    println!("{value}");
    Ok(())
}
```

默认验证 TLS 证书及主机名。自定义 CA 和物理连接地址按该版本仓库 README/example 配置，不关闭验证，不改变逻辑 Endpoint 身份。

同一事务及 savepoint 必须使用同一个 Session，并明确 commit 或 rollback 后 close；close 不会提交，断线或取消不证明回滚。网络中断、响应缺失或 `outcome_unknown()` 为真时，先用独立只读查询核实结果，不自动重放 SQL。新建 Session 不会恢复旧事务、临时表或会话状态。更多类型、大小与超时边界见仓库 README；SQL 使用与结果不明处理见 [SQL 命令](sql.md)。
