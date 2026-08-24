# wellbegun Plugin Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the wellbegun Claude Code plugin — four pipeline skills (wellbegin → wellspec → wellplan → wellrun) plus shared references and example enforcement hooks — ready for local installation and dogfooding.

**Architecture:** A skills-only Claude Code plugin. Each lens from the design doc becomes one skill under `skills/<name>/SKILL.md`. Cross-skill knowledge (reversibility grades, probe angles, registry templates, hook examples) lives in top-level `references/`. Target projects get a `.wellbegun/` state directory whose files carry `status:` frontmatter; the existence and status of those files is how each skill knows where the pipeline stands.

**Tech Stack:** Markdown skills, JSON plugin manifests, POSIX shell for validation and hook examples. No build step, no runtime dependencies.

**Spec:** `docs/2026-08-24-wellbegun-design-notes.md` — every content requirement below cites it. Executors MUST read it in full before implementing any skill task.

## Global Constraints

- Plugin name: `wellbegun`. Skill names and directories: `wellbegin`, `wellspec`, `wellplan`, `wellrun` (confirmed by Arden 2026-08-24; supersedes the `begin/spec/plan/run` sketch in the design doc).
- wellbegun is fully independent: never read state from, write to, or reference talpi/loopspace/pslog. Their repos were used once as format references only.
- Skill bodies and references are written in **English** (public-distribution convention; the design doc stays Korean).
- State directory in target projects: `.wellbegun/` with exactly these artifacts: `begin.md`, `spec.md`, `plan.md`, `decisions.md`, `pending/<slug>.md`. These names are a cross-skill interface — do not improvise variants.
- Every `.wellbegun/` pipeline artifact starts with YAML frontmatter whose first key is `status: draft` or `status: approved`. Each skill gates on its predecessor being `approved`.
- Every SKILL.md frontmatter has `name:` matching its directory and a `description:` that starts with "Use when".
- Runtime skill bodies must never instruct calling superpowers:brainstorming or superpowers:writing-plans (design doc: pipeline stages must not double-run). Delegating implementation techniques (TDD, debugging, verification) to Superpowers when present is encouraged.
- Commit after every task with a conventional-commit message ending in the Claude Code trailer.
- Verification command for all tasks: `bash scripts/validate.sh` (built in Task 1).

---

### Task 1: Plugin manifests, license, validation script

**Files:**
- Create: `.claude-plugin/plugin.json`
- Create: `.claude-plugin/marketplace.json`
- Create: `LICENSE`
- Create: `scripts/validate.sh`
- Modify: `README.md` (license line only)

**Interfaces:**
- Produces: `scripts/validate.sh` — exit 0 when structure is valid; every later task runs it as its test.

- [ ] **Step 1: Write the validation script (the failing test for the whole structure)**

```bash
#!/usr/bin/env bash
# Structural validation for the wellbegun plugin. Exit non-zero on any violation.
set -u
cd "$(dirname "$0")/.."
fail=0
err() { echo "FAIL: $1"; fail=1; }

# 1. Manifests parse as JSON and agree on the plugin name.
for f in .claude-plugin/plugin.json .claude-plugin/marketplace.json; do
  [ -f "$f" ] || { err "$f missing"; continue; }
  python3 -m json.tool "$f" >/dev/null 2>&1 || err "$f is not valid JSON"
done
name=$(python3 -c 'import json;print(json.load(open(".claude-plugin/plugin.json"))["name"])' 2>/dev/null)
[ "$name" = "wellbegun" ] || err "plugin.json name is '$name', expected 'wellbegun'"

# 2. Each skill dir has SKILL.md with matching name and a "Use when" description.
for d in skills/*/; do
  [ -d "$d" ] || continue
  s="$d/SKILL.md"; dirname=$(basename "$d")
  [ -f "$s" ] || { err "$s missing"; continue; }
  head -1 "$s" | grep -q '^---$' || err "$s missing frontmatter"
  grep -q "^name: $dirname$" "$s" || err "$s name does not match directory '$dirname'"
  grep -q '^description: "\?Use when' "$s" || err "$s description must start with 'Use when'"
done

# 3. Skills must not invoke forbidden Superpowers stages or reference sibling plugins.
# (no pipe into while — a piped while runs in a subshell and would drop fail=1)
for f in $(grep -rlE 'superpowers:(brainstorming|writing-plans)' skills/ 2>/dev/null); do err "$f invokes a forbidden Superpowers planning skill"; done
for f in $(grep -rlE '\.talpi/|\.loopspace/|pslog' skills/ references/ 2>/dev/null); do err "$f references a sibling plugin"; done

[ $fail -eq 0 ] && echo "OK: wellbegun structure valid"
exit $fail
```

