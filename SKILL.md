---
name: al-credential-sync
description: Install, update, configure, diagnose, pair, and operate the AL credential-agent and Chrome or Linux Chromium credential extension across personal computers and cloud desktops. Use when Codex needs to initialize AL credential sync, complete OAuth or device pairing, prepare or repair the Chrome or Chromium extension and Native Messaging host, sync or revoke secrets, named environment variables, credential sets such as AK/SK, sensitive configuration files, browser sessions, dynamic credentials, or managed keys, inspect device or sync health, or recover an expired or unhealthy AL credential device.
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
4. Classify the request as setup, browser repair, sync, revoke/cleanup, status, or diagnosis.
5. Read only the relevant reference:
   - Setup or browser work: [browser-installation.md](references/browser-installation.md)
   - Sync or command selection: [agent-command-map.md](references/agent-command-map.md)
   - Configuration files: [file-profiles.md](references/file-profiles.md)
   - Failures or recovery: [troubleshooting.md](references/troubleshooting.md)

## Install or update the Agent

If the Agent is missing or cannot execute `help`, run the matching bootstrap wrapper. The wrappers download a signed release manifest, verify its Ed25519 signature, select the exact OS/architecture artifact, and verify length and SHA-256 before installing. GitHub ZIP installation may clear Unix executable bits, so always invoke bundled scripts through their interpreter instead of executing the file directly.

- macOS: `sh <skill-directory>/scripts/bootstrap-agent-macos.sh`
- Linux: `sh <skill-directory>/scripts/bootstrap-agent-linux.sh`
- Windows: `powershell.exe -NoProfile -ExecutionPolicy Bypass -File <absolute-skill-directory>\scripts\bootstrap-agent-windows.ps1`

If the Agent exists, prefer its signed `update` path through the same wrapper. Do not paste `set -euo pipefail` into an interactive shell. Do not replace a running Windows executable manually.

After installation, rerun host inspection and invoke the returned absolute Agent path with `help`.

## Initialize a personal computer

1. Determine the role from existing Agent state, then the user's explicit wording. Do not infer cloud role solely from virtualization.
2. Run `credential-agent setup --role personal --skip-browser` in an interactive terminal.
3. Let the Agent open OAuth Device Flow. Do not read, fill, or log passwords, verification codes, access tokens, or refresh tokens.
4. Wait for setup to exit successfully. On cancellation, preserve existing state and stop.
5. Complete the browser workflow below unless the user explicitly asks to skip it.
6. Run `credential-agent doctor --strict`.

Do not re-enroll a device whose authorization is valid. Repeated setup should repair only unhealthy components.

## Initialize a cloud or peer computer

1. Run `credential-agent setup --role cloud --skip-browser` in an interactive terminal.
2. Let the Agent display the short-lived pairing code.
3. If a separate, already logged-in personal-computer execution channel is available, show the pending device to the user. After explicit approval, prefer its absolute Agent path with `credential-agent pair --approve --output json CODE`; use interactive `credential-agent pair CODE` only for an older Agent without these flags.
4. Otherwise show exactly one local approval command. Do not copy device credentials or OAuth tokens between computers.
5. Wait for the cloud setup process to finish, then complete browser setup and run `doctor --strict`.

Never store the pairing code in a file. Regenerate it after expiry.

## Prepare and connect Chrome or Chromium

Follow [browser-installation.md](references/browser-installation.md).

Use the Agent's current compatible command:

```text
credential-agent browser setup --timeout 10m
```

Read `chrome.user_data_dirs` from the host inspection result. When it is non-empty, append each exact absolute directory as a repeatable flag:

```text
credential-agent browser setup --user-data-dir /absolute/browser/user-data --timeout 10m
```

This is required for managed Chrome/Chromium processes started with `--user-data-dir`. Never copy a Native Messaging manifest into that directory yourself; let Agent validate the directory and install the binding.

Run it in a yielded terminal session because it waits for extension connection and permissions. While it waits:

