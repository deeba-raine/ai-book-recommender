"""Integration tests: UserHandler (Facade) <-> DatabaseManager (Singleton) <-> SQLite.

Bottom-Up strategy from the CS 360 Week 12_2 Test Plan:
- DatabaseManager is real (in-memory SQLite loaded from backend/schema.sql).
- The LLM is a stub (fixed reply) because the local model is not running.
- This file is the driver: it calls UserHandler directly and also posts through
  the FastAPI app with TestClient.
"""
import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND))

from database_manager import DatabaseManager  # noqa: E402

# Build the shared in-memory database BEFORE importing app.py, because app.py
# creates its UserHandler at import time and the Singleton then reuses this DB.
DatabaseManager.reset_for_tests()
DB = DatabaseManager.get_instance(":memory:")
DB.execute(
    "INSERT INTO books (id, title, author, publisher, publDate, series, tags, pages) "
    "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
    (1, "Dune", "Frank Herbert", "Chilton", "1965-08-01", "", "Science fiction,Fantasy", 412),
)
DB.execute(
    "INSERT INTO books (id, title, author, publisher, publDate, series, tags, pages) "
    "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
    (2, "Emma", "Jane Austen", "John Murray", "1815-12-23", "", "Classic,Romance", 474),
)

from fastapi.testclient import TestClient  # noqa: E402
from user_handler import UserHandler, InputTooLong, MAX_CHARS  # noqa: E402
import app as app_module  # noqa: E402

LLM_STUB = lambda prompt: "stubbed reply"  # noqa: E731
HANDLER = UserHandler(llm=LLM_STUB)
HANDLER.db = DB  # same singleton, pinned explicitly for clarity
client = TestClient(app_module.app)


@pytest.fixture(autouse=True)
def clean_notes():
    DB.execute("DELETE FROM notes")
    DB.execute("DELETE FROM library")
    DB.execute("DELETE FROM reading_log")
    DB.execute("DELETE FROM settings")
    yield
    DB.execute("DELETE FROM notes")
    DB.execute("DELETE FROM library")
    DB.execute("DELETE FROM reading_log")
    DB.execute("DELETE FROM settings")


def note_rows():
    return DB.query("SELECT * FROM notes")


# ---- Driver 1: direct Facade calls -----------------------------------------
def test_append_note_saves_trimmed_body_and_returns_note():
    note = HANDLER.append_note(1, "  Loved the ending.  ")
    assert note["body"] == "Loved the ending."
    assert note["kind"] == "note"
    assert note["isbn"] == "1"
    rows = note_rows()
    assert len(rows) == 1
    assert rows[0]["body"] == "Loved the ending."
    assert rows[0]["book_id"] == 1


def test_empty_body_is_rejected_and_nothing_is_saved():
    with pytest.raises(ValueError, match="Note text cannot be empty"):
        HANDLER.append_note(1, " \n\t ")
    assert note_rows() == []


def test_too_long_body_is_rejected_and_nothing_is_saved():
    with pytest.raises(InputTooLong):
        HANDLER.append_note(1, "a" * (MAX_CHARS + 1))
    assert note_rows() == []


def test_missing_book_is_rejected_and_nothing_is_saved():
    # Regression test for the Part 3 interface fault: must be a readable
    # ValueError, not a raw sqlite3.IntegrityError.
    with pytest.raises(ValueError, match="Book not found"):
        HANDLER.append_note(999999, "orphan note")
    assert note_rows() == []


def test_get_book_returns_notes_written_through_append_note():
    HANDLER.append_note(2, "First impression")
    HANDLER.append_note(2, "Second thought")
    book = HANDLER.get_book(2)
    assert book["title"] == "Emma"
    assert [n["text"] for n in book["notes"]] == ["First impression", "Second thought"]


def test_get_book_unknown_id_returns_none():
    assert HANDLER.get_book(999999) is None


def test_search_returns_a_matching_title():
    result = HANDLER.execute_search("Dune")
    assert [book["title"] for book in result["results"]] == ["Dune"]


