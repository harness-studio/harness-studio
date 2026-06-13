---
description: List Harness Studio templates, or register/remove your own
argument-hint: [list | add <name> <git-url> [tech] | rm <name>]
---
Request: $ARGUMENTS

- empty or `list` → `hssd template list` (blessed catalog + my registered templates).
- `add <name> <git-url> [tech]` → register a template I trust that is **not already listed**:
  `hssd template add --name <name> --from=<git-url> --tech <a,b>`
  (The blessed templates are already in the list — do **not** re-register them; `add` will refuse a URL that's already known.)
- `rm <name>` → `hssd template rm --name <name>` (removes one of my registered templates).

To actually use a template: `hssd template import --from=<git-url>` (into this repo) or `hssd new <name> --from=<git-url>`. Any git URL works. Whether to apply one is an architecture (P2) decision.
