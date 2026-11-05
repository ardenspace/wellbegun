# Lean wellrun verification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move fresh verification to a few planned points (shared-foundation gates, money/auth gate, whole-run with parallel perspective reviewers), stop code changes from invalidating verified records, and carry forwarded findings into the packets that must see them.

**Architecture:** Runtime changes live in `plugins/wellbegun/scripts/artifacts.py` (single-file helper, stdlib only). New packet information (forwarded lines, changed-foundation review items, recheck list) is computed at `context` time and returned in a non-receipt `notes` field, so it never creates read obligations or drift. Whole-run perspective verification extends the existing fresh checking path with per-perspective verifier contexts inside one scope and one round. Skill and reference text changes follow the runtime.

**Tech Stack:** Python 3 stdlib, `unittest` (run through `scripts/validate.sh`), Markdown skill files.

**Spec:** `docs/2026-11-05-lean-wellrun-verification-design.md` (Korean). Read it fully before Task 1; section "구현 전에 정한 세부 사항" settles most edge cases.

## Global Constraints

- Skill and reference bodies are English; keep the existing terse style.
- Helper stays stdlib-only and single-file; no schema number bump (`schema: 2` stays).
- Existing approved plans must still validate: `perspectives` is optional; fresh steps and fresh phases remain legal.
- Old `state.json` files lack new record fields; read them with `.get(...)` defaults, never require them in `validate_state`'s `fields(...)` list.
- Legacy (schema 1) cycles are untouched.
- Version becomes `0.8.0` in both `plugins/wellbegun/.claude-plugin/plugin.json` and `.codex-plugin/plugin.json`.
- Full suite: `bash scripts/validate.sh` from the repo root must print `OK: wellbegun structure valid` and the unittest `OK`.
- Commit after each task; messages follow `feat:`/`fix:`/`docs:` style and end with the attribution line used in this repo.

## Review Focus

1. A verified fresh gate whose target file is later edited: no `code_drift`, and the gate appears in `notes.review_items` of every later not-yet-verified fresh record (Task 2 test).
2. A `deferred.md` line appended mid-record (`→ step-x`) must not cause `unread_context`, `input_drift` or `code_drift` for the in-flight record (Task 3 test).
3. Whole-run REJECT from one perspective: the next round must demand verifiers only for non-accepted perspectives, and the round counter still increments once (Task 4 test).
4. Recheck without a verifier is only legal for a record that previously held an independent ACCEPT; a never-verified gate cannot use `recheck_reason` (Task 5 test).
5. Basic phase start/complete uses one audience consistently; a basic phase must not hit `unread_context` at completion (Task 4 test).

---

### Task 1: Verified records ignore code drift

**Files:**
- Modify: `plugins/wellbegun/scripts/artifacts.py:372-401` (`drifted`)
- Test: `plugins/wellbegun/tests/test_state.py`

**Interfaces:**
- Produces: `drifted(root, state, records=None, only=None) -> list[str]` — for records with `status == 'verified'`, only `input_digest` mismatch counts (selected decision/registry sections). Target snapshot, check-input snapshot and runtime-environment changes no longer count for verified records. Non-verified records keep current behavior (target snapshot check).

- [ ] **Step 1: Write the failing tests** in `test_state.py`:
  - `test_verified_record_survives_later_code_change`: complete `producer` (basic) and `gate` (fresh); edit `src.py`; assert `runtime.context(root, 'consumer', context_id='consumer-worker')` returns `status == 'ok'` and `runtime.validate(root)` raises nothing; assert `state(root)['records']['producer']['status'] == 'verified'`.
  - `test_verified_record_survives_runtime_change`: same setup, patch `runtime.runtime_environment` to return a different value; assert `runtime.validate(root)` passes.
  - `test_selected_input_change_still_invalidates_verified`: keep as the existing G1-002 tests already do (decision supersede / registry constraint change still raise `code_drift`). No new test needed; confirm they stay green.
- [ ] **Step 2: Run** `python3 -m unittest discover -s plugins/wellbegun/tests -k survives` — expected FAIL with `code_drift`.
- [ ] **Step 3: Implement** the `drifted` change: in the loop, when `rec['status'] == 'verified'`, evaluate only the `input_digest` comparison and skip the target and `current_result` check blocks.
- [ ] **Step 4: Run the full suite** `bash scripts/validate.sh`. Tests that asserted `code_drift` caused by editing a *verified* record's files or runtime now fail by design. For each, rewrite the assertion to the new behavior (no drift; the record stays verified) and rename the test so its name states the new rule. Known candidates: `test_state.py` tests at about lines 65, 108, 216-220, 243-260, 469-535, 759, 769, 795-805. Tests where the drifting record is `implementing`/`fixing`/`stopped` (e.g. 886-892) keep asserting `code_drift`. Do not delete coverage of selected-input drift (G1-002 tests).
- [ ] **Step 5: Run** `bash scripts/validate.sh` — expected all OK.
- [ ] **Step 6: Commit** `feat(runtime): verified records ignore later code changes`.

