# Contributing to Harness Studio

> This kit exists to be **used, tested, and improved** by whoever receives it. Here's how to adopt it, give useful feedback, and extend the framework. The kit's own evolution follows the principle it preaches: every failure becomes a new guard.

## How to adopt (start small)

1. Pick **one small, real engagement** (a feature, a bug, a vertical slice). Don't start with the whole company.
2. Run the flow from `00-OPERATING-MANUAL.md` + `04-KICKOFF.md`, phase by phase.
3. Use the fast lane for the trivial and the adversarial rigor for what's at risk of being wrong.
4. Capture the AI Interaction Log live — it's your learning data.

## How to give useful feedback

Generic feedback ("seemed nice") doesn't help. What helps:

- **Where a gate caught something** a naive flow would have missed. (Proof of value.)
- **Where a role became bureaucracy** — spent tokens/time without adding value. (Candidate to cut or move to the fast lane.)
- **Where the process broke** — a phase stalled, a handoff was ambiguous, an adversary gave too many false positives.
- **What was missing** — a role, gate, or template you had to improvise.

### Feedback template (one per engagement)
```markdown
## Engagement: <what it was> — <date>
- Lane used: fast / standard / deliberate
- Gate that added the most: ...
- Role that became bureaucracy: ...
- Where it broke / created friction: ...
- What was missing (role/gate/template): ...
- Escape: did anything get through and get caught later? What?
- Cost note: time/tokens vs perceived value
```

## How to extend the framework

The kit is modular. The most common extensions:

- **Add a role:** copy the format in `01-ROLES.md` (mandate, "rewarded for", takes→delivers). Remember the rule: if it's a role that builds, an adversary that judges it must exist.
- **Add a gate:** prefer computational (test/lint/script) over inferential. Define what it **blocks** and with what evidence.
- **Add a template:** put it in `templates/` and reference it in the relevant protocol.
- **Tune autonomy:** promote a gate from "human" to "automatic" only when the escape rate proves the confidence; demote it when a surprise audit catches something.

## The evolution principle (steering loop)

The rule that keeps the kit honest: **every escaped defect becomes the question "what guide or gate would have caught this?"** — and the answer is added to the framework. The kit isn't born perfect; it hardens with every engagement. Whoever uses it and reports escapes is literally improving the product.

## What would be great to get back

- Real (anonymized) AI Interaction Logs — they show where the method helps and where it gets in the way.
- New domain-specific roles/gates/templates.
- Cases where the harness was too heavy (to calibrate right-sizing).
- Metrics: escape rate, first-pass, review toil, cost per delivery.
