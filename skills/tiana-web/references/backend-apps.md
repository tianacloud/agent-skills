# 带后端服务的 Web 开发流程

仅在应用需要后端时使用。Web skill 负责以下编排与浏览器验收；后端实现交给 [Tiana Function](../../tiana-function/SKILL.md)，具体命令、参数格式和 Go 示例由该 skill 维护。

## 1. 确定共仓资源

修改已有 Web 时读取实际 Git 绑定和后端服务列表，复用对应资源。新建应用时先创建一份 Git，在创建 Web 与后端服务时共同关联。已有 Web 沿用创建时固定的关联；未关联 Git 时为后端服务创建仓库，并记录前端与后端的实际源码位置。用户指定其他仓库时按其选择，模板工程按已声明的仓库关系处理。

将实际 Git ID、已知后端服务 ID、接口需求和数据库依赖交给 Tiana Function。新服务明确使用这个 Git；由 Function skill 确定并保存 source_dir。前端和后端编辑保持同仓其他文件，共享仓库的后续提交基于最新 main，避免用前端旧副本覆盖后端或构建写回的依赖文件。

Web 只绑定前端实际需要直连的数据库；仅供后端使用的数据库不绑定 Web。纯后端访问模式创建 Web 时省略 `--database-instance-id`，并用 `--git-instance-id` 关联已确定的共享 Git。

## 2. 完成后端交接

向 Tiana Function 提供业务接口、所需参数的名称和用途、目标数据库及表结构；敏感值按该 skill 的参数配置流程处理，不作为前端构建变量。由它完成源码保存、编译发布和后端核验，返回：

- 后端服务 ID、Git ID 和实际 source_dir。
- 已发布的源码提交、构建回执及接口路径、方法、请求和响应格式。
- 必需参数的名称及配置／生效结果，不返回参数值；缺失配置或待生效状态明确列出。

仅保存 Git 或构建受理不能视为后端就绪。后端失败时留在后端步骤处理；前端可以继续开发，但不能将真实调用未通过的应用交付为可用。

## 3. 绑定并接入前端

```sh
tiana web functions get WEB_ID --json
tiana web functions set WEB_ID --function-id FUNCTION_ID --expected-revision REVISION --json
```

使用实际 ID 和 get 返回的 revision。set 替换完整列表；保留仍需使用的服务，多个服务重复传 `--function-id`，冲突后重读列表。不传 ID 会清空绑定。

前端使用平台提供的 `context.functions.fetch(FUNCTION_ID, "/orders", {method: "GET"})`。页面只保存服务 ID 和业务接口契约，所需调用凭据由平台提供；数据库 Token、第三方 API Key 等只留在后端参数中。按 [Web 开发与发布](csr-apps.md)处理入口、交互、构建和发布。

## 4. 验证实际可用

先用 `tiana web serve WEB_ID --dir dist` 验证接口及页面，再发布前端并核对实际托管页面。已有后端可能仍运行旧版本：按 Function skill 核对实际接口结果，不能仅凭最新构建成功判断当前请求使用新版。

需要分享时，用另一账号通过 Site 登录打开应用，完成业务读写，确认只取得所绑定后端服务的调用权限，浏览器的 Bootstrap、网络响应和发布产物中没有后端私有数据库凭据或第三方密钥。本地预览的开发者账号不能替代此验收。按业务要求验证各用户的数据范围。

交付托管地址、资源关联、源码提交及实测结果；缺少配置、未执行的环境验收如实列出。制作可安装模板另按[后端服务模板](function-templates.md)处理复制、参数映射与跨账号安装。
