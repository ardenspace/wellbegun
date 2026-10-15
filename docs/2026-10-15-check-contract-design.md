# 검사 계약 — 기계로 막을 수 있는 규약은 린트와 테스트로 옮기고 검증 라운드를 줄인다

- 작성일: 2026-10-15
- 상태: 설계 승인, 구현 계획 전
- 대상 버전: 0.7.0
- 근거: your-journey `lint-ci-pilot` 브랜치(커밋 `1b7c33b`, `55328dd`), `docs/2026-09-05-wellrun-round-cap-notes.md`, `docs/2026-09-12-lean-execution-validation.md`

## 목표

wellbegun이 쓰이는 프로젝트에서, 기계적으로 판별할 수 있는 결함은 프로젝트의 린터와 테스트가 잡게 하고, LLM 검증은 기계가 판별할 수 없는 부분에만 쓰게 한다. 그 결과로 검사 범위가 덮인 스텝은 독립 검증 라운드 상한을 3에서 2로 낮춘다.

프로젝트마다 스택이 다르므로(React Native, Next.js, Flutter 등) 스킬 본문은 스택과 무관하게 유지한다. 스택마다 다른 부분은 그 프로젝트 안의 설정 파일에만 남는다.

## 배경

### KBO 4.1의 11라운드

`docs/2026-09-05-wellrun-round-cap-notes.md`에 기록된 대로, 3~11라운드의 REJECT 사유는 모두 grep 기반 훅의 빈틈이었다. 텍스트로 패턴을 찾는 검사는 언어 문법을 모르기 때문에 표기를 바꾸면 피해 갈 수 있고, 그래서 빈틈이 끝없이 나왔다. 같은 규칙을 구문 트리를 읽는 언어 린터로 구현했다면 표기 우회가 불가능했다.

### wellbegun 자체의 G1 REJECT

`docs/2026-09-12-lean-execution-validation.md`의 G1-001~009는 모두 동작 결함이었다(gate 무효화 누락, 미응답 pending 우회 등). 이런 결함은 린트로는 잡을 수 없고, 계약을 옮긴 테스트가 있어야 잡힌다. 따라서 이 설계는 모든 라운드를 줄이지 않는다. 검사 계약이 실제로 덮는 범위의 라운드만 줄인다.

### your-journey 파일럿 (2026-10-15)

Expo 57 / React Native 0.86 / TypeScript 프로젝트에서 `.talpi/conventions.md`의 산문 규약을 ESLint 규칙으로 옮겼다.

| 항목 | 결과 |
|---|---|
| 옮긴 규약 | 6개 (생값 금지, `Text` 대신 `AppText`, expo-sqlite·expo-crypto 소유권, `app/` 별칭과 `src/` 상대 경로, UTC 날짜 자르기 금지) |
| 구현 수단 | `no-restricted-imports`, `no-restricted-syntax`만 사용. 커스텀 플러그인 없음 |
| 코드 양 | `eslint.config.js` 147줄, 규칙 테스트 195줄(30건) |
| 소요 시간 | 시각 기록으로 약 4분 |
| 현재 코드에서 잡힌 위반 | 3건(`JourneyPath.tsx`의 `borderRadius` 생값). 크기에서 계산하도록 고쳐서 해소 |
| 오탐 | 0건 |
| 옮기지 못한 규약 | 1개("settings 키는 settingsRepository 경유"). 린트로 표현하기 어려움 |

진행 중에 드러난 사실은 다음과 같다.

1. 규칙 테스트가 범위 결함을 잡았다. 생값 규칙을 처음에 `src/ui/`에만 걸었는데, 화면을 그리는 `src/db/provider.tsx`가 빠졌다는 것을 테스트가 알려 줬다.
2. 그 수정은 규약 해석이기도 했다. 규약 문서에는 "화면 코드"라고만 적혀 있어서 비화면 컴포넌트에도 적용할지는 판단이 필요했다.
3. 규칙은 리터럴만 잡는다. `const R = 6; borderRadius: R`처럼 상수를 거치면 통과한다.
4. flat config에서는 여러 설정 객체가 같은 파일에 적용될 때 규칙 옵션이 합쳐지지 않고 덮어써진다. 범위마다 옵션 전체를 다시 구성해야 했다.
5. Jest 안에서는 ESLint가 설정 파일을 동적 import로 읽지 못한다. 테스트에서 설정 객체를 직접 넘겨야 했다.

