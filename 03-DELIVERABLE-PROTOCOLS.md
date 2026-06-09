# Harness Studio — Graded Deliverable Protocols

> A client may grade the **ADR and AI Interaction Log as much as the code**. Here are the protocols to produce them as first-class product. The Harness Studio advantage: the adversarial process **generates** these artifacts naturally — you just capture them.

---

## 1. AI Interaction Log (live-capture protocol)

> **Capture as you work, never reconstruct at the end.** A reconstructed log looks reconstructed. A live log shows real judgment — and our process (roles + adversaries + corrections) makes it a tech-lead differentiator.

**What the client requires:** (1) each meaningful prompt, (2) the output (summary is fine), (3) corrections/redirections when the AI got it wrong, (4) a 3-5 bullet reflection at the end.

**Entry format (one per meaningful role invocation):**

```markdown
### [Phase] Role — short objective
**Prompt (summary):** what I asked the AI in that role.
**Output (summary):** what it produced.
**Correction/redirection:** what was wrong and how I redirected. (If nothing, "—".)
**Why it mattered:** 1 line (optional, but gold for a tech lead).
```

**Why this impresses:** the most valuable entries are the **corrections** and the **adversaries' findings**. When the log shows "the Architecture Adversary tore down the first stack proposal because X, so I switched to Y" or "the Test Adversary found a race the happy path hid", it proves you **govern** the AI — not the other way around. Record those moments with care.

**Final reflection (3-5 bullets, required):**
- What the AI was good at (e.g., scaffolding, boilerplate, first draft of tests).
- Where it failed (e.g., confident but subtly wrong concurrency code; declaring "done" early).
- What you had to check manually (e.g., actually running the stress test; reviewing transaction isolation).
- (Optional) what the adversarial process caught that a naive flow would have missed.

> Honesty tip: also record where the AI led you down a dead end. Technical panels value an honest, critical log over one that pretends the AI got everything right.

---

## 2. ADR (Architecture Decision Record — 1 page)

> Comes straight from Phases 0 and 2. Don't write it from scratch at the end — **assemble it from what the roles already produced.**

**The 4 questions the client requires (answer exactly):**

1. **The 2-3 most important decisions, and why.** → from P2 (Architect proposed, Adversary challenged). For each: the decision, the alternative considered, why this one won. Include the highest domain-risk decisions (e.g., concurrency/isolation strategy, persistence choice, dashboard transport).
2. **What was unclear in the spec and what you assumed.** → straight from the Definition Skeptic's list (P0). This is already done if you captured P0. The client explicitly said the spec leaves things open — showing you *identified and consciously assumed* them is a seniority signal.
3. **What would change at significant scale (you define "significant").** → from the Architecture Adversary's scale challenges. Put a number on it (e.g., 50 → 50,000 users, or much higher request rates) and say what breaks first and what replaces it.
4. **What you deliberately left out, and why.** → from P0's out-of-scope + budget right-sizing decisions. List and justify (time, marginal value, controlled risk).

**Form:** 1 page. Direct. Decision → reason → trade-off. No filler. A tech lead writes a lean ADR.

---

## 3. README & repo (delivery standard)

The client will **run the code** and won't penalize setup issues *if the README is clear*. So the README is part of the grade.

**Minimal README:**
- One line on what it is.
- Prerequisites (versions).
- How to bring it up (exact commands, from scratch — including DB if any).
- How to run the tests (especially the concurrency ones — they prove the guarantees).
- How to exercise each endpoint (curl/examples) and how to open the dashboard.
- What's included vs deliberately out (link to the ADR).

**Repo:**
- Single public git repository.
- Clean structure, backend/frontend separation.
- ADR and AI log versioned in the repo (e.g., `/docs/ADR.md`, `/docs/AI_LOG.md`).
- Commits that tell the story of the process are a bonus (they show the phases).

---

## The principle that binds the three
The graded deliverables **are not overhead** — they're the evidence of the method. A common candidate ships code + a hastily-assembled messy log. Harness Studio ships code **proven by adversaries**, an ADR that shows challenged decisions, and an AI log that reads like the minutes of a governed engineering team. That's the difference between "I used AI" and "I led AI".
