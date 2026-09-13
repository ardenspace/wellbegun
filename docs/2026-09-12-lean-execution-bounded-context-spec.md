---
status: approved
date: 2026-09-12
revision: 2
supersedes: docs/2026-09-12-bounded-context-deterministic-handoff-spec.md
sources:
  - docs/2026-09-12-lean-wellrun-dogfood-feedback.md
  - docs/2026-09-12-dogfood-context-handoff-review.md
---

# lean execution and bounded context — spec

## 목표와 우선순위

최우선 목표는 어떤 에이전트와 프로젝트에서도 작은 입력과 적은 절차로 핵심을 짚고
코딩을 돕는 것이다. 그다음은 실행 시간 단축, 누적 문서의 선택적 읽기다.
문서 줄 수만 줄이거나 작업을 덜 검증해서 빠르게 만드는 것은 성공 기준이 아니다.

유지할 핵심은 네 가지다.

1. 되돌리기 어려운 결정을 일찍 발견한다.
2. 구현 전에 완료 조건을 정한다.
3. 중요한 경계에서는 구현자 설명에 물들지 않은 검증을 한다.
4. 중단 후 현재 작업을 찾아 이어간다.

기본 원칙: **검증된 경계 안에서는 구현자를 재사용하고, 새 기반을 확산하기 전에는
독립 검증한다.** 지금 쉽게 바꿀 수 있어도 후속 작업들이 의존하면 비싸지는 결정을 포함한다.

## 근거와 아직 확인하지 못한 것

도그푸딩 보고에 따르면 KBO cycle 2의 plan은 36,557 bytes, run은 276,005 bytes,
decisions는 351,074 bytes였다. cycle 3에서는 fresh 검증이 역사적 데이터 모양의 누락을,
phase 검증이 migration과 테마 조합 문제를 발견했다. 독립 검증에는 실제 가치가 있었다.
반면 새 구현자 생성, 전체 회귀, probe와 결정 기록이 반복되었다.

위 수치는 보고된 관찰이다. 별도로 2026-09-12 도그푸딩 프로젝트
`/Users/arden/Documents/dev/kbo-away-fans`를 읽기 전용으로 확인한 결과, 현재
`.wellbegun/decisions.md`는 352,338 bytes / 435줄, 가장 긴 줄은 4,086 bytes였다.
L/XL 색인과 전체 원장이 같은 파일에 있으며, spec에는 날짜만으로 결정을 참조하는 항목이 있다.
`lib/backend/REGISTRY.md`도 17,928 bytes로, 현재 계약에 결정 이유와 변경 역사가 함께 실려 있다.
따라서 한 줄 기록, 색인 추가, decisions만 선택 조회하는 것으로는 입력 부담이 충분히 줄지 않는다.

구현자 재사용의 시간 절감과 결함 누락률은 아직 입증되지 않았다.
아래 성능·품질 검증으로 확인한다.

## 이번 범위

- 같은 경계 안의 구현자 재사용과 단일 에이전트 basic 실행.
- 의존 작업 실행 전 독립 검증 gate, 계약에 따른 완료 판정.
- 영향 범위 검증과 유효한 실행 결과 재사용.
- 현재 작업 추출, 작은 실행 상태, 활성 결정 선택 조회.
- 선택적 registry, 요청 분류 후 관련 영역 audit, 작은 작업의 pipeline 생략.
- 최소 checkpoint 복구, legacy와 기능이 부족한 host의 명시적 처리.
- 아래 정책과 모순되는 기존 skill·reference·template·검사 규칙의 동시 수정.

이번 범위에서 제외한다: 모든 writer의 worktree 강제, 자동 cherry-pick ingestion 엔진,
Git과 여러 문서에 걸친 atomic transaction, 모든 기획 문서의 schema 전환,
전체 과거 decision 승인·변환, context 사용률별 host 기본값, prompt caching 최적화.
병렬 실행 최적화도 후속이다. 기본 실행은 순차다.

## 1. 실행 단위와 구현자 연속성

step은 관찰 가능한 결과 하나와 완료 조건을 가진다. 에이전트 호출 하나 또는 UI 요소 하나가
step의 기준이 아니다. 승인된 step 안의 widget·helper 수정은 구현 subtask로 처리한다.
계약은 코드보다 먼저 정하되, 새 probe와 필요한 검사 보완은 구현 중에도 허용한다.

