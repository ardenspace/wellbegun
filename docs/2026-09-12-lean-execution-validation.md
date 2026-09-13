---
status: complete
date: 2026-09-13
spec-revision: 2
g1-rounds: 7
g1-additional-rounds-approved: 4
g1-additional-rounds-used: 4
c1: independently-accepted
c2: bounded-controlled-comparison-complete
final-review: round-2-accept
---

# Lean execution 구현·검증 결과

승인된 revision 2와 2026-09-13 사용자 보완에 따른 구현은 **G1 round 7 ACCEPT,
최종 독립 검토 round 2 ACCEPT**를 받았다. C1 연결과 실제 CLI lifecycle을 포함한
88개 로컬 검사가 통과했으며, C2는 같은 host/model·완전한 문서 입력 계측을 갖춘
step 수준 비교를 완료했다. 독립 검토자가 prompt 10개와 reader 출력 50개의 해시/bytes,
시간 산식 및 후보 동일성을 직접 대조했다. 이전 REJECT/finding과 제한된 첫 관측은 보존한다.

최종 판정은 C1, bounded C2 및 전체 구현 완료를 지지한다. 관측된 입력량·호출 수·시간은
아래 결과의 범위에 한하며 일반 속도/비용 개선 보장은 아니다. KBO baseline-identical 코드의
범위 밖 Flutter 실패 7개는 남아 있고 전체 프로젝트 suite를 green으로 주장하지 않는다.

아래 round 3·4 기록은 당시 이력이다. 최신 결과는 마지막의 2026-09-13 절을 따른다.

## 반영된 범위

- 스펙·계획 frontmatter에 사용자의 승인을 반영했다. superseded 스펙과 과거 피드백을 구현 기준으로 읽지 않았다.
- 다섯 skill과 관련 reference/template에 구현자 재사용, basic 직접 완료, 확산 전 gate,
  유효 검사 재사용, 3-round 후 미해결 유지, 선택적 registry와 triage를 반영했다.
- 표준 라이브러리 Python runtime에 다섯 CLI, 선택 조회·읽기 확인, 상태·evidence 저장,
  독립 검증 조건, drift 무효화, pending·재개, opt-in HANDOFF, 재개 가능한 archive를 구현했다.
- 최소 fixture와 동작 테스트를 추가했다. Git·subagent가 없는 basic, legacy 선택 조회,
  352KB급 원장/10배 history, 장문·중복·supersede, overflow와 상태 복구를 검사한다.
- G1 선행 조건을 지켜 skill에 runtime 호출을 연결하지 않았다.
  README와 `scripts/validate.sh`의 C1 변경 및 `test_lifecycle.py`는 아직 없다.

## 독립 G1

검증자는 승인된 계약, 코드·fixture, 명령 결과와 대상 해시만 받았다.
구현자 설명과 이전 검증자의 서사는 전달하지 않았다. 각 검증자는 기존 suite의 유효성을
확인해 재사용하고, 별도 임시 프로젝트에서 추가 probe를 실행했다.

| round | 결과 | 재현한 계약 위반 |
|---|---|---|
| 1 | REJECT | G1-001: 재개한 구현자의 자기 검증; G1-002: 결정 교체 후 gate 무효화 누락; G1-003: escape된 큰 section의 조회 불가 |
| 2 | REJECT | G1-001의 gate/phase 수정자 변형; G1-004: 상세 이름 `record` 충돌; G1-005: 요청한 HANDOFF 유실 후 재생성 실패 |
| 3 | REJECT | G1-006: consumer 시작 후 선행 코드·검사 입력 drift에도 완료 저장; G1-007: reconcile 후 미응답 pending을 우회한 완료 |

같은 독립성 위반은 G1-001로 유지한다. 이름을 바꾸거나 다른 재현 형태가 나왔다고 round를
초기화하지 않았다. 구현자 수정과 회귀 테스트 성공은 독립 ACCEPT와 다르다.
세 번째 검토 이후의 수정 후보는 추가 독립 검증을 받지 않았으므로 G1은 계속 미해결이다.

승인된 스펙 §3: “동일 검증 범위는 최초 포함 최대 3 round다. cap 도달 시 unresolved 상태를
유지한다. 사용자가 추가 round나 범위 변경을 승인할 수 있지만, 실패를 verified로 바꾸지는 않는다.”
당시 cap에서 멈췄으며, 이후 추가 1회 승인은 마지막 절에 기록했다.

## 실행 검사

- A 완료 시 `bash scripts/validate.sh` → exit 0. 이후 해당 구조 검사 입력은 유지했다.
- B 초기 기반: unittest discovery 49개 → exit 0, 5.785초.
- 1차 G1 수정 후: 58개 → exit 0, 6.756초.
- 2차 G1 수정 후: 65개 → exit 0, 6.795초.
- 3차 G1 수정 후 최종 후보: `python3 -m unittest discover -s plugins/wellbegun/tests`
  → 71개, exit 0, 7.450초. 독립 재검증은 아직 없다.
- 최종 runtime SHA-256: `344acef2717196542925418bc74cc8b546ba18a06b8dcade53deaf5fd0822b8a`.
- runtime이 바뀐 뒤의 검사 실행은 이전 성공 결과의 입력이 달라졌기 때문이다.
  세 독립 검증자는 같은 suite를 관례적으로 재실행하지 않았다.
- skill-creator의 별도 `quick_validate.py`는 PyYAML 부재로 실행할 수 없었다.
  이를 통과했다고 기록하지 않으며 의존성이나 플러그인을 설치·갱신하지 않았다.

환경: Python 3.12.12, macOS 26.6.2 arm64, runtime 의존성은 표준 라이브러리다.
최신 명령·환경·파일 해시는 `/private/tmp/wellbegun-b-checks.json`에 있다.
추가 probe/검토 사실은 `/private/tmp/wellbegun-g1-*`,
`/private/tmp/wellbegun-independent2-*`, `/private/tmp/wellbegun-independent3-*`에 보존했다.