### Task 2: Changed-foundation review items

**Files:**
- Modify: `plugins/wellbegun/scripts/artifacts.py` (new function near `drifted`; `context` at 517-568)
- Test: `plugins/wellbegun/tests/test_context.py`

**Interfaces:**
- Consumes: Task 1 `drifted`.
- Produces:
  - `changed_foundations(root, state, records) -> list[dict]` returning `[{'record': key, 'files': [sorted project-relative paths whose hash differs from rec['target']]}]` for every record with `status == 'verified'`, `records[key]['grade'] == 'fresh'`, and `not valid_snapshot(root, rec['target'])`.
  - `context(...)` full-packet and single-section responses gain `notes: dict`. This task adds `notes['review_items']`, present only when the requested record's contract is `grade == 'fresh'` and its state status is not `verified`. `notes` is never part of `parts`, receipts, `ensure_reads` or `selected_sections`.

- [ ] **Step 1: Write the failing test** `test_fresh_packet_lists_changed_verified_foundation`: build a plan with `producer` (basic), `gate` (fresh), `consumer` (basic), and a `whole-run` record (fresh, `requires: ['consumer']`; add via `write_plan` before init). Verify producer and gate, edit `src.py`, then `packet = runtime.context(root, 'whole-run', context_id='final')`; assert `packet['notes']['review_items'] == [{'record': 'gate', 'files': ['src.py']}]`. Also assert `runtime.context(root, 'consumer', context_id='c')['notes']` has no `review_items` key (basic record).
- [ ] **Step 2: Run** it — expected FAIL (`KeyError: 'notes'`).
- [ ] **Step 3: Implement** `changed_foundations` and attach `notes` in `context` after `base` is built and before the `LIMIT` checks. Cap each notes list at 50 entries; when truncated, add `notes['<name>_more'] = <remaining count>`.
- [ ] **Step 4: Run** `bash scripts/validate.sh` — expected OK.
- [ ] **Step 5: Commit** `feat(runtime): surface changed verified foundations to later fresh reviews`.

### Task 3: Forwarded lines and whole-run lists

**Files:**
- Modify: `plugins/wellbegun/scripts/artifacts.py`
- Test: `plugins/wellbegun/tests/test_context.py`

**Interfaces:**
- Consumes: Task 2 `notes`.
- Produces:
  - `FORWARD_FILES = ('deferred.md', 'rule-candidates.md')` (both under `.wellbegun/`).
  - `forward_lines(root) -> list[dict]`: every line in those files matching `→\s*([\w.-]+)`; each item `{'file': name, 'line': stripped text, 'to': captured ID, 'done': ('✓ ' + to) in line}`. Missing files yield nothing.
  - `notes['forwarded']`: items with `to == key` (all records, both audiences), always present (possibly empty).
  - `notes['open_forwards']` (only when contract `kind == 'whole-run'`): items with `done is False`, any `to`.
  - `notes['rechecks']` (only for whole-run): `[{'record': k, 'reason': ev['recheck_reason']}]` for records whose `current_result` evidence has a nonempty `recheck_reason` (populated by Task 5; empty until then).

- [ ] **Step 1: Write failing tests:**
  - `test_forwarded_lines_reach_target_packet`: write `.wellbegun/deferred.md` with `- step-1: refund policy undecided → consumer\n- step-1: other → gate ✓ gate\n`; assert `runtime.context(root, 'consumer', context_id='c')['notes']['forwarded'] == [{'file': 'deferred.md', 'line': '- step-1: refund policy undecided → consumer', 'to': 'consumer', 'done': False}]`.
  - `test_appending_forward_line_does_not_block_inflight_record`: start `producer` (implementing) with all reads; append `- x: y → producer` to `deferred.md`; assert `tx(root, {**success_payload(), 'op': 'complete-basic'})` succeeds and `producer` is verified (no `unread_context`/`input_drift`/`code_drift`).
  - `test_whole_run_lists_open_forwards`: with the Task 2 whole-run plan, lines `→ consumer` (open) and `→ gate ✓ gate` (done); assert `notes['open_forwards']` contains only the open line.