- [ ] **Step 2: Run it to confirm it fails (no manifests yet)**

Run: `bash scripts/validate.sh`
Expected: FAIL lines for both missing manifests, exit code 1.

- [ ] **Step 3: Write the manifests and license**

`.claude-plugin/plugin.json`:
```json
{
  "name": "wellbegun",
  "description": "MVP pipeline that spends attention only on hard-to-reverse decisions: begin (user lens), spec (reversal-cost grades + global registries), plan (foundation-first contracts), run (fresh-eyes verification scaled by reversal cost).",
  "version": "0.1.0",
  "author": {
    "name": "ardenspace",
    "email": "ardensdevspace@gmail.com"
  },
  "homepage": "https://github.com/ardenspace/wellbegun",
  "repository": "https://github.com/ardenspace/wellbegun",
  "license": "MIT",
  "keywords": ["mvp", "reversibility", "one-way-door", "planning", "pipeline", "registry", "verification"]
}
```

`.claude-plugin/marketplace.json`:
```json
{
  "name": "wellbegun",
  "owner": {
    "name": "ardenspace",
    "email": "ardensdevspace@gmail.com"
  },
  "plugins": [
    {
      "name": "wellbegun",
      "source": "./",
      "description": "MVP pipeline that spends attention only on hard-to-reverse decisions."
    }
  ]
}
```

`LICENSE`: standard MIT text, copyright `2026 ardenspace`. In `README.md` replace `TBD` under License with `MIT`.

- [ ] **Step 4: Run validation to verify it passes**

Run: `bash scripts/validate.sh`
Expected: `OK: wellbegun structure valid`, exit 0 (skills loop is vacuous for now).

- [ ] **Step 5: Commit**

```bash
git add .claude-plugin LICENSE scripts/validate.sh README.md
git commit -m "feat: plugin manifests, MIT license, structural validation script"
```

---

### Task 2: references/reversibility-grades.md

**Files:**
- Create: `references/reversibility-grades.md`

**Interfaces:**
- Produces: the S/M/L/XL grading rubric cited by wellspec (grading queued decisions), wellplan (verification tiers), wellrun (hidden-decision escalation).

- [ ] **Step 1: Write the rubric**

Required content (design doc §스펙 렌즈 1, §런 렌즈 규칙 4):
- Grading question: "If this decision turns out wrong, what does it cost to change?" Grade by **reversal cost, not importance**.
- A table with four rows. Exact semantics to encode:
  - **S** — reversed in minutes inside one file; nobody else notices. Examples: variable naming, internal helper structure, copy text. Handling: implementer decides silently.
  - **M** — reversed in under a day; touches a few files, no data or API migration. Examples: component internal state shape, non-shared endpoint response field. Handling: decide, record one line in `.wellbegun/decisions.md`, keep moving.
  - **L** — reversal is a mini-project: data backfill, cross-cutting rename, coordinated changes across layers. Examples: DB schema for a core entity, shared component API, error-format contract. Handling: mandatory alternative comparison in spec; fresh-eyes verification in run; stops the run if discovered mid-implementation (companion mode).
  - **XL** — reversal is a rewrite or a user-visible break. Examples: account model, multi-tenancy, pricing unit, platform choice, data ownership. Handling: same as L, plus these belong in wellbegin (product identity) whenever they are product-shaped.
- A "grade fast" note: grading a decision should take under a minute; when torn between two grades, take the higher one.
- Mini-ADR line format used everywhere a decision is recorded:
  `- [YYYY-MM-DD] [grade] <decision> — <why, one clause>; rejected: <alternative, if L/XL>`

- [ ] **Step 2: Verify and commit**

Run: `bash scripts/validate.sh` — Expected: OK.

```bash
git add references/reversibility-grades.md
git commit -m "feat: reversibility grade rubric (S/M/L/XL) with mini-ADR format"
```

---

### Task 3: references/probe-angles.md

**Files:**
- Create: `references/probe-angles.md`

