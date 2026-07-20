# Security rules

Read this file before every AL credential operation.

## Trust boundaries

- Invoke only the public `credential-agent` CLI. Do not call Credential Vault, OAuth enrollment, or Provider internal HTTP endpoints directly.
- Let Agent own device keys, DPoP, encryption, Secret Cache, browser capture/restore, and local background services.
- Do not read or edit the Agent state directory except through bundled read-only host inspection.
- Do not read Chrome Cookie databases, Local Storage databases, `Secure Preferences`, or Profile files.
- Do not forge Chrome enterprise management or modify extension allowlists at runtime.

## Sensitive data

Never place these in Codex context, shell arguments, shell history, logs, clipboard, temporary scripts, or task artifacts:

- Secret or environment-variable values
- Cookie or Local Storage values
- Access, refresh, device, enrollment, or pairing approval tokens
- Device credentials or private keys
- Decrypted configuration-file contents
- AK/SK, passwords, TLS private keys, OAuth client secrets

Secret values must be entered through Agent's no-echo prompt. Environment variables may be named in commands, but their values must not be printed. Configuration files must be passed by path without reading their contents.

## Authorization

- Confirm the exact target device before every sync.
- Preserve Agent confirmation for browser sessions and high-risk credentials.
- Sync only explicitly named environment variables. Never implement `env --all`.
- Do not infer permission to sync every website from permission to sync one website.
- Do not silently select among multiple devices with similar names.
- Treat pairing codes as short-lived. Do not persist or reuse them.
- Never run cloud setup or pairing through a generic background task that retains commands or stdout. On supported AIO Agents, use foreground `setup --pair-phase begin|complete`; keep Windows on its capability-reported interactive path.

## Browser automation

- Operate only a visible, unlocked desktop.
- Use semantic UI labels and visible state, not fixed screen coordinates as the sole locator.
- Select only the exact absolute extension directory returned or opened by Agent.
- Stop on an unexpected Chrome permission prompt or unclear directory.
- Do not bypass Chrome's user-gesture or unpacked-extension protections.

## Cleanup

Before revoke or cleanup, state whether the action affects central snapshots, future synchronization, target-browser cookies, restored files, or local cached resources. Do not imply that `browser revoke` clears every already-restored browser cookie unless the running Agent explicitly reports that result.

## Logs

Allowed: command name, resource reference, device display name/type, Agent or extension version, job ID, status/error code, timestamp, duration, retry count.

Forbidden: every sensitive value listed above. Retain failure logs only when non-sensitive and necessary, and return their absolute path.
