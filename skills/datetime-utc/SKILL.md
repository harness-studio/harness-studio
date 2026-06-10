---
name: datetime-utc
description: Load when designing, building, or reviewing ANY application that handles time — backend, database, data lake, or frontend. The universal rule: everything is UTC; only the frontend localizes. Applies to every stack, every project.
---
<!-- status: BLESSED — ratified. Non-negotiable, every application. -->

## The blessed way

**All datetimes are UTC, everywhere, always.** The backend computes in UTC, the database stores UTC, the data lake / warehouse stores UTC, messages on the wire are UTC. **Only the frontend localizes**, at the moment of display, to the user's timezone. There is exactly one timezone boundary in the system — the UI — and it is one-way.

## Conventions (the blessed patterns)

1. **Timezone-aware UTC, never naive.** Backend: `datetime.now(timezone.utc)` — never `datetime.now()` or `datetime.utcnow()` (both produce naive datetimes that silently misbehave).
2. **Wire format is ISO 8601 with an explicit offset/`Z`.** `2026-06-09T12:00:00Z`. Reject timezone-naive input at the boundary with a `422` — never "assume it's UTC".
3. **Store UTC.** Database/data lake columns hold UTC (ISO 8601 text, or a timestamptz / epoch). Never store local time. A column's timezone is never ambiguous because the answer is always UTC.
4. **Convert offset-bearing input to UTC before using it.** `2026-06-09T08:00:00+05:30` is `02:30:00Z` — normalize to UTC immediately, then all comparisons/filters are UTC-vs-UTC.
5. **The frontend owns localization.** It receives UTC, renders in the user's locale/timezone. The backend never formats for a locale.

## Anti-patterns to DETECT (and the fix to PROPOSE)

- **`datetime.now()` or `datetime.utcnow()`** (naive) → propose `datetime.now(timezone.utc)`.
- **A datetime column/field with no timezone discipline stated** → propose "UTC, tz-aware ISO 8601".
- **An endpoint accepting datetime params without rejecting naive strings** → propose tz-aware-only validation (`422` on naive).
- **Offset-bearing input compared/filtered without converting to UTC first** → propose normalize-to-UTC at the boundary, plus a test that an offset input filters against its UTC-equivalent.
- **Backend formatting timestamps for a locale / timezone** → propose returning UTC and moving localization to the frontend.
- **Mixed local + UTC anywhere in backend/DB/lake** → propose UTC throughout.

## Review checklist

- [ ] No naive datetimes anywhere in the backend (`now(timezone.utc)` only).
- [ ] All stored timestamps (DB, data lake) are UTC.
- [ ] Datetime inputs are tz-aware ISO 8601; naive input is rejected (422).
- [ ] Offset-bearing inputs are normalized to UTC before use (with a test proving correct conversion).
- [ ] Localization happens only in the frontend.
