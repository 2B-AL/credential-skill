# AL Credential Sync Skill

`al-credential-sync` 是用于 Codex 的 AL 凭据同步 Skill。它帮助 Codex 在个人电脑和云电脑上完成 `credential-agent` 的可信安装、设备入网、浏览器扩展准备、设备配对、健康检查，以及 Secret、环境变量、凭据组合、配置文件和网站登录状态的跨设备同步。

这个仓库的根目录本身就是一个可安装 Skill，不需要选择子目录。

## 能做什么

- 自动识别 macOS、Linux 或 Windows，以及对应 CPU 架构。
- 从公开 HTTPS 制品地址下载 `credential-agent`。
- 验证发布清单的 Ed25519 签名、制品长度和 SHA-256。
- 初始化个人电脑并完成 OAuth Device Flow 登录。
- 初始化云电脑或对端电脑，并通过短期配对码入网。
- 安装、更新和诊断 Agent 后台服务。
- 准备 Chrome Native Messaging 和 AL Credential Center 扩展。
- 在可见桌面中协助完成 Chrome 未打包扩展安装。
- 启用当前扩展支持的全部网站。
- 同步自定义 Secret、指定环境变量、AK/SK 等凭据组合、配置文件和网站会话。
- 检查设备、后台 Agent、浏览器扩展、权限和同步投递状态。
- 协助撤销网站授权、删除托管内容和排查过期设备。

## 直接安装

### 使用 Codex 自带 Skill Installer

在 macOS 或 Linux 终端执行：

```bash
python3 "${CODEX_HOME:-$HOME/.codex}/skills/.system/skill-installer/scripts/install-skill-from-github.py" \
  --repo 2B-AL/credential-skill \
  --path . \
  --name al-credential-sync
```

其中 `--path .` 表示 Skill 位于仓库根目录，并不代表还存在一层嵌套目录。

默认安装位置：

```text
${CODEX_HOME:-$HOME/.codex}/skills/al-credential-sync
```

安装完成后，新建一个 Codex 任务，或者重启 Codex 使其重新发现 Skill。

Windows PowerShell 中可以执行：

```powershell
$CodexHome = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $HOME ".codex" }
$Installer = Join-Path $CodexHome "skills\.system\skill-installer\scripts\install-skill-from-github.py"

python $Installer `
  --repo 2B-AL/credential-skill `
  --path . `
  --name al-credential-sync
```

### 私有仓库或需要 GitHub 身份认证

如果匿名下载不可用，但本机 Git 已经具备仓库访问权限，可以指定 Git 安装方式：

```bash
python3 "${CODEX_HOME:-$HOME/.codex}/skills/.system/skill-installer/scripts/install-skill-from-github.py" \
  --repo 2B-AL/credential-skill \
  --path . \
  --name al-credential-sync \
  --method git
```

不要把 GitHub Token 写入命令行或 README；使用本机已有的 Git/SSH/GitHub CLI 凭据。

### 更新 Skill

安装器不会覆盖已经存在的 Skill。确认本地 Skill 没有需要保留的修改后，删除旧目录并重新安装：

```bash
SKILL_DIR="${CODEX_HOME:-$HOME/.codex}/skills/al-credential-sync"
rm -rf "$SKILL_DIR"

python3 "${CODEX_HOME:-$HOME/.codex}/skills/.system/skill-installer/scripts/install-skill-from-github.py" \
  --repo 2B-AL/credential-skill \
  --path . \
  --name al-credential-sync
