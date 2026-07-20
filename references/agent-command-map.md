# Agent command map

Use the absolute Agent path returned by host inspection. On PowerShell invoke it with the call operator: `& $Agent ...`.

## Table of contents

- Device lifecycle
- Target selection
- Unified sync
- Secret and environment variables
- Credential sets
- Managed files
- Browser sessions
- Dynamic credentials and managed keys
- Rotation and governance
- Delivery states

## Device lifecycle

```text
credential-agent setup --role personal --skip-browser
credential-agent setup --role cloud --skip-browser
credential-agent pair PAIR-CODE
credential-agent pair --approve --output json PAIR-CODE
credential-agent pair --deny --output json PAIR-CODE
credential-agent status
credential-agent doctor --strict
credential-agent pull
```

Use interactive `pair PAIR-CODE` when the Agent itself must collect the decision. After the exact pending device has already been shown and the user decided, use `--approve` or `--deny`; do not answer ReadLine prompts through a PTY. Structured pair output never includes the pairing code. Prefer `status --output json`, `devices --output json`, and `doctor --strict --output json` only after feature detection confirms the installed Agent accepts them. Legacy releases expose human output; use their exit status rather than parsing translated strings.

## Target selection

```text
credential-agent devices
```

Match a user-specified display name exactly. Auto-select only a single active cloud/peer target. Do not select the current source device.

## Unified sync

Use the guided multi-resource wizard when the user asks to choose interactively:

```text
credential-agent sync --to DEVICE
```

## Secret and environment variables

Custom Secret:

```text
credential-agent secret sync --to DEVICE REF [REF...]
```

Let Agent collect each value through hidden terminal input. `--value-stdin` is appropriate only when the user explicitly supplies a secure pipe outside Codex context.

Named environment variables:

```text
credential-agent env sync --to DEVICE NAME [NAME...]
```

Use only explicit names. Do not enumerate or print their current values. On the target, inject them into a child process with Agent's `env run`; do not make them permanent by default.

## Credential sets

Supported named types include:

- `aws_aksk`
- `volcengine_aksk`
- `oauth_client`
- `username_password`
- `tls_keypair`

Example:

```text
credential-agent credential-set sync --to DEVICE --type volcengine_aksk --name volcengine-default
```

Let Agent prompt for fields. Do not construct JSON or print values. For execution bindings, use `credential-set run` according to `credential-agent help` from the installed version.

## Managed files

Prefer a server-defined profile when one exists:

```text
credential-agent file sync --to DEVICE --profile PROFILE
```

For an explicit file mapping:

```text
credential-agent file sync --to DEVICE --map 'SOURCE=home://relative/path'
```

Read [file-profiles.md](file-profiles.md) before constructing custom mappings. Do not read the file contents into Codex.

Target-side operations:

```text
credential-agent file list
credential-agent file restore --to DEVICE [--target home://relative/path] REF
credential-agent file remove --to DEVICE REF
```

`file list` shows files applied on the current computer. `file restore` and `file remove` are issued from a logged-in control device and target the peer explicitly. Check installed help before destructive removal.

## Browser sessions

All currently authenticated supported sites:

```text
credential-agent browser sync --to DEVICE --all
```

Use this only for an explicit all-sites request. Enabling all supported sites during browser setup grants the policy-defined host-permission capability; it does not select `--all` for later syncs.

Selected sites:

```text
credential-agent browser sync --to DEVICE github reddit google
```

After the user has explicitly approved the exact target and selected sites, Agent orchestration should prefer stable phase output:

```text
credential-agent browser sync --to DEVICE --yes --output jsonl github
```

Do not drive the interactive confirmation by guessing prompt state or sending `Y\n` through a PTY. Use JSONL until the final `result` event, and retain the `operation_id` and Sync Job ID for diagnostics. Fall back to the interactive form only when the installed Agent does not support these flags.

The `prepare_browser` phase returns policy counters under `details.policies`:

- `checked`: selected policies compared with the current extension heartbeat.
- `already_current`: exact digest matches that required no write.
- `updated`: policies actually sent successfully to the extension.

When `checked == already_current` and `updated == 0`, Agent skips both `UPDATE_SITE_POLICY` and the 30-second digest wait. It still validates login state, captures the selected sites, creates the Sync Job, and waits for target delivery.

Site support comes from Credential Vault dynamic policy. Do not hardcode site names or a count, and do not infer support from files packaged with the extension. Agent verifies `policy_version` and `policy_digest` before the generic extension executes it. Preserve Agent confirmation and report each site's result. Google policy may validate Google Search display login without guaranteeing Gmail, Drive, or Google Account sensitive pages.

Revoke central site consent/snapshot:

```text
credential-agent browser revoke SITE
```

Do not claim this automatically signs out every previously restored target browser unless Agent confirms a clear operation was delivered.

## Dynamic credentials and managed keys

Inspect installed help before using advanced commands:

```text
credential-agent dynamic lease ...
credential-agent dynamic run ...
credential-agent managed-key ...
```

Dynamic credentials are short-lived leases. Managed keys are non-exportable key references and operations; do not attempt to retrieve key material.

## Rotation and governance

```text
credential-agent rotation set ...
credential-agent rotation run ...
credential-agent governance ...
credential-agent capability verify
```

Use only when the user asks for policy, audit, rotation, capability, or managed-device operations. Read installed `help` because advanced flags evolve faster than this Skill.

## Delivery states

Distinguish:

- `succeeded`: target acknowledged every item
- `partial`: at least one item succeeded and one failed
- `failed`: no requested delivery completed
- `pending_target`: job exists but target is offline or has not polled
- `cancelled`: user or Agent cancelled

Do not resubmit successful items after a partial batch. Retry only the failed references/sites.
