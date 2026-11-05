# Runtime disk and CLI contract

Python 3.9+ and its standard library are required. Run the plugin's
`scripts/artifacts.py` by absolute path; `--root` is the project's `.wellbegun`
directory. The project root is its parent. Git and subagent APIs are optional.
The five commands emit one JSON object: success exit 0, errors exit 2 with
`status:error`, `code`, `message`, and bounded details. `overflow` is an explicit
successful routing response, never a truncated contract. No command returns logs.

## Minimal runnable input

`tests/fixtures/plan.md`, `init.json`, `decisions.index.json`, and
`registry.index.json` form a producer → independent gate → consumer example.
`tests/test_support.py` provides `create_project`, `read_all`, `start`, `checking`,
and `record_success` for disposable examples. These helpers call the public Python
functions with the same payloads accepted by the CLI.

```sh
python3 /path/to/plugin/scripts/artifacts.py transition --root .wellbegun --expected-revision 0 --input .wellbegun/init.json
python3 /path/to/plugin/scripts/artifacts.py context --root .wellbegun --context-id worker-1
python3 /path/to/plugin/scripts/artifacts.py validate --root .wellbegun
python3 /path/to/plugin/scripts/artifacts.py render --root .wellbegun
python3 /path/to/plugin/scripts/artifacts.py decision-get --root .wellbegun --key theme.owner
```

## Plan and selected inputs

The plan requires YAML frontmatter `status: approved`. Each plan record is JSON inside `<!-- wellbegun:contract ID -->` and
`<!-- /wellbegun:contract -->`. Other Markdown is preserved and ignored by the
extractor. File order is execution order. Required fields are `id`, `kind`
(`step|gate|phase|whole-run`), `scope_id`, `goal`, `completion` (nonempty list of
`{id,text}`), `verification` (nonempty command strings), `decisions` (keys),
`registry` (keys), `discretion`, `requires` (predecessor IDs), and `grade`
(`basic|fresh`). Gate and whole-run records use fresh; a phase may be basic or
fresh; a step either. A gate also declares
nonempty `producers` and `consumers`. Optional `round_limit` is `2` or `3`
(default `3`; see State writes). Optional `perspectives` is a nonempty unique
subset of `goal|abuse|money`, only on fresh records. A whole-run without it
reviews all three; plans without the field stay valid. Dependencies must precede consumers;
cycles, missing IDs, duplicate IDs/scopes, and transitive gate bypass fail.
`scope_id` survives renaming and contract edits so rounds cannot reset. Stable IDs,
keys, context IDs and detail names use 1–120 ASCII letters/digits/`_.-`.

`decisions.index.json` has `schema:1`, `active:[{key,id}]`, and `records:[...]`.
It is the authoritative current pointer/status representation for new decisions.
Each record has `key,id,grade,status,choice,scope,constraints,reason,source,
required_sections`. Status is `approved|proposed|superseded`; only approved active
records can be returned. IDs are immutable identities: supersede with a new ID,
update the active pointer, and preserve the old record. Source originals remain
untouched. Duplicate pointers/IDs are ambiguous, including identical duplicates.
`source` is null or `{path,start,end,sha256}`; the hash is SHA-256 of the exact UTF-8
text strictly between globally unique delimiters. Paths are relative to artifact
root and may reach other files within project root. `required_sections` maps
names to such references; every mandatory constraint belongs in `constraints`
or in a required section. A pointer alone is not a constraint.

Selective legacy entries use the same index, plus `legacy:true` and required
`active_source` evidence of the current pointer/approval. Both original constraint
and current-status ranges must match. Ambiguous current status cannot be guessed
from a date. A changed range invalidates the curated entry until reviewed again;
unrelated history outside those ranges does not. This sidecar is a selected
lookup representation, not a new approval or full migration. Keep active-source
evidence current when superseding; the helper cannot infer meaning from arbitrary
new prose elsewhere in a legacy ledger. Preserve legacy S constraints.

`registry.index.json` has `schema:1,entries:[...]`. Each entry is
`{key,status:"N/A"}` or `{key,status:"active",location,contract,constraints,
decisions:[keys],source?:reference}`. Only current reusable contracts/constraints
are emitted; arbitrary history fields are ignored. Decision IDs referenced by
plan and registry occur once in a packet. HANDOFF is never an input source.