| 상황 | 기본 실행 | 확인 시점 |
|---|---|---|
| 작은 수정, 새로운 비싼 결정 없음 | 현재 에이전트 직접 구현 | 영향에 맞는 검사 후 종료 |
| 검증된 경계 안의 연속 S/M step | 현재 구현자 재사용 | step 계약 검사 |
| 새 공유 계약·데이터 흐름 도입 | 구현 후 독립 검증 | 첫 의존 작업 전 |
| L/XL 변경 | 구현자와 분리된 fresh 검증 | 완료 및 의존 작업 전 |
| phase 조합 | fresh 통합 검증 | 다음 phase 전 |
| 전체 종료 | fresh 최종 검토 | release 조건 충족 후 완료 |

구현자 재사용은 같은 작업 영역, 유효한 계약·결정, 충분한 context에서만 허용한다.
phase 종료, context 부족, 소유권 충돌 또는 계약의 중대한 변경 시 새 구현자를 사용한다.
L/XL 발견 후 재개도 결정이 정리된 계약으로 새 구현자에게 넘긴다.
단순 재사용 여부를 매 step마다 사용자에게 묻거나 ADR로 기록하지 않는다.

계약 누락·모순, 예상 밖 제약, 같은 원인의 실패 반복, 수정 범위 확대를 발견하면
후속 의존 작업을 멈추고 가정과 계약을 확인한다. 필요하면 gate를 추가한다.
구현자 교체 자체를 문제 발견 또는 검증 완료로 취급하지 않는다.

## 2. 확산 전 독립 검증 gate

wellplan은 새 기반의 첫 사용 이후 여러 작업이 그 결과에 의존하게 되는 지점을 표시한다.
예: 테마 저장·전달 구조를 만든 뒤 여러 화면에 적용하기 전, 새 데이터 형식을 만든 뒤
여러 소비자를 옮기기 전. 이름·색상 같은 독립 수정마다 gate를 만들지 않는다.

- gate는 검증 대상 producer와 통과 전 실행할 수 없는 consumer를 명시한다.
- producer가 L/XL이면 해당 fresh 검증으로 gate를 충족한다. 같은 대상의 별도 검증을 추가하지 않는다.
- phase integration이 첫 consumer 전에 실행되고 같은 조건을 검증한다면 gate를 겸한다.
- gate 실패 시 producer를 수정한다. consumer로 확산하지 않는다.
- gate 이후 기반 계약이나 검증 대상 동작이 바뀌면 gate를 무효화한다. 관련 consumer와
  기존 결과의 영향 범위를 확인하고 필요한 검증을 다시 수행한다.
- 새로운 의존 관계를 구현 중 발견하면 계획에 gate와 근거를 반영한다. 비싼 결정의
  변경이 없으면 기존 권한 안에서 처리한다.

검증 등급은 기존 L/XL 결정을 단순히 사용하는지가 아니라 **이번에 도입·변경하는 결정의
되돌림 비용**에서 도출한다. 다만 S/M producer도 위 확산 경계에서는 fresh gate를 받는다.
되돌림 비용과 검사 범위는 별개다. 작은 변경도 영향 범위가 넓으면 회귀를 넓힌다.

## 3. 검증과 완료 판정

basic은 해당 계약 테스트와 영향 범위 lint/analyze 등으로 완료한다. 별도 verifier나
verifier ACCEPT가 필요 없다. 실제 변경과 무관한 검사를 형식적으로 추가하지 않는다.

fresh verifier는 계약, 대상 코드/diff, 실행 명령, 필요한 registry·활성 결정을 받는다.
구현자의 설명·자기평가, canonical evidence 전체, 이전 verifier의 판단 서사는 받지 않는다.
필요한 코드를 직접 탐색하고 새 probe를 만들 수 있다. fixer에는 실패한 계약과 재현 사실을 준다.
재검증 verifier는 새로운 독립 context를 사용한다.

REJECT는 위반한 계약 조항과 재현 근거를 명시한다. 계약 밖 제안은 완료를 막지 않는 finding으로
분리하되, 새 L/XL 결정이나 현재 계약 자체의 결함이면 명시적으로 처리한다.
테스트·hook·문서만 수정되었다는 이유로 구현 완료를 추정하지 않는다.

