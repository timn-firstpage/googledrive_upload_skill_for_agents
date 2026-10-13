# Google Drive Upload Skill for Agents

让 **macOS 和 Windows** 上的 Codex 使用 **Google Cloud service account**，将已完成的本地报告上传到你指定的 Google Drive 文件夹。它用同一份本地 Python 脚本访问 Drive API，不需要运行 MCP server。Skill 会按当前系统选择 Bash/zsh 或 PowerShell 的配置步骤。

Skill 提供两个流程：

- **Setup**：先检测已有服务账号配置，让用户确认 JSON key 的路径；缺少配置时才逐步引导创建账号、下载 key、授权目标文件夹和验证。
- **Upload**：上传明确的最终输出；支持指定子文件夹、按明确要求创建缺少的子文件夹，以及通过文件 ID明确替换已有普通文件。

它可以和现有 onsite checking skills 配合：审计由原来的 skills完成，外部 prompt再调用这个 Skill 上传输出。示例见 [onsite 衔接 prompt](examples/onsite-upload-prompt.md)。

## 使用前提

1. macOS 或 Windows 上有 Codex、Git、本地命令执行能力、Python **3.10+** 和网络连接。
2. Google Cloud 项目已启用 Google Drive API。
3. 一个服务账号及其 JSON key 文件。**JSON 文件留在本机仓库外，不能提交 GitHub。**
4. 一个 **Shared Drive / 共享云端硬盘**中的目标文件夹，直接分享给服务账号，并允许添加内容和所需的子文件夹/文件修改。

