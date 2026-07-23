# Browser installation and repair

## Table of contents

- Capability boundary
- State machine
- Visible UI assistance
- Manual fallback
- Permission authorization
- Upgrade repair
- Final validation

## Capability boundary

Official unmanaged Chrome on Windows/macOS and Chromium on Linux cannot silently force-install a private unpacked extension. A development CUA may automate the same visible Developer mode and Load unpacked flow through its trusted desktop Connector, provided it does not modify browser profile files or bypass user-gesture requirements. Off-store policy force installation remains reserved for domain/enterprise-managed Windows.

On Linux, the Agent supports both native-host locations:

- Chrome: `~/.config/google-chrome/NativeMessagingHosts`
- Chromium: `~/.config/chromium/NativeMessagingHosts`

Those are only the default user-data locations. Chrome/Chromium resolves the user-level Native Messaging directory from its effective user-data directory. Current Linux Agents automatically discover same-user running main-browser processes, resolve symlink aliases, and merge their effective `--user-data-dir`; the Skill should still pass every canonical host-inspected absolute directory with repeatable `--user-data-dir` flags for deterministic orchestration and older-Agent compatibility. Root AIO publishes `/root/.config/browser` in `/run/credential-agent/runtime.json`; `/home/root` is a compatibility alias, not a second profile. Agent must validate and install the additional binding; the Skill must not copy or link manifests into browser data directories.

Only one browser needs to be installed. A missing manifest for an unused default browser is healthy; an existing malformed or mismatched manifest is not.

Current Agents expose a staged, machine-readable workflow:

```text
credential-agent browser prepare [--user-data-dir DIR ...] --output json
credential-agent browser status --output json
credential-agent browser open-install --output json
credential-agent browser wait --for connected --timeout 10m --output json
credential-agent browser configure-policies --output json
credential-agent browser open-permissions --output json
credential-agent browser wait --for permissions --timeout 10m --output json
```

The status contract also exposes `distribution_mode`, `expected_extension_id`, `expected_build_id`, and `expected_manifest_version`. Treat their combination as the browser identity:

| Mode | Intended environment | Install action |
|---|---|---|
| `unpacked` | personal macOS/Linux, Linux sandboxes, and my-cua development Windows | visible one-time Load unpacked; my-cua Connector may drive it deterministically |
| `managed_store` | environment explicitly configured for a published Store item | Chrome Web Store policy; no developer-mode UI |
| `managed_self_hosted` | AD/Azure AD/Chrome Enterprise Windows | verified CRX through Agent loopback policy; no developer-mode UI |

`managed_store` requires a published Store item. A missing item ID/build/manifest version is a release-configuration blocker only for targets that selected this mode; it does not change an explicitly `unpacked` CUA contract.

The compatible fallback for older Agents is:

```text
credential-agent browser setup --timeout 10m
```

For a managed browser with a custom user-data directory:

```text
credential-agent browser setup --user-data-dir /absolute/browser/user-data --timeout 10m
```

Both forms install Native Messaging, download and verify the signed extension artifact, prepare the managed directory, connect the detected Chrome/Chromium extension, deliver current dynamic policies, authorize supported-site origins, and validate the running version. The staged form separates local preparation, UI action, policy delivery, and waits so an Agent orchestrator does not hold an opaque 10-minute command or repeat completed UI steps.

## State machine

1. Run the distribution-appropriate `browser prepare --output json`, including every `chrome.user_data_dirs` value returned by host inspection. For my-cua unpacked mode, the Connector owns this invocation and validates the exact returned directory and fixed Extension ID. For `managed_store`, the platform must add exact Store ID/build/manifest flags. This step does not require enrollment or a healthy daemon and can overlap OAuth/pair approval.
2. Run `browser status --output json`. Require connected runtime ID/build/manifest to match expected values.
3. In unpacked mode only, run `open-install` when disconnected or stale and repair the exact Agent-managed directory. In managed modes, installation or update failure is a policy/release error; do not open developer mode.
4. Run `browser configure-policies --output json`. `deferred=true` is valid only for a device-only endpoint where the first restore task will deliver the exact policy.
5. Inspect `browser status` again. If every reported supported site is authorized, skip permission UI. Otherwise run `open-permissions`, approve exact origins, and yield on `wait --for permissions`.
6. Continue to `doctor --strict --output json` and require Agent-observed state; do not infer success from an extension card or dialog alone.

The `open-*` JSON contract is request-oriented: `requested=true` and `verified=false` means Chrome accepted a launch request, not that the internal page is visibly active. Generic targets confirm the internal page through their visible browser-control channel. A my-cua Connector instead opens `chrome://extensions/` through its authenticated CDP broker and uses the fixed extension options URL for permission handoff.

