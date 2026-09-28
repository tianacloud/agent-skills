CREATE TABLE IF NOT EXISTS study_tasks (
  id TEXT PRIMARY KEY,
  workspace_id TEXT NOT NULL,
  title TEXT NOT NULL,
  subject TEXT NOT NULL,
  estimated_minutes INTEGER NOT NULL,
  done_at TEXT
);

CREATE INDEX IF NOT EXISTS study_tasks_workspace
  ON study_tasks (workspace_id);

CREATE TABLE IF NOT EXISTS study_sessions (
  id TEXT PRIMARY KEY,
  workspace_id TEXT NOT NULL,
  started_at TEXT NOT NULL,
  minutes INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS study_sessions_recent
  ON study_sessions (workspace_id, started_at);

CREATE TABLE IF NOT EXISTS study_profile (
  workspace_id TEXT PRIMARY KEY,
  display_name TEXT NOT NULL
);
