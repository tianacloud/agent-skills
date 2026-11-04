# 用户密钥库

执行前核实 `tiana secrets --help` 包含 init、list、set、remove；若正式 CLI 尚未提供，说明配套能力未发布，使用用户已指定的候选版本或等待配套发布，不猜造其他访问方式。

## 初始化与列表

```sh
tiana secrets init --json
tiana secrets list --keyword database --page-size 50 --json
```

每个用户一个密钥库。init 复用已有实例及创建任务，只占一个实例名额；已有实例停用时不会自动启用。accepted 仅表示创建已受理，保留 instance_id、job_id 及实际状态。失败时使用 Console 原任务的重试入口；结果未知时再次 init 查询同一实例，不创建替代实例。

list 只返回名称与当前版本号，支持任意位置包含关键词。需要下一页时将返回的 next_cursor 原样传给 `--after`。只查询当前任务需要的页面，不把没有结果误认为未启用。

## 写入与删除

```sh
tiana secrets set production/database/password --file /private/input/secret.txt --json
tiana secrets remove production/database/password --force --json
```

Set 的值从用户指定文件或 `--stdin` 输入，保留空字符串、空格和换行。不要把值放入命令参数、源码、对话或日志。使用运行时管道传递标准输入，避免包含值的 shell 字面量。自行创建的输入临时文件放在 Git 外、仅当前用户可读写，完成后删除；用户原文件保持原样。

Set 直接写入，不先读取密钥。新 key 从 v1 开始，值变化则版本号增加，同值不变；只保留当前值。Remove 删除整个 key，重新创建从 v1 开始。`--force` 用于已确认的删除意图；交互终端可省略并确认提示。

仅根据返回的 key、version、changed、删除结果或 List 元数据报告操作。失败和未知结果不要自动重复写入；先核对状态，不能以版本变化证明密钥值内容。普通输出、JSON、错误、诊断都不回显密钥值。

## 函数引用

写入后，需要供函数使用时，按[参数配置与生效](commands.md#参数配置与生效)将 key 保存为函数参数。函数参数使用 `{"kind":"secret","value":"production/database/password"}`，value 是引用名称，不是密钥明文；函数执行首次读取成功后缓存，下次冷启动读取当前值。

密钥管理不提供 Get、明文回显或导出，也不通过 curl、SDK 或函数接口绕过 CLI 读取明文。需要人工查看时，引导用户到 Console 输入安全口令自行操作。平台 HashiCorp Vault 运维不属于本密钥管理流程。
