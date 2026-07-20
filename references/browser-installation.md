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

Official unmanaged Chrome on Windows/macOS and Chromium on Linux cannot silently install a private unpacked extension. This Skill may prepare the signed extension and assist visible UI, but it must not modify browser profiles or bypass user-gesture requirements.

On Linux, the Agent supports both native-host locations:

- Chrome: `~/.config/google-chrome/NativeMessagingHosts`
- Chromium: `~/.config/chromium/NativeMessagingHosts`

Those are only the default user-data locations. Chrome/Chromium resolves the user-level Native Messaging directory from its effective user-data directory. If host inspection reports a process started with `--user-data-dir`, pass every reported absolute directory to Agent with repeatable `--user-data-dir` flags. Agent must validate and install the additional binding; the Skill must not copy or link manifests into browser data directories.

Only one browser needs to be installed. A missing manifest for an unused default browser is healthy; an existing malformed or mismatched manifest is not.

The current compatible Agent command is:

```text
credential-agent browser setup --timeout 10m
```

For a managed browser with a custom user-data directory:

```text
credential-agent browser setup --user-data-dir /absolute/browser/user-data --timeout 10m
```

It installs Native Messaging, downloads and verifies the signed extension artifact, prepares the managed directory, opens the detected Chrome/Chromium browser and the directory, waits for extension heartbeat, opens the permissions page, waits for supported-site authorization, and validates the running version.

## State machine

1. Start `browser setup` in a yielded terminal session, including every `chrome.user_data_dirs` value returned by host inspection.
2. If it exits successfully, continue to `doctor --strict`.
3. If it waits for connection, operate the visible browser UI or use the minimum manual fallback.
4. If an old extension is online, reload its card. If the running version remains old, remove only the AL Credential Center extension and load the Agent-managed directory again.
5. Wait for Agent to observe the expected version; do not infer success from the card alone.
6. Authorize all supported sites and wait for Agent heartbeat confirmation.

When future Agent versions expose `browser prepare/status/open-install/open-permissions/wait`, prefer those machine-readable commands. Do not require them on older releases.

## Visible UI assistance

Use browser or computer control only on an unlocked visible desktop.

Semantic labels:

- `开发者模式` / `Developer mode`
- `加载未打包的扩展程序` / `Load unpacked`
- `选择文件夹` / `Select Folder`
- `重新加载` / `Reload`
- `启用全部支持的网站` / `Enable all supported sites`

Procedure:

1. Confirm the page is `chrome://extensions/`.
2. Enable developer mode if necessary.
3. Click Load unpacked.
4. Select the exact `chrome-extension` directory already opened by Agent.
5. Confirm the installed extension ID is `lnpfljjigmgmakiclchpnoehbbceomeb`.
6. Let Agent determine whether the heartbeat version matches.

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

After connection, Agent fetches the currently enabled Vault policies and opens the extension options page. Use visible UI to click `启用全部支持的网站` and accept the expected browser host-permission prompt. Stop if the prompt requests permissions outside the exact origins displayed for those policies.

The policy authority is Credential Vault. Extension heartbeat only reports the policy digests it cached and the origins the browser granted. Do not assume a fixed count or silently omit newly configured sites. On a device-only cloud endpoint, the first restore task may install one policy and trigger its exact permission prompt; leave Agent running so it can retry after approval.

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
