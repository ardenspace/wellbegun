# Design token registry

> **Rule: no raw hex/px/font literals outside the token file.** Every color, spacing, radius, and type value in product code comes from a named token. The token source file is the registry; this roster only points at it.

**Token source file:** `<path/to/tokens file — e.g. src/styles/tokens.css>`

| name | purpose (one line) | location | use when |
|---|---|---|---|
| `color.*` tokens | Product palette translated from the begin-lens product character | `<token file>` | Any color in any component |
| `space.*` tokens | Spacing scale | `<token file>` | Margins, paddings, gaps |
| `type.*` tokens | Font families, sizes, weights | `<token file>` | Any text styling |

<!-- Add rows per token group, not per token. The token file itself carries the values. -->
