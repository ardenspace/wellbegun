---
status: approved
date: 2026-09-12
spec: docs/2026-09-12-lean-execution-bounded-context-spec.md
spec-revision: 2
---

# Lean execution — 구현 계획

## 기준과 범위

[스펙 revision 2](2026-09-12-lean-execution-bounded-context-spec.md)를 세 묶음으로 구현한다.
최우선은 에이전트의 입력·판단·절차 부담 감소다. 실행 시간과 결함 발견 능력을 함께 확인한다.
이 문서는 구현 순서와 완료 조건을 정하며, 현재 구현 완료나 스펙의 승인 상태를 뜻하지 않는다.

기존 skill 이름과 host manifest는 유지한다. mandatory worktree, Git ingestion transaction,
전체 legacy migration, 범용 캐시·요약 서비스는 만들지 않는다. 도그푸딩 원본은 읽기 전용으로
취급하고, 실제 변경 비교는 별도 임시 복사본에서 한다. 배포·설치 갱신은 이 계획의 범위 밖이다.

파일 경로는 저장소 기준이다. 새 Python helper와 테스트는 표준 라이브러리만 사용한다.
현재 `scripts/validate.sh`는 manifest와 skill 구조 검사만 하므로 동작 검증을 추가해야 한다.

| 묶음 | 결과 | 순서와 검증 경계 |
|---|---|---|
| A. 실행 정책 | 재사용·gate·검증·기록 규칙 일치 | A1 → A2 → 정책 조합 검토 |
| B. 선택 조회와 상태 | 작은 helper와 검증된 disk 계약 | B1 → B2 → B3 → 독립 기반 검증 G1 |
| C. 연결과 실측 | 실제 skill에서 사용, legacy 호환·비용 비교 | C1 → C2 → 최종 독립 검토 |

같은 묶음의 구현은 검증된 경계 안에서 구현자를 재사용할 수 있다. G1 통과 전에는
runtime 인터페이스를 다섯 skill에 확산하지 않는다. 독립 검증은 새 context에서 진행하며,
기존 검증 결과를 재사용하되 같은 명령을 관례적으로 반복하지 않는다.

## A. 실행 정책 경량화

### A1. 실행·검증 규칙 정리

- 변경: `plugins/wellbegun/skills/wellrun/SKILL.md`, `skills/wellplan/SKILL.md`,
  `references/reversibility-grades.md` (뒤 두 경로도 같은 plugin root 기준).
- 구현: basic 직접 완료, 경계 안 구현자 재사용, 새 기반의 producer/consumer gate,
  변경하는 결정 기준의 등급, 영향 범위 검사·결과 재사용, 임시 probe 우선 정책.
- 제거: fresh-per-step 강제, fresh 직전 전체 suite 의무, S ADR, cap 도달 시 자동 통과,
  구현 파일의 비주석 변경 유무로 완료를 추정하는 규칙.
- 완료 조건: 기존 L급 API 사용과 L급 API 변경을 구분하며, 같은 finding을 이름 변경으로
  초기화하지 않는다. 구현자는 언제 계속하고 언제 경계를 확인해야 하는지 바로 알 수 있다.
- 검증: 작은 UI 변경, 새 테마 기반 확산, round 3 실패의 세 시나리오로 지침을 대조한다.
  문구 복사 여부만 검사하는 테스트는 추가하지 않는다. `bash scripts/validate.sh` → exit 0.

### A2. 계획·결정·registry의 불필요한 절차 제거

- 변경: 다섯 skill의 해당 입력·출력 규칙, `references/registry-templates/*.md`,
  `references/reversibility-grades.md`, `references/hooks/README.md`.
- 구현: 관련 registry만 active, 불필요한 foundation 생략, planned-shared/실제 재사용 기준,
  요청 triage 후 관련 영역 audit, 저장된 mode·승인 재사용, 의미 있는 M만 영구 기록.
- 완료 조건: CLI에는 UI registry를 만들지 않고 작은 수정에는 cycle audit를 먼저 수행하지 않는다.
  새 결정의 key·ID·현재 제약과 상세 근거를 구분하며 날짜만으로 참조하지 않는다.
- 검증: A1과 연결해 모순을 확인한다. 기존 hook 코드는 필요한 결함이 발견되지 않으면 유지한다.
  helper 호출은 B가 검증된 후 C1에서 연결한다. 중간 상태를 완성된 release로 안내하지 않는다.

## B. 선택 조회와 최소 실행 상태

