# 오늘 뭐 먹지? — Menu Agent

Claude SDK `tool_use` 루프 기반 점심 메뉴 추천 에이전트. 사용자의 선호·제약·위치·날씨를 고려해 주변 식당을 찾아주고, 부족한 정보가 있으면 form 으로 되묻는다.

- **Frontend**: React 19 + TypeScript + Vite (SSE 스트리밍 UI)
- **Backend**: FastAPI + Anthropic Python SDK
- **Storage**: PostgreSQL (선호/이력/세션) + Qdrant (식당·메뉴 RAG)
- **Runtime**: Docker Compose 한 방에 기동

---

## 기능

- **대화형 메모리** — 대화 중 "나 해산물 싫어", "분식 좋아" 같은 발화를 감지하면 `update_user_memory` 로 기록해 다음 세션에서 자동 반영.
- **Hybrid 검색** — Qdrant 에서 dense + sparse hybrid 후 rerank. hard filter(예산, 거리, 카테고리 배제) 이후 soft preference 로 랭킹.
- **컨텍스트 반영** — 현재 날씨(Open-Meteo), 랜드마크 기준 도보 이동시간(haversine) 을 tool 로 가져와 추천에 반영.
- **Generative UI** — 에이전트가 JSONL atomic block 으로 응답을 스트리밍하면 FE 는 `message` / `recommendation_card` / `comparison_table` / `quick_actions` / `form` 블록으로 렌더링.
- **자가 평가** — `evaluate_response` tool 로 최종 응답을 LLM-as-judge 로 점검 후 방출.

## 아키텍처

```
┌────────────┐   SSE    ┌─────────────┐   tool_use loop   ┌───────────────┐
│  React UI  │ ───────▶ │ FastAPI     │ ────────────────▶ │ Anthropic API │
│ (port 3000)│ ◀─────── │ (port 8000) │ ◀──────────────── │   (Claude)    │
└────────────┘  stream  └─────┬───────┘    tool results   └───────────────┘
                              │
                ┌─────────────┼──────────────┐
                ▼             ▼              ▼
          ┌──────────┐ ┌─────────────┐ ┌──────────────┐
          │ Postgres │ │   Qdrant    │ │ Open-Meteo   │
          │  memory  │ │ RAG vectors │ │   weather    │
          └──────────┘ └─────────────┘ └──────────────┘
```

오케스트레이션은 LLM 이, 각 tool 내부 로직은 코드가 담당한다. 에이전트 루프는 `stop_reason` 이 `tool_use` 인 동안 tool 을 실행하고 `messages` 에 결과를 붙여 재호출하며, `end_turn` 에서 종료된다.

### Tool 목록

| Tool | 역할 |
|---|---|
| `get_user_memory` | 사용자의 선호·제약·최근 식사 이력을 Postgres 에서 조회 |
| `update_user_memory` | 대화에서 추출한 선호 시그널을 `preference_signals` 에 기록 |
| `search_restaurants` | hard filter + Qdrant hybrid 검색 + rerank |
| `get_weather` | Open-Meteo 로 현재 날씨 조회 |
| `estimate_travel_time` | 랜드마크 기준 도보 이동시간 계산 |
| `ask_user` | 부족한 정보를 form 블록으로 사용자에게 질문 |
| `evaluate_response` | 최종 응답의 근거/제약 준수 여부를 LLM-as-judge 로 자가 평가 |

## 요구사항

- Docker Desktop 또는 Rancher Desktop (Memory ≥ 6GB)
- Anthropic API Key

## 기동

```bash
cp .env.example .env
# .env 의 ANTHROPIC_API_KEY 를 채운다
docker compose up --build -d
```

첫 기동은 10~15분 걸린다 — 임베딩 모델(`multilingual-e5-large`, 약 1.5GB) 을 이미지에 포함하기 때문. 이후 build 는 캐시로 수초 내 완료.

기동되는 서비스:

| 서비스 | 종류 | 포트 | 역할 |
|---|---|---|---|
| `web` | 상주 | 3000 | React 프런트엔드 |
| `api` | 상주 | 8000 | FastAPI + 에이전트 런타임 |
| `postgres` | 상주 | 5432 | 메모리/메타데이터 |
| `qdrant` | 상주 | 6333 | 벡터 인덱스 |
| `adminer` | 상주 | 8080 | Postgres 웹 뷰어 |
| `migrate` | sidecar | - | `infra/db/migrations/*.sql` 자동 적용 후 종료 |
| `qdrant-init` | sidecar | - | `data/qdrant_snapshots/*.snapshot` 자동 복원 후 종료 |

### Health check

| | URL |
|---|---|
| 프런트엔드 | http://localhost:3000 |
| API Swagger | http://localhost:8000/docs |
| API health | http://localhost:8000/health |
| Adminer | http://localhost:8080 |
| Qdrant Dashboard | http://localhost:6333/dashboard |

