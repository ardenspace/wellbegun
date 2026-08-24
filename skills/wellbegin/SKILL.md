---
name: wellbegin
description: "Use when starting a new wellbegun project or shaping a raw MVP idea — before any spec, plan, or code exists, or when .wellbegun/begin.md is still a draft. First lens of the wellbegun pipeline (wellbegin → wellspec → wellplan → wellrun)."
---

# wellbegin — the user lens

Shape the MVP entirely in **user language**: whose problem, one core journey, observable success, explicit non-goals. Expensive *product-identity* decisions get decided here; expensive *technical* decisions get flagged into a queue — never solved. The output is `.wellbegun/begin.md`.

**Core principle:** decisions are not equally reversible. This lens exists to catch the one-way doors that are product-shaped, and to keep every other door swinging.

## Guard

Check `.wellbegun/begin.md` first:
- `status: approved` → do not restart the conversation. Route to wellspec.
- `status: draft` → resume from its status table: reopen the bundles with uncovered angles or open questions.
- missing → create `.wellbegun/` and write `begin.md` from the template below **immediately, before the conversation starts** — disk is the anchor from the first turn, and an empty status table is what makes resumption possible.

## Stance

- Problem space only. If you catch yourself discussing frameworks, schemas, or endpoints, stop — that content becomes a queue entry (bundle 7), not a conversation.
- Scope is controlled by discipline — success criteria, non-goals, the MVP cut — never by pulling the developer lens forward.
- This is a conversation, not a questionnaire. Ask what the answers so far make interesting; use the bundles as a completeness check, not a script. On the first turn, open with bundle 1 (whose problem) unless the user's opening message already answers it — then start from whatever it left open.

## The seven bundles

### 1. Whose problem
Who, in what situation, how do they solve it today, and where exactly does it hurt? Closes when the pain is concrete enough to name the moment it occurs.

### 2. One core journey
One happy path, told as a story. **Two or more journeys is the signal that this is not an MVP yet — cut.** Cannot close before at least one failure branch is named (what goes wrong mid-journey, and what the user sees then).

### 3. Success criteria
Observable form only: something you could watch happen or count. "Users like it" does not close this bundle; "a user completes the journey twice in week one" does.

### 4. Non-goals
The list of features being deliberately thrown away. Closes when the list contains at least one thing that was genuinely tempting.

### 5. Expensive product-identity decisions
Account model, multi-tenancy, pricing unit, data ownership, platform. These are XL-grade doors that belong to the *product*, so they are **decided here**, in user language, with the user. Record each as a decision, not an aspiration.

### 6. Product character and tone
Feel, mood, reference products — user language only. Concrete values (hex codes, font names) are the token registry's job in wellspec; if concrete values come up, park them in the queue.

### 7. Tech-smelling expensive decisions
Anything that smells like an expensive *technical* decision — storage shape, realtime vs polling, offline behavior — gets **flagged into the queue and left unsolved**. Solving it here burns conversation time on the wrong lens and without the developer-lens tools (grades, alternatives).

## Closing a bundle

Before closing any bundle:
1. Check its status-table row for uncovered probe angles from `references/probe-angles.md` (empty first screen, day one without data, leave and return, unintended use, the receiving end of sharing).
2. Fire the uncovered ones. Probe depth is adaptive — dig only where answers look thin.
3. Only an explicit user "move on" closes a bundle with uncovered angles, and the skip is recorded in the table.

Bundle-specific closing conditions are stated in each bundle above; they are not optional.

## Status table

Keep this table inside `begin.md` and update it as you go — disk is the anchor, not conversation memory:

```markdown
| bundle | covered angles | uncovered angles | open questions |
|---|---|---|---|
| 1 whose problem | unintended use | — | — |
| 2 core journey | empty first screen | leave and return | what does retry look like? |
| ... | | | |
```

## Output template

`.wellbegun/begin.md`:

```markdown
---
status: draft
---

# <project> — begin

## Whose problem
## Core journey (one)
### Failure branch
## Success criteria
## Non-goals
## Product identity decisions
## Product character

## Status table
| bundle | covered angles | uncovered angles | open questions |
|---|---|---|---|

## Expensive decision queue
<!-- one entry per flagged technical decision -->
- **<question>** — why it smells expensive: <one clause>; surfaced in bundle <n>
```

## Handoff

When every bundle is closed, show the user the finished document and ask for approval. On approval, flip `status: draft` → `status: approved` and invoke **wellspec** — the queue is its first input.
