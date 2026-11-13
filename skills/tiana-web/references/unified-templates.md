# 统一模板候选流程

状态：统一模板客户端候选流程。2026-11-12 的 Staging 专项验证以候选 CLI 完成创建和更新；这不代表整体验收通过，也不代表其他环境或已发布 CLI 支持该流程。执行前确认目标服务支持相同协议且当前 CLI 帮助包含这些命令；否则可准备和本地验证安装包，发布与分发步骤标为待集成。所有命令中的大写标识和目录均替换为实际值，保留当前任务选定的环境和空间。

## 从 Web 创建与更新

按[分享模板打包流程](share-template.md)整理公开副本、图标、预览和安装包。模板 ID、来源 Web ID、发布 job ID、版本、revision 和材料摘要分别保存，不能互换。首次从所属空间的真实 Web 制作：

```sh
tiana web publish-share-template WEB_ID --unified --request-id REQUEST_ID --file INSTALL_ZIP --wait --json
```

执行前保存本次 request ID、原始安装包及摘要。创建返回稳定模板身份，当前版本在首版发布完成前为 null。后续更新先查 `tiana web status-template TEMPLATE_ID --json` 核对来源和版本，再使用同一身份：

```sh
tiana web publish-share-template WEB_ID --template-id TEMPLATE_ID --request-id NEW_REQUEST_ID --file INSTALL_ZIP --wait --json
```

新发布使用新请求身份；结果未知时保留原身份和原包，查询 `tiana web status-template TEMPLATE_ID --job-id JOB_ID --json`。只有原 job 的 status=complete 且 published_version 非 null 才成功，不能用后来版本的 current_version 代替原回执。未拿到模板 ID 时，可用 `tiana web list-owned-templates --limit 20 --json` 及返回游标只读核对，但不能凭名称猜测身份；以原 Web ID、`--unified`、原 request ID 和原包显式重放取回原身份。已确认模板 ID 但未拿到 job，或原 job 仍为 `uploading` 时，以该模板 ID、原 request ID 和原包显式重放；不要使用新 request ID。原 job 为 `pending` 或 `running` 时只读查询该 job，等待结果。失败或未知保留此前成功记录，不盲目再上传。

来源 Web 已删除时不再执行依赖 Web 的发布；模板仍按自己的分发状态工作。不要创建替代 Web 冒充原来源。模板删除后重建属于新身份，旧链接不得改指新作品；当前 CLI 未提供模板删除命令，不能用旧撤回模拟删除。

## 分享与市场分别管理

发布材料不等于开启分享或上架市场。先读取模板详情中服务端计算的 permissions、revision 与 distribution，分别确认用户授权和实际权限。仅变更用户要求的一项：

```sh
tiana web set-template-distribution TEMPLATE_ID --request-id REQUEST_ID --expected-revision REVISION --share-enabled=false --json
# 上架市场是另一项操作，需要当前空间具备该能力。
tiana web set-template-distribution TEMPLATE_ID --request-id ANOTHER_REQUEST_ID --expected-revision NEW_REVISION --market-enabled=true --json
```

成功以返回的固定 before/after 回执为准。未知时保留 request_id、expected_revision 和相同开关输入，显式重放同一请求取得原回执；后来的 GET 可能包含别人的更新，不能据其状态推断原操作成功。冲突时先核对，不能换 request ID 规避。官方认证、市场能力与分享风险豁免各自独立。

两个已开启入口使用同一当前版本；更新只影响后续分发，不升级已安装应用。分享安装、市场安装和市场定制三项计数按原口径分别展示，不相加。来源 Web 删除不自动下架模板。

## 源码、安装与链接

按当前版本实际材料选择：无源码的有效纯前端包仅支持安装，不提供做同款源码下载或保留源码选项。构建产物仍有浏览器代码，不能承诺隐藏前端代码。含函数的模板仍须包含安装构建所需源码；既有外置素材包对 source.zip 的校验要求继续执行，不因统一模板而绕过。

`has_source` 与 `installable` 分别判断。无源码响应 409 TEMPLATE_SOURCE_UNAVAILABLE 时不下载 install.zip 或 site.tweb 冒充工程、不创建空工程；有源码／无源码版本可双向更新，但必须校验新包，保留原模板身份和旧安装的固定材料。

使用服务端确认的链接，不从显示名称拼接身份。统一分享地址为当前 PublicOrigin 的 `/templates/{template_id}`；旧 `/shared-templates/{webID}` 永久定位原代，删除重建不能重绑。`init-share-template LINK --dir NEW_DIRECTORY --json` 分别识别这两类不带查询参数或片段的链接。链接带参数或仅知模板 ID 时，使用 `init-unified-template TEMPLATE_ID --channel share|market --dir NEW_DIRECTORY --json`，不要猜测渠道。按市场模板身份和可选固定版本取源码可用：

```sh
tiana web init-unified-template TEMPLATE_ID --channel market --version VERSION --dir NEW_DIRECTORY --json
```

这是源码初始化，不是服务端安装，不写安装来源或安装次数。源码下载拒绝时不绕过权限；无源码模板转到已验证的安装界面，不能发明 CLI 安装命令。

## 旧 CLI 与集成验收

默认 `publish-share-template WEB_ID` 仍使用旧 Web ID 接口；只有显式 --unified 或 --template-id 使用新接口。旧 status-share-template／withdraw-share-template 保留原语义，后者清除旧当前发布指针，不等于新分享开关。错误不会自动转旧写接口。

联调分别覆盖创建幂等、同 ID 更新、两个分发状态、有／无源码双向切换、来源删除后分发与更新拒绝、原 job 在更新后的回读、旧 CLI 与旧链接、删除重建墓碑及未知结果恢复。尚未执行的项目标为未验证；本地打包、fixture 和 CLI 帮助不能当作服务端或线上验收。
