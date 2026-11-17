# Tiana Cloud for QwenWork Desktop

This ZIP contains Tiana CLI built from the published source version {{CLI_VERSION}} for Windows x64,
macOS Apple Silicon and macOS Intel, plus all Skills from
@tianacloud/agent-skills {{SKILLS_VERSION}}. The connector manifest version is
{{SKILLS_VERSION}} and must match the submission form. QwenWork selects the
native connector entrypoint from the corresponding `bin/<os>_<arch>/` directory.

Read `skills/tiana/SKILL.md` for account login, environment selection and updates,
then the relevant product Skill for business operations. The native CLI manages
its account credentials. `tiana version` reports the CLI version; `tiana --version`
reports the connector manifest version. The entrypoint maps `auth init` to blocking
browser login, `auth show --status` to an account check, `auth logout` to logout,
and `identity whoami` to the nonsecret account identity. Status refreshes an expired
session when possible and does not query quota. Ordinary unauthenticated status
is `{"status":"unauthorized"}` with exit 0; operational errors use nonzero exits
and JSON `code`/`message` on stderr.

The packaging script compiles the default source into the bundled core in
`bin/<os>_<arch>/libexec/`. `tiana version --json` reports it through
`data.default_acquisition_source`. Explicit environment values (including empty)
are preserved, and `login --from` takes priority. Use this entrypoint for Agent commands
as well as desktop authentication. Upgrade the connector package as a unit to keep
the entrypoint, core, manifest and Skills together.

The native CLI runs without Node.js. Native Git workflows require Git and the
official npm package's `git-remote-tiana` installation described in the Skills.
The npm CLI requires Node.js 20+; the Skills installer requires Node.js 22.20+.
Web projects use their documented Node.js/npm toolchain.

Before submission, verify the target client's command requirements and complete
real installation, browser authorization and business-operation acceptance on
each target platform. Packaging checks establish archive contents and integrity.

Source: https://github.com/tianacloud/cli and
https://github.com/tianacloud/agent-skills.
See LICENSE and licenses/cli-LICENSE for the Apache-2.0 licenses.

## 审核补充材料

本包将全部 Skills 与各桌面平台的 CLI 入口整合为一个 Tiana Cloud 连接器。
请从 [review/01-审核补充说明.md](review/01-审核补充说明.md) 阅读产品归属、
官网备案证据、公开来源和 API 授权链路。`review/` 是独立审核材料目录。
其中的原厂确认函为待核实、填写及盖章的草稿；公开信息补全文案尚未发布。
