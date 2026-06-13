# AI Interaction Log

> **Interactions**, **Corrections**, and **Reflection** are human-authored. Run `hssd ailog` to
> (re)generate the **Summary** and the **Appendix** (harness agent calls) from
> `.harness/logs/metrics.jsonl`; your human sections are preserved across re-runs. Capture LIVE —
> don't reconstruct at the end.

## Summary

_(auto — run `hssd ailog`)_

## Interactions

> Human-authored. One entry per meaningful prompt YOU issued to an AI tool (Claude Code, Cursor,
> Copilot, ...). At least 3 entries for the final submission. Per-entry shape:

### 1. Human — <ISO date>

**Prompt:**

```text
<what you asked>
```

**Output (summary):**

```text
<what came back — a summary is fine>
```

**Correction / redirect (if any):** <what you fixed, or "none">

## Corrections & redirections

> Human-authored. Must not be empty: list each correction/redirect, plus at least one instance
> where you checked the AI and it was correct (shows active supervision).

- <correction or verified-correct instance>

## Reflection

> Human-authored. 3-5 bullets, each grounded in a concrete artifact (work item ID, endpoint,
> agent role, error class, filename) — no platitudes.

- <what the AI was strong at — named instance>
- <where it failed you — named instance>
- <what you double-checked manually>

## Appendix — Harness agent calls (auto from metrics.jsonl)

_(auto — run `hssd ailog`)_
