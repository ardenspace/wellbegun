---
name: wellrun
description: "Use when .wellbegun/plan.md has status: approved and execution should start or continue — including resuming after a stop, or when .wellbegun/pending/ is non-empty. Final lens of the wellbegun pipeline (wellbegin → wellspec → wellplan → wellrun)."
---

# wellrun — the conductor

Execute the approved plan with subagents: implementers build against step contracts, fresh-eyes verifiers judge against those same contracts — never against the implementer's story. Verification intensity follows reversal cost.

**Core principle:** blind spots travel through shared context. So the context is what gets isolated — a verifier who read the implementer's narrative inherits the implementer's blind spots and stops being a verifier.

## Conductor charter

While a run is active, **this skill is the conductor**. The main session reads the plan, dispatches steps in order, receives results, and never writes code itself.

Superpowers, if present, is a toolbox for the *implementation technique layer only*: implementer subagents may use its test-driven-development, systematic-debugging, and verification-before-completion skills. The planning-layer skills from Superpowers (its brainstorming and writing-plans skills) are **never invoked during a run** — the pipeline already did that work, and double-running a stage corrupts it.

## Guard

- `.wellbegun/plan.md` missing or not `status: approved` → stop and route to wellplan.
- `.wellbegun/pending/` non-empty → **the run is stopped, awaiting answers.** Process the mailbox first: for each pending file, get the user's answer, append a mini-ADR line to `.wellbegun/decisions.md`, then delete the pending file. The file's existence is the state flag — an empty `pending/` means nothing is owed. Only after the mailbox is empty, re-run the start briefing and resume at the step `run.md` marks as stopped.

## Running state — `.wellbegun/run.md`

The conductor's durable memory. Created at the first briefing, updated after **every** step transition, so a new session (or a return hours later) can resume from disk alone:

```markdown
---
mode: companion
---
- [x] 1.1 verified (basic)
- [x] 1.2 verified (fresh)
- [>] 1.3 stopped → pending/auth-model.md
- [ ] 1.4
```

One line per step: `[x]` verified, `[>]` in progress or stopped (with the pending file when stopped), `[ ]` not started.

## Start briefing

Before the first step (and again when resuming):

1. **Enforcement check (rule 1):** confirm phase 1 contains the enforcement-hook installation step from the spec's enforcement plan. Missing → add it now, as a phase 1 step.
2. Announce: "the run stops on L/XL decisions" and show the plan's run-preview table — the steps where a stop is likely.
3. Ask the user to pick a mode:
   - **companion** (default) — stop and ask on L/XL discoveries.
   - **autonomous** (unattended, e.g. overnight) — never stop: take the *most reversible* provisional choice, mark it `provisional` in code and in `decisions.md`, and collect every L/XL decision into an end-of-run report for the user.
4. Create `.wellbegun/run.md` (first briefing) or update it (resume): record the chosen mode in its frontmatter and make sure every plan step has a line.

## Three layers

| layer | context | receives |
|---|---|---|
| Conductor (main session) | the plan + `run.md` | step results, verdicts |
| Implementer subagent | fresh per step | the step contract + the area rosters its item 4 names |
| Verifier subagent (fresh tier) | brand-new, isolated | the contract, the diff, the run commands, the item-4 rosters — **and nothing else** |

"The run commands" means the concrete commands to build, run the app, and execute the contract's boundary tests — the conductor writes them into the dispatch. "The item-4 rosters" are the same registry files the implementer was required to read, so the verifier can judge registry-rule compliance (reuse vs. hardcode) with its own eyes.

The verifier is never given the implementer's narrative, summary, or self-assessment. Not as a convenience, not "for context."

## Execution loop

Serial by default: implement → verify → fix → next step. (Reversal-cost-proportional verification keeps cheap steps fast, so serial costs little.)

The four rules, enforced on every step:

1. **Enforcement check** — done at briefing; hooks must be installed by the end of phase 1 and stay green.
2. **Read the registry first** — the implementer reads the area rosters named in contract item 4 before touching that area.
3. **Common-element rule** — on the roster → reuse it. Not on the roster but shared-shaped → create it in the common folder **and update the roster in the same commit**. "Hardcode now, clean up later" is forbidden — that cleanup is the debt this plugin exists to prevent.
4. **Hidden expensive decisions** — when an implementer hits a decision the spec didn't cover, the roles split: the **implementer** grades it (`references/reversibility-grades.md`). S/M → the implementer decides, records one ADR line, and continues. L/XL → the implementer reports the decision (situation, options it sees) back to the conductor and ends its turn; the **conductor** re-grades, and in companion mode writes the pending file and halts the step. Partial work stays in the working tree; on resume, the conductor dispatches a **fresh** implementer with the same contract plus the recorded decision.

## Verification

- **basic tier:** lint + the contract's boundary tests pass. That's it — spending fresh-eyes effort on an S step inverts the plugin's premise.
- **fresh tier:** a context-isolated verifier with an adversarial charter: *"find the reason this fails."* The verifier runs the contract's boundary tests **and has the authority to write new probe tests of its own** — the contract is the floor, not the ceiling.
- Three verification layers across the run: per-step verification → phase integration verification (do the slices compose?) → whole-run fresh-eyes review before final acceptance.

A failed verification returns the verdict to the conductor; the conductor dispatches a fix (same contract, findings attached) and re-verifies. Findings travel as *facts about the code*, never as the previous implementer's narrative — and they go to the **fixing implementer only**. Re-verification always means a **new** fresh verifier that receives the standard four inputs and nothing about the previous round; a verifier that knows the old findings only checks the old findings.

## Stop UX — the pending mailbox

On an L/XL stop, write `.wellbegun/pending/<slug>.md` so the user can answer from one file even hours later:

```markdown
# Pending decision: <one-line question>

## Situation
<where the run stopped and why this decision surfaced — 3–5 lines>

## Options
1. <option> — reversal grade <S/M/L/XL>, <one-clause tradeoff>
2. <option> — ...

## Recommendation
<option n>, because <one clause>.

## How to answer
Reply with the option number (or your own choice). The answer gets recorded
in decisions.md and this file is deleted; the run resumes at the stopped step.
```

Push notification on stop is the user's choice of channel, wired via the harness's Notification hook — see `references/hooks/README.md`. Documented, never forced.

## Run completion

After the last step passes: run the whole-run fresh-eyes review (layer 3), then report — steps completed, decisions recorded (including provisionals, which the user must revisit), and the state of the enforcement hooks.
