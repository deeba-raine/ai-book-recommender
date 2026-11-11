import ast
import json
import pandas as pd
from datetime import date
import database_manager as db

def asList(n) -> list:
    # json list to python list
    if isinstance(n, str):
        try:
            n = ast.literal_eval(n)
        except (ValueError, SyntaxError):
            return []
    return n if isinstance(n, list) else []

# replace author ids with the author names
def pair(books: pd.DataFrame, names: dict, arg1: str, arg2: str=None) -> None:
    if arg2:
        books[arg1] = books[arg1].map(lambda a: ", ".join([names[x[arg2]] for x in asList(a) if x[arg2] in names]))
        return
    books[arg1] = books[arg1].map(lambda a: ", ".join(names[i] for i in asList(a) if i in names))

# libarary processing excluding tags
def process(books: pd.DataFrame) -> pd.DataFrame:
    out = pd.DataFrame()
    out = books.drop(columns=['isbn', 'text_reviews_count', 'asin', 'kindle_asin', 'format', 'link', 'isbn13', 'edition_information', 'url', 'ratings_count', 'work_id', 'title_without_series'])

    # map is_ebook
    out['is_ebook'] = out['is_ebook'].str.lower()
    out['is_ebook'] = out['is_ebook'].map({'true': 1, 'false': 0})

    # process publication date
    out['pubDate'] = (out['publication_year'].astype(str) + '-' + out['publication_month'].astype(str).str.zfill(2) + '-' + out['publication_day'].astype(str).str.zfill(2))
    out = out.drop(columns=['publication_year', 'publication_month', 'publication_day'])

    # number conversions
    out['num_pages'] = pd.to_numeric(out['num_pages'], errors='coerce')
    out = out[out['num_pages'] > 0]
    out['book_id'] = out['book_id'].astype(int)

    out['average_rating'] = pd.to_numeric(out['average_rating'], errors='coerce')
    out['average_rating'] = out['average_rating'].fillna(0)

    # turn similar books list into string with comma seperators
    out['similar_books'] = out['similar_books'].map(", ".join)

    ### REPLACE WITH TAG PROCESSOR LATER
    out['tags'] = ""

    return out

# only run if database doesn't exist
if not db.DatabaseManager.present():
    # load authors as id name pairs
    with open('goodreads_book_authors.json', 'r', encoding='utf-8') as au:
        authors = dict()
        for line in au:
            if (x := json.loads(line)):
                authors[x['author_id']] = x['name']

    # load series as id name pairs
    with open('goodreads_book_series.json', 'r', encoding='utf-8') as se:
        series = dict()
        for line in se:
            if (x := json.loads(line)):
                series[x['series_id']] = x['title']

    # create database before loading books into it
    manager = db.DatabaseManager.get_instance(r"..\backend\books.db")

    # target info columns
    failed = 0
    with pd.read_json('goodreads_books.json', lines=True, chunksize=10000) as chunks:
        for chunk in chunks:
            # transform ids to names/titles
            pair(chunk, authors, 'authors', 'author_id')
            pair(chunk, series, 'series')

            # process chunk
            rows = process(chunk)

            # Extract features -- empty notes until user writes into them
            rows['notes'] = ''
            rows = rows[['book_id', 'title', 'authors', 'country_code', 'language_code', 'description', 'is_ebook', 'image_url', 'publisher', 'pubDate', 'series', 'tags', 'similar_books', 'num_pages', 'average_rating', 'notes']]

            # create nulls and attempt to push
            rows = rows.astype(object).where(rows.notna(), None)
            failed += sum(not manager.addBook(r) for r in rows.itertuples(index=False, name=None))
            manager.pushChanges()
            #break

    print(f"Successful Build with {failed} Dropped Rows")