첫 접속 시 "뭐라고 불러드릴까요?" 모달에 이름을 입력하면 `users` row 가 생성되고, 이후 대화에서 `get_user_memory` / `update_user_memory` 로 선호가 축적된다.

## API

### `POST /api/agent/run` — SSE 스트림

에이전트 루프 실행. 응답은 `text/event-stream` 이며 각 이벤트는 `data: {json}\n\n` 형식.

```bash
curl -N -X POST http://localhost:8000/api/agent/run \
  -H "Content-Type: application/json" \
  -d '{
    "initiated_by_user_id": "<uuid>",
    "participant_ids": ["<uuid>"],
    "user_message": "오늘 점심 추천해줘"
  }'
```

주요 이벤트 타입:

| Type | 설명 |
|---|---|
| `session` | 스트림 시작 시 1회 (`session_id`) |
| `reasoning_start` / `delta` / `end` | tool_use 턴의 진행 해설 |
| `tool_status` | tool 실행 start/done (`input` 포함) |
| `message_start` / `delta` / `end` | 사용자 향 텍스트 메시지 |
| `recommendation_card`, `comparison_table`, `quick_actions`, `context_summary`, `form` | Generative UI atomic block |
| `done` | 스트림 종료 (`debug_info` 포함) |
| `error` | 예외 발생 |

### 기타 엔드포인트

- `GET /api/agent/sessions` — 사이드바용 최근 대화 목록
- `GET /api/agent/sessions/{session_id}` — 세션 상세 (복원용 turn 배열)
- `POST /api/feedback` — 피드백 기록
- `POST /api/users` / `GET /api/users/{id}` — 사용자 생성/조회

전체 스키마는 `/docs` Swagger 참고.

## 데이터

- **Postgres** — 기동 시 `001_init.sql` 로 스키마만 생성. `users`, `concepts`, `preference_signals` 등 전 테이블은 **백지 상태로 시작**하며 첫 접속과 대화로 채워진다.
- **Qdrant** — `data/qdrant_snapshots/{restaurants,menus}.snapshot` 이 `qdrant-init` 에 의해 자동 복원된다 (현재 시드 기준 restaurants ≈ 611, menus ≈ 1419).

## 개발

```bash
make up          # docker compose up --build (foreground)
make up-d        # background
make down        # 컨테이너 정리
make reset       # 볼륨까지 삭제 (완전 초기화)
make logs        # api 로그 follow
make test        # API pytest
make web-test    # web jest
make lint        # ruff + eslint
make shell-api   # api 컨테이너 접속
```

디렉터리 레이아웃:

```
apps/
  api/               # FastAPI + 에이전트
    app/
      agent/         # 런타임 (runner, system_prompt, tools_registry, block parser)
      tools/         # 7개 tool 구현
      api/routes/    # /api/agent, /api/users, /api/feedback
      repositories/  # Postgres access
      services/      # 검색·메모리 도메인 서비스
  web/               # React + Vite
    src/
      pages/         # SessionPage, PreviewPage
      components/    # cards, compare, inputs, message, shell ...
infra/db/migrations/ # 001_init.sql (최종 스키마)
data/                # qdrant snapshots, seed fixtures
```

에이전트 런타임 진입점은 `apps/api/app/agent/runner.py::run_agent_stream` 이다. 새 tool 을 추가하려면:

1. `apps/api/app/tools/<name>.py` 에 `handle(input: dict) -> dict` 구현
2. `tools_registry.py::TOOL_DEFINITIONS` 에 JSON Schema append
3. `TOOL_HANDLERS` 에 `name → handler` 매핑 추가

## 환경 변수

`.env.example` 참고. 필수 값은 `ANTHROPIC_API_KEY` 하나이며, 나머지(`MODEL_ID`, `MAX_TOOL_TURNS`, 포트 등) 는 기본값으로 동작한다.

## 트러블슈팅

| 증상 | 원인 / 처방 |
|---|---|
| `401 authentication_error` | `ANTHROPIC_API_KEY` 오타 또는 비활성. `.env` 재확인 후 재기동 |
| `403 credit balance is too low` | API Key 워크스페이스 크레딧 부족 |
| `NotFoundError ... model` | `MODEL_ID` 오타 |
| `Port already in use` | 3000/8000/5432 점유. `.env` 의 포트 변경 또는 기존 프로세스 종료 |
| `.env` 수정이 반영 안 됨 | 컨테이너는 기동 시점에만 `.env` 를 읽음. `docker compose down && up -d` 재기동 |
| Qdrant 컬렉션이 비어있음 | `docker compose logs qdrant-init` 로 복원 실패 원인 확인 |
