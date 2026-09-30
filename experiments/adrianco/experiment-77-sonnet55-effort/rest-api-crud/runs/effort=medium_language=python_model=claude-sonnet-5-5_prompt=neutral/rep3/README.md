# Book Collection API

A REST API for managing books, written in Python using only the standard
library (WSGI + `sqlite3`); no framework was specified, so no third-party
runtime dependencies are needed.

## Setup and run

    python app.py                # serves on http://127.0.0.1:8000

Environment variables: `PORT` (default 8000), `BOOKS_DB` (SQLite file, default `books.db`).

## Endpoints

| Method | Path | Description |
|---|---|---|
| POST | /books | Create (`title`, `author` required; `year` int, `isbn` string optional) → 201 |
| GET | /books | List; optional `?author=` exact-match filter |
| GET | /books/{id} | Get one → 200 / 404 |
| PUT | /books/{id} | Replace/update → 200 / 400 / 404 |
| DELETE | /books/{id} | Delete → 204 / 404 |
| GET | /health | `{"status": "ok"}` |

Errors return JSON `{"error": "..."}` (400 validation, 404 missing, 405 bad method).

Example:

    curl -X POST localhost:8000/books -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0441013593"}'

## Tests

    pip install pytest
    python -m pytest
