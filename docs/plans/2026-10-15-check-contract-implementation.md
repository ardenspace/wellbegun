# Check Contract Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let projects mechanize their conventions as lint rules and tests behind one check command, narrow fresh verification to what machines cannot judge, and cap covered steps at two verification rounds.

**Architecture:** Skills-plus-runtime plugin. The runtime (`plugins/wellbegun/scripts/artifacts.py`, stdlib Python) gains an optional per-contract `round_limit` (2 or 3) that fixes a scope's round limit at scope creation and its re-open allowance. The skills gain a check contract: wellspec defines it, wellplan sets `round_limit` from it, wellrun completes and verifies against it, wellnext promotes recurring findings into it. A new reference, `references/check-contract.md`, holds the classification guide and stack tool table.

**Tech Stack:** Python 3.9+ stdlib `unittest`, Markdown skills, POSIX shell (`scripts/validate.sh`).

**Spec:** `docs/2026-10-15-check-contract-design.md`. Executors MUST read it in full before any task. The spec is Korean; skill and reference text is English per repo convention.

## Global Constraints

- Skill bodies, references, and code comments are **English**. Design docs and release notes follow existing language (release notes English, like `docs/releases/0.6.0.md`).
- Every SKILL.md keeps frontmatter `name:` matching its directory and a `description:` starting with `Use when`.
- Skills and references must not mention `superpowers:brainstorming`, `superpowers:writing-plans`, `.talpi/`, `.loopspace/`, or `pslog` (`scripts/validate.sh` fails on these). Do not name the pilot project's management folder; say "the project's convention documents".
- `round_limit` accepts only the integers `2` or `3` (not `bool`, not strings). Absent means `3`.
- A scope's `limit` is fixed when the scope is created; a later `round_limit` change does not alter it. Raising a limit uses `op:approve-rounds`.
- Scope state gains `allowance` (2 or 3). State files without it read as `3`.
- Plans and state files from 0.6.0 behave exactly as before.
- Rule candidates live in `.wellbegun/rule-candidates.md` (never in schema 2 `run.md`, which is derived and must not be hand-edited).
- Version `0.7.0` in both `plugins/wellbegun/.claude-plugin/plugin.json` and `plugins/wellbegun/.codex-plugin/plugin.json`.
- Verification for every task: `bash scripts/validate.sh` from the repo root → exit 0, prints `OK: wellbegun structure valid`, all unit tests pass.
- Commit after every task; conventional-commit message ending with `Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>`. Do not add `docs/2026-09-03-dryforge-domain-lens-notes.md`.

## Review Focus

- A `round_limit` of `true` must be rejected even though Python's `bool` is an `int` subclass (test in Task 1).
- A replacement verifier on a two-round scope must stop at the cap instead of opening round 3 (test in Task 1).
- `approve-rounds` on a two-round scope must extend from 2, giving round 3 (test in Task 1).
- A tampered state file with `allowance: 5` must be rejected as `invalid_state` (test in Task 1).
- A legacy cycle with no check contract must keep the old Basic completion rule; the skill text must say so explicitly (wording in Task 5).

---

### Task 1: Runtime `round_limit` and scope `allowance`

**Files:**
- Modify: `plugins/wellbegun/scripts/artifacts.py` (plan validation near line 103–118; state scope validation near line 319–321; invalidation near line 703; init near line 771; replan near line 808)
- Modify: `plugins/wellbegun/tests/test_support.py` (`create_project`)
- Create: `plugins/wellbegun/tests/test_round_limit.py`
- Modify: `plugins/wellbegun/references/runtime-contract.md` (round paragraph near lines 193–206)

**Interfaces:**
- Consumes: existing `runtime.plan`, `runtime.transition`, test helpers `start`, `checking`, `record_success`, `read_all`, `tx`, `state`, `write_plan`.
- Produces: contract field `round_limit: 2|3` (optional); scope state `{'round': int, 'limit': int, 'allowance': 2|3}`; helper `new_scope(contract) -> dict` in `artifacts.py`; `create_project(directory, basic_only=False, round_limits=None)` where `round_limits` maps record ID → limit.

