"""Acceptance tests AT-01 to AT-15 (the final project test list).

Run this file on its own:  python -m pytest tests/test_acceptance.py -v

Each test is one action and one expected outcome. Some of them are supposed to
FAIL right now: those features are not built yet or depend on the full
database. A failing acceptance test is reported honestly, not hidden.

The tests copy backend/books.db to a temp folder first, so the real file is
never changed by a test run (ratings, notes and progress are written to the copy).
"""
import os
import shutil
import sys
import time
from datetime import date
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND))

from fastapi.testclient import TestClient  # noqa: E402
from database_manager import DatabaseManager  # noqa: E402
from user_handler import UserHandler  # noqa: E402

TODAY = date.today().isoformat()


@pytest.fixture(scope="module", autouse=True)
def demo_app(tmp_path_factory):
    """Point the running app at a temporary copy of books.db."""
    source = BACKEND / "books.db"
    if not source.is_file():
        pytest.skip("backend/books.db not found. Run data-pipeline/make_demo_db.py first.")
    copy = tmp_path_factory.mktemp("acceptance") / "books.db"
    shutil.copy(source, copy)

    DatabaseManager.reset_for_tests()
    DatabaseManager.get_instance(str(copy))
    import app as app_module
    app_module.handler = UserHandler()

    # Give the search index a moment to build (it is built in a background thread)
    deadline = time.time() + 60
    while app_module.handler.nlp_bot.index.status == "building" and time.time() < deadline:
        time.sleep(0.5)

    yield app_module
    DatabaseManager.reset_for_tests()


@pytest.fixture
def client(demo_app):
    return TestClient(demo_app.app, raise_server_exceptions=False)


@pytest.fixture
def db(demo_app):
    return demo_app.handler.db


# AT-01: The user rates a book; the rating is saved in the database and shows in the library
def test_at01_rating_updates_database_and_library(client, db):
    r = client.post("/api/books/1/rate", json={"rating": 5})
    assert r.status_code == 200
    row = db.query("SELECT rating FROM library WHERE id = 1")
    assert row and row[0]["rating"] == 5
    lib = [b for b in client.get("/api/library").json() if b["id"] == 1]
    assert lib and lib[0]["rating"] == 5


# AT-02: Notes can be created, edited and deleted; notes over 3000 characters are refused
def test_at02_notes_create_edit_delete_and_limit(client):
    r = client.post("/api/notes", json={"isbn": 1, "body": "Loved the ending."})
    assert r.status_code == 200
    note_id = r.json()["note"]["id"]

    r = client.put(f"/api/notes/{note_id}", json={"body": "Changed my mind."})
    assert r.status_code == 200
    assert client.get("/api/books/1").json()["notes"][0]["text"] == "Changed my mind."

    r = client.post("/api/notes", json={"isbn": 1, "body": "a" * 3001})
    assert r.status_code == 400
    r = client.put(f"/api/notes/{note_id}", json={"body": "a" * 3001})
    assert r.status_code == 400

    r = client.delete(f"/api/notes/{note_id}")
    assert r.status_code == 200
    assert all(n["id"] != note_id for n in client.get("/api/books/1").json()["notes"])


# AT-03: Searching for a book title finds it
def test_at03_search_by_title(client):
    results = client.get("/api/search?q=Dune").json()["results"]
    assert any(b["title"] == "Dune" for b in results)


# AT-04: Searching for an author finds the books they wrote
def test_at04_search_by_author(client):
    titles = [b["title"] for b in client.get("/api/search?q=Jane Austen").json()["results"]]
    assert "Emma" in titles and "Pride and Prejudice" in titles


# AT-05: Changing the name in settings saves it (the top-right initial is checked by hand)
def test_at05_name_change_saved(client, db):
    r = client.post("/api/settings", json={"name": "Sam"})
    assert r.status_code == 200
    assert client.get("/api/settings").json()["name"] == "Sam"
    row = db.query("SELECT value FROM settings WHERE key = 'display_name'")
    assert row and row[0]["value"] == "Sam"


