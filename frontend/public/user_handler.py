"""user_handler.py: Structural pattern, Facade (Design Pattern 2).

The UI only ever talks to UserHandler (FR-30). It validates input, then
coordinates the database, NLP and recommendation subsystems.
"""
import json
import re
from datetime import date, datetime

from database_manager import DatabaseManager
from recommendation_engine import (RecommendationEngine, SearchBasedStrategy,
                                   DashboardStrategy, ChatBasedStrategy)

MAX_CHARS = 3000                       # Boundary 5, NFR-07


class InputTooLong(ValueError):
    pass


def clean(text):
    """Reject over-long text and strip control characters (NFR-07, NFR-14)."""
    if not text:
        return ""
    if len(text) > MAX_CHARS:
        raise InputTooLong(f"Input is limited to {MAX_CHARS} characters")
    return re.sub(r"[\x00-\x08\x0b-\x1f]", "", str(text)).strip()


class UserHandler:
    def __init__(self, db_path="books.db", llm=None):
        self.db = DatabaseManager.get_instance(db_path)
        self.engine = RecommendationEngine(DashboardStrategy(self.db))
        self.llm = llm or (lambda prompt: "Local model not running.")
        self.seed_data_if_empty()

    # ---- search (FR-01, FR-02, FR-04, FR-05) --------------------------------
    def execute_search(self, query="", genre=""):
        cleaned_query = clean(query)[:200]
        self.engine.set_strategy(SearchBasedStrategy(self.db))
        hits = self.engine.get_recommendations({"query": cleaned_query, "genre": genre})
        
        # Attach library status and rating to hits
        enriched_hits = []
        for h in hits:
            lib = self.db.query("SELECT state, pages_read, rating FROM library WHERE isbn = ?", (h["isbn"],))
            h_copy = dict(h)
            h_copy["genres"] = [g.strip() for g in h["genres"].split(",") if g.strip()]
            h_copy["themes"] = [t.strip() for t in h["themes"].split(",") if t.strip()]
            h_copy["desc"] = h["summary"]
            h_copy["avg"] = h["avg_rating"]
            if lib:
                st = lib[0]["state"]
                h_copy["status"] = "progress" if st == "InProgress" else "finished" if st in ("Finished", "Rated") else "unread"
                h_copy["progress"] = lib[0]["pages_read"]
                h_copy["rating"] = lib[0]["rating"] or 0
            else:
                h_copy["status"] = "none"
                h_copy["progress"] = 0
                h_copy["rating"] = 0
            enriched_hits.append(h_copy)

        authors = {h["author"] for h in hits}
        more = []
        for a in authors:
            rows = self.db.query("SELECT isbn, title, author, themes, genres FROM books WHERE author = ? LIMIT 5", (a,))
            for r in rows:
                r_dict = dict(r)
                r_dict["themes"] = [t.strip() for t in r["themes"].split(",") if t.strip()]
                more.append(r_dict)

        return {"results": enriched_hits, "more_by_author": more}

    # ---- book details (FR-03, FR-04, FR-05) ----------------------------------
    def get_book(self, isbn):
        rows = self.db.query("SELECT * FROM books WHERE isbn = ?", (isbn,))
        if not rows:
            return None
        book = dict(rows[0])
        book["genres"] = [g.strip() for g in book["genres"].split(",") if g.strip()]
        book["themes"] = [t.strip() for t in book["themes"].split(",") if t.strip()]
        book["desc"] = book["summary"]
        book["avg"] = book["avg_rating"]

        lib = self.db.query("SELECT * FROM library WHERE isbn = ?", (isbn,))
        if lib:
            st = lib[0]["state"]
            book["status"] = "progress" if st == "InProgress" else "finished" if st in ("Finished", "Rated") else "unread"
            book["progress"] = lib[0]["pages_read"]
            book["rating"] = lib[0]["rating"] or 0
            book["started"] = lib[0]["started_on"]
            book["finished"] = lib[0]["finished_on"]
        else:
            book["status"] = "none"
            book["progress"] = 0
            book["rating"] = 0
            book["started"] = None
            book["finished"] = None

        # Notes
        notes = self.db.query("SELECT id, kind as type, body as text, created_on as at FROM notes WHERE isbn = ? ORDER BY id ASC", (isbn,))
        book["notes"] = [dict(n) for n in notes]

        # More by author
        more_rows = self.db.query("SELECT isbn, title, author, themes FROM books WHERE author = ? AND isbn != ? LIMIT 6", (book["author"], isbn))
        more = []
        for r in more_rows:
            d = dict(r)
            d["themes"] = [t.strip() for t in d["themes"].split(",") if t.strip()]
            more.append(d)
        book["more_by_author"] = more

        # Similar books (shared themes)
        similar = []
        theme_set = set(book["themes"])
        all_other = self.db.query("SELECT isbn, title, author, themes, genres FROM books WHERE isbn != ? AND author != ?", (isbn, book["author"]))
        for o in all_other:
            oth_themes = set(t.strip() for t in o["themes"].split(",") if t.strip())
            overlap = len(theme_set & oth_themes)
            if overlap > 0:
                d = dict(o)
                d["themes"] = list(oth_themes)
                d["score"] = overlap
                similar.append(d)
        similar.sort(key=lambda x: -x["score"])
        book["similar"] = similar[:6]

        return book

    # ---- progress (FR-06 to FR-10, FR-09) ------------------------------------
    def save_reading_progress(self, isbn, pages, day=None):
        if pages < 0:
            raise ValueError("Pages cannot be negative")
        log_day = day or date.today().isoformat()
        self.db.save_progress(isbn, pages, log_day)

    # ---- ratings (FR-16) -----------------------------------------------------
    def rate_book(self, isbn, rating):
        rating = max(0, min(5, int(rating)))
        existing = self.db.query("SELECT state, pages_read FROM library WHERE isbn = ?", (isbn,))
        if not existing:
            # Auto add to library as Finished if rated from scratch
            b = self.db.query("SELECT pages FROM books WHERE isbn = ?", (isbn,))
            pages = b[0]["pages"] if b else 100
            today_str = date.today().isoformat()
            self.db.execute(
                "INSERT INTO library (isbn, state, pages_read, rating, started_on, finished_on) VALUES (?, 'Finished', ?, ?, ?, ?)",
                (isbn, pages, rating, today_str, today_str)
            )
        else:
            self.db.execute("UPDATE library SET rating = ? WHERE isbn = ?", (rating, isbn))

    # ---- library actions (FR-06, FR-38, FR-39) -------------------------------
    def add_to_library(self, isbn):
        self.db.execute(
            "INSERT INTO library (isbn, state, pages_read, rating) VALUES (?, 'Unread', 0, 0) "
            "ON CONFLICT(isbn) DO UPDATE SET state='Unread', pages_read=0",
            (isbn,)
        )

    def remove_from_library(self, isbn):
        self.db.execute("DELETE FROM library WHERE isbn = ?", (isbn,))

    def reread_book(self, isbn):
        today_str = date.today().isoformat()
        self.db.execute(
            "UPDATE library SET state = 'InProgress', pages_read = 0, started_on = ?, finished_on = NULL WHERE isbn = ?",
            (today_str, isbn)
        )

    # ---- notes (FR-17, FR-31) ------------------------------------------------
    def append_note(self, isbn, body, kind="note"):
        clean_body = clean(body)
        if not clean_body:
            raise ValueError("Note text cannot be empty")
        today_str = date.today().isoformat()
        note_id = self.db.execute(
            "INSERT INTO notes (isbn, kind, body, created_on) VALUES (?, ?, ?, ?)",
            (isbn, kind, clean_body, today_str)
        )
        return {"id": note_id, "isbn": isbn, "kind": kind, "body": clean_body, "created_on": today_str}

    def edit_note(self, note_id, body):
        clean_body = clean(body)
        self.db.execute("UPDATE notes SET body = ? WHERE id = ?", (clean_body, note_id))

    def delete_note(self, note_id):
        self.db.execute("DELETE FROM notes WHERE id = ?", (note_id,))

    # ---- dashboard / recommendations (FR-23, FR-25) --------------------------
    def get_dashboard_data(self, genre="", limit=4):
        self.engine.set_strategy(DashboardStrategy(self.db))
        recs = self.engine.get_recommendations({"limit": limit, "genre": genre})
        for r in recs:
            r["genres"] = [g.strip() for g in r["genres"].split(",") if g.strip()]
            r["themes"] = [t.strip() for t in r["themes"].split(",") if t.strip()]
            r["desc"] = r["summary"]
            r["avg"] = r["avg_rating"]
        return recs

    # ---- my library view (FR-33, FR-34) --------------------------------------
    def get_my_library(self):
        rows = self.db.query(
            "SELECT b.*, l.state, l.pages_read, l.rating, l.started_on, l.finished_on "
            "FROM library l JOIN books b USING(isbn) ORDER BY l.rowid DESC"
        )
        items = []
        for r in rows:
            d = dict(r)
            d["genres"] = [g.strip() for g in d["genres"].split(",") if g.strip()]
            d["themes"] = [t.strip() for t in d["themes"].split(",") if t.strip()]
            d["desc"] = d["summary"]
            d["avg"] = d["avg_rating"]
            st = d["state"]
            d["status"] = "progress" if st == "InProgress" else "finished" if st in ("Finished", "Rated") else "unread"
            d["progress"] = d["pages_read"]
            d["rating"] = d["rating"] or 0
            
            # Notes for this book
            notes = self.db.query("SELECT id, kind as type, body as text, created_on as at FROM notes WHERE isbn = ? ORDER BY id ASC", (d["isbn"],))
            d["notes"] = [dict(n) for n in notes]
            items.append(d)
        return items

    # ---- settings & reading log (FR-12, FR-13, FR-37) ------------------------
    def get_settings(self):
        rows = self.db.query("SELECT key, value FROM settings")
        s = {r["key"]: r["value"] for r in rows}
        fav_genres = [g.strip() for g in s.get("fav_genres", "Fantasy,Science fiction").split(",") if g.strip()]
        return {
            "name": s.get("display_name", "Reader"),
            "goal": int(s.get("daily_goal", 40)),
            "yearGoal": int(s.get("yearly_goal", 12)),
            "favGenres": fav_genres
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
    def submit_chat_query(self, query, isbn=None):
        query = clean(query)
        # Assistant has strictly READ-ONLY database access (FR-40, NFR-13)
        context = []
        if isbn:
            context = self.db.query("SELECT title, author, themes, summary FROM books WHERE isbn = ?", (isbn,))
        
        # Read-only recommendation lookup if requested
        picks = []
        if re.search(r"recommend|suggest|what should i read|books like|similar", query, re.I):
            self.engine.set_strategy(DashboardStrategy(self.db))
            picks = self.engine.get_recommendations({"limit": 3})

        prompt = f"You are a friendly, witty AI Book Assistant who loves books and occasionally uses kaomoji like (◕‿◕), (＾▽＾), (っ˘ω˘ς), (ง •̀_•́)ง.\nBook context: {context}\nQuestion: {query}"
        raw_llm = self.llm(prompt)
        
        if raw_llm and raw_llm != "Local model not running.":
            answer = clean(raw_llm)
        else:
            # Charming local fallback with kaomoji
            if picks:
                answer = f"Here are {len(picks)} great recommendations based on your favorite shelves (＾▽＾):"
            elif context:
                b = context[0]
                answer = f"{b['title']} by {b['author']} is built around {b['themes']} (っ˘ω˘ς). Ask me about its plot or say 'suggest something similar' (◕‿◕)!"
            elif re.search(r"hello|hi|hey", query, re.I):
                answer = "Hello there! (◕‿◕) Ready to find your next great read or chat about your notes? (ง •̀_•́)ง"
            else:
                answer = "I can answer questions about your books, notes, and reading habits, and suggest new books whenever you ask (◕‿◕)b. Try 'suggest a short mystery' or 'what have I finished?' (っ˘ω˘ς)"

        return {
            "text": answer,
            "picks": [{"isbn": p["isbn"], "why": p.get("why", "Recommended based on themes")} for p in picks],
            "used": ["Your reading library", "Your ratings"]
        }

    # ---- seed initial data (Sprint 3 startup) --------------------------------
    def seed_data_if_empty(self):
        count = self.db.query("SELECT count(*) as cnt FROM books")[0]["cnt"]
        if count > 0:
            return

        sample_books = [
            ("9781073915312", "Circe", "Madeline Miller", 400, 2018, "Little, Brown", 4.3, "Fantasy,Mythology", "isolation,identity,mythology", "In the house of Helios, god of the sun, a daughter is born. Banished to a deserted island, she hones her art of witchcraft."),
            ("9781047830623", "Project Hail Mary", "Andy Weir", 476, 2021, "Ballantine", 4.5, "Science fiction", "isolation,friendship,science", "Ryland Grace is the sole survivor on a desperate, last-chance mission to save humanity."),
            ("9781021745934", "The Song of Achilles", "Madeline Miller", 378, 2011, "Ecco", 4.4, "Fantasy,Mythology", "mythology,devotion,loss", "Patroclus forms an unlikely friendship with Achilles that deepens as they grow into young men."),
            ("9781095661245", "The Martian", "Andy Weir", 369, 2014, "Crown", 4.4, "Science fiction", "survival,science,isolation", "Astronaut Mark Watney is stranded alone on Mars after a dust storm."),
            ("9781069576556", "The Night Circus", "Erin Morgenstern", 387, 2011, "Doubleday", 4.0, "Fantasy,Romance", "magic,atmospheric", "A fierce competition between two young magicians within an enchanted circus."),
            ("9781043491867", "Piranesi", "Susanna Clarke", 272, 2020, "Bloomsbury", 4.2, "Fantasy,Mystery", "solitude,mystery,isolation", "Piranesi lives in a labyrinthine house with infinite rooms and oceans trapped inside."),
            ("9781017407178", "Ariadne", "Jennifer Saint", 352, 2021, "Celadon", 4.1, "Fantasy,Mythology", "mythology,betrayal", "Princess of Crete Ariadne must decide how much to sacrifice for love when Theseus arrives."),
            ("9781091322489", "Rendezvous with Rama", "Arthur C. Clarke", 243, 1973, "Gollancz", 4.1, "Science fiction", "exploration,mystery,science", "A team of human explorers investigates an enigmatic cylindrical alien vessel."),
            ("9781065237790", "Gone Girl", "Gillian Flynn", 422, 2012, "Crown", 4.1, "Mystery,Thriller", "betrayal,identity,mystery", "On their fifth wedding anniversary, Amy Dunne disappears and Nick becomes the prime suspect."),
            ("9781039153101", "The Thursday Murder Club", "Richard Osman", 382, 2020, "Viking", 4.1, "Mystery,Cozy", "friendship,mystery", "Four friends in a retirement village meet weekly to investigate unsolved crimes."),
            ("9781013068412", "Dune", "Frank Herbert", 612, 1965, "Chilton", 4.3, "Science fiction", "power,survival,betrayal", "Paul Atreides travels to the dangerous desert planet Arrakis to secure his family's future."),
            ("9781086983723", "Station Eleven", "Emily St. John Mandel", 333, 2014, "Knopf", 4.0, "Science fiction,Literary fiction", "survival,art,identity", "A nomadic theater troupe keeps Shakespeare alive across a devastated post-flu North America."),
            ("9781060899034", "Artemis", "Andy Weir", 305, 2017, "Crown", 3.7, "Science fiction,Thriller", "survival,science,betrayal", "Jazz Bashara is a smuggler living in the first and only city on the moon."),
            ("9781034814345", "The Hobbit", "J.R.R. Tolkien", 310, 1937, "Allen & Unwin", 4.3, "Fantasy,Adventure", "friendship,exploration,magic", "Bilbo Baggins embarks on a grand quest to reclaim the Lonely Mountain from Smaug."),
            ("9781008729656", "Murder on the Orient Express", "Agatha Christie", 256, 1934, "Collins Crime Club", 4.2, "Mystery,Classic", "mystery,betrayal", "Detective Hercule Poirot must find the murderer trapped on a snowbound luxury train."),
            ("9781082644967", "And Then There Were None", "Agatha Christie", 272, 1939, "Collins Crime Club", 4.3, "Mystery,Classic", "mystery,isolation,betrayal", "Ten strangers with dark secrets are lured to an isolated island off the Devon coast.")
        ]
        with self.db.conn:
            self.db.conn.executemany(
                "INSERT OR IGNORE INTO books (isbn, title, author, pages, year, publisher, avg_rating, genres, themes, summary) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                sample_books
            )
            # Sample library
            self.db.conn.execute("INSERT OR IGNORE INTO library (isbn, state, pages_read, rating, started_on) VALUES ('9781073915312', 'InProgress', 210, 0, '2026-08-28')")
            self.db.conn.execute("INSERT OR IGNORE INTO library (isbn, state, pages_read, rating, started_on) VALUES ('9781047830623', 'InProgress', 64, 0, '2026-09-12')")
            self.db.conn.execute("INSERT OR IGNORE INTO library (isbn, state, pages_read, rating, started_on, finished_on) VALUES ('9781021745934', 'Finished', 378, 5, '2026-07-05', '2026-07-27')")
            self.db.conn.execute("INSERT OR IGNORE INTO library (isbn, state, pages_read, rating, started_on, finished_on) VALUES ('9781095661245', 'Finished', 369, 4, '2026-08-04', '2026-08-14')")
            self.db.conn.execute("INSERT OR IGNORE INTO library (isbn, state, pages_read, rating) VALUES ('9781069576556', 'Unread', 0, 0)")
            self.db.conn.execute("INSERT OR IGNORE INTO library (isbn, state, pages_read, rating) VALUES ('9781043491867', 'Unread', 0, 0)")

            # Sample notes
            self.db.conn.execute("INSERT OR IGNORE INTO notes (isbn, kind, body, created_on) VALUES ('9781073915312', 'note', 'Circe loneliness on Aiaia feels like the heart of the book.', '2026-09-16')")
            self.db.conn.execute("INSERT OR IGNORE INTO notes (isbn, kind, body, created_on) VALUES ('9781073915312', 'highlight', 'I decided that I would be the kind of witch who keeps her door open.', '2026-10-04')")
            self.db.conn.execute("INSERT OR IGNORE INTO notes (isbn, kind, body, created_on) VALUES ('9781047830623', 'note', 'Rocky is already my favorite character. The friendship feels earned and the science is a joy.', '2026-10-14')")
            self.db.conn.execute("INSERT OR IGNORE INTO notes (isbn, kind, body, created_on) VALUES ('9781021745934', 'note', 'The last chapters are devastating. Rereading the opening after finishing changes everything.', '2026-07-27')")

            # Sample reading log (last 12 days)
            logs = [(0, 32), (1, 41), (2, 28), (3, 40), (4, 36), (5, 30), (6, 45), (7, 22), (8, 38), (9, 34), (10, 40), (11, 29)]
            for days_ago, pages in logs:
                d = (date.today().fromordinal(date.today().toordinal() - days_ago)).isoformat()
                self.db.conn.execute("INSERT OR IGNORE INTO reading_log (day, pages) VALUES (?, ?)", (d, pages))

            # Settings
            self.db.conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('display_name', 'Reader')")
            self.db.conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('daily_goal', '40')")
            self.db.conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('yearly_goal', '12')")
            self.db.conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('fav_genres', 'Fantasy,Science fiction')")
