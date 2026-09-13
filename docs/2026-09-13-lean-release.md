# Lean execution local release — 2026-09-13

## Release scope

Packages the approved revision 2 implementation and §5 user supplement, accepted
by G1 round 7 and final review round 2. See the [validation record](2026-09-12-lean-execution-validation.md).
Includes runtime, synthetic fixtures/tests, five skills, relevant references,
validation wiring, README, approved spec/plan and validation history. No full
temporary experiment or dogfood project is copied into the repository.

The four pre-existing untracked proposal/review/feedback documents are excluded:
`2026-09-12-bounded-context-deterministic-handoff-spec.md`,
`2026-09-12-bounded-context-spec-review.md`,
`2026-09-12-dogfood-context-handoff-review.md`,
`2026-09-12-lean-wellrun-dogfood-feedback.md`.
References to these in the approved spec are historical local provenance; those
documents are not part of this release. No unrelated changes are reverted/stashed.

## Changes

- Basic completion and implementer reuse within verified boundaries; independent
  gates block consumers, preserving unresolved findings and round caps.
- Selected contract/decision/registry reads, schema 2 state, checkpoint recovery,
  result reuse, rendering and archive. Legacy cycles retain their execution format.
- Codex local installation identifier: `0.5.0+codex.20260913032044`.
  The plugin-creator cachebuster helper preserves the `0.5.0` base version;
  Claude manifest remains `0.5.0`. No remote version/publication is claimed.
- Runtime SHA-256:
  `9ec9821bb6be96d2055b7faa02d8f1c0bdcbd865659d9eb4d9425bd6436de51a`.

## Reused evidence

Python 3.12.12, executable `/opt/homebrew/opt/python@3.12/bin/python3.12`,
macOS-26.6.2-arm64-arm-64bit match the C1 environment. 19/20 C1 input hashes
match; README alone differs by the recorded post-acceptance completion update.
The hooks README and four template hashes additionally match the pre-G1-round-7
manifest. The registry README matches the newer C1 manifest. Runtime, tests,
fixtures and five skills are unchanged. Reuse the successful 88 tests and
independent ACCEPTs; do not rerun the suite/G1 for packaging.

Original evidence remains in `/private/tmp` (ephemeral, not release dependencies):

| File | SHA-256 |
|---|---|
| `wellbegun-c1-checks.json` | `a8e12d65e9357ca85c7450ba56793b227848e4b14a2d1080622bb22c63728896` |
| `wellbegun-lean-validation/controlled-final-review-facts.json` | `4f3e37cb70df152a3268d696102f85a908d8b9bf8d01ba69d66527926311ea66` |
| `wellbegun-lean-validation/final-review-round2-cli-final.txt` | `5106b5e340253759dcee86aafef67847c4efb489dfc0109c37961c7ea3c3c258` |

The repository validation record retains the measured results, verdict history
and limitations if temporary raw evidence is later removed.

## Packaging checks

After the cachebuster change, the existing `scripts/validate.sh` structural portion
was executed separately with its original script path and final `exit $fail`:
PASS. `git diff --check`: PASS. An initial stdin invocation resolved the script
directory incorrectly and failed; the corrected invocation above passed.
The external plugin-creator validator could not start because its Python lacks
PyYAML; this is not a plugin runtime dependency. Repository checks are the fallback.

## Limits

Measured document input reductions apply to the controlled step observations;
they do not guarantee general speed, token or monetary savings. Seven broader
Flutter failures on baseline-identical KBO code remain unresolved and are not
reported green. KBO source and other Herdr sessions are outside this operation.
Installation smoke tests validate the local CLI protocol, not new independent
agent judgments or a fresh model's end-to-end skill execution.

## Installation and smoke result

Implementation commit: `b8e71b0` (`feat: release lean execution and bounded context runtime`).
The pre-existing `wellbegun` marketplace used Git source
`https://github.com/ardenspace/wellbegun.git`. CLI add rejected changing an existing
name's source, so `codex plugin marketplace remove wellbegun` was followed by
`codex plugin marketplace add /Users/arden/Documents/dev/wellbegun` and
`codex plugin add wellbegun@wellbegun`. All three completed successfully.
Only that marketplace registration was replaced; the original source URL above
can be re-registered through the same CLI if needed. No push or remote publish.

Installed path:
`/Users/arden/.codex/plugins/cache/wellbegun/wellbegun/0.5.0+codex.20260913032044`.
All 29 payload files match the release source byte-for-byte (excluding generated
`__pycache__`). Payload content identifier:
`bcea2a4a2a5df8deea197eeb4a009f201f974adb8906077f02dfadfb03b32d65`.
This is SHA-256 of compact, sorted-key JSON mapping relative file paths to their
SHA-256 values. Runtime retains the accepted hash above.

`python3 /private/tmp/wellbegun-installed-smoke.py`: PASS, one installed lifecycle
test, 1.249 seconds. It uses the installed fixtures, skill shell examples and
runtime, derives the plugin root from the installed wellrun SKILL.md, and runs
from an unrelated cwd against a temporary project whose path contains spaces.
The existing lifecycle case verifies:

- decision lookup before state initialization, selected context and N/A registry;
- basic completion without a verifier, consumer rejection before the gate;
- synthetic gate protocol acceptance and reuse of valid command facts;
- checkpoint, pending question, archive rejection while unresolved, answer
  resolution and resume with next action preserved;
- derived document regeneration, completion, archive preserving decisions, and
  the next cycle's packet excluding previous execution context.

Compact temporary observations: `/private/tmp/wellbegun-installed-smoke-result.json`.
Fixture projects were cleaned by the existing harness. No new permanent tests
were added, and the full suite/G1/Flutter tests were not repeated. The external
validator's PyYAML limitation above remains; the official CLI accepted and
installed the package and the repository structural check passed.

Use a new Codex thread to load the updated skill instructions. Existing threads
may retain the previously loaded 0.5.0 skill text; installed runtime smoke success
does not claim to reload those contexts or change another session.
