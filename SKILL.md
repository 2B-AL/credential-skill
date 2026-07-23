---
name: al-credential-sync
description: Install, update, configure, diagnose, pair, and operate the AL credential-agent and Chrome or Linux Chromium credential extension across personal computers, Linux sandboxes, and Windows cloud desktops. Use when Codex needs to initialize AL credential sync, complete OAuth or device pairing, prepare or repair the Chrome or Chromium extension and Native Messaging host, sync or revoke secrets, named environment variables, credential sets such as AK/SK, sensitive configuration files, browser sessions, dynamic credentials, or managed keys, inspect device or sync health, or recover an expired or unhealthy AL credential device.
---

# AL Credential Sync

Treat `credential-agent` as the authority for authentication, device keys, encryption, sync, browser capture, and restore. Use this Skill only to install, invoke, observe, and safely assist the Agent. Never call Credential Vault internal APIs or manipulate Chrome/Chromium profile data directly.

## Start every task

Resolve the absolute directory containing this `SKILL.md` before invoking bundled resources. The paths below are relative to that directory; do not assume the user's working directory is the Skill directory.

1. Read [security-rules.md](references/security-rules.md). Apply it before running any command.
2. Run the platform inspection script:
   - macOS/Linux: `sh <skill-directory>/scripts/inspect-host.sh`
   - Windows: `powershell.exe -NoProfile -ExecutionPolicy Bypass -File <absolute-skill-directory>\scripts\inspect-host.ps1`
3. Locate the Agent from the returned JSON. Never assume it is on `PATH`.
4. If the Agent supports it, run its absolute path with `capabilities --output json` once and retain the result for this task. Use `runtime.kind`, `enrollment`, `daemon.manager`, `daemon.healthy`, `browser.features`, and `jobs.features` as the orchestration contract. On Linux, both Agent and host inspection may obtain this contract from the root-owned `/run/credential-agent/runtime.json`; do not require inherited shell environment. On an older Agent, feature-detect commands from `help`; do not infer runtime type from virtualization or parse localized output.
5. Classify the request as setup, browser repair, sync, revoke/cleanup, status, or diagnosis.
6. Read only the relevant reference:
   - Setup or browser work: [browser-installation.md](references/browser-installation.md)
   - Sync or command selection: [agent-command-map.md](references/agent-command-map.md)
   - Configuration files: [file-profiles.md](references/file-profiles.md)
   - Failures or recovery: [troubleshooting.md](references/troubleshooting.md)

## Install or update the Agent

If the Agent is missing or cannot execute `help`, run the matching bootstrap wrapper. The wrappers download a signed release manifest, verify its Ed25519 signature, select the exact OS/architecture artifact, and verify length and SHA-256 before installing. GitHub ZIP installation may clear Unix executable bits, so always invoke bundled scripts through their interpreter instead of executing the file directly.

- macOS: `sh <skill-directory>/scripts/bootstrap-agent-macos.sh`
- Linux: `sh <skill-directory>/scripts/bootstrap-agent-linux.sh`
- Windows: `powershell.exe -NoProfile -ExecutionPolicy Bypass -File <absolute-skill-directory>\scripts\bootstrap-agent-windows.ps1`

If the Agent exists and executes `help`, do not update it merely because a task started. Use the signed `update` path only when the user requested an update, capability detection shows that the installed version lacks a command required for the task, or diagnosis identifies a broken/outdated Agent. Do not paste `set -euo pipefail` into an interactive shell. Do not replace a running Windows executable manually.

After installation, rerun host inspection and invoke the returned absolute Agent path with `help`.

Run bootstrap through the execution channel already provided for the target. If that channel supports durable background tasks, retain its task ID and poll its structured terminal status and exit code; otherwise use a yielded foreground session. Never infer remote completion from a client transport timeout. Use background execution only for non-sensitive bootstrap output, never setup or pairing.

## Initialize a personal computer

