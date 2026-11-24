# AI Book Assistant - Sprint 3 Backend & Frontend Integration

## Overview
This directory contains the working prototype connecting the single-file front end to the Python **FastAPI** backend running on `127.0.0.1:8000` with **SQLite** (`books.db`), implementing the Sprint 3 architectural subsystems and design patterns:
- **DatabaseManager** (`database_manager.py`): Creational Singleton owning the single SQLite connection with parameterized queries.
- **UserHandler** (`user_handler.py`): Structural Facade validating inputs and coordinating subsystems.
- **RecommendationEngine** (`recommendation_engine.py`): Behavioral Strategy pattern (`SearchBasedStrategy`, `DashboardStrategy`, `ChatBasedStrategy`).
- **FastAPI Web Server** (`app.py`): Serves the front end at `http://127.0.0.1:8000` and provides RESTful endpoints.

## How to Run
You Must Download and Extract goodreads_books.json.gz from `https://cseweb.ucsd.edu/~jmcauley/datasets/goodreads.html#datasets` and add it to data-pipeline folder to build the database.
Do the Same for goodreads_book_authors.json.gz and goodreads_books_series.json.gz; add them both to data-pipeline folder

### AI assistant setup
The Assistant writes its answers with [Groq](https://console.groq.com/keys) (model `openai/gpt-oss-20b`).
1. Copy `backend/.env.example` to `backend/.env` and put your key after `GROQ_API_KEY=`. Never commit `.env`.
2. Start the app. The first time, it builds `backend/search_index.db` in the background (a few minutes for the full
   2 GB database). The assistant answers recommendation requests once the terminal prints `Search index ready.`
   Delete `search_index.db` to rebuild it after rebuilding `books.db`.

How it works: your request is matched against the catalog with SQLite full-text search (FTS5), the best matches plus
your library are sent to Groq, and Groq explains the picks in natural language. It only recommends books found in the
catalog, and it never writes to your library.

Double-click `start_app.bat` (installs packages, starts the server, opens the browser) or run:
```bash
python -m uvicorn app:app --host 127.0.0.1 --port 8000 --reload
```
Then open your browser to [http://127.0.0.1:8000](http://127.0.0.1:8000).

*(The HTML file also runs offline via file:// and automatically connects to the API when available, falling back gracefully if the server is stopped).*

## Time Machine (Streak Simulation)
To simulate time passing and test streak changes:
1. Open the Home screen (`#/`).
2. Look at the top **Time Machine** bar:
   - **`+1 Day (Skip Reading)`**: Advances time by 1 day without logging pages. If consecutive reading stops, your streak resets to 0 and the headline switches to:
     `Oops! You lost your streak!` with a dotted candle.
   - **`+1 Day (Hit Goal)`**: Logs your daily goal (40 pages) and advances to the next day. The streak increases and the headline displays:
     `You're on a roll!` with glowing flame candles.
   - **`Reset to Today`**: Snaps the clock back to the real calendar date.
