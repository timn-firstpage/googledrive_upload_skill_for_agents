# 外部 onsite 衔接 prompt

配置完成后，在 Mac Codex 中使用：

> 使用现有 onsite checking skills 对我指定的网站完成审计，将最终报告保存在本地。列出本次明确生成的最终输出文件。然后使用 `$gdrive-upload` 将这些文件上传到已配置根文件夹下的 `<site>/<run-date>`。本次请求授权上传这些最终输出及创建这个明确的子文件夹路径；如果同名文件存在就停止，不能覆盖。首次使用先检测已有 service account 配置，并让我确认 JSON key 的路径。每个文件先做 dry-run 校验，成功后返回 Drive 链接和文件 ID。不上传 crawl cache、凭据或项目内其他文件。

把 `<site>/<run-date>` 换成明确的文件夹路径。这个 prompt 编排两类 skills；gdrive-upload 本身只处理 setup 与上传。

每个文件的实际上传要带上对应 dry-run 返回的 `--expected-md5`。如果文件之后变化，停止并重新确认最终版，不能静默替换校验值。

## 只上传已完成报告

> 使用 `$gdrive-upload`。`/absolute/path/report.xlsx` 是最终版，授权上传到配置好的根文件夹。先检测现有服务账号设置，让我确认凭据路径；确认后预览实际目标并上传。遇到同名文件停止。

## 明确替换已有输出

> `/absolute/path/report-v2.xlsx` 是最终版。我授权用它替换该目标文件夹中的 Drive 文件 ID `<file-id>`。使用 `$gdrive-upload` 先校验文件仍在根文件夹范围内，再预览并替换内容，返回同一个文件 ID 的链接。保留远端原有文件名称，不改变共享权限。
