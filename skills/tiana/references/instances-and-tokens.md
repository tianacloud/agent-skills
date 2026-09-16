# Instances, accounts and saved credentials

An instance is the logical database App. Its instance_id identifies management
operations; its endpoint_id identifies the Gateway connection destination.
Use IDs returned by the CLI rather than deriving one ID from another. A display
name is not a unique identity.

The local auth status exposes principal_id (the signed-in identity) and
tenant_id (the tenant context). Saved connections and task journals are scoped
to that account context. If switching accounts hides a task, reconnect the
original account instead of re-creating the database.

A management session is used with MGR. An InstanceToken authorizes the selected
database Endpoint. SQL travels from the CLI executor through Gateway to SQLite,
not through MGR; the two credential types are not interchangeable.

Creating an instance is asynchronous: the product record or an Operation ID
alone is not full success. The CLI waits for its original operation, obtains
the published root Endpoint, issues the initial Token, and saves it locally.
Inspect instance_created and credential_saved separately.

The server delivers a raw InstanceToken once. The CLI saves it directly in its
credential backend before reporting credential_saved=true. Task metadata and
command output contain IDs and status, not the Token. If the original secret
cannot be recovered, keep the existing instance and obtain the user's approval
before issuing a replacement credential.

A sleeping SQLite instance can wake on connection; do not create a replacement
because it is idle. A requested desired state is not proof that the operation
completed. Inspect actual instance/operation results and report failures.

For the supported CLI operations and recovery commands, read
[CLI commands and recovery](cloud-cli.md).
