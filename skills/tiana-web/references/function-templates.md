# 带后端服务的 Web 模板

配套 Function CLI 与模板安装扩展部署后使用。先确认 `tiana function --help`、`tiana web functions --help` 可用；未部署环境不能当作已支持。

## 确认资源关系

从目标 Web 的 `web functions get WEB_ID --json` 取得后端服务 ID，逐个 `function show` 读取源码 Git。每个 Git 固定一个 main commit；共享同一 Git 的前端和多个后端服务只取这一份快照。后端服务源码位置从元信息的 source_dir 取得。

后端数据库依据后端服务参数和实际源码确认。读取参数名与 Endpoint，再用已知 SQLite ID 的元信息核对 Endpoint；不要因为 Web 未直接绑定数据库就认为没有数据库，也不要默认复制当前租户的任意数据库。源码动态选择数据库或依赖多个数据库、无法确认对应实例时，先向用户明确该依赖，本格式目前声明一个安装 SQLite。报告只包含实例 ID、参数名和用途，不打印 Token。

沿用[分享模板](share-template.md)对结构、seed 和公开内容的筛选。后端服务参数只导出明确可公开的业务初值；数据库 Endpoint/Token 在安装时生成。源码、JSON、SQL、前端 bundle、source map 和展示材料均检查凭据和私有数据。

## 组织 metadata.json

将各仓库快照放在一个公开工作副本的 `repositories/<key>/` 下，根部放 metadata.json、showcase 和数据库初始化 SQL。同仓前后端保持原有目录布局。例如：

```json
{
  "name": "orders",
  "display_name": "订单管理",
  "description": "由后端服务处理业务并访问私有 SQLite",
  "database_required": true,
  "private_database": true,
  "schema": "db/schema.sql",
  "web_repository": "app",
  "repositories": [{
    "key": "app",
    "path": "repositories/app",
    "variables": [{
      "name": "FUNCTION_ID:api",
      "placeholder": "__TIANA_FUNCTION_API_91ad47ef__",
      "description": "本次安装的订单后端服务 ID",
      "files": ["src/app.js"]
    }]
  }],
  "functions": [{
    "key": "api",
    "name": "订单接口",
    "repository": "app",
    "source_dir": "/services/orders",
    "parameters": {"MESSAGE": "欢迎使用订单服务"},
    "database": {"endpoint_parameter": "SQLITE_ENDPOINT", "token_parameter": "SQLITE_TOKEN"}
  }],
  "site_variables": [{
    "name": "FUNCTION_ID:api",
    "placeholder": "__TIANA_FUNCTION_API_91ad47ef__",
    "description": "本次安装的订单后端服务 ID",
    "files": ["app.js"]
  }]
}
```

- `private_database: true` 创建并初始化 SQLite，但不把它绑定到 Web 的浏览器连接。后端服务通过参数访问数据库。
- `repositories` 的 key 标识逻辑仓库，path 选择 source.zip 内的快照子树。每个后端服务引用一个 repository；Web 引用 web_repository。共享关系在安装后保持。
`source_dir` 填写服务元信息中保存的仓库内目录，支持 `/` 根目录；每个目录含自身 go.mod。安装保留仓库目录结构，为新服务 ID 关联同一个 source_dir，不改名源码目录。同仓同目录允许多个服务引用。源码 variables 的文件路径相对于原仓库，资源 ID 引用仍按声明替换；数据库 Token 只写入运行参数。
- `parameters` 只放公开业务初值，`database` 指定接收新数据库 Endpoint/Token 的参数名。可选 `cors` 使用后端服务 CORS 配置对象。
- 仓库 variables 的 files 相对于该仓库，保持原路径；site_variables 的 files 相对于前端 dist。必须检查构建后的真实文件名及占位符仍然存在，不能照抄 `app.js`。
- `FUNCTION_ID:<key>`、`GIT_INSTANCE_ID:<key>` 引用新资源，WEB_ID、SQLITE_INSTANCE_ID 沿用本次安装值。目录结构与相对模块引用保留，Token 不作为替换变量。

前端直接调用 `context.functions.fetch('__TIANA_FUNCTION_API_91ad47ef__', '/orders', {...})`。占位符是普通字符串，干净构建后应保留在声明的 site_variables 文件中。数据库凭据只在后端服务运行参数中，不能进入这些文件。

## 打包与安装验证

从固定提交导出整个公开工作副本为 source.zip；在其中 `web_repository` 选择的目录安装依赖、干净构建，再给 [pack-template.py](../scripts/pack-template.py) 传入该 dist。脚本把这些字段写入 install.json。后端服务模板必须包含源码供安装时编译，不使用 `--without-source`。用户安装时可以不额外保留纯前端仓库；后端服务使用的 Git 始终创建，同仓 Web 保留该 Git 关联。

安装会先创建 SQLite、各 Git 和后端服务，取得所有新 ID 后关联原 source_dir、替换声明值，再保存 Git。设置新数据库参数，逐个编译后端服务并绑定 Web 后发布前端。同仓后端服务顺序构建，后一个读取前一个依赖整理后的 commit。安装失败时保留资源和回执，通过安装任务的重试继续，不能重新执行一组无关联的创建命令。

发布分享前用另一个租户实际安装：核对一个共享 Git、两个新后端服务的原 source_dir、实际发布版本和 Web 绑定；通过另一账号的 Site Cookie 打开分享应用，执行读写，确认访问的是新 SQLite、原数据库未变且浏览器不能取得 SQLite 连接或 Token。单纯编译通过不代表分享与隔离验收通过。

## 下载源码后继续开发

`web init-template` / `init-share-template` 只解压，不代替资源安装。读到 repositories/functions 后按逻辑 key 创建或按用户指定复用资源：每个 Git 一份、后端服务关联对应 Git；创建时传入原 source_dir，保留目录结构并替换声明的变量。初始化目标数据库，把新凭据放入后端服务参数；从 web_repository 构建前端。用 `web functions set` 保存后端服务列表后预览与发布。保留真实资源回执，重试时复用；不得将原作者后端服务或数据库 ID 留作默认值。
