# Design token registry

> **Reuse the active token contract.** The token source file is the source of truth; this roster points at it and carries only constraints code cannot express. Define literal restrictions and exceptions in the project’s applicable checks. Do not create a token registry for a project with no UI.

**Token source file:** `<path/to/tokens file — e.g. src/styles/tokens.css>`

| name | purpose (one line) | location | use when |
|---|---|---|---|
| `color.*` tokens | Product palette translated from the begin-lens product character | `<token file>` | Any color in any component |
| `space.*` tokens | Spacing scale | `<token file>` | Margins, paddings, gaps |
| `type.*` tokens | Font families, sizes, weights | `<token file>` | Any text styling |

<!-- Add rows per token group, not per token. The token file itself carries the values. -->

<!-- Active areas only. Retain public contracts, required current constraints and stable decision keys here; link detailed rationale/history without duplicating it. -->