`decision-get --key K` works without state or plan, including planning/legacy
cycles. An item is at most 1KB by default; larger items return `overflow` and
`required_sections`. `--section record[@N]` reads decision metadata. Mandatory
details always use canonical `--section detail:<name>[@N]` selectors; names such
as `record` and `sections` remain valid detail names without alias collisions.
The response’s `section` is the canonical selector to use for later pages.
Unambiguous plain detail-name aliases remain supported. Use the advertised selectors
for later pages. Follow non-null `next_section` for remaining required selectors
(`sections@N`); none are optional. `--domain theme` lists at most 20 matching keys. Unknown,
ambiguous, proposed, superseded, and source_changed are distinct errors; never
fall back to reading the whole ledger.

## Context, receipts, and independent verification

`context [--record ID] [--section NAME] [--context-id ID]
[--audience implementer|verifier] [--remember]` validates linked state/contracts/inputs.
Without context-id it creates a new identity and returns it. A new host context
must use a new ID. Same-context reuse may supply the existing ID. Each new-context response includes selected content, required detail selectors, and receipt objects.
In the same context and audience, previously acknowledged decision/registry/detail
sections with matching names, content hashes and plan identity are replaced by
`reused_sections` pointers, including across records. Changed content and new
contexts always receive bodies again. Explicit section requests always return bodies.
Packets are at most 12KB UTF-8. Oversized packets contain selectors only; use
explicit section calls. Large sections use `section@1`, `section@2`, etc.; the
returned JSON fragments reconstruct the serialized section and never drop text.
Chunk budgets include fragment escaping in the outer JSON response, so quotes,
backslashes and control characters remain readable through the same selectors.
Decision bodies over 1KB and mandatory details always require explicit reads.
Selector lists paginate with `next_section:sections@N`; follow every page before
dispatch. Context lists contain at most 24 selectors; decision-get overflow lists
contain at most 3, keeping their default response within 1KB.

For the normal host path, use `context --remember`: it saves only the sections
actually returned in that packet under the writer lock and returns the updated
revision, without asking the agent to copy receipt JSON. Required detail/overflow
selectors still need their own `--remember` reads; an overflow routing response
acknowledges no content. The trusted host must deliver the output to that context;
if delivery is lost, use a new context ID or explicit section reads. This option
does not claim to prove cognition. Without that option, after reading the actual
output, store all returned receipts together using:
`{"op":"read","receipts":[...receipt objects...]}`. Receipts bind record,
context ID, audience, plan digest, section, and current content hash. The helper
recomputes them before saving. Dispatch requires matching receipts for every
contract, decision, registry, and detail section, and a state read. A new context
cannot use an old context's receipts. Receipts are acknowledgments by a trusted
caller, not proof of human cognition; never submit fabricated reads.

Every full `ok` packet (and its overflow routing response, but not an explicit
section fetch) also carries `notes`, an informational object outside sections,
receipts and drift: reading it is not acknowledged, and changing it never blocks
an in-flight record. `notes.forwarded` lists lines in `.wellbegun/deferred.md`
and `rule-candidates.md` whose last `→ <ID>` naming a plan record names this
record (arrows in prose, such as `src→worker`, are ignored), each
`{file,line,to,done}`; `done` means the line contains `✓ <record ID>`.
A fresh record that is not yet verified also gets `notes.review_items`:
`[{record,files}]` for verified fresh records whose target files changed after
their acceptance, or since a later fresh record last accepted them with a
verifier (a checks-only recheck does not count). A whole-run packet adds `notes.open_forwards` (every other
forward line without its `✓`), `notes.rechecks` (`[{record,reason}]` for current
results accepted by a checks-only recheck) and `notes.screenshot_reviews`
(`[{record,command,files}]` for phase checks whose command starts with
`screenshot review:`). Lists hold at most 50 items and all notes at most 6000
bytes, trimmed in the order `review_items`, `screenshot_reviews`, `rechecks`,
`open_forwards`, `forwarded`. A truncated list adds `<name>_more` with the
dropped count; a truncated forward list also adds `<name>_hint`, telling the
reader to read the `→` lines in both files directly. A target
ID is ASCII letters, digits, `_.-` and ends with a letter, digit or `_`, so a
sentence period after it is ignored.

Verifier packets contain contract, target identity, execution location, command
facts and reproducible unresolved findings. They omit implementer reports,
canonical evidence bodies, and prior verdict narratives. An independent session
must read with audience verifier. Context IDs support enforcing separate sessions;
the helper cannot attest host isolation. Same-context self-review is not fresh.

