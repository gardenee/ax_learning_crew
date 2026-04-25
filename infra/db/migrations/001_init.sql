-- 초기 스키마 — 모든 세션의 최종 형태.
-- main-only 정책이므로 학생은 이 파일 하나로 전체 DB 를 받는다.
-- 식당 메타는 Postgres 가 아니라 Qdrant (`restaurants` 컬렉션) 에 산다.

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE IF NOT EXISTS schema_migrations (
  version TEXT PRIMARY KEY,
  applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- === 기본 식별 ===

CREATE TABLE IF NOT EXISTS users (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  handle TEXT NOT NULL UNIQUE,
  display_name TEXT NOT NULL,
  default_location_alias TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- === 온톨로지 ===
-- concept 은 `update_user_memory` 호출 시 on-demand 로 INSERT 되는 키워드 노드.
-- 모든 concept 은 'food' 타입 (매운 거 / 국물 / 해산물 같은 메뉴·음식 카테고리).

CREATE TABLE IF NOT EXISTS concepts (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  key TEXT NOT NULL UNIQUE,
  label_ko TEXT,
  concept_type TEXT CHECK (concept_type IN ('food')),
  description TEXT
);

-- === 채팅 세션 / 메시지 ===

CREATE TABLE IF NOT EXISTS chat_sessions (
  id UUID PRIMARY KEY,
  title TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_chat_sessions_updated_at
  ON chat_sessions (updated_at DESC);

CREATE TABLE IF NOT EXISTS chat_messages (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  session_id UUID NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
  turn_index INTEGER NOT NULL,
  role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
  content JSONB NOT NULL,
  status TEXT NOT NULL DEFAULT 'completed'
    CHECK (status IN ('completed', 'aborted')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (session_id, turn_index)
);

CREATE INDEX IF NOT EXISTS idx_chat_messages_session
  ON chat_messages (session_id, turn_index ASC);

-- === 피드백 이벤트 ===
-- restaurant_* 는 Qdrant payload 의 place_id (TEXT) 를 가리키며 FK 없음.

CREATE TABLE IF NOT EXISTS feedback_events (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  candidate_restaurant_place_id TEXT,
  verdict TEXT CHECK (verdict IN ('liked', 'disliked', 'visited')),
  reason_tags TEXT[],
  free_text TEXT,
  created_by_user_id UUID REFERENCES users(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- === 선호 신호 ===
-- concept 에 대한 선호(국물류 좋아함) 또는 특정 식당에 대한 선호(이 가게 좋아함) 중 하나.

CREATE TABLE IF NOT EXISTS preference_signals (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  owner_id UUID NOT NULL REFERENCES users(id),
  signal_type TEXT CHECK (signal_type IN ('likes', 'dislikes')),
  concept_id UUID REFERENCES concepts(id),
  target_restaurant_place_id TEXT,
  target_restaurant_name TEXT,
  -- weight: 같은 식당 버튼을 반복 클릭하면 +1.0 씩 누적 (cap 5.0).
  --         세션 6 의 reinforcement 신호. concept 선호는 기본값 1.0 유지.
  weight NUMERIC DEFAULT 1.0,
  source TEXT DEFAULT 'manual',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT preference_signals_target_chk
    CHECK (concept_id IS NOT NULL OR target_restaurant_place_id IS NOT NULL)
);

CREATE UNIQUE INDEX IF NOT EXISTS preference_signals_user_concept_uq
  ON preference_signals (owner_id, signal_type, concept_id)
  WHERE concept_id IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS preference_signals_user_restaurant_uq
  ON preference_signals (owner_id, signal_type, target_restaurant_place_id)
  WHERE target_restaurant_place_id IS NOT NULL;

INSERT INTO schema_migrations (version) VALUES ('001_init')
  ON CONFLICT (version) DO NOTHING;
