# Stories & Acceptance Criteria — <engagement title>

> Output of Phase 1. The AC Adversary validates each AC: testable? measurable? covers error/edge/concurrency? "Guarantee/atomicity/under-concurrency" requirements MUST become stress tests.

## Story <ID>
**As a** <persona> **I want** <action> **so that** <value>.

### Acceptance Criteria
- **[AC-1]** Given <context>, when <action>, then <verifiable result>.
  - Type: happy / error / edge / **concurrency**
  - Proven by: <test/evidence — e.g., "K simultaneous events on the same counter ⇒ count == K">
- **[AC-2]** ...

### Example data
<concrete examples>

### Dependencies
<other stories/order>

---
<!-- repeat per story -->

## AC Adversary check
- [ ] Every AC is objectively testable (I could write the test right now).
- [ ] Each guarantee/atomicity/concurrency requirement has a matching **stress test**.
- [ ] Error and edge cases covered, not just the happy path.
- [ ] No AC contradicts another.