- [ ] **Step 1: Extend the test helper**

In `plugins/wellbegun/tests/test_support.py`, replace `create_project` with:

```python
def create_project(directory, basic_only=False, round_limits=None):
    root = Path(directory).resolve() / '.wellbegun'
    root.mkdir(parents=True)
    for file in (PLUGIN / 'tests/fixtures').iterdir():
        shutil.copyfile(file, root / file.name)
    (root.parent / 'src.py').write_text('value = 1\n')
    (root.parent / 'check.py').write_text('assert True\n')
    if basic_only:
        records, _ = runtime.plan(root)
        write_plan(root, [records['producer']])
    if round_limits:
        records, _ = runtime.plan(root)
        for key, limit in round_limits.items():
            records[key]['round_limit'] = limit
        write_plan(root, list(records.values()))
    runtime.transition(root, 0, json.loads((root / 'init.json').read_text()))
    return root
```

- [ ] **Step 2: Write the failing tests**

Create `plugins/wellbegun/tests/test_round_limit.py`:

```python
import json
import tempfile
import unittest

from test_support import checking, create_project, read_all, record_success, runtime, start, state, tx, write_plan


def fail(root, record='producer', fid='F1', cid='worker'):
    return tx(root, {'op': 'set', 'record': record, 'status': 'fixing', 'context_id': cid, 'findings': [{'id': fid, 'clause': 'works', 'reproduction': 'python3 check.py reproduces contract failure'}]})


class RoundLimitTests(unittest.TestCase):
    def project(self, **limits):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        return create_project(temp.name, round_limits=limits or None)

    def raises(self, code, func, *args, **kwargs):
        with self.assertRaises(runtime.Error) as caught:
            func(*args, **kwargs)
        self.assertEqual(code, caught.exception.code)

    def test_two_round_limit_stops_after_second_reject(self):
        root = self.project(producer=2)
        self.assertEqual({'round': 0, 'limit': 2, 'allowance': 2}, state(root)['scopes']['scope-producer'])
        start(root)
        checking(root); fail(root)
        self.assertEqual('fixing', state(root)['records']['producer']['status'])
        checking(root); fail(root)
        rec = state(root)['records']['producer']
        self.assertEqual(('stopped', 'round_cap', 2), (rec['status'], rec['stop_reason'], rec['round']))
        self.raises('invalid_transition', record_success, root)

    def test_missing_round_limit_keeps_three(self):
        root = self.project()
        self.assertEqual({'round': 0, 'limit': 3, 'allowance': 3}, state(root)['scopes']['scope-producer'])
        start(root)
        for _ in range(2):
            checking(root); fail(root)
        self.assertEqual('fixing', state(root)['records']['producer']['status'])
        checking(root); fail(root)
        self.assertEqual(('stopped', 'round_cap'), (state(root)['records']['producer']['status'], state(root)['records']['producer']['stop_reason']))

    def test_invalid_round_limit_rejected(self):
        root = self.project()
        records, _ = runtime.plan(root)
        for bad in [1, 4, '2', True, None, 2.0]:
            records['producer']['round_limit'] = bad
            write_plan(root, list(records.values()))
            self.raises('invalid_plan', runtime.plan, root)

    def test_replan_does_not_change_existing_scope_limit(self):
        root = self.project()
        records, _ = runtime.plan(root)
        records['producer']['round_limit'] = 2
        write_plan(root, list(records.values()))
        tx(root, {'op': 'reconcile', 'reason': 'tighten round limit'})
        self.assertEqual({'round': 0, 'limit': 3, 'allowance': 3}, state(root)['scopes']['scope-producer'])

    def test_new_scope_from_replan_uses_round_limit(self):
        root = self.project()
        records, _ = runtime.plan(root)
        extra = dict(records['producer'], id='extra', scope_id='scope-extra', round_limit=2)
        write_plan(root, list(records.values()) + [extra])
        tx(root, {'op': 'reconcile', 'reason': 'add extra step', 'approved_new_scopes': ['scope-extra'], 'approval': 'User approved the extra step'})
        self.assertEqual({'round': 0, 'limit': 2, 'allowance': 2}, state(root)['scopes']['scope-extra'])

    def test_reopened_scope_extends_by_its_allowance(self):
        root = self.project(producer=2)
        start(root); checking(root); record_success(root)
        (root.parent / 'src.py').write_text('value = 2\n')
        tx(root, {'op': 'reconcile', 'reason': 'new intentional foundation revision'})
        self.assertEqual(3, state(root)['scopes']['scope-producer']['limit'])

    def test_state_without_allowance_reads_as_three(self):
        root = self.project()
        start(root); checking(root); record_success(root)
        data = state(root)
        del data['scopes']['scope-producer']['allowance']
        (root / 'state.json').write_text(json.dumps(data))
        (root.parent / 'src.py').write_text('value = 2\n')
        tx(root, {'op': 'reconcile', 'reason': 'new intentional foundation revision'})
        self.assertEqual(4, state(root)['scopes']['scope-producer']['limit'])

    def test_invalid_allowance_in_state_rejected(self):
        root = self.project()
        data = state(root)
        data['scopes']['scope-producer']['allowance'] = 5
        (root / 'state.json').write_text(json.dumps(data))
        self.raises('invalid_state', runtime.context, root)

    def test_approve_rounds_extends_two_round_scope(self):
        root = self.project(producer=2)
        start(root)
        for _ in range(2):
            checking(root); fail(root)
        tx(root, {'op': 'approve-rounds', 'scope_id': 'scope-producer', 'additional': 1, 'approval': 'User approved one additional round'})
        read_all(root)
        tx(root, {'op': 'set', 'record': 'producer', 'status': 'fixing'})
        checking(root)
        self.assertEqual(3, state(root)['records']['producer']['round'])
        self.assertEqual('checking', state(root)['records']['producer']['status'])

    def test_replacement_verifier_stops_at_two_round_cap(self):
        root = self.project(producer=2)
        records, _ = runtime.plan(root)
        records['producer']['grade'] = 'fresh'
        write_plan(root, list(records.values()))
        tx(root, {'op': 'reconcile', 'reason': 'fresh boundary'})
        self.assertEqual(2, state(root)['scopes']['scope-producer']['limit'])
        start(root)
        read_all(root, context_id='v1', audience='verifier')
        tx(root, {'op': 'set', 'record': 'producer', 'status': 'checking', 'verifier_context_id': 'v1'})
        for num in range(2, 4):
            tx(root, {'op': 'set', 'record': 'producer', 'status': 'stopped', 'reason': 'verifier context lost'})
            cid = 'v' + str(num)
            read_all(root, context_id=cid, audience='verifier')
            tx(root, {'op': 'set', 'record': 'producer', 'status': 'checking', 'context_id': cid, 'verifier_context_id': cid})
        rec = state(root)['records']['producer']
        self.assertEqual(('stopped', 2, 'round_cap'), (rec['status'], rec['round'], rec['stop_reason']))


if __name__ == '__main__':
    unittest.main()
```

