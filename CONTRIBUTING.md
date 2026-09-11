# Contributing

Edit only the canonical copies under `skills/`. WorkBuddy ZIP files are generated
from those sources and must not be edited or committed.

When product behavior changes, update the smallest relevant reference and keep
the status of preview interfaces explicit. A draft specification is not evidence
that an API is available.

Before opening a pull request, run:

```sh
npm ci
npm run validate:ci
```

To inspect WorkBuddy packages locally:

```sh
npm run build:workbuddy
```