## 실측과 미측정 구분

| 항목 | 관측 결과 | 해석 범위 |
|---|---|---|
| 도그푸딩 기준 | 원본 HEAD와 tracked·untracked 402개 파일 해시 기록 | 원본의 시작 시점 기준 |
| 임시 복사 준비 | 기준 1개 + UI old/new + data old/new, 26.951초 | dependency cache 복사 포함; 구현 비교 시간과 별도 |
| 복사본 동일성 | 네 candidate 모두 시작 기준 402개 파일과 동일 | 비교 실행 전 준비 검사 |
| 원본 결정 원장 | 352,869 bytes | 파일 크기이며 모델 입력량 측정이 아님 |
| 변경한 기존 Markdown 12개 | 55,051 → 50,728 bytes | 파일량 -4,323 bytes; 실제 context 또는 시간 절감이 아님 |
| 새 runtime 계약 문서 | 17,765 bytes 별도 추가됨 | 전체 문서량 감소를 주장하지 않음 |
| 에이전트 호출 | 구현 5 turn + 독립 G1 3 turn = 8 subagent turn | A 1, B 초기+수정 4, G1 3; root의 모델 turn·token은 별도 미측정 |
| UI·L 데이터 비교의 첫 수정/전체 시간 | 미측정 | G1 gate와 round cap으로 실행하지 않음 |
| 비교의 문서 입력 bytes/tokens·검사 반복·관리 문서량·재작업 | 미측정 | 준비 파일 크기로 실제 실행 비용을 대체하지 않음 |
| 관측 구간 wall-clock | 3174.853초 (기준 해시 기록부터 보고 시점) | 준비·구현·대기·수정 포함; 사용자 요청 전체 시간이나 old/new 비교 시간이 아님 |
| 모델 token·금액 | 미측정 | 이 세션 도구에서 실제 usage/billing 값을 제공하지 않음 |

Flutter 환경만 읽기 전용으로 확인했다: 3.44.3, Dart 3.12.2,
framework revision `e1fd963c6f6922bd32afde2e9698a363cd0406d2`.
UI 및 L 데이터 workload 계약은 임시 작업 공간에 준비했지만 구현·테스트 비교는 실행하지 않았다.
고의 기반 결함에 대한 실제 도그푸딩 에이전트 탐지율도 측정하지 않았다.
G1에서 결함을 실제 발견한 사실을 도그푸딩 품질·속도 개선의 증거로 대신하지 않는다.

## 보존과 한계

도그푸딩 원본 `/Users/arden/Documents/dev/kbo-away-fans`에는 이 작업에서 쓰기 명령을
실행하지 않았다. 시작 이후 대조에서 `.wellbegun/HANDOFF.md`, `.wellbegun/run.md`,
`lib/app.dart`, `lib/features/profile/theme_settings.dart`의 변경과
`test/features/profile/cycle3_phase2_fresh_r1_probe_test.dart` 추가가 감지됐다.
변경 주체를 확정하지 않으며, 이 변화도 덮어쓰거나 되돌리지 않았다.
임시 복사본은 처음 기록한 기준을 유지한다.

현재 저장소의 기존 미추적 문서는 보존했다. 사용자 승인 반영을 위한 스펙·계획 편집 외에
과거 검토 문서는 수정하지 않았다. 실서비스 데이터 조작, 배포, 플러그인 설치 갱신,
무차별 staging·revert는 수행하지 않았다. 별도 프로젝트 핸드오프 파일도 만들지 않았다.

runtime은 실제 command 실행·환경 식별·host context 독립성과 사용자 승인에 관해 caller가
제공한 사실을 신뢰한다. 선언되지 않은 의존성을 자동 발견하거나 비협조적 외부 writer의
귀속을 보장하지 않는다. 전체 multi-file/Git atomic transaction도 제공하지 않는다.
Python이 없는 host의 manual 경로를 자동 bounded runtime 제공으로 해석하면 안 된다.

round 3 종료 당시 다음 조건은 추가 G1 승인이었다. 이후 경과는 아래 재개 기록을 따른다.
현재 상태는 구현 후보이며 완성된 release가 아니다.

## 2026-09-12 재개 — 승인과 고정 기준

사용자가 코드 수정·필요 검사, G1 추가 독립 검증 **1회**, ACCEPT 이후 C 연결·도그푸딩을
승인했다. 기존 G1 3회 결과는 보존하며 추가 승인을 실패의 통과 처리로 해석하지 않는다.
입력·호출 감소를 우선해 consumer 변경의 과잉 무효화, 동일 context 본문 반복, basic 수동
receipt/JSON/상태 전이를 수정했다. 기반 계약 위반과 미응답 pending 차단은 유지한다.

재개 preflight에서 보존된 baseline과 UI/data old/new 복사본 모두 시작 manifest의 402개
파일과 동일했다(변경 0). `/private/tmp/wellbegun-lean-validation/resume-preflight.json`에 기록했다.
KBO 원본을 새 기준으로 덮어쓰지 않으며 다른 Herdr 세션에 지시·중단을 보내지 않는다.
데이터 workload는 baseline에 이미 구현되어 있으므로 비교 실행 시 동일 결함을 주입한
고정 후보를 두 정책에 적용한다. 결함 주입 준비 시간과 실제 복구 실행 시간은 구분한다.

### B 경량화 수정과 round 4

- 기반 target·선택 계약과 광범위 검사 입력을 구분했다. 선언된 downstream consumer의
  정상 수정은 broad check만 `reusable:false`로 만들고 변경 없는 기반을 되돌리지 않는다.
  같은 파일에 기반과 consumer가 있으면 파일 전체 기반 target 보호를 유지한다.