동일 검증 범위는 최초 포함 최대 3 round다. cap 도달 시 unresolved 상태를 유지한다.
사용자가 추가 round나 범위 변경을 승인할 수 있지만, 실패를 verified로 바꾸지는 않는다.
autonomous에서도 계약 위반을 임의로 통과시키지 않는다. 영향을 받지 않는 독립 작업만
계획상 가능하면 진행하고, 불가능하면 checkpoint와 미해결 결과를 보고한다.

step 이름·candidate SHA·contract 문구 변경만으로 round를 초기화하지 않는다.
같은 미해결 위반은 stable finding ID로 추적한다. 실제 승인된 신규 범위만 새 검증 단위이며,
기존 finding은 해결·명시적 범위 제외·미해결 중 무엇인지 남긴다. 범위 제외는 통과와 다르다.

### 검사 결과 재사용

- S/M: boundary tests와 영향 범위 검사. fresh: 필요한 회귀와 독립 판단.
- phase: phase가 만드는 조합과 필요한 전체 회귀. UI는 주요 상태의 실행·렌더 확인을 포함한다.
- whole-run: 모든 release 조건의 충족 여부를 검토하고 미확인·무효화된 검사만 실행한다.
- 같은 대상·명령·환경의 성공 검사는 기본 1회다. 실행 담당을 하나로 정하며,
  conductor와 verifier가 관례적으로 같은 명령을 반복하지 않는다.
- verifier는 기존 명령 결과를 사실 정보로 받을 수 있고 불신할 근거가 있으면 재실행한다.
  최종 판단은 독립적으로 내린다.

evidence에는 대상 commit 또는 내용 식별자, 검사 범위, 명령, exit status, 관련 환경·의존성
식별 정보, 외부 상태 의존 여부를 기록한다. dirty tree에서 HEAD만으로 대상을 식별하지 않는다.
테스트 코드·설정·의존성·관련 소스·환경이 바뀌면 해당 결과는 무효다.
외부 상태나 식별 불가능한 환경에 의존하는 결과는 유효성을 가정해 재사용하지 않는다.
문서 변경 등 검사 입력이 그대로임을 확인한 경우에는 SHA 변경만으로 전체 회귀를 반복하지 않는다.
복잡한 범용 테스트 캐시 엔진은 만들지 않는다. 재실행 시 이유 한 줄이면 충분하다.

UI의 관찰 가능한 렌더 기준도 유효한 완료 조건이다. 모든 시각 조건을 exit code로
바꾸려고 테스트 기반을 새로 만들지 않는다. golden은 안정된 환경과 목적이 있을 때만 추가한다.

### Probe

임시 재현을 먼저 사용하고, 새 회귀 방어 가치가 있는 case만 영구 테스트로 남긴다.
기존 테스트에 통합 가능하면 구현자가 통합한다. verifier는 대상 구현과 기존 테스트를
수정하지 않는다. 통합 후 바뀐 테스트는 실행해서 확인한다.
round당 신규 영구 probe 0–2개는 목표치이며 quota나 hard cap이 아니다.
새 파일 수보다 중복·유지 비용을 판단하고 phase 종료 때 관련 probe만 정리한다.

## 4. 현재 작업만 읽는 문서 구조

보관량이 늘어나도 기본 입력량은 늘어나지 않아야 한다. 매 재개마다 과거 문서를 모델로
요약하는 작업도 하지 않는다. 현재 상태의 선택과 추출은 작은 runtime helper가 담당한다.

| 자료 | 역할 | 기본 읽기 |
|---|---|---|
| `plan.md` | 계약·의존 관계·gate | 현재 계약과 관련 gate만 |
| `state.json` | 권위 있는 실행 상태 | helper가 현재 record만 반환 |
| `run.md` | 사람이 읽는 진행 색인 | state에서 생성; bootstrap 입력 아님 |
| `evidence/` | 검사·실패의 상세 근거 | 미해결 finding과 유효 결과의 짧은 항목만 |
| `decisions.md` | 현재 결정 index와 역사 | 관련 active key만 |
| `HANDOFF.md` | 현재 상태의 파생 인계 문서 | 필요 시 생성; state와 중복 주입하지 않음 |
| `cycles/`·과거 검토 문서 | 보존된 역사 | 명시적 원인 조사 때만 |