1. Prefer visible UI automation through browser/computer control when available.
2. Use semantic labels such as `开发者模式`, `Developer mode`, `加载未打包的扩展程序`, `Load unpacked`, `选择文件夹`, and `Select Folder`.
3. Select only the Agent-managed `chrome-extension` directory already opened by the Agent.
4. If UI automation is unavailable, leave the detected browser and the directory open and ask for the single minimum action described in the browser reference.
5. Do not ask the user to return to the terminal or type that installation is complete. Let Agent heartbeat detection continue.
6. On the extension options page, activate `启用全部支持的网站` or its English label, then let the Agent validate permissions.

Site support is controlled by Credential Vault dynamic policy, not by an extension build-time registry. Trust only policies that the Agent fetched and verified. The extension heartbeat reports cached policy digests and granted origins; do not treat it as the policy authority or hardcode site names/counts. On a device-only cloud endpoint, a site's policy may first arrive with its restore task. If Agent opens the permission page, approve only the exact origins displayed for that policy and let Agent retry.

`启用全部支持的网站` is capability authorization, not a request to sync every site. For a user request naming GitHub, invoke selected-site sync for GitHub only. Use `browser sync --all` only when the user explicitly requests all supported authenticated sites.

Stop automation immediately on an unexpected permission dialog, locked desktop, disconnected remote desktop, or uncertain target directory.

## Select a target and sync

Read [agent-command-map.md](references/agent-command-map.md) before selecting commands.

1. Run `credential-agent devices`. If `devices --output json` is supported, prefer it.
2. Match an explicitly named target exactly. Auto-select only when exactly one active peer/cloud target exists.
3. Summarize resource names/types and the target before invoking Agent. Never reveal values.
4. Keep Secret values in Agent's hidden input. Never place them in arguments, a script, clipboard, logs, or Codex context.
5. For browser sessions and high-risk credential sets, preserve the Agent's explicit confirmation.
6. Treat submission and delivery as different states. Report success only when the Agent reports the target received the item; otherwise report pending, partial, cancelled, or failed.

For Agent orchestration, once the exact target and site list have already been shown and approved, prefer `browser sync --to DEVICE --yes --output jsonl SITE...`. Consume JSONL phase events and the final result instead of answering localized prompts through a PTY. Fall back to interactive mode only when feature detection shows an older Agent.

Treat JSONL as a stage protocol, not localized text: retain `operation_id`, read each phase `status` and `duration_ms`, and wait for the final `result`. For browser sync, inspect `details.policies.checked`, `already_current`, and `updated`; `updated=0` with every checked policy already current means Agent safely skipped policy writes and the 30-second policy heartbeat wait. This is not a skipped login capture or delivery.

Never offer an all-environment-variables operation. Only sync names the user explicitly selected.

## Diagnose and recover

Run these in order, using the absolute Agent path:

```text
credential-agent status
credential-agent doctor --strict
credential-agent devices
```

Prefer `--output json` when the installed Agent accepts it; never parse localized human prose in scripts. Use exit status for legacy Agent compatibility. Then apply [troubleshooting.md](references/troubleshooting.md).

Keep device enrollment, browser integration, and artifact updates as separate states. A browser failure must not erase valid device enrollment. An Agent update must not force pairing when authorization remains valid.

## Completion criteria

For complete setup, require all of the following:

- Agent executes from the standard per-user path.
- Device credential is valid.
- Device key store and cache are usable.
- Background Agent is running.
- OAuth checks pass on a personal computer; device-only cloud endpoints may skip them.
- Native Messaging manifest is valid.
- Chrome/Chromium extension is connected and its running version matches the Agent-managed version.
- On a personal computer, all currently enabled Vault site policies are installed and their required origins are authorized. A device-only cloud endpoint may authorize a policy when its first restore task arrives.
- `doctor --strict` exits successfully.

If the user explicitly skips browser integration, report device setup as complete and browser setup as skipped. Never report a partial browser state as fully complete.
