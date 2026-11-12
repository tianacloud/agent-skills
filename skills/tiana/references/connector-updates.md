# 连接器与宿主中的更新

在任意连接器中首次使用 Tiana、发现 CLI/Skills 新版或安装后仍运行旧版时读取。更新决策与会话记录按[开始使用](getting-started.md#更新)。Connector 提供 CLI 和技能。版本检查保留；CLI 满足最低基线后，升级 CLI 或 Skills 均先展示当前/目标版本并征得用户同意，再使用实际返回且获准的目标版本安装。Skills 升级会覆盖已有技能并补齐新增技能，询问时说明这一影响。CLI 缺失或低于 1.0.17 时可自动安装并核验基线。

## CLI：沿用当前托管安装

在 Agent 实际执行命令的环境定位运行时和安装位置；CLI 需要 Node.js 20+，Skills 安装器需要 Node.js 22.20+。宿主提供隔离运行时或安装 prefix 时沿用其环境；系统终端的全局 npm 列表不能代表连接器中的安装。先核对：

```sh
command -v node
command -v npm
command -v tiana
npm prefix --global
npm root --global
```

Windows PowerShell 使用 `Get-Command node,npm.cmd,tiana.cmd`、`npm.cmd prefix --global` 和 `npm.cmd root --global`。沿入口解析符号链接或 npm shim，确认实际 `@tianacloud/cli/package.json` 所在位置及版本。

当前 CLI 包位于返回的 npm root 下时，沿用该 Node/npm、prefix 和 PATH，执行开始使用中的精确版本全局安装。若当前 shell 的 npm prefix 与实际 CLI 所属位置不同，从实际包位置确认原安装 prefix，再用相应 npm 显式指定该 prefix：

```sh
npm install -g --prefix "CLI_PREFIX" @tianacloud/cli@VERSION --registry=https://registry.npmjs.org/
```

CLI_PREFIX 来自实际安装位置，VERSION 来自更新回执。后续独立命令调用都沿用已核实的命令路径与运行环境，包括 Git helper 所需 PATH 和本任务 TIANA_API_ORIGIN。安装后核验实际入口的 `tiana version` 及任务所需命令帮助。安装位置取自当前宿主，不在指令中固化某个客户端的私有目录。

## Skills：更新整套并补齐新增目录

从宿主返回的当前 SKILL.md 绝对路径确认实际技能根目录：其直接子目录分别包含各技能的 SKILL.md。连接器内置技能使用其已安装的 skills 根目录；普通目录安装沿用原目标。该目录就是开始使用中 `install --dir "SKILLS_DIR"` 的目标。

执行新版 Skills 包的完整安装，不指定旧技能名单。安装器返回的名单包含新版包全部技能，因此连接器初始包没有的新增技能也会安装。逐份核验 metadata.version，读取本任务所需的新技能和引用；其他已安装技能由安装器保留。

让宿主重载技能，或提示用户开始新会话；随后核对实际加载路径、版本及新增技能是否出现在技能列表。若存在同名副本，按实际加载路径处理更新，避免继续读取旧副本。实际目录不可写或重载后仍只加载旧内容时，报告具体安装或宿主加载阻塞；分别报告文件安装与技能启用状态。

## 宿主权限与加载验收

安装目录尚未出现在任务 PATH 时，后续调用使用已核实的完整 CLI 路径，或在每次命令调用中传入相应 PATH。宿主可能单独显示安装或新命令入口的执行授权；按当前权限及用户已授权范围处理后继续，分别报告执行授权与版本检查结果。

在真实宿主中验证：CLI/Skills 分别发现新版时先询问用户，同意后仅升级获准的包和版本；用户拒绝或尚未回复时保留当前版本；should_notify=false 时保留记录；实际 CLI 入口使用新版本；新版包中新增技能目录安装并可加载；重启后核对实际版本与登录状态。归档内容、本地安装夹具和文件核验分别记录，结合宿主中的实际加载结果报告验收结论。