기본 packet은 현재 목표·완료 조건·재량, state와 다음 행동, 적용되는 활성 결정·registry,
미해결 finding, 유효한 검사 요약과 상세 포인터로 구성한다. 완료 라운드 서사는 넣지 않는다.
phase gate와 whole-run에는 해당 검증 범위의 계약·결과를 별도 packet으로 제공한다.
독립 verifier용 packet에는 구현자·이전 verifier의 서사를 제외한다.

정상 step packet은 UTF-8 4–8KB를 초기 목표로 한다. 기본 출력은 최대 12KB이며,
초과하면 cursor·초과 영역·분할 조회 방법만 반환하고 성공 packet인 척 잘라내지 않는다.
필수 조건은 모두 읽고 나서 구현한다. 큰 계약·통합 검토는 명시적 section 조회로 확장하고
총 읽기량을 측정한다. 12KB 초과 자체로 사용자 승인이나 작업 중단을 요구하지 않는다.

registry도 관련 항목만 조회한다. 다른 영역의 기존 결정을 침범할 가능성을 발견하면
domain 또는 코드 참조로 조회 범위를 넓힌다. 선택된 입력이 프로젝트의 모든 사실이라는
가정은 하지 않는다.

### Plan 식별

새 plan은 `step-1.1`, `gate-1.1`, `phase-1-integration`, `whole-run` 같은 stable ID와
명시적 contract 시작/끝 marker를 사용한다. 각 record에는 목표, 완료 조건, 검증 방법,
관련 registry/decision key, 재량 범위, 선행 record, 검증 등급을 둔다.
phase 표의 순서를 기본 순서로 쓰며 선행 record가 verified인 작업만 실행 가능하다.
누락·중복 ID, 순환 의존, 의존 작업 뒤에 놓인 확산 gate는 validation failure다.
phase integration과 whole-run도 자신이 판정할 완료 조건을 가진다.

## 5. 최소 실행 상태와 checkpoint

새 cycle의 runtime 형식은 `state.json`의 `schema: 2`로 식별한다. begin/spec/audit 등
모든 문서를 같은 schema로 바꾸도록 요구하지 않는다.

state는 cycle, revision, plan contract digest, mode, cursor, record 상태와 최소 결과 포인터를
가진다. 현재 record에는 검증 대상 식별자, 실행 주체/작업 위치, round, 미해결 finding ID,
다음 행동, 중단 이유·재개 상태를 보존한다. 없는 agent·Git 정보는 null로 명시한다.
raw log와 라운드 서사는 넣지 않는다. 활성 record는 최대 하나다.
cursor는 활성 record를 가리키며, 없으면 plan 순서상 첫 실행 가능한 queued record를 가리킨다.
미해결 stopped record가 남아 있으면 해당 blocker를 표시하고 complete로 만들지 않는다.
L/XL 질문의 본문은 `pending/`에 보존하고 state에서 참조한다. 답을 결정 기록에 반영한 뒤
재개 상태를 저장하고 질문 파일을 정리한다. state와 mailbox가 어긋나면 답변 여부를 먼저 대조한다.

허용 흐름:

```text
step: queued → implementing → checking → verified
gate / phase / whole-run: queued → checking → verified
checking → fixing → checking
implementing / checking / fixing → stopped → 기록된 재개 상태
```

basic의 checking은 로컬 계약 검사다. fresh의 checking은 독립 verifier가 필요하다.
verified 전이는 검사 성공, 필수 fresh 판정, 관련 gate와 선행 조건을 확인한다.
독립 검증을 제공할 수 없거나 round cap이 소진되면 stopped이며 verified가 아니다.
모두 verified일 때만 cursor는 complete다. plan 변경은 현재 digest와 의존 관계를 재검증하고
영향받은 record/gate의 기존 성공을 무효화한다. 과거 성공 이력은 evidence에 보존한다.
무효화는 근거를 남기며 기존 finding의 round를 지우지 않는다. 아래 2026-09-13 사용자 보완에
따라 이미 구현된 record는 처음부터 queued로 되돌리는 대신 필요한 재검증으로 복구한다.

