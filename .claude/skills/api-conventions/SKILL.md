---
name: api-conventions
description: Load when designing, building, or reviewing any HTTP/REST API — response shapes, HTTP status codes, filtering/range semantics, pagination, and error bodies. The blessed contract so every endpoint answers the same recurring questions the same way.
---
<!-- status: BLESSED — ratified. Exists so endpoint contracts are decided ONCE, not re-litigated per story. -->

## The blessed way

Every endpoint answers the same recurring contract questions the same way. These are settled here so a story's spec never has to re-decide "array or envelope?", "404 or empty?", "inclusive or exclusive?" — and so an adversary can flag any endpoint that deviates.

## Conventions (the blessed contract)

1. **Collections return a bare JSON array.** `GET /things` → `[ {...}, {...} ]`. A single resource returns an object. (Add an envelope only when pagination metadata is actually required — see 6.)
2. **Empty result is `200` with `[]`, never `404`.** `404` is only for "this specific resource by id does not exist" (`GET /things/{id}`). A filter that matches nothing is a successful empty query.
3. **Status codes:** `200` read/ok · `201` created · `204` no content · `400` malformed · `422` validation failure (FastAPI/Pydantic default) · `404` specific resource-by-id missing · `409` conflict (e.g. idempotency/duplicate) · `503` dependency/lock unavailable. Don't invent ad-hoc codes.
4. **Time ranges are closed intervals `[since, until]`** — `>= since AND <= until`. Matches natural language "between A and B" and avoids off-by-one at exact-timestamp boundaries. Default window when omitted: state it (e.g. last 24 h); one-sided supply anchors the other end symmetrically.
5. **Sorting is explicit with a deterministic tiebreak.** State the order (e.g. `detected_at DESC`) AND a tiebreak on a unique column (`id DESC`) so equal sort-keys never produce flaky order.
6. **Pagination policy is per tier.** Lightweight/PoC tier: no pagination (return all matching rows; fixtures are small). Full tier: `limit`/`offset` (or cursor) with a documented default cap. State which applies.
7. **Validation errors are structured.** A cross-field rule (e.g. `since <= until`) is a single `model_validator` producing one message that names both fields — not two independent parse errors. Inverted range → `422`.
8. **Filters are optional unless stated.** "filtered by X" means X narrows when supplied, not that X is mandatory. A required filter must be called out explicitly.

## Anti-patterns to DETECT (and the fix to PROPOSE)

- **`404` for an empty filter result** → propose `200 []`.
- **An envelope `{items, total}` with no pagination need** → propose a bare array (or justify the envelope).
- **Unspecified sort / no tiebreak** → propose `<col> DESC, id DESC`.
- **Half-open or unspecified interval bounds** → propose closed `[since, until]`.
- **Datetime params without tz-aware validation** → defer to `datetime-utc` (422 on naive).
- **A response/field contract left unstated** ("returns the anomalies") → propose the exact field set + types.
- **Ad-hoc or wrong status codes** → propose the table-3 mapping.

## Review checklist

- [ ] Collection endpoints return bare arrays; empty = `200 []` (not 404).
- [ ] Status codes follow the blessed mapping.
- [ ] Time ranges are closed intervals with a stated default window.
- [ ] Sort order is explicit with a deterministic tiebreak.
- [ ] Pagination policy matches the stack tier and is stated.
- [ ] Cross-field validation yields one structured `422`; field set + types are specified.
