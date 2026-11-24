"""nlp_chatbot.py: find matching books with SQLite full-text search, then let Groq
write the recommendation in natural language (FR-24, FR-27 to FR-29).

Flow for one question (coordinated by UserHandler, the Facade):
  1. BookSearchIndex.search()      -> ids of the best matching books (fast, even on 2 GB)
  2. UserHandler builds a prompt   -> question + matches + the reader's library
  3. BookNLPChatbot.generate_reply -> Groq writes a conversational answer
"""
import os
import re
import random
import sqlite3
import threading
from pathlib import Path

try:                                   # optional: tests and CI run without these installed
    import groq
except ImportError:
    groq = None
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent / ".env")   # works from any launch folder
except ImportError:
    pass

# openai/gpt-oss-20b is a reasoning model: its hidden thinking counts against the token
# limit, so it needs a generous budget and a low reasoning effort to leave room for the answer.
MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
MAX_TOKENS = 1500

SYSTEM_PROMPT = """You are a friendly, witty AI Book Assistant inside a reading-tracker app. You love books.

How to answer:
- Write like a warm librarian: 1 to 3 short, natural paragraphs. Plain text only: no markdown, no asterisks, no bullet lists, no headings.
- You may use one kaomoji now and then, such as (◕‿◕), (＾▽＾) or (っ˘ω˘ς). Do not overdo it.
- When the reader wants recommendations, pick the 2 or 3 best books from "Catalog matches" and say in a sentence or two why each one fits their mood, theme or request. Write each title exactly as it appears there.
- Recommend ONLY books listed under "Catalog matches". Never invent titles, authors or plot details; use only the descriptions provided.
- If none of the matches really fit, say so honestly and invite the reader to describe what they want in a different way.
- Questions about the reader's own reading (what they finished, ratings, goals) are answered from "Reader's library". Do not recommend books unless they ask for suggestions.
- Keep the whole answer under 180 words."""

# Words that carry no search value in a request like "recommend me a cozy book about dragons"
STOPWORDS = set("""
a about after again all also an and any are as at be been being but by can could did do does
for from get give good great had has have her him his how i if in into is it its just like
looking me more most my need new no not of off on one only or other our out over own really
should some something somebody someone such than that the their them then there these they
this those to too up us very want was we were what when where which while who why will with
would you your book books novel novels story stories read reading reader recommend recommendation
recommendations suggest suggestion suggestions please tell show find next pick surprise mood
feel feeling anything best
""".split())


class ChatUnavailable(Exception):
    """The AI service could not answer. The message is safe to show to the reader."""


def keywords(text: str, limit: int = 8) -> list:
    seen, out = set(), []
    for word in re.findall(r"[a-z0-9]+", (text or "").lower()):
        if len(word) >= 3 and word not in STOPWORDS and word not in seen:
            seen.add(word)
            out.append(word)
    return out[:limit]


