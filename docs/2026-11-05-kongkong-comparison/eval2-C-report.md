# Eval2 C (kongkong-beginonly @eabfdcb), begin.md-only verifier
tests: tsc 0; vitest 38/38; playwright 7/7 (3.9 min)
Clauses: J1-J9 PASS; J10, J11 PASS (mock); F1 PASS (repo e2e); F2 PASS; F3 PARTIAL (D2); S1 PARTIAL (D3); T1 PARTIAL (tone fits, 90s 문방구 feel only partly there; plain pastel boxes, capsule characters)
D1 high-at-launch: /api/charge mints coins with no payment proof; login by id only = takeover; no server-side payment confirmation seam
D2 medium: overflow arrivals from a full park each get their own empty park
D3 medium: one person with 3 cids trips successReached; no distinct-person record
D4 medium: /api/stats lists live parks; 15 anon sockets fill any park, friend link fails
D5 low-med: no ws heartbeat; frozen clients hold seats forever
D6 low: product "__proto__" -> 500 TypeError leak
D7 low: board/unboard unlimited -> 5000 broadcasts
D8 low: slam forgeable (documented)
Held: buy needs login/coins, unowned look reset, forged pose stripped, malformed frames don't crash.
Suspicions 5: readBody hang >10KB; stale UI after other-tab logout; ref not checked vs p; corrupt db.json crash + full rewrite; address-bar copy undercounts.
Launch: single node + JSON db; needs real db/txn, ws scaling, real payment+webhook, real OAuth+httpOnly session, overflow park, rate limits, metrics.
Effort ~25 min, 20 tool calls.
