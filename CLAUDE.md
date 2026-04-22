# Menu Agent — Claude Code 프로젝트 컨텍스트

## 프로젝트 개요

"오늘 뭐 먹지?" — Claude SDK tool_use 기반 점심 메뉴 추천 에이전트.
교육용 프로젝트이며, 세션마다 tool 을 하나씩 추가하면서 에이전트가 점점 똑똑해지는 과정을 체험한다.

## 아키텍처 핵심

- **에이전트 런타임**: Claude SDK (anthropic Python) + Anthropic API
- **에이전트 패턴**: tool_use loop (while loop 에서 stop_reason 확인)
- **오케스트레이션은 LLM 이, tool 내부 로직은 코드가 담당**
- **응답 형식**: structured block 배열 (message, recommendation_card, comparison_table, quick_actions, context_summary, form)

## Tool 목록

1. `get_user_memory` — Postgres 에서 사용자/그룹 선호 조회 (세션 2)
2. `update_user_memory` — 대화에서 나온 선호를 Postgres 에 기록 (세션 2)
3. `search_restaurants` — hard filter + hybrid RAG + rerank (세션 3)
4. `get_weather` — Open-Meteo 기반 현재 날씨 (세션 4)
5. `estimate_travel_time` — haversine 기반 도보 이동시간 (세션 4)
6. `ask_user` — 사용자에게 form 으로 추가 정보 요청 (세션 5)
7. `evaluate_response` — LLM-as-judge 기반 최종 응답 평가 (세션 6)

> 세션당 tool 개수는 학습 목표에 맞춰 유동적이다. "매주 tool 하나" 같은 고정 리듬은 없음.

## 기술 스택

- Frontend: React + TypeScript + Vite
- Backend: FastAPI + Pydantic
- DB: PostgreSQL (memory/metadata) + Qdrant (RAG)
- Infra: Docker Compose

## 디렉터리 구조

- `apps/api/` — FastAPI 서버 + 에이전트 + tool 함수 (스키마는 `/docs` Swagger 자동 제공)
- `apps/web/` — React 프런트엔드
- `infra/` — Docker, DB 마이그레이션
- `data/` — seed/fixture 데이터

## 코드 작성 규칙

- 사용자 요청 전에 커밋 금지
- Tool 함수는 `apps/api/app/tools/` 에 위치
- 에이전트 코어는 `apps/api/app/agent/` 에 위치

## 브랜치 정책 — main only

정답 코드는 **오직 `main` 브랜치** 에만 존재한다. v2(정답지)/v3(심화) 분기는 더 이상 쓰지 않는다. 모든 변경은 일단 main 에 쓴다.

### 수강생 스타터 배포 — `<student-fill>` 마커 + export

학생용 빈칸 처리는 **파일 안 마커** 로 한다:

```python
# <student-fill session="02" hint="설명">
<정답 코드>
# </student-fill>
```

`scripts/export_student.py --session N` 실행 시:
- `session="N"` 블록 → 빈칸 + TODO 로 치환
- `session<N` 블록 → 정답 유지 (cumulative)
- `session>N` 블록 → 블록 통째 제거

학생이 세션 N 을 시작할 때 받는 스타터는 이렇게 만들어진다.

### 프롬프트/진화하는 리소스

in-place 수정하지 말고 파일 분리: `apps/api/app/agent/prompts/session_NN.py`. 런타임은 항상 최신 (`session_06`) 만 사용한다. 각 파일은 **세션 N 시점의 프롬프트 전문(全文)** 으로 독립 작성한다 — BASE import chain 금지. 세션이 진행되며 규칙이 단순 append 가 아니라 **교체/오버라이드** 되는 지점 (예: 세션 4 의 자연어 대화체 → 세션 5 의 JSONL block) 을 한 파일에서 읽을 수 있어야 학생이 교체/비교가 쉽다. 학생 배포용 빈칸은 `<student-fill>` 마커로 감싼 블록 변수(예: `CHOICE_CHIPS_RULES`, `EVAL_RULES`) 를 `SYSTEM_PROMPT` 끝에 `+` concat 하는 방식을 유지한다.

### Docker 마이그레이션

`docker compose up` 시 `migrate` sidecar 가 `infra/db/migrations/*.sql` 을 순서대로 적용하고 `schema_migrations` 테이블에 기록한다. 볼륨이 이미 있어도 미적용 마이그레이션은 추가로 돈다. API 는 `migrate` 가 완료된 뒤 기동한다.

main-only 정책이라 마이그레이션은 "시간적 진화 기록" 이 아니라 **최종 스키마 하나**로 관리한다 — `001_init.sql` 에 전 세션 공통의 최종 스키마가 담겨있다. DDL 진화 과정(식당 테이블을 Qdrant 로 옮긴 세션 4 의 결정 등) 은 SQL diff 가 아니라 `guide/` 문서로 설명한다.

사용자 선호/식사 이력/온톨로지 개념 — 전부 **seed 없이 백지 상태로 시작**한다. `concepts` 는 `update_user_memory` 호출 시 on-demand 로 INSERT 되고, 선호는 세션 2 대화로 쌓는 것이 체험 포인트.

### 주의사항

- **실험 문서는 gitignore** (`plan/`). 학생 공유 안 됨.
- **`guide/` 는 커밋 대상** — 모든 수강생이 본다. 멘토 전용 노트는 파일 분리 후 `guide/internal/` 로 빼거나 배포 전 제거.
- **export 결과 zip 전 체크**: `.env` 비밀값, 내부 문서 미포함, `.git` commit 1개만 있는지, `guide/` 내 멘토 전용 자료 제거 여부.
