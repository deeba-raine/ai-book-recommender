"""database_manager.py: Creational pattern, Singleton (Design Pattern 1).

Exactly one DatabaseManager exists per process, so only one SQLite
connection is ever open (NFR-10). Every query is parameterized (NFR-11).
"""
import sqlite3
import threading
from pathlib import Path


class DatabaseManager:
    _instance = None                    # holds the single shared instance
    _lock = threading.Lock()            # makes first creation thread safe

    def __new__(cls, *args, **kwargs):
        raise RuntimeError("Use DatabaseManager.get_instance()")

    @classmethod
    def get_instance(cls, db_path="books.db"):
        with cls._lock:
            if cls._instance is None:
                obj = object.__new__(cls)
                obj._connect(db_path)
                cls._instance = obj
        return cls._instance

    @classmethod
    def present(cls, db_path=None) -> bool:
        path = Path(db_path) if db_path is not None else Path(__file__).with_name("books.db")
        return path.is_file()

    def _connect(self, db_path):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.cur = self.conn.cursor()
        self.conn.row_factory = sqlite3.Row
        schema_file = Path(__file__).with_name("schema.sql")
        if schema_file.exists():
            schema = schema_file.read_text(encoding="utf-8")
            self.conn.executescript(schema)

    def query(self, sql, params=()):
        """Read rows. Values always go in params, never into the sql text."""
        return [dict(r) for r in self.conn.execute(sql, params).fetchall()]

    def execute(self, sql, params=()):
        """Write and commit immediately (auto-save, NFR-06)."""
        with self.conn:
            cur = self.conn.execute(sql, params)
            return cur.lastrowid

    # Non-Vague Commands for Database Builder Usage
    def addBook(self, info: tuple) -> bool:
        try:
            self.cursor.execute(
                "INSERT INTO books VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", info
            )
        except Exception:
            return False
        return True

    def pushChanges(self) -> None:
        self.conn.commit

    def save_progress(self, isbn, pages_read, day):
        book_rows = self.query("SELECT pages FROM books WHERE isbn = ?", (isbn,))
        if not book_rows:
            return
        book = book_rows[0]
        pages_read = max(0, min(pages_read, book["pages"]))
        state = ("Finished" if pages_read >= book["pages"]
                 else "InProgress" if pages_read > 0 else "Unread")
        
        # Check current progress to calculate pages added today
        curr_rows = self.query("SELECT pages_read FROM library WHERE isbn = ?", (isbn,))
        prev_pages = curr_rows[0]["pages_read"] if curr_rows else 0
        added = max(0, pages_read - prev_pages)

        with self.conn:
            self.conn.execute(
                """INSERT INTO library (isbn, pages_read, state, started_on)
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT(isbn) DO UPDATE SET
                   pages_read = excluded.pages_read,
                   state = excluded.state,
                   started_on = COALESCE(library.started_on, excluded.started_on),
                   finished_on = CASE WHEN excluded.pages_read >= (SELECT pages FROM books WHERE isbn=?) THEN ? ELSE library.finished_on END
                """,
                (isbn, pages_read, state, day, isbn, day)
            )
            if added > 0:
                self.conn.execute(
                    """INSERT INTO reading_log (day, pages) VALUES (?, ?)
                       ON CONFLICT(day) DO UPDATE SET pages = pages + ?
                    """,
                    (day, added, added)
                )

    @classmethod
    def reset_for_tests(cls):
        """Lets unit tests inject an in-memory database (risk RSK-05)."""
        if cls._instance is not None:
            cls._instance.conn.close()
        cls._instance = None
