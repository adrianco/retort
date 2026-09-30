# Book Collection API

A REST API for managing books, built with the Python standard library
(`http.server` + `sqlite3`). It has no runtime dependencies.

## Setup

    python -m venv venv && source venv/bin/activate
    pip install pytest      # tests only

## Run

    python app.py

Environment variables: `PORT` (default 8000), `HOST` (default 127.0.0.1),
`BOOKS_DB` (SQLite file, default `books.db`).

## Endpoints

| Method | Path | Description |
|---|---|---|
| POST | /books | Create a book (`title`, `author` required; `year` int, `isbn` string optional) -> 201 |
| GET | /books | List books; optional `?author=` exact-match filter |
| GET | /books/{id} | Get a book (404 if missing) |
| PUT | /books/{id} | Replace a book's fields (400 invalid, 404 missing) |
| DELETE | /books/{id} | Delete a book -> 204 (404 if missing) |
| GET | /health | Health check -> `{"status": "ok"}` |

Example:

    curl -X POST localhost:8000/books -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"111"}'

## Tests

    python -m pytest