파일럿은 번역 비용과 규칙의 정확도를 보여 줬을 뿐, 라운드가 실제로 줄어드는지는 측정하지 않았다. 라운드 상한 2는 측정값이 아니라 정책으로 정하는 값이며, 다음 dogfooding에서 확인한다.

## 설계

### 1. wellspec Step 4: Enforcement plan → Check contract

**검사 명령 하나를 정한다.**

- 프로젝트에 이미 있는 명령을 먼저 찾는다(`npm run check`, `make check` 등).
- 없으면 기존 lint, 타입 검사, 테스트 명령을 묶는 명령을 만드는 작업을 plan에 넣는다. spec 단계에서 직접 만들지 않는다.
- spec에는 명령 문자열과 그 명령이 포함하는 것(lint / typecheck / test)만 적는다.
- 검사 명령은 실패하면 0이 아닌 종료 코드를 내야 한다. 경고는 실패로 보지 않는다.

**기계로 강제할 수 있는 규약을 셋으로 나눈다.** 입력은 begin/spec의 결정, 활성 레지스트리, 프로젝트에 이미 있는 규약 문서다.

| 분류 | 기준 | 예시 |
|---|---|---|
| lint | 구문 트리에서 위치와 형태로 판별할 수 있다 | 생값 금지, 모듈 import 소유권, 별칭 규칙 |
| test | 실행해야 판별할 수 있다 | 레포지토리 경유 규칙, 상태 전이, 데이터 계약 |
| review | 둘 다 어렵다. LLM 검증에 남긴다 | 상수를 거친 우회, 규약 해석, 데이터 흐름 전체 |

모든 규약을 분류할 필요는 없다. 이번 사이클이 건드리는 영역의 규약만 분류한다.

**lint로 분류한 규약은 규칙 테스트를 함께 둔다.** 규칙마다 잡아야 하는 예시와 통과해야 하는 예시를 하나 이상 두고, 실제 파일 경로를 넣어 범위까지 확인한다. 이 테스트도 검사 명령 안에서 실행된다.

**규약 해석은 결정으로 드러낸다.** 규약 문서의 문구가 적용 범위를 정하지 않으면(파일럿의 "provider.tsx에도 생값 금지를 적용하는가") 그 해석을 기존 등급 규칙으로 매긴다. 대부분 S/M이므로 spec에 짧게 남기고, 여러 영역에 퍼지는 해석만 사용자에게 묻는다.

**grep 스크립트는 마지막 수단이다.** 언어 린터로 표현할 수 없을 때만 `references/hooks/`의 스크립트를 쓴다. 그때는 "표기 우회를 막지 못하며, 이 검사의 빈틈은 REJECT 사유가 아니다"라는 한계를 spec에 함께 적는다.

**CI는 선택이다.** 검사 명령을 정한 뒤 CI 워크플로를 추가할지 plan에 적는다. 원격 저장소나 CI 권한이 없는 프로젝트는 로컬 실행만으로 완료 조건을 채운다.

**spec 템플릿**: `## Enforcement plan` 절을 다음으로 바꾼다.

```markdown
## Check contract
- command: `<one command>` (<lint | typecheck | test, as included>)
- lint: <convention> → <rule>, scope <globs>
- test: <convention> → <test location>
- review: <convention> — <why it cannot be mechanized>
- CI: <workflow path> | local only
```

델타 모드에서도 `command:`와 `CI:` 줄, 그리고 이번 사이클이 건드리는 영역의 항목은 바뀌지 않았더라도 다시 적는다. 검사 계약은 spec.md에만 있는데, spec.md는 사이클이 끝나면 보관 폴더로 옮겨지기 때문이다. 이번 사이클이 건드리지 않는 영역의 항목은 적지 않는다. `audit.md`의 `## Rule promotions`가 추가 입력이 된다(설계 3 참조).

