CREATE TABLE IF NOT EXISTS notebook_notes (
  app_id TEXT NOT NULL,
  id TEXT NOT NULL,
  title TEXT NOT NULL,
  body TEXT NOT NULL,
  folder TEXT NOT NULL,
  pinned INTEGER NOT NULL DEFAULT 0,
  updated INTEGER NOT NULL,
  PRIMARY KEY (app_id, id)
);
CREATE INDEX IF NOT EXISTS notebook_notes_recent ON notebook_notes (app_id, pinned DESC, updated DESC, id);