```

更新后新建 Codex 任务或重启 Codex。

## 最快使用方式

安装完成后，直接对 Codex 说：

```text
使用 $al-credential-sync 初始化这台个人电脑。
```

云电脑或对端电脑：

```text
使用 $al-credential-sync 初始化这台云电脑，并引导我和个人电脑完成配对。
```

同步凭据：

```text
使用 $al-credential-sync 把我的 GitHub 和 Google 网站登录状态同步到 win-cloud。
```

```text
使用 $al-credential-sync 把环境变量 OPENAI_API_KEY 和 ARK_API_KEY 同步到 win-cloud。
```

```text
使用 $al-credential-sync 把 ~/.codex/auth.json 同步到 win-cloud 对应用户的 ~/.codex/auth.json。
```

```text
使用 $al-credential-sync 检查这台电脑的 Agent、设备授权和浏览器扩展是否正常。
```

Skill 会自行识别环境、定位 Agent、选择正确命令，并只在 OAuth、设备配对、敏感凭据输入或 Chrome 必须要求用户手势时让用户介入。

## 首次初始化流程

### 个人电脑

Codex 使用本 Skill 时会执行以下流程：

1. 检测操作系统、架构、Chrome 和 Agent 安装状态。
2. 下载最新签名发布清单。
3. 校验 Ed25519 签名、平台、长度和 SHA-256。
4. 安装或更新 `credential-agent`。
5. 运行：

   ```text
   credential-agent setup --role personal --skip-browser
   ```

6. Agent 打开 OAuth Device Flow 页面，用户在页面中完成登录确认。
7. Agent 创建设备密钥、保存设备授权并启动后台同步。
8. 运行浏览器安装流程：

   ```text
   credential-agent browser setup --timeout 10m
   ```

9. 安装或连接 AL Credential Center Chrome 扩展。
10. 启用当前扩展支持的全部网站。
11. 运行 `credential-agent doctor --strict` 完成检查。

### 云电脑或对端电脑

1. 检测操作系统、架构、Chrome 和 Agent 安装状态。
2. 安装或更新 `credential-agent`。
3. 运行：

   ```text
   credential-agent setup --role cloud --skip-browser
   ```

4. Agent 显示短期配对码。
5. 在已经登录的个人电脑上执行：

   ```text
   credential-agent pair PAIR-CODE
   ```

6. 用户确认允许该云电脑接收凭据。
7. 云电脑完成设备入网并启动后台同步。
8. 准备 Chrome 扩展并启用当前支持的网站。
9. 运行 `credential-agent doctor --strict`。

配对码只用于一次短期批准，不会替代设备密钥，也不应写入文件、日志或聊天记录。

## Chrome 扩展安装说明

在未加入 Chrome Enterprise 管理、未通过 Chrome Web Store 发布扩展、也未修改 Chromium 的情况下，官方 Chrome 不允许普通应用完全静默安装私有扩展。

因此当前流程是：

1. Agent 自动下载并验证扩展制品。
2. Agent 自动解压到固定管理目录。
3. Agent 自动安装 Native Messaging 配置。
4. Agent 尝试打开 `chrome://extensions/` 和扩展目录。
5. Codex 在可见且已解锁的桌面上尽量通过 UI 完成：
   - 开启“开发者模式”；
   - 点击“加载未打包的扩展程序”；
   - 选择 Agent 已经打开的 `chrome-extension` 目录。
6. 如果 UI 自动化不可用，用户只需完成这一次 Chrome 强制要求的可见操作。
7. Agent 根据扩展心跳确认实际运行版本，而不是仅根据目录存在判断成功。
8. 在扩展授权页面点击“启用全部支持的网站”。

固定扩展 ID：

```text
lnpfljjigmgmakiclchpnoehbbceomeb
```

Skill 不会修改 Chrome Profile、Cookie 数据库、Secure Preferences，也不会伪造 Chrome 企业管理状态。

## 支持的凭据类型

| 类型 | 用途 | 典型 Agent 命令 |
| --- | --- | --- |
| 自定义 Secret | API Key、Token 或任意命名秘密 | `secret sync` |
| 环境变量 | 将指定变量安全交给目标进程 | `env sync` / `env run` |
| 凭据组合 | AK/SK、OAuth Client、用户名密码、TLS Key Pair | `credential-set sync` |
| 托管配置文件 | `~/.codex/auth.json` 等跨平台文件 | `file sync` |
| 浏览器网站会话 | 允许列表网站的 Cookie/会话快照 | `browser sync` |
| 动态凭据 | 有时效的租约型凭据 | `dynamic lease` / `dynamic run` |
| 托管密钥 | 不导出私钥材料的密钥引用与签名操作 | `managed-key` |
| 轮换和治理 | 凭据轮换、能力校验和治理策略 | `rotation` / `governance` |