1. Determine the role from existing Agent state, then the user's explicit wording. Do not infer cloud role solely from virtualization.
2. Run `credential-agent setup --role personal --skip-browser` in an interactive terminal. If capabilities report `daemon.manager=external`, append `--daemon-manager external`; this is the AIO/external-supervisor contract. Otherwise omit the flag and let the Agent use the platform manager.
3. Let the Agent open OAuth Device Flow. Do not read, fill, or log passwords, verification codes, access tokens, or refresh tokens.
4. Wait for setup to exit successfully. On cancellation, preserve existing state and stop.
5. Complete the browser workflow below unless the user explicitly asks to skip it.
6. Run `credential-agent doctor --strict`.

Do not re-enroll a device whose authorization is valid. Repeated setup should repair only unhealthy components.

## Initialize a cloud or peer computer

1. When capabilities/help advertises phased cloud setup, use foreground `setup --role cloud --skip-browser [--daemon-manager MANAGER] --pair-phase begin --output json`, approve its short-lived pairing code, then run the matching `--pair-phase complete --pair-timeout 2m --output json`. Use the capability-reported daemon manager on every OS; append `external` only when reported. Never put either call in a generic background task.
2. On an older Agent without phased setup, run `credential-agent setup --role cloud --skip-browser` interactively and use its reported daemon manager.
3. If a separate, already logged-in personal-computer execution channel is available, show the pending device to the user. After explicit approval, prefer its absolute Agent path with `credential-agent pair --approve --output json CODE`; use interactive `credential-agent pair CODE` only for an older Agent without these flags.
4. Otherwise show exactly one local approval command. Do not copy device credentials or OAuth tokens between computers.
5. Wait for the cloud setup process to finish, then complete browser setup and run `doctor --strict`.

Never store the pairing code in a file. Regenerate it after expiry.

## Prepare and connect Chrome or Chromium

Follow [browser-installation.md](references/browser-installation.md).

For an Agent exposing the staged browser commands, prefer this state-driven sequence:

```text
credential-agent browser prepare [--user-data-dir DIR ...] --output json
credential-agent browser status --output json
credential-agent browser open-install --output json       # only when disconnected/version-mismatched
credential-agent browser wait --for connected --timeout 10m --output json
credential-agent browser configure-policies --output json
credential-agent browser open-permissions --output json   # only when required
credential-agent browser wait --for permissions --timeout 10m --output json
```

Choose the preparation branch from `capabilities.browser.distribution_mode` or the target Connector contract; never infer it from the OS alone:

- `unpacked`: personal computers, Linux sandboxes, and a development CUA whose Connector explicitly owns visible unpacked installation. Generic endpoints use the sequence above. A my-cua Connector instead owns `prepare`, canonical Browser Owner launch, CDP extension-page actions, and the constrained native folder-picker step.
- `managed_store`: only a target whose platform contract explicitly selects a published Chrome Web Store item. The Connector must supply the exact Store `extension_id`, expected build id, and numeric manifest version. Do not infer this mode merely because the target is Windows.
- `managed_self_hosted`: only an AD/Azure AD/Chrome Enterprise managed Windows target. Agent verifies CRX/update metadata and serves the policy update from its loopback provider. Do not select this merely because the target is Windows.

When a target has a Credential Agent Connector, let that Connector own `prepare`, Browser Owner launch, installation/reload, and version readiness. In my-cua unpacked mode, do not separately run `open-install` or start screenshot-driven UI automation: the Connector uses authenticated CDP for `chrome://extensions/` and UIA only for the Chrome-owned native folder picker. Use the target control channel only for the exact permission handoff it reports. This keeps the Skill generic for Linux sandboxes and other endpoints.

For the configured development my-cua, invoke the local `$my-cua-dev` script before target restore:

```text
python3 <my-cua-dev-skill-dir>/scripts/cua.py credential-browser ensure
```

Do not delegate a CUA model task to install the extension. The command is an idempotent Connector operation and creates no model run. This conditional integration does not replace the generic Linux/macOS unpacked workflow.
If it returns `ready=true, connected=false`, continue device pairing and rerun the check afterward; this is installation readiness only and must not be reported as `browser_ready`.

`prepare` performs local manifest and signed-artifact work without waiting for pairing or daemon health, so an orchestrator may run it while the user completes OAuth/pair approval. `status` decides which UI action is actually needed. Do not reopen installation or permissions pages when the corresponding state is already ready.

