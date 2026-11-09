"""app.py: FastAPI web server wrapping UserHandler facade.

Provides JSON endpoints on 127.0.0.1:8000 (NFR-12), serves the single-file
front end at root, enables CORS, and maintains strict read-only access for the assistant.
"""
from pathlib import Path
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel
from typing import Optional, List

from user_handler import UserHandler, InputTooLong

app = FastAPI(title="AI Book Assistant API", version="1.0.0")

# Enable CORS for file:// access and local clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

handler = UserHandler()


# ---- Request / Response Models -----------------------------------------------
class ProgressRequest(BaseModel):
    isbn: str
    pages: int
    day: Optional[str] = None


class RateRequest(BaseModel):
    rating: int


class NoteRequest(BaseModel):
    isbn: str
    body: str
    kind: Optional[str] = "note"


class NoteEditRequest(BaseModel):
    body: str


class ChatRequest(BaseModel):
    query: str
    isbn: Optional[str] = None


class SettingsRequest(BaseModel):
    name: Optional[str] = None
    goal: Optional[int] = None
    yearGoal: Optional[int] = None
    favGenres: Optional[List[str]] = None


# ---- Static Frontend Serving -------------------------------------------------
@app.get("/", response_class=HTMLResponse)
async def serve_home():
    html_path = Path(__file__).with_name("index.html")
    if html_path.exists():
        return HTMLResponse(content=html_path.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>AI Book Assistant API Ready</h1><p>index.html not found</p>")


@app.get("/index.html", response_class=HTMLResponse)
async def serve_index():
    return await serve_home()


# ---- API Endpoints: Search & Books (FR-01 to FR-05) -------------------------
@app.get("/api/search")
async def search_books(q: str = Query("", max_length=200), genre: str = ""):
    try:
        return handler.execute_search(q, genre)
    except InputTooLong as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/books/{isbn}")
async def get_book(isbn: str):
    book = handler.get_book(isbn)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    return book


# ---- API Endpoints: Progress, Rating, Library (FR-06 to FR-10, FR-16) --------
@app.post("/api/progress")
async def save_progress(req: ProgressRequest):
    try:
        handler.save_reading_progress(req.isbn, req.pages, req.day)
        return {"ok": True, "isbn": req.isbn, "pages": req.pages}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/books/{isbn}/rate")
async def rate_book(isbn: str, req: RateRequest):
    handler.rate_book(isbn, req.rating)
    return {"ok": True, "isbn": isbn, "rating": req.rating}


@app.post("/api/library/add")
async def add_to_library(req: dict):
    isbn = req.get("isbn")
    if not isbn:
        raise HTTPException(status_code=400, detail="Missing isbn")
    handler.add_to_library(isbn)
    return {"ok": True, "isbn": isbn}


@app.delete("/api/library/{isbn}")
async def remove_from_library(isbn: str):
    handler.remove_from_library(isbn)
    return {"ok": True, "isbn": isbn}


@app.post("/api/books/{isbn}/reread")
async def reread_book(isbn: str):
    handler.reread_book(isbn)
    return {"ok": True, "isbn": isbn}


@app.get("/api/library")
async def get_my_library():
    return handler.get_my_library()


# ---- API Endpoints: Notes (FR-17, FR-31) -------------------------------------
@app.post("/api/notes")
async def add_note(req: NoteRequest):
    try:
        created = handler.append_note(req.isbn, req.body, req.kind or "note")
        return {"ok": True, "note": created}
    except (ValueError, InputTooLong) as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.put("/api/notes/{note_id}")
async def edit_note(note_id: int, req: NoteEditRequest):
    try:
        handler.edit_note(note_id, req.body)
        return {"ok": True, "id": note_id}
    except InputTooLong as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/api/notes/{note_id}")
async def delete_note(note_id: int):
    handler.delete_note(note_id)
    return {"ok": True, "id": note_id}


# ---- API Endpoints: Dashboard & Recommendations (FR-23, FR-25) ---------------
@app.get("/api/dashboard")
async def get_dashboard(genre: str = "", limit: int = 4):
    return handler.get_dashboard_data(genre=genre, limit=limit)


@app.get("/api/recommendations")
async def get_recommendations(genre: str = "", limit: int = 8):
    return handler.get_dashboard_data(genre=genre, limit=limit)


# ---- API Endpoints: Settings & Log (FR-12, FR-13, FR-37) ---------------------
@app.get("/api/settings")
async def get_settings():
    return handler.get_settings()


@app.post("/api/settings")
async def save_settings(req: SettingsRequest):
    handler.save_settings(req.model_dump(exclude_unset=True))
    return {"ok": True}


@app.get("/api/reading-log")
async def get_reading_log():
    return handler.get_reading_log()


@app.post("/api/reading-log")
async def log_reading_day(req: dict):
    day = req.get("day")
    pages = req.get("pages")
    if not day or pages is None:
        raise HTTPException(status_code=400, detail="Missing day or pages")
    handler.log_pages_for_day(day, pages)
    return {"ok": True, "day": day, "pages": pages}


# ---- API Endpoint: Assistant (READ ONLY, FR-40, NFR-13) ----------------------
@app.post("/api/chat")
async def chat_assistant(req: ChatRequest):
    try:
        return handler.submit_chat_query(req.query, req.isbn)
    except InputTooLong as e:
        raise HTTPException(status_code=400, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