高级命令的参数演进较快，Skill 会先读取已安装 Agent 的 `help`，不会假设旧参数仍然有效。

## 同步示例

以下命令用于解释 Agent 的能力。正常使用时优先让 Codex 通过 Skill 执行，避免人工处理路径、目标选择和状态判断。

### 查看设备

macOS/Linux：

```bash
AGENT="$HOME/.local/bin/credential-agent"
"$AGENT" devices
```

Windows PowerShell：

```powershell
$Agent = Join-Path $env:LOCALAPPDATA "AL\CredentialAgent\credential-agent.exe"
& $Agent devices
```

### 自定义 Secret

```bash
"$AGENT" secret sync --to win-cloud demo/api-key
```

Agent 会在终端中无回显地读取 Secret。不要把 Secret 值放在命令参数、脚本、剪贴板或 Codex 上下文中。

一次同步多个 Secret 引用：

```bash
"$AGENT" secret sync --to win-cloud service/api-key service/client-secret
```

### 指定环境变量

```bash
"$AGENT" env sync --to win-cloud OPENAI_API_KEY ARK_API_KEY
```

仅同步用户明确指定的变量名。Skill 不提供枚举并同步全部环境变量的能力。

### AK/SK 和其他凭据组合

火山引擎 AK/SK：

```bash
"$AGENT" credential-set sync \
  --to win-cloud \
  --type volcengine_aksk \
  --name volcengine-default
```

当前命名类型包括：

- `aws_aksk`
- `volcengine_aksk`
- `oauth_client`
- `username_password`
- `tls_keypair`

具体字段由 Agent 交互式读取，Skill 不构造或打印包含明文的 JSON。

### 配置文件

优先使用服务端定义的文件 Profile：

```bash
"$AGENT" file sync --to win-cloud --profile PROFILE_NAME
```

没有 Profile 时，可以使用逻辑路径映射：

```bash
"$AGENT" file sync \
  --to win-cloud \
  --map "$HOME/.codex/auth.json=home://.codex/auth.json"
```

逻辑根用于处理 macOS/Linux 与 Windows 的目录差异：

- `home://`：目标当前用户的主目录。
- `config://`：目标平台配置目录。
- `local-data://`：目标平台本地应用数据目录。
- `state://`：策略允许时使用的应用状态目录。

不要通过通用文件同步传输 SSH 私钥、浏览器 Profile 数据库、系统钥匙串数据库或 Agent 设备密钥。

### 浏览器网站会话

同步所有已经登录且当前扩展支持的网站：

```bash
"$AGENT" browser sync --to win-cloud --all
```

同步指定网站：

```bash
"$AGENT" browser sync --to win-cloud github reddit google
```

支持网站列表由扩展动态上报，不应在自动化里写死数量。Google 当前只保证策略允许的页面验证；Google Search 展示登录成功并不表示 Gmail、Drive 或 Google Account 敏感页面一定无需再次认证。

撤销某个网站在凭据中心的授权/快照：

```bash
"$AGENT" browser revoke github
```

撤销中心快照不等于自动清除所有目标电脑已经恢复的 Cookie，除非 Agent 明确报告目标清理已经投递成功。

### 交互式批量同步

需要在一个向导里选择多种资源时：

```bash
"$AGENT" sync --to win-cloud
```

## 健康检查和状态

推荐顺序：

```bash
"$AGENT" status
"$AGENT" doctor --strict
"$AGENT" devices
```

Windows PowerShell 必须使用调用运算符：

```powershell
& $Agent status
& $Agent doctor --strict
& $Agent devices
```

不要写成 `$Agent doctor`，PowerShell 会把它解析为错误表达式。

完整初始化应满足：