## State writes

`transition --expected-revision N --input FILE` accepts a JSON operation.
Use `--input -` to read JSON from stdin without creating a temporary input file. Every
successful write increments revision once, including receipt/checkpoint writes.
Initialization is `{"op":"init","cycle":"cycle-1","mode":"companion"}`
(or autonomous), requires absent state and expected revision 0. Do not initialize
over a legacy in-progress cycle; finish that cycle in its existing format.
Initialization rejects existing run/HANDOFF/pending artifacts and incomplete archives.

Schema 2 state stores cycle/revision/plan_digest/mode/cursor, opt-in
`handoff_requested` boolean, record map, stable
scope rounds, findings, read receipts, and minimal immutable evidence pointers.
Each record stores status/scope/contract digest, target
content fingerprints, effective selected-input digest, actor/workspace/current
context identity, every implementing context ID, round, finding IDs,
next_action, stop_reason/resume_status, pending pointer, evidence IDs and verifier
context IDs. Missing agent is null; no Git identifier is required. No logs or
round narratives are stored. One record may be active. Cursor is active record,
otherwise first runnable queued record; unresolved stopped records remain blockers.
Only all verified with no unresolved finding permits `complete`.

`op:set` requires record and status. Allowed transitions:
step queued→implementing→checking→verified; gate/phase/whole-run queued→checking;
checking→fixing→checking; active→stopped→saved resume_status. A basic phase
starts and completes with implementer reads and needs no verifier.

Starting needs `context_id`, `actor` (string/null), `workspace` (absolute project
root), and `target` (nonempty project-relative file paths, at least one existing).
Missing paths in a snapshot are represented by null, detecting later creation or
deletion. Callers declare the relevant source/test/config/dependency input closure;
the helper does not discover arbitrary undeclared dependencies.

For a basic example: `context --remember`; set implementing with start fields;
then `op:complete-basic,record,checks:[...]` (and `target:[...]` after edits).
This atomically applies the normal checking and verified validations, using the
current implementing context by default. A runtime-created `recheck_required`
stop with saved checking state also uses this direct path. It also accepts existing reuse facts.
No extra verifier, result-input file, or separate checking write is needed.
Start is still explicit, so ownership and pending checks precede code edits.
The explicit set-checking/set-verified path remains supported. A check requires `command`,
`files`, `exit_status`, nonempty `environment` identity object,
`environment_known` boolean, `external_state` boolean, and `covers` clause IDs.
The helper fingerprints files and runtime Python/platform. Required commands and
all completion clauses must be covered by successful checks. At dispatch, entry
to checking, and completion, every transitive prerequisite/gate must be verified
with current selected-contract fingerprints. A verified record is not reopened by
later changes to its target files, check inputs or runtime: the record that made
the change proves it with its own checks, and a verified fresh record whose
target changed is listed in `notes.review_items` for the next fresh review.
Its old check facts become `reusable:false`; they cannot be reused as current
successful command results. A record that is not yet verified still drifts on
its own target. Known drift rejects the transition before state/evidence success
is saved; reconcile is the explicit invalidation path.
A complete cursor is validated against all current record input/evidence identities.
Command execution
and declared environment facts are trusted caller reports, not sandbox attestations.

Fresh checking additionally needs `verifier_context_id` with all verifier reads.
It must differ from every context that implemented or fixed this scope or a
predecessor, including gate/phase/whole-run repairs and contexts used after
resume, and from earlier verification
rounds. Starting/resuming implementation or fixing records the current writer;
when a new fixer checkpoints target changes or enters checking, pass its actual
`context_id` with its implementer reads. Never use a previous session’s identity.
Gate checking uses the independent verifier as its initial context. Completion
uses verifier `context_id` and `verdict:{status:"ACCEPT",independent:true,
context_id:...}`. Without a verifier the record stops; basic needs no verdict.

