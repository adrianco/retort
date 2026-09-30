# Book Collection API

REST API for managing books, built with the Python standard library
(`http.server` + `sqlite3`) — no third-party runtime dependencies.

## Setup & run

    python app.py            # serves on http://127.0.0.1:8000

Environment: `PORT` (default 8000), `BOOKS_DB` (SQLite file, default `books.db`).

## Endpoints

| Method | Path | Description |
|---|---|---|
| POST | /books | Create (`title`, `author` required; `year` int, `isbn` string optional) → 201 |
| GET | /books | List; optional `?author=Name` exact-match filter |
| GET | /books/{id} | Get one (404 if missing) |
| PUT | /books/{id} | Full update (same validation) |
| DELETE | /books/{id} | Delete → 204 |
| GET | /health | `{"status": "ok"}` |

Errors are JSON: `{"error": "...", "details": [...]}` with 400 (validation) or 404.

Example:

    curl -X POST localhost:8000/books -d '{"title":"Dune","author":"Frank Herbert","year":1965}'

## Tests

    pip install pytest
    python -m pytest