If feature detection shows that staged commands are unavailable, run legacy `browser setup` in a yielded terminal and follow the same visible UI rules.

This authorization step establishes the allowed capability range only. It must not be translated into a later `browser sync --all`; selected-site requests remain selected-site actions.

Do not require staged commands on older releases and do not update a healthy Agent solely to avoid the legacy fallback unless the task requires deterministic machine orchestration.

## Visible UI assistance

Use browser or computer control only on an unlocked visible desktop.

Semantic labels:

- `开发者模式` / `Developer mode`
- `加载未打包的扩展程序` / `Load unpacked`
- `选择文件夹` / `Select Folder`
- `重新加载` / `Reload`
- `启用全部支持的网站` / `Enable all supported sites`

Unpacked installation procedure only:

1. Confirm the page is `chrome://extensions/`.
2. Enable developer mode if necessary.
3. Click Load unpacked.
4. Select the exact `chrome-extension` directory already opened by Agent.
5. Confirm the installed extension ID is `lnpfljjigmgmakiclchpnoehbbceomeb`.
6. Let Agent determine whether the heartbeat version matches.

Managed installation has no extension-management procedure. Once Chrome Policy installs the extension, the only visible browser action that may remain is exact Origin permission authorization. A my-cua Connector may use its authenticated CDP broker to open only `chrome-extension://<expected-id>/options.html`; do not use raw CDP, arbitrary page eval, or Cookie methods.

### my-cua Connector-owned unpacked automation

For a my-cua target whose contract is `unpacked`, do not repeat the generic visible procedure from the Skill. The Connector must:

1. Use Agent `browser prepare` and accept only the Agent-managed absolute `chrome-extension` directory and fixed Extension ID.
2. Use authenticated CDP to open/foreground `chrome://extensions/`, inspect its Accessibility tree, and activate Developer mode, Load unpacked, or the matching extension card's Reload action. If no unique actionable CDP node exists, fail closed; do not fall back to extension-page UIA.
3. Use UIA only after a foreground window matches both the Chrome process and `Select Folder`/`选择文件夹`; enter the exact Agent directory without coordinates.
4. Return to Agent `wait`, policy configuration, and structured `browser status` for success. An extension card or closed dialog alone is not success.
5. Never use screenshots, arbitrary JavaScript evaluation, profile file edits, or CDP Network/Storage Cookie methods to advance the successful path. A screenshot is terminal diagnostic evidence only.

Use `sh scripts/browser-assist-macos.sh DIRECTORY` or invoke `scripts/browser-assist-windows.ps1 -ExtensionDirectory DIRECTORY` through PowerShell only when Agent failed to open the page/directory. These scripts prepare visible state; they do not install or modify the browser. On Linux, use the browser opened by Agent; it detects `google-chrome`, `google-chrome-stable`, `chromium`, and `chrome`. Do not rely on Unix executable bits surviving GitHub ZIP installation.

## Manual fallback

If UI control is unavailable, display only:

```text
Chrome/Chromium 已打开。

请点击“加载未打包的扩展程序”。
文件夹选择窗口出现后，选择已经打开的 chrome-extension 文件夹。

安装完成后无需返回终端，我会自动继续。
```

Do not ask the user to type `Y` or confirm completion in the terminal. Leave Agent waiting.

## Permission authorization

After connection, Agent fetches the currently enabled Vault policies and opens the extension options page. Chrome requires `optional_host_permissions` requests to originate from a user gesture, including for a preinstalled extension. Use visible UI to activate the exact site permission control and accept the expected host-permission prompt. Stop if the prompt requests permissions outside the exact origins displayed for those policies.

The policy authority is Credential Vault. Extension heartbeat only reports the policy digests it cached and the origins the browser granted. Do not assume a fixed count or silently omit newly configured sites. On a device-only cloud endpoint, the first restore task may install one policy and trigger its exact permission prompt; leave Agent running so it can retry after approval.

Repeated `browser setup` and selected-site sync are digest-aware. If the extension heartbeat already reports the exact Vault digest, Agent does not resend that policy or wait another 30 seconds for the same digest. Do not force a policy refresh merely because setup is being repeated; let Agent update only missing or stale policies.

## Upgrade repair

Directory presence is not success. Require:

- fixed extension ID
- recent Native Messaging heartbeat
- running version equals prepared version
- running policy digests match the Agent-delivered policies
- all policies already delivered to this endpoint have their required origins authorized

If versions differ, reload the extension card. If the browser continues running the old code, remove only this extension and load the same managed directory again.

## Final validation

Run:

```text
credential-agent doctor --strict
```

A cloud device may legitimately report device-only authorization and skip the user control-plane check. Any extension offline, version mismatch, invalid Native Messaging manifest, or incomplete permissions state prevents complete browser setup.
