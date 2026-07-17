# Managed file mappings

## Table of contents

- Source of truth
- Logical roots
- Mapping procedure
- Cross-platform examples
- Safety checks

## Source of truth

Prefer Credential Vault managed-file profiles. Profiles define permitted logical destinations, write policy, replacement behavior, ownership, permissions, and cleanup. Do not override server policy from the Skill.

Use a custom `--map` only when no profile represents the user's file and the user accepts the shown source/destination mapping.

## Logical roots

Valid logical paths use Agent-owned schemes such as:

- `home://` — current user's home directory on every OS
- `config://` — platform configuration root
- `local-data://` — platform local application-data root
- `state://` — Agent/application state root when policy permits

Never use an absolute Windows target derived on macOS, or an absolute macOS target derived on Windows. Reject `..`, path traversal, empty components, drive escapes, UNC paths, and symlink-based escapes.

## Mapping procedure

1. Confirm the source file exists without reading or printing it.
2. Resolve a known profile first.
3. If custom mapping is required, show the source path and logical target only.
4. Confirm the target device.
5. Invoke Agent and let it encrypt/read the file.
6. On the target, let Agent apply the file atomically according to profile policy.

Example:

```text
credential-agent file sync --to win-cloud --map '~/.codex/auth.json=home://.codex/auth.json'
```

Quote mappings so the source shell does not split spaces. Expand `~` only when the installed Agent requires it; never echo the file contents.

## Cross-platform examples

Codex login file:

```text
~/.codex/auth.json -> home://.codex/auth.json
```

Generic application config:

```text
~/Library/Application Support/Example/config.json -> config://Example/config.json
```

Use a server-defined profile for the second example whenever possible because macOS and Windows application-data layouts differ.

## Safety checks

- Do not sync SSH private keys, browser profile databases, OS keychain databases, or Agent device keys through generic files.
- Do not overwrite an unrelated existing target file without policy approval.
- Do not force replacement after an ownership or digest conflict unless the user understands the exact target.
- Do not claim removal succeeded until Agent confirms rollback/cleanup.
