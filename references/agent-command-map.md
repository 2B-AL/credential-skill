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
credential-agent capabilities --output json
credential-agent setup --role personal --skip-browser
credential-agent setup --role cloud --skip-browser
credential-agent setup --role cloud --skip-browser --daemon-manager external --pair-phase begin --output json
credential-agent setup --role cloud --skip-browser --daemon-manager external --pair-phase complete --pair-timeout 2m --output json
credential-agent pair PAIR-CODE
credential-agent pair --approve --output json PAIR-CODE
credential-agent pair --deny --output json PAIR-CODE
credential-agent status
credential-agent doctor --strict
credential-agent device unenroll --yes --reason "reset for end-to-end test" --output json
credential-agent pull
credential-agent job status JOB_ID --output json
credential-agent job wait JOB_ID --timeout 5m --output jsonl
```

Run `capabilities --output json` before setup when supported. Its `daemon.manager` is authoritative for lifecycle orchestration:

On Linux, a platform image may publish the same non-sensitive contract at `/run/credential-agent/runtime.json`. Current Agent and host inspection read this root-owned descriptor when their shell did not inherit PID 1 environment. Windows continues to use its native capability and service-manager path and does not require this file.

- `platform`: launchd/systemd or the current platform's normal user-service manager.
- `external`: an image or desktop supervisor owns the long-running process; append `--daemon-manager external` to setup and never install a second platform daemon.
- `none`: the caller intentionally owns foreground lifecycle.

Do not derive this choice from OS alone. In particular, Windows cloud computers continue to use their reported platform manager; AIO sandbox images report `runtime.kind=aio_sandbox` and `daemon.manager=external`.

`device unenroll` is a current-personal-device operation, advertised as `capabilities.enrollment.features=unenroll-self`. It centrally revokes the current Device before stopping the platform daemon and clearing local User Auth, device identity/keys, and Secret Cache. Treat `central_revoked=true, local_state_cleared=false` as a partial result that requires local repair before setup. It deliberately preserves browser profile data, browser integration artifacts, restored files, central resources/snapshots, and the Agent binary. Never use it on a device-only cloud endpoint or an externally supervised Agent; revoke the exact cloud Device ID from a personal computer and reset that environment through its Connector instead.

Use phased setup whenever capabilities/help advertises it so the pairing code is returned by a fast foreground command and never retained by a generic background task. This applies to current Windows cloud Agents as well as AIO; use the regular interactive setup path only on older Agents.

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

Staged setup/repair commands for current Agents:

```text
credential-agent browser prepare [--user-data-dir DIR ...] --output json
credential-agent browser status --output json
credential-agent browser open-install --output json
credential-agent browser wait --for connected --timeout 10m --output json
credential-agent browser configure-policies --output json
credential-agent browser open-permissions --output json
credential-agent browser wait --for permissions --timeout 10m --output json
```

Select the preparation contract from Agent capabilities or the target Connector:

```text
# Personal computers and Linux sandboxes using the generic workflow
credential-agent browser prepare --distribution-mode unpacked --output json

# Development my-cua: let its Connector own unpacked prepare/install/reload
python3 <my-cua-dev-skill-dir>/scripts/cua.py credential-browser ensure

# Development my-cua exact-site fast path: one workflow session and one Job
python3 <skill-directory>/scripts/sync-my-cua.py \
  --agent-path /absolute/path/to/credential-agent github volcengine

# Only a target explicitly configured for a published Store item
credential-agent browser prepare --distribution-mode managed_store \
  --extension-id STORE_ITEM_ID \
  --expected-build-id RELEASE_BUILD_ID \
  --expected-manifest-version NUMERIC_VERSION \
  --output json

