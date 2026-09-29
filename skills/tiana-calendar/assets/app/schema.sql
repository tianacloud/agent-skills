CREATE TABLE IF NOT EXISTS calendar_events (
  app_id TEXT NOT NULL,
  id TEXT NOT NULL,
  title TEXT NOT NULL,
  date TEXT NOT NULL,
  start TEXT NOT NULL,
  end TEXT NOT NULL,
  category TEXT NOT NULL,
  location TEXT NOT NULL DEFAULT '',
  note TEXT NOT NULL DEFAULT '',
  PRIMARY KEY (app_id, id)
);
CREATE INDEX IF NOT EXISTS calendar_events_range ON calendar_events (app_id, date, start, id);
