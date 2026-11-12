"""user_handler.py: Structural pattern, Facade (Design Pattern 2).

The UI only ever talks to UserHandler (FR-30). It validates input, then
coordinates the database, NLP and recommendation subsystems.

Books are keyed by the integer books.id from schema.sql. The front end still
reads that key from a field called "isbn", so every book sent to the UI carries
isbn = str(id) as well as id.
"""
import re
from datetime import date

from database_manager import DatabaseManager
from recommendation_engine import (RecommendationEngine, SearchBasedStrategy,
                                   DashboardStrategy)

MAX_CHARS = 3000                       # Boundary 5, NFR-07

# library.state codes (see schema.sql)
STATE_UNSTARTED, STATE_IN_PROGRESS, STATE_FINISHED, STATE_UNFINISHED, STATE_RATED = range(5)

BOOK_COLUMNS = ("SELECT b.*, l.state AS state, l.progress AS progress, "
                "l.rating AS rating, l.startDate AS startDate "
                "FROM books b LEFT JOIN library l ON l.id = b.id ")


class InputTooLong(ValueError):
    pass


def clean(text):
    if not text:
        return ""
    if len(text) > MAX_CHARS:
        raise InputTooLong(f"Input is limited to {MAX_CHARS} characters")
    return re.sub(r"[\x00-\x08\x0b-\x1f]", "", str(text)).strip()


def _split(text):
    return [t.strip() for t in (text or "").split(",") if t.strip()]


def _status(state):
    if state is None:
        return "none"
    if state == STATE_IN_PROGRESS:
        return "progress"
    if state in (STATE_FINISHED, STATE_RATED):
        return "finished"
    return "unread"


def to_book(row):
    """Convert a books row (optionally joined with library) into the UI's shape."""
    d = dict(row)
    year = (d.get("publDate") or "")[:4]
    tags = _split(d.get("tags"))
    out = {
        "id": d["id"],
        "isbn": str(d["id"]),                 # UI routing key, same value as id
        "title": d["title"],
        "author": d["author"],
        "publisher": d.get("publisher") or "",
        "year": int(year) if year.isdigit() else None,
        "pages": d.get("pages"),
        "avg": d.get("avgRating") or 0,
        "genres": tags,
        "themes": tags,
        "desc": d.get("descr") or "",
        "cover": d.get("cover") or "",
        "series": _split(d.get("series")),
        "language": d.get("language") or "",
        "isEBook": bool(d.get("isEBook")),
        "status": _status(d.get("state")),
        "progress": d.get("progress") or 0,
        "rating": d.get("rating") or 0,
        "started": d.get("startDate") if d.get("state") is not None else None,
        "finished": None,                     # schema has no finish date
    }
    return out