# Enterprise-managed Windows only
credential-agent browser prepare --distribution-mode managed_self_hosted --output json
```

Never invent or substitute Store identity fields. When a target Connector owns preparation, observe its readiness state instead of issuing a second prepare. For my-cua, `credential-browser ensure` is the idempotent Connector operation and must not create a model task. Call `open-install` only in the generic unpacked workflow and only when `browser status` proves it is needed. `open-permissions` remains a visible exact-Origin handoff in every mode. `configure-policies` is digest-aware and may report `deferred=true` on a device-only endpoint; its first target Sync Job delivers the exact policy through a metadata-only preparation task, waits for the authorization heartbeat, and only then runs Restore in the same Job. Use legacy `browser setup` as the feature-detected fallback only on older Agents.

All currently authenticated supported sites:

```text
credential-agent browser sync --to DEVICE --all
```

Use this only for an explicit all-sites request. Enabling all supported sites during browser setup grants the policy-defined host-permission capability; it does not select `--all` for later syncs.

Selected sites:

```text
credential-agent browser sync --to DEVICE github reddit google
```

Read-only source login preflight:

```text
credential-agent browser validate --output jsonl github
```

Call it only when `capabilities.browser.features` contains `validate` or older `help` explicitly lists it. If absent, rely on the selected-site capture validation rather than issuing an unknown command.

Run this before provisioning a new target. It sends `VALIDATE_SITE` through the connected extension and reports per-site status without capture, upload, binding creation, or target selection.

After the user has explicitly approved the exact target and selected sites, Agent orchestration should prefer stable phase output:

```text
credential-agent browser sync --to DEVICE --yes --output jsonl github
```

Do not drive the interactive confirmation by guessing prompt state or sending `Y\n` through a PTY. Use JSONL until the final `result` event, and retain the `operation_id` and Sync Job ID for diagnostics. Fall back to the interactive form only when the installed Agent does not support these flags.

After the `create_sync_job` JSONL phase, keep the source process running and immediately handle any exact-origin permission UI on the target through its own browser channel. The target may be a Linux sandbox or a Windows cloud desktop; this orchestration does not import or call another Skill. If the source result is `pending_target`, resume the same ID with `job wait`; do not rerun `browser sync`.

Current Vault and Agent versions expose this pause as the nonterminal Job/Item status `waiting_permission` with reason `browser_host_permission`. After the target heartbeat confirms the exact policy digest and Origin grant, the same Job emits `restoring_sessions` again and continues. Preserve these states in JSONL; `pending_target` is only the caller's wait timeout result and must not overwrite the stored Job status.

They also expose `waiting_network` with reason `browser_network_unreachable`. A compatible target first probes `PROBE_SITE_REACHABILITY`; after reachability returns, `resumed` moves the same Job to `validating` and only then runs `VALIDATE_SITE`. This path never sends another Restore payload.

The `prepare_browser` phase returns policy counters under `details.policies`:

- `checked`: selected policies compared with the current extension heartbeat.
- `already_current`: exact digest matches that required no write.
- `updated`: policies actually sent successfully to the extension.

When `checked == already_current` and `updated == 0`, Agent skips both `UPDATE_SITE_POLICY` and the 30-second digest wait. It still validates login state, captures the selected sites, creates the Sync Job, and waits for target delivery.

Current Agent/extension pairs advertise combined `CAPTURE_AND_VALIDATE` and `RESTORE_AND_VALIDATE` tasks through the extension heartbeat. Agent uses them automatically and falls back to the older two-task protocol when the extension does not advertise support; the Skill must not choose task types itself.

Site support comes from Credential Vault dynamic policy. Do not hardcode site names or a count, and do not infer support from files packaged with the extension. Agent verifies `policy_version` and `policy_digest` before the generic extension executes it. Preserve Agent confirmation and report each site's result. Google policy may validate Google Search display login without guaranteeing Gmail, Drive, or Google Account sensitive pages.

Revoke central site consent/snapshot:

```text
credential-agent browser revoke SITE
```

Do not claim this automatically signs out every previously restored target browser unless Agent confirms a clear operation was delivered.

When decommissioning any temporary target, revoke its exact device ID with `credential-agent device revoke --yes --reason "temporary target decommissioned" --output json DEVICE_ID`.

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