`test_replacement_verifier_stops_at_two_round_cap` mirrors `test_g1_001_verifier_replacement_cannot_bypass_round_cap` in `tests/test_state.py` (line ~374), with the cap at 2 instead of 3. It also exercises a replan of an existing scope (grade change) keeping `limit` at 2.

- [ ] **Step 3: Run the tests to verify they fail**

Run: `cd plugins/wellbegun && python3 -m unittest tests/test_round_limit.py -v 2>&1 | tail -20` (run from `tests/` if imports fail: `cd plugins/wellbegun/tests && python3 -m unittest test_round_limit -v`)
Expected: failures on the `allowance` key assertions, `invalid_plan` not raised, and two-round cap not stopping.

- [ ] **Step 4: Implement plan validation**

In `artifacts.py`, inside the per-contract loop of `plan()`, after the line checking `kind`/`grade`, add:

```python
        if 'round_limit' in rec:
            need(type(rec['round_limit']) is int and rec['round_limit'] in {2, 3}, 'invalid_plan', f'{key}: round_limit must be 2 or 3')
```

- [ ] **Step 5: Implement scope creation**

Add near `new_record`:

```python
def new_scope(contract):
    allowance = contract.get('round_limit', 3)
    return {'round': 0, 'limit': allowance, 'allowance': allowance}
```

