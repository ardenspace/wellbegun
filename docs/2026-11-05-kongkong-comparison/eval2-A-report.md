# Eval2 A (kongkong @ac8daf0), begin.md-only verifier
tests: npm run check exit 0; vitest 282; playwright 11
Clauses: J1 PARTIAL (friend not identified; always trampoline 1); J2-J4 PASS; J5 PASS api / PARTIAL content (no buyable poses); J6 PASS; J7 FAIL (shards); J8 PASS; J9 PASS; J10 PARTIAL (own cosmetics not shown on return); J11 PASS; F1-F3 PASS; S1 PASS weak (forgeable); T1 PASS
D1 high: 63 idle sockets lock jang indefinitely, client loops offline
D2 med-high: lobby shards scatter no-link visitors (4/12 found people)
D3 medium: impact/pose relay no rate limit/validation; launched to 10.43 m
D4 medium: returning logged-in player's own rider shows no cosmetics until shop opened
D5 medium: Transaction.Cancelled webhook keeps coins and items (refund not handled)
D6 low-med: lobby assign spam
D7 low: logout doesn't revoke session (30d)
Suspicions 4: equip rejoin new id; ?from kept in address bar; storeId missing accepted; paymentId craftable without prepare
Effort ~40 min, ~40 tool calls.
