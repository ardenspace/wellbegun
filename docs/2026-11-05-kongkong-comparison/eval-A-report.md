# Eval A (kongkong wellbegun @d2f3941) — saved from verifier hand-back
check: exit 0; vitest 282 (25 files); Playwright 11 (Pixel 7 project)
Coverage gap: login/topup/shop e2e mock /api/auth,/api/pay,/api/shop + fakeJang; no automated real-worker topup->buy->equip->seen test (verifier ran it by hand: OK)
Clauses: journey PASS(local), failure PASS, real-device N/C, cost-alert N/C, cost-table PASS (DO page fetched; others from knowledge), non-goals PASS, check-green PASS
Held: kakao id mapping, forged cookie 401, complete before PAID refused, foreign payment 403, amount mismatch, 3 concurrent completes once, re-complete after cancel, overdraft race, dup buy/unowned/wrong slot equip refused, smuggled cosmetics/chat dropped, impacts same-trampoline only, spread query 2-hop =1.
D1 medium: lobby shards=4 by visitor id vs jang id -> no-link visitors miss existing riders (~3/4). p3_lobby.mjs
D2 medium: 64 never-join sockets lock a jang (count vs MAX_PLAYERS 64, no idle timeout); client treats 1013 as offline, retries forever, no full notice. p2_jang.mjs
D3 low: full-trampoline tap -> 42 move msgs in 4s (billed). trfull.mjs
D4 low: equip reconnects -> new player id + nickname each equip; full-jang rejoin risk unreproduced.
Suspicions (7): missing storeId accepted; lobby hold spam; rejoin race; stale ?from after full move; client-asserted analytics ids; no server logout/revocation (30d cookie); no rate limit on poses/impacts.
Effort: ~35 min, ~40 tool calls.