### B1. Disk·CLI 계약을 작은 실행 예제로 고정

- 신규: `plugins/wellbegun/scripts/artifacts.py`, `references/runtime-contract.md`,
  `tests/fixtures/` 아래 최소 plan·decision·state 예제.
- 구현: 스펙의 다섯 CLI 기능에 대해 입력·성공·오류 형식을 정의한다. plan marker,
  선행 관계와 gate, decision key/ID·상태, state 필수 필드, evidence 참조를 예제로 고정한다.
- 반드시 구체화: 최초 state 생성과 revision 검증, blocked record가 있는 cursor 선택,
  pending 답변 대조, 필수 추가 section을 읽었는지의 기록, verifier용 입력 분리,
  legacy 조회 항목의 저장 위치·원문 식별자·무효화 규칙. 상태 초기화도 기존 transition 기능
  안에서 처리하며 CLI 수를 늘리지 않는다.
- 완료 조건: queued → basic 완료, producer → gate → consumer, interrupted → resume,
  legacy decision 조회의 실제 입출력 예제가 있고 날짜·서술로 상태를 추측할 빈칸이 없다.
- 검증: 예제와 schema validation을 함께 실행 가능하게 만든다. 내부 모듈 분할은 구현자 재량이며,
  reference에는 실행에 필요한 계약만 쓴다. 스펙 전체를 다시 복제하지 않는다.

### B2. Decision·contract·registry 선택 조회

- 변경/신규: `scripts/artifacts.py`, `tests/test_context.py`, `tests/fixtures/` (plugin root 기준).
- 구현: 현재 contract 추출, active key → ID 조회, 좁힌 후보·section 조회, 동일 결정 중복 제거,
  1KB 결정 항목과 12KB 기본 packet 한도, overflow 뒤 필수 제약의 명시적 확장.
- legacy: 352KB급 원장을 모델에 넘기지 않고 관련 원문만 조회한다. 장문 의미 정리는 필요한
  항목에 한해 에이전트가 수행하고 helper는 원문 연결·유효성을 검사한다. 자동 의미 요약은 하지 않는다.
- 완료 조건: unknown/ambiguous/superseded/proposed를 구분한다. registry에 같은 결정 설명이
  있어도 중복 역사 서사가 packet에 들어오지 않는다. 필요한 legacy S 제약은 보존한다.
- 검증: `python3 -m unittest discover -s plugins/wellbegun/tests -p 'test_context.py'` → exit 0.
  10배 history, 4KB 단일 행, 같은 날짜의 여러 결정, 원문 변경, 누락·중복 key,
  다중 문서 참조, 필수 상세 section, 새 context의 본문 재전달을 검사한다.
  fixture는 합성·최소화하며 실제 프로젝트 원장 전체를 plugin에 복사하지 않는다.

### B3. 상태 전이·checkpoint·검증 유효성

- 변경/신규: `scripts/artifacts.py`, `tests/test_state.py`, `tests/fixtures/`.
- 구현: 단일 state의 lock/revision/atomic replace, evidence 선기록, run/HANDOFF 파생 생성,
  상태 복구 대조, basic/fresh 완료 구분, gate 무효화와 round/finding 보존.
- 검사 재사용: 대상 내용·명령·테스트·관련 환경 식별 정보를 검증한다. dirty HEAD만으로
  동일 대상을 판정하지 않고, 외부 상태가 불확실하면 재사용 불가를 반환한다.
- 완료 조건: 실패·cap·검증 수단 부재를 verified로 저장하지 않는다. 기반 변경 후 consumer가
  기존 gate 성공을 재사용하지 못한다. Git 자동 롤백·커밋 재적용은 수행하지 않는다.
- 검증: `python3 -m unittest discover -s plugins/wellbegun/tests -p 'test_state.py'` → exit 0.
  stale revision, state 저장 전후 중단, 미참조 evidence, 파생 문서 유실, pending 불일치,
  코드/계약 drift, gate 무효화, round 우회, 손상된 state를 검사한다.

### G1. 독립 기반 검증 — C1의 선행 조건

새 verifier가 스펙의 관련 계약, B의 코드/diff, fixture와 실행 명령만 받아 확인한다.
구현자의 자기평가와 이전 verifier 서사는 전달하지 않는다.

- producer의 잘못된 기반을 first consumer 전에 gate가 막는가?
- required decision/section 누락, supersede, context 재생성에서 필수 제약이 사라지지 않는가?
- 중단·dirty tree·invalid evidence에서 완료를 잘못 추정하지 않는가?
- legacy와 없는 host 기능 때문에 지원 가능한 basic까지 막지 않는가?

