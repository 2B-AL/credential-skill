# CUA Target Adapter v1

`al-credential-sync` uses one environment-neutral target protocol. The caller
must pass an absolute Adapter CLI path; the skill never searches for or falls
back between development and production environments.

Invoke:

```text
python3 /absolute/path/cua.py credential-target <action> [options]
```

Every invocation writes exactly one JSON object to stdout. Success:

```json
{"schema_version":1,"adapter_protocol":"cua-target/v1","ok":true,"action":"begin","data":{}}
```

Failure:

```json
{"schema_version":1,"adapter_protocol":"cua-target/v1","ok":false,"action":"begin","error":{"code":"TARGET_NOT_AUTHORIZED","message":"...","retryable":false}}
```

Supported actions:

- `capabilities [--desktop-id ID]`
- `begin --mode device|browser --agent-path /absolute/credential-agent [--desktop-id ID]`
- `health --workflow-id ID`
- `browser-authorize-begin --workflow-id ID SITE...`
- `browser-authorize-watch --operation-id ID`
- `browser-network-ensure --workflow-id ID SITE...`
- `finish --workflow-id ID`
- `reset --desktop-id ID --device-id ID`

`begin` returns an opaque `workflow_id`, exact `device_id`, `device_ready`,
`browser_extension_ready`, `browser_connected`, and expiry. In `browser` mode
both browser readiness fields must be true before the synchronization state
machine may create a Vault Job. Only the Adapter may map the workflow to a my-cua session. `finish`
is idempotent and may delete only the exact temporary session created by that
workflow.

`browser-authorize-begin/watch` are compatibility observations only. They may
verify that the required HTTPS capability is effective for the requested
signed Policy sites, but must not open Options, call
`chrome.permissions.request/remove()`, or drive an Allow/Deny prompt. New
normal sync orchestration does not call them.

The explicit Agent path is the already verified source/personal Agent. The
Adapter may use it only for the encrypted automatic pair-relay approval; it
must never upload the binary, read source browser data, or infer another Agent
path.

Stable errors are `TARGET_NOT_FOUND`, `TARGET_NOT_AUTHORIZED`, `TARGET_BUSY`,
`TARGET_AGENT_UNAVAILABLE`, `PAIR_RELAY_EXPIRED`, `PAIR_RELAY_CLOCK_SKEW`,
`PAIR_RELAY_TARGET_MISMATCH`, `BROWSER_SETUP_REQUIRED`,
`BROWSER_PERMISSION_REQUIRED`, `BROWSER_NETWORK_UNREACHABLE`,
`OPERATION_IN_PROGRESS`, `WORKFLOW_EXPIRED`, and `NETWORK_AMBIGUOUS`.

Security requirements:

- Never return or log a pairing code, relay key/envelope, operator token,
  signed capability, Cookie/Secret value, profile path, or upstream body.
- `mode=device` must not initialize Chrome or the browser extension.
- Site commands accept exact policy site IDs only. They never accept `all` or
  a caller-supplied proxy.
- A timed-out compatibility observation is queried by workflow/operation ID;
  it is not blindly replayed.
- `workflow_id`, Connector `operation_id`, Vault `job_id`, and Identity
  `device_id` are distinct and must never be substituted for one another.

Implementations:

- `my-cua-dev`: `transport=direct_dev`, fixed development desktop, private
  static operator-token file, and explicit local TLS exception only.
- `cua_skill_bytesso`: `transport=access_hub_gateway`, Access Hub ownership
  resolution and short-lived signed operation capabilities only. It must never
  discover or invoke `my-cua-dev`.