**2026-09-13 사용자 보완 — 같은 파일의 후속 변경:** 같은 `src.py`에 정상 consumer 코드를
추가하는 경우도 지원한다. 파일 해시 변화는 재검증 필요를 뜻하며 기반 계약 파괴 판정이나
과거 구현 재실행의 근거로 단정하지 않는다. 이미 검증한 producer/gate는 구현·검증 이력을
보존한 `stopped → checking` 경로로 복구하고, 진행 중 consumer의 target·context·재개 위치를
보존한다. 재검증이 성공하면 consumer를 이어가며, 실제 기반 파괴는 실패 finding으로 남겨
의존 작업을 계속 차단한다. 의미 분석기나 작업별 사용자 승인을 추가하지 않는다.
미응답 pending·기존 실패 cap은 이 복구 경로로 해제하지 않으며, 변경된 입력의 과거 검사·
독립 판정을 현재 성공으로 재사용하지 않는다. 이 보완은 원래 같은 파일 재현을 별도 파일
사례로 대체하지 말라는 사용자의 명시적 실행 지시를 반영한다.

helper는 expected revision 확인과 writer lock 아래 새 state를 검증하고 단일 파일을
atomic replace한다. evidence는 필요한 경우 새 immutable 파일을 먼저 기록하고,
그다음 state가 참조한다. 중간 중단으로 생긴 미참조 evidence는 완료 근거로 채택하지 않는다.
run/HANDOFF는 state 저장 후 생성한다. 생성 실패나 유실 시 다시 만들 수 있어야 한다.
Git 반영과 state 저장이 동시에 atomic하다고 주장하지 않는다.

재개 시 대상 코드·작업 위치·계약 digest를 확인한다. 다르면 완료를 추정하지 않고 영향과
기존 검증의 유효성을 확인한다. 검사 완료 후 state 저장 전 중단한 경우 필요한 검사를
재실행할 수 있다. 코드 롤백이나 커밋 재적용은 자동 복구의 기본 동작이 아니다.
state 자체가 손상되었으면 dispatch를 막고 보존된 코드·evidence로 복구를 진단한다.

checkpoint는 step/검증 round/gate 완료, 결정 대기, 사용자 중단, host의 context 부족 신호에
작성한다. host가 사용률을 제공하지 않으면 추측하지 않고 이 작업 경계를 사용한다.
mode는 저장된 선택을 재사용한다. 재개할 때마다 다시 묻지 않는다.

## 6. 변경 소유권과 host 지원

기본은 한 writer가 기존 작업 트리에서 순차 실행한다. 시작 시 기존 변경과 허용 범위를
확인하고 사용자 변경을 revert, stash, overwrite, 무차별 stage하지 않는다.
기존 미커밋 변경 보존은 새 작업도 영원히 미커밋으로 두라는 뜻이 아니다.
프로젝트의 커밋 정책과 사용자 권한 안에서 소유 변경만 선택적으로 커밋한다.

기존 dirty hunk와 작업이 겹치거나 별도 candidate 격리가 필요하면 worktree 또는 host의
격리 기능을 선택한다. worktree에는 필요한 미커밋 기준 코드가 자동으로 들어오지 않으므로
baseline을 명시한다. 소유권을 확인하지 못하면 임의 반영하지 않는다.
공유 트리는 비협조적 외부 writer의 완전한 귀속을 보장하지 않는다.

서브에이전트가 없는 host에서도 basic은 실행한다. fresh는 별도 독립 세션으로 넘길 packet을
생성하고 해당 경계에서 기다린다. 같은 context의 자기검토를 fresh로 표시하지 않는다.
모델 선택 기능이 있으면 fresh에 적합한 높은 추론 역량을 우선하되 특정 모델명을 필수화하지 않는다.
Git·hook·context 사용률 API는 기본 실행의 필수 조건이 아니다.
Python helper를 실행할 수 없으면 명시적으로 legacy/manual 경로를 사용하며,
schema 2 자동 검증과 bounded extraction을 제공했다고 주장하지 않는다.

## 7. 결정·registry·pipeline 부담 축소

- S는 영구 ADR을 만들지 않는다. M은 외부 동작·데이터 계약·공개 API·의미 있는 성능/비용
  제약처럼 미래 작업이 알아야 하는 선택만 기록한다. L/XL은 항상 비교 근거와 상태를 남긴다.
- 새 기록은 stable key와 immutable ID를 쓴다. active index의 key → record ID → 한 항목을
  조회한다. superseded·미승인 제안은 확정된 현재 결정으로 반환하지 않는다.
