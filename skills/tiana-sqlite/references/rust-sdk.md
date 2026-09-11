# Tiana Rust SDK

The current development release is `tiana-sdk` `v0.1.0-dev.5`. It is an async
transparent transport core, not a SQL query builder or ORM.

## Dependency

The crate is intentionally distributed from immutable internal Git rather than
crates.io:

```toml
[dependencies]
tiana-sdk = { git = "https://git.service.internal.tiana.com/tiana/sdk.git", tag = "v0.1.0-dev.5" }
```

## Connect a tunnel

```rust
use tiana_sdk::{Client, DatabaseProtocol, SecretToken};

# async fn connect() -> Result<(), Box<dyn std::error::Error>> {
let token = SecretToken::parse(std::fs::read("/run/secrets/tiana-token")?)?;
let client = Client::builder(
        "ep-00000000000000000000000000.db.service.internal.tiana.com",
    )
    .token(token)
    .build()?;

let tunnel = client.connect(DatabaseProtocol::HranaHttp).await?;
// `tunnel` implements Tokio AsyncRead + AsyncWrite and carries opaque Hrana bytes.
drop(tunnel);
# Ok(())
# }
```

Select `DatabaseProtocol::HranaHttp` or the SDK's Hrana WebSocket variant to
match the database client protocol. Do not send SQL directly unless the caller
is itself implementing the corresponding database protocol.

## Transport behavior

- TLS requires 1.3 with ALPN `h2`.
- One logical Tiana Endpoint is bound to each physical HTTP/2 connection.
- A client can multiplex independent streams; each stream is one database
  session and supports bidirectional half-close.
- The full successful CONNECT response must be validated before the tunnel is
  returned.
- The SDK never automatically retries or replays a database session after a
  successful CONNECT boundary.

Development Gateway address and trust overrides change physical dialing only.
They must leave Endpoint validation, TLS SNI, and HTTP/2 authority bound to the
logical Endpoint hostname and port 443. Do not add an insecure TLS mode.

