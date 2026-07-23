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
- Execution-channel timeout during bootstrap: if the channel supports durable background tasks, require its task ID, terminal status, and exit code. A client transport timeout is not a remote task state; otherwise resume or inspect through the same channel instead of blindly rerunning bootstrap.
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
- On root AIO, prefer foreground `setup --pair-phase begin --output json`, approve the exact pending device, then call `setup --pair-phase complete --output json`. On Windows, continue using its reported platform manager and interactive setup.

## Browser integration

- Inspect `browser status --output json` and its `distribution_mode` before reopening anything. Do not infer the repair path from Windows/Linux alone.
- In generic `unpacked` mode, Chrome opens but not `chrome://extensions/`: rerun the Agent open-install step, then use the safe browser-assist script and visible UI.
- In my-cua `unpacked` mode, run the Connector's `credential-browser ensure`; do not duplicate it with `open-install`, screenshot-driven UI automation, or extension-page UIA. CDP owns Chrome controls and UIA is limited to the native folder picker.
- In either managed mode, never open developer mode or load a directory. An absent or stale extension is a Chrome Policy, Store publication, release identity, or signed-artifact error.
- `managed_store` reports missing identity: configure the exact published Store item ID, build ID, and numeric manifest version in the platform Connector; do not fall back to the self-hosted ID.
- `managed_self_hosted` reports provider unavailable: verify the enterprise-management prerequisite, signed CRX/update manifest state, Agent loopback provider, and Chrome policy.
- In unpacked mode, extension directory exists but Agent waits: verify the expected ID, reload the extension, and wait for heartbeat. Directory presence is insufficient.
- Running/expected ID, build, or manifest differs: repair through the selected distribution channel. Only unpacked mode may remove and reload the Agent-managed directory.
- Options page says enabled but Agent reports incomplete: click enable-all again, accept the Chrome permission prompt, and wait for a new heartbeat.
- Locked/disconnected cloud desktop: pause UI automation until an active visible session exists.
- Site reports unauthenticated: ensure the source browser is actually logged in and the extension version/permissions are current. Do not expand cookie allowlists from the Skill.
- `prepare_browser` is slow: inspect JSONL `details.policies`. If `updated` is nonzero, Agent is applying stale/missing policy digests; if every checked policy is `already_current`, a compatible Agent should skip policy writes and the 30-second digest wait.
- `SITE_PERMISSION_REQUIRED`: Agent opened the extension options page, but Chrome still requires a visible user gesture for the exact origins. Complete that gesture; `--yes` does not bypass browser permission prompts.

## Sync and delivery

- Target receives before manual `pull`: normal; background Agent may have already consumed the assignment.
- `pull` says nothing pending after source reports received: normal and not a version mismatch.
- `pending_target`: keep the returned Job ID, verify target `doctor`, background Agent, network, and authorization, then run `credential-agent job wait JOB_ID --timeout 5m --output jsonl` when advertised. Do not rerun the original sync.
- A current target holds a bounded long poll for assignments; normal pickup should not require repeated manual `pull`. A persistent delay indicates daemon/network/authorization health, not a reason to increase Skill sleeps.
- For browser jobs, begin target-side visible permission inspection immediately after the source JSONL `create_sync_job` phase rather than after the source wait window. Approve only the exact policy origins, and leave the original Job active.
- Machine output must end with a `result` event. Do not report success from an intermediate `phase` event, even when Capture succeeded.
- `BROWSER_VALIDATION_TIMED_OUT` or `BROWSER_VALIDATION_FAILED` after restore means the browser mutation completed but login validation could not be confirmed. A current Agent retries `VALIDATE_SITE` once without restoring Cookie or Local Storage again. Do not restart the whole sync automatically; use the final job status.
- An older target reporting `browser_restore_failed(BROWSER_OPERATION_FAILED)` after a visibly authenticated first-party page may be conflating validation with restore. Update the target Agent and extension before retrying; do not infer success from the page alone.
- Partial browser sync: retry only failed sites after source/target validation.
- Reauthentication required: the destination site or policy rejected the restored session. Do not bypass site validation.

## Network

Classify the failing origin: OAuth, Credential Vault, artifact TOS, or target website. Proxy settings may be provided through `HTTP_PROXY`, `HTTPS_PROXY`, and `NO_PROXY` when the user authorizes them. Browser or operating-system proxy configuration belongs to the target execution environment; use only its explicit managed interface and never edit browser supervisor files from this Skill. Never clear valid login/device state merely because a network request failed.