- 같은 context ID·audience에서 읽은 decision/registry/detail 본문은 내용 해시로 재사용한다.
  새 context·audience, 변경된 본문, 미조회 필수 상세는 재전달하며 unread 조건을 유지한다.
- `context --remember`는 반환한 section만 자동 저장한다. `transition --input -`는 stdin을
  지원하고 `op:complete-basic`은 검사 후 checking/verified를 한 atomic 저장으로 처리한다.
  구현 시작의 ownership/pending 확인은 유지한다. 별도 receipt 파일·checking write·verifier는
  basic의 필수 절차가 아니다.
- 성공이 완료된 scope의 실제 입력 변경은 총 round 이력을 보존하면서 새 실패 허용량을
  부여한다. 미해결 finding, 미완료 실패, 이름·문구만 변경하는 경우는 cap을 초기화하지 않는다.
- G1 제출 후보: 78개 unittest, exit 0, wall 4.522초. Python 3.12.12 / macOS 26.6.2 arm64.
  runtime SHA-256 `4c3e2f523a13f5b30567020a4c2c13d4b96bc971c6e8719c5a9a6189f58f5fa6`.
  `/private/tmp/wellbegun-b-resume-checks.json`에 대상 9개 파일 hash와 명령·환경을 저장했다.
- 독립 verifier는 9개 hash·환경 일치를 확인해 suite를 재실행하지 않고 재사용했다.
  임시 probe 1개로 아래 문제를 재현했다. 구현자 설명·기존 검증 서사는 입력하지 않았다.

| round | 결과 | 조항과 재현 |
|---|---|---|
| 4 (승인된 추가 1회) | REJECT | G1-008 (검증자 alias `G1-EXTRA-001`): spec §2·§5 및 사용자 정상 consumer 재진입 방지 요구. consumer.py만 변경하고 checkpoint 후 stopped하면 정상 resume이 code_drift로 실패하며 reconcile이 producer/gate를 queued로 바꾼다. finding은 비어 있다. |

재현 명령은 `python3 /private/tmp/wellbegun-g1-extra-probe.py`(검증 당시 exit 0).
판정·사실은 `/private/tmp/wellbegun-g1-extra-review.md`,
`/private/tmp/wellbegun-g1-extra-probe-facts.json`, `wellbegun-g1-extra-facts.json`에 있다.
추가 승인 1회를 소진했으며 새 독립 G1을 임의로 실행하지 않는다.

### 실측 준비의 범위

고정 baseline의 현재 테마 원문만 선택해 theme.owner/fields/clock/family/backfill 다섯 key의
legacy sidecar를 `/private/tmp/wellbegun-lean-validation/selected-inputs/`에 준비했다.
원장 원본 내용은 보존했으며 준비 과정에서 전체 원장을 모델 입력으로 반환하지 않았다.
이는 최초 선택 정리 준비이며 C2의 실제 런타임 조회·UI/L 데이터 비교 실행 결과가 아니다.
context token·가격·old/new 시간 절감·독립 agent 도그푸딩 탐지율은 계속 미측정이다.

### round 4 이후 수정 후보 — 독립 판정 대기

G1-008의 원인은 `drifted`의 downstream 소유권 인정에서 stopped record를 제외한 것이다.
소유권 인정에 stopped를 포함하는 좁은 수정으로, checkpoint된 target과 재개 상태를 보존했다.
기반 target/선택 계약의 drift 검사, pending 답변 확인, stale command 재사용 금지는 유지했다.

영구 회귀 `test_g1_008_stopped_consumer_preserves_ownership_without_bypassing_blockers`를
기존 `tests/test_state.py`에 통합했다. 정상 중단 뒤 context/validate/reconcile에서 upstream
verified·round 1을 보존하고, 실제 기반 drift와 미응답 pending은 재개를 차단하며, 답변 반영 후
consumer·후속 작업 완료와 archive까지 이어진다. 광범위 과거 검사는 `reusable:false`다.

- 최종 변경 입력의 unittest discovery **79개, exit 0, wall 4.572초**.
- `bash scripts/validate.sh` → exit 0, `git diff --check` → exit 0.
  runtime reference도 구조 검사 입력이므로 변경 후 구조 검사를 한 번 실행했다.
- runtime SHA-256 `a61dc121d262ea784480f8f4cb8ab44d194ab78a0b5c29929377e42c67da03f9`.
  최종 명령·환경·9개 파일 hash: `/private/tmp/wellbegun-b-post-extra-checks.json`.
- PyYAML 부재로 skill-creator quick validator는 여전히 사용할 수 없다. 패키지를 설치하지
  않았으며 기존 스킬 구조 검사를 대체 실행으로 기록했다.
- 이번 재개 subagent turn은 구현 1 + 독립 G1 1 + 실패 수정 1 = 3회다.
  C 비교 agent 호출·비용 실측으로 해석하지 않는다.

G1-008은 **구현 수정·회귀 통과 / 독립 판정 미확인**이다. 승인된 추가 독립 1회는 이미 사용했다.
다음 작업은 이 후보에 대한 추가 독립 G1 1회 승인 후 검증이다. ACCEPT이면 기존 승인에 따라
C1 연결 → C2 고정 복사본 비교 → 최종 독립 검토를 진행한다. C를 위해 별도 재승인은 필요 없다.
KBO 원본과 다른 Herdr 세션에는 이 재개 작업에서 쓰기·지시·중단을 수행하지 않았다.

## 2026-09-13 재개 — 동일 파일 원래 재현

