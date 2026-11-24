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
from nlp_chatbot import BookNLPChatbot, ChatUnavailable, keywords

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
    def __init__(self, db_path=None, llm=None):
        self.db = DatabaseManager.get_instance(db_path)
        self.engine = RecommendationEngine(DashboardStrategy(self.db))
        self.nlp_bot = BookNLPChatbot(self.db.db_path)
        # llm(prompt) -> text. Tests pass a stub; otherwise Groq answers.
        self.llm = llm or self.nlp_bot.generate_reply

    # ---- books list & search (FR-01, FR-02, FR-04, FR-05) --------------------
    def list_books(self, limit=200, offset=0):
        rows = self.db.query(BOOK_COLUMNS + "ORDER BY b.id LIMIT ? OFFSET ?", (limit, offset))
        return [to_book(r) for r in rows]

    def execute_search(self, query="", genre=""):
        q = clean(query)[:200]
        rows = []

        if q:
            ids = self.nlp_bot.retrieve_book_ids(q, top_n=50)
            if ids:
                marks = ",".join("?" * len(ids))
                matches = self.db.query(
                    BOOK_COLUMNS + f"WHERE b.id IN ({marks}) LIMIT 50",
                    tuple(ids),
                )
                by_id = {row["id"]: row for row in matches}
                rows = [by_id[id_] for id_ in ids if id_ in by_id]
                if genre:
                    genre_marker = genre.lower()
                    rows = [
                        row for row in rows
                        if genre_marker in str(row.get("tags") or "").lower()
                    ]

        if not rows:
            prefix = f"{q}%"
            if genre:
                rows = self.db.query(
                    BOOK_COLUMNS
                    + "WHERE (b.title LIKE ? OR b.author LIKE ?) "
                    "AND b.tags LIKE ? LIMIT 50",
                    (prefix, prefix, f"%{genre}%"),
                )
            else:
                rows = self.db.query(
                    BOOK_COLUMNS
                    + "WHERE b.title LIKE ? OR b.author LIKE ? LIMIT 50",
                    (prefix, prefix),
                )

        if not rows and q:
            like = f"%{q}%"
            if genre:
                rows = self.db.query(
                    BOOK_COLUMNS
                    + "WHERE (b.title LIKE ? OR b.author LIKE ?) "
                    "AND b.tags LIKE ? LIMIT 50",
                    (like, like, f"%{genre}%"),
                )
            else:
                rows = self.db.query(
                    BOOK_COLUMNS
                    + "WHERE b.title LIKE ? OR b.author LIKE ? LIMIT 50",
                    (like, like),
                )
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
        # Check the book first so a bad id gives a readable 400, not a raw IntegrityError (500)
        if not self.db.query("SELECT id FROM books WHERE id = ?", (book_id,)):
            raise ValueError("Book not found")
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
    def submit_chat_query(self, query, book_id=None, history=None):
        """Answer a chat message in natural language. Never writes to the database."""
        query = clean(query)
        if not query:
            return {"text": "Ask me for a book recommendation, or about a book (◕‿◕)!",
                    "picks": [], "used": []}

        history = self._clean_history(history)
        selected = self._selected_book(book_id)

        # What to search for: the question, plus the open book (for "something similar"),
        # plus the previous question when this one is a short follow-up ("something shorter").
        search_text = query
        if selected:
            search_text = f"{selected['title']} {_plain(selected['descr'])[:200]} {query}"
        elif history and len(keywords(query)) < 3:
            earlier = [m["text"] for m in history if m["role"] == "Reader"]
            if earlier:
                search_text = f"{earlier[-1]} {query}"

        ids = self.nlp_bot.retrieve_book_ids(search_text, top_n=5,
                                             exclude=(selected["id"],) if selected else ())
        matches = self._books_in_order(ids)
        library = self._library_summary()

        used = (["Book you're viewing"] if selected else []) + (["Your library"] if library else []) \
            + (["Book catalog search"] if matches else [])
        prompt = self._build_prompt(query, selected, matches, library, history)

        try:
            reply = clean(self.llm(prompt)[:MAX_CHARS])
            # Only show cards for the books the assistant actually talked about
            shown = [b for b in matches if _mentioned(reply, b["title"])]
        except ChatUnavailable as exc:
            shown = matches[:3]
            reply = f"{exc} Here are the closest matches I found." if shown else str(exc)

        picks = []
        for row in shown[:3]:
            book = to_book(row)
            why = f"Rated {book['avg']:.1f} by readers" if book["avg"] else ""
            picks.append({"isbn": book["isbn"], "why": why, "book": book})
        return {"text": reply, "picks": picks, "used": used}

    # ---- assistant helpers -----------------------------------------------------
    @staticmethod
    def _clean_history(history):
        """Last few chat turns as [{"role": "Reader"|"Assistant", "text": ...}]."""
        if not isinstance(history, list):
            return []
        out = []
        for m in history[-6:]:
            if isinstance(m, dict):
                text = clean(str(m.get("text") or "")[:800])
                if text:
                    out.append({"role": "Reader" if m.get("role") == "user" else "Assistant",
                                "text": text})
        return out

    def _selected_book(self, book_id):
        try:
            rows = self.db.query(BOOK_COLUMNS + "WHERE b.id = ?", (int(book_id),))
        except (TypeError, ValueError):
            return None
        return rows[0] if rows else None

    def _books_in_order(self, ids):
        if not ids:
            return []
        marks = ",".join("?" * len(ids))
        by_id = {r["id"]: r for r in self.db.query(
            BOOK_COLUMNS + f"WHERE b.id IN ({marks})", tuple(ids))}
        return [by_id[i] for i in ids if i in by_id]

    def _library_summary(self):
        rows = self.db.query(
            "SELECT b.title, l.state, l.rating FROM library l JOIN books b ON b.id = l.id "
            "ORDER BY l.startDate DESC LIMIT 40")
        groups = {"Finished": [], "Reading now": [], "Not started": []}
        for r in rows:
            title = _short_title(r["title"])
            if r["state"] in (STATE_FINISHED, STATE_RATED):
                groups["Finished"].append(f"{title} (rated {int(r['rating'])}/5)" if r["rating"] else title)
            elif r["state"] == STATE_IN_PROGRESS:
                groups["Reading now"].append(title)
            elif r["state"] == STATE_UNSTARTED:
                groups["Not started"].append(title)
        lines = [f"{label}: {', '.join(titles[:8])}" for label, titles in groups.items() if titles]
        fav = self.db.query("SELECT value FROM settings WHERE key = 'fav_genres'")
        if fav and fav[0]["value"]:
            lines.append("Favorite genres: " + fav[0]["value"])
        return "\n".join(lines)

    def _build_prompt(self, query, selected, matches, library, history):
        parts = []
        if selected:
            parts.append("The reader has this book open: " + _describe(selected, 500))
        if library:
            parts.append("Reader's library:\n" + library)
        if matches:
            parts.append("Catalog matches:\n" + "\n".join("- " + _describe(b, 300) for b in matches))
        elif self.nlp_bot.index.status == "building":
            parts.append("Catalog matches: none yet. The catalog search index is being built for the "
                         "first time; if the reader wants recommendations, ask them to try again in a few minutes.")
        else:
            parts.append("Catalog matches: none found for this request.")
        if history:
            parts.append("Conversation so far:\n" + "\n".join(f"{m['role']}: {m['text']}" for m in history))
        parts.append(f"Reader's message: {query}")
        return "\n\n".join(parts)


def _plain(text):
    """Goodreads descriptions contain HTML such as <br />; strip it."""
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", str(text or ""))).strip()


def _short_title(title):
    """'Dune (Dune, #1)' -> 'Dune'."""
    return re.sub(r"\s*\([^)]*\)\s*$", "", title or "").strip() or (title or "")


def _describe(row, max_chars):
    r = dict(row)
    rating = f"rating {r['avgRating']:.1f}, " if r.get("avgRating") else ""
    return (f"{_short_title(r['title'])} by {r['author']} ({rating}{r.get('pages') or '?'} pages): "
            f"{_plain(r.get('descr'))[:max_chars]}")


def _mentioned(reply, title):
    norm = lambda t: t.lower().replace("\u2019", "'")
    short = norm(_short_title(title))
    return len(short) >= 3 and short in norm(reply)
