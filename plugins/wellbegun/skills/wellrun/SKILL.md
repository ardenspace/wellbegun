---
name: wellrun
description: "Use when .wellbegun/plan.md has status: approved and execution should start or continue — including resuming after a stop, or when .wellbegun/pending/ is non-empty. Final lens of the wellbegun pipeline (wellbegin → wellspec → wellplan → wellrun)."
---

# wellrun — execute within verified boundaries

Execute approved step contracts sequentially. Reuse the implementer within a verified boundary; independently verify a new foundation before dependent work spreads it.

## Shared resources

Resolve `<plugin-root>` before reading a bundled resource: `${CLAUDE_PLUGIN_ROOT}` in Claude Code; the directory two levels above the directory containing this `SKILL.md` in Codex. Never resolve it relative to the user's project.

## Guard and resume

Use `<plugin-root>/references/selected-inputs.md` for `context --remember`
bootstrap, selective lookup and independent dispatch (reuse it if already read).

First reconcile explicit session approval with artifact status; update a stale draft flag for that approved scope instead of restarting planning.

- Missing or unapproved `.wellbegun/plan.md` → route to wellplan.
- Read the current contract, relevant gates, applicable registry entries and active decisions, plus the current progress record. Do not load historical decisions or completed-round narratives as default input. Decision lookup and recording rules are in `<plugin-root>/references/reversibility-grades.md`.
- Process `.wellbegun/pending/` before resuming affected work. Reconcile answers already given and record the resulting decision. Schema 2 uses `resolve-pending` below; legacy removes only the answered file after recording it. An interruption is not an answer.
- Preserve the existing cycle's artifact format. For legacy cycles, `run.md` remains the progress record; do not partially introduce a new state format.
- Check current code, work location and contract against the recorded target before reusing completion results. Drift requires checking the impact, not assuming completion or automatically rolling back code.

## Start briefing and ownership

Reuse the stored mode and existing user approval. On a first run with no choice, use **companion**: ask only for newly discovered L/XL decisions. **Autonomous** applies when authorized: choose the most reversible provisional option within that authority and report it. Neither mode permits passing a broken contract or exceeding execution permissions.

Briefly show likely decision stops and required verification boundaries. Install only enforcement selected by the spec and needed for this project; do not invent a foundation or hook step at briefing.

Default to one writer in the existing worktree. Inspect existing changes and scope; never revert, stash, overwrite or indiscriminately stage user changes. Commit only owned changes under project policy and existing authority. Choose isolation when ownership overlaps or a separate candidate is needed, explicitly preserving the required uncommitted baseline.

## Schema 2 execution

Use the helper for authoritative writes; never hand-edit state/run/HANDOFF. On a
new approved marker-based plan with no previous execution artifacts, initialize
once with the chosen cycle and stored/authorized mode:

```sh
python3 "$wb_helper" transition --root "$wb_root" --expected-revision 0 --input - <<'JSON'
{"op":"init","cycle":"cycle-1","mode":"companion"}
JSON
```

Then read `context --remember`. For each write, use the last returned revision
as `wb_revision`; pass the operation as JSON via stdin, without temporary input
or receipt files:

```sh
python3 "$wb_helper" transition --root "$wb_root" --expected-revision "$wb_revision" --input -
```

Start a step with `op:set,record,status:implementing,context_id,actor,workspace,target`.
`actor` may be null; workspace is the absolute project root, target is the
relevant project-relative source/test/config paths (including planned new files,
with at least one existing file). Declare the actual dependency/input closure;
the helper cannot discover undeclared dependencies. Execute checks in that
workspace, regardless of where the helper was called.

After basic implementation and successful affected checks, one
`op:complete-basic,record,target,checks` write completes it. No separate checking
write, receipt copying or verifier is required. Each check records its actual
`command,files,exit_status,environment,environment_known,external_state,covers`;
`covers` names completion clause IDs. Reuse valid evidence with
`reuse:[{evidence:ID,covers:[IDs]}],environment` instead of rerunning it. Read only
“State writes” in the runtime contract when constructing a payload the first time.

