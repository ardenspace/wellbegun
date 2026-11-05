You are an independent acceptance verifier. You judge one implementation of a small multiplayer web game against its product idea document. You did not write it and have no stake in it.

## Inputs
- Implementation (read-only): /Users/arden/code/kongkong
- The contract is ONE document: /Users/arden/code/kongkong-beginonly/docs/begin.md (Korean product idea). Read it first. Judge only against it, plus ordinary expectations for a public web product that takes real money.
- Do NOT read: EXPERIMENT_LOG.md, anything under .wellbegun/, docs/design/ (if present), git history beyond `git log --oneline | head`, or any other folder under /Users/arden/code except /Users/arden/code/kongkong and the begin.md above. The implementation's own README, docs (other than those excluded), code and tests are fine. Other implementations of the same idea exist; do not look at them.

## What to judge
1. Run the project's own full test/check commands once (find them in package.json/README) and record exit status and counts.
2. Clause table. For each item give PASS / FAIL / PARTIAL / NOT-CHECKABLE-HERE with evidence you observed on the running local stack (login and payment mocked; start the servers yourself):
   - J1 a shared link opens at the jang entrance (slush machine, cup-tteokbokki shop) and you can walk in and find the friend who sent it
   - J2 timing-based higher jumps and mid-air poses/tricks
   - J3 a friend's hard landing launches you (rebound), visible to both
   - J4 anyone inside can re-share a link to this jang
   - J5 the shop on the way in: coins buy slush 300원 / cup-tteokbokki 500원, giving cosmetic rewards; riding works without buying
   - J6 multiple trampolines per jang, each with a capacity; a full one sends you to the next
   - J7 a visitor with no link goes to a jang that has people; full jang → a new one opens; alone you can still do everything
   - J8 phone (touch) rides the same as PC
   - J9 auto names like "떡볶이마니아 37"; no chat, speech bubbles, preset reactions, nickname entry, gacha, report/block
   - J10 riding needs no login; login only when charging; bought cosmetics persist on the account and return after re-login; guests start fresh
   - J11 charge model: real money buys 100원 coins (e.g. 1,000원 → 10 coins); coins are spent in the shop
   - F1 the sender already left → you just ride alone there; F2 friend's trampoline full → ride the next one, can move back when a seat frees; F3 the friend's jang is full → "꽉 찼어요" notice and a new jang
   - S1 the success criterion (a link shared by someone who arrived by link, then someone arriving by that link rides together) can actually be measured from what the system records
   - T1 tone: playful round cartoon, 90s stationery-shop scenery. Take screenshots at PC and phone size, look at them, and describe what you see honestly.
3. Defect hunt (most important): find real defects the existing tests miss. Focus on server authority for coins/cosmetics/equip (a client must not be able to mint coins, buy without paying, or wear what it doesn't own), auth/session, the realtime relay, capacity and assignment, crash/abuse paths an anonymous user can reach, and the failure branches. Each defect needs: the begin.md clause or general expectation violated, a concrete reproduction you actually ran (command/script and output), and severity (high = money/security/journey broken, medium = a clause wrong in a reachable case, low = edge case). Put unconfirmed suspicions in a separate list.
4. Launch readiness (judgment, no pass/fail): what would have to change before this could be put on the public internet for the shared-link scenario in begin.md (hosting, scale of one viral link, real Kakao/payment integration path, cost). Keep it to a short list.

## Rules
- Do not modify files under /Users/arden/code/kongkong. Put probes in /private/tmp/claude-501/-Users-arden-code-kongkong/c2a1d656-298c-4c2d-9074-68cf7e197e82/scratchpad/eval2-A (create it).
- For your own servers use only ports 5193, 5194, 8817; check each with `lsof -nP -iTCP:<port> -sTCP:LISTEN` first; stop only processes you started. Never use 8080, 8787, 8000, 8081, 5000, 7000. The repo's own fixed ports used by its test commands are fine, but run its test commands only once.
- No real keys, no deploys, no cloud resources, no network calls to Kakao/PortOne/payment providers.
- Aim to finish within about 40 minutes.

## Output
You cannot write report files; reply with the full report as text: test results, clause table, confirmed defects (one line each with severity, then details), number of unconfirmed suspicions with one line each, launch-readiness list, and roughly how long and how many tool calls you used.