사용자가 같은 `src.py`에 정상 consumer 코드를 추가했을 때 producer/gate/consumer가 모두
queued로 돌아가는 원래 문제를 우선 수정하도록 명시했다. 이전 수정은 별도 파일의 검사 입력
귀속 문제만 해결했으며 동일 파일 경로의 해결로 대체할 수 없다. 세 문제 모두 해결이라는
판정은 철회한다. 기반 계약 파괴 검출을 유지하면서 필요한 재검증으로 회복하고 과거 구현
재진입을 최소화하는 후보를 만든다. 범용 의미 분석기·작업별 사용자 승인은 추가하지 않는다.

이 수정까지 마친 후보에 독립 G1 **1회 추가(총 round 5 예정)**를 승인받았다. 기존 round 4의
REJECT와 수정 이력은 보존한다. 유효 검사를 재사용하고 ACCEPT 이후 C1/C2는 기존 승인으로
진행한다. KBO는 고정 복사본만 쓰며 원본과 다른 Herdr 세션에는 쓰기·지시·중단을 하지 않는다.

### 동일 파일 후보의 로컬 검사

계약·선택 입력이 동일한 이미 시작한 record의 파일 drift는 구현 완료 사실을 보존한다.
producer/gate는 stopped/resume checking으로 재검증하고, consumer는 기존 context·target·
진행 상태를 유지한다. 계약 자체 변경은 기존 재계획 경로를 유지한다. pending이 없고 선행
검증이 복구되면 cursor가 다음 recheck record를 선택한다. 선택 본문 receipt는 내용·plan
해시가 유효하면 재사용하며 현재 상태·계약은 다시 읽는다. 동일 target을 수정한 consumer
context의 fresh gate 자기 검증도 차단한다.

동일 src.py에 정상 코드를 네 번 추가한 실제 Python 검사 회귀에서 producer/gate는
구현을 다시 시작하지 않고 총 round 5에 도달했으며 finding 0, 마지막 consumer 완료가 됐다.
같은 src.py 기반 value를 파괴한 회귀는 실제 검사 3회 실패 후 stable finding과 cap에서
멈추고 gate·consumer를 차단했다. 별도 파일 fixture로 대체하지 않았다.

최종 후보 unittest discovery 82개, exit 0, wall 5.071초.
명령·환경·hash는 `/private/tmp/wellbegun-b-same-file-checks.json`, 고정 runtime 사본은
`/private/tmp/wellbegun-runtime-g1-round5.py`에 있다. 사용자 승인된 총 round 5 독립 검증을
시작했다. 결과가 나오기 전 C 연결·도그푸딩을 완료로 표시하지 않는다.

### G1 round 5 — 독립 결과

추가 승인 1회를 실행했다. Python/platform 및 9개 hash가 일치해 82-test 성공을 재사용했고
suite를 반복하지 않았다. 검증자는 같은 src.py에서 정상 append 이후 producer/gate가
stopped/checking, consumer가 stopped/implementing을 거쳐 complete에 도달하며 코드와
consumer context가 보존되는 것을 확인했다. 과거 성공의 reuse는 stale_evidence로 차단했다.

판정은 **REJECT, G1-009**(verifier alias `G1-SAMEFILE-RESUME-ACTION`)다. §5의 다음 행동·
재개 위치 보존 위반: consumer checkpoint의 `Implement render_consumer() output escaping;
parsing is done, keep existing parser.`가 reconcile에서 일반 재개 문구로 덮였고, producer/gate
재검증 후 consumer에 돌아와도 복원되지 않았다. 원래 지시가 state/evidence에 남지 않았다.
별도 파일 사례를 같은 파일의 통과로 대체하지 않았다. 다른 blocking finding은 보고하지 않았다.

판정·재현 사실: `/private/tmp/wellbegun-g1-same-file-review.md`,
`/private/tmp/wellbegun-g1-same-file-facts.json`, `wellbegun-g1-same-file-probe.py`.
이번 추가 1회는 소진됐고 로컬 수정은 독립 ACCEPT가 아니다. C 연결·도그푸딩을 시작하지 않았다.

### round 5 이후 수정 후보 — 독립 판정 대기

G1-009를 수정했다. 진행 중 consumer의 구체적 next_action은 reconcile, user stop,
pending resolution, resume를 거쳐도 보존한다. 기존 stop_reason/resume_status가 중단·재검증
안내를 맡으며 새 상태 필드나 작업별 승인 절차는 추가하지 않았다. 이미 완료된 producer/gate는
현재 필요한 `run contract checks`를 표시한다. checkpoint evidence에는 next_action,
invalidation evidence에는 previous_next_action을 보존해 기록의 유실도 막는다.

기존 `test_state.py`에 `test_g1_009_concrete_action_survives_same_file_recheck_and_saved_stops`를
통합했다. 동일 src.py에서 일반 재검증·사용자 중단·pending 답변의 세 경로를 검사한다.
실제 기반 검사 성공 → producer 검사 완료 → 새 독립 gate → consumer packet/재개 상태의
원래 action 유지 → complete를 확인했다. 기존 기반 파괴·stable finding cap·미응답 pending·
current-target writer 독립성 검사는 함께 유지된다.

- 최종 변경 입력 unittest discovery **83개, exit 0, wall 5.192초**.
- `bash scripts/validate.sh` → exit 0. `git diff --check` → exit 0.
- runtime SHA-256 `31b3a71612515fa61a89dcd1c1cf22552bb24a8e94535d527e3959aa62e6a5a9`.
- 명령·환경·9개 파일 hash: `/private/tmp/wellbegun-b-post-round5-checks.json`.
  재검토 가능한 고정 runtime 사본: `/private/tmp/wellbegun-runtime-post-round5.py`.
- 이번 재개 agent turn: 동일 파일 수정 1 + 독립 G1 1 + G1-009 수정 1 = 3회.
  G1은 유효한 82-test 사실을 재사용했고, 수정 후 변경 입력의 suite를 1회 실행했다.