**Interfaces:**
- Produces: the blind-spot probe catalog wellbegin cites before closing each question bundle.

- [ ] **Step 1: Write the catalog**

Required content (design doc §기획 렌즈): the five confirmed angles, each with a one-line prompt the agent can ask verbatim, plus which question bundles (1–7) it applies to:
1. **Empty first screen** — what does the very first user see before any data exists? (bundles 2, 6)
2. **Day one without data** — is the core journey still meaningful with zero history? (bundles 2, 3)
3. **Leave and return** — a user disappears for two weeks and comes back; what state greets them? (bundles 2, 3)
4. **Unintended use** — what is the most likely off-label use, and does it break anything expensive? (bundles 1, 5)
5. **The receiving end of sharing** — if anything is shared/exported, what does the recipient (no account, no context) experience? (bundles 2, 5)

Also encode the usage rule: probes are fired **before closing a bundle**, only for angles not yet covered; probe depth is adaptive — dig only where answers look thin (design doc: 탐침 강도는 가변).

- [ ] **Step 2: Verify and commit**

Run: `bash scripts/validate.sh` — Expected: OK.

```bash
git add references/probe-angles.md
git commit -m "feat: blind-spot probe angle catalog for the begin lens"
```

---

### Task 4: references/registry-templates/

**Files:**
- Create: `references/registry-templates/README.md`
- Create: `references/registry-templates/design-tokens.md`
- Create: `references/registry-templates/frontend-components.md`
- Create: `references/registry-templates/backend-common.md`
- Create: `references/registry-templates/db-schema.md`

**Interfaces:**
- Produces: per-area thin-index templates. wellspec instantiates them as markdown rosters; wellplan's phase 1 turns them into code; wellrun's rule 2/3 reads and updates them.

- [ ] **Step 1: Write README.md with the three principles**

Verbatim principles to encode (design doc §전역 관리 구조): (1) thin index — name, one-line purpose, real file location, when to use; never copy content ("a map, not a document"); (2) code is the source of truth — e.g. the token file itself is the registry, markdown only points; (3) sync is machine-verified — a new file in a common folder that is absent from the roster is a lint failure. Placement rule: each registry file lives in its own area of the target repo (e.g. next to the code it indexes), and area CLAUDE.md or hooks force reading it before working in that area.

- [ ] **Step 2: Write the four templates**

Each template is a table skeleton `| name | purpose (one line) | location | use when |` plus an area-specific header note:
- `design-tokens.md`: points at the token source file; rule "no raw hex/px/font literals outside the token file".
- `frontend-components.md`: shared component roster; rule "if it renders in two places, it lives here first".
- `backend-common.md`: error format, auth middleware, logging, pagination helpers; rule "every endpoint goes through the common layers".
- `db-schema.md`: entities, migration location, ownership notes; rule "schema changes always ride a migration, never a hand edit".

- [ ] **Step 3: Verify and commit**

Run: `bash scripts/validate.sh` — Expected: OK.

```bash
git add references/registry-templates
git commit -m "feat: thin-index registry templates for four areas"
```

---

### Task 5: references/hooks/ — enforcement examples

**Files:**
- Create: `references/hooks/README.md`
- Create: `references/hooks/check-hardcoded-values.sh`
- Create: `references/hooks/check-registry-sync.sh`

**Interfaces:**
- Produces: adaptable enforcement scripts. wellspec's step 4 plans their installation; wellplan puts the installation step in phase 1; wellrun's rule 1 confirms it happened.

- [ ] **Step 1: Write README.md**

Must state the resolution of the design doc's open question (훅·린트 세부): wellbegun ships **generic, grep-based reference scripts**, and the wellrun conductor adapts them to the project's stack during phase 1 (choosing file globs, wiring them as a Claude Code PostToolUse hook and/or a git pre-commit hook — both wirings shown with a concrete JSON/shell snippet). The plugin documents but does not force any notification channel (design doc: 푸시 알림은 하네스의 Notification 훅에 연결 가능하게 문서화).

- [ ] **Step 2: Write check-hardcoded-values.sh**