class BookSearchIndex:
    """Full-text index (SQLite FTS5) over title, author and description.

    Built once, in a background thread, into search_index.db next to books.db, so the
    2 GB books.db itself is never modified. Delete search_index.db to rebuild it
    (for example after rebuilding books.db).
    """

    # Skip books with no real description or a poor rating: they make weak recommendations,
    # and leaving them out keeps the index small and the first build fast.
    SOURCE_FILTER = "avgRating >= 3.5 AND length(descr) > 40"

    def __init__(self, books_db_path):
        self.books_db = Path(str(books_db_path)).resolve()
        self.index_path = self.books_db.with_name("search_index.db")
        self.status = "missing"            # missing | building | ready | failed
        self._conn = None
        self._max_id = 1
        self._lock = threading.Lock()

    def start(self):
        """Open the index if it exists, otherwise build it in the background."""
        if not self.books_db.is_file():    # e.g. the in-memory test database
            return
        if self._open():
            return
        self.status = "building"
        threading.Thread(target=self._build, daemon=True).start()

    def _open(self):
        if not self.index_path.is_file():
            return False
        try:
            conn = sqlite3.connect(f"{self.index_path.as_uri()}?mode=ro", uri=True,
                                   check_same_thread=False)
            max_id = conn.execute("SELECT max(rowid) FROM fts").fetchone()[0]
        except sqlite3.Error:
            return False
        self._conn, self._max_id = conn, max_id or 1
        self.status = "ready"
        return True

    def _build(self):
        tmp = self.index_path.with_suffix(".building")
        try:
            print("[search] Building the book search index (first run only, a few minutes)...")
            tmp.unlink(missing_ok=True)
            conn = sqlite3.connect(tmp.as_uri(), uri=True)
            conn.execute("PRAGMA journal_mode = OFF")
            conn.execute("PRAGMA synchronous = OFF")
            conn.execute("ATTACH DATABASE ? AS src", (f"{self.books_db.as_uri()}?mode=ro",))
            conn.execute("CREATE VIRTUAL TABLE fts USING fts5("
                         "title, author, descr, content='', tokenize='porter unicode61')")
            conn.execute("INSERT INTO fts(rowid, title, author, descr) "
                         "SELECT id, title, author, descr FROM src.books "
                         f"WHERE {self.SOURCE_FILTER}")
            conn.commit()
            conn.close()
            os.replace(tmp, self.index_path)
            self._open()
            print("[search] Search index ready.")
        except Exception as exc:
            self.status = "failed"
            print(f"[search] Could not build the search index: {exc}")
            tmp.unlink(missing_ok=True)

    def search(self, text: str, limit: int = 6) -> list:
        """Best matching book ids for a natural-language request (best first)."""
        if self.status != "ready":
            return []
        terms = keywords(text)
        with self._lock:
            if not terms:
                # Nothing specific asked ("surprise me"): offer a few random indexed books
                start = random.randint(1, self._max_id)
                rows = self._conn.execute(
                    "SELECT rowid FROM fts WHERE rowid >= ? ORDER BY rowid LIMIT ?",
                    (start, limit)).fetchall()
            else:
                query = " OR ".join(f'"{t}"' for t in terms)
                rows = self._conn.execute(
                    "SELECT rowid FROM fts WHERE fts MATCH ? "
                    "ORDER BY bm25(fts, 6.0, 3.0, 1.0) LIMIT ?", (query, limit)).fetchall()
        return [int(r[0]) for r in rows]


class BookNLPChatbot:
    def __init__(self, db_path):
        self.index = BookSearchIndex(db_path)
        self.index.start()
        api_key = os.getenv("GROQ_API_KEY")
        self.client = (groq.Groq(api_key=api_key, timeout=25.0, max_retries=1)
                       if groq and api_key else None)

    def retrieve_book_ids(self, query: str, top_n: int = 5, exclude=()) -> list:
        ids = [i for i in self.index.search(query, top_n + len(exclude) + 2) if i not in exclude]
        return ids[:top_n]

    def generate_reply(self, prompt: str) -> str:
        """Ask Groq to answer the prompt. Raises ChatUnavailable with a readable reason."""
        if not groq:
            raise ChatUnavailable("The AI package is not installed. Run: python -m pip install groq python-dotenv")
        if not self.client:
            raise ChatUnavailable("The AI key is missing. Add GROQ_API_KEY to backend/.env and restart the server.")
        try:
            completion = self.client.chat.completions.create(
                model=MODEL,
                messages=[{"role": "system", "content": SYSTEM_PROMPT},
                          {"role": "user", "content": prompt}],
                temperature=0.6,
                max_completion_tokens=MAX_TOKENS,
                extra_body={"reasoning_effort": "low"},
            )
        except groq.AuthenticationError:
            raise ChatUnavailable("Groq rejected the API key. Check GROQ_API_KEY in backend/.env.")
        except groq.RateLimitError:
            raise ChatUnavailable("The AI service is rate limited right now. Try again in a minute.")
        except groq.APIConnectionError:
            raise ChatUnavailable("I couldn't reach the AI service. Check the internet connection.")
        except groq.APIStatusError as exc:
            print(f"[chat] Groq error {exc.status_code}: {exc}")
            raise ChatUnavailable(f"The AI service returned an error ({exc.status_code}). "
                                  f"Check that the model '{MODEL}' is still available on Groq.")

        text = (completion.choices[0].message.content or "").strip()
        if not text:
            raise ChatUnavailable("The AI service returned an empty answer. Please try again.")
        return text
