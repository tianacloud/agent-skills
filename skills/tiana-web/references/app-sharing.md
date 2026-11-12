# 应用访问分享

本流程授权其他空间使用当前应用。需要交付可独立安装的副本时，使用[模板分享](share-template.md)。

使用 CLI 1.0.24 或更新正式版，先读取当前应用的实际状态：

```sh
tiana web share get WEB_ID --json
```

保存 `data.web_id`、`project_revision`、`share_enabled`、`share_auto_approve`、`feature_enabled`、`can_manage`、`can_approve` 和实际返回的 `url`。所有操作使用已确认的 Web ID、当前账号和空间。

## 修改设置

用户要求开启或关闭应用分享时：

```sh
tiana web share set WEB_ID --enabled=true --expected-revision REVISION --json
```

用户要求开启或关闭自动批准时，先说明它只影响新申请，已有待审批申请仍需手动批准，然后执行：

```sh
tiana web share set WEB_ID --auto-approve=true --expected-revision REVISION --json
```

`REVISION` 使用上一轮查询或成功修改实际返回的 `project_revision`；关闭时使用 `false`。每次修改一个设置。用户要求同时开启分享和自动批准时，先开启分享，再用该回执中的新版本号开启自动批准。两次分别确认结果。

应用创建者或当前空间管理员可管理分享；自动批准由来源空间 owner/admin 管理，按服务端返回的能力与结果判断。全局分享能力关闭、无权限或名额限制时，说明实际原因，不把设置为 true 等同于任何人均可使用。

用户只要求发布应用时沿用原分享设置。用户只要求修改一个开关时，仅修改该开关。

## 结果与交付

成功后用实际返回状态说明分享和自动批准是否开启，并将返回的永久 `url` 标为“申请使用”。该链接用于接收空间申请使用；已批准资格归接收空间，同空间有效成员共享。

版本冲突先重新查询。修改响应丢失、超时或 `status: unknown` 时，保留原 Web ID、目标设置和原版本，在原账号／空间只读查询；不自动重发修改。两步部分成功时逐项说明已确认结果。应用发布成功与分享设置结果分别报告。

小程序链接和小程序码只定位应用，进入后由微信绑定的账号及当前空间决定使用资格。来源空间成员、已有资格空间直接按原流程进入；新接收空间在分享与自动批准开启、名额允许时按现有流程自动获批。已有待审批申请仍待管理员处理。
