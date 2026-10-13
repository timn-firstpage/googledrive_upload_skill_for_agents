# Mac setup：先检测、再逐步引导

Windows 使用 [PowerShell setup](setup-windows.md)，不要在 Windows 直接执行本页的 Bash 或 chmod 命令。

向用户逐步提供当前所需操作，不一次要求用户交出所有账号信息。以下是引导顺序；已完成的步骤检查后复用。

## 1. 检测已有配置并确认凭据路径

先运行 helper 的 `detect`。只显示已配置的两个环境变量的路径及文件是否存在，不打开 key。

如果用户已保存仓库外的环境配置但 Codex 没继承它，请先确认配置文件的位置，核对它只含预期的 export 路径/ID设置，再在执行 helper 的同一个 shell 中加载。不要执行来历不明的 shell 配置。

如果检测到路径，询问：“检测到已有服务账号凭据路径 `<path>`，是否使用它？”如果两个变量指定不同路径，让用户选择。用户确认后才允许加载该 key，并将该路径作为 `--confirmed-key-file` 参数传给脚本。同一会话中已确认相同路径时无需再次询问。新会话或路径改变重新确认。

没有环境变量时，先问用户是否已有 JSON key 文件及其本地路径。没有才进入创建流程。不要扫描整个 Downloads 或磁盘来寻找 key；只能检查用户提供的位置。复用现有 key 不需要创建新账号。

## 2. 服务账号和 Drive API

1. 用户登录 Google Cloud Console，选择或创建他们指定的项目。
2. 在 APIs & Services 中启用 Google Drive API (`drive.googleapis.com`)。
3. 打开 IAM & Admin → Service Accounts。已有指定服务账号就复用；否则创建一个有明确用途的服务账号。
4. **不给它项目级 Owner/Editor；不启用 domain-wide delegation。** Drive 文件访问来自 Drive 分享，不来自 Google Cloud 项目角色。
5. 如确需新 key，在账号 Keys → Add key → Create new key → JSON。确认用户同意生成并下载该私钥，再操作；组织禁止创建 key 时报告该限制，由管理员处理。
6. 将 key 保存到用户批准的私有目录，例如 `~/.config/gdrive-upload/service-account.json`。设置文件权限 `chmod 600`、目录权限 `chmod 700`。迁移到 Mac 时用户用他们信任的方法传输，不在聊天里粘贴内容。不要改名/覆盖另一份 key 而不先核对。

参考：[创建服务账号](https://docs.cloud.google.com/iam/docs/service-accounts-create)、[创建密钥](https://docs.cloud.google.com/iam/docs/keys-create-delete)。

## 3. 目标文件夹和隔离

用户给出准确的目标文件夹 URL或 ID；从 `/folders/<id>` 提取 ID，不按名称猜测。目标应位于 **Shared Drive / 共享云端硬盘**。

在该目标文件夹的 Share 页面直接添加服务账号邮箱，并给可上传文件/创建子文件夹/修改所需内容的最低合适权限。通常文件夹 Editor 授权适合此用途，实际能力由 Shared Drive 及管理员限制决定，用 doctor 检查 `canAddChildren`。不要默认为整个共享云端硬盘授予 Content Manager。检查该账号是否已有其他分享或整个共享云端硬盘成员权限；若已有更广权限，明确告诉用户，不能靠脚本的根 ID 把 Google 权限收回。

检查隔离时，让有管理权限的用户在目标 Shared Drive 的 Manage members 页面核对该服务账号是否是整盘成员，并在目标文件夹 Share 页面核对它的直接授权/继承授权。Doctor 只检查目标可访问和写入能力，不能证明整个账号没有其他资源授权；缺少用户或管理员核对结果时明确报告“目标可写，账号全局隔离尚未验证”。不要自动移除已有权限。

若组织禁止向非成员或组织外账号分享文件夹，停止并请 Drive 管理员允许所需分享或提供专用 Shared Drive。服务账号不是普通 Workspace 用户，分享给“整个公司域”也不等于分享给服务账号。调整权限需与用户确认实际资源和角色；已有明确授权仍有效。

**My Drive 中的普通共享文件夹不满足服务账号新文件上传的存储所有权要求。** 服务账号没有个人存储配额，不能拥有新文件。脚本会拒绝 My Drive 目标，而不是悄悄改为用户 OAuth。[官方说明](https://docs.cloud.google.com/iam/docs/service-account-overview)

Shared Drive 文件由组织拥有。根文件夹 ID在脚本中限制写入位置及后代，不能限制持有 key 的其他程序；真正隔离依赖 Drive 的分享范围。Limited access 是管理员可能使用的另一种限制方式，不是所有直接文件夹分享都必须启用。[共享云端硬盘权限](https://developers.google.com/workspace/drive/api/guides/about-shareddrives)

## 4. Mac venv 和环境配置

安装 Python 3.10+（如已有 Homebrew 可用 `brew install python`；否则由用户选择安装方式）。用仓库 README 中的命令创建仓库外的 venv并安装依赖。

环境变量：

| 变量 | 值 |
| --- | --- |
| `GDRIVE_SA_KEY_FILE` | JSON 私钥文件的绝对路径 |
| `GOOGLE_APPLICATION_CREDENTIALS` | 前者的可选替代变量，不是第二把 key |
| `GDRIVE_ROOT_FOLDER_ID` | 指定根文件夹 ID |
| `GDRIVE_PYTHON` | venv 中 Python 可执行文件的绝对路径 |

不需要 client mapping：当前设计只使用一个根文件夹及准确的后代 ID/路径。配置保存到仓库外的用户私有目录。Mac 的 GUI Codex 不一定继承 Terminal 的 export；每次由执行 shell 显式加载已核对的本机配置，再调用脚本。不要假定修改 `.zshrc` 已让当前 Codex 会话生效。

## 5. 验证

路径确认后运行 `doctor --confirmed-key-file "<confirmed path>"`。输出账号邮箱、实际根名称/ID、Shared Drive ID和可添加子项状态。遇到 ID错、My Drive、只读权限、网络或 API限制时先处理该问题，不声称连接成功。

Doctor 不写入。要实测上传/修改，使用用户同意的普通测试文件及指定子文件夹，先 dry-run，再执行一次上传；记录链接。若需要检验替换，明确授权替换该测试文件 ID。测试文件留在目标内由用户处理；本 Skill 无删除命令。不要把离线单元测试或 doctor 当成真实上传成功的证据。

正常上传按 SKILL.md执行。网络中断可能留下子文件夹或已创建文件；先核对目的地，不盲目重跑。这个脚本的可续传仅在当前进程内重试，不把上传会话保存为跨进程自动恢复。
