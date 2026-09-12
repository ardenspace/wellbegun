# Backend common-layer registry

> **Rule: every endpoint goes through the common layers.** No endpoint invents its own error shape, auth check, or log format. If a step needs behavior the common layers lack, extend the layer and update this roster in the same commit — never fork the behavior locally.

**Common layer folder:** `<path — e.g. src/server/common/>`

| name | purpose (one line) | location | use when |
|---|---|---|---|
| Error format | The single error response envelope | `<folder>/errors.*` | Every non-2xx response |
| Auth middleware | Who is calling, verified once | `<folder>/auth.*` | Every protected route |
| Logging | Structured request/event logging | `<folder>/log.*` | Every handler |
| Pagination helper | One cursor/offset convention | `<folder>/pagination.*` | Every list endpoint |