普通 **My Drive / 我的云端硬盘**中的共享文件夹不适合作为服务账号新文件上传目标：服务账号不能拥有新文件。脚本会检测并停止。[Google 官方说明](https://docs.cloud.google.com/iam/docs/service-account-overview)

为保持隔离，只分享目标文件夹，不默认把账号加为整个共享云端硬盘的 Content Manager，也不授予 Cloud 项目级 Editor/Owner。管理员的分享限制仍然适用。[Drive 权限说明](https://developers.google.com/workspace/drive/api/guides/about-shareddrives)

## 选择你的系统

当前 onsite 使用目标：**`Onsite_audit_ai_run_records`**（新建的 Shared Drive）。配置步骤见 [onsite 目标配置](references/onsite-target.md)。实际上传仍使用你确认的 Drive ID，不按此名称搜索或猜测。

| 项目 | macOS（Bash/zsh） | Windows（PowerShell） |
| --- | --- | --- |
| 逐步引导 | [Mac setup](references/setup-macos.md) | [Windows setup](references/setup-windows.md) |
| Skill 目录 | `~/.agents/skills/gdrive-upload` | `$HOME\.agents\skills\gdrive-upload` |
| 私有配置建议位置 | `~/.config/gdrive-upload` | `$env:LOCALAPPDATA\gdrive-upload` |
| venv Python | `venv/bin/python` | `venv\Scripts\python.exe` |
| 加载配置 | `source env.sh` | `. '完整路径\env.ps1'` |
| 调用解释器 | `"$GDRIVE_PYTHON"` | `& $env:GDRIVE_PYTHON` |

同一个账号和 Drive 文件夹 ID 可以在两台机器上复用，每台机器分别配置 JSON 文件路径与 Python 路径。Windows 的 `C:\...` 路径不能直接在 Mac 使用。下面先给 Windows 快速安装，再列出 Mac 的完整示例；Windows 的检测、doctor 和上传命令见 [Windows setup](references/setup-windows.md)。

## 在 Windows 安装

在 PowerShell 中执行，目录已存在时先检查，不要覆盖：

```powershell
$skillDir = Join-Path $HOME '.agents\skills\gdrive-upload'
New-Item -ItemType Directory -Force (Split-Path $skillDir) | Out-Null
git clone https://github.com/timn-firstpage/googledrive_upload_skill_for_agents.git $skillDir
py -3 --version
$venvDir = Join-Path $env:LOCALAPPDATA 'gdrive-upload\venv'
py -3 -m venv $venvDir
$gdrivePython = Join-Path $venvDir 'Scripts\python.exe'
& $gdrivePython -m pip install -r (Join-Path $skillDir 'requirements.txt')
& $gdrivePython (Join-Path $skillDir 'scripts\gdrive_upload.py') detect
```

需要已安装的 Python 3.10+；没有 `py` launcher 时，用已验证的 Python 可执行文件替换 `py -3`。无需激活 venv。配置示例见 [env.windows.example.ps1](examples/env.windows.example.ps1)，复制到仓库外再填写。PowerShell 中使用 `$env:变量名` 和调用运算符 `&`，不要直接运行本文中的 `export`、`source` 或 `chmod`。

## 在 Mac 安装

把仓库克隆为用户级 Skill（目标目录已存在时先检查，不要覆盖）：

```bash
mkdir -p "$HOME/.agents/skills"
git clone https://github.com/timn-firstpage/googledrive_upload_skill_for_agents.git \
  "$HOME/.agents/skills/gdrive-upload"
```

Codex 支持在 `~/.agents/skills` 发现本地 Skill。如果没有显示，重启 Codex，在新对话中输入 `$gdrive-upload`。[Codex Skill 安装位置](https://learn.chatgpt.com/docs/build-skills)

创建仓库外的 Python 环境并安装依赖：

```bash
python3 --version
python3 -m venv "$HOME/.local/share/gdrive-upload/venv"
"$HOME/.local/share/gdrive-upload/venv/bin/python" -m pip install \
  -r "$HOME/.agents/skills/gdrive-upload/requirements.txt"
```

安装完成后，在任一系统的 Codex 中输入：

> 使用 `$gdrive-upload` 带我逐步 setup。先检测已有服务账号配置；找到 key 路径后让我确认再读取。如果我已有账号，复用它。只授权我指定的 Shared Drive 文件夹。

完整引导见 [Mac setup](references/setup-macos.md) 或 [Windows setup](references/setup-windows.md)。这个仓库是 Skill 包，不会自动在 Google Cloud 创建账号或扩大 Drive 权限。

## 保存本机配置（以下命令为 Mac 示例）

准备两个位置：Skill 仓库存放通用代码，私有配置目录存放 key 和环境配置。

```bash
mkdir -p "$HOME/.config/gdrive-upload"
chmod 700 "$HOME/.config/gdrive-upload"
```

将用户已下载的 key 安全保存到该目录，例如 `service-account.json`，设置文件权限 `chmod 600`。不要覆盖已有 key。

创建 `~/.config/gdrive-upload/env.sh`，只写路径和 ID（用你自己的值替换）：

```bash
export GDRIVE_SA_KEY_FILE="$HOME/.config/gdrive-upload/service-account.json"
export GDRIVE_ROOT_FOLDER_ID="YOUR_APPROVED_ROOT_FOLDER_ID"
export GDRIVE_PYTHON="$HOME/.local/share/gdrive-upload/venv/bin/python"
```

`GOOGLE_APPLICATION_CREDENTIALS` 是 `GDRIVE_SA_KEY_FILE` 的备用来源，通常不用同时设置。这里没有额外的 Google API key、OAuth client secret或客户映射文件。

Mac GUI启动的 Codex 不一定继承 Terminal export。让 agent在调用脚本的**同一个 shell**显式加载你已确认的配置；修改 `.zshrc` 后不要假定当前 GUI会话已经拿到它。只加载你自己维护、只含预期 export设置的文件。

## 先检测，再确认 path

```bash
source "$HOME/.config/gdrive-upload/env.sh"
"$GDRIVE_PYTHON" "$HOME/.agents/skills/gdrive-upload/scripts/gdrive_upload.py" detect
```

`detect` 只检查环境变量指向的路径是否存在，不读取 JSON key，不调用 Google API。它不是“账号已经连通”的证明。Skill 会询问你是否使用检测到的 path；多个不同 path会让你选择。新会话先确认，当前会话已确认同一路径则复用。

你确认凭据路径和目标根文件夹 ID 后才运行：

```bash
source "$HOME/.config/gdrive-upload/env.sh"
"$GDRIVE_PYTHON" "$HOME/.agents/skills/gdrive-upload/scripts/gdrive_upload.py" \
  doctor --confirmed-key-file "$GDRIVE_SA_KEY_FILE"
```

Doctor 只读检查，返回服务账号邮箱、实际目标文件夹和写入能力；不会上传测试文件。`--confirmed-key-file` 是路径，不是 key内容。CLI 参数本身不能证明人的确认，确认流程由 Skill与用户交互完成。

## 上传一个最终输出

以下命令假设你已确认凭据路径和上传授权，每次执行都在同一个 shell加载配置。

预览报告及将创建的准确子文件夹：

```bash
source "$HOME/.config/gdrive-upload/env.sh"
"$GDRIVE_PYTHON" "$HOME/.agents/skills/gdrive-upload/scripts/gdrive_upload.py" \
  upload "/absolute/path/final-report.xlsx" \
  --confirmed-key-file "$GDRIVE_SA_KEY_FILE" \
  --subfolder "example.com/2026-10-13" --create-subfolders --dry-run
```

Dry-run 会显示文件路径、名称、大小、`md5` 校验值、实际目标以及待创建的子文件夹，**不会创建文件夹或上传**。确认目标正确并授权后，去掉 `--dry-run`，加上预览返回的校验值：

```bash
source "$HOME/.config/gdrive-upload/env.sh"
"$GDRIVE_PYTHON" "$HOME/.agents/skills/gdrive-upload/scripts/gdrive_upload.py" \
  upload "/absolute/path/final-report.xlsx" \
  --confirmed-key-file "$GDRIVE_SA_KEY_FILE" \
  --subfolder "example.com/2026-10-13" --create-subfolders \
  --expected-md5 "MD5_FROM_APPROVED_DRY_RUN"
```

脚本先生成临时文件快照，核对它与已批准的校验值一致，再上传该快照。文件内容有变化时会在远端写入前停止；需要重新预览并确认。临时快照在命令结束时清理，需要与上传文件大小相当的额外本地磁盘空间。

- 省略 `--subfolder`：上传到配置的根文件夹。
- 用 `--folder-id "EXACT_DESCENDANT_FOLDER_ID"`：上传到根范围内一个准确的文件夹；不能逃出配置根目录，不能和 `--subfolder` 同用。
- 用 `--create-subfolders`：只创建你明确指定路径中缺少的文件夹。同名文件夹有歧义时停止。
- 用 `--replace-file-id "EXACT_FILE_ID"`：明确替换目标文件夹内已有普通文件的内容，保留远端名称及共享权限。必须得到替换授权；不能编辑原生 Google Docs/Sheets内容。

同名文件默认停止，不覆盖，也没有 `--allow-duplicate`。Google Drive允许同名项目，并发上传之间仍可能竞争；不要对同一个目标/文件名同时启动多个上传。

成功输出示意：

```text
action: uploaded / replaced
file_id: Drive 文件 ID
filename: 文件名称
folder_id: 实际目的地 ID
md5: 上传内容校验值
link: 可打开的 Drive URL
```

实际 stdout是 JSON。返回链接不改变访问权限，已有文件夹分享继续决定谁能看到文件。

## 权限和范围

脚本每次检查目标是否为配置根文件夹或其后代；它拒绝另一共享云端硬盘、根范围外的文件夹、快捷方式及原生 Google 文档替换。凭据只在确认后由 Google认证库从本机路径读取，不打印 key内容。

根文件夹检查是脚本的操作限制；**真正的权限隔离由 Google Drive sharing 决定**。若服务账号已经是整个共享云端硬盘成员，持有 key的其他程序仍可能访问更广内容。不要把本脚本的限制当成 Google的权限收回。

写入前会重新检查目标的目录范围，但 Google API 没有把目录检查与写入合并为一个原子操作。上传期间不要移动相关文件夹；Google Drive 的实际分享权限仍是访问边界。

脚本不删除文件、不移动文件、不改变共享权限。创建子文件夹是上传过程的一部分，网络失败时可能留下已创建子文件夹或文件；先检查准确目标和同名文件再重试。上传使用当前进程内的可续传及有界重试，没有跨进程自动续传恢复。

## 问题排查

| 情况 | 处理 |
| --- | --- |
| detect找不到 path | 检查同一执行 shell是否加载本机配置，或向用户询问已有 key路径 |
| key path不存在 | 确认当前机器的路径；Mac 和 Windows 的绝对路径不能互用 |
| PowerShell 加载 env.ps1 被阻止 | 在同一个命令块直接设置三项 `$env:` 变量再调用 helper，无需修改系统执行策略 |
| HTTP 403 | 检查 Drive API、根文件夹授权、管理员外部分享限制及 key有效性 |
| My Drive目标被拒绝 | 改用用户指定的 Shared Drive文件夹；不会改用主账号登录 |
| 同名文件停止 | 检查已上传文件；要替换时明确指定文件 ID和授权 |
| 上传中断 | 先检查目标文件夹实际状态，不盲目重新创建同名文件 |
| 希望输出到新位置 | 明确确认新根 ID；原根范围检查不会自动跨文件夹 |

退出码：`0` 成功/预览；`2` 输入或配置缺失；`3` 子文件夹缺失/歧义；`4` 同名文件；`5` 依赖/凭据加载失败；`6` 目录/权限/范围不满足；`1` API或上传失败。

## 开发和验证

```bash
python3 -m unittest discover -s tests -v
python3 scripts/gdrive_upload.py --help
```

Windows 可用 `py -3 -m unittest discover -s tests -v`，或用自己的 venv Python 执行同样参数。[跨平台 CI 示例](examples/cross-platform-tests.yml) 可在获得 GitHub workflow 权限后保存到 `.github/workflows/tests.yml`，在 macOS 和 Windows、Python 3.10/3.12 上运行同一套离线测试。目前示例尚未启用。

测试使用离线 Drive 替身，验证路径确认、目录范围、dry-run 不写入、子文件夹、同名保护和文件替换；不使用真实 key 或写入生产 Drive。每台机器上的实际 Google 连接和一次真实上传需要由用户在 setup 完成后验证。

更新已安装仓库：

```bash
git -C "$HOME/.agents/skills/gdrive-upload" pull --ff-only
```

## 文件

- [SKILL.md](SKILL.md)：agent的 setup/upload流程。
- [setup-macos.md](references/setup-macos.md)：逐步配置和权限说明。
- [setup-windows.md](references/setup-windows.md)：Windows PowerShell 安装、配置与上传。
- [gdrive_upload.py](scripts/gdrive_upload.py)：本地检测、检查和上传工具。
- [外部 prompt](examples/onsite-upload-prompt.md)：与 onsite checking skills串联。
- [.env.example](.env.example)：只含示例路径，实际配置留在仓库外。
- [env.windows.example.ps1](examples/env.windows.example.ps1)：Windows 路径配置示例。

这是自定义 Skill，不是 Google或 OpenAI官方 Drive连接器。没有把任何服务账号 key或客户实际配置打包进仓库。