```bash
#!/usr/bin/env bash
# Flag raw design values outside the token source. Adapt GLOBS and TOKEN_FILE per project (phase 1).
set -u
TOKEN_FILE="${TOKEN_FILE:-src/styles/tokens.css}"
GLOBS=("src/**/*.tsx" "src/**/*.css")
hits=$(grep -rnE '#[0-9a-fA-F]{3,8}\b|(^|[^a-zA-Z-])[0-9]+(px|rem)\b' "${GLOBS[@]}" 2>/dev/null | grep -v "$TOKEN_FILE")
if [ -n "$hits" ]; then
  echo "Hardcoded design values found (use tokens from $TOKEN_FILE):"
  echo "$hits"
  exit 1
fi
```

- [ ] **Step 3: Write check-registry-sync.sh**

```bash
#!/usr/bin/env bash
# Fail when a file exists in a common folder but is absent from its registry roster. Adapt pairs per project.
set -u
# pairs: "<common-dir>:<registry-md>"
PAIRS=("src/components/shared:src/components/shared/REGISTRY.md")
fail=0
for pair in "${PAIRS[@]}"; do
  dir="${pair%%:*}"; reg="${pair##*:}"
  [ -d "$dir" ] || continue
  for f in "$dir"/*; do
    base=$(basename "$f")
    [ "$base" = "$(basename "$reg")" ] && continue
    grep -q "$base" "$reg" 2>/dev/null || { echo "FAIL: $base is in $dir but not listed in $reg"; fail=1; }
  done
done
exit $fail
```

- [ ] **Step 4: Verify and commit**

Run: `bash -n references/hooks/*.sh && bash scripts/validate.sh` — Expected: no syntax errors, OK.

```bash
git add references/hooks
git commit -m "feat: reference enforcement hooks (hardcoding, registry sync)"
```

---

### Task 6: skills/wellbegin/SKILL.md

**Files:**
- Create: `skills/wellbegin/SKILL.md`

**Interfaces:**
- Produces: `.wellbegun/begin.md` artifact spec (with 비싼 결정 대기 목록 section) that wellspec consumes.

- [ ] **Step 1: Write the skill**

Frontmatter (verbatim):
```yaml
---
name: wellbegin
description: "Use when starting a new wellbegun project or shaping an MVP idea — before any spec, plan, or code. Shapes the product in user language: whose problem, one core journey, success criteria, non-goals. Decides expensive product-identity decisions; flags expensive technical decisions into a queue without solving them. First lens of the wellbegun pipeline (wellbegin → wellspec → wellplan → wellrun)."
---
```

Body sections, with the design-doc requirements each must carry (§기획 렌즈):
1. **Guard** — if `.wellbegun/begin.md` exists with `status: approved`, route to wellspec instead; if `status: draft`, resume from its status table.
2. **Stance** — problem space only, user language only; scope is controlled by discipline (success criteria, non-goals, MVP cut), never by pulling the developer lens forward.
3. **The seven bundles** — one subsection each: (1) whose problem, in what situation, how solved today, where it hurts; (2) one core journey — happy path; two or more journeys = not an MVP, cut; must name at least one failure branch before it can close; (3) observable success criteria; (4) explicit non-goals list; (5) expensive product-identity decisions decided HERE: account model, multi-tenancy, pricing unit, data ownership, platform; (6) product character and tone in user language only (feel, reference products) — concrete values (hex, fonts) are wellspec's token registry job; (7) tech-smelling expensive decisions: only FLAG into the queue, never solve.
4. **Closure pressure valves** — per-bundle closing conditions; before closing a bundle, fire uncovered angles from `references/probe-angles.md`; only an explicit user "넘어가자/move on" overrides; probe depth adaptive.
5. **Status table** — the disk-anchored per-bundle table (covered angles / uncovered angles / open questions) kept inside `begin.md` and updated as you go.
6. **Output template** — full `begin.md` skeleton: `status: draft` frontmatter, sections for the seven bundles, the status table, and `## Expensive decision queue` (each entry: question, why it smells expensive, discovered-in bundle). Ends by asking the user to approve → flip to `status: approved`, then invoke wellspec.

- [ ] **Step 2: Verify and commit**

Run: `bash scripts/validate.sh` — Expected: OK (frontmatter checks now bite).

```bash
git add skills/wellbegin
git commit -m "feat: wellbegin skill — user-lens planning with probe-driven closure"
```

---

### Task 7: skills/wellspec/SKILL.md

**Files:**
- Create: `skills/wellspec/SKILL.md`

**Interfaces:**
- Consumes: `.wellbegun/begin.md` (approved) and its Expensive decision queue.
- Produces: `.wellbegun/spec.md` and first entries of `.wellbegun/decisions.md` that wellplan consumes.

