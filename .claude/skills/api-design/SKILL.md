---
name: api-design
description: Load when designing, building, or reviewing APIs — versioning, auth patterns, rate limiting, idempotency, webhooks, breaking vs non-breaking changes, and long-running operations. Extends api-conventions.
---
<!-- status: BLESSED — load alongside api-conventions for full API design coverage. -->

## The blessed way

An API is a contract. Once published, breaking it has a cost paid by callers. Design for clarity, predictability, and evolvability — not for the implementation's convenience. The client's experience is the product.

## REST vs RESTful — know the difference

**REST** (Representational State Transfer) is an architectural style: stateless, client-server, cacheable, layered system, uniform interface.

**RESTful** is implementing REST properly:
- Resources are nouns, not verbs: `GET /users/{id}` not `GET /getUser`
- HTTP verbs carry meaning: `GET` reads, `POST` creates, `PUT` replaces, `PATCH` updates, `DELETE` removes
- State lives on the server or in the resource representation, not in the URL
- Collections are plural nouns: `/users`, `/orders`, `/products`

**Common violations (detect and fix):**
| Violation | Fix |
|---|---|
| `POST /getUser` | `GET /users/{id}` |
| `POST /createOrder` | `POST /orders` |
| `POST /deleteItem` | `DELETE /items/{id}` |
| `GET /users?action=delete&id=5` | `DELETE /users/5` |
| Mixed singular/plural (`/user` and `/products`) | Pick plural, apply consistently |

## OpenAPI specification — mandatory

Every API must have a machine-readable OpenAPI specification (`openapi.yaml` or `openapi.json`). It is not optional documentation — it is the contract.

**FastAPI**: generates the spec automatically at `/openapi.json`. Always verify it matches the intent; the auto-generated spec reflects the code, not necessarily what was designed.

**Other frameworks**: use a spec-first approach — write `openapi.yaml` first, generate stubs from it.

**Serve the spec** at a discoverable path: `/openapi.json` (machine) and `/docs` (human via Swagger UI or Redoc).

### Organized schemas — no inline definitions

All reusable types go in `#/components/schemas`. Use `$ref` consistently. Never define the same shape inline in two places.

```yaml
# WRONG — inline, duplicated
paths:
  /users:
    get:
      responses:
        '200':
          content:
            application/json:
              schema:
                type: object
                properties:
                  id: {type: string}
                  email: {type: string}

# CORRECT — defined once, referenced everywhere
components:
  schemas:
    User:
      type: object
      required: [id, email]
      properties:
        id:
          type: string
          format: uuid
        email:
          type: string
          format: email

paths:
  /users/{id}:
    get:
      responses:
        '200':
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/User'
```

### Spectral — the API lint gate

Run Spectral against the OpenAPI spec before declaring done. Zero errors required.

```bash
npx @stoplight/spectral-cli lint openapi.yaml
```

Spectral catches: missing descriptions, inconsistent naming, wrong response codes, missing error schemas, security definition gaps, and custom ruleset violations.

**Blessed `.spectral.yaml` base config:**
```yaml
extends:
  - "spectral:oas"
rules:
  operation-description: warn
  operation-operationId: error
  operation-tags: warn
  info-contact: warn
```

Add to `make lint` so it runs as part of the standard lint gate:
```makefile
lint:
	uv run ruff check .
	npx @stoplight/spectral-cli lint openapi.yaml
```

## Conventions

### 1. Versioning

- **URL versioning for breaking changes**: `/v1/`, `/v2/` — explicit, easy to route, easy to deprecate
- **No versioning for non-breaking additions**: adding a field to a response is backwards-compatible; adding an endpoint is backwards-compatible; changing a field type is not
- **What is a breaking change**: removing a field, renaming a field, changing a field's type, changing a status code meaning, making an optional parameter required, changing endpoint path
- **What is NOT a breaking change**: adding a new optional field to a response, adding a new endpoint, adding a new optional request parameter
- **Deprecation before removal**: a deprecated endpoint returns `Deprecation: true` header and a `sunset` date in the response; it lives for at least one release cycle before removal

### 2. Authentication patterns

- **Bearer token for user sessions**: `Authorization: Bearer <token>` — JWT or opaque token
- **API key for service-to-service**: `X-API-Key: <key>` header — never in the URL (logged by proxies)
- **Never in query params**: `?api_key=<key>` leaks into server logs, browser history, and referrer headers
- **Scope tokens**: each token has an explicit scope; the API validates scope, not just token validity
- **Short-lived access tokens + refresh tokens**: access tokens expire in minutes/hours; refresh tokens in days/weeks
- **401 vs 403**: `401 Unauthorized` = not authenticated (missing or invalid credentials); `403 Forbidden` = authenticated but not authorized (wrong scope/role)

### 3. Rate limiting

