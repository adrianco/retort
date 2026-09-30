# Book Collection API

REST API for managing books, built with the Python standard library
(`http.server`) and SQLite. No third-party runtime dependencies.

## Run

    python app.py            # http://127.0.0.1:8000

Environment variables: `HOST`, `PORT`, `DB_PATH` (default `books.db`).

## Endpoints

| Method | Path | Notes |
|---|---|---|
| POST | /books | body: `title`*, `author`*, `year` (int), `isbn`; 201 |
| GET | /books | optional `?author=` exact-match filter |
| GET | /books/{id} | 404 if missing |
| PUT | /books/{id} | full update, same validation as POST |
| DELETE | /books/{id} | 204, or 404 |
| GET | /health | `{"status": "ok"}` |

Validation errors return 400 with a JSON `error` message.

## Test

    pip install pytest
    python -m pytest