# ---- Driver 2: HTTP layer through FastAPI (app.py) -------------------------
def test_post_note_over_http_returns_200_and_row_exists():
    r = client.post("/api/notes", json={"isbn": 1, "body": "Great world-building"})
    assert r.status_code == 200
    assert r.json()["ok"] is True
    assert r.json()["note"]["body"] == "Great world-building"
    assert len(note_rows()) == 1


def test_post_empty_note_over_http_returns_400():
    r = client.post("/api/notes", json={"isbn": 1, "body": "   "})
    assert r.status_code == 400
    assert note_rows() == []


def test_post_note_for_missing_book_returns_400_not_500():
    r = client.post("/api/notes", json={"isbn": 999999, "body": "orphan"})
    assert 400 <= r.status_code < 500
    assert "Book not found" in r.json()["detail"]
    assert note_rows() == []


def test_get_book_over_http_shows_saved_note():
    client.post("/api/notes", json={"isbn": 2, "body": "Witty and sharp"})
    r = client.get("/api/books/2")
    assert r.status_code == 200
    assert [n["text"] for n in r.json()["notes"]] == ["Witty and sharp"]


# ---- Assistant (chat) ------------------------------------------------------
def test_chat_returns_the_llm_reply_with_text_picks_and_used():
    result = HANDLER.submit_chat_query("hello there")
    assert result["text"] == "stubbed reply"
    assert result["picks"] == []
    assert isinstance(result["used"], list)


def test_chat_over_http_answers_even_without_an_api_key():
    # app_module.handler uses the real Groq client; with no key it must degrade gracefully
    r = client.post("/api/chat", json={"query": "suggest a short mystery", "history": []})
    assert r.status_code == 200
    assert r.json()["text"]


def test_chat_rejects_text_over_the_limit():
    r = client.post("/api/chat", json={"query": "x" * (MAX_CHARS + 1)})
    assert r.status_code == 400


def test_chat_falls_back_when_the_ai_is_unavailable():
    from nlp_chatbot import ChatUnavailable

    def broken(prompt):
        raise ChatUnavailable("The AI key is missing.")

    handler = UserHandler(llm=broken)
    result = handler.submit_chat_query("recommend something")
    assert result["text"] == "The AI key is missing."


# ---- Five short demonstration cases (16-20) ---------------------------------
def test_16_list_books_returns_sample_catalog():
    r = client.get("/api/books", params={"limit": 10})
    assert r.status_code == 200
    assert {book["title"] for book in r.json()} >= {"Dune", "Emma"}


def test_17_save_progress_updates_library_and_reading_log():
    r = client.post("/api/progress", json={"isbn": 1, "pages": 100, "day": "2026-11-23"})
    assert r.status_code == 200
    assert r.json()["ok"] is True
    assert DB.query("SELECT progress, state FROM library WHERE id = 1") == [
        {"progress": 100, "state": 1}
    ]
    assert DB.query("SELECT pages FROM reading_log WHERE day = '2026-11-23'") == [
        {"pages": 100}
    ]


def test_18_rating_a_book_adds_it_to_the_library():
    r = client.post("/api/books/2/rate", json={"rating": 5})
    assert r.status_code == 200
    assert r.json()["rating"] == 5
    row = DB.query("SELECT state, rating FROM library WHERE id = 2")[0]
    assert row == {"state": 4, "rating": 5}


def test_19_add_reread_and_remove_book_from_library():
    assert client.post("/api/library/add", json={"isbn": 1}).status_code == 200
    assert client.post("/api/books/1/reread").status_code == 200
    assert client.get("/api/library").json()[0]["isbn"] == "1"
    assert client.delete("/api/library/1").status_code == 200
    assert client.get("/api/library").json() == []


def test_20_save_settings_and_reading_log_then_read_them_back():
    settings = client.post("/api/settings", json={
        "name": "Demo Reader",
        "goal": 40,
        "yearGoal": 12,
        "favGenres": ["Fantasy", "Mystery"],
    })
    log = client.post("/api/reading-log", json={"day": "2026-11-23", "pages": 25})
    assert settings.status_code == 200
    assert log.status_code == 200
    assert client.get("/api/settings").json() == {
        "name": "Demo Reader",
        "goal": 40,
        "yearGoal": 12,
        "favGenres": ["Fantasy", "Mystery"],
    }
    assert client.get("/api/reading-log").json() == {"2026-11-23": 25}
