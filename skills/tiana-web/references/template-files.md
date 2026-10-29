# 模板素材文件

本参考描述配套格式 2 的源码候选行为。实际使用前核对目标服务端已经部署并启用
`template_files_v1`；兼容版 C 会拒绝新格式。本地脚本存在或打包成功不代表已上线。
程序、数据库、小图片与预览的分工见[数据与素材存储](storage-and-assets.md)。

## 声明与路径

有安装必需且可公开的外置素材时，在原有 `metadata.json` 增加
`"file_seeds": "template-files"`，将其实际字节放在工程根部 `template-files/`。
保留原来的名称、说明、数据库需求与变量。目录内全部文件参与安装；不得混入用户
附件、凭据、作者环境文件或私人记录。

| 位置 | 同一文件的路径 |
| --- | --- |
| 源码 | `template-files/images/cover.webp` |
| 安装包独立材料 | `files/images/cover.webp` |
| 应用和初始 SQL | `template-assets/images/cover.webp` |
| Console / CLI 租户目录 | `WEB_ID/template-assets/images/cover.webp` |

素材为 1..256 个普通文件，单个和合计均不超过 16 MiB。路径为 UTF-8，相对路径
最长 1,024 字节；拒绝重复、文件/目录冲突、软链接、特殊文件、绝对路径、`.`/`..`、
反斜线、控制字符和百分号编码。未声明素材时省略字段与目录，不造空素材流程。

程序按[文件 API](files.md)使用 `context.files`：

```js
export async function mount(root, { files }) {
  const image = document.createElement('img');
  image.alt = '封面';
  root.append(image);
  const unbind = await files.bindImage(image, 'template-assets/images/cover.webp');
  return () => unbind();
}
```

数据库保存这条应用相对路径。实际 Web ID 由当前应用上下文提供，不将作者 URL、
临时授权 URL、租户前缀或 OSS key 固化到源码/SQL，也不替换二进制素材中的变量。

## CLI 初始化后的普通开发

`web init-template` / `init-share-template` 校验并原样解压源码，其中的 `template-files/`
仍在本地。它们不创建应用，也不上传素材。读取声明、确认每份素材和来源后，保存
本次新建应用的真实 `data.id`，为这个尚未初始化的新目录逐项准备文件：

```sh
tiana file put ./template-files/images/cover.webp WEB_ID/template-assets/images/cover.webp --json
tiana file put ./template-files/documents/guide.pdf WEB_ID/template-assets/documents/guide.pdf --json
tiana file list WEB_ID/template-assets/ --json
tiana file get WEB_ID/template-assets/images/cover.webp ./verified-cover.webp --json
```

把 `WEB_ID` 替换为创建回执中的真实 ID。下载目标必须不存在。核对字节数和 SHA-256，
在 `web serve WEB_ID` 中实际读取，再普通发布。`web publish` 只更新程序包，不自动
复制 `template-files/`。同名默认拒绝；未知上传先检查原上传标识，不能用 overwrite
重试未知写入。已存在应用沿用其实际文件，不能因改名、更新程序或用户删除素材而
重新灌入。用户明确要求修改的文件按普通文件操作单独处理。

## 制作格式 2 安装包

从同一个确定 Git 提交导出源码，在该提交的干净目录安装依赖、构建。
使用[分享流程](share-template.md#4-打包和发布)中的打包脚本；素材从传入的固定
`source.zip` 读取，不能只存在于作者工作目录。声明素材时，脚本生成：

- `source.zip` 中的 `template-files/`，用于服务端逐字节核对。
- `files/` 中的独立素材，包含相同字节，供两种安装模式直接复制。
- `install.json` 的 `format_version: 2`、`requires: ["template_files_v1"]` 及 `files`。
  文件清单 version 为 1，root 固定 `template-assets/`，按路径的 UTF-8 字节顺序排列。
  每项包含路径、大小、SHA-256 和合法 Content-Type。

清单摘要取 `files` 对象在安装清单中的原始 UTF-8 字节；整包摘要取最终完整
`install.zip`。不能把源码包摘要代替整包摘要，或重排 JSON 后重算清单摘要。
支持两种安装模式的是这份完整包：安装者直接安装时不创建源码库，素材仍取自
独立材料。发布者的 `--without-source` 则只支持无素材旧格式包，不能省略新格式
用于核对的源码，也不能未经授权默默改为提供源码。

检查干净 `dist` 和 `site.tweb`，排除外置素材目录、改名副本、原始字节和 base64
内嵌；脚本能检查常见复制/内嵌，不能证明所有自定义编码或转换后的资源都已排除。
平台根图标仍按例外保留，小图片按 16 KiB 规则确实进入 JS。由 Agent 复核源码、
构建过程及实际文件访问。无素材包继续省略格式、必需能力与文件清单字段。

## 实际验收与恢复

至少覆盖“保留源码/直接安装 × 桌面/手机”四种组合。使用独立测试模板，包含
超过 16 KiB 的图片、附件、内嵌小图片和引用相对路径的合成 SQL 记录。另验证
无素材包跳过文件步骤且不占素材预留，不能用无素材样例替代素材验收。

核对原任务/安装回执、文件数量与字节、CLI 路径、数据库和实际应用读回。
首次打开、刷新、重开和另一授权会话均能访问；修改一份安装不影响其他安装，
未授权租户无法读取，预览的恢复示例不修改真实应用。存在上传功能时另验证上传。

安装失败或响应未知时刷新原安装记录，沿原根任务恢复，不新建安装替代未知结果。
模板 V1 中断后发布 V2，恢复仍固定 V1 材料；重试不重复复制或入账。用户改动、
删除已安装文件后，不自动补齐或覆盖。保存各组合的真实回执、哈希及读取证据，
未验证步骤保留未完成状态，不将本地打包或脚本测试当作云端安装通过。