원래 동일 파일 재현의 재검증 회복은 독립 probe에서 확인됐다. 그러나 G1 전체 verdict는
REJECT였으므로, G1-009의 로컬 회귀 성공을 전체 ACCEPT로 바꾸지 않는다. 승인된 추가
1회(총 round 5)는 소진됐다. 다음 조건은 이 수정 후보에 대한 추가 독립 G1 **1회 승인**이다.
ACCEPT 이후 C1 연결·C2 고정 복사본 비교·최종 검토는 기존 승인으로 진행한다.
C2 입력 bytes/token·비교 시간·도그푸딩 탐지율은 미측정이며 성능 달성을 주장하지 않는다.
KBO 원본 및 고정 workload 후보의 코드는 이 재개에서 수정하지 않았고, 다른 Herdr 세션에
지시하거나 중단하지 않았다.

## 2026-09-13 재개 — G1 round 6

사용자가 round 5 이후 수정 후보에 독립 G1 1회(총 round 6)를 추가 승인했다. 사전 확인에서
`/private/tmp/wellbegun-b-post-round5-checks.json`의 9개 파일 SHA-256과 현재 입력이 모두
일치했고 Python 3.12.12 / macOS 26.6.2 arm64도 같았다. 따라서 83개 unittest 성공,
`bash scripts/validate.sh`, `git diff --check` 성공 사실을 재사용하고 관례적으로 반복하지 않았다.

### 독립 결과

검증자는 최신 스펙·G1 계약, 대상 코드·fixture, 명령과 유효 검사 사실만 받았다. 구현자 설명,
이전 verifier 서사, 이 validation 문서 전체는 전달하지 않았다. 저장소는 수정하지 않고
`/private/tmp/wellbegun-g1-r6-th6V2k/environment_probe.py`로 환경 변경 경계를 확인했다.

판정은 **REJECT, G1-R6-ENV-001**이다. Python 3.12.12에서 producer와 독립 gate가 통과한 뒤
실행 runtime이 Python 3.9.6으로 바뀌고 같은 기반 검사가 실패해 gate packet이
`reusable:false`를 반환해도, prerequisite 판정은 과거 gate 성공을 받아 `validate`를 통과시키고
첫 consumer를 `implementing`으로 시작했다. 이는 스펙 §3의 관련 환경 변경 시 검사 무효화와
B3의 invalid gate 성공 재사용 금지를 위반한다. 다른 blocking finding과 계약 밖 finding은
보고되지 않았다. 승인된 round 6은 이 판정으로 소진됐고 G1은 ACCEPT가 아니다.

### round 6 이후 수정 후보 — 독립 판정 대기

`artifacts.py`의 drift 판정이 verified result의 기록된 runtime identity와 현재 runtime을
비교하도록 좁게 수정했다. 환경 drift에서는 producer/gate를 구현 재시작이 아닌
`stopped → checking` 재검증으로 복구하고, consumer는 선행 검증 회복 전까지 차단한다.
기존 same-file 재검증, 구체적 next_action, pending, finding cap 경로는 유지한다.

`test_state.py`에
`test_runtime_drift_revalidates_prerequisites_before_consumer_dispatch`를 추가했다. 변경 환경에서
gate check의 `reusable:false`, validate/consumer dispatch 차단, reconcile 뒤 producer/gate
재검증, fresh gate 성공 후 consumer 재개를 확인한다.

- 변경 입력의 targeted test 1개 통과.
- `python3 -m unittest discover -s plugins/wellbegun/tests -p 'test_*.py'` → **84개, exit 0**.
- `bash scripts/validate.sh` → exit 0. `git diff --check` → exit 0.
- runtime SHA-256: `5130c25b5e36a774d3300230d61557c2760b4f52298dcb848e77667e234d73b5`.

이 결과는 구현 수정과 로컬 검사 성공이며 독립 ACCEPT가 아니다. 따라서 C1 연결, C2 고정
복사본 비교, 최종 독립 검토는 시작하지 않았다. 다음 조건은 이 수정 후보에 대한 새 독립 G1
승인이다. 성능·비용·도그푸딩 탐지율은 계속 미측정이며 달성을 주장하지 않는다. KBO 원본과
고정 workload 복사본은 수정하지 않았고, 다른 Herdr 세션에 지시하거나 중단하지 않았다.

## 2026-09-13 집중 점검 후 G1 round 7

사용자가 판정 경로 집중 점검·필요 수정 → 유효 검사 재사용 → 독립 G1 1회 → ACCEPT 후
C1/C2의 추천 순서를 승인했다. 기존 round와 finding 이력을 유지한다.

집중 점검에서 실패한 command fact도 packet의 `reusable:true`로 표시되는 불일치를 발견했다.
실제 reuse 경로는 이미 거절했으므로 packet과 reuse가 작은 `reusable_check`를 공유하도록
수정했다. 기존 prerequisite drift 판정의 공통 사용을 확인하고 runtime drift를 기존
context/validate/checking/completion 회귀 matrix에 보강했다. 기반 acceptance와 downstream
소유 broad-check 입력 재사용은 구분을 유지한다. 범용 캐시나 새 승인 절차는 추가하지 않았다.

- 영향 검사 3개 통과; 전체 `python3 -m unittest discover -s plugins/wellbegun/tests`
  85개, exit 0, unittest 보고 5.325초.
- 구조 검사와 `git diff --check` exit 0.
- Python 3.12.12 / macOS 26.6.2 arm64, stdlib.
- 명령·환경·27개 파일 해시: `/private/tmp/wellbegun-b-pre-round7-checks.json`.
  conductor는 27개 해시와 현재 환경 일치를 대조하고 전체 suite를 반복하지 않았다.
- runtime SHA-256: `9ec9821bb6be96d2055b7faa02d8f1c0bdcbd865659d9eb4d9425bd6436de51a`.
- baseline 및 UI/data old/new 고정 복사본은 원래 manifest의 402개 파일과 모두 동일하다.

