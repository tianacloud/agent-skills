CREATE TABLE IF NOT EXISTS journey_settings (
  id TEXT PRIMARY KEY,
  phase TEXT NOT NULL,
  week_number INTEGER NOT NULL,
  started_at TEXT NOT NULL,
  mom_name TEXT NOT NULL DEFAULT '妈妈',
  dad_name TEXT NOT NULL DEFAULT '爸爸'
);

CREATE TABLE IF NOT EXISTS journey_progress (
  journey_id TEXT NOT NULL,
  task_id TEXT NOT NULL,
  completed_at TEXT NOT NULL,
  PRIMARY KEY (journey_id, task_id)
);

CREATE TABLE IF NOT EXISTS journey_comments (
  id TEXT PRIMARY KEY,
  journey_id TEXT NOT NULL,
  task_id TEXT,
  author TEXT NOT NULL,
  body TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS journey_comments_recent
  ON journey_comments (journey_id, created_at DESC);

INSERT OR IGNORE INTO journey_settings (id, phase, week_number, started_at)
VALUES ('main', 'prepare', 1, date('now'));