- [ ] **Step 2: Run** — expected FAIL.
- [ ] **Step 3: Implement** `forward_lines`, the three notes, and `rechecks` (reads evidence via `load_evidence`).
- [ ] **Step 4: Run** `bash scripts/validate.sh` — expected OK.
- [ ] **Step 5: Commit** `feat(runtime): deliver forwarded findings to their target packets`.

### Task 4: Perspectives, basic phases and parallel whole-run verification

**Files:**
- Modify: `plugins/wellbegun/scripts/artifacts.py` (`plan` 88-147, `validate_state` 277-335, `apply_status` 888-1008, `sections` 438-459)
- Test: `plugins/wellbegun/tests/test_round_limit.py` or a new `plugins/wellbegun/tests/test_perspectives.py` (use `test_support` helpers)

**Interfaces:**
- Produces:
  - `PERSPECTIVES = ('goal', 'abuse', 'money')`.
  - `plan()`: optional `perspectives` — nonempty list, unique, subset of `PERSPECTIVES`, only on `grade == 'fresh'` records, else `invalid_plan`. Grade rule becomes: `gate` and `whole-run` must be fresh; `phase` may be `basic` or `fresh`; steps either.
  - `perspectives_of(contract) -> list[str]`: `contract.get('perspectives')` or, for `kind == 'whole-run'`, `list(PERSPECTIVES)`; else `[]`.
  - `parallel(contract) -> bool`: `kind == 'whole-run' and len(perspectives_of(contract)) > 1`.
  - Packet: `sections()` adds `result['contract']` unchanged (perspectives are inside the contract already); no new section.
  - New optional record fields (default via `.get`): `perspective_verifiers: {p: cid}` (current round), `accepted_perspectives: {p: cid}` (carried across rounds of the scope).
  - Transition payloads for a parallel record:
    - entering `checking`: `verifier_context_ids: {p: cid}` whose keys equal `set(perspectives_of) - set(accepted)` after removing any `rerun_perspectives: [p]` from accepted. Each cid passes `independent(..., current_target=True)`, is not in `rec['verifier_contexts']`, and has verifier reads (`ensure_reads(..., 'verifier')`). Round increments once. `current_verifier` stays `None`.
    - `checking → verified`: `verdicts: {p: {'status': 'ACCEPT', 'independent': True, 'context_id': cid}}` for every key in `perspective_verifiers`; accepted ∪ these must equal all perspectives. The result evidence stores the merged `verdicts` map. Skip the single-verdict check and the `ensure_reads` on the payload `context_id`.
    - `checking → fixing`: `verdicts` for perspectives that accepted this round (merged into `accepted_perspectives`), plus `findings` (each `id` starts with `'<p>-'` for some `p` in `perspective_verifiers`) and/or `recheck_perspectives: [p]` (whole-run fixed-now: those perspectives are removed from accepted). At least one of `findings` or `recheck_perspectives` must be nonempty. `findings` may be empty only when `recheck_perspectives` is nonempty.
  - `validate_state`: for a verified parallel record, require result `verdicts` covering all perspectives, each ACCEPT/independent, each `context_id` in `rec['verifier_contexts']` and passing `independent(records, state, key, cid)`.
  - Basic non-step records (basic phase): start audience is `'implementer'` (change `audience = 'implementer' if contract['kind'] == 'step' else 'verifier'` to also use `'implementer'` when `contract['grade'] == 'basic'`), so completion's `ensure_reads(..., 'implementer')` matches.

- [ ] **Step 1: Write failing tests:**
  - `test_perspectives_validation`: `perspectives: ['goal', 'goal']`, `['speed']`, and on a basic step each raise `invalid_plan`; `['goal', 'abuse']` on the fresh gate passes; a `kind: phase, grade: basic` record passes; `kind: gate, grade: basic` raises.
  - `test_basic_phase_completes_without_verifier`: plan producer → basic phase (`requires: ['producer']`); verify producer, start phase with `verifier`-free checking, complete with checks; assert `verified`.
  - `test_whole_run_parallel_accept`: whole-run with default perspectives; enter checking with three distinct verifier cids (each did verifier reads); complete with three ACCEPT verdicts; assert verified and `scopes[...]['round'] == 1`.
  - `test_whole_run_reject_reruns_only_rejecting_perspective`: round 1: goal and money ACCEPT, finding `abuse-1`; assert entering round 2 with `{'goal': ..., 'abuse': ...}` raises `invalid_input`, entering with `{'abuse': 'v4'}` succeeds, round is 2; completing with only `abuse` ACCEPT yields verified.
  - `test_whole_run_fixed_now_reruns_perspective`: round 1 all ACCEPT except payload goes to `fixing` with `recheck_perspectives: ['goal']` and no findings; round 2 requires exactly `{'goal'}`.
  - `test_whole_run_finding_needs_perspective_prefix`: finding `id: 'x-1'` raises `invalid_input`.
  - `test_whole_run_rerun_perspectives_reopens_accepted`: after the REJECT round, entering round 2 with `rerun_perspectives: ['money']` requires `{'abuse', 'money'}`.