A whole-run with more than one perspective runs one verifier per perspective in
one round. Entering checking passes `verifier_context_ids:{perspective:ID}` for
exactly the perspectives not yet accepted in this scope (all of them at first);
each ID is new, distinct, independent and has verifier reads. Optional
`rerun_perspectives:[...]` reopens accepted perspectives, e.g. when a fix changed
contract-visible behavior they cover. The round counts once. Completion passes
`verdicts:{perspective:{status:"ACCEPT",independent:true,context_id}}` for every
verifier of the round; with earlier accepted perspectives they must cover all.
Failure passes ACCEPT verdicts for perspectives that passed, plus `findings` whose
IDs start with a rejecting perspective (`goal-`, `abuse-`, `money-`) and/or
`recheck_perspectives:[...]` for accepted perspectives that must look again after
a fix made during this review; at least one of the two is required. The next
round then needs verifiers only for those perspectives. A stopped in-flight round
resumes with the same verifiers; replacing any starts a new counted round. A
whole-run round started or accepted with a single verifier before 0.8.0 finishes
or stays valid on the single path.

After a contract change, a fresh record with an earlier verified result holding a
full independent ACCEPT (every perspective, for a parallel whole-run; failed
rounds and earlier rechecks do not count) and no unresolved finding may enter
checking from queued or stopped with
`recheck_reason` (one line: why contract-visible behavior did not change). It
needs implementer reads and checks only, no verifier or verdict. The result
stores `recheck_reason`, and the whole-run packet lists it in `notes.rechecks`.
If contract-visible behavior changed, use a verifier round instead.

Failure sets fixing with `findings:[{id,clause,reproduction}]` and any check facts.
The same unresolved violation keeps its stable ID. Initial checking counts as
round 1. At the scope's limit (default 3) failure stays stopped/unresolved. Resolving needs explicit
`resolved_findings:[IDs]` alongside passing evidence. Extra rounds require
`op:approve-rounds,scope_id,additional,approval` with the actual user approval.
The helper cannot itself establish user authorization.
After a verified scope is invalidated by selected-input drift (including drift
propagated from a prerequisite),
its total round count is retained and its limit is extended by the scope's `allowance` (default 3)
for the new failure episode. Reconcile during implementing/fixing/stopped never
refreshes this allowance, and unresolved findings cannot reset it. Plan wording
or record renaming alone does not extend the limit. Successful
iterations therefore do not exhaust a failure cap merely through normal progress.
A contract may set `round_limit` to `2` or `3` (default `3`). The value fixes
the scope's `limit` and `allowance` when the scope is created, at init or at an
approved new scope in replan. Changing `round_limit` on an existing scope never
alters its limit; use `op:approve-rounds` to add rounds. State files without
`allowance` read it as `3`.

`checks` can be replaced/supplemented by `reuse:[{evidence:ID,covers:[clause IDs]}],environment:{...}`.
Only previously state-referenced successful results with matching commands,
actual input hashes, declared environment, and runtime identity are reusable.
`covers` explicitly maps command facts to current completion clauses; facts can
be reused across step/gate/phase/whole-run contracts. Prior verdicts never replace
a new scope’s independent judgment. The verifier must differ from this scope and
all predecessor implementers; only the current round’s assigned verifier may
ACCEPT. External-state-dependent or unidentified environments cannot be reused. Dirty
HEAD alone is never target identity. Evidence files are immutable content-addressed
JSON; orphan files are never adopted as success. Each result records scope,
contract, target, round, checks, verdict and finding IDs.

## Checkpoint, drift, and recovery

`op:checkpoint,record,reason` records a boundary. Active work may supply refreshed
`target` paths and `next_action` after expected edits. `op:set,status:stopped`
requires reason and preserves resume status; optional `pending` points to an
existing question JSON under pending/. Resume verifies workspace, target and
current reads. A stopped in-flight fresh round may resume in its existing host
context. If that context was lost, a new independent `verifier_context_id` with
new verifier reads starts an explicitly counted replacement round; the former
verifier can no longer ACCEPT. The round cap still applies, and replacement at
the cap remains stopped pending explicit extra-round approval. No code rollback
or commit replay occurs.

An answered question contains `question`, nonempty `answer`, and `decision_key`.
Its question body must match the original pending question digest.
When mailbox content differs from the saved pointer, dispatch reports
pending_mismatch. `op:resolve-pending,record,decision_key` checks the actual answer
and active approved decision, stores immutable answer evidence, saves cleared
pending state, then removes that question. Resume is a separate set transition.
Lost/mismatched mailbox files are never guessed answered. Any pending pointer or
mailbox file blocks implementation dispatch, checking and completion, regardless
of the current record. An unreferenced mailbox file is a pending_mismatch requiring
comparison with actual answer/decision evidence, not permission to ignore it.