`python3 -m unittest discover -s plugins/wellbegun/tests`의 유효 결과를 제공한다.
verifier는 불신하는 경계만 추가 확인할 수 있다. 계약 위반을 수정하고 이 gate가 통과한 뒤
C1을 시작한다. 이후 공개 계약이 바뀌면 G1의 해당 검증도 무효화한다.

## C. 실제 연결과 도그푸딩

### C1. 모든 lens·재개·archive 경로 연결

- 변경: 다섯 `SKILL.md`, 관련 reference/template, `scripts/validate.sh`, `README.md`.
- 신규: `plugins/wellbegun/tests/test_lifecycle.py`.
- 구현: bootstrap/context, decision lookup, transition, run/HANDOFF 생성, next-cycle archive를
  검증된 helper에 연결한다. plugin root 기준 경로를 쓰고 실행 위치에 의존하지 않는다.
- legacy는 기존 cycle 상태 형식을 유지하면서 선택 조회를 사용한다. 새 cycle부터 state를
  생성한다. Git 없음·Python 없음·subagent 없음의 실제 지원 범위와 fallback을 명시한다.
- AGENTS/CLAUDE 생성 지침과 dispatch도 관련 항목 조회로 바꾼다. user-owned 지침을
  무차별 교체하지 않는다. 모든 skill에 runtime reference 전체 읽기를 추가하지 않는다.
- 완료 조건: helper가 있지만 모델이 원장 전체를 읽는 경로가 남지 않는다. pending/stopped가
  있으면 cycle close를 막고, archive 뒤 current packet에 과거 cycle이 들어오지 않는다.
- 검증: 임시 프로젝트에서 new → basic → gate → resume → complete → archive lifecycle,
  legacy 진행 유지, CLI/라이브러리 N/A registry를 실행한다. skill의 명령 예제도 실제 실행한다.
  `bash scripts/validate.sh`에 unittest discovery를 연결해 구조·동작 검사를 한 번에 수행한다.

### C2. 입력 비용과 실제 구현 비교

- 신규 결과: `docs/2026-09-12-lean-execution-validation.md` (실측할 때 작성).
- 먼저 read-only로 KBO 관련 테마 결정·registry 입력을 추출한다. 최초 legacy 정리 비용과
  이후 조회 비용을 분리하고 전체 원장 유입 0회, 정상 packet 4–8KB 목표/12KB 상한을 확인한다.
- 작은 UI 변경과 L급 데이터 변경을 별도 임시 복사본의 동일 시작 코드·작업 계약으로 비교한다.
  기존/새 정책, host/model, 의존성·환경, 시작 revision, 명령을 결과에 기록한다.
  사용자 원본 변경·외부 배포·실서비스 데이터 조작 없이 재현 가능한 fixture/emulator를 쓴다.
- 측정: 첫 수정까지/전체 시간, 문서 입력 bytes(가능하면 tokens), agent 호출, 검사 반복,
  관리 문서량, 재작업, 발견·누락 결함. wall-clock과 비용 감소 추정을 구분한다.
- 초기 기반 결함을 의도적으로 넣은 사례에서 consumer 전 독립 검증 여부와 실제 탐지 여부를
  각각 보고한다. 결정적 fixture 통과를 agent의 탐지율 증명으로 대신하지 않는다.
- 완료 조건: 측정 결과가 있고 품질 퇴행·미해결 계약 위반을 숨기지 않는다. 비교 실행이 불가능하면
  이유와 미측정 항목을 남기며 C2를 완료 처리하거나 시간 단축을 달성했다고 주장하지 않는다.

## 최종 검토와 인계

G1의 통과 결과와 C1의 유효 검사를 재사용해 최종 fresh 검토를 수행한다. 새 검토는 전체
동작의 조합, 실제 읽기 경로, legacy 보존, 미해결 결과와 실측 해석을 확인한다.
같은 소스·명령·환경의 전체 suite를 phase와 whole-run이라는 이름으로 반복하지 않는다.

`bash scripts/validate.sh` 통과, G1·최종 독립 검토 완료, C2 결과 보고가 완료 조건이다.
결과 문서에 구현 완료와 성능 목표 충족 여부를 구분한다. README에는 실제 제공 기능과 한계만
반영한다. 계획 단계에서 새 run/evidence/decision ledger를 만들어 관리 문서를 늘리지 않는다.