- [ ] **Step 2: Run** — expected FAIL.
- [ ] **Step 3: Implement** in the order: `plan()` validation and grade rule; `perspectives_of`/`parallel`; basic non-step audience; parallel branches in `apply_status`; `validate_state` branch. Non-parallel fresh records keep the existing single-verifier path unchanged.
- [ ] **Step 4: Run** `bash scripts/validate.sh` — expected OK (existing round-limit tests still pass).
- [ ] **Step 5: Commit** `feat(runtime): perspective-parallel whole-run review and basic phases`.

### Task 5: Recheck without a verifier after contract change

**Files:**
- Modify: `plugins/wellbegun/scripts/artifacts.py` (`apply_status`, `validate_state`)
- Test: `plugins/wellbegun/tests/test_state.py`

**Interfaces:**
- Consumes: Task 3 `notes['rechecks']`.
- Produces:
  - `previously_accepted(root, rec) -> bool`: any evidence in `rec['evidence']` with `kind == 'result'` and either `verdict.status == 'ACCEPT'` or a `verdicts` map whose values are all ACCEPT.
  - Entering `checking` on a fresh record with payload `recheck_reason` (nonempty str): allowed only when `previously_accepted`; no verifier required; sets `rec['recheck'] = reason`; round increments as usual.
  - `checking → verified` with `rec.get('recheck')`: no verdict required; result evidence gets `'recheck_reason': reason`; then `rec['recheck'] = None`.
  - `validate_state`: a verified fresh record passes the verdict check if its result has a nonempty `recheck_reason`.

- [ ] **Step 1: Write failing tests:**
  - `test_contract_change_recheck_with_reason_skips_verifier`: verify producer and gate; edit the gate's completion text in `plan.md`; `reconcile` (with approval fields the existing replan tests use); re-enter gate checking with `recheck_reason: 'wording only'` and no verifier; complete with checks only; assert verified and the result evidence holds `recheck_reason`; assert the whole-run packet (Task 2 plan) `notes['rechecks'] == [{'record': 'gate', 'reason': 'wording only'}]`.
  - `test_recheck_reason_rejected_without_prior_accept`: a never-verified gate with `recheck_reason` raises `invalid_transition` (or the existing verifier-required stop) — assert it does not reach verified.
- [ ] **Step 2: Run** — expected FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** `bash scripts/validate.sh` — expected OK.
- [ ] **Step 5: Commit** `feat(runtime): checks-only recheck of previously accepted fresh records`.

### Task 6: Runtime contract and verification policy text

**Files:**
- Modify: `plugins/wellbegun/references/runtime-contract.md` (plan fields ~28-40; packets ~100-120; rounds/drift ~195-240)
- Modify: `plugins/wellbegun/references/reversibility-grades.md` ("Verification boundaries")

- [ ] **Step 1:** In runtime-contract, document: optional `perspectives`; gate/whole-run fresh, phase basic or fresh; `notes` (`forwarded`, `review_items`, `open_forwards`, `rechecks`) is informational, carries no receipts and never drifts; verified records drift only on selected-input change; parallel whole-run payloads (`verifier_context_ids`, `verdicts`, `rerun_perspectives`, `recheck_perspectives`, finding prefixes); `recheck_reason`. Replace the sentence "After a verified scope is invalidated by actual target/check-input or selected-input content drift" with selected-input drift only.
- [ ] **Step 2:** In reversibility-grades "Verification boundaries": fresh review sits at planned points (shared-foundation gates, the money/auth gate, whole-run); L/XL grade alone no longer makes a step fresh; foundation changes after a verified gate become review items for the next fresh point instead of invalidating it.
- [ ] **Step 3: Run** `bash scripts/validate.sh` — expected OK.
- [ ] **Step 4: Commit** `docs(reference): runtime contract for lean verification`.

### Task 7: wellplan text

**Files:**
- Modify: `plugins/wellbegun/skills/wellplan/SKILL.md` (format paragraph ~58-62, grade paragraph 64, round_limit paragraph 66, Run preview template ~93-96)

