# Tiana instances and InstanceTokens

Use these examples only against a configured MGR origin. The loopback origin
below is for local development.

## Authentication context

CLI-oriented MGR sessions use a bearer token:

```sh
curl -sS http://127.0.0.1:8081/mgr/v1/instances \
  -H "Authorization: Bearer $TIANA_MGR_SESSION"
```

Browser sessions use the same-origin HttpOnly cookie. Mutating browser requests
also copy the current readable CSRF value into exactly one `X-CSRF-Token`
header. Do not add that browser proof to bearer-session requests.

## List and create instances

```sh
curl -sS http://127.0.0.1:8081/mgr/v1/instances \
  -H "Authorization: Bearer $TIANA_MGR_SESSION"

curl -sS http://127.0.0.1:8081/mgr/v1/instances \
  -H "Authorization: Bearer $TIANA_MGR_SESSION" \
  -H 'Content-Type: application/json' \
  -H 'Idempotency-Key: create-demo-001' \
  -d '{"display_name":"Demo","engine":"sqlite","config":{"idle_timeout_ms":60000}}'
```

Use an engine returned by `GET /mgr/v1/app-types`. Instance creation requires a
stable `Idempotency-Key`. Retry an uncertain result with the same key and the
same normalized body; changing the body under that key is a conflict.

## Read and edit an instance

```sh
curl -sS http://127.0.0.1:8081/mgr/v1/instances/INSTANCE_ID \
  -H "Authorization: Bearer $TIANA_MGR_SESSION"

curl -sS -X PATCH http://127.0.0.1:8081/mgr/v1/instances/INSTANCE_ID \
  -H "Authorization: Bearer $TIANA_MGR_SESSION" \
  -H 'Content-Type: application/json' \
  -H 'If-Match: "1"' \
  -d '{"display_name":"Demo renamed","labels":{"env":"dev"}}'
```

Use the current quoted `product_revision` in `If-Match`. If the body changes
`config`, also include the current `expected_config_revision` in the JSON body.
On a conflict, read the current instance and let the user decide how to reapply
their intended edit.

## Create a Token

```sh
curl -sS http://127.0.0.1:8081/mgr/v1/instances/INSTANCE_ID/tokens \
  -H "Authorization: Bearer $TIANA_MGR_SESSION" \
  -H 'Content-Type: application/json' \
  -H 'Idempotency-Key: create-cli-token-001' \
  -d '{"request_id":"req-cli-token-001","name":"cli","expires_at":"2099-01-01T00:00:00.000Z"}'
```

The committed response contains `token` once. Save it to the user's chosen
secret store without printing it again. The canonical no-lifetime-limit value
is `9999-12-31T23:59:59.999Z`; there is no null or zero equivalent.

## List Token metadata

```sh
curl -sS 'http://127.0.0.1:8081/mgr/v1/instances/INSTANCE_ID/tokens?page=1&page_size=20' \
  -H "Authorization: Bearer $TIANA_MGR_SESSION"
```

List responses contain non-secret fields such as Token ID, name, status,
creation and expiry metadata, and `auth_policy_revision`. They never contain the
raw Token.

## Revoke a Token

Use the Token ID and the current policy revision returned by a fresh list:

```sh
curl -sS -X PATCH http://127.0.0.1:8081/mgr/v1/instances/INSTANCE_ID/tokens/TOKEN_ID \
  -H "Authorization: Bearer $TIANA_MGR_SESSION" \
  -H 'Content-Type: application/json' \
  -H 'Idempotency-Key: revoke-cli-token-001' \
  -d '{"request_id":"req-revoke-cli-token-001","expected_revision":"POLICY_REVISION"}'
```

Create and revoke operations are idempotent. If an operation result is
uncertain, read `GET /mgr/v1/gateway-auth-operations/{operation_id}` rather than
creating a replacement operation with new identity.

