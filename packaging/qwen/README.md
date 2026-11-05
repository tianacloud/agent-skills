# Tiana Cloud for QwenWork Desktop

This ZIP contains the published Tiana CLI {{CLI_VERSION}} for Windows x64,
macOS Apple Silicon and macOS Intel, plus all Skills from
@tianacloud/agent-skills {{SKILLS_VERSION}}. The connector manifest version is
{{SKILLS_VERSION}} and must match the submission form. QwenWork selects the
native program from the corresponding `bin/<os>_<arch>/` directory.

Read `skills/tiana/SKILL.md` for account login, environment selection and updates,
then the relevant product Skill for business operations. The native CLI manages
its account credentials. `tiana version` reports the CLI version.

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
