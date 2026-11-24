"""recommendation_engine.py: Behavioral pattern, Strategy (Design Pattern 3).

RecommendationEngine is the context. Each algorithm is its own class that
implements recommend(context), so strategies swap at runtime (FR-21, NFR-09).
"""
from abc import ABC, abstractmethod


class RecommendationStrategy(ABC):
    """Common interface every algorithm implements."""

    @abstractmethod
    def recommend(self, context):
        """Return a list of book dicts, best match first."""


class SearchBasedStrategy(RecommendationStrategy):
    """FR-22: theme, keyword and author matches straight from SQLite."""

    def __init__(self, db):
        self.db = db

    def recommend(self, context):
        query = context.get("query", "")[:200]
        like = f"%{query}%"
        genre = context.get("genre", "")
        if genre:
            return self.db.query(
                "SELECT * FROM books WHERE (title LIKE ? OR author LIKE ? OR tags LIKE ?) "
                "AND tags LIKE ? LIMIT 50", (like, like, like, f"%{genre}%"))
        return self.db.query(
            "SELECT * FROM books WHERE title LIKE ? OR author LIKE ? "
            "OR tags LIKE ? LIMIT 50", (like, like, like))


class DashboardStrategy(RecommendationStrategy):
    """FR-23: rank unread books by overlap with highly rated books."""

    def __init__(self, db):
        self.db = db

    def recommend(self, context):
        liked = self.db.query(
            "SELECT b.tags FROM library l JOIN books b ON b.id = l.id "
            "WHERE l.rating >= 4")
        wanted = {t.strip().lower() for row in liked for t in (row["tags"] or "").split(",") if t.strip()}

        # Favorite genres from settings
        fav_rows = self.db.query("SELECT value FROM settings WHERE key = 'fav_genres'")
        fav_genres = [g.strip().lower() for g in fav_rows[0]["value"].split(",")] if fav_rows and fav_rows[0]["value"] else []

        # Books not yet in the library, or still marked Unstarted (state 0)
        unread = self.db.query(
            "SELECT b.*, COALESCE(l.state, -1) AS state, COALESCE(l.rating, 0) AS rating, "
            "COALESCE(l.progress, 0) AS progress, l.startDate AS startDate "
            "FROM books b LEFT JOIN library l ON l.id = b.id "
            "WHERE l.id IS NULL OR l.state = 0 LIMIT 2000")

        target_genre = context.get("genre", "").lower()
        if target_genre:
            unread = [b for b in unread if target_genre in (b["tags"] or "").lower()]

        scored = []
        for book in unread:
            tags = {t.strip().lower() for t in (book["tags"] or "").split(",") if t.strip()}
            genres = sorted(tags)
            overlap = len(tags & wanted)
            fav_match = any(g in fav_genres for g in genres)
            score = overlap * 2 + (2 if fav_match else 0)
            
            match_pct = max(58, min(97, 52 + score * 6))
            why = (f"Shares #{next(iter(tags & wanted))} with books you rated highly"
                   if (tags & wanted) else
                   f"Matches your favorite genre: {genres[0].title()}"
                   if fav_match and genres else
                   "Popular pick for readers in this genre")
            
            b_dict = dict(book)
            b_dict["match"] = match_pct
            b_dict["why"] = why
            b_dict["score"] = score
            scored.append(b_dict)

        scored.sort(key=lambda b: -b["score"])
        limit = context.get("limit", 4)
        return scored[:limit]


class ChatBasedStrategy(RecommendationStrategy):
    """FR-24: ask the local Ollama model, only on an explicit request (FR-29)."""

    def __init__(self, llm):
        self.llm = llm            # callable(prompt) -> text, wraps Ollama

    def recommend(self, context):
        reply = self.llm(context["prompt"])
        return [{"suggestion": reply}]


class RecommendationEngine:
    def __init__(self, strategy):
        self._strategy = strategy

    def set_strategy(self, strategy):
        self._strategy = strategy         # runtime switch (FR-21)

    def get_recommendations(self, context):
        return self._strategy.recommend(context)