Fresh step completion uses checking with the independent `verifier_context_id`,
then verified with successful checks/reuse and the actual verifier ACCEPT.
Gate/phase/whole-run start directly in checking, with the independent context as
both `context_id` and `verifier_context_id`, after its verifier packet reads.
Do not manufacture independent verdicts when the host cannot provide them.

Transitions generate run.md. Use `render` only to recover missing derived output;
`render --handoff` optionally requests a persistent HANDOFF and returns a new
revision. Neither generated file is a second bootstrap input.

At interruption or decision wait use `op:set,status:stopped,record,reason` and
the concrete `next_action`; a checkpoint may refresh expected edited `target`
paths before a stop. On resume, bootstrap the current packet and explicitly set
the saved `resume_status` with the actual context identity. For detected drift,
use `op:reconcile,reason`, restore prerequisites through required checking and
fresh gates, then resume the preserved consumer action. Same-file additions
require current checks; do not repeat completed implementation merely because a
hash changed. Pending and unresolved caps remain blockers. Read only “Checkpoint,
drift, and recovery” for an unfamiliar recovery case.

Schema 2 questions are `pending/<slug>.json` with a `question` body containing
the situation, choices and recommendation. Stop with `pending:"pending/<slug>.json"`.
Preserve that question when adding the actual `answer` and `decision_key`;
record the approved active decision, then use
`op:resolve-pending,record,decision_key`. It saves answer evidence and removes
the answered file; explicit resume follows. Never unlink a schema 2 question to
bypass dispatch. Lost/mismatched mailbox files require reconciliation.

## Implementer continuity

The current agent may implement basic work directly. A subagent is optional for basic execution. Reuse an implementer for successive S/M steps when the area, contracts and decisions remain valid and context is sufficient. Use a new implementer after a phase, context shortage, ownership conflict, material contract change, or resolution of a newly discovered L/XL decision. Do not ask or write an ADR for routine reuse.

Technique skills may support implementation. Do not restart another planning pipeline during an approved run.

Before changing an area, read its relevant active registry entries and current constraints. Reuse established public contracts. Materialize elements explicitly planned as shared from their first use; otherwise keep the first use local and assess promotion at the second actual use. Similar appearance alone does not justify abstraction. Update relevant registry entries with shared changes; N/A areas need no registry.

Grade the decision being introduced or changed, not an existing L/XL API merely being used. Consult `<plugin-root>/references/reversibility-grades.md`: S needs no permanent ADR; record M only when future work needs the choice. New L/XL decisions go to the conductor/current session for authority and contract review. Companion pauses affected work with a pending question; authorized autonomous work records a provisional choice. Resume with the resolved contract and a new implementer, and use fresh verification for the L/XL change.

If contracts are missing or contradictory, constraints surprise you, the same cause fails repeatedly, or scope grows, pause dependent work and revisit assumptions. Add a gate when needed. Replacing the implementer is not verification.

## Propagation gates

A gate names its producer and the consumers blocked until it passes. Independently verify a new shared contract or data flow before the first consumer, even if its producer is S/M. An L/XL producer's fresh verification, or phase integration before the first consumer testing the same conditions, can satisfy the gate without another review.

On failure, fix the producer before consumers proceed. A change to the foundation contract or verified behavior invalidates the gate; assess affected consumers and rerun necessary verification. Record newly discovered dependencies and gates in the plan under existing authority unless they change an expensive decision or authorized scope.

## Verification and completion