- legacy ledger 전체의 변환을 새 cycle 시작 조건으로 삼지 않는다. 이미 명확한 active
  pointer는 활용하고, 현재 작업과 관련된 애매한 결정만 조사·확인한다. 미해결이면 해당
  작업의 blocker로 표시한다. 과거 행을 추측으로 덮어쓰지 않는다.
- registry는 프로젝트별 `active | N/A`다. 기존 코드·타입·schema·lint를 재사용하고,
  자동으로 알 수 있는 사실을 별도 markdown에 중복 유지하도록 강제하지 않는다.
- 계획에서 공용으로 확정한 요소는 첫 사용부터 공용화한다. 그 외에는 첫 사용은 local,
  두 번째 실제 사용에서 승격 여부를 판단한다. 모양만 비슷하다는 이유로 추상화하지 않는다.
- foundation phase는 필요한 기반 변경이 있을 때만 만든다. 기존 구조의 재생성, 네 종류
  registry의 일괄 생성, 관련 없는 hook 설치를 강제하지 않는다.
- wellnext는 요청 분류를 먼저 한다. 작은 수정이면 pipeline을 생략하고 바로 처리한다.
  cycle이 필요하면 변경 영역을 audit하고, 광범위한 drift 근거가 있을 때 전체로 확장한다.
  audit 완료를 기다려야 작은 작업인지 판단할 수 있는 순서를 없앤다.
- 기존 사용자 승인·mode·프로젝트 관례를 재사용한다. 새로운 비싼 결정이나 범위 변경만
  필요한 확인을 거친다. autonomous의 provisional도 사용자가 부여한 권한 범위 안에서만 쓴다.

### Decision 읽기·쓰기 계약

정상 구현·재개·dispatch에서 `decisions.md` 전체를 모델에 전달하지 않는다.
helper는 파일 전체를 로컬에서 파싱할 수 있지만, 모델에는 요청한 활성 결정만 반환한다.
모델이 전체를 읽은 뒤 필요한 내용을 요약하는 방식은 선택 조회로 인정하지 않는다.
전체 원장 검토는 사용자가 요청한 감사 등 별도 작업에서만 수행한다.

- plan의 관련 결정은 날짜나 자연어 제목 대신 stable key로 지정한다.
  예: `theme.profile-defaults`, `theme.global-owner`. 예시 key는 실제 legacy 매핑을 뜻하지 않는다.
- 각 조회 결과는 key, record ID, grade, 승인/활성 상태, 현재 선택, 적용 범위·필수 제약,
  짧은 이유와 원문 포인터를 포함한다. 변경 역사·검증 서사·장문의 대안 비교는 기본 출력에서 뺀다.
- 새 결정의 기본 항목은 UTF-8 1KB 이하다. 상세 근거는 별도 참조로 둔다.
  필수 제약을 상한에 맞춰 삭제하지 않는다. 1KB에 담을 수 없는 계약은 필요한 상세 section을
  명시하고 작업 전 추가 조회한다. helper가 장문을 임의로 잘라 요약하지 않는다.
- 동일 packet에서 같은 decision ID는 한 번만 전달한다. plan·registry·HANDOFF가 같은
  결정을 참조해도 본문을 반복 삽입하지 않는다. 총량은 section 4의 packet 예산에 포함한다.
- key 미존재·중복 active pointer·미승인/상충 상태는 명시적으로 반환한다.
  not-found를 제약 없음으로 해석하거나 실패 시 전체 원장을 읽는 fallback은 금지한다.
  관련 domain의 key 목록 또는 특정 원문 후보를 좁혀 조사한다.
- 구현자 재사용 중 이미 읽은 결정은 ID와 내용 식별자가 그대로면 포인터로 대체할 수 있다.
  새 context에는 필요한 본문을 다시 제공하고, supersede 또는 내용 변경 시 갱신한다.

### Legacy 조회와 registry의 중복 설명

기존 352KB 원장은 삭제하거나 매번 요약하지 않는다. 현재 작업이 참조하는 결정부터
명확한 색인·원문 범위·supersede 근거로 선택 조회한다. 날짜 하나만으로 현재 결정을 확정하지 않는다.
긴 항목은 최초 관련 작업에서 현재 제약과 근거 포인터를 구분해 짧은 조회 항목으로 정리하고,
원문 위치와 내용 식별자를 함께 보존한다. 이후에는 그 항목을 재사용하며 원문 변경 시 재확인한다.
이는 선택적으로 만드는 조회용 표현이며 새로운 결정 승인이나 전체 ledger migration이 아니다.
active 여부나 의미가 모호하면 관련 부분만 조사하고, 실제 선택이 필요한 때 해당 결정만 확인한다.
legacy의 S 기록도 현재 코드에 필요한 제약을 담았다면 등급만 보고 제외하지 않는다.

