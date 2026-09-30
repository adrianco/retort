# Book Collection API

REST API for managing books, built with the Python standard library
(`http.server` + `sqlite3`). No third-party runtime dependencies. Requires Python 3.9+.

## Run

    python app.py

Environment variables: `HOST` (default `127.0.0.1`), `PORT` (default `8000`),
`DB_PATH` (default `books.db`).

## Endpoints

| Method | Path | Description |
|---|---|---|
| POST | /books | Create a book (`title`, `author` required; `year` int and `isbn` string optional) → 201 |
| GET | /books | List books; `?author=Name` filters by exact author → 200 |
| GET | /books/{id} | Get one book → 200 / 404 |
| PUT | /books/{id} | Replace a book's fields → 200 / 404 / 422 |
| DELETE | /books/{id} | Delete → 204 / 404 |
| GET | /health | Health check → `{"status": "ok"}` |

Invalid JSON returns 400; failed validation returns 422 with a `details` list.

Example:

    curl -X POST localhost:8000/books -H 'Content-Type: application/json' \
      -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}'

## Test

    pip install pytest
    python -m pytest