- **Basic:** complete after the contract checks and affected lint/analyze or other relevant checks pass. No separate verifier or verifier ACCEPT is required.
- **Fresh:** use a new independent context. Give it the contract, target code/diff, execution commands, relevant registry entries and active decisions. Valid command-result facts may be supplied; exclude implementer self-assessment, full evidence narratives and previous verifier judgments. The verifier explores code and may make probes, but does not modify target implementation or existing tests. Prefer strong reasoning capability if the host offers model selection; no named model is required.
- Without subagents, basic still runs. At a fresh boundary, prepare the same packet for a separate independent session and wait. Same-context self-review is not fresh. Git, hooks and context-usage APIs are not prerequisites for basic execution.
- REJECT must identify a violated contract clause and reproduction evidence. Report outside-contract suggestions separately; they do not block completion unless they expose a new L/XL choice or a defect in the current contract. Give the fixer failed clauses and reproduction facts. Reverification uses a new independent context.
- The observable Goal and acceptance criteria determine completion. A diff limited to tests, hooks, documentation or comments is not evidence that the deliverable is complete.

### Rounds and unresolved findings

Each verification scope gets at most three rounds including the first. Keep stable finding IDs across retries. Renaming a step or finding, changing a candidate SHA or rewording a contract does not reset rounds. Only an actually approved new scope is a new unit; retain each prior finding as resolved, explicitly excluded, or unresolved. Exclusion is not a pass.

After round 3 fails, preserve the unresolved status. Ask for additional rounds or a meaningful scope change when needed; neither companion nor autonomous may mark the failure verified. Continue only unaffected independent work allowed by the plan; otherwise checkpoint and report the blocker. Outside-contract deferred suggestions remain distinct from unresolved contract violations.

### Checks and evidence

Run each successful check once for the same valid inputs. Assign one execution owner, so conductor and verifier do not habitually duplicate commands. S/M uses contract and affected checks; fresh adds necessary regression and independent judgment. There is no mandatory full suite immediately before a fresh dispatch.

Record target commit or content identity (HEAD alone is insufficient for dirty code), scope, command, exit status, relevant environment/dependency identities and external-state dependence. Changed source, tests, configuration, dependencies or environment invalidate affected results. Uncertain external state is not reusable. Documentation-only SHA changes do not invalidate unchanged test inputs. A verifier may rerun a result it has reason to distrust; record the reason briefly.

UI rendering and observable states are valid acceptance checks. Do not invent a test framework just to turn every visual criterion into an exit code; use goldens only for a stable environment and clear purpose.

Use temporary reproductions first. Keep permanent probes only for new regression value, preferably integrated by the implementer into existing tests. Rerun changed tests after integration. Zero to two new permanent probes per round is a target, not a quota or cap; clean up relevant probes at phase end.

Phase integration uses a fresh context to verify the phase's composition and necessary regression, including key rendered states for UI. Its contract states what must compose. Fix owned failures under the relevant contract; do not reset finding rounds. Whole-run fresh review checks all release criteria, reusing valid results and running only missing or invalidated checks. Every required step, gate and review must pass before completion.

## Legacy progress and checkpoint

Keep one current line per record in `.wellbegun/run.md`, with the saved mode in frontmatter. Use `[ ]` queued, `[>]` active/stopped, `[x]` verified. Record status, target identity, round, stable unresolved finding IDs, short check results, evidence pointers and next action. Keep raw logs and failed-round narratives in evidence files, not growing single lines. A stopped contract violation cannot be hidden under `## Deferred`; that section is for outside-contract work.

Checkpoint after a step, verification round or gate, on a decision wait, user interruption, or host context-shortage signal. Do not guess usage percentages. Preserve work location, current target, contract, round and resume action. Reports normally contain status, target ID, changed scope, checks, unresolved findings and next action within 300 words; detailed findings live in referenced files.

## Pending questions and completion

For a legacy cycle's new decision requiring an answer, write `.wellbegun/pending/<slug>.md` with the question, situation, options and reversal grades, recommendation, and how to answer. Schema 2 uses the JSON question protocol above. Notifications are optional and require existing channel authorization; see `<plugin-root>/references/hooks/README.md`.

After all contracts and required gates/reviews pass, report completed work, valid verification, remaining outside-contract findings and provisional decisions. A missing independent verifier or unresolved contract means stopped, not complete.
