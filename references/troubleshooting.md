# Troubleshooting

## Table of contents

- Initial evidence
- Agent installation/update
- Device authorization
- Background Agent
- Pairing
- Browser integration
- Sync and delivery
- Network

## Initial evidence

Run from the absolute Agent path:

```text
credential-agent capabilities --output json
credential-agent status --output json
credential-agent doctor --strict --output json
credential-agent devices --output json
```

Use structured commands only if feature detection succeeds. On a legacy Agent, use human commands plus exit status; do not parse localized prose in scripts. Keep diagnostic logs free of sensitive values.

## Agent installation/update

- Missing executable: run the platform bootstrap wrapper.
- Existing executable lacks `update`: bootstrap may perform a verified direct install on macOS/Linux; on Windows do not overwrite a running file. Close Chrome or stop its Native Host only when the wrapper explicitly requests it.
- Download interruption: keep the old executable, retry with proxy environment variables if authorized, and rely on manifest size/SHA-256 validation.
- Signature/hash mismatch: stop. Do not install or retry from an untrusted alternate URL.
- Windows staged update lock: the background scheduled task and Chrome Native Host may both hold the executable. Use current Agent updater; do not repeatedly force-copy over the running binary.

## Device authorization

- Expired personal device: rerun `setup --role personal --skip-browser`; complete OAuth.
- Expired cloud device: rerun `setup --role cloud --skip-browser`; approve a new pairing code.
- Valid authorization after update: do not re-enroll.
- Corrupt state: stop and preserve it for diagnosis. Do not delete device keys unless Agent explicitly reports unrecoverable corruption.

## Background Agent

First inspect `capabilities.daemon`. If `manager=platform`, rerun role-appropriate `setup --skip-browser`; it repairs LaunchAgent, `systemd --user`, or Windows Scheduled Task. Do not manually edit task XML or plist files as the first response.

If `manager=external`, do not install a platform service. The owning image/desktop supervisor must already be running; in AIO, the root watcher may start before enrollment and should make `daemon.healthy=true` as soon as the signed Agent binary appears. Check the external supervisor and binary path, then rerun setup with `--daemon-manager external`. `manager=none` means the caller must keep a foreground Agent alive.

On Windows, invoke an executable variable with `& $Agent doctor`, not `$Agent doctor`.

## Pairing

- Pair code expired: restart cloud setup and use the new code.
- Approval command requires a logged-in workstation Agent; a device-only cloud Agent cannot approve its own code.
- Agent orchestration appears stuck after sending `Y\n`: the interactive CLI uses raw terminal ReadLine and may still be waiting for carriage return. Stop guessing prompt state; after explicit user approval use `pair --approve --output json CODE` on a compatible Agent.
- Structured pair returns `CLI_USAGE`: supply exactly one of `--approve` or `--deny`, plus the pairing code.
- Do not send pairing codes through persistent files or logs.

## Browser integration

- Chrome opens but not `chrome://extensions/`: rerun Agent browser setup, then use the safe browser-assist script and visible UI.
- For staged setup, inspect `browser status --output json` before reopening anything. Run `open-install` only for disconnected/version-mismatched state, and run `open-permissions` only after `configure-policies` when authorization is incomplete.
- Extension directory exists but Agent waits: verify the fixed ID, reload the extension, and wait for heartbeat. Directory presence is insufficient.
- Running/prepared versions differ: reload; if still mismatched, remove only the AL extension and load the managed directory again.
- Options page says enabled but Agent reports incomplete: click enable-all again, accept the Chrome permission prompt, and wait for a new heartbeat.
- Locked/disconnected cloud desktop: pause UI automation until an active visible session exists.
- Site reports unauthenticated: ensure the source browser is actually logged in and the extension version/permissions are current. Do not expand cookie allowlists from the Skill.
- `prepare_browser` is slow: inspect JSONL `details.policies`. If `updated` is nonzero, Agent is applying stale/missing policy digests; if every checked policy is `already_current`, a compatible Agent should skip policy writes and the 30-second digest wait.
- `SITE_PERMISSION_REQUIRED`: Agent opened the extension options page, but Chrome still requires a visible user gesture for the exact origins. Complete that gesture; `--yes` does not bypass browser permission prompts.

## Sync and delivery

- Target receives before manual `pull`: normal; background Agent may have already consumed the assignment.
- `pull` says nothing pending after source reports received: normal and not a version mismatch.
- `pending_target`: verify target `doctor`, background Agent, network, and authorization.
- A current target holds a bounded long poll for assignments; normal pickup should not require repeated manual `pull`. A persistent delay indicates daemon/network/authorization health, not a reason to increase Skill sleeps.
- Machine output must end with a `result` event. Do not report success from an intermediate `phase` event, even when Capture succeeded.
- `BROWSER_VALIDATION_TIMED_OUT` or `BROWSER_VALIDATION_FAILED` after restore means the browser mutation completed but login validation could not be confirmed. A current Agent retries `VALIDATE_SITE` once without restoring Cookie or Local Storage again. Do not restart the whole sync automatically; use the final job status.
- An older target reporting `browser_restore_failed(BROWSER_OPERATION_FAILED)` after a visibly authenticated first-party page may be conflating validation with restore. Update the target Agent and extension before retrying; do not infer success from the page alone.
- Partial browser sync: retry only failed sites after source/target validation.
- Reauthentication required: the destination site or policy rejected the restored session. Do not bypass site validation.

## Network

Classify the failing origin: OAuth, Credential Vault, artifact TOS, or target website. Proxy settings may be provided through `HTTP_PROXY`, `HTTPS_PROXY`, and `NO_PROXY` when the user authorizes them. In an AIO sandbox, let the Sandbox Skill call its explicit `ConfigureBrowserProxy` tool before browser setup or sync; do not edit `/run/gem/browser-supervisor.json` manually. Keep this sandbox-only mechanism separate from Windows cloud-computer proxy handling. Never clear valid login/device state merely because a network request failed.
