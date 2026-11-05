You are an independent acceptance verifier. You judge one implementation of a small multiplayer web game against its written design. You did not write it and have no stake in it.

## Inputs
- Implementation (read-only): /Users/arden/code/kongkong-noplugin
- Design documents (the contract), read these first: /Users/arden/code/kongkong-noplugin/docs/design/begin.md, spec.md, plan.md, decisions.md. Do not read anything else under kongkong-noplugin unless /Users/arden/code/kongkong-noplugin is that folder.
- Do NOT read process notes: EXPERIMENT_LOG.md, .wellbegun/, docs/ops/*handoff*, git commit messages beyond `git log --oneline | head`. Judge the code, tests, config and docs/ops only. (Another implementation of the same design exists; do not look at it.)

## What to judge
1. The whole-run contract in plan.md (search "whole-run — 전체 완료"). For each clause give PASS / FAIL / NOT-CHECKABLE-HERE with evidence:
   - journey, failure, non-goals, check-green: check locally. A deployed preview is out of scope for this evaluation; judge whether the journey works on the local stack (vite + wrangler dev, Kakao/PortOne mocked) at PC and phone viewport.
   - real-device and the "usage alert is set" half of cost: human-only, mark NOT-CHECKABLE-HERE. Do judge the other half: is the cost table computed from real current Cloudflare pricing, with arithmetic you can reproduce?
2. Defect hunt (most important): find contract violations against spec.md / plan.md step contracts and decisions.md that the existing tests miss. Focus on server authority (money, cosmetics, equip), auth/session, the jang relay and lobby assignment, failure branches, and anything the spec calls out as a risk. Each defect needs: the violated clause (quote it), a concrete reproduction you actually ran (command, request, or script and its output), and severity (high = money/security/journey broken, medium = a contract clause is wrong in a reachable case, low = edge case). Put unconfirmed suspicions in a separate list, clearly marked.

## Rules
- Do not modify files under /Users/arden/code/kongkong-noplugin. Put temporary probes in /private/tmp/claude-501/-Users-arden-code-kongkong/c2a1d656-298c-4c2d-9074-68cf7e197e82/scratchpad/eval-B (create it).
- Run `npm run check` once in /Users/arden/code/kongkong-noplugin and record exit status and counts. If you need your own dev servers for probes, use only ports 5203, 5204, 8827; check each with `lsof -nP -iTCP:<port> -sTCP:LISTEN` first, and stop only the processes you started. Never use ports 8080, 8787, 8000, 8081, 5000, 7000. The repo's own fixed ports for npm run check are fine.
- No real keys, no deploys, no Cloudflare resource creation, no network calls to Kakao/PortOne.
- Time budget: aim to finish within about 40 minutes of work.

## Output
Write the full report in English to /private/tmp/claude-501/-Users-arden-code-kongkong/c2a1d656-298c-4c2d-9074-68cf7e197e82/scratchpad/eval-B/report.md, then reply with: the clause table, the confirmed defect list (one line each with severity), the count of unconfirmed suspicions, the npm run check result, and roughly how long and how many tool calls you used.
