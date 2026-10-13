# Windows setup（PowerShell）

逐步引导，先复用已有服务账号。Google Cloud 创建账号、下载 key、Drive API 和目标权限的规则与 [Mac setup 的第 2–3 节](setup-macos.md) 相同；Windows 使用下面的本地路径与命令。

## 1. 安装 Skill 与 Python 环境

```powershell
$skillDir = Join-Path $HOME '.agents\skills\gdrive-upload'
New-Item -ItemType Directory -Force (Split-Path $skillDir) | Out-Null
git clone https://github.com/timn-firstpage/googledrive_upload_skill_for_agents.git $skillDir
py -3 --version
$venvDir = Join-Path $env:LOCALAPPDATA 'gdrive-upload\venv'
py -3 -m venv $venvDir
$gdrivePython = Join-Path $venvDir 'Scripts\python.exe'
& $gdrivePython -m pip install -r (Join-Path $skillDir 'requirements.txt')
```

目录已存在时先检查，不覆盖。`py -3` 需要已安装的 Python 3.10+ 和 launcher；若没有 launcher，使用已验证的 Python 可执行文件替换 `py -3`。`python` 打开 Microsoft Store 或提示找不到命令时，先安装 Python，不能视为已安装。无需激活 venv，也无需修改执行策略。

## 2. 先检测已有配置

```powershell
& $gdrivePython (Join-Path $skillDir 'scripts\gdrive_upload.py') detect
```

先显示已配置的 key 路径，等待用户确认再读取。两条不同路径让用户选择。若找不到配置，询问是否已有 JSON key 及准确路径；不要扫描磁盘。如果已有私有配置，先核对其位置和内容再加载。复用现有账号不需要创建新账号。

## 3. 保存私有配置

建议配置目录为 `$env:LOCALAPPDATA\gdrive-upload`，key 可放在其中的 `service-account.json`；也可以使用用户指定的已有路径。它在 Skill 仓库外。Windows 使用文件夹 Security 设置检查私钥只有本人及必要系统/管理员能读取，不套用 Mac 的 `chmod` 命令，不放到公开共享目录。

创建该私有目录中的 `env.ps1`，只保存路径和用户确认的根 ID：

```powershell
$env:GDRIVE_SA_KEY_FILE = Join-Path $env:LOCALAPPDATA 'gdrive-upload\service-account.json'
$env:GDRIVE_ROOT_FOLDER_ID = 'YOUR_APPROVED_ROOT_FOLDER_ID'
$env:GDRIVE_PYTHON = Join-Path $env:LOCALAPPDATA 'gdrive-upload\venv\Scripts\python.exe'
```

`GOOGLE_APPLICATION_CREDENTIALS` 是第一项的可选替代，不是第二把 key。配置文件只写路径和 ID，不能写 key 内容。已有 key 可保持原路径，不强制搬移或覆盖。

GUI 启动的 Codex 不一定继承另外一个 PowerShell 窗口的环境变量。每次在执行 helper 的同一个 PowerShell 中加载已核对的配置。若策略阻止加载 `env.ps1`，直接在同一个命令块设置以上三项，再调用 helper；不要修改系统执行策略。

## 4. 确认路径和目标后检查连接

```powershell
. (Join-Path $env:LOCALAPPDATA 'gdrive-upload\env.ps1')
$skillDir = Join-Path $HOME '.agents\skills\gdrive-upload'
$helper = Join-Path $skillDir 'scripts\gdrive_upload.py'
& $env:GDRIVE_PYTHON $helper detect
# 用户确认 key 路径与根文件夹 ID 后：
& $env:GDRIVE_PYTHON $helper doctor --confirmed-key-file $env:GDRIVE_SA_KEY_FILE
```

Doctor 只读，不证明账号没有其他 Drive 授权。让用户或管理员检查目标分享及整个 Shared Drive 的成员范围。只授权指定文件夹；My Drive 新文件上传会被拒绝。

## 5. 上传最终文件

同一个 PowerShell 命令块先加载已确认配置，再执行：

```powershell
. (Join-Path $env:LOCALAPPDATA 'gdrive-upload\env.ps1')
$helper = Join-Path $HOME '.agents\skills\gdrive-upload\scripts\gdrive_upload.py'
& $env:GDRIVE_PYTHON $helper upload 'C:\Reports\final-report.xlsx' `
  --confirmed-key-file $env:GDRIVE_SA_KEY_FILE `
  --subfolder 'example.com/2026-10-13' --create-subfolders --dry-run
```

确认最终文件、目的地与上传授权后，带上预览返回的 MD5：

```powershell
. (Join-Path $env:LOCALAPPDATA 'gdrive-upload\env.ps1')
$helper = Join-Path $HOME '.agents\skills\gdrive-upload\scripts\gdrive_upload.py'
& $env:GDRIVE_PYTHON $helper upload 'C:\Reports\final-report.xlsx' `
  --confirmed-key-file $env:GDRIVE_SA_KEY_FILE `
  --subfolder 'example.com/2026-10-13' --create-subfolders `
  --expected-md5 'MD5_FROM_APPROVED_DRY_RUN'
```

本地文件路径可用 Windows 反斜杠并加引号；Drive 的 `--subfolder` 在两个系统上都使用 `/`，例如 `site/run`。PowerShell 续行反引号后不能有空格。替换文件、同名保护及错误处理与 SKILL.md 相同。

迁移到另一台机器时复用账号和目标 ID，但重新确认该机器上的 key 路径、venv 路径及授权；不把本机配置提交 GitHub。
