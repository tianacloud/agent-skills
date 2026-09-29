CREATE TABLE IF NOT EXISTS ledger_entries (
  app_id TEXT NOT NULL,
  id TEXT NOT NULL,
  title TEXT NOT NULL,
  cents INTEGER NOT NULL,
  type TEXT NOT NULL,
  category TEXT NOT NULL,
  date TEXT NOT NULL,
  note TEXT NOT NULL DEFAULT '',
  PRIMARY KEY (app_id, id)
);
CREATE INDEX IF NOT EXISTS ledger_entries_month ON ledger_entries (app_id, date, id);
