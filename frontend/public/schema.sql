-- schema.sql: SQLite schema for the AI Book Assistant (one file, local only).
PRAGMA foreign_keys = ON;

-- Catalog of books. The ISBN-13 is the primary key (team decision, Week 10).
CREATE TABLE IF NOT EXISTS books (
    isbn        TEXT PRIMARY KEY,            -- ISBN-13, unique book ID
    title       TEXT NOT NULL,
    author      TEXT NOT NULL,
    pages       INTEGER NOT NULL CHECK (pages > 0),
    year        INTEGER DEFAULT 2020,
    publisher   TEXT DEFAULT '',
    avg_rating  REAL DEFAULT 4.0,
    genres      TEXT NOT NULL DEFAULT '',    -- comma separated
    themes      TEXT NOT NULL DEFAULT '',    -- comma separated theme tags
    summary     TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_books_title  ON books(title);
CREATE INDEX IF NOT EXISTS idx_books_author ON books(author);

-- One row per book the reader tracks (library). Lifecycle state lives here.
CREATE TABLE IF NOT EXISTS library (
    isbn        TEXT PRIMARY KEY REFERENCES books(isbn),
    state       TEXT NOT NULL DEFAULT 'Unread'
                CHECK (state IN ('Unread','InProgress','Unfinished','Finished','Rated')),
    pages_read  INTEGER NOT NULL DEFAULT 0 CHECK (pages_read >= 0),
    rating      INTEGER CHECK (rating BETWEEN 0 AND 5),
    started_on  TEXT,
    finished_on TEXT
);

-- Notes and highlights appended to a book (max 3,000 characters, FR-17).
CREATE TABLE IF NOT EXISTS notes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    isbn        TEXT NOT NULL REFERENCES books(isbn),
    kind        TEXT NOT NULL CHECK (kind IN ('note','highlight')),
    body        TEXT NOT NULL CHECK (length(body) <= 3000),
    created_on  TEXT NOT NULL DEFAULT (date('now'))
);

-- Pages read per day: feeds goals, streaks and reading velocity.
CREATE TABLE IF NOT EXISTS reading_log (
    day         TEXT PRIMARY KEY,
    pages       INTEGER NOT NULL CHECK (pages >= 0)
);

-- Saved assistant conversations (compressed text, see FR-36).
CREATE TABLE IF NOT EXISTS chat_history (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    title       TEXT DEFAULT 'Conversation',
    isbn        TEXT REFERENCES books(isbn),
    transcript  TEXT NOT NULL,
    saved_on    TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Settings (daily goal, yearly goal, favourite genres, display name).
CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
