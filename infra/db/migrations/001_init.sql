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

CREATE TABLE IF NOT EXISTS groups (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  name TEXT NOT NULL,
  kind TEXT NOT NULL CHECK (kind IN ('ad_hoc', 'project', 'team')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS group_members (
  group_id UUID REFERENCES groups(id),
  user_id UUID REFERENCES users(id),
  role TEXT,
  PRIMARY KEY (group_id, user_id)
);

CREATE TABLE IF NOT EXISTS projects (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  code TEXT NOT NULL UNIQUE,
  name TEXT NOT NULL,
  active BOOLEAN NOT NULL DEFAULT true
);

-- === 선호 프로필 ===

CREATE TABLE IF NOT EXISTS preference_profiles (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  owner_type TEXT NOT NULL CHECK (owner_type IN ('user', 'group', 'project')),
  owner_id UUID NOT NULL,
  spice_tolerance TEXT,
  budget_min INTEGER,
  budget_max INTEGER,
  max_walk_minutes INTEGER,
  max_meal_minutes INTEGER,
  notes TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (owner_type, owner_id)
);

-- === 온톨로지 ===

CREATE TABLE IF NOT EXISTS concepts (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  key TEXT NOT NULL UNIQUE,
  label_ko TEXT,
  concept_type TEXT CHECK (concept_type IN ('food', 'context', 'constraint', 'mood', 'service')),
  description TEXT
);

CREATE TABLE IF NOT EXISTS concept_aliases (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  concept_id UUID REFERENCES concepts(id),
  alias TEXT NOT NULL,
  locale TEXT DEFAULT 'ko'
);

CREATE TABLE IF NOT EXISTS concept_edges (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  source_concept_id UUID REFERENCES concepts(id),
  target_concept_id UUID REFERENCES concepts(id),
  relation_type TEXT CHECK (relation_type IN ('related_to', 'broader_than', 'good_for', 'opposite_of')),
  weight NUMERIC DEFAULT 1.0
);

-- === 채팅 세션 / 메시지 ===

CREATE TABLE IF NOT EXISTS chat_sessions (
  id UUID PRIMARY KEY,
  title TEXT,
  mode TEXT,
  initiated_by_user_id UUID,
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

-- === 이벤트 ===
-- restaurant_* 는 Qdrant payload 의 place_id (TEXT) 를 가리키며 FK 없음.
-- restaurant_name 은 UI 표시·디버깅용 스냅샷 (Qdrant 왕복 없이 이름 보이게).

CREATE TABLE IF NOT EXISTS recommendation_runs (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  initiated_by_user_id UUID REFERENCES users(id),
  mode TEXT,
  group_id UUID,
  input_snapshot JSONB,
  derived_context JSONB,
  chosen_restaurant_place_id TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS meal_events (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  actor_user_id UUID REFERENCES users(id),
  group_id UUID,
  restaurant_place_id TEXT,
  restaurant_name TEXT,
  occurred_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  meal_kind TEXT DEFAULT 'lunch',
  context_snapshot JSONB
);

CREATE TABLE IF NOT EXISTS feedback_events (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  recommendation_run_id UUID REFERENCES recommendation_runs(id),
  candidate_restaurant_place_id TEXT,
  verdict TEXT CHECK (verdict IN ('selected', 'liked', 'disliked', 'visited')),
  reason_tags TEXT[],
  free_text TEXT,
  created_by_user_id UUID REFERENCES users(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- === 선호 신호 ===
-- concept 에 대한 선호(국물류 좋아함) 또는 특정 식당에 대한 선호(이 가게 좋아함) 중 하나.

CREATE TABLE IF NOT EXISTS preference_signals (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  owner_type TEXT NOT NULL,
  owner_id UUID NOT NULL,
  signal_type TEXT CHECK (signal_type IN ('likes', 'dislikes', 'avoids', 'prefers_context')),
  concept_id UUID REFERENCES concepts(id),
  target_restaurant_place_id TEXT,
  target_restaurant_name TEXT,
  weight NUMERIC DEFAULT 1.0,
  source TEXT DEFAULT 'manual',
  confidence NUMERIC DEFAULT 1.0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT preference_signals_target_chk
    CHECK (concept_id IS NOT NULL OR target_restaurant_place_id IS NOT NULL)
);

CREATE UNIQUE INDEX IF NOT EXISTS preference_signals_user_concept_uq
  ON preference_signals (owner_type, owner_id, signal_type, concept_id)
  WHERE concept_id IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS preference_signals_user_restaurant_uq
  ON preference_signals (owner_type, owner_id, signal_type, target_restaurant_place_id)
  WHERE target_restaurant_place_id IS NOT NULL;

INSERT INTO schema_migrations (version) VALUES ('001_init')
  ON CONFLICT (version) DO NOTHING;
