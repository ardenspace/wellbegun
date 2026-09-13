# Registry templates

Use a registry only for an active area where code, types, schemas or lint do not already communicate the needed contract. Mark irrelevant areas N/A without creating empty files. CLI and library projects need no UI registries by default.

A registry holds reuse locations, public contracts, mandatory current constraints and stable decision keys. Read only entries relevant to the task, expanding when dependencies warrant. Keep long rationale, failed rounds and change history behind precise source pointers; never hide required constraints there without requiring that section before work.

For schema 2 plans, `registry.index.json` holds only selected current entries:
`{"schema":1,"entries":[{"key":"ui","status":"N/A"}]}` needs no UI file.
An active entry has `key,status,location,contract,constraints,decisions` (stable
decision keys), with an optional fingerprinted source reference. Put its key in
the plan record; `context --remember` then delivers it with deduplicated decisions.
Before state exists, read only the affected existing entry/code section. See
`../selected-inputs.md`; do not initialize or migrate a cycle just for lookup.

Code remains the source of truth. Avoid copying facts already maintained in code. Put an active registry near the code it describes; preserve project-owned instructions when adding relevant entry-reading guidance to AGENTS.md or CLAUDE.md. Do not require full roster or ledger reads.

Elements explicitly planned as shared belong in the common layer from first use. Otherwise keep the first use local and assess promotion on the second actual use. Similar appearance alone does not establish a common contract.

Adapt only relevant templates: design-tokens, frontend-components, backend-common, db-schema. Their sample rows illustrate possible entries, not required project architecture. Use existing enforcement when sufficient; the optional `../hooks/check-registry-sync.sh` checks listed files, not every semantic contract.