Target drift of a record that is not verified, plan-contract drift, or effective
selected decision/registry drift blocks context/dispatch. Each started record and its completion evidence preserve
an `input_digest` of selected current decision IDs/bodies, registry contracts,
source fingerprints and required detail content. Supersede or selected constraint
changes invalidate that record and dependent gates/consumers, even when plan text
and source code did not change. Unrelated ledger history is excluded. Source
references that no longer match first require selective mapping review; then
reconcile provides the recovery path. `op:reconcile,reason`
compares current plan and snapshots, invalidates affected records and all dependent
gates/consumers, and preserves evidence and stable finding rounds. Contract/state
reads are cleared; same-context selected-section receipts survive, but only
matching current hashes and plan identity can be reused.

For target drift of unverified work with unchanged plan record and selected
constraints, already started work retains its target paths, execution context and
progress. An active record becomes a recheck-required stop with its original
implementing/checking/fixing resume state; verified records are not reopened.
Read current inputs and resume it from its saved state. A checkpoint’s concrete
`next_action` survives this recheck, prerequisite invalidation, a normal user stop, pending resolution and explicit resume. Blocker
instructions belong to `stop_reason`/`resume_status`; they do not overwrite that
continuation. Checkpoint evidence records the action, and invalidation evidence
retains the prior action. An explicit new `next_action` replaces it; entering a
new checking/completion stage updates the normal action. Shared-file additions are not assumed safe: the record that
changed the file runs its checks over it, and actual failures create findings
and block its completion. Fresh checks exclude all known writers of the current target,
including downstream consumers who touched that same file. No semantic change
classifier is used. Contract or selected-constraint changes still return the
directly changed work to queued; never-started records also remain queued. Already-stopped records remain stopped
with their original stop reason, saved resume status and pending pointer. Their
current source/selected-input identities are refreshed for explicit resumption,
while current success and in-flight verification are invalidated. Reconcile never
answers a question or releases a stop. A pending answer can still be recorded with
resolve-pending even when predecessor success was invalidated; after resolution,
restore prerequisites, read current inputs and explicitly resume the saved state.
Resuming checking starts a newly counted round after such invalidation.
Renames with the same scope retain rounds. New scopes require
`approved_new_scopes:[...],approval`; old unresolved findings remain blockers unless
explicitly excluded using `finding_dispositions:{ID:"excluded"}` with approval.
Exclusion is recorded as exclusion, not verified success.

Writes hold `.state.lock`, compare expected revision, write immutable evidence
first, then fsync/atomic-replace state. A crash may leave orphan evidence or a
lock requiring manual diagnosis. Never delete an active writer's lock. Corrupt
state blocks dispatch; diagnose using preserved code/evidence, not guessed status.
run.md is generated after state save. HANDOFF is opt-in: use
`render --handoff [--expected-revision N]`, or explicitly create HANDOFF.md before
rendering. The first request is persisted as `handoff_requested:true` under the
writer lock and increments state revision once; the response returns that revision.
An optional expected revision rejects stale preference changes. Subsequent plain
`render` calls and transition rendering regenerate a requested HANDOFF after loss
or generation failure. Request persistence precedes file generation. Without a
request, plain render and transitions create no HANDOFF. These files are derived
indexes, never bootstrap authority. Git and
multiple artifact files are not one atomic transaction.

## Cycle archive

`transition --expected-revision N --input archive.json`, where archive.json is
`{"op":"archive"}`, requires cursor complete, valid current checks, no stopped
record and no pending mailbox files. It archives `plan.md`, `state.json`,
`run.md`, optional existing `HANDOFF.md`, and all cycle `evidence/` under
`cycles/<cycle>/`. Project decisions/indexes/registries remain in place.
An existing destination is never overwritten. New-cycle initialization starts
at revision 0 after archive and preparation of an approved new plan.

Before copying, `.archive.json` durably records cycle, existing state revision and
exact file hashes. Files copy into a private staging directory, are verified, and
the directory is renamed to its immutable destination. Current files are removed
only if their hashes still match. This is a resumable multi-file operation, not
an atomic transaction. If interrupted, dispatch/init/render are blocked; reissue
`op:archive` with the manifest revision. Missing current files can be recovered
from the validated archive. Source/destination mismatch returns archive_drift for
explicit diagnosis, preserving changed files. Success reports the archived state
revision; moving a snapshot does not invent another execution revision. Do not
delete a partial archive marker to bypass validation.
