# Onsite 目标：Onsite_audit_ai_run_records

本次 onsite 输出使用新建的 **Shared Drive `Onsite_audit_ai_run_records`**，替代之前 My Drive 中的普通共享文件夹。通用 Skill 和上传脚本保持按环境配置，不把目标名称当成 Drive ID。

## 手动设置权限

在该 Shared Drive 的管理成员页面添加你现有服务账号的完整邮箱，授予所需的上传、创建子文件夹及修改文件能力。若你希望 agent 可以处理这个专用盘内的所有 onsite 输出，可将它加入这个专用 Shared Drive；不要因此授予其他共享云端硬盘或 Google Cloud 项目的 Editor/Owner 权限。

账号邮箱来自你已确认的服务账号信息。无需新建账号或重新下载 JSON key。私钥和本机路径继续留在仓库外。

本流程选择 **Contributor（贡献者）**，满足 API 上传、创建子文件夹及编辑文件。用户已确认完成添加；实际 API 访问能力仍需运行 doctor 检查。

## 使用准确 ID

用户提供的 `Onsite_audit_ai_run_records` 根目录链接：

```text
https://drive.google.com/drive/u/0/folders/0AOx3b-buiVeqUk9PVA
```

准确 ID 为 `0AOx3b-buiVeqUk9PVA`，设置为 `GDRIVE_ROOT_FOLDER_ID`。ID 来自用户提供的链接，未做真实账号连接或写入验证。通用脚本仍不硬编码此 ID；若换目标，确认新的准确 ID 并更新本机配置。

Mac 本机配置：

```bash
export GDRIVE_ROOT_FOLDER_ID="0AOx3b-buiVeqUk9PVA"
```

Windows PowerShell 本机配置：

```powershell
$env:GDRIVE_ROOT_FOLDER_ID = '0AOx3b-buiVeqUk9PVA'
```

更新各自仓库外的 `env.sh` / `env.ps1`，保留已确认的 JSON key 和 Python 路径。Skill 在当前机器先检测已有凭据，再确认路径和新目标 ID，运行只读 `doctor`。输出根名称应为 `Onsite_audit_ai_run_records`（若选择子文件夹则为该文件夹名）。新会话仍需确认凭据路径。

## 衔接审计输出

在 [外部 onsite prompt](../examples/onsite-upload-prompt.md) 的流程中，使用以上配置并先通过 doctor 检查。每次审计可明确指定 `<site>/<run-date>` 子路径；创建该路径及上传最终文件需有用户授权。实际上传带对应 dry-run 的 MD5，成功后返回文件 ID 和链接。