`open-install` and `open-permissions` report only that Chrome accepted an open request. Confirm the visible internal URL through the browser-control channel already provided for the target, and navigate explicitly when Chrome ignores the launch request.

For an older compatible Agent, use the combined fallback:

```text
credential-agent browser setup --timeout 10m
```

Read `chrome.user_data_dirs` from the host inspection result. When it is non-empty, append each exact absolute directory as a repeatable flag:

```text
credential-agent browser setup --user-data-dir /absolute/browser/user-data --timeout 10m
```

Current Linux Agents also discover same-user running Chrome/Chromium processes, resolve symlink aliases, and merge their effective `--user-data-dir` automatically. Keep passing the canonical host-inspected directories for deterministic orchestration and compatibility with older Agents. A root AIO runtime uses `/root/.config/browser`; `/home/root` is only a compatibility symlink and must not produce a second browser profile. Never copy a Native Messaging manifest into that directory yourself; let Agent validate the directory and install the binding.

Run `browser wait` or the legacy `browser setup` in a yielded terminal session because it waits for extension connection and permissions. While it waits:

1. Prefer the target Credential Agent Connector when it declares deterministic browser setup; otherwise use visible UI automation through browser/computer control when available.
2. In `unpacked` mode only, use semantic labels such as `开发者模式`, `Developer mode`, `加载未打包的扩展程序`, `Load unpacked`, `选择文件夹`, and `Select Folder`.
3. In `unpacked` mode only, select the Agent-managed `chrome-extension` directory already opened by the Agent.
4. In either managed mode, never enter developer mode or select a directory. If the managed extension is absent, stop on the Connector/Agent policy or release error. In my-cua unpacked mode, let the Connector own these actions instead of duplicating them here.
5. If UI automation is unavailable, leave the detected browser and the required page open and ask for the single minimum action described in the browser reference.
6. Do not ask the user to return to the terminal or type that installation is complete. Let Agent heartbeat detection continue.
7. On the extension options page, activate only the exact requested site permission control (or the bounded “enable supported sites” capability control), verify the displayed origins match Agent-delivered policy, then let the Agent validate permissions.

Site support is controlled by Credential Vault dynamic policy, not by an extension build-time registry. Trust only policies that the Agent fetched and verified. The extension heartbeat reports cached policy digests and granted origins; do not treat it as the policy authority or hardcode site names/counts. On a device-only cloud endpoint, a site's policy may first arrive while its target Sync Job is being processed. A compatible Agent sends a metadata-only `UPDATE_SITE_POLICY`, keeps the same Job active until the extension heartbeat confirms the exact digest and origins are authorized, and only then sends the Cookie-bearing Restore task. If Agent opens the permission page, approve only the exact origins displayed for that policy; do not create a second Job.

`启用全部支持的网站` is capability authorization, not a request to sync every site. For a user request naming GitHub, invoke selected-site sync for GitHub only. Use `browser sync --all` only when the user explicitly requests all supported authenticated sites.

Stop automation immediately on an unexpected permission dialog, locked desktop, disconnected remote desktop, or uncertain target directory.

## Select a target and sync

Read [agent-command-map.md](references/agent-command-map.md) before selecting commands.

For browser sync, fail fast on the personal/source computer before creating or initializing a new target when `browser.features` contains `validate` (or older `help` explicitly lists `browser validate`):

```text
credential-agent browser validate --output jsonl SITE...
```

This uses `VALIDATE_SITE` only; it does not read, capture, or upload Cookie material. Continue target provisioning only when the final result is `succeeded` and every requested site is `authenticated`. If an older Agent does not advertise or list `validate`, skip this standalone preflight and let the later capture phase validate; do not call an unknown command or parse its error text.

1. Run `credential-agent devices`. If `devices --output json` is supported, prefer it.
2. Match an explicitly named target exactly. Auto-select only when exactly one active peer/cloud target exists.
3. Summarize resource names/types and the target before invoking Agent. Never reveal values.
4. Keep Secret values in Agent's hidden input. Never place them in arguments, a script, clipboard, logs, or Codex context.
5. For browser sessions and high-risk credential sets, preserve the Agent's explicit confirmation.
6. Treat submission and delivery as different states. Report success only when the Agent reports the target received the item; otherwise report pending, partial, cancelled, or failed.
7. Retain the exact enrolled device ID returned for a temporary target. When that target is decommissioned, revoke the exact ID with `device revoke --yes --output json`; never revoke by display name.

