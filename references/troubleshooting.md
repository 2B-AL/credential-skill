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
credential-agent status
credential-agent doctor --strict
credential-agent devices
```

Prefer JSON output only if feature detection succeeds. Do not parse localized prose in scripts. Keep diagnostic logs free of sensitive values.

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

Rerun role-appropriate `setup --skip-browser`; it repairs LaunchAgent, `systemd --user`, or Windows Scheduled Task. Do not manually edit task XML or plist files as the first response.

On Windows, invoke an executable variable with `& $Agent doctor`, not `$Agent doctor`.

## Pairing

- Pair code expired: restart cloud setup and use the new code.
- Approval command requires a logged-in workstation Agent; a device-only cloud Agent cannot approve its own code.
- Do not send pairing codes through persistent files or logs.

## Browser integration

- Chrome opens but not `chrome://extensions/`: rerun Agent browser setup, then use the safe browser-assist script and visible UI.
- Extension directory exists but Agent waits: verify the fixed ID, reload the extension, and wait for heartbeat. Directory presence is insufficient.
- Running/prepared versions differ: reload; if still mismatched, remove only the AL extension and load the managed directory again.
- Options page says enabled but Agent reports incomplete: click enable-all again, accept the Chrome permission prompt, and wait for a new heartbeat.
- Locked/disconnected cloud desktop: pause UI automation until an active visible session exists.
- Site reports unauthenticated: ensure the source browser is actually logged in and the extension version/permissions are current. Do not expand cookie allowlists from the Skill.

## Sync and delivery

- Target receives before manual `pull`: normal; background Agent may have already consumed the assignment.
- `pull` says nothing pending after source reports received: normal and not a version mismatch.
- `pending_target`: verify target `doctor`, background Agent, network, and authorization.
- Partial browser sync: retry only failed sites after source/target validation.
- Reauthentication required: the destination site or policy rejected the restored session. Do not bypass site validation.

## Network

Classify the failing origin: OAuth, Credential Vault, artifact TOS, or target website. Proxy settings may be provided through `HTTP_PROXY`, `HTTPS_PROXY`, and `NO_PROXY` when the user authorizes them. Never clear valid login/device state merely because a network request failed.
