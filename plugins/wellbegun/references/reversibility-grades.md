# Reversibility grades (S/M/L/XL)

Ask: **If the decision introduced or changed here is wrong, what does changing it cost?** Grade reversal cost, not importance or the grade of an existing API being used. Include downstream dependence: a cheap new foundation can become expensive after consumers spread it.

| Grade | Reversal cost | Examples | Handling |
|---|---|---|---|
| S | Minutes, local | Naming, copy, private helper | Decide and continue; no permanent ADR. |
| M | Under a day, a few files, no API/data migration | Internal state, config default | Decide and continue. Record only choices future work needs: external behavior, data/public contracts or meaningful cost/performance constraints. |
| L | A mini-project or coordinated migration | Shared API change, core schema, error contract | Compare alternatives and retain status/rationale. Fresh verification for the change. New unapproved decisions require companion review. |
| XL | Rewrite or user-visible break | Account model, tenancy, pricing, platform, data ownership | Same as L. Product identity belongs in wellbegin. |

Grade proportionately. Reuse approved choices and mode; do not request approval for ordinary work within them. Autonomous provisional choices stay inside granted authority.

## Verification boundaries

Basic work can complete through contract and affected checks with the current agent. Reuse implementers inside a verified boundary. A new shared foundation needs an independent gate before its first consumer even when its producer is S/M; an L/XL fresh review or equivalent earlier phase integration may satisfy it. Gate failure blocks consumers; foundation changes invalidate affected gate results.

Fresh review uses an independent context without implementer or previous verifier narratives. Valid check facts may be reused. Maximum three rounds per verification scope including the initial review; keep stable finding IDs through renames, SHA changes and contract rewording. Cap exhaustion preserves unresolved status in every mode. Only approved new scope starts a new unit; explicitly excluded findings are not passes. See wellrun for evidence, probe and completion rules.

## Decision records

Use `.wellbegun/decisions.md` for meaningful M and all L/XL decisions. New records have a stable semantic **key**, immutable **record ID**, grade and explicit status. Refer to keys from plans and registries, never dates alone. Keep the current entry at most 1KB UTF-8 when possible; preserve mandatory constraints through explicitly required detail sections if needed. Long comparisons, history and failed-round narratives belong behind source pointers, not in current entries.

```markdown
## Active index
| key | record ID |
|---|---|
| timestamps.storage | dec-0001 |

## Records
### dec-0001
- key: timestamps.storage
- grade: M
- status: approved, active
- choice: UTC ISO timestamps
- scope and constraints: stored timestamps include UTC offset; preserve instant on display
- reason: sortable, explicit timezone
- source: <precise file/section for detailed rationale, if any>
```

L/XL records also compare at least two alternatives and preserve their rationale. Proposed or provisional is not approved; do not enter an unapproved proposal as the confirmed active choice. Amend proposal status after actual approval. A replacement gets a new immutable ID, `supersedes: <old-ID>`, and the old record becomes superseded when the replacement takes effect; update the active key pointer in the same edit. Preserve old records and current product identity in begin.md. Do not silently treat date/slug coincidence as identity.

## Selective reading and legacy

Use the installed helper's `decision-get --root <absolute-.wellbegun> --key KEY`
or `--domain DOMAIN` before execution state exists and during legacy cycles.
Schema 2 `context --remember` supplies required entries without repeat receipts.
New decisions must also update `decisions.index.json` (authoritative active
key/ID/status pointers); preserve detailed comparisons in the ledger. For index
fields and selective legacy source proofs, read only “Plan and selected inputs”
in `runtime-contract.md`. A Markdown active table alone is not a helper index.

Read only relevant active entries and required constraint details for ordinary planning, implementation, resume and dispatch. Do not load the whole ledger to summarize it. Missing or ambiguous keys require a narrowed domain/key or source-section search, not a whole-ledger fallback or an assumption of no constraints. Deduplicate by record ID. A fresh context needs the actual applicable constraints; an implementer may reuse unchanged entries by ID and content identity.

Keep legacy history and format intact; wholesale conversion is not a new-cycle prerequisite. Resolve only currently relevant entries through exact source ranges, clear active/supersede evidence and content identity. Preserve necessary legacy S constraints. When a long entry first becomes relevant, separate current constraints from detailed source pointers and reuse that representation until the source changes. Ambiguous current meaning blocks only affected work until clarified. A full ledger audit is a separate user-requested task.