high-tier의 새 독립 context에 계약·대상 코드·실행 명령·검사 사실만 전달해 총 round 7을
시작했다. 구현자 점검 서사와 이 validation 보고서는 전달하지 않았다.

판정은 **ACCEPT**다. 새 임시 probe 4개가 통과했으며, 같은 파일의 이중 reconcile과
consumer implementing/checking/fixing 재개 상태·구체적 action 보존, runtime drift 뒤
과거 gate evidence 재사용 차단을 포함한다. 검사 실행과 결과 등록 사이의 입력 변경 가설은
명시된 trusted-caller 보고 계약 안에서 위반으로 확정되지 않아 finding으로 올리지 않았다.
계약 밖 finding은 없다. 85-test 성공은 재사용했으며 target 구현/기존 테스트는 수정하지 않았다.

독립 판정: `/private/tmp/wellbegun-g1-round7-review.md`.
독립 probe: `/private/tmp/wellbegun-g1-round7-probe.py`.
G1 선행 조건 충족 후 C1 다섯 lens·재개·archive 경로 연결을 시작했다.

## C1 연결 — 로컬 검사 통과

다섯 lens에 작은 `references/selected-inputs.md`를 연결했다. 새 cycle의 marker plan,
선택 조회/remember, init, basic 직접 완료, fresh gate, pending 답변·재개, render와 archive를
실제 helper에 연결한다. legacy는 기존 cycle 형식을 유지하며 결정 key와 관련 registry
section만 읽는다. AGENTS/CLAUDE 생성 지침은 사용자 규칙을 보존하고 선택 조회만 추가한다.
Python/Git/subagent 부재 시 지원 범위도 명시했다. 모든 lens의 runtime 계약 전체 읽기는 없다.

wellnext는 helper archive 뒤 begin/spec/이전 audit의 이동과 그 사이 중단 복구를 안내한다.
새 plan packet에 과거 cycle의 state/read/evidence를 복사하지 않는다. G1이 통과한 runtime과
공개 계약은 그대로이며 해시 `9ec9821b…de51a`를 유지한다.

`tests/test_lifecycle.py`는 실제 CLI와 skill shell/plan 예제를 다른 cwd와 공백 경로에서
실행한다. basic→gate→pending/재개→complete→archive→다음 cycle, legacy 보존 및 N/A
registry를 검사한다. 합성 verifier identity는 프로토콜 검사이며 실제 agent 탐지율이 아니다.

- `bash scripts/validate.sh`: 구조 + unittest discovery **88개, exit 0, 9.829초**.
- `git diff --check`: exit 0.
- 최초 신규 fixture 실패는 macOS `/var`/`/private/var` 실제 경로 불일치였다. fixture 경로를
  정규화한 뒤 변경된 입력을 재검사했다. runtime 오류를 우회하지 않았다.
- 명령·환경·20개 파일 해시: `/private/tmp/wellbegun-c1-checks.json`; conductor 대조 일치.

C1은 구현·로컬 검사 통과 상태이며 전체 조합의 독립 판단은 최종 검토에 남겨 둔다.
승인된 C2 고정 복사본 비교를 시작했다.

## C2 고정 복사본 — 제한된 실행 관측

원본을 다시 복사하지 않고 기존 baseline/UI old/new/data old/new에서 실행했다.
baseline의 402개 manifest 파일은 모두 보존됐다. UI old/new는 허용된 sheet와 기존 test에
동일한 label/assertion 변경만 있다. 두 데이터 후보는 종료 후 402개 파일 모두 baseline과
같다. legacy 관리 문서는 그대로이며 부분적인 schema 2 도입은 없다.

| 실행 | 첫 코드 수정까지(초, 수정 전후 경계) | checkpoint 완료까지(초) | 결과 |
|---|---:|---:|---|
| UI old | 52.935–65.259 | 200.500 | widget 4개 + 영향 analyze 통과 |
| UI new | 12.192–12.298 | 82.173 | widget 4개 + 영향 analyze 통과 |
| data old | 202.597–214.186 | 423.144 | 필수 14개 + 외부 probe 2개 통과, 독립 ACCEPT |
| data new | 420.726–420.834 | 622.606 | 필수 14개 + 외부 probe 2개 통과, 새 CLI 독립 ACCEPT |

시간은 orchestration·보고·대기를 포함한다. UI 구간에는 packet 작업이 끼어 있으며 new
구현 context가 old 결과를 본 순서 효과도 있다. 변경·검사 명령 자체는 순차 실행했다.
데이터는 agent thread 한도로 새 context 생성이 막혀 새 ephemeral Codex CLI로 이어갔다.
CLI sandbox는 Flutter의 localhost socket을 막았으므로 assertion 실행 전 실패했고,
기존 host가 필요한 검사를 실행한 뒤 독립 CLI가 유효 결과와 코드를 판단했다. sandbox나
rules를 우회하지 않았다. 다른 Herdr 세션의 재개·지시·중단은 수행하지 않았다.

**데이터 시간 단축 목표는 이번 관측에서 미달이다.** in-app 역할은 모델/effort를 상속했고
CLI는 codex-cli 0.154.0, gpt-6-astra/high를 명시했다. 데이터의 동일 host/model 통제가
깨졌으므로 순수 정책 효과의 시간·비용 비교가 아니다. 네 실행의 결과를 완전한 통제
benchmark로 대체하지 않는다. paired 총 tokens/billing과 전체 입력량은 미측정이다.

