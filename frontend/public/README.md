# AI Book Assistant - Sprint 3 Backend & Frontend Integration

## Overview
This directory contains the working prototype connecting the single-file front end to the Python **FastAPI** backend running on `127.0.0.1:8000` with **SQLite** (`books.db`), implementing the Sprint 3 architectural subsystems and design patterns:
- **DatabaseManager** (`database_manager.py`): Creational Singleton owning the single SQLite connection with parameterized queries.
- **UserHandler** (`user_handler.py`): Structural Facade validating inputs and coordinating subsystems.
- **RecommendationEngine** (`recommendation_engine.py`): Behavioral Strategy pattern (`SearchBasedStrategy`, `DashboardStrategy`, `ChatBasedStrategy`).
- **FastAPI Web Server** (`app.py`): Serves the front end at `http://127.0.0.1:8000` and provides RESTful endpoints.

## How to Run
Double-click `run_backend.bat` or run:
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
