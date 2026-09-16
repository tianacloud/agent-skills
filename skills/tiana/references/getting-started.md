# Getting started — CLI 0.2.0 preview

CLI 0.2.0 is available from npm as `@tianacloud/cli@0.2.0`. The service deployment
and your account's WorkBuddy Connector entry must be verified separately.

## First use

In WorkBuddy, use the Tiana Cloud Connector installation/connection entry
provided for your account by the delivery owner. It prepares the managed CLI
and opens the existing Console browser login. A Skill alone does not install
or authenticate the Connector.

After installation, check:

    tiana --version
    tiana verify-install --json
    tiana auth status --json

Expect CLI 0.2.0, helper contract 3, matching SQL executor and a readable public
Gateway CA. If installation fails, restore the complete matching package;
do not download a different helper, build SDK source during chat, or read
credential files.

For an ordinary terminal, install the complete native platform package or the
same CLI npm package, then run:

    tiana auth login

The browser must reach https://console.service.internal.tiana.com from the
user's network. The CLI and WorkBuddy's managed Node runtime also need the
deployment's existing trust configuration. Follow the delivery installation
instructions for the public CA; it is not a Token.

## Continue across chats and restarts

The CLI stores login and instance credentials separately from installation.
Use the same account and full instance ID in a new chat. Inspect existing
instances rather than assuming a new chat needs a new database. For unfinished
creation, inspect the current account's requests and resume the intended task.

See [CLI commands and recovery](cloud-cli.md) for exact flags and partial
success handling, and [Instances and tokens](instances-and-tokens.md) for the
resource model.