두 데이터 후보에는 준비 단계에서 동일한 absent-only backfill 결함을 넣었다. 저장된
b/dark를 덮어쓰는 `C2-backfill-preserve`를 old/new 독립 agent가 실제로 발견했다.
old는 검사 6개 통과/8개 실패, new CLI는 코드로 발견했고 host 검사에서도 6/8을 재현했다.
각 수정 후 새 독립 context가 ACCEPT했다. consumer 변경은 ACCEPT 전 수행하지 않았고,
adapter는 baseline에 이미 있어 새 consumer 구현은 필요하지 않았다. 실제 탐지 두 사례가
일반 탐지율 보장은 아니다. fake Firestore 검사이며 production rule/emulator 동등성은 미측정이다.

old UI는 구현 agent 1회, new UI는 현재 context 직접 실행이며 verifier는 둘 다 없다.
old data는 수정자 1회 + 독립 verifier 2회, new data는 현재 context 수정 + 새 CLI verifier
2회다. 실패한 생성 시도와 공통 conductor 작업은 별도 비용이다. old 정책의 전체 suite/phase/
whole-run, mode 재질문과 관리 기록 절차를 모두 재연하지 않았다. 관리 문서 변경 0회는
이번 제한된 실험의 관측이며 일반 old workflow 비용을 뜻하지 않는다.

기록된 문서 입력 일부는 UI old 4,970B/new 1,353B다. 공통 선택 준비, 상속 prompt와 일부
미계측 읽기가 있어 이를 전체 입력량으로 해석하거나 차이를 비용 절감으로 계산하지 않는다.
잘린 코드 출력은 생성 bytes와 실제 전달량을 구분하며 unknown을 0으로 세지 않는다.
동일한 성공 검사를 같은 run 안에서 반복한 횟수는 0이다. 데이터 재검사는 코드 변경이나
socket 실패 환경 변경 때문이었다. 외부 probe 두 개는 정책 간 재사용했다.

실제 helper 선택 packet 관측:

- 새 context 3,933B → 같은 context 1,466B → 다른 새 context 3,933B.
  decision 3개/registry 1개 본문이 같은 context에서 포인터로 바뀌고 새 context에 복원된다.
  작은 계약이라 4–8KiB 목표보다 작고 12KiB 상한을 지킨다.
- 무관한 registry history 0/336,000/3,360,000B에서 manual-receipt packet 5,481B는
  byte-identical이다. 원장 352,869B는 로컬에서만 파싱했고 모델에 전체 전달한 횟수는 0이다.
- overflow 안내 443B + 명시 section 6,213/6,211/6,211/3,023B로 Unicode 계약을 정확히
  복원했다. 각 응답은 12KiB 이하다. 합성 확장 본문은 로컬 검사이므로 agent 실제 읽기나
  인지 증거로 세지 않는다. 최초 legacy 정리 비용은 `selected-preparation.json`에 별도 남긴다.

원시 결과: `/private/tmp/wellbegun-lean-validation/c2-results.json`.
해석과 한계: 같은 디렉터리 `c2-report.md`.
계약·현재 해시·명령·판정 사실·측정 한계만 분리한 `final-review-facts.json`을 최종 독립
검토 입력으로 사용한다. 전체 validation 서사와 구현자/이전 verifier 서사는 전달하지 않는다.
검토는 새 ephemeral CLI context, gpt-6-astra/high이며 저장소/후보에는 쓰지 않는다.

## 최종 독립 검토 round 1 — C2 근거 보완

판정은 REJECT다. C1 구현과 lifecycle 연결, 기존 G1 runtime 보존에는 구체적인 위반을
발견하지 않았다. 이전 유효 검사를 재사용했고 새 테스트나 구현 변경은 하지 않았다.

- `FINAL-C2-001`: 스펙 §9의 동등 환경 비교. data old의 in-app 상속 모델과 data new의
  CLI gpt-6-astra/high가 달라 이 요구의 충족을 뒷받침하지 못한다.
- `FINAL-C2-002`: 계획 C2의 실행별 문서 입력 bytes. 네 run의 전체 actual bytes가 null이고
  공통·상속·미계측 읽기가 배분되지 않아 요구한 입력 비용 비교가 미완료다.

한계를 공개한 것은 맞지만 완료 조건을 대신하지 않는다. 계약 밖 finding은 없다.
판정 원문: `/private/tmp/wellbegun-lean-validation/final-review-cli-final.txt`.
명령·새 context·실행 로그는 같은 위치의 `final-review-cli-*`에 보존한다.

기존 고정 baseline을 기준으로 추가 controlled 비교 후보를 만들고 old/new 모두 같은
CLI/model/검사 환경, 새로운 context, 전달 문서 전체 bytes를 기록하는 보완 실행을 시작했다.
기존 네 후보/관측은 유지하며 원본에서 복사본을 갱신하지 않는다. G1은 여전히 ACCEPT이며
이 보완은 C2 검증 근거의 수정이다. 최종 검토 round/finding을 초기화하지 않는다.

## C2 보완 — 같은 환경·완전한 문서 입력 계측

`controlled/`의 네 후보는 보존된 baseline에서 파생했으며 최초 402개 파일이 일치한다.
기존 네 관측 후보와 baseline을 덮어쓰지 않았다. UI old→new→data old→new 순서로
각 run을 끝낸 뒤 다음 run을 시작했다. 비교 범위는 양쪽 모두 step 수준이며 phase/전체
pipeline 종료 비용은 측정 범위 밖이다. old 데이터 step의 필수 전체 Flutter 회귀는 실행했다.

모든 모델 역할 10개를 codex-cli 0.154.0, gpt-6-astra/high, 새 ephemeral context로 실행했다.
검사 명령은 양쪽 모두 같은 기존 host/Flutter 환경이 담당했다. 자동 AGENTS 입력은
해당 호출의 `project_doc_max_bytes=0`으로 끄고 적용되는 CLAUDE/계약/결정 제약을 정확히
계측되는 prompt에 넣었다. 저장된 사용자 설정과 rules는 변경하지 않았다.