- Agent 位于当前用户的标准安装目录并且可以执行。
- 设备授权仍然有效。
- 设备密钥、系统密钥保护和本地 Secret Cache 可用。
- 后台 Agent 正在运行。
- 个人电脑 OAuth 检查通过。
- 云电脑设备授权控制面可用。
- Native Messaging Manifest 正确绑定固定扩展 ID。
- Chrome 扩展在线。
- 扩展运行版本与 Agent 管理目录中的目标版本一致。
- 当前支持的网站已经授权。
- `doctor --strict` 成功退出。

## 投递状态怎么理解

| 状态 | 含义 |
| --- | --- |
| `succeeded` | 目标设备已经确认接收全部内容 |
| `partial` | 同一批次中部分成功、部分失败 |
| `failed` | 本次请求没有任何内容完成投递 |
| `pending_target` | 任务已创建，但目标离线或尚未轮询到任务 |
| `cancelled` | 用户或 Agent 取消操作 |

源端显示“目标已接收”后，目标端再次运行 `pull` 显示没有待处理内容是正常的：后台 Agent 可能已经消费并应用了任务。

## 常见问题

### 更新 Agent 后需要重新配对吗？

通常不需要。更新 Agent 不应改变设备 ID、设备密钥和仍然有效的设备授权。只有设备授权过期或 Agent 明确报告设备状态不可恢复时，才重新运行对应角色的 `setup --skip-browser`。

### 为什么云电脑只有设备授权，没有用户登录？

这是正常状态。云电脑使用配对后获得的设备授权接收凭据，不需要持有个人电脑的 OAuth 用户 Token。

### 为什么 Chrome 扩展目录已经存在，Agent 仍然在等待？

目录存在不代表 Chrome 已经加载扩展。Agent 会等待固定扩展 ID 的 Native Messaging 心跳，并检查运行版本、权限和准备版本是否一致。

### 为什么扩展更新后仍然运行旧版本？

先在 `chrome://extensions/` 对 AL Credential Center 点击重新加载。如果心跳版本仍然不一致，只移除这个扩展，然后重新加载 Agent 管理的同一个 `chrome-extension` 目录。

### 为什么网站会话同步后仍要求重新认证？

目标网站可能校验设备绑定密钥、IP、地区、User-Agent、风险评分或二次认证状态。`SESSION_REAUTH_REQUIRED` 表示站点或策略拒绝了恢复后的完整会话，Skill 不会绕过站点验证。

### 为什么不能同步全部本地环境变量？

环境变量可能包含不相关的敏感信息。Skill 只允许同步用户明确选择的变量名，避免无意扩大凭据暴露范围。

### 下载失败怎么办？

先判断失败的是 OAuth、Credential Vault、制品 TOS 还是目标网站。如果用户明确授权，可以为当前终端设置 `HTTP_PROXY`、`HTTPS_PROXY` 和 `NO_PROXY` 后重试。签名或 SHA-256 不匹配时必须停止，不能换成未受信任下载地址。

### Windows 更新提示文件被占用怎么办？

后台计划任务和 Chrome Native Host 都可能持有 Agent 可执行文件。使用当前 Agent 的 `update` 路径或本 Skill 的 Windows bootstrap 脚本，不要反复强制覆盖正在运行的 EXE。必要时关闭 Chrome，让 Native Host 退出后重试；不需要删除设备状态。

## 安全边界

这个 Skill 只调用公开的 `credential-agent` CLI，不直接访问 Credential Vault、OAuth Enrollment 或 Provider 内部接口。

职责划分：

```text
Codex + al-credential-sync Skill
  -> 安装、调用、观察、可见 UI 协助

credential-agent
  -> 用户/设备认证、设备密钥、本地加密、同步任务、后台服务

credential-vault-service
  -> 加密后的 Secret、文件和会话快照托管、投递与租约

credential-browser-extension
  -> 允许列表网站的会话捕获、恢复和验证
```

Skill 不会读取或输出：

