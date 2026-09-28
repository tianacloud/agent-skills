CREATE TABLE IF NOT EXISTS board_notes (
  id TEXT PRIMARY KEY,
  board_id TEXT NOT NULL,
  x REAL NOT NULL,
  y REAL NOT NULL,
  title TEXT NOT NULL,
  body TEXT NOT NULL,
  color TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS board_notes_board
  ON board_notes (board_id);

CREATE TABLE IF NOT EXISTS board_links (
  id TEXT PRIMARY KEY,
  board_id TEXT NOT NULL,
  from_id TEXT NOT NULL,
  to_id TEXT NOT NULL,
  created_at TEXT NOT NULL,
  UNIQUE (board_id, from_id, to_id)
);

CREATE INDEX IF NOT EXISTS board_links_board
  ON board_links (board_id);

CREATE TABLE IF NOT EXISTS board_strokes (
  id TEXT PRIMARY KEY,
  board_id TEXT NOT NULL,
  points_json TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS board_strokes_board
  ON board_strokes (board_id);

CREATE TABLE IF NOT EXISTS board_profiles (
  board_id TEXT NOT NULL,
  client_id TEXT NOT NULL,
  display_name TEXT NOT NULL,
  PRIMARY KEY (board_id, client_id)
);
