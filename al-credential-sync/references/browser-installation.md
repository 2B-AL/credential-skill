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

Official unmanaged Chrome on Windows/macOS cannot silently install a private unpacked extension. This Skill may prepare the signed extension and assist visible UI, but it must not modify Chrome profiles or bypass user-gesture requirements.

The current compatible Agent command is:

```text
credential-agent browser setup --timeout 10m
```

It installs Native Messaging, downloads and verifies the signed extension artifact, prepares the managed directory, opens Chrome and the directory, waits for extension heartbeat, opens the permissions page, waits for supported-site authorization, and validates the running version.

## State machine

1. Start `browser setup` in a yielded terminal session.
2. If it exits successfully, continue to `doctor --strict`.
3. If it waits for connection, operate the visible Chrome UI or use the minimum manual fallback.
4. If an old extension is online, reload its card. If the running version remains old, remove only the AL Credential Center extension and load the Agent-managed directory again.
5. Wait for Agent to observe the expected version; do not infer success from the card alone.
6. Authorize all supported sites and wait for Agent heartbeat confirmation.

When future Agent versions expose `browser prepare/status/open-install/open-permissions/wait`, prefer those machine-readable commands. Do not require them on older releases.

## Visible UI assistance

Use Chrome or computer control only on an unlocked visible desktop.

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

Use `scripts/browser-assist-macos.sh DIRECTORY` or `scripts/browser-assist-windows.ps1 -ExtensionDirectory DIRECTORY` only when Agent failed to open the page/directory. These scripts prepare visible state; they do not install or modify Chrome.

## Manual fallback

If UI control is unavailable, display only:

```text
Chrome 已打开。

请点击“加载未打包的扩展程序”。
文件夹选择窗口出现后，选择已经打开的 chrome-extension 文件夹。

安装完成后无需返回终端，我会自动继续。
```

Do not ask the user to type `Y` or confirm completion in the terminal. Leave Agent waiting.

## Permission authorization

After connection, Agent opens the extension options page. Use visible UI to click `启用全部支持的网站` and accept the expected Chrome host-permission prompt. Stop if the prompt requests permissions outside the displayed supported-site origins.

The supported list comes from extension heartbeat. Do not assume a fixed count or silently omit newly supported sites.

## Upgrade repair

Directory presence is not success. Require:

- fixed extension ID
- recent Native Messaging heartbeat
- running version equals prepared version
- supported-site list is non-empty
- all supported sites are authorized

If versions differ, reload the extension card. If Chrome continues running the old code, remove only this extension and load the same managed directory again.

## Final validation

Run:

```text
credential-agent doctor --strict
```

A cloud device may legitimately report device-only authorization and skip the user control-plane check. Any extension offline, version mismatch, invalid Native Messaging manifest, or incomplete permissions state prevents complete browser setup.
