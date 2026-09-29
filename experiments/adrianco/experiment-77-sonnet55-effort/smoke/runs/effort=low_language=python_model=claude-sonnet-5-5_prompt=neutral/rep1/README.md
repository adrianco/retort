# Book Collection API

REST API for managing books, built with the Python standard library
(`http.server` + `sqlite3`); no third-party runtime dependencies. Python 3.9+.

## Run

    python app.py [port]      # default port 8000, data in ./books.db

## Endpoints

| Method | Path | Description |
|---|---|---|
| GET | /health | Health check |
| POST | /books | Create (`title`, `author` required; `year` int, `isbn` string optional) → 201 |
| GET | /books | List; optional `?author=Name` exact-match filter |
| GET | /books/{id} | Get one (404 if missing) |
| PUT | /books/{id} | Full update (400 invalid, 404 missing) |
| DELETE | /books/{id} | Delete → 204 |

Example:

    curl -X POST localhost:8000/books -d '{"title":"Dune","author":"Herbert","year":1965,"isbn":"123"}'

## Test

    pip install pytest
    python -m pytest tests
