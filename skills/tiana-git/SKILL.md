---
name: tiana-git
description: 使用 Tiana Git 管理 Git 实例和原生仓库，关联项目远程地址、同步源码分支及应用版本。SQLite 数据库分支使用 tiana-sqlite；托管 Web 构建发布使用 tiana-web。
license: Apache-2.0
metadata:
  author: Tiana Cloud
  version: "1.0.19"
  parent: tiana
  source: https://github.com/tianacloud/agent-skills/tree/main/skills/tiana-git
---

# Tiana Git

安装 CLI、浏览器登录和通用资源恢复见 `tiana` 技能。本技能操作用户自己的 Git 实例；使用原生 Git 和包内的 `git-remote-tiana`。

## 每个会话一次的更新检查

**本会话首次使用任一 Tiana 技能时，先完成以下步骤，再开始登录、查询模板或操作应用：**

CLI 与 Skills 各自独立比较本包的 npm 最新正式版。下面的版本检查与安装只访问公共包仓库，不需要 Tiana 登录，不操作 Tiana 云端资源；用户要求暂不登录或不操作云端资源时仍执行。用户明确要求离线、禁止联网或禁止安装时遵从该限制。

1. 执行 `tiana version`，按 `tiana` 技能的“开始使用”指引核验最低版本；缺少 CLI 或版本过低时，自动安装 npm latest 正式版并重新核验。
2. CLI 满足最低版本后，从本会话实际加载的 SKILL.md 的 `metadata.version` 取得 `SKILLS_VERSION`，在同一次 shell 调用中赋值并**实际执行** `tiana version check --skills-version "$SKILLS_VERSION" --json`。这一步检查是否有更新版本。
3. `updates` 中 CLI 或 Skills 有新正式版时，**自动安装各项实际返回的 `latest_version`，无需再次询问**；`should_notify=false` 也执行。Skills 按新版包完整安装，覆盖已有技能并补齐新增技能。各连接器初始版本仅用于分发，后续更新独立于连接器发版；安装目标及重载按 `tiana` 技能的“更新”指引，连接器内使用时再读其中链接的宿主说明。
4. 在对话中简短报告实际 CLI/Skills 版本、检查状态与更新结果（包括新增技能及是否需要重载）；检查不可用时明确说明未能确认是否有新版，更新失败时说明实际错误。

实际发起检查命令后才记录已尝试，保留检查结果或执行错误，以及两个包的安装与核验结果。各 Tiana 技能共享这份记录；后续轮次、重复加载或切换技能复用记录，每个包失败后本会话不自动重试。上下文压缩或任务交接时保留记录，新会话重新检查。仅运行 `tiana version` 只完成第 1 步。

CLI 仍管理检查缓存和共同的 24 小时提醒额度；该额度不限制自动更新或本会话首次结果报告。更新核验完成后继续原任务；失败时按更新流程判断可否继续。

## 实例与仓库

1. 在实际命令环境核验 `git --version`、`tiana version` 和 `git-remote-tiana` 路径。Windows 阅读 `tiana` 技能的“Windows 安装与 Git helper 排查”指引。
2. 阅读 `tiana` 技能的“CLI 命令与恢复”指引，复用已核实的 Git 实例；需要查找时 `tiana git list/show`，缺少才 `tiana git create NAME --wait`。等待就绪后保存完整实例 ID 和实际 Endpoint。
3. 根据返回 Endpoint 使用 `tiana://HOST[:PORT]/repo.git`。原生 Git 自动调用 helper，账号凭据由 CLI 管理；不把 Token 放入 remote URL。
4. 克隆、fetch、commit、branch 和 push 使用原生 Git。Git refs 与 SQLite 数据库分支是不同对象。保持已有 remote、跟踪设置及用户工作区；新远程名称冲突时先核对目标。

## 同步应用源码

标准 Git 数据连接失败时，阅读 `tiana` 技能的“兼容传输”指引；可通过 `tiana --transport compat git` 的直接子命令访问原 remote。结果未知的 push 先核对实际推送目标的 ref。

阅读 [源码与版本](references/source-releases.md)，确认项目托管选择和实际推送范围。全新 Tiana 应用创建自己的 Tiana Git；已有外部仓库首次同步时确认用户选择。提交源码与锁文件，排除凭据，普通推送并核验远端对应版本引用。

Web 发布时从干净、确定的源码提交构建，在交付记录中保存实际 `git_instance_id`、完整源码提交号和对应发布回执。推送失败停止关联的 Web 发布，结果不明先读取远端状态。Web 构建和上传见 `tiana-web` 技能。
