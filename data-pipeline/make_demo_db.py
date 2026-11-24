"""Builds backend/books.db from a small hand-written demo catalog.

Use this when the full Goodreads database isn't on your computer. The real
books.db (built by db_build.py) replaces it: just drop that file into backend/.
Run from the repo root:  python data-pipeline/make_demo_db.py
"""
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "backend" / "schema.sql"
OUT = ROOT / "backend" / "books.db"

# id, title, author, tags, pages, avg rating, publisher, year, description
BOOKS = [
 (1, "Dune", "Frank Herbert", "Science fiction,Fantasy", 412, 4.3, "Chilton", 1965,
  "A desert planet, a noble family caught in a power struggle, and a young heir who must survive and lead."),
 (2, "Emma", "Jane Austen", "Classic,Romance", 474, 3.9, "John Murray", 1815,
  "A clever, confident young woman in a country village decides she knows best who should marry whom."),
 (3, "Gone Girl", "Gillian Flynn", "Thriller,Mystery", 419, 4.1, "Crown", 2012,
  "On their fifth anniversary a man's wife disappears, and the more the police learn, the less the marriage adds up."),
 (4, "The Hobbit", "J.R.R. Tolkien", "Fantasy,Adventure", 310, 4.3, "George Allen & Unwin", 1937,
  "A comfortable hobbit is pulled into a quest with a company of dwarves to win back a mountain treasure from a dragon."),
 (5, "The Name of the Wind", "Patrick Rothfuss", "Fantasy,Adventure", 662, 4.5, "DAW Books", 2007,
  "A gifted young man tells the story of how he became the most notorious wizard in the world."),
 (6, "Mistborn: The Final Empire", "Brandon Sanderson", "Fantasy,Adventure", 541, 4.5, "Tor Books", 2006,
  "A crew of thieves plans to overthrow an immortal emperor who has ruled a land covered in ash for a thousand years."),
 (7, "Pride and Prejudice", "Jane Austen", "Classic,Romance", 432, 4.3, "T. Egerton", 1813,
  "Elizabeth Bennet turns down a proud, wealthy suitor and then has to face her own first impressions."),
 (8, "Frankenstein", "Mary Shelley", "Classic,Horror", 280, 3.8, "Lackington, Hughes", 1818,
  "A young scientist brings a creature to life, then abandons it, with terrible results for everyone he loves."),
 (9, "Dracula", "Bram Stoker", "Horror,Classic", 418, 3.9, "Archibald Constable", 1897,
  "Letters, diaries and newspaper clippings tell how a Transylvanian count travels to England to find new victims."),
 (10, "The Girl with the Dragon Tattoo", "Stieg Larsson", "Thriller,Mystery", 590, 4.0, "Norstedts", 2005,
  "A disgraced journalist and a hacker with a sharp mind investigate a forty-year-old disappearance in a wealthy family."),
 (11, "Big Little Lies", "Liane Moriarty", "Mystery,Fiction", 460, 3.9, "Penguin", 2014,
  "Three mothers at a school in a seaside town each have a secret, and a death at a school fundraiser ties them together."),
 (12, "Sapiens: A Brief History of Humankind", "Yuval Noah Harari", "Nonfiction,History", 443, 4.0, "Harvill Secker", 2011,
  "A sweeping look at how Homo sapiens came to dominate the planet, from the first tools to the modern economy."),
 (13, "Educated", "Tara Westover", "Memoir,Nonfiction", 334, 4.5, "Random House", 2018,
  "A woman raised by survivalist parents in Idaho teaches herself enough to go to university and then has to face her family."),
 (14, "The Martian", "Andy Weir", "Science fiction,Adventure", 369, 4.4, "Crown", 2011,
  "An astronaut left behind on Mars has to grow food, fix his habitat and find a way to signal Earth with very little help."),
 (15, "Neuromancer", "William Gibson", "Science fiction,Cyberpunk", 271, 3.9, "Ace Books", 1984,
  "A washed-up computer hacker takes one last job that could free him from the criminals who ruined him."),
 (16, "The Left Hand of Darkness", "Ursula K. Le Guin", "Science fiction,Classic", 304, 4.1, "Ace Books", 1969,
  "An envoy from an interstellar alliance travels to a frozen world where people have no fixed gender, and learns what trust costs."),
 (17, "Foundation", "Isaac Asimov", "Science fiction,Classic", 255, 4.2, "Gnome Press", 1951,
  "A mathematician predicts the collapse of a galactic empire and plans to shorten the dark age that follows."),
 (18, "A Game of Thrones", "George R.R. Martin", "Fantasy,Epic", 694, 4.4, "Bantam Spectra", 1996,
  "Noble families fight for the Iron Throne while winter approaches and an old enemy stirs beyond the northern wall."),
 (19, "The Hunger Games", "Suzanne Collins", "Young adult,Science fiction", 374, 4.3, "Scholastic", 2008,
  "A teenager volunteers to take her younger sister's place in a televised fight to the death in a ruined nation."),
 (20, "Project Hail Mary", "Andy Weir", "Science fiction,Adventure", 476, 4.5, "Ballantine", 2021,
  "A schoolteacher wakes up alone on a spaceship with no memory and must work out why he is there and how to save Earth."),
 (21, "Rebecca", "Daphne du Maurier", "Mystery,Classic", 380, 3.9, "Victor Gollancz", 1938,
  "A young bride moves into her new husband's estate, where the memory of his first wife still rules every room."),
 (22, "The Haunting of Hill House", "Shirley Jackson", "Horror,Classic", 246, 3.9, "Viking", 1959,
  "Four people spend a summer in a house with a reputation, and the house begins to choose who stays."),
 (23, "Circe", "Madeline Miller", "Fantasy,Mythology", 393, 4.2, "Little, Brown", 2018,
  "The witch from the Odyssey tells her own story, from an exiled childhood to her dealings with gods and heroes."),
 (24, "The Night Circus", "Erin Morgenstern", "Fantasy,Romance", 387, 3.9, "Doubleday", 2011,
  "Two magicians bound to a contest meet in a black-and-white circus that only opens at night."),
 (25, "Atomic Habits", "James Clear", "Nonfiction,Self-help", 320, 4.3, "Avery", 2018,
  "Small daily changes in habits compound over time, and this book gives a method for building good ones and breaking bad ones."),
 (26, "Thinking, Fast and Slow", "Daniel Kahneman", "Nonfiction,Psychology", 499, 4.2, "Farrar, Straus and Giroux", 2011,
  "A tour of the two systems that drive how people think, and the mistakes each one tends to make."),
 (27, "The Road", "Cormac McCarthy", "Fiction,Post-apocalyptic", 287, 4.0, "Alfred A. Knopf", 2006,
  "A father and his young son walk south through a burned country, trying to stay alive and stay good."),
 (28, "Murder on the Orient Express", "Agatha Christie", "Mystery,Classic", 256, 4.0, "Collins Crime Club", 1934,
  "A famous detective is asked to solve a murder on a snowbound train, where every passenger has a reason to lie."),
 (29, "The Lion, the Witch and the Wardrobe", "C.S. Lewis", "Fantasy,Children", 206, 4.2, "Geoffrey Bles", 1950,
  "Four siblings find a wardrobe that leads to a snowy land ruled by a witch, where an old prophecy is about to come true."),
 (30, "Where the Crawdads Sing", "Delia Owens", "Mystery,Fiction", 370, 4.0, "G.P. Putnam's Sons", 2018,
  "A girl raised alone in the marshes of North Carolina is accused of murder, and the story goes back to her childhood."),
]


def main():
    if OUT.exists():
        OUT.unlink()
    conn = sqlite3.connect(OUT)
    conn.executescript(SCHEMA.read_text(encoding="utf-8"))
    for (bid, title, author, tags, pages, avg, publisher, year, descr) in BOOKS:
        conn.execute(
            "INSERT INTO books (id, title, author, country, language, descr, isEBook, cover, publisher, "
            "publDate, series, tags, similar, pages, avgRating, notes) "
            "VALUES (?, ?, ?, 'US', 'English', ?, 0, '', ?, ?, '', ?, '', ?, ?, '')",
            (bid, title, author, descr, publisher, f"{year}-01-01", tags, pages, avg),
        )
    conn.commit()
    conn.close()
    print(f"Wrote {len(BOOKS)} demo books to {OUT}")


if __name__ == "__main__":
    main()