- [ ] **Step 1:** Replace the grade paragraph with these decisions:
  - Steps are `basic`. Fresh review sits only at: a gate after each new shared foundation (protocol, schema, shared server); one gate where money and auth flows first connect (bundle both); `whole-run`.
  - A bundled point is one gate whose `requires`/`producers` list the bundled steps and whose `completion` restates the clauses to verify.
  - Foundation gates set `perspectives` including `goal` and `abuse`; the money/auth gate includes `money` and `abuse`; whole-run defaults to all three.
  - An L/XL step outside these points gets one line "fresh not needed: <reason>" shown in Run preview.
  - Phase records are `basic`; their completion includes an e2e run and a screenshot review of key states.
- [ ] **Step 2:** Update `round_limit` paragraph: applies to fresh gate and whole-run contracts.
- [ ] **Step 3:** Replace the Run preview template: table `point | records bundled | perspectives`, then one summary line `fresh N points, about M agents, recheck: checks only`, then the "fresh not needed" lines.
- [ ] **Step 4: Run** `bash scripts/validate.sh` — expected OK.
- [ ] **Step 5: Commit** `docs(wellplan): plan fresh points and perspectives`.

### Task 8: wellrun text

**Files:**
- Modify: `plugins/wellbegun/skills/wellrun/SKILL.md`

- [ ] **Step 1:** Edit these sections to state the decisions (keep prose terse):
  - Schema 2 execution: fresh checking for whole-run uses `verifier_context_ids`/`verdicts`; recheck after a contract change uses `recheck_reason` with checks only unless contract-visible behavior changed; read `notes` in every packet.
  - Implementer continuity: a newly discovered L/XL decision still pauses for approval (companion) or a provisional choice (autonomous), but its review is added as a line `→ <next fresh record ID>` in `deferred.md`, not as a new fresh verification.
  - Propagation gates: gates are the planned foundation and money/auth fresh points; a later change to a verified gate's files is not invalidation and reaches the next fresh point through `notes.review_items`.
  - Verification and completion: replace 0.7.4's single-verifier "Goal check" and "Abuse and robustness" bullets with perspectives — each fresh verifier reads `begin.md` and covers the contract's `perspectives`; at whole-run one verifier per perspective runs in parallel, finding IDs use `goal-`/`abuse-`/`money-`, reverification reruns only rejecting perspectives (plus any whose contract-visible behavior the fix changed).
  - Classification rule: an outside-contract finding touching abuse, money or a `begin.md` promise is not only deferred. Default: fix now when within current contract scope and S/M, then add `- <record ID>: fixed now — <finding ID>: <fix> → <next fresh record ID or whole-run>` to `deferred.md`. Ask the user (one pending at review end) only when the fix changes a `begin.md` promise or needs an L/XL choice; autonomous records a provisional choice. At whole-run, a fixed-now finding sends its perspective back via `recheck_perspectives` (counts as a round).
  - Lost coverage: on money/auth/shared-protocol paths, the coverage-loss line in `deferred.md` carries `→ <next fresh record ID>`; elsewhere keep the 0.7.4 line without forwarding.
  - Deferred findings and rule candidates: a finding meant for a later record carries `→ <record ID>`; the receiving implementer appends `✓ <record ID>` when handled or forwards it again; whole-run reports every open forward.
  - Phase integration: the implementer runs e2e and reviews screenshots; record the review as a check whose `files` are the screenshot paths and whose `command` is `screenshot review: <one-line note>`.
  - Checks and evidence: the 0.7.4 test-count rule applies to basic steps and phases too.
- [ ] **Step 2: Run** `bash scripts/validate.sh` — expected OK.
- [ ] **Step 3: Commit** `docs(wellrun): lean verification flow`.

### Task 9: Release 0.8.0

**Files:**
- Modify: `plugins/wellbegun/.claude-plugin/plugin.json`, `plugins/wellbegun/.codex-plugin/plugin.json` (`"version": "0.8.0"`)
- Modify: `README.md` ("Current release" line → 0.8.0 and `docs/releases/0.8.0.md`; update the test count sentence if it names a current count)
- Create: `docs/releases/0.8.0.md` (same shape as `docs/releases/0.7.4.md`: title, one paragraph of why with a link to the design doc, bullets of changes, a note that in-progress schema 2 cycles get the drift relaxation immediately and old plans stay valid)

- [ ] **Step 1:** Write the files above.
- [ ] **Step 2: Run** `bash scripts/validate.sh` — expected OK.
- [ ] **Step 3: Commit** `feat: lean wellrun verification (0.8.0)`.