For Agent orchestration, once the exact target and site list have already been shown and approved, prefer `browser sync --to DEVICE --yes --output jsonl SITE...`. Consume JSONL phase events and the final result instead of answering localized prompts through a PTY. Fall back to interactive mode only when feature detection shows an older Agent.

Treat JSONL as a stage protocol, not localized text: retain `operation_id`, read each phase `status` and `duration_ms`, and wait for the final `result`. For browser sync, inspect `details.policies.checked`, `already_current`, and `updated`; `updated=0` with every checked policy already current means Agent safely skipped policy writes and the 30-second policy heartbeat wait. This is not a skipped login capture or delivery.

Keep the source sync process in a foreground/yielded session and consume JSONL incrementally. As soon as the `create_sync_job` phase succeeds, retain `details.job.id` and immediately inspect the target's own browser status and visible tabs through whatever execution/browser channel was provided for that target. Do this while the same source process continues waiting; do not wait for its fixed delivery window to expire first. If the target shows the exact policy-origin permission page, complete that visible user-gesture flow and let the original Job continue. This is upper-level orchestration and must not depend on a Sandbox Skill or assume the target is Linux.

For a configured my-cua target, replace repeated cached status reads with its
request-scoped exact-site adapter while the same source process remains active:

```text
python3 <my-cua-dev-skill-dir>/scripts/cua.py credential-browser authorize SITE...
```

This my-cua-specific command is only an adapter around Connector probes and the
exact Chrome permission gesture. It does not change this Skill's generic Agent
workflow, does not capture Cookie material, and must not be used for Linux
sandboxes or non-CUA endpoints.

If the source command finishes with `pending_target`, continue the exact Job instead of resubmitting the browser capture:

```text
credential-agent job status JOB_ID --output json
credential-agent job wait JOB_ID --timeout 5m --output jsonl
```

Use these commands only when `jobs.features` advertises them or `help` lists `job status|wait`. On older Agents, use the existing governance job/audit views only for diagnosis and keep the result pending; never create a duplicate Job merely to learn whether the first one finished.

If delivery reports `BROWSER_VALIDATION_TIMED_OUT` or `BROWSER_VALIDATION_FAILED`, do not resubmit the restore. A compatible target Agent already performs one validate-only retry after the browser mutation completes. Wait for the authoritative final job result; retry only `VALIDATE_SITE` during diagnosis, never the Cookie restore.

Never offer an all-environment-variables operation. Only sync names the user explicitly selected.

## Diagnose and recover

Run these in order, using the absolute Agent path:

```text
credential-agent status --output json
credential-agent doctor --strict --output json
credential-agent devices --output json
```

Use these structured forms only after capability/feature detection confirms them; otherwise use the legacy commands and exit status. Never parse localized human prose in scripts. Then apply [troubleshooting.md](references/troubleshooting.md).

Keep device enrollment, browser integration, and artifact updates as separate states. A browser failure must not erase valid device enrollment. An Agent update must not force pairing when authorization remains valid.

## Completion criteria

Report readiness in two layers. `device_ready` requires:

- Agent executes from the standard per-user path.
- Device credential is valid.
- Device key store and cache are usable.
- Background Agent is running.
- OAuth checks pass on a personal computer; device-only cloud endpoints may skip them.

`browser_ready` additionally requires:

- Native Messaging manifest is valid.
- Chrome/Chromium extension is connected and its running version matches the Agent-managed version.
- On a personal computer, all currently enabled Vault site policies are installed and their required origins are authorized. A device-only cloud endpoint may authorize a policy while its first target Sync Job is being processed.
- `doctor --strict` exits successfully.

If the user explicitly skips browser integration, report `device_ready=true` and `browser_ready=skipped`. A browser repair failure must not downgrade valid device enrollment. Never report a partial browser state as fully complete.