In `init` (line ~771) replace `'scopes': {r['scope_id']: {'round': 0, 'limit': 3} for r in records.values()}` with `'scopes': {r['scope_id']: new_scope(r) for r in records.values()}`.

In replan (line ~808) replace `state['scopes'].setdefault(contract['scope_id'], {'round': 0, 'limit': 3})` with `state['scopes'].setdefault(contract['scope_id'], new_scope(contract))`.

- [ ] **Step 6: Implement re-open allowance and state validation**

In `invalidate` (line ~703) replace `scope['limit'] = max(scope['limit'], scope['round'] + 3)` with:

```python
            scope['limit'] = max(scope['limit'], scope['round'] + scope.get('allowance', 3))
```

In `validate_state` scope loop (line ~319) add after the existing `need`:

```python
        need(scope.get('allowance', 3) in {2, 3} and type(scope.get('allowance', 3)) is int, 'invalid_state', 'Invalid scope allowance')
```

- [ ] **Step 7: Run the new and existing tests**

Run: `bash scripts/validate.sh` (repo root)
Expected: `OK: wellbegun structure valid`, all tests pass (88 existing + 10 new). If an existing test compares a whole scope dict to `{'round': 0, 'limit': 3}`, update that expectation to include `'allowance': 3` and note it in the commit body.

- [ ] **Step 8: Document the runtime contract**

In `references/runtime-contract.md`, replace "At round 3 failure stays stopped/unresolved." with "At the scope's limit (default 3) failure stays stopped/unresolved." and replace "its limit is extended to allow three rounds" with "its limit is extended by the scope's `allowance` (default 3)". Then append after that paragraph:

```markdown
A contract may set `round_limit` to `2` or `3` (default `3`). The value fixes
the scope's `limit` and `allowance` when the scope is created, at init or at an
approved new scope in replan. Changing `round_limit` on an existing scope never
alters its limit; use `op:approve-rounds` to add rounds. State files without
`allowance` read it as `3`.
```

- [ ] **Step 9: Commit**

```bash
git add plugins/wellbegun/scripts/artifacts.py plugins/wellbegun/tests/test_support.py plugins/wellbegun/tests/test_round_limit.py plugins/wellbegun/references/runtime-contract.md
git commit -m "feat(runtime): per-contract round_limit with fixed scope allowance" -m "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: Check contract reference and hooks demotion

**Files:**
- Create: `plugins/wellbegun/references/check-contract.md`
- Modify: `plugins/wellbegun/references/hooks/README.md` (first paragraph)

**Interfaces:**
- Produces: reference path `<plugin-root>/references/check-contract.md` with sections `## Check command`, `## Classification`, `## Rule tests`, `## Stack tools`, `## Worked example: ESLint`, `## Text-pattern hooks`. Tasks 3–6 link to it by path.

- [ ] **Step 1: Write the reference**

Create `plugins/wellbegun/references/check-contract.md`:

````markdown
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

## Rule tests

Every `lint` entry has at least one should-flag case and one should-pass case,
linted at a real file path so the rule's file scope is tested too. The rule
tests run inside the check command. A rule without them can silently match
nothing.

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
````

- [ ] **Step 2: Demote grep hooks in the hooks README**

In `plugins/wellbegun/references/hooks/README.md`, replace the first paragraph (starting "wellbegun ships optional") with:

```markdown
wellbegun ships optional **generic, grep-based reference scripts**. They are a last resort: prefer the project's language linter, type checker and tests behind one check command (see `<plugin-root>/references/check-contract.md`). Text patterns cannot stop notation bypass, so their gaps are never REJECT grounds. Adapt a reference only for active areas and concrete enforcement needs that no linter can express, choosing relevant globs and paths. These scripts do not prove semantic registry compliance; no hook installation or foundation phase is required for unrelated work.
```

- [ ] **Step 3: Validate**