registry에는 재사용 위치, 공개 계약, 반드시 지킬 현재 제약과 decision key를 남긴다.
결정 이유·실패 라운드·과거 변경 과정은 원문 포인터로 대체한다. 이렇게 옮긴 설명을
다른 요약 문서에 복제해서 기본 입력에 다시 넣지 않는다. 필수 제약을 포인터 뒤에 숨겨
구현자가 읽지 못하게 하지 않으며, 관련 제약은 registry 항목 또는 결정 조회 결과에 포함한다.
같은 원칙을 프로젝트의 AGENTS/CLAUDE 지침, plan, spec, HANDOFF와 dispatch template에 적용한다.
프로젝트 고유 지침은 보존하면서 플러그인이 추가한 무조건 전체 읽기 지시를 선택 조회로 바꾼다.

이 조회 개선은 state.json 전환과 독립적이다. 진행 중 legacy cycle에서도 artifact 형식을
유지한 채 적용할 수 있다. 도그푸딩 프로젝트의 실제 정리는 구현·적용 작업에 포함될 때 수행하며,
스펙 작성만으로 프로젝트 원장이나 registry를 변경하지 않는다.

## 8. Runtime와 기존 프로젝트 전환

작은 표준 라이브러리 기반 Python helper를 plugin에 배포한다. 공개 기능은 다음으로 제한한다.

```text
artifacts.py validate --root .wellbegun
artifacts.py context --root .wellbegun [--record <id>] [--section <name>]
artifacts.py transition --root .wellbegun --expected-revision <n> --input <file>
artifacts.py render --root .wellbegun
artifacts.py decision-get --root .wellbegun --key <key>
```

`decision-get`은 key 조회 실패 시 제한된 후보 key와 원문 포인터를 제공할 수 있다.
좁힌 domain 목록·원문 section 조회는 기존 context/decision-get 기능 안에서 제공하며,
전체 문서를 모델로 돌려주는 별도 fallback이나 범용 요약 서비스를 추가하지 않는다.

context는 상태·계약 연결을 검증하고 packet을 반환한다. transition은 관련 상태·선행/gate·
결과 참조를 검증한다. 관련 없는 모든 기획 문서와 전체 history를 매 write마다 검증하지 않는다.
출력 형식·오류 코드는 작고 명시적으로 유지하며 raw log를 정상 응답에 붙이지 않는다.
subagent 정상 보고는 상태, 대상 ID, 변경 범위, 검사 결과, 미해결 finding, 다음 행동만 담고
보통 300단어 이내로 한다. 상세 finding은 파일로 보존하며 상한 때문에 누락하지 않는다.

schema 없는 진행 중 cycle은 기존 artifact 형식으로 끝낸다. 반복 검사 제거·기존 권한
재사용 같은 형식 독립 정책은 적용할 수 있으나 새 gate/계약 변경은 명시적으로 반영한다.
state.json을 부분 도입하지 않는다. 다음 cycle부터 새 runtime 형식을 사용한다.
wellnext는 새 형식의 state·run·plan·관련 evidence를 함께 archive하고, 역사 문서를 변환하지 않는다.
decisions는 project 범위로 남긴다. 기존 review 문서는 이전 설계의 근거이며 새 요구사항이 아니다.

## 9. 구현 순서와 완료 기준

### A. 실행 정책부터 경량화

wellrun/wellplan 및 reversibility reference의 상충 문구를 함께 고친다. 구현자 재사용,
확산 gate, basic 완료 경로, 회귀 중복 제거, round와 unresolved 의미를 먼저 확정한다.
wellnext/wellspec/template의 전체 audit·필수 registry·S/M 일괄 기록도 함께 정리한다.

### B. 작은 상태와 선택 읽기 연결