- **Limit by authenticated identity, not IP**: IP-based limits are bypassable; identity-based limits are enforceable
- **Return rate limit headers always** (not just on limit hit):
  ```
  X-RateLimit-Limit: 1000
  X-RateLimit-Remaining: 942
  X-RateLimit-Reset: 1719532800
  ```
- **`429 Too Many Requests` on limit hit** with `Retry-After: <seconds>` header
- **Different limits for different endpoint tiers**: read endpoints can have higher limits than write endpoints; auth endpoints must have strict limits (brute force protection)
- **Burst allowance + sustained rate**: allow a burst of N requests, then enforce a per-second/per-minute rate

### 4. Idempotency

- **Idempotency keys for mutations**: POST endpoints that create resources accept an `Idempotency-Key: <uuid>` header; same key → same response, no duplicate creation
- **Idempotency key lifecycle**: store the key + response for a minimum of 24 hours; return `409 Conflict` if the same key is reused with a different request body
- **GET/DELETE are naturally idempotent**: GET has no side effects; DELETE of an already-deleted resource returns `204` (not `404`)
- **PUT is idempotent by definition**: same PUT with same body → same result; enforce this in implementation

### 5. Webhooks

- **Sign webhook payloads**: HMAC-SHA256 with a shared secret; caller verifies `X-Signature-256: sha256=<hmac>` before processing
- **Retry with exponential backoff**: if the recipient returns non-2xx, retry with: 1s · 5s · 30s · 5m · 30m · 2h · 24h — then mark as failed
- **Deliver exactly-once guarantees via idempotency**: include a unique `event_id` in every payload; recipients deduplicate on it
- **Timeout quickly**: fail the delivery attempt after 10 seconds; the recipient should accept and process async
- **Dead letter queue**: failed deliveries after all retries go to a DLQ for inspection and manual replay

### 6. Long-running operations (async job pattern)

- **Accepted, not completed**: a request that starts a long job returns `202 Accepted` with a `Location` header pointing to a job status endpoint
  ```
  POST /reports/generate → 202 Accepted
  Location: /reports/jobs/job-123
  ```
- **Job status endpoint**: `GET /reports/jobs/job-123` returns `status: queued|running|completed|failed`; `completed` includes a link to the result
- **Never block the request**: do not make the client wait 30 seconds for a synchronous response; accept and process async
- **Result expiry**: completed job results expire after a stated TTL (e.g. 24h); document it
- **Progress events**: for operations where progress matters, provide a WebSocket or SSE endpoint; don't poll the client into rate-limiting itself

### 7. Error body convention

Every error response uses the same structure:
```json
{
  "error": {
    "code": "<machine-readable-slug>",
    "message": "<human-readable explanation>",
    "details": [
      {"field": "<field_name>", "issue": "<what is wrong>"}
    ]
  }
}
```
- `code` is stable across API versions — clients key off it for error handling
- `message` is for developers, not end users — it can change between releases
- `details` is for validation errors — one entry per invalid field

## Anti-patterns to DETECT (and the fix to PROPOSE)

- **RPC-style URLs** (`POST /createUser`, `GET /getOrder`) → propose resource-oriented RESTful paths
- **API key in query param** → propose `X-API-Key` header
- **Breaking change without version bump** → propose `/v2/` route or field aliasing
- **No rate limit on auth endpoint** → propose strict limits (e.g. 5 requests/minute per IP for login)
- **Synchronous response for a 30-second operation** → propose `202 Accepted` + job status endpoint
- **Unsigned webhook** → propose HMAC-SHA256 signature verification
- **`404` on repeat DELETE** → propose `204 No Content` (DELETE is idempotent)
- **Generic error body** (`{"error": "something went wrong"}`) → propose the structured error convention
- **`200` for everything, errors in the body** → propose the correct HTTP status code
- **Inline schema definitions** (same shape defined twice) → propose `$ref` to `#/components/schemas`
- **Missing OpenAPI spec** → mandatory; generate or write it
- **Spec not linted with Spectral** → add `spectral lint openapi.yaml` to the lint gate

## Review checklist

- [ ] All endpoints follow RESTful resource naming (nouns, plural, correct HTTP verbs)
- [ ] OpenAPI spec exists (`openapi.yaml` / `openapi.json`) and is served at `/openapi.json`
- [ ] All reusable types are in `#/components/schemas`, referenced via `$ref`
- [ ] `spectral lint openapi.yaml` passes with zero errors
- [ ] Breaking changes increment the URL version (`/v2/`)
- [ ] Auth tokens are in `Authorization` or `X-API-Key` header — never in query params
- [ ] Every endpoint has documented rate limits; `429` + `Retry-After` returned on limit
- [ ] Mutation endpoints accept and deduplicate `Idempotency-Key`
- [ ] Webhooks are HMAC-signed and retried with exponential backoff
- [ ] Long-running operations return `202 Accepted` + `Location` job-status endpoint
- [ ] All error responses use the structured `{error: {code, message, details}}` body
- [ ] `401` vs `403` are used correctly (auth vs authorization)
