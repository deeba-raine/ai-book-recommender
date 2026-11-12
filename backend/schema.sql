PRAGMA foreign_keys = ON;

-- All Books Table, uses Book-ID as Primary Key to Avoid Missing ISBN (I Found a Few Missing it - Jae)
CREATE TABLE IF NOT EXISTS books(
    id          INTEGER PRIMARY KEY,

    -- Display Information
    title       TEXT NOT NULL,
    author      TEXT NOT NULL,
    country     TEXT,
    language    TEXT,
    descr       TEXT DEFAULT '',
    isEBook     BOOLEAN DEFAULT false,
    cover       TEXT,
    publisher   TEXT NOT NULL,
    publDate    DATE NOT NULL,
    
    -- MetaData
    series      TEXT NOT NULL, -- Seperated by Commas; series titles
    tags        TEXT NOT NULL, -- Seperated by Commas
    similar     TEXT, --INTEGER Seperated by Commas
    pages       INTEGER NOT NULL CHECK (pages > 0),
    avgRating   REAL DEFAULT 0.0,

    notes       TEXT DEFAULT '' CHECK (length(notes) <= 3000)
    );
CREATE INDEX IF NOT EXISTS idx_book_title  ON books(title  COLLATE NOCASE);
CREATE INDEX IF NOT EXISTS idx_book_author ON books(author COLLATE NOCASE);

-- User Books Table, References all Books
CREATE TABLE IF NOT EXISTS library(
    id          INTEGER PRIMARY KEY REFERENCES books(id),

    -- Unstarted, InProgress, Finished, Unfinished, Rated
    state       INTEGER NOT NULL CHECK (state >= 0 AND state <= 5),
    rating      REAL DEFAULT NULL,
    progress    INTEGER DEFAULT 0,
    -- This is The Date of Addition, Not the Date of Progress
    startDate   DATE NOT NULL
);

-- Daily Reading Logs
CREATE TABLE IF NOT EXISTS reading_log (
    day         TEXT PRIMARY KEY,
    pages       INTEGER NOT NULL CHECK (pages >= 0),
    -- Whether or Not a Goal was Hit on a Given Day
    target      BOOLEAN DEFAULT false
);

-- Saved assistant conversations (compressed text, see FR-36).
CREATE TABLE IF NOT EXISTS chats (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    startDate   DATE NOT NULL,
    title       TEXT DEFAULT 'Conversation',
    reference   INTEGER REFERENCES books(id),
    transcript  TEXT NOT NULL
);

-- Reader notes and highlights, one row per note (FR-17, FR-31)
CREATE TABLE IF NOT EXISTS notes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id     INTEGER NOT NULL REFERENCES books(id),
    kind        TEXT NOT NULL DEFAULT 'note',
    body        TEXT NOT NULL CHECK (length(body) <= 3000),
    created_on  DATE NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_notes_book ON notes(book_id);

-- Settings-AKA User Data
CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