- Secret、环境变量值、AK/SK 或密码。
- Cookie、Local Storage 或配置文件明文。
- OAuth Access Token、Refresh Token 或设备授权 Token。
- Agent 设备私钥或浏览器数据库。

所有敏感值都应通过 Agent 的无回显交互输入，由 Agent 在本机加密。

## 平台与依赖

| 平台 | 当前 bootstrap 支持 |
| --- | --- |
| macOS arm64 | 支持 |
| macOS amd64 | 支持 |
| Linux amd64 | 支持 |
| Windows amd64 | 支持 |

基础依赖：

- Codex。
- Python 3：macOS/Linux bootstrap 和主机检测使用。
- Windows PowerShell：Windows bootstrap 和检测使用。
- Google Chrome：只在需要浏览器会话同步时要求。
- 能访问 GitHub 和公开制品地址的网络。

Agent 默认安装位置：

- macOS/Linux：`~/.local/bin/credential-agent`
- Windows：`%LOCALAPPDATA%\AL\CredentialAgent\credential-agent.exe`

Agent 和浏览器扩展制品默认从以下公开 HTTPS Origin 获取：

```text
https://al-artifacts.tos-ap-southeast-1.volces.com
```

下载不需要向 Skill 提供 TOS AK/SK。bootstrap 会验证签名清单和制品哈希，不能只依赖 HTTPS 地址本身。

## 仓库结构

```text
credential-skill/
├── SKILL.md
├── README.md
├── agents/
│   └── openai.yaml
├── scripts/
│   ├── bootstrap-agent.py
│   ├── bootstrap-agent-macos.sh
│   ├── bootstrap-agent-linux.sh
│   ├── bootstrap-agent-windows.ps1
│   ├── inspect-host.py
│   ├── inspect-host.sh
│   ├── inspect-host.ps1
│   ├── browser-assist-macos.sh
│   ├── browser-assist-windows.ps1
│   └── wait-agent-state.py
├── references/
│   ├── security-rules.md
│   ├── agent-command-map.md
│   ├── browser-installation.md
│   ├── file-profiles.md
│   └── troubleshooting.md
└── docs/
    └── design.md
```

- `SKILL.md`：Codex 触发后读取的核心执行流程。
- `agents/openai.yaml`：Skill 列表中的名称、简介和默认提示词。
- `scripts/`：可信安装、平台检测和浏览器可见操作辅助脚本。
- `references/`：按任务需要加载的安全、命令、文件、浏览器和排障规则。
- `docs/design.md`：完整设计、约束和实现说明。

详细设计见 [docs/design.md](docs/design.md)。

## 本地开发和验证

### 校验 Skill 结构

```bash
uv run --with pyyaml \
  python ~/.codex/skills/.system/skill-creator/scripts/quick_validate.py .
```

预期输出：

```text
Skill is valid!
```

### Ed25519 自测

macOS/Linux：

```bash
python3 scripts/bootstrap-agent.py --self-test
```

Windows PowerShell：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File .\scripts\bootstrap-agent-windows.ps1 `
  -SelfTest
```

### 只验证最新 Agent 制品，不安装

macOS：

```bash
sh scripts/bootstrap-agent-macos.sh --verify-only
```

Linux：

```bash
sh scripts/bootstrap-agent-linux.sh --verify-only
```

Windows：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File .\scripts\bootstrap-agent-windows.ps1 `
  -VerifyOnly
```

### 验证从 GitHub 安装后的真实形态

GitHub ZIP 下载不会保留 Unix 可执行位，所以 Skill 中的 Shell/Python 脚本必须通过解释器调用。不要依赖 `chmod +x`：

```bash
python3 /path/to/al-credential-sync/scripts/bootstrap-agent.py --self-test
sh /path/to/al-credential-sync/scripts/inspect-host.sh
```

## 设计文档

完整设计、状态机、安全模型和未来演进位于 [docs/design.md](docs/design.md)。

## License

当前仓库尚未包含独立 LICENSE 文件。使用和分发范围以仓库所有者的内部约定为准。