- [ ] **Step 1: Write the skill**

Frontmatter (verbatim):
```yaml
---
name: wellspec
description: "Use when .wellbegun/begin.md is approved and no approved spec exists. Developer lens of the wellbegun pipeline: resolves the queued expensive decisions with reversal-cost grades (S/M/L/XL) and mini-ADRs, defines global registries (design tokens, shared components, backend common layers, DB schema) as markdown rosters, deliberately leaves cheap decisions to implementer discretion, and plans enforcement hooks."
---
```

Body sections (§스펙 렌즈, §전역 관리 구조):
1. **Guard** — require approved `begin.md`; if `spec.md` approved, route to wellplan; if draft, resume.
2. **Resolve the queue** — for every queue item: grade with `references/reversibility-grades.md`, record a mini-ADR (3–4 lines) into `.wellbegun/decisions.md`; L/XL require at least two compared alternatives; effort must be visibly proportional to grade.
3. **Define registries** — instantiate the four templates from `references/registry-templates/` as markdown rosters only (design tokens translate bundle-6 product character into named tokens with concrete values; component roster; backend common layers — error format, auth, logging; DB schema sketch). Timing rule: markdown rosters only — real files are created in plan phase 1, after the stack is fixed.
4. **Leave cheap decisions blank** — an explicit `## Implementer discretion` section listing what is deliberately unspecified; this section is the plugin's signature, not an omission.
5. **Enforcement plan** — which checks from `references/hooks/` apply, where they will be wired; installation itself becomes a phase 1 step in wellplan.
6. **Output template** — `spec.md` skeleton: `status:` frontmatter, resolved decisions (grades + ADR pointers), four registry rosters, discretion section, enforcement plan. Approval flips status → invoke wellplan.

- [ ] **Step 2: Verify and commit**

Run: `bash scripts/validate.sh` — Expected: OK.

```bash
git add skills/wellspec
git commit -m "feat: wellspec skill — graded decision resolution and registry rosters"
```

---

### Task 8: skills/wellplan/SKILL.md

**Files:**
- Create: `skills/wellplan/SKILL.md`

**Interfaces:**
- Consumes: `.wellbegun/spec.md` (approved).
- Produces: `.wellbegun/plan.md` with phase > step structure and six-item step contracts that wellrun executes.

- [ ] **Step 1: Write the skill**

Frontmatter (verbatim):
```yaml
---
name: wellplan
description: "Use when .wellbegun/spec.md is approved and no approved plan exists. Turns the spec into foundation-first phases: phase 1 materializes hard-to-reverse foundations (DB schema, design token file, minimal shared components, backend common layers, enforcement hooks) as real code while changing them is still cheap; later phases stack vertical feature slices. Every step gets a six-item contract written before any implementation exists."
---
```

Body sections (§플랜 렌즈, §검증 설계):
1. **Guard** — require approved `spec.md`; route/resume as in prior skills.
2. **Phase decomposition** — phase 1 is fixed: registries become code + hooks installed; rationale verbatim from design doc (materializing expensive foundations before code piles up is cheapest, and later steps start in a world where reuse is easier than hardcoding). Phase 2+ are vertical slices of the core journey.
3. **Step sizing** — one subagent, one context, machine-checkable completion; when in doubt, split.
4. **The six-item contract** (문제지) — exact template with all six: goal (one line); observable acceptance criteria; boundary tests fixed BEFORE implementation (the verifier will run these); registries to read; verification tier `fresh` or `basic` — derived automatically from the highest reversibility grade the step touches (L/XL → fresh, S/M → basic); discretion scope copied from the spec's discretion section.
5. **Output template** — `plan.md` skeleton: `status:` frontmatter, phase list, per-step contracts, a run-preview table (steps likely to stop on L/XL). Approval flips status → invoke wellrun.

- [ ] **Step 2: Verify and commit**

Run: `bash scripts/validate.sh` — Expected: OK.

```bash
git add skills/wellplan
git commit -m "feat: wellplan skill — foundation-first phases with step contracts"
```

---

### Task 9: skills/wellrun/SKILL.md

**Files:**
- Create: `skills/wellrun/SKILL.md`

**Interfaces:**
- Consumes: `.wellbegun/plan.md` (approved), `.wellbegun/decisions.md`, `references/hooks/`.
- Produces: executed steps; `.wellbegun/pending/<slug>.md` stop files; ADR entries.