| 실행 | 역할 수 | 실제 전달 문서·dispatch bytes 전체 | 모델 실행 구간(초) | 완료까지(초) |
|---|---:|---:|---:|---:|
| UI old | 2 | 30,103 | 46.012 | 169.642 |
| UI new | 1 | 25,189 | 36.615 | 120.830 |
| data old | 4 | 69,520 | 186.684 | 610.340 |
| data new | 3 | 62,202 | 158.463 | 378.164 |

문서량은 각 역할에 실제 전달된 정책·프로젝트 제약·계약·dispatch·검사 사실 prompt의
정확한 UTF-8 bytes를 모두 합산한다. 모든 prompt 해시/본문 크기와 추가 읽기 출력을
CLI 이벤트의 실제 본문에 대조했다. 예상 밖 프로젝트 문서 출력 0, 출력 잘림/본문 불일치 0이다.
코드 읽기는 별도 계측하며 provider system prompt/token/billing을 이 문서량으로 대체하지 않는다.
전체 bootstrap 문서 합계는 단일 정상 runtime packet의 12KiB 상한과 다른 측정이다.

old UI는 conductor+구현자, new UI는 직접 실행 역할 하나다. old 데이터는 conductor+첫
독립 gate+수정자+새 독립 gate, new 데이터는 첫 gate+직접 수정 역할+새 gate다.
두 정책의 데이터 gate는 동일한 주입 결함을 REJECT하고 수정 뒤 ACCEPT했다.
UI 최종 코드·테스트는 동일하며 data의 비관리 파일은 baseline과 같다. legacy run.md의
실제 진행 줄 변경은 별도 관리 쓰기량에 포함했다. consumer는 ACCEPT 전 변경하지 않았다.

old 전체 Flutter 검사: 결함 후보는 960 pass/1 skip/18 fail, 복원 후보는
971 pass/1 skip/7 fail. 복원 뒤 남는 7개는 baseline-identical 코드에서 관측된 smoke/팀선택
timer·timeout 테스트다. 구체적인 원인 진단을 주장하지 않으며 전체 회귀를 green으로 표시하지
않는다. 데이터 step의 필수 14개 및 추가 probe 2개의 성공과 분리한다. 범위 밖 코드는 고치지 않았다.

new는 정확한 코드·환경·검사 입력이 일치하는 성공 사실을 재사용했다. UI 검사 내용이
이전 관측과 달랐을 때는 old에서 실행했고, new의 최종 해시가 old와 같음을 확인한 뒤
재사용했다. 실패 결과를 성공으로 재사용하지 않았다. 이 재사용과 warm cache, 실행 순서,
orchestration/보고 시간이 관측 시간에 포함된다. 위 수치는 한 쌍의 실제 관측이며 일반적인
속도·금액·token 절감 보장은 아니다. 앞선 동등성 실패 관측은 별도 이력으로 유지한다.

원시 결과 `controlled-results.json`, 독립 입력 `controlled-final-review-facts.json`, 해석
`controlled-report.md`를 `/private/tmp/wellbegun-lean-validation/`에 보존한다.
보완 근거를 새 독립 최종 context에 전달하며 round 1 verifier 서사는 전달하지 않는다.

## 최종 독립 검토 round 2 — ACCEPT / 구현 완료

새 ephemeral CLI, gpt-6-astra/high context는 최신 계약·코드·유효 검사 사실·controlled
측정 사실만 받았다. 전체 validation 문서나 구현자/이전 verifier 서사는 전달하지 않았다.
판정은 **ACCEPT**이며 C1, bounded C2, 최종 구현 완료가 계약으로 뒷받침된다고 판단했다.
`FINAL-C2-001`은 동일 CLI/model/검사 환경의 보완 비교로, `FINAL-C2-002`는 누락 없는
역할별 문서 입력 계측과 독립 재계산으로 해결됐다. G1 및 최종 round 이력은 유지한다.

독립 검토자는 prompt 10개, reader 출력 50개의 해시·길이를 재계산하고, 실제 CLI 전달
기록과 총량·시간 계산·명령 출력 해시·후보 동일성을 대조했다. G1/C1 및 workload의
유효 검사 사실을 재사용했으며 plugin suite와 Flutter 검사를 반복하지 않았다.

- 판정: `/private/tmp/wellbegun-lean-validation/final-review-round2-cli-final.txt`.
- 독립 산식 감사: `/private/tmp/wellbegun-lean-validation/final-review-round2-ozwpjzvo/independent-metric-audit.json`.
- 실행/입력 기록: 같은 상위 디렉터리의 `final-review-round2-cli-*`.
- 완료 시 runtime SHA-256: `9ec9821bb6be96d2055b7faa02d8f1c0bdcbd865659d9eb4d9425bd6436de51a`.

성능 해석의 한계는 유지한다. 단일 표본·고정 순서·warm cache·검사 재사용·orchestration
시간이 포함되고 관리 문서량은 모든 경우 줄지 않았다. 전체 pipeline 비용, provider system
입력, paired token/billing은 미측정이다. 실패 검사 사실도 gate 판단에 제공됐으므로 두 결함
탐지 사례를 맹검 탐지율로 해석하지 않는다. 작은 정상 packet은 3,933B이며 목표 구간을
맞추려고 채우지 않았다. 범위 밖 Flutter 실패 7개는 보존하고 고치거나 통과로 바꾸지 않았다.

최종 판정 뒤 README/이 문서의 상태만 완료로 갱신했다. 런타임·검사 입력은 유지했으며
문서 상태 반영 때문에 전체 suite를 반복하지 않는다. KBO 원본, 이전 고정 baseline,
다른 Herdr 세션은 보존했다. 설치·배포·무차별 stage/revert/stash/commit은 하지 않았다.
