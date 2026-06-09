---
description: List Harness Studio templates, or register the blessed ones
argument-hint: [list | add-blessed]
---
Request: $ARGUMENTS

- empty or `list` → run `hssd template list` and show the catalog (blessed + my registered templates).
- `add-blessed`  → register the two official templates:
  ```bash
  hssd template add --name frontend --from=https://github.com/harness-studio/hssd-template-vite-react-ts --tech react,typescript
  hssd template add --name backend  --from=https://github.com/harness-studio/hssd-template-fastapi-sqlite --tech python,fastapi
  ```

Any git URL also works: `hssd template import --from=<git-url>` (into this repo) or `hssd new <name> --from=<git-url>` (fresh project). Whether to actually apply a template is an architecture (P2) decision.