Run: `bash scripts/validate.sh`
Expected: `OK: wellbegun structure valid`, tests pass.

- [ ] **Step 4: Commit**

```bash
git add plugins/wellbegun/references/check-contract.md plugins/wellbegun/references/hooks/README.md
git commit -m "docs(references): add check contract guide, demote grep hooks to last resort" -m "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: wellspec Step 4 becomes the check contract

**Files:**
- Modify: `plugins/wellbegun/skills/wellspec/SKILL.md` (`## Step 4: Enforcement plan` section and the `## Enforcement plan` block in the output template)

**Interfaces:**
- Consumes: `references/check-contract.md` (Task 2).
- Produces: spec section `## Check contract` with lines `command:`, `lint:`, `test:`, `review:`, `CI:`. Tasks 4–6 refer to "the spec's check contract" and "the check command".

- [ ] **Step 1: Replace the Step 4 section**

Replace the whole `## Step 4: Enforcement plan` section (heading and paragraph) with:

```markdown
## Step 4: Check contract

Read `<plugin-root>/references/check-contract.md` (reuse it if already read in this context).

1. **One check command.** Find the project's existing aggregate command. If none exists, plan a step that composes the existing lint, typecheck and test commands; do not create it now. It exits non-zero on failure; warnings do not fail it.
2. **Classify affected conventions.** For conventions in areas this cycle touches — begin/spec decisions, active registry entries, and convention documents the project already keeps — assign `lint`, `test` or `review`. Leave untouched areas unclassified.
3. **Rule tests.** Each `lint` entry needs at least one should-flag and one should-pass case at real file paths, run by the check command. Plan their creation with the rule.
4. **Interpretations are decisions.** When a convention's wording does not fix its scope, grade the chosen interpretation with `<plugin-root>/references/reversibility-grades.md`. Record it briefly; ask the user only when it spreads across areas.
5. **Text-pattern hooks are a last resort.** Use `<plugin-root>/references/hooks/` scripts only where no language linter can express the rule, and record beside the entry that it cannot stop notation bypass and its gaps are not REJECT grounds.
6. **CI is optional.** Record a workflow path when the project has a remote and CI authority, otherwise `local only`. Running the check command locally satisfies completion either way.

Delta mode: write only changed entries. `.wellbegun/audit.md` `## Rule promotions` is an additional input; plan each accepted promotion as a rule plus its rule tests.
```

- [ ] **Step 2: Replace the template block**

In the output template, replace:

```markdown
## Enforcement plan
- <check> wired as <host editing-time hook / pre-commit / both>, adapted how
```

with:

```markdown
## Check contract
- command: `<one command>` (<lint | typecheck | test, as included>)
- lint: <convention> → <rule>, scope <globs>
- test: <convention> → <test location>
- review: <convention> — <why it cannot be mechanized>
- CI: <workflow path> | local only
```

- [ ] **Step 3: Validate**

Run: `bash scripts/validate.sh` and `grep -n "Enforcement plan" plugins/wellbegun/skills/*/SKILL.md`
Expected: validate passes; grep prints nothing.

- [ ] **Step 4: Commit**

```bash
git add plugins/wellbegun/skills/wellspec/SKILL.md
git commit -m "feat(wellspec): replace enforcement plan with check contract" -m "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 4: wellplan sets `round_limit`

**Files:**
- Modify: `plugins/wellbegun/skills/wellplan/SKILL.md` (`## Step sizing and contract`, after the paragraph starting "Derive `grade`")

**Interfaces:**
- Consumes: runtime `round_limit` (Task 1); spec `## Check contract` (Task 3).

- [ ] **Step 1: Add the paragraph**

After the paragraph starting "Derive `grade` from the reversal cost", insert:

```markdown
Set `round_limit` per contract from the spec's check contract. Use `2` when the completion clauses are covered by `lint`/`test` entries run by the check command, so fresh verification only judges interpretation and `review` entries. Omit it (default `3`) otherwise, including steps that build the check contract's own rules and rule tests, and every contract in a cycle without a check contract. Note the reason in one line beside the contract. The runtime accepts only `2` or `3` and fixes a scope's limit when the scope is created; raising it later needs `op:approve-rounds`.
```

- [ ] **Step 2: Validate**

Run: `bash scripts/validate.sh`
Expected: pass.

- [ ] **Step 3: Commit**

```bash
git add plugins/wellbegun/skills/wellplan/SKILL.md
git commit -m "feat(wellplan): set round_limit from check contract coverage" -m "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 5: wellrun completes and verifies against the check contract

**Files:**
- Modify: `plugins/wellbegun/skills/wellrun/SKILL.md` (`## Verification and completion` bullets; `### Rounds and unresolved findings` first sentences)

**Interfaces:**
- Consumes: spec check contract (Task 3), `round_limit` (Tasks 1, 4), `references/check-contract.md` (Task 2).
- Produces: file `.wellbegun/rule-candidates.md`, one line per candidate: `- <finding ID>: <defect kind> — lint | test via <means>`. Task 6 reads it.

- [ ] **Step 1: Replace the Basic bullet**

Replace the bullet starting `- **Basic:**` with:

```markdown
- **Basic:** complete after the spec's check command and the step's contract checks pass. Warnings do not block. A legacy cycle or a spec without a check contract keeps the previous rule: contract checks plus affected lint/analyze or other relevant checks. No separate verifier or verifier ACCEPT is required.
```

- [ ] **Step 2: Extend the Fresh bullet**

Append to the end of the bullet starting `- **Fresh:**`:

```markdown
 Include the check contract and the latest check-command result (command, exit status, input identity). The verifier does not re-examine conventions classified `lint` or `test`; it focuses on contract interpretation and gaps, `review` entries, completion clauses without tests, and new L/XL choices.
```

- [ ] **Step 3: Extend the REJECT bullet and add rule candidates**

Append to the end of the bullet starting `- REJECT must identify`:

```markdown
 A rule gap is REJECT grounds only when the verifier reproduces an actual violation present in the current code; the fixer then fixes the code. A theoretical bypass is an outside-contract finding. Gaps in text-pattern hooks are never REJECT grounds.
```

Insert a new bullet right after it:

```markdown
- **Rule candidates.** When a finding's defect kind could be mechanized as lint or test, fix the code and add one line to `.wellbegun/rule-candidates.md`: `- <finding ID>: <defect kind> — lint | test via <means>`. Do not build new rules during the cycle; wellnext promotes candidates into the next cycle's check contract. This file is not derived state; schema 2 `run.md` stays helper-written.
```

- [ ] **Step 4: Make the round section limit-aware**

In `### Rounds and unresolved findings`, replace "Each verification scope gets at most three rounds including the first." with "Each verification scope gets at most its contract's `round_limit` rounds including the first (default three)." and replace "After round 3 fails," with "After the last allowed round fails,".

- [ ] **Step 5: Validate**

Run: `bash scripts/validate.sh` and `grep -n "round 3" plugins/wellbegun/skills/wellrun/SKILL.md`
Expected: validate passes; grep prints nothing.

- [ ] **Step 6: Commit**

```bash
git add plugins/wellbegun/skills/wellrun/SKILL.md
git commit -m "feat(wellrun): complete on check command, narrow fresh scope, record rule candidates" -m "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 6: wellnext promotes rule candidates

**Files:**
- Modify: `plugins/wellbegun/skills/wellnext/SKILL.md` (no-pipeline paragraph; `## Step 2: Relevant-area audit`; Step 3 archive item 1; `## audit.md template`)

**Interfaces:**
- Consumes: `.wellbegun/rule-candidates.md` (Task 5); spec check command (Task 3).
- Produces: `audit.md` sections `## Check command` and `## Rule promotions (input to wellspec delta step 4)`, read by wellspec delta mode (Task 3).

- [ ] **Step 1: No-pipeline uses the check command**

Replace "For **no pipeline**, perform the authorized small change and affected checks immediately;" with "For **no pipeline**, perform the authorized small change and run the spec's check command (or affected checks when no check contract exists) immediately;".

- [ ] **Step 2: Audit reads rule candidates**

Append to `## Step 2: Relevant-area audit`:

```markdown
Read `.wellbegun/rule-candidates.md` when present. Promote a defect kind that appears twice or more, or once with an obvious lint/test means, into `## Rule promotions`; leave the rest out. Promotions are input to wellspec delta step 4, not rules built here.
```

- [ ] **Step 3: Archive the candidates file**

In Step 3 item 1, replace "move begin/spec and the previous cycle's audit, if present, into that same returned destination" with "move begin/spec, `rule-candidates.md` and the previous cycle's audit, if present, into that same returned destination". In the legacy sentence, replace "preserving its original begin/spec/plan/run/audit format" with "preserving its original begin/spec/plan/run/audit format and moving `rule-candidates.md` with them".

- [ ] **Step 4: Update the audit template**

In the `audit.md` template, replace:

```markdown
## Enforcement status
- <hook/linter>: pass | FAIL — <what broke>
```

with:

```markdown
## Check command
- `<command>`: pass | FAIL — <what broke>

## Rule promotions (input to wellspec delta step 4)
- **<defect kind>** — seen as <finding IDs>; lint | test via <means>
```

- [ ] **Step 5: Validate**

Run: `bash scripts/validate.sh` and `grep -n "Enforcement status" plugins/wellbegun/skills/wellnext/SKILL.md`
Expected: validate passes; grep prints nothing.

- [ ] **Step 6: Commit**

```bash
git add plugins/wellbegun/skills/wellnext/SKILL.md
git commit -m "feat(wellnext): promote recurring rule candidates into the next check contract" -m "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 7: Release 0.7.0

**Files:**
- Modify: `plugins/wellbegun/.claude-plugin/plugin.json` (`"version"`), `plugins/wellbegun/.codex-plugin/plugin.json` (`"version"`)
- Create: `docs/releases/0.7.0.md`
- Modify: `README.md:57`

- [ ] **Step 1: Bump versions**

Set `"version": "0.7.0"` in both plugin manifests.

- [ ] **Step 2: Write release notes**

Create `docs/releases/0.7.0.md`:

```markdown
# wellbegun 0.7.0 — Check contract

Projects can now move conventions a machine can judge into their own linter and
tests behind one check command. wellspec defines the check contract, wellplan
caps steps it covers at two verification rounds, wellrun completes on the check
command and narrows fresh verification to what machines cannot judge, and
wellnext promotes recurring findings into the next cycle's contract.

- New reference `references/check-contract.md`: lint / test / review
  classification, rule tests, stack tool table, an ESLint worked example.
- Contracts accept an optional `round_limit` of 2 or 3 (default 3). A scope's
  limit is fixed at creation; extra rounds still need explicit approval.
- Rule gaps reject only with a reproduced violation in current code; gaps in
  grep-based hooks never reject. Grep hooks are now a last resort.
- Rule candidates are recorded in `.wellbegun/rule-candidates.md` and archived
  with the cycle.

Evidence: a pilot on an Expo / React Native project moved six prose conventions
into ESLint configuration (147 lines) with 30 rule tests; the rules found 3 real
violations and no false positives, and the rule tests caught one scope mistake
in the rules themselves. The pilot did not measure verification rounds; the
two-round cap is a policy value to be checked in the next dogfooding cycle.

Existing plans and state files behave as before.
```

- [ ] **Step 3: Update README**

Replace `Current release: **0.6.0** — [release notes](docs/releases/0.6.0.md).` with `Current release: **0.7.0** — [release notes](docs/releases/0.7.0.md).`

- [ ] **Step 4: Validate**

Run: `bash scripts/validate.sh` and `grep -rn '"version"' plugins/wellbegun/.claude-plugin plugins/wellbegun/.codex-plugin`
Expected: validate passes; both show `0.7.0`.

- [ ] **Step 5: Commit**

```bash
git add plugins/wellbegun/.claude-plugin/plugin.json plugins/wellbegun/.codex-plugin/plugin.json docs/releases/0.7.0.md README.md
git commit -m "chore: release wellbegun 0.7.0 with check contract" -m "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```
