---
description: Manage work items via the hssd PM (list / add / claim)
argument-hint: [list | claim <ID> | add "<title>"]
---
Request: $ARGUMENTS

Run the matching `hssd` command and show the result. Use the CLI — never edit the PM database by hand.

- empty or `list`        → `hssd work list`
- `claim <ID>`           → `hssd work claim <ID>` (atomic; creates the feature branch)
- `add <title>`          → `hssd work add --title "<title>"`
- `show <ID>`            → `hssd work show <ID>`
