# Backend common-layer registry

> **Apply the project’s active shared contracts.** Reuse established error/auth/logging layers where applicable. Add only layers the project needs; changing their public contract is a decision to grade, while using it is ordinary implementation. Update the relevant entry with an approved shared change.

**Common layer folder:** `<path — e.g. src/server/common/>`

| name | purpose (one line) | location | use when |
|---|---|---|---|
| Error format | The single error response envelope | `<folder>/errors.*` | Every non-2xx response |
| Auth middleware | Who is calling, verified once | `<folder>/auth.*` | Every protected route |
| Logging | Structured request/event logging | `<folder>/log.*` | Every handler |
| Pagination helper | One cursor/offset convention | `<folder>/pagination.*` | Every list endpoint |

<!-- Active areas only. Retain public contracts, required current constraints and stable decision keys here; link detailed rationale/history without duplicating it. -->