# AT-06: Updating pages read saves progress and adds to today's reading log
def test_at06_pages_read_updates_progress(client):
    r = client.post("/api/progress", json={"isbn": 2, "pages": 50, "day": TODAY})
    assert r.status_code == 200
    lib = [b for b in client.get("/api/library").json() if b["id"] == 2]
    assert lib and lib[0]["progress"] == 50
    assert client.get("/api/reading-log").json().get(TODAY, 0) >= 50


# AT-07: After notes are saved, the NLP module pulls out up to 4 themes, up to 5 named
# entities and a tone (positive, negative, mixed or neutral).  NOT BUILT YET.
def test_at07_notes_are_analysed_for_themes_entities_and_tone(client):
    client.post("/api/notes", json={"isbn": 1, "body": "Paul and the Fremen fight for the spice, and I loved it."})
    note = client.get("/api/books/1").json()["notes"][-1]
    assert "themes" in note and "entities" in note and note.get("tone") in ("positive", "negative", "mixed", "neutral")


# AT-08: For You, with a genre picked: at least 3 titles, each with theme tags and a one-line reason,
# all in that genre.
def test_at08_for_you_genre_recommendations(client):
    picks = client.get("/api/dashboard?genre=Fantasy&limit=4").json()
    assert len(picks) >= 3
    for b in picks:
        assert "Fantasy" in b["genres"]
        assert b["genres"], "needs theme tags"
        assert b.get("why"), "needs a one-line reason"


# AT-09: The AI assistant answers within 5 seconds (an AI answer, not an error message)
def test_at09_assistant_answers_within_5_seconds(client):
    start = time.time()
    r = client.post("/api/chat", json={"query": "Recommend me a fantasy book"})
    elapsed = time.time() - start
    text = r.json()["text"]
    assert r.status_code == 200
    assert elapsed < 5
    assert not text.startswith(("The AI key is missing", "The AI service", "I couldn't reach",
                                "The AI package", "Groq rejected", "The AI service is rate limited"))


# AT-10: A book page shows a Similar Books list, ranked by shared themes (most shared first).
# NOT BUILT YET on the demo catalog (the "similar" column is empty).
def test_at10_similar_books_ranked_by_shared_themes(client):
    similar = client.get("/api/books/1").json()["similar"]
    assert len(similar) >= 1
    overlaps = [len(set(b["genres"]) & {"Science fiction", "Fantasy"}) for b in similar]
    assert overlaps == sorted(overlaps, reverse=True)


# AT-11: Asking the assistant about a book gives an answer that matches the database
def test_at11_assistant_answer_matches_database(client):
    r = client.post("/api/chat", json={"query": "What is this book about?", "isbn": 2})
    text = r.json()["text"]
    assert "Emma" in text or "Austen" in text or "village" in text.lower()


# AT-12: Changing the daily goal updates the web page and the database, and the goal adapts
# to how the reader is doing. The adaptive part is NOT BUILT YET.
def test_at12_daily_goal_saved_and_adapts(client, db):
    r = client.post("/api/settings", json={"goal": 25})
    assert r.status_code == 200
    row = db.query("SELECT value FROM settings WHERE key = 'daily_goal'")
    assert row and row[0]["value"] == "25"
    s = client.get("/api/settings").json()
    assert s["goal"] == 25
    assert "adaptiveGoal" in s


# AT-13: A book in the library shows a live, updating estimate of when it will be finished.
# NOT BUILT YET.
def test_at13_finish_time_estimate_shown(client):
    client.post("/api/library/add", json={"isbn": 4})
    book = client.get("/api/books/4").json()
    assert "estimatedFinish" in book


# AT-14: Export JSON from settings returns settings, library and metadata. NOT BUILT YET.
def test_at14_export_json(client):
    r = client.get("/api/export")
    assert r.status_code == 200
    data = r.json()
    assert {"settings", "library"} <= set(data)


# AT-15: The assistant still answers when the AI service can't be reached (offline).
# Expected to FAIL: there is no offline model yet, so the reply is an error message.
def test_at15_assistant_answers_offline(client, monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    handler = sys.modules["app"].handler
    handler.nlp_bot.client = None
    text = client.post("/api/chat", json={"query": "Recommend me a sci-fi book"}).json()["text"]
    assert not text.startswith("The AI key is missing")
    assert len(text) > 40