helper와 최소 fixture를 만들고 실제 skill의 시작·전이·재개에 연결한다.
문구만 추가하고 모델이 여전히 plan/run/ledger 전체를 읽는 구현은 완료가 아니다.
run/HANDOFF 파생 생성과 legacy routing을 연결한다.
모든 lens와 dispatch의 decision 읽기 경로 및 registry·프로젝트 지침을 통한 중복 유입을
함께 확인한다. extractor만 구현하고 기존 전체 원장 읽기 지침이 남아 있으면 완료가 아니다.

### C. 동작과 비용 확인

필수 결정적 검사:

- basic은 verifier 없이 verified 가능, fresh/gate 미충족은 의존 작업 실행 불가.
- 기반 변경 시 gate 무효화, 같은 finding의 이름 변경으로 round 초기화 불가.
- 미해결 계약 위반은 cap 이후에도 verified가 되지 않음.
- state atomic 저장 전후 중단, 미참조 evidence, run/HANDOFF 유실에서 과거 작업을
  완료로 오인하지 않고 현재 상태를 복원하거나 명시적 복구 필요를 반환.
- 오래된 revision, 코드/계약 drift, 잘못된 ID·의존 관계를 검출.
- history를 10배 늘려도 같은 현재 작업 packet의 내용·크기가 증가하지 않음.
- overflow의 명시적 분할 조회, active 결정 조회, legacy 유지와 archive 동작 확인.
- 352KB급 legacy ledger, 4KB 장문 항목, 날짜가 같은 결정 여러 개, superseded·미승인·
  중복 pointer fixture에서 관련 현재 제약을 잃지 않고 제한된 결과 또는 명시적 모호성을 반환.
- 같은 결정을 plan·registry·HANDOFF가 참조해도 packet에는 한 번만 포함.
  원문 변경 시 조회 항목을 재확인하고, 필수 제약의 상세 조회가 끝나기 전 dispatch하지 않음.
- 서브에이전트 없음, Git 없음, N/A registry에서 지원 범위대로 동작.

도그푸딩은 작은 UI 변경과 L급 데이터 변경을 각각 같은 시작점·동등한 환경에서
기존/새 정책으로 비교한다. 실행 시간은 모델 변동 영향을 받으므로 관찰값과 추정치를 구분한다.
각 실행에서 첫 코드 수정까지의 시간, 전체 시간, 문서 입력 bytes(가능하면 tokens),
에이전트 호출 수, 동일 검사 반복 횟수, 생성·수정한 관리 문서량, 재작업과 발견 결함을 기록한다.

수용 조건:

- 정상 step 재개 packet 4–8KB 목표, 12KB 기본 상한 및 명시적 확장 준수.
- 도그푸딩의 테마 작업에서 관련 활성 결정만 입력에 포함하고, 무관한 로그인·지도·배지
  결정과 과거 구현 서사가 기본 입력에 들어오지 않음. 실제 의존 관계가 있으면 명시적으로 확장.
- 정상 step에서 전체 decisions 원장을 모델에 전달한 횟수 0회. registry를 통해 복제된
  역사 서사도 기본 packet에서 제외. 최초 legacy 정리 비용과 이후 반복 조회 비용은 분리 측정.
- 독립 S/M 작업마다 새 agent·fresh 검증·전체 suite가 자동 추가되지 않음.
- 동일 유효 입력의 검사 반복은 기본 0회; 예외에는 구체적 이유가 있음.
- 잘못된 초기 기반 가정을 넣은 fixture를 첫 consumer 전에 독립 검증 대상으로 보냄.
  실제 agent가 발견했는지는 도그푸딩 결과로 별도 보고하며 탐지 보장을 주장하지 않음.
- L급 변경에서 계약 위반과 미해결 상태를 숨기지 않음.
- 기존 대비 측정된 비용 변화와 품질 결과를 보고. 시간이 줄지 않으면 원인을 확인하고
  성능 목표 미달로 기록하며, 호출 수 감소만으로 시간 단축을 달성했다고 보고하지 않음.
- 저장소의 기존 `bash scripts/validate.sh`와 새 runtime 관련 fixture가 통과.

이 문서 revision 2의 방향과 구현 착수는 사용자가 승인했다. 이전 초안의 L 결정 목록을 그대로 승인 절차로
승계하지 않는다. 사용자가 합의한 경량화 방향을 유지하고, 이후 구현 중 새로운 권한이나
의미 있는 범위 확장이 필요한 경우에만 구체적인 변경을 제시한다.