### 2. wellplan: 스텝별 라운드 상한

wellplan은 각 fresh 스텝과 gate에 대해, 그 스텝의 완료 조건이 검사 계약의 lint/test 항목으로 덮이는지 판단한다.

- 덮이면 계약에 `"round_limit": 2`를 넣는다.
- 덮이지 않거나 review 항목이 핵심이면 필드를 생략한다(기본값 3).
- 판단 근거는 plan의 해당 스텝에 한 줄로 남긴다.

검사 계약을 구현하는 스텝(규칙과 규칙 테스트를 만드는 스텝)은 그 자체가 검사 계약에 덮이지 않으므로 3을 쓴다.

### 3. wellrun: 완료 조건과 검증 범위

**Basic 완료 조건.** "contract checks와 affected lint/analyze 통과"를 "spec의 검사 명령 통과와 해당 스텝의 계약 확인"으로 바꾼다. 검사 명령이 없는 legacy 사이클은 지금 규칙을 그대로 쓴다.

**fresh 검증 packet.** 검사 계약과 최신 검사 결과(명령, 종료 코드, 입력 식별자)를 넣는다. 검증자는 lint/test로 분류된 규약을 다시 확인하지 않고, 다음에 집중한다.

- 계약 해석과 계약의 빈틈
- review로 분류된 규약
- 완료 조건 가운데 테스트가 없는 부분
- 새로 생긴 L/XL 결정

**규칙의 빈틈에 대한 판정.** 검증자가 규칙의 빈틈 때문에 현재 코드에 실제 위반이 존재한다는 것을 재현하면 REJECT할 수 있다. 수정자는 코드를 고친다. "이론상 이렇게 우회할 수 있다"는 지적은 계약 밖 발견으로만 보고한다. grep 스크립트의 빈틈은 어느 경우에도 REJECT 사유가 아니다.

**규칙 후보 기록.** 검증자가 잡은 결함이 lint/test로 옮길 수 있는 종류라면, 수정자는 코드를 고치고 그 종류를 `.wellbegun/rule-candidates.md`에 한 줄로 남긴다(결함 ID, 종류, 옮길 수단). schema 2 사이클의 `run.md`는 상태 파일에서 다시 만들어지는 파일이라 직접 고칠 수 없으므로 별도 파일을 쓴다. wellnext가 사이클을 닫을 때 이 파일을 begin/spec과 함께 보관 폴더로 옮긴다. 사이클 중에 규칙을 새로 만들지 않는다. 수정 라운드가 보조 산출물만 키우는 것을 막는 0.4.1 규칙과 충돌하기 때문이다.

**라운드 상한.** 상한은 스텝 계약의 `round_limit`을 따른다. 상한에 도달한 뒤의 처리(추가 라운드 승인, 범위 변경, 미해결 보존)는 지금 규칙을 그대로 쓴다.

### 4. wellnext: 규칙 후보를 규칙으로 올리기

- **no pipeline** 판정의 작은 작업도 완료 전에 검사 명령을 실행한다. 지금의 "affected checks"를 검사 명령으로 구체화한다.
- Step 2 감사에서 `.wellbegun/rule-candidates.md`를 읽는다. 같은 종류가 두 번 이상 나왔거나, 한 번이어도 옮길 수단이 분명하면 `audit.md`의 `## Rule promotions`에 올린다.
- `audit.md`의 `## Enforcement status` 절은 검사 명령 결과로 바꾼다.

`audit.md` 템플릿 변경:

```markdown
## Check command
- `<command>`: pass | FAIL — <what broke>

## Rule promotions (input to wellspec delta step 4)
- **<defect kind>** — seen as <finding IDs>; lint | test via <means>
```

### 5. 런타임 (`scripts/artifacts.py`)

현재 라운드 상한 3은 런타임에 고정되어 있다(사이클 초기화, replan의 새 scope, 재검증 시 `round + 3`).