- [ ] **Step 1: Write the skill**

Frontmatter (verbatim):
```yaml
---
name: wellrun
description: "Use when .wellbegun/plan.md is approved and execution should start or continue, including resuming after a stop. Conductor for subagent-driven execution: implementer subagents get the step contract and area registries; fresh-eyes verifier subagents get the contract and the diff, never the implementer's narrative. Verification intensity scales with reversal cost; hidden L/XL decisions stop the run in companion mode or get provisional reversible choices in autonomous mode."
---
```

Body sections (§런 렌즈, §검증 설계):
1. **Guard & conductor charter** — require approved `plan.md`. Verbatim rule: while a run is active, THIS skill is the conductor; Superpowers may be used for implementation techniques only (test-driven-development, systematic-debugging, verification-before-completion) — never brainstorming or writing-plans. If `.wellbegun/pending/` is non-empty, the run is stopped awaiting answers: process those first (answer → append mini-ADR to `decisions.md` → delete pending file; the file's existence IS the state flag).
2. **Start briefing** — confirm phase 1 contains the enforcement-hook installation step (add it if missing — rule 1); announce "the run stops on L/XL decisions"; show the plan's run-preview table; ask the user to pick a mode: **companion** (default; stop and ask on L/XL) or **autonomous** (never stop; take the most reversible provisional choice, mark it `provisional`, collect all L/XL decisions into an end-of-run report).
3. **Three-layer structure** — main session conducts and never writes code; implementer subagent receives the step contract + that area's registries; verifier subagent (fresh tier) is a brand-new context receiving ONLY: the contract, the diff, how to run things, registry rules — never the implementer's narrative or self-assessment (blind spots travel through shared context, so context is what gets isolated).
4. **Execution loop** — serial by default: implement → verify → fix → next. Four rules verbatim: (1) enforcement check at briefing; (2) read the area registry before working; (3) on the roster → reuse; not on it → create in the common folder and update the roster in the same commit; "hardcode now, clean up later" is forbidden; (4) hidden expensive decisions: grade them; S/M → decide, one ADR line, continue; L/XL → stop (companion) with a pending file containing situation, options, recommendation.
5. **Verifier charter** — adversarial framing ("find the reason this fails"), authority to write new probe tests; three layers: step verification → phase integration verification → whole-run fresh-eyes review. `basic` tier = lint + boundary tests pass.
6. **Stop UX** — pending file template (situation / options / recommendation / how to answer); note that push notification can be wired via the harness Notification hook (document, don't force).

- [ ] **Step 2: Verify and commit**

Run: `bash scripts/validate.sh` — Expected: OK.

```bash
git add skills/wellrun
git commit -m "feat: wellrun skill — conductor with context-isolated fresh-eyes verification"
```

---

### Task 10: README refresh + whole-set fresh-eyes review

**Files:**
- Modify: `README.md` (installation section, skill table)
- Possibly modify: any file the review flags

- [ ] **Step 1: Add installation + usage to README**

Add after "How it works": a `## Install` section (`/plugin marketplace add ardenspace/wellbegun` then `/plugin install wellbegun@wellbegun`) and a four-row table mapping skill → lens → artifact (`wellbegin → begin.md`, etc.). Update Status section: implementation shipped, dogfooding next.

- [ ] **Step 2: Dispatch a fresh-eyes review subagent**

Dispatch one subagent (fresh context — this project's own philosophy applied to itself) with: the design doc path, the four SKILL.md paths, references/, and this charter: "Find the reasons this plugin fails: contradictions with the design doc, contradictions between skills (artifact names, status conventions, grade semantics), instructions a naive agent would misread, and forbidden references (talpi/loopspace/pslog, superpowers planning skills). Report file:line per finding." Fix every legitimate finding inline.

- [ ] **Step 3: Final validation and commit**

Run: `bash scripts/validate.sh` — Expected: OK.

```bash
git add -A
git commit -m "docs: install guide and skill table; apply fresh-eyes review fixes"
```

---

## Out of scope (next sessions)

- Dogfooding on a real project (design doc step: 시식) — separate session, after local install.
- Marketplace publication/announcement; version bump discipline (CHANGELOG starts at first release tag).
- Stack-specific hook packs beyond the generic grep examples.
