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
    yield
    DB.execute("DELETE FROM notes")


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