- 계약에 선택 필드 `round_limit`을 추가한다. 값은 정수 2 또는 3만 받는다. 그 밖의 값은 `invalid_plan`으로 거부한다.
- scope를 처음 만들 때 `limit`을 `round_limit`(없으면 3)으로 정한다.
- 이미 있는 scope의 `round_limit`이 replan에서 바뀌어도 `limit`은 바꾸지 않는다. 계약을 고쳐서 상한을 우회하는 것을 막기 위해서다. 상한을 늘리려면 지금처럼 `approve-rounds`를 쓴다.
- 검증된 기록이 실제 입력 변경으로 다시 열릴 때 늘어나는 폭(`round + 3`)은 그 scope의 기본 폭(`round_limit`, 없으면 3)을 따른다. 이 값을 scope 상태에 `allowance`로 저장한다. `allowance`가 없는 기존 상태는 3으로 읽는다.
- 필드가 없는 기존 plan과 상태 파일은 지금과 똑같이 동작한다.

추가할 테스트:

- `round_limit: 2`인 스텝이 2라운드 REJECT 후 멈추고, 추가 라운드 승인 없이는 진행하지 않는다.
- 필드가 없는 스텝은 3라운드를 유지한다.
- 1, 4, 문자열 같은 잘못된 값은 거부한다.
- replan에서 `round_limit`을 바꿔도 기존 scope의 `limit`은 그대로다.
- `round_limit: 2`인 검증 완료 기록이 다시 열리면 `round + 2`로 늘어난다.
- `allowance`가 없는 기존 상태 파일을 읽을 수 있다.

### 6. 참고 문서

**`references/check-contract.md` (신규)**

- lint / test / review 분류 기준과 예시
- 규칙 테스트의 최소 형태
- 스택별 도구 표(도구 이름만 적는다)

| 역할 | React Native / Next.js | Flutter | Python |
|---|---|---|---|
| 린트 | ESLint | `dart analyze` | ruff |
| 설정만으로 쓰는 금지 규칙 | `no-restricted-imports`, `no-restricted-syntax` | `analysis_options.yaml` | ruff `banned-api` |
| 커스텀 규칙 | ESLint 플러그인 | `custom_lint` 또는 analyzer 플러그인 | ruff는 미지원. 별도 AST 검사 |
| 타입 검사 | `tsc --noEmit` | `dart analyze`에 포함 | mypy / pyright |
| 테스트 | Jest / Vitest | `flutter test` | pytest |

- React(ESLint) 예시 하나: 파일럿의 규칙 형태, flat config에서 옵션이 덮어써지는 문제, Jest 안에서 설정 객체를 직접 넘기는 방법
- Flutter analyzer 플러그인처럼 방식이 바뀌고 있는 도구는 구현 시점의 공식 문서를 확인하라는 한 줄

**`references/hooks/README.md`**: 첫 문단에 grep 스크립트가 마지막 수단이며 표기 우회를 막지 못한다는 점을 추가한다.

**`references/runtime-contract.md`**: `round_limit`과 `allowance`를 설명하는 절을 추가한다.

## 호환성

- legacy 사이클과 0.6.0에서 만든 schema 2 사이클은 그대로 동작한다. 새 필드가 없으면 기존 규칙을 따른다.
- 검사 계약이 없는 프로젝트에서도 wellbegun은 동작한다. 그 경우 모든 스텝의 상한은 3이다.

## 검증

- `scripts/validate.sh`가 통과한다. 기존 테스트 88개와 새 런타임 테스트가 모두 통과한다.
- 스킬 문서 변경은 기존 구조 검사(frontmatter, `Use when` 설명, 금지 참조)를 통과한다.
- 효과 측정은 다음 dogfooding 사이클에서 한다. 비교 항목: 스텝별 라운드 수, 검증자가 lint/test 범위의 결함으로 REJECT한 횟수, 규칙 후보 수.

## 범위 밖

- 스택별 설정 템플릿과 프리셋
- CI 워크플로 자동 생성(plan의 선택 스텝으로만 둔다)
- 사이클 중간에 규칙을 새로 만드는 것
- 라운드 감소 효과의 정량 측정(다음 dogfooding으로 미룬다)