class UserHandler:
    def __init__(self, db_path="books.db", llm=None):
        self.db = DatabaseManager.get_instance(db_path)
        self.engine = RecommendationEngine(DashboardStrategy(self.db))
        self.llm = llm or (lambda prompt: "Local model not running.")

    # ---- books list & search (FR-01, FR-02, FR-04, FR-05) --------------------
    def list_books(self, limit=200, offset=0):
        rows = self.db.query(BOOK_COLUMNS + "ORDER BY b.id LIMIT ? OFFSET ?", (limit, offset))
        return [to_book(r) for r in rows]

    def execute_search(self, query="", genre=""):
        q = clean(query)[:200]
        like = f"%{q}%"
        if genre:
            rows = self.db.query(BOOK_COLUMNS + "WHERE (b.title LIKE ? OR b.author LIKE ?) AND b.tags LIKE ? LIMIT 50",
                                 (like, like, f"%{genre}%"))
        else:
            rows = self.db.query(BOOK_COLUMNS + "WHERE b.title LIKE ? OR b.author LIKE ? LIMIT 50", (like, like))
        results = [to_book(r) for r in rows]

        more = []
        if results:
            top_author = results[0]["author"]
            more = [to_book(r) for r in self.db.query(
                BOOK_COLUMNS + "WHERE b.author = ? LIMIT 5", (top_author,))]
        return {"results": results, "more_by_author": more}

    # ---- book details (FR-03, FR-04, FR-05) ----------------------------------
    def get_book(self, book_id):
        rows = self.db.query(BOOK_COLUMNS + "WHERE b.id = ?", (book_id,))
        if not rows:
            return None
        book = to_book(rows[0])

        book["notes"] = self._notes(book_id)

        book["more_by_author"] = [to_book(r) for r in self.db.query(
            BOOK_COLUMNS + "WHERE b.author = ? AND b.id != ? LIMIT 6", (book["author"], book_id))]

        # "similar" column holds comma-separated ids from the builder
        similar_ids = [int(x) for x in _split(rows[0]["similar"]) if x.isdigit()][:6]
        book["similar"] = []
        if similar_ids:
            marks = ",".join("?" * len(similar_ids))
            book["similar"] = [to_book(r) for r in self.db.query(
                BOOK_COLUMNS + f"WHERE b.id IN ({marks})", tuple(similar_ids))]
        return book

    def _notes(self, book_id):
        rows = self.db.query(
            "SELECT id, kind AS type, body AS text, created_on AS at "
            "FROM notes WHERE book_id = ? ORDER BY id ASC", (book_id,))
        return [dict(r) for r in rows]

    # ---- progress (FR-06 to FR-10) -------------------------------------------
    def save_reading_progress(self, book_id, pages, day=None):
        if pages < 0:
            raise ValueError("Pages cannot be negative")
        log_day = day or date.today().isoformat()
        self.db.save_progress(book_id, pages, log_day)

    # ---- ratings (FR-16) -----------------------------------------------------
    def rate_book(self, book_id, rating):
        rating = max(0, min(5, int(rating)))
        existing = self.db.query("SELECT id FROM library WHERE id = ?", (book_id,))
        if not existing:
            # Rating an unshelved book adds it to the library as Rated
            total = self.db.query("SELECT pages FROM books WHERE id = ?", (book_id,))
            pages = total[0]["pages"] if total else 0
            self.db.execute(
                "INSERT INTO library (id, state, rating, progress, startDate) VALUES (?, ?, ?, ?, ?)",
                (book_id, STATE_RATED, rating, pages, date.today().isoformat())
            )
        else:
            self.db.execute("UPDATE library SET rating = ? WHERE id = ?", (rating, book_id))

    # ---- library actions (FR-06, FR-38, FR-39) -------------------------------
    def add_to_library(self, book_id):
        self.db.execute(
            "INSERT INTO library (id, state, rating, progress, startDate) VALUES (?, ?, 0, 0, ?) "
            "ON CONFLICT(id) DO UPDATE SET state = excluded.state, progress = 0",
            (book_id, STATE_UNSTARTED, date.today().isoformat())
        )

    def remove_from_library(self, book_id):
        self.db.execute("DELETE FROM library WHERE id = ?", (book_id,))

    def reread_book(self, book_id):
        self.db.execute(
            "UPDATE library SET state = ?, progress = 0, startDate = ? WHERE id = ?",
            (STATE_IN_PROGRESS, date.today().isoformat(), book_id)
        )

    # ---- notes (FR-17, FR-31) ------------------------------------------------
    def append_note(self, book_id, body, kind="note"):
        clean_body = clean(body)
        if not clean_body:
            raise ValueError("Note text cannot be empty")
        today_str = date.today().isoformat()
        note_id = self.db.execute(
            "INSERT INTO notes (book_id, kind, body, created_on) VALUES (?, ?, ?, ?)",
            (book_id, kind, clean_body, today_str)
        )
        return {"id": note_id, "isbn": str(book_id), "kind": kind, "body": clean_body, "created_on": today_str}

    def edit_note(self, note_id, body):
        clean_body = clean(body)
        self.db.execute("UPDATE notes SET body = ? WHERE id = ?", (clean_body, note_id))

    def delete_note(self, note_id):
        self.db.execute("DELETE FROM notes WHERE id = ?", (note_id,))

    # ---- dashboard / recommendations (FR-23, FR-25) --------------------------
    def get_dashboard_data(self, genre="", limit=4):
        self.engine.set_strategy(DashboardStrategy(self.db))
        recs = self.engine.get_recommendations({"limit": limit, "genre": genre})
        return [dict(to_book(r), match=r["match"], why=r["why"]) for r in recs]

    # ---- my library view (FR-33, FR-34) --------------------------------------
    def get_my_library(self):
        rows = self.db.query(BOOK_COLUMNS + "WHERE l.id IS NOT NULL ORDER BY l.rowid DESC")
        items = []
        for r in rows:
            d = to_book(r)
            d["notes"] = self._notes(d["id"])
            items.append(d)
        return items

    # ---- settings & reading log (FR-12, FR-13, FR-37) ------------------------
    def get_settings(self):
        rows = self.db.query("SELECT key, value FROM settings")
        s = {r["key"]: r["value"] for r in rows}
        return {
            "name": s.get("display_name", "Reader"),
            "goal": int(s.get("daily_goal", 40)),
            "yearGoal": int(s.get("yearly_goal", 12)),
            "favGenres": _split(s.get("fav_genres", "Fantasy,Science fiction"))
        }

    def save_settings(self, data):
        if "name" in data:
            self.db.execute("INSERT INTO settings (key, value) VALUES ('display_name', ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (clean(data["name"]),))
        if "goal" in data:
            self.db.execute("INSERT INTO settings (key, value) VALUES ('daily_goal', ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (str(int(data["goal"])),))
        if "yearGoal" in data:
            self.db.execute("INSERT INTO settings (key, value) VALUES ('yearly_goal', ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (str(int(data["yearGoal"])),))
        if "favGenres" in data:
            val = ",".join(data["favGenres"])
            self.db.execute("INSERT INTO settings (key, value) VALUES ('fav_genres', ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (val,))

    def get_reading_log(self):
        rows = self.db.query("SELECT day, pages FROM reading_log")
        return {r["day"]: r["pages"] for r in rows}

    def log_pages_for_day(self, day, pages):
        self.db.execute(
            "INSERT INTO reading_log (day, pages) VALUES (?, ?) ON CONFLICT(day) DO UPDATE SET pages = excluded.pages",
            (day, int(pages))
        )

    # ---- assistant: READ ONLY (FR-27, FR-28, FR-29, NFR-13, FR-40) -----------
    def submit_chat_query(self, query, book_id=None):
        query = clean(query)
        # Assistant has strictly READ-ONLY database access (FR-40, NFR-13)
        context = []
        if book_id is not None:
            context = self.db.query("SELECT title, author, tags, descr FROM books WHERE id = ?", (book_id,))

        picks = []
        if re.search(r"recommend|suggest|what should i read|books like|similar", query, re.I):
            self.engine.set_strategy(DashboardStrategy(self.db))
            picks = self.engine.get_recommendations({"limit": 3})

        prompt = f"You are a friendly, witty AI Book Assistant who loves books and occasionally uses kaomoji like (◕‿◕), (＾▽＾), (っ˘ω˘ς), (ง •̀_•́)ง.\nBook context: {context}\nQuestion: {query}"
        raw_llm = self.llm(prompt)

        if raw_llm and raw_llm != "Local model not running.":
            answer = clean(raw_llm)
        else:
            if picks:
                answer = f"Here are {len(picks)} great recommendations based on your favorite shelves (＾▽＾):"
            elif context:
                b = context[0]
                answer = f"{b['title']} by {b['author']} (っ˘ω˘ς). Ask me about its plot or say 'suggest something similar' (◕‿◕)!"
            elif re.search(r"hello|hi|hey", query, re.I):
                answer = "Hello there! (◕‿◕) Ready to find your next great read or chat about your notes? (ง •̀_•́)ง"
            else:
                answer = "I can answer questions about your books, notes, and reading habits, and suggest new books whenever you ask (◕‿◕)b. Try 'suggest a short mystery' or 'what have I finished?' (っ˘ω˘ς)"

        return {
            "text": answer,
            "picks": [{"isbn": str(p["id"]), "why": p.get("why", "Recommended based on themes")} for p in picks],
            "used": ["Your reading library", "Your ratings"]
        }
