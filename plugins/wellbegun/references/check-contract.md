# Check contract

A check contract moves conventions a machine can judge into the project's own
linter and tests, behind one command. Fresh verification then spends its rounds
only on what machines cannot judge.

## Check command

One command runs every mechanized check: for example `npm run check`,
`make check` or `./scripts/check.sh`. It exits non-zero when any lint error,
type error or test failure occurs. Warnings do not fail it. Prefer the project's
existing aggregate command; otherwise plan a step that composes the existing
lint, typecheck and test commands. CI, when present, runs the same command.

## Classification

Classify only conventions in areas the current cycle touches.

| Class | Decidable by | Examples |
|---|---|---|
| `lint` | position and shape in the syntax tree | raw style values outside the token file; a module imported outside its owner; alias vs relative import rules |
| `test` | running code | access only through a repository; state transitions; data contracts |
| `review` | neither | bypass through an intermediate constant; convention interpretation; whole data-flow properties |

When a convention's wording does not fix its scope (for example "no raw values
in screen code" — does a non-screen component count?), the chosen
interpretation is a decision. Grade it with `reversibility-grades.md`.

Each class also decides where the knowledge lives, so it costs context only
when needed:

- `lint`: in the rule's message, delivered only when the rule fires.
- `review` needed in one area only: in that area's CLAUDE.md or AGENTS.md.
- Needed by almost every task: a one-line pointer in the root instructions,
  never the full list.

## Rule tests

Every `lint` entry has at least one should-flag case and one should-pass case,
linted at a real file path so the rule's file scope is tested too. The rule
tests run inside the check command. A rule without them can silently match
nothing.

Write each rule message as a correction: what to use instead and where it
lives, for example "Render UI text with AppText from @/ui/primitives." A
message that only says what is forbidden sends the agent searching.

Lint rules match syntax, not values: `const R = 6; borderRadius: R` passes a
literal-only rule. Deliberate bypass stays a `review` concern.

## Stack tools

| Role | React Native / Next.js | Flutter | Python |
|---|---|---|---|
| Lint | ESLint | `dart analyze` | ruff |
| Configuration-only bans | `no-restricted-imports`, `no-restricted-syntax` | `analysis_options.yaml` | ruff `banned-api` |
| Custom rules | ESLint plugin | `custom_lint` or an analyzer plugin | none in ruff; a separate AST check |
| Type check | `tsc --noEmit` | included in `dart analyze` | mypy / pyright |
| Tests | Jest / Vitest | `flutter test` | pytest |

Analyzer plugin mechanisms change between releases; check the tool's current
documentation before writing configuration.

## Worked example: ESLint

Configuration-only rules cover most conventions:

```js
// import ownership: only src/db/database.ts may import the driver
"no-restricted-imports": ["error", { paths: [
  { name: "expo-sqlite", message: "Only src/db/database.ts may import expo-sqlite." },
  { name: "react-native", importNames: ["Text"], message: "Use AppText." },
], patterns: [{ group: ["@/*"], message: "Inside src/, use relative imports." }] }]

// raw sizes in style objects (0 allowed)
"no-restricted-syntax": ["error", {
  selector: 'Property[key.name=/^(fontSize|gap|padding[A-Za-z]*|margin[A-Za-z]*|border[A-Za-z]*Radius)$/][value.type="Literal"][value.value!=0]',
  message: "Use theme tokens.",
}]
```

Two pitfalls:

- In flat config, when several objects match one file, a later object's rule
  options replace earlier ones; they do not merge. Build each scope's full
  option list from shared parts.
- Inside Jest, ESLint cannot dynamically import `eslint.config.js`. Rule tests
  pass the configuration directly:

```ts
const eslint = new ESLint({ cwd: root, overrideConfigFile: true, overrideConfig: require("../eslint.config.js") });
const [result] = await eslint.lintText(code, { filePath: path.join(root, "app/index.tsx") });
```

## Text-pattern hooks

The grep-based scripts in `hooks/` are a last resort for rules no language
linter can express. They cannot stop notation bypass. Record that limit beside
the entry; gaps in a text-pattern hook are never REJECT grounds.
