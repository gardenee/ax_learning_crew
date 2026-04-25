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

### 크루원 스타터 배포 — hand-maintained

`ax_learning_crew_students` (별도 디렉터리) 가 크루원 스타터의 source of truth. 멘토가 직접 maintain.

핵심 차이 — 이 답지 (`_crew`) vs 크루원 스타터 (`_students`):

| 영역 | _crew (답지) | _students (스타터) |
|---|---|---|
| `apps/api/app/agent/prompts/` | `session_01~06.py` 분리 (세션별 정답 스냅샷) + `__init__.py` 가 session_06 import | `__init__.py` 한 파일에 `SYSTEM_PROMPT` 직접 정의. 크루원이 매 세션 누적 수정 |
| 가이드 (`guide/`) | 마스터 8 파일 (`00_setup`, `01_overview`, `session-1~6.md`) + 옛 멘토용 자료 | 마스터 8 파일만 미러 (옛 자료 X) |
| 토글 / 코드 / tool / infra | 동일 | 동일 (mirror) |

학기 끝나고 답지 변경 시 — 크루원 스타터의 prompts 와 가이드를 멘토가 직접 갱신. 자동화 스크립트 없음.

### 프롬프트 — 답지 측 분리, 크루원 측 단일

답지 (`_crew`) 는 매 세션 시점 프롬프트를 `session_NN.py` 에 독립 작성 (스냅샷 archive). 런타임은 `session_06` 사용. 이건 답지 디버깅 / diff 비교 편의.

크루원 (`_students`) 은 단일 `__init__.py` 의 `SYSTEM_PROMPT` 한 변수에 누적 수정. 세션 6 진입 시점에만 `BASE_SYSTEM_PROMPT + EVAL_RULES` split 으로 변환 (self_check 토글 효과). 단일 파일이라 크루원 친화적.

### Docker 마이그레이션

`docker compose up` 시 `migrate` sidecar 가 `infra/db/migrations/*.sql` 을 순서대로 적용하고 `schema_migrations` 테이블에 기록한다. 볼륨이 이미 있어도 미적용 마이그레이션은 추가로 돈다. API 는 `migrate` 가 완료된 뒤 기동한다.

main-only 정책이라 마이그레이션은 "시간적 진화 기록" 이 아니라 **최종 스키마 하나**로 관리한다 — `001_init.sql` 에 전 세션 공통의 최종 스키마가 담겨있다. DDL 진화 과정(식당 테이블을 Qdrant 로 옮긴 세션 4 의 결정 등) 은 SQL diff 가 아니라 `guide/` 문서로 설명한다.

사용자 선호/식사 이력/온톨로지 개념 — 전부 **seed 없이 백지 상태로 시작**한다. `concepts` 는 `update_user_memory` 호출 시 on-demand 로 INSERT 되고, 선호는 세션 2 대화로 쌓는 것이 체험 포인트.

### 주의사항

- **실험 문서는 gitignore** (`plan/`). 크루원 공유 안 됨.
- **`guide/` 는 커밋 대상** — 크루원용 8 파일 (`00_setup`, `01_overview`, `session-1~6.md`) 이 마스터. 옛 멘토용 자료 (`00_curriculum.md`, `00_pre_setup.md`, `session-N/` 디렉터리 등) 는 답지 측 reference.
- 크루원 스타터 (`_students`) 갱신 시 체크: prompts 단일 파일 무결성, 가이드 8 파일 mirror, `.env` 비밀값 미포함, `.claude` / `plan` / 멘토 전용 자료 미포함.
