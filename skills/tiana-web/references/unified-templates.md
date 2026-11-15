# 统一模板生命周期与分发管理

所有模板已统一为单一入口：`share` 与模板市场共用同一套模板模型（`Source WebApp → template_id → share_enabled / market_enabled`）。之前通过 Gaia 上传/草稿/发布及旧 `WEB_ID` 独立分享接口的旧流程已废弃。所有命令中的大写标识和目录均替换为实际值，保留当前任务选定的环境和空间。

## 从 Web 创建与更新

按[分享模板打包流程](share-template.md)整理公开副本、图标、预览和安装包。模板 ID、来源 Web ID、发布 job ID、版本、revision 和材料摘要分别保存，不能互换。首次从所属空间的真实 Web 制作：

```sh
tiana web publish-share-template WEB_ID --request-id REQUEST_ID --file INSTALL_ZIP --wait --json
```

执行前保存本次 `request_id`、原始安装包及摘要。创建返回稳定模板身份 `template_id`，当前版本在首版发布完成前为 `null`。后续更新先查 `tiana web status-template TEMPLATE_ID --json` 核对来源和版本，再使用同一身份：

```sh
tiana web publish-share-template WEB_ID --template-id TEMPLATE_ID --request-id NEW_REQUEST_ID --file INSTALL_ZIP --wait --json
```

新发布使用新请求身份；结果未知时保留原身份和原包，查询 `tiana web status-template TEMPLATE_ID --job-id JOB_ID --json`。只有原 job 的 `status=complete` 且 `published_version` 非 `null` 才成功，不能用后来版本的 `current_version` 代替原回执。发布被服务端拒绝（`status=fail`）时读取回执中的 `last_error` 与本地包修复原因后，重新打包并用新的 `--request-id` 重试。

未拿到模板 ID 时，可用 `tiana web status-share-template WEB_ID --json`（按来源 Web 查）或 `tiana web list-owned-templates --limit 20 --json` 只读核对，不能凭名称猜测身份；确认不存在新模板前，以原 Web ID、原 `request_id` 和原包显式重放取回原身份。已确认模板 ID 但未拿到 job，或原 job 仍为 `uploading` 时，以该 `--template-id`、原 `request_id` 和原包显式重放；不要使用新 `request_id`。原 job 为 `pending` 或 `running` 时只读查询该 job，等待结果。

来源 Web 已删除时不再执行依赖 Web 的发布；模板仍按自己的分发状态工作。不要创建替代 Web 冒充原来源。永久删除模板使用：

```sh
tiana web delete-template TEMPLATE_ID --request-id REQUEST_ID --expected-revision REVISION --json
```

模板删除后重建属于新身份，旧链接不得改指新作品。

## 分享与市场分别管理

发布材料不等于开启分享或上架市场。先读取模板详情中服务端计算的 `permissions`、`revision` 与 `distribution`，分别确认用户授权和实际权限。仅变更用户要求的一项：

```sh
tiana web set-template-distribution TEMPLATE_ID --request-id REQUEST_ID --expected-revision REVISION --share-enabled=false --json
# 上架市场是另一项操作，需要当前空间具备该能力。
tiana web set-template-distribution TEMPLATE_ID --request-id ANOTHER_REQUEST_ID --expected-revision NEW_REVISION --market-enabled=true --json
```

成功以返回的固定 `before`/`after` 回执为准。未知时保留 `request_id`、`expected_revision` 和相同开关输入，显式重放同一请求取得原回执；后来的 GET 可能包含别人的更新，不能据其状态推断原操作成功。冲突时先核对，不能换 `request_id` 规避。

两个已开启入口使用同一当前版本；更新只影响后续分发，不升级已安装应用。分享安装、市场安装和市场定制三项计数按原口径分别展示，不相加。来源 Web 删除不自动下架模板。

## 源码、安装与链接

按当前版本实际材料选择：无源码的有效纯前端包仅支持安装，不提供做同款源码下载或保留源码选项。构建产物仍有浏览器代码，不能承诺隐藏前端代码。含函数的模板仍须包含安装构建所需源码；既有外置素材包对 `source.zip` 的校验要求继续执行，不因统一模板而绕过。

`has_source` 与 `installable` 分别判断。无源码响应 `409 TEMPLATE_SOURCE_UNAVAILABLE` 时不下载 `install.zip` 或 `site.tweb` 冒充工程、不创建空工程；有源码／无源码版本可双向更新，但必须校验新包，保留原模板身份和旧安装的固定材料。

统一模板分享链接为当前 PublicOrigin 的 `/templates/{template_id}`（可带 `?channel=share` 或 `?channel=market`）。`init-share-template LINK --dir NEW_DIRECTORY --json` 解析统一链接下载源码；直接按模板 ID 从市场目录获取源码可用：

```sh
tiana web init-template TEMPLATE_ID --dir NEW_DIRECTORY --json
# 如需指定渠道或固定版本：
tiana web init-unified-template TEMPLATE_ID --channel market --version VERSION --dir NEW_DIRECTORY --json
```

这是源码初始化，不是服务端安装，不写安装来源或安装次数。源码下载拒绝时不绕过权限；无源码模板转到已验证的安装界面，不能发明 CLI 安装命令。
