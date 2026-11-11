import ast
import json
import pandas as pd
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
def pair(books: pd.DataFrame, names: dict) -> None:
    books['authors'] = books['authors'].map(lambda a: ", ".join([names[x['author_id']] for x in asList(a) if x['author_id'] in names]))


# only run if database doesn't exist
if not db.DatabaseManager.present():
    # load authors as id name pairs
    with open('goodreads_book_authors.json', 'r', encoding='utf-8') as au:
        authors = dict()
        for line in au:
            if (x := json.loads(line)):
                authors[x['author_id']] = x['name']

    # create database before loading books into it
    db.DatabaseManager.get_instance(r"..\backend\books.db")

    # target info columns
    with pd.read_json('goodreads_books.json', lines=True, chunksize=10000) as chunks:
        for chunk in chunks:
            # Process Chunk Into Database Schema
            pair(chunk, authors)
            
            # Extract and Push Each Tuple
            
            break

print("This Works